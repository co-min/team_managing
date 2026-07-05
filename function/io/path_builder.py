"""
path_builder.py
---------------
Single source of truth for all result-directory paths.

Directory schema
----------------
data/
  sub-{subject_id}/
    phase_0/
      {char_id}/
        frame_log.csv
    {domain}/
      phase_1/
        {stim_pair_id}/
          frame_log.csv
          metadata.json
      phase_2/
        {stim_pair_id}/
          frame_log.csv
          metadata.json
      phase_3/
        {stim_pair_id}/
          frame_log.csv
          metadata.json
"""

from pathlib import Path
from function.config.settings import DATA_DIR


# ── Phase folder names ────────────────────────────────────────────────────────
PHASE_DIR_NAMES = {
    "phase_0": "phase_0",
    "phase_1": "phase_1",
    "phase_2": "phase_2",
    "phase_3": "phase_3",
}


def get_subject_dir(subject_id: str) -> Path:
    """Return  data/sub-{subject_id}/"""
    return DATA_DIR / f"sub-{subject_id}"


def build_trial_save_dir(
    subject_id: str,
    phase: str,
    domain: str,
    stim_pair_id: str,
) -> Path:
    """
    Construct (but do not create) the save directory for one trial/phase.

    Parameters
    ----------
    subject_id   : e.g. "001"
    phase        : one of "phase_1", "phase_2", "phase_3"
    domain       : one of "cooking", "repairing", "tennis"
    stim_pair_id : e.g. "pair_001"

    Returns
    -------
    Path  e.g. data/sub-001/cooking/phase_1/pair_001/
    """
    phase_dir = PHASE_DIR_NAMES.get(phase, phase)
    return get_subject_dir(subject_id) / domain / phase_dir / stim_pair_id


def ensure_trial_save_dir(
    subject_id: str,
    phase: str,
    domain: str,
    stim_pair_id: str,
) -> Path:
    """Same as build_trial_save_dir but also creates the directory."""
    p = build_trial_save_dir(subject_id, phase, domain, stim_pair_id)
    p.mkdir(parents=True, exist_ok=True)
    return p
