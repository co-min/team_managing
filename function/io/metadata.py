"""
metadata.py
-----------
Per-trial behavioral metadata saver.

Saves JSON to:
  data/sub-{subject_id}/block_{block_i}/{phase}/{domain}/{stim_pair_id}/metadata.json
"""

import json
from datetime import datetime
from itertools import combinations
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


def _compute_optimal(char_order: List[str], domain: str, score_data: dict):
    """Return (optimal_score, optimal_key) for the highest-scoring pair among char_order."""
    best_score, best_key = None, None
    for a1, a2 in combinations(char_order, 2):
        key = tuple(sorted([_CHAR_CODE[a1], _CHAR_CODE[a2]]))
        sc = score_data.get(key, {}).get(domain, 0)
        if best_score is None or sc > best_score:
            best_score, best_key = sc, key
    return best_score, best_key

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
    score_data: Optional[dict] = None,
) -> Dict[str, Any]:
    """Build and return the trial metadata dict (does not write to disk)."""
    layout = {slot: animal for slot, animal in zip(_SLOT_NAMES, char_order)}
    code_to_animal = {_CHAR_CODE[animal]: animal for animal in char_order}
    responded = result is not None
    c1 = result['choice1'] if responded else None
    c2 = result['choice2'] if responded else None
    c1_animal = code_to_animal.get(c1) if c1 else None
    c2_animal = code_to_animal.get(c2) if c2 else None

    if score_data is not None and responded and c1 and c2:
        optimal_score, optimal_key = _compute_optimal(char_order, domain, score_data)
        is_optimal = tuple(sorted([c1, c2])) == optimal_key
    else:
        optimal_score = None
        is_optimal = None

    return {
        "subject_id":     subject_id,
        "block":          f"block_{block_i}",
        "phase":          phase,
        "domain":         domain,
        "trial_id":       trial_id,
        "stim_pair_id":   stim_pair_id,
        "trial_layout":   layout,
        "response_made":  responded,
        "choice1_code":   c1,
        "choice2_code":   c2,
        "choice1_animal": c1_animal,
        "choice2_animal": c2_animal,
        "trig_choice1":   _trig_code(phase, c1_animal, 1) if responded else None,
        "trig_choice2":   _trig_code(phase, c2_animal, 2) if responded else None,
        "rt_choice1":     round(result['rt1'], 4) if responded and result.get('rt1') is not None else None,
        "rt_choice2":     round(result['rt2'], 4) if responded and result.get('rt2') is not None else None,
        "feedback_score": feedback_score if responded else None,
        "optimal_score":  optimal_score,
        "is_optimal":     is_optimal,
        "elapsed_time":   round(elapsed_time, 4) if elapsed_time is not None else None,
        "timestamp":      datetime.now().isoformat(timespec='seconds'),
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
    score_data: Optional[dict] = None,
) -> tuple:
    """
    Save one trial's behavioral data to JSON.

    Returns
    -------
    (Path, record) — path of the saved JSON and the record dict.
    """
    record = build_trial_record(
        subject_id, block_i, phase, domain, trial_id, stim_pair_id,
        char_order, result, feedback_score, elapsed_time, score_data,
    )
    save_dir = ensure_trial_save_dir(subject_id, block_i, phase, domain, stim_pair_id)
    out_path = save_dir / "metadata.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return out_path, record
