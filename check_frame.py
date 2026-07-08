"""
check_frame.py
--------------
Detects frame drops in frame_log.csv produced by FrameRecorder.

Frame drop definition
---------------------
A frame drop occurs when the interval between two consecutive flip_times
within the same trial exceeds THRESHOLD * expected_frame_duration.

Usage
-----
    python check_frame.py                              # all subjects combined
    python check_frame.py --sub sub-003               # one subject only
    python check_frame.py --sub sub-003 --save        # save drop_report.csv to data/sub-003/
    python check_frame.py path/to/frame_log.csv       # single explicit file
    python check_frame.py --hz 120                    # override monitor refresh rate
"""

import csv
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


# ─── constants ────────────────────────────────────────────────────────────────

DEFAULT_HZ        = 60        # monitor refresh rate (Hz)
DROP_THRESHOLD    = 1.5       # intervals > threshold * expected_duration → drop
SEVERE_THRESHOLD  = 2.5       # intervals > this → severe drop (skipped ≥2 frames)


# ─── loading ──────────────────────────────────────────────────────────────────

def load_frame_log(csv_path: Path) -> List[Dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        row["frame_idx"]    = int(row["frame_idx"])
        row["trial_id"]     = int(row["trial_id"])
        row["flip_time"]    = float(row["flip_time"])
        row["elapsed_time"] = float(row["elapsed_time"])
        row["global_time"]  = float(row["global_time"])

    return rows


def load_all_frame_logs(paths: List[Path]) -> List[Dict]:
    """Load and concatenate multiple frame_log.csv files."""
    all_rows: List[Dict] = []
    for p in paths:
        all_rows.extend(load_frame_log(p))
    return all_rows


# ─── grouping ─────────────────────────────────────────────────────────────────

def group_by_trial(rows: List[Dict]) -> Dict[Tuple, List[Dict]]:
    """Group rows by (phase, trial_id, stim_pair_id) preserving frame order."""
    groups: Dict[Tuple, List[Dict]] = defaultdict(list)
    for row in rows:
        key = (row["phase"], row["trial_id"], row["stim_pair_id"])
        groups[key].append(row)
    for key in groups:
        groups[key].sort(key=lambda r: r["flip_time"])
    return groups


# ─── detection ────────────────────────────────────────────────────────────────

def detect_drops(
    groups: Dict[Tuple, List[Dict]],
    expected_ms: float,
) -> List[Dict]:
    """
    Returns a list of drop-event dicts, one per detected drop.
    Fields: phase, trial_id, stim_pair_id,
            frame_before, frame_after,
            interval_ms, expected_ms,
            skipped_frames, severity
    """
    drops = []
    for (phase, trial_id, stim_pair_id), frames in groups.items():
        for i in range(1, len(frames)):
            prev = frames[i - 1]
            curr = frames[i]
            # skip segment boundaries (frame_idx resets to 0 at each new segment)
            if curr["frame_idx"] <= prev["frame_idx"] and curr["frame_idx"] == 0:
                continue
            interval_ms = (curr["flip_time"] - prev["flip_time"]) * 1000.0
            if interval_ms > DROP_THRESHOLD * expected_ms:
                skipped = round(interval_ms / expected_ms) - 1
                severity = "SEVERE" if interval_ms > SEVERE_THRESHOLD * expected_ms else "MILD"
                drops.append({
                    "phase":         phase,
                    "trial_id":      trial_id,
                    "stim_pair_id":  stim_pair_id,
                    "frame_before":  prev["frame_idx"],
                    "frame_after":   curr["frame_idx"],
                    "interval_ms":   round(interval_ms, 3),
                    "expected_ms":   round(expected_ms, 3),
                    "skipped_frames": skipped,
                    "severity":      severity,
                    "event_marker":  curr["event_marker"],
                    "elapsed_s":     round(curr["elapsed_time"], 4),
                })
    return drops


# ─── statistics ───────────────────────────────────────────────────────────────

def compute_stats(
    rows: List[Dict],
    groups: Dict[Tuple, List[Dict]],
    drops: List[Dict],
) -> Dict:
    total_frames = len(rows)
    total_trials = len(groups)
    total_drops  = len(drops)
    severe_drops = sum(1 for d in drops if d["severity"] == "SEVERE")

    # per-trial interval statistics (within-segment only, skip segment boundaries)
    all_intervals = []
    for frames in groups.values():
        for i in range(1, len(frames)):
            prev, curr = frames[i - 1], frames[i]
            if curr["frame_idx"] == 0 and prev["frame_idx"] >= 0:
                continue
            ms = (curr["flip_time"] - prev["flip_time"]) * 1000.0
            all_intervals.append(ms)

    if all_intervals:
        mean_ms = sum(all_intervals) / len(all_intervals)
        max_ms  = max(all_intervals)
        min_ms  = min(all_intervals)
        sorted_iv = sorted(all_intervals)
        p99 = sorted_iv[int(len(sorted_iv) * 0.99)]
    else:
        mean_ms = max_ms = min_ms = p99 = 0.0

    # drops per phase
    drops_by_phase: Dict[str, int] = defaultdict(int)
    for d in drops:
        drops_by_phase[d["phase"]] += 1

    # trials with at least one drop
    affected_trials = len({(d["phase"], d["trial_id"], d["stim_pair_id"]) for d in drops})

    return {
        "total_frames":    total_frames,
        "total_trials":    total_trials,
        "total_intervals": len(all_intervals),
        "total_drops":     total_drops,
        "severe_drops":    severe_drops,
        "drop_rate_pct":   round(total_drops / len(all_intervals) * 100, 3) if all_intervals else 0,
        "affected_trials": affected_trials,
        "mean_interval_ms": round(mean_ms, 3),
        "min_interval_ms":  round(min_ms, 3),
        "max_interval_ms":  round(max_ms, 3),
        "p99_interval_ms":  round(p99, 3),
        "drops_by_phase":  dict(drops_by_phase),
    }


# ─── reporting ────────────────────────────────────────────────────────────────

def print_report(stats: Dict, drops: List[Dict], expected_ms: float) -> None:
    SEP = "=" * 65

    print(f"\n{SEP}")
    print("  FRAME DROP REPORT")
    print(SEP)
    print(f"  Expected frame duration : {expected_ms:.3f} ms")
    print(f"  Drop threshold          : > {DROP_THRESHOLD}x  ({DROP_THRESHOLD * expected_ms:.1f} ms)")
    print(f"  Severe threshold        : > {SEVERE_THRESHOLD}x  ({SEVERE_THRESHOLD * expected_ms:.1f} ms)")
    print(SEP)
    print(f"  Total frames logged     : {stats['total_frames']}")
    print(f"  Total within-trial ivs  : {stats['total_intervals']}")
    print(f"  Mean interval           : {stats['mean_interval_ms']} ms")
    print(f"  Min  / Max  interval    : {stats['min_interval_ms']} / {stats['max_interval_ms']} ms")
    print(f"  p99  interval           : {stats['p99_interval_ms']} ms")
    print(SEP)
    print(f"  Frame drops (total)     : {stats['total_drops']}")
    print(f"    ├─ MILD  drops        : {stats['total_drops'] - stats['severe_drops']}")
    print(f"    └─ SEVERE drops       : {stats['severe_drops']}")
    print(f"  Drop rate               : {stats['drop_rate_pct']} %")
    print(f"  Affected trials         : {stats['affected_trials']} / {stats['total_trials']}")

    if stats["drops_by_phase"]:
        print(f"\n  Drops by phase:")
        for phase, count in sorted(stats["drops_by_phase"].items()):
            print(f"    {phase:<30} {count}")

    if drops:
        print(f"\n  {'─'*63}")
        print(f"  {'#':<5} {'Phase':<12} {'Trial':>6} {'Stim':<14} "
              f"{'Frames':>10} {'Interval':>10} {'Skip':>5} {'Sev':<7} {'Marker'}")
        print(f"  {'─'*63}")
        for i, d in enumerate(drops, 1):
            frames_str  = f"{d['frame_before']}→{d['frame_after']}"
            print(
                f"  {i:<5} {d['phase']:<12} {d['trial_id']:>6} {d['stim_pair_id']:<14} "
                f"{frames_str:>10} {d['interval_ms']:>9.1f}ms {d['skipped_frames']:>5} "
                f"{d['severity']:<7} {d['event_marker']}"
            )
    else:
        print(f"\n  No frame drops detected.")

    print(SEP + "\n")


def save_drop_report(drops: List[Dict], out_path: Path) -> None:
    if not drops:
        return
    fieldnames = [
        "phase", "trial_id", "stim_pair_id",
        "frame_before", "frame_after",
        "interval_ms", "expected_ms", "skipped_frames", "severity",
        "elapsed_s", "event_marker",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(drops)
    print(f"  Drop report saved → {out_path}")


# ─── auto-find ────────────────────────────────────────────────────────────────

def find_frame_logs(start: Path) -> List[Path]:
    candidates = sorted(start.rglob("frame_log.csv"))
    if not candidates:
        raise FileNotFoundError(f"No frame_log.csv found under {start}")
    print(f"  [INFO] {len(candidates)} frame_log.csv file(s) found - combining all.")
    return candidates


# ─── entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Check frame drops in frame_log.csv")
    parser.add_argument("csv_path", nargs="?", type=Path,
                        help="Path to a single frame_log.csv (auto-detected if omitted)")
    parser.add_argument("--sub",  type=str, default=None,
                        help="Subject ID to analyse (e.g. sub-003). Searches data/<sub>/")
    parser.add_argument("--hz",  type=float, default=DEFAULT_HZ,
                        help=f"Monitor refresh rate in Hz (default: {DEFAULT_HZ})")
    parser.add_argument("--save", action="store_true",
                        help="Save drop list to drop_report.csv")
    args = parser.parse_args()

    expected_ms = 1000.0 / args.hz

    if args.csv_path:
        print(f"  Loading: {args.csv_path}")
        rows    = load_frame_log(args.csv_path)
        save_dir = args.csv_path.parent
    elif args.sub:
        sub_dir = Path("data") / args.sub
        if not sub_dir.exists():
            raise FileNotFoundError(f"Subject folder not found: {sub_dir}")
        print(f"  Subject : {args.sub}")
        paths   = find_frame_logs(sub_dir)
        rows    = load_all_frame_logs(paths)
        save_dir = sub_dir
    else:
        paths   = find_frame_logs(Path("."))
        rows    = load_all_frame_logs(paths)
        save_dir = Path(".")

    groups = group_by_trial(rows)
    drops  = detect_drops(groups, expected_ms)
    stats  = compute_stats(rows, groups, drops)

    print_report(stats, drops, expected_ms)

    if args.save and drops:
        out_path = save_dir / "drop_report.csv"
        save_drop_report(drops, out_path)


if __name__ == "__main__":
    main()
