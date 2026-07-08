"""
summary.py
----------
Experiment-level summary JSON writer.

Reads data/sub-{id}/trials.csv and produces:
  data/sub-{id}/summary.json

Experiment structure assumed
----------------------------
6 blocks run sequentially.  Blocks alternate phase_1 / phase_2.
Each block contains 18 trials spread evenly across 3 domains (6 per domain).
Each block uses a dedicated animal group (4 animals).

  block_0 → phase_1,  block_1 → phase_2,  block_2 → phase_1 ...

Output structure
----------------
{
  "subject_id": "001",
  "generated_at": "...",
  "overall": { total_trials, responded_trials, response_rate,
               mean_rt1, mean_rt2, mean_feedback_score, total_score },
  "by_block": {
    "block_0": {
      "phase": "phase_1",
      "domain_order": ["cooking", "repairing", "tennis"],
      "total_trials": 18,
      ...same stats...
    },
    ...
  },
  "by_phase": {
    "phase_1": { total_trials: 54, ... },   ← aggregated across all phase_1 blocks
    "phase_2": { ... }
  },
  "by_domain": {
    "cooking": { total_trials: 36, ... }    ← aggregated across all blocks
  },
  "by_block_domain": {
    "block_0": {
      "cooking":   { total_trials: 6, ... },
      "repairing": { ... },
      "tennis":    { ... }
    },
    ...
  }
}
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from function.io.path_builder import get_subject_dir


# ── helpers ──────────────────────────────────────────────────────────────────

def _read_trials(subject_id: str) -> List[Dict[str, Any]]:
    csv_path = get_subject_dir(subject_id) / "trials.csv"
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _safe_mean(values: List[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for an arbitrary subset of trial rows."""
    total = len(rows)
    responded = [
        r for r in rows
        if r.get("response_made") in ("True", True, "1", 1)
    ]
    n = len(responded)
    feedback_scores = [_to_float(r.get("feedback_score")) for r in responded]
    clean_scores = [v for v in feedback_scores if v is not None]
    return {
        "total_trials":        total,
        "responded_trials":    n,
        "response_rate":       round(n / total, 4) if total > 0 else None,
        "mean_rt1":            _safe_mean([_to_float(r.get("rt_choice1"))  for r in responded]),
        "mean_rt2":            _safe_mean([_to_float(r.get("rt_choice2"))  for r in responded]),
        "total_score":         round(sum(clean_scores), 4) if clean_scores else None,
        "mean_feedback_score": _safe_mean(feedback_scores),
    }


# ── public API ────────────────────────────────────────────────────────────────

def build_experiment_summary(subject_id: str) -> Dict[str, Any]:
    """
    Build the full summary dict from data/sub-{id}/trials.csv.

    Preserves the encounter order of blocks, phases, and domains so that
    'domain_order' reflects the actual run sequence.
    """
    rows = _read_trials(subject_id)

    # Preserve first-seen ordering for blocks, phases, and domains
    blocks_seen: List[str] = []
    for r in rows:
        b = r.get("block", "")
        if b and b not in blocks_seen:
            blocks_seen.append(b)

    phases_seen: List[str] = []
    for r in rows:
        p = r.get("phase", "")
        if p and p not in phases_seen:
            phases_seen.append(p)

    domains_seen: List[str] = []
    for r in rows:
        d = r.get("domain", "")
        if d and d not in domains_seen:
            domains_seen.append(d)

    # Phase and domain run-order within each block
    block_phase: Dict[str, str] = {}
    block_domain_order: Dict[str, List[str]] = {}
    for r in rows:
        b, p, d = r.get("block", ""), r.get("phase", ""), r.get("domain", "")
        if b and p:
            block_phase.setdefault(b, p)
        if b and d:
            order = block_domain_order.setdefault(b, [])
            if d not in order:
                order.append(d)

    # by_block
    by_block: Dict[str, Any] = {}
    for block in blocks_seen:
        block_rows = [r for r in rows if r.get("block") == block]
        stats = _aggregate(block_rows)
        stats["phase"]        = block_phase.get(block, "")
        stats["domain_order"] = block_domain_order.get(block, [])
        by_block[block] = stats

    # by_phase (aggregated across ALL blocks of the same phase)
    by_phase: Dict[str, Any] = {
        phase: _aggregate([r for r in rows if r.get("phase") == phase])
        for phase in phases_seen
    }

    # by_domain (aggregated across ALL blocks)
    by_domain: Dict[str, Any] = {
        domain: _aggregate([r for r in rows if r.get("domain") == domain])
        for domain in domains_seen
    }

    # by_block_domain (finest grain: one cell per block × domain)
    by_block_domain: Dict[str, Dict[str, Any]] = {}
    for block in blocks_seen:
        by_block_domain[block] = {
            domain: _aggregate([
                r for r in rows
                if r.get("block") == block and r.get("domain") == domain
            ])
            for domain in block_domain_order.get(block, [])
        }

    return {
        "subject_id":      subject_id,
        "generated_at":    datetime.now().isoformat(timespec="seconds"),
        "overall":         _aggregate(rows),
        "by_block":        by_block,
        "by_phase":        by_phase,
        "by_domain":       by_domain,
        "by_block_domain": by_block_domain,
    }


def save_experiment_summary(subject_id: str) -> Path:
    """
    Build and write data/sub-{id}/summary.json.

    Call this at the end of each block or at experiment completion.
    The file is overwritten each time so it always reflects the
    latest completed trials.

    Returns the saved path.
    """
    summary = build_experiment_summary(subject_id)
    out_path = get_subject_dir(subject_id) / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return out_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m function.io.summary <subject_id> [subject_id ...]")
        print("Example: python -m function.io.summary 003 004")
        sys.exit(1)

    for sid in sys.argv[1:]:
        path = save_experiment_summary(sid)
        print(f"[OK] sub-{sid} → {path}")
