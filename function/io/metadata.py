"""
metadata.py
-----------
Per-trial behavioral metadata saver.

Saves JSON to:
  data/sub-{subject_id}/{domain}/{phase}/{stim_pair_id}/metadata.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from function.io.path_builder import ensure_trial_save_dir

_CODE_TO_ANIMAL: Dict[str, str] = {
    'A': 'duck', 'B': 'frog', 'C': 'panda', 'D': 'rabbit'
}
_SLOT_NAMES: List[str] = ['up', 'down', 'right', 'left']


def build_trial_record(
    subject_id: str,
    phase: str,
    domain: str,
    trial_id: int,
    stim_pair_id: str,
    char_order: List[str],
    result: Optional[Dict[str, Any]],
    feedback_score: int = 0,
) -> Dict[str, Any]:
    """Build and return the trial metadata dict (does not write to disk)."""
    layout = {slot: animal for slot, animal in zip(_SLOT_NAMES, char_order)}
    responded = result is not None
    c1 = result['choice1'] if responded else None
    c2 = result['choice2'] if responded else None
    return {
        "subject_id":     subject_id,
        "phase":          phase,
        "domain":         domain,
        "trial_id":       trial_id,
        "stim_pair_id":   stim_pair_id,
        "trial_layout":   layout,
        "response_made":  responded,
        "choice1_code":   c1,
        "choice2_code":   c2,
        "choice1_animal": _CODE_TO_ANIMAL.get(c1) if c1 else None,
        "choice2_animal": _CODE_TO_ANIMAL.get(c2) if c2 else None,
        "rt_choice1":     round(result['rt1'], 4) if responded and result.get('rt1') is not None else None,
        "rt_choice2":     round(result['rt2'], 4) if responded and result.get('rt2') is not None else None,
        "feedback_score": feedback_score if responded else None,
        "timestamp":      datetime.now().isoformat(timespec='seconds'),
    }


def save_trial_metadata(
    subject_id: str,
    phase: str,
    domain: str,
    trial_id: int,
    stim_pair_id: str,
    char_order: List[str],
    result: Optional[Dict[str, Any]],
    feedback_score: int = 0,
) -> tuple:
    """
    Save one trial's behavioral data to JSON.

    Returns
    -------
    (Path, record) — path of the saved JSON and the record dict.
    """
    record = build_trial_record(
        subject_id, phase, domain, trial_id, stim_pair_id,
        char_order, result, feedback_score,
    )
    save_dir = ensure_trial_save_dir(subject_id, phase, domain, stim_pair_id)
    out_path = save_dir / "metadata.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return out_path, record
