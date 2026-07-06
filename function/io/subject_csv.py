"""
subject_csv.py
--------------
Subject-level consolidated CSV writers.

Per-trial JSON files cover crash recovery; these CSVs cover analysis convenience.
Every trial appends one row — no need to glob dozens of files in pandas.

Output layout
-------------
data/
  sub-{id}/
    trials.csv   ← one row per trial (all phases/domains)
    frames.csv   ← one row per frame (all phases/domains)
"""

import csv
from pathlib import Path
from typing import Any, Dict, List

_BASE = Path("data")

# trial_layout is a nested dict in the JSON record; flatten it here.
_TRIAL_FIELDS = [
    "subject_id", "global_trial_id", "phase", "domain", "trial_id", "stim_pair_id",
    "layout_up", "layout_down", "layout_right", "layout_left",
    "response_made",
    "choice1_code", "choice2_code", "choice1_animal", "choice2_animal",
    "rt_choice1", "rt_choice2", "feedback_score", "elapsed_time", "timestamp",
]

_FRAME_FIELDS = [
    "subject_id",
    "frame_idx", "phase", "trial_id", "stim_pair_id",
    "elapsed_time", "global_time", "flip_time", "event_marker",
]


def _subject_dir(subject_id: str) -> Path:
    d = _BASE / f"sub-{subject_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_trial_row(subject_id: str, record: Dict[str, Any]) -> None:
    """Append one trial's metadata to data/sub-{id}/trials.csv."""
    csv_path = _subject_dir(subject_id) / "trials.csv"
    write_header = not csv_path.exists()

    # Count existing rows to assign a sequential global_trial_id
    global_trial_id = 0
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            global_trial_id = sum(1 for _ in f) - 1  # subtract header row

    layout = record.get("trial_layout", {})
    flat = {k: v for k, v in record.items() if k != "trial_layout"}
    flat["global_trial_id"] = global_trial_id
    flat["layout_up"]    = layout.get("up")
    flat["layout_down"]  = layout.get("down")
    flat["layout_right"] = layout.get("right")
    flat["layout_left"]  = layout.get("left")

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_TRIAL_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(flat)


def append_frame_rows(subject_id: str, rows: List[Dict[str, Any]]) -> None:
    """Append frame-log rows (from get_rows()) to data/sub-{id}/frames.csv."""
    if not rows:
        return
    csv_path = _subject_dir(subject_id) / "frames.csv"
    write_header = not csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FRAME_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({"subject_id": subject_id, **row})
