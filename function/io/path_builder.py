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
    phase_1/
      domain_1/
        {stim_pair_id}/
          metadata.json
          frame_log.csv
      domain_2/
        {stim_pair_id}/
          metadata.json
          frame_log.csv
      domain_3/
        {stim_pair_id}/
          metadata.json
          frame_log.csv
    phase_2/
      domain_1/ ...
    phase_3/
      domain_1/ ...
"""

from pathlib import Path
from function.config.settings import DATA_DIR


# ── Phase folder names ────────────────────────────────────────────────────────
PHASE_DIR_NAMES = {
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
    domain       : one of "domain_1", "domain_2", "domain_3"
    stim_pair_id : e.g. "pair_001"

    Returns
    -------
    Path  e.g. data/sub-001/phase_1/domain_1/pair_001/
    """
    phase_dir = PHASE_DIR_NAMES.get(phase, phase)
    return get_subject_dir(subject_id) / phase_dir / domain / stim_pair_id


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
