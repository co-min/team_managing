"""
frame_saver.py
--------------
Writes accumulated frame-log rows to a CSV file.
Does NOT compute save paths itself – receives save_dir from caller.
"""

import csv
from pathlib import Path
from typing import List, Dict


FRAME_LOG_FILENAME = "frame_log.csv"

FIELDNAMES = [
    "frame_idx",
    "phase",
    "trial_id",
    "stim_pair_id",
    "elapsed_time",
    "global_time",
    "flip_time",
    "event_marker",
]


def save_frame_log(rows: List[Dict], save_dir: Path) -> Path:
    """
    Write *rows* to  save_dir / frame_log.csv.

    Parameters
    ----------
    rows     : list of frame dicts from FrameLogger.get_rows()
    save_dir : directory that already exists (caller must create it)
    
    Returns
    -------
    Path  – full path of the written file
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / FRAME_LOG_FILENAME


    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return out_path
