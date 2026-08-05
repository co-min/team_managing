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
    trials.csv   ← one row per trial (all blocks/phases/domains)
    frames.csv   ← one row per frame (all blocks/phases/domains)
"""

import csv
from pathlib import Path
from typing import Any, Dict, List

_BASE = Path("data")

# trial_layout is a nested dict in the JSON record; flatten it here.
_TRIAL_FIELDS = [
    "subject_id", "global_trial_id", "block_trial_id",
    "block", "phase", "domain", "trial_id", "stim_pair_id",
    "layout_up", "layout_down", "layout_right", "layout_left",
    "pos_up_x",    "pos_up_y",
    "pos_down_x",  "pos_down_y",
    "pos_right_x", "pos_right_y",
    "pos_left_x",  "pos_left_y",
    "animal_size_px",
    "win_width", "win_height",
    "response_made",
    "choice1_code", "choice2_code", "choice1_animal", "choice2_animal",
    "trig_choice1", "trig_choice2",
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

    global_trial_id = 0
    block_trial_id = 0
    current_block = record.get("block")
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                global_trial_id += 1
                if row.get("block") == current_block:
                    block_trial_id += 1

    layout      = record.get("trial_layout", {})
    slot_coords = record.get("slot_coords") or {}
    win_size_raw = record.get("win_size")

    flat = {k: v for k, v in record.items() if k not in ("trial_layout", "slot_coords", "win_size")}
    flat["global_trial_id"] = global_trial_id
    flat["block_trial_id"]  = block_trial_id
    flat["layout_up"]    = layout.get("up")
    flat["layout_down"]  = layout.get("down")
    flat["layout_right"] = layout.get("right")
    flat["layout_left"]  = layout.get("left")

    if win_size_raw:
        flat["win_width"]  = win_size_raw[0]
        flat["win_height"] = win_size_raw[1]
    for slot in ('up', 'down', 'right', 'left'):
        pos = slot_coords.get(slot)
        flat[f"pos_{slot}_x"] = pos[0] if pos is not None else None
        flat[f"pos_{slot}_y"] = pos[1] if pos is not None else None

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
