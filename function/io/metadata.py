"""
metadata.py
-----------
Per-trial behavioral metadata saver.

Saves JSON to:
  data/sub-{subject_id}/block_{block_i}/{phase}/{domain}/{stim_pair_id}/metadata.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from function.config.settings import CHAR_CODE as _CHAR_CODE
from function.io.path_builder import ensure_trial_save_dir
from utils.labjack_trigger import (
    ANIMAL_IDX,
    TRIG_P1_CHOICE1, TRIG_P1_CHOICE2,
    TRIG_P2_CHOICE1, TRIG_P2_CHOICE2,
    TRIG_P3_CHOICE1, TRIG_P3_CHOICE2,
)

_SLOT_NAMES: List[str] = ['up', 'down', 'right', 'left']

_CHOICE1_BASE = {'phase_1': TRIG_P1_CHOICE1, 'phase_2': TRIG_P2_CHOICE1, 'phase_3': TRIG_P3_CHOICE1}
_CHOICE2_BASE = {'phase_1': TRIG_P1_CHOICE2, 'phase_2': TRIG_P2_CHOICE2, 'phase_3': TRIG_P3_CHOICE2}


def _trig_code(phase: str, animal: Optional[str], choice_num: int) -> Optional[int]:
    """Return the trigger code that was sent for this choice, or None if not applicable."""
    if animal is None:
        return None
    base = (_CHOICE1_BASE if choice_num == 1 else _CHOICE2_BASE).get(phase)
    idx  = ANIMAL_IDX.get(animal)
    if base is None or idx is None:
        return None
    return base + idx


def build_trial_record(
    subject_id: str,
    block_i: int,
    phase: str,
    domain: str,
    trial_id: int,
    stim_pair_id: str,
    char_order: List[str],
    result: Optional[Dict[str, Any]],
    feedback_score: int = 0,
    elapsed_time: Optional[float] = None,
    session_id: Optional[str] = None,
    neon_recording_id: Optional[str] = None,
    win_size: Optional[tuple] = None,
    slot_coords: Optional[Dict[str, Any]] = None,
    animal_size_px: Optional[int] = None,
) -> Dict[str, Any]:
    """Build and return the trial metadata dict (does not write to disk)."""
    layout = {slot: animal for slot, animal in zip(_SLOT_NAMES, char_order)}
    code_to_animal = {_CHAR_CODE[animal]: animal for animal in char_order}
    responded = result is not None
    c1 = result['choice1'] if responded else None
    c2 = result['choice2'] if responded else None
    c1_animal = code_to_animal.get(c1) if c1 else None
    c2_animal = code_to_animal.get(c2) if c2 else None
    return {
        "subject_id":        subject_id,
        "session_id":        session_id,
        "neon_recording_id": neon_recording_id,
        "block":             f"block_{block_i}",
        "phase":             phase,
        "domain":            domain,
        "trial_id":          trial_id,
        "stim_pair_id":      stim_pair_id,
        "trial_layout":      layout,
        "response_made":     responded,
        "choice1_code":      c1,
        "choice2_code":      c2,
        "choice1_animal":    c1_animal,
        "choice2_animal":    c2_animal,
        "trig_choice1":      _trig_code(phase, c1_animal, 1) if responded else None,
        "trig_choice2":      _trig_code(phase, c2_animal, 2) if responded else None,
        "rt_choice1":        round(result['rt1'], 4) if responded and result.get('rt1') is not None else None,
        "rt_choice2":        round(result['rt2'], 4) if responded and result.get('rt2') is not None else None,
        "feedback_score":    feedback_score if responded else None,
        "elapsed_time":      round(elapsed_time, 4) if elapsed_time is not None else None,
        "timestamp":         datetime.now().isoformat(timespec='seconds'),
        "win_size":          [int(v) for v in win_size] if win_size is not None else None,
        "slot_coords":       {k: [int(x), int(y)] for k, (x, y) in slot_coords.items()} if slot_coords else None,
        "animal_size_px":    animal_size_px,
    }


def save_trial_metadata(
    subject_id: str,
    block_i: int,
    phase: str,
    domain: str,
    trial_id: int,
    stim_pair_id: str,
    char_order: List[str],
    result: Optional[Dict[str, Any]],
    feedback_score: int = 0,
    elapsed_time: Optional[float] = None,
    session_id: Optional[str] = None,
    neon_recording_id: Optional[str] = None,
    win_size: Optional[tuple] = None,
    slot_coords: Optional[Dict[str, Any]] = None,
    animal_size_px: Optional[int] = None,
) -> tuple:
    """
    Save one trial's behavioral data to JSON.

    Returns
    -------
    (Path, record) — path of the saved JSON and the record dict.
    """
    record = build_trial_record(
        subject_id, block_i, phase, domain, trial_id, stim_pair_id,
        char_order, result, feedback_score, elapsed_time,
        session_id=session_id, neon_recording_id=neon_recording_id,
        win_size=win_size, slot_coords=slot_coords, animal_size_px=animal_size_px,
    )
    save_dir = ensure_trial_save_dir(subject_id, block_i, phase, domain, stim_pair_id)
    out_path = save_dir / "metadata.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return out_path, record


def save_session_metadata(
    subject_id: str,
    session_id: str,
    win_size: tuple,
    slot_info: Optional[Dict[str, Any]] = None,
    neon_recording_id: Optional[str] = None,
) -> Path:
    """Save one-time session-level metadata to data/sub-{subject_id}/session_metadata.json.

    Captures the actual runtime win.size (ground truth for all slot coordinates),
    plus slot positions and animal_size_px so AOI construction needs no code reconstruction.
    """
    from function.config.settings import WINDOW_FULLSCR, MONITOR_NAME, FRAME_RATE, MISSION_MODE
    from function.io.path_builder import get_session_metadata_path

    record: Dict[str, Any] = {
        "subject_id":        subject_id,
        "session_id":        session_id,
        "timestamp":         datetime.now().isoformat(timespec='seconds'),
        "win_width":         int(win_size[0]),
        "win_height":        int(win_size[1]),
        "win_fullscr":       WINDOW_FULLSCR,
        "monitor_name":      MONITOR_NAME,
        "frame_rate":        FRAME_RATE,
        "mission_mode":      MISSION_MODE,
        "neon_recording_id": neon_recording_id,
    }
    if slot_info:
        record["slot_coords"]    = {k: [int(x), int(y)] for k, (x, y) in slot_info['slot_coords'].items()}
        record["animal_size_px"] = slot_info['animal_size_px']

    out_path = get_session_metadata_path(subject_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return out_path
