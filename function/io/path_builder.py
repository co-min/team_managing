"""
path_builder.py
---------------
Single source of truth for all result-directory paths.

Directory schema
----------------
data/
  sub-{subject_id}/
    trials.csv
    frames.csv
    summary.json
    block_{block_i}/
      {phase}/
        {domain}/
          {stim_pair_id}/
            metadata.json
            frame_log.csv
"""

from pathlib import Path
from function.config.settings import DATA_DIR


def get_subject_dir(subject_id: str) -> Path:
    """Return  data/sub-{subject_id}/"""
    return DATA_DIR / f"sub-{subject_id}"


def build_trial_save_dir(
    subject_id: str,
    block_i: int,
    phase: str,
    domain: str,
    stim_pair_id: str,
) -> Path:
    """
    Construct (but do not create) the save directory for one trial.

    Parameters
    ----------
    subject_id   : e.g. "001"
    block_i      : 0-indexed block number (0–5)
    phase        : one of "phase_1", "phase_2"
    domain       : one of "cooking", "repairing", "tennis"
    stim_pair_id : e.g. "block0_phase_1_t00"

    Returns
    -------
    Path  e.g. data/sub-001/block_0/phase_1/cooking/block0_phase_1_t00/
    """
    return get_subject_dir(subject_id) / f"block_{block_i}" / phase / domain / stim_pair_id


def ensure_trial_save_dir(
    subject_id: str,
    block_i: int,
    phase: str,
    domain: str,
    stim_pair_id: str,
) -> Path:
    """Same as build_trial_save_dir but also creates the directory."""
    p = build_trial_save_dir(subject_id, block_i, phase, domain, stim_pair_id)
    p.mkdir(parents=True, exist_ok=True)
    return p
