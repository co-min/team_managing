"""
Gaze heatmap analysis aligned to trial events.

Trial event windows extracted from individual frame_log.csv files:
  ITI         : iti_onset → DOMAIN_ONSET_onset
  DOMAIN_ONSET: DOMAIN_ONSET_onset → CHOICE1_onset
  CHOICE1     : CHOICE1_onset → CHOICE1_response
  CHOICE2     : CHOICE2_onset → CHOICE2_response
  FEEDBACK    : CHOICE2_response → next trial's iti_onset  (gap not in frame_log)

Alignment:
  gaze timestamp [ns] <-> flip_time [s] via fixed offset derived from sections.csv
"""

import json
import csv
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no GUI window)
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# ── paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(r"../anaysis_sub-006")
SUBJ_DIR  = BASE / "sub-006"
CSV_DIR   = BASE / "sub-006_csv"

# ── screen geometry (from session_metadata.json) ───────────────────────────────
with open(SUBJ_DIR / "session_metadata.json") as f:
    meta = json.load(f)

WIN_W = meta["win_width"]   # 2560
WIN_H = meta["win_height"]  # 1600

# PsychoPy slot coords (origin = screen center, y-up)
SLOTS = meta["slot_coords"]   # {"up":[0,112], "down":[0,-528], "right":[384,-208], "left":[-384,-208]}
ANIMAL_SIZE = meta["animal_size_px"]  # 256

# Convert PsychoPy (x,y) → normalized screen coords (0-1, origin top-left, y-down)
def psychopy_to_norm(px, py):
    nx = (px + WIN_W / 2) / WIN_W
    ny = 1 - (py + WIN_H / 2) / WIN_H
    return nx, ny

SLOT_NORM = {k: psychopy_to_norm(*v) for k, v in SLOTS.items()}
ANIMAL_NORM = ANIMAL_SIZE / WIN_W   # approximate radius in normalized units


# ── Step 1: compute flip_time ↔ gaze_ns offset ────────────────────────────────
def get_flip_offset():
    """
    Derive offset so that:  gaze_s = flip_time + offset
    Uses first section start (ns) and first frame's flip_time.
    """
    sections = pd.read_csv(CSV_DIR / "sections.csv")
    # Keep only the recording that matches neon_recording_id
    rec_id = meta["neon_recording_id"]
    sec = sections[sections["recording id"] == rec_id].sort_values("section start time [ns]")
    first_section_start_s = sec.iloc[0]["section start time [ns]"] / 1e9

    # First flip_time in sub-006's frames.csv
    frames = pd.read_csv(SUBJ_DIR / "frames.csv")
    first_flip = frames["flip_time"].iloc[0]

    offset = first_section_start_s - first_flip
    return offset


# ── Step 2: extract per-trial event windows ────────────────────────────────────
EVENT_SEGMENTS = ["ITI", "DOMAIN_ONSET", "CHOICE1", "CHOICE2", "FEEDBACK"]

def extract_trial_events():
    """
    Walk all per-trial frame_log.csv files and collect flip_time windows
    for each event segment. Returns list of trial dicts.
    """
    trials_csv = pd.read_csv(SUBJ_DIR / "trials.csv")
    # Build stim_pair_id → next trial's iti flip_time (for FEEDBACK end)
    frames_all = pd.read_csv(SUBJ_DIR / "frames.csv")
    iti_rows = frames_all[frames_all["event_marker"].str.startswith("iti_onset", na=False)]
    iti_lookup = dict(zip(iti_rows["stim_pair_id"], iti_rows["flip_time"]))

    trial_events = []

    for _, trial in trials_csv.iterrows():
        pair_id   = trial["stim_pair_id"]
        block     = trial["block"]
        phase     = trial["phase"]
        domain    = trial["domain"]
        tid       = trial["trial_id"]

        # Locate frame_log
        log_path = SUBJ_DIR / block / phase / domain / pair_id / "frame_log.csv"
        if not log_path.exists():
            continue

        log = pd.read_csv(log_path)
        markers = log[log["event_marker"].str.len() > 0] if "event_marker" in log.columns else pd.DataFrame()

        def flip_of(marker):
            row = log[log["event_marker"] == marker]
            return row["flip_time"].values[0] if len(row) else np.nan

        ev = {
            "stim_pair_id" : pair_id,
            "block"        : block,
            "phase"        : phase,
            "domain"       : domain,
            "trial_id"     : tid,
            "global_trial" : trial["global_trial_id"],
            "feedback_score": trial["feedback_score"],
            "layout"       : {d: trial[f"layout_{d}"] for d in ["up","down","right","left"]},
            "choice1_animal": trial["choice1_animal"],
            "choice2_animal": trial["choice2_animal"],
        }

        ev["iti_start"]     = flip_of("iti_onset_dur_" + str(round(
            log[log["event_marker"].str.startswith("iti_onset", na=False)]["elapsed_time"].min(), 3)))
        # simpler: grab first flip in file
        ev["iti_start"]     = log["flip_time"].iloc[0]
        ev["domain_start"]  = flip_of("DOMAIN_ONSET_onset")
        ev["choice1_start"] = flip_of("CHOICE1_onset")
        ev["choice1_end"]   = flip_of("CHOICE1_response")
        ev["choice2_start"] = flip_of("CHOICE2_onset")
        ev["choice2_end"]   = flip_of("CHOICE2_response")  # feedback starts here
        ev["feedback_start"]= ev["choice2_end"]

        # feedback ends at next trial's ITI (from merged frames.csv)
        # find next trial's pair_id
        next_row = trials_csv[trials_csv["global_trial_id"] == trial["global_trial_id"] + 1]
        if len(next_row):
            next_pair = next_row.iloc[0]["stim_pair_id"]
            next_block = next_row.iloc[0]["block"]
            next_phase = next_row.iloc[0]["phase"]
            next_domain = next_row.iloc[0]["domain"]
            next_log_path = SUBJ_DIR / next_block / next_phase / next_domain / next_pair / "frame_log.csv"
            if next_log_path.exists():
                nlog = pd.read_csv(next_log_path)
                ev["feedback_end"] = nlog["flip_time"].iloc[0]
            else:
                ev["feedback_end"] = np.nan
        else:
            ev["feedback_end"] = np.nan

        trial_events.append(ev)

    return trial_events


# ── Step 3: load gaze data and assign to events ────────────────────────────────
def load_gaze(offset):
    """
    Load gaze.csv, convert timestamp to flip_time scale,
    filter to valid gaze on surface.
    """
    gaze = pd.read_csv(CSV_DIR / "gaze.csv")
    gaze = gaze[gaze["gaze detected on surface"] == True].copy()
    gaze["flip_time"] = gaze["timestamp [ns]"] / 1e9 - offset
    gaze["x_norm"]   = gaze["gaze position on surface x [normalized]"]
    gaze["y_norm"]   = gaze["gaze position on surface y [normalized]"]
    return gaze[["flip_time", "x_norm", "y_norm", "fixation id"]].reset_index(drop=True)


def get_gaze_window(gaze, t_start, t_end):
    """Return gaze rows within [t_start, t_end] flip_time."""
    if np.isnan(t_start) or np.isnan(t_end):
        return gaze.iloc[0:0]
    return gaze[(gaze["flip_time"] >= t_start) & (gaze["flip_time"] < t_end)]


# ── Step 4: heatmap plotting ───────────────────────────────────────────────────
def draw_heatmap(ax, xs, ys, title, resolution=200, bandwidth=0.02):
    """KDE-based heatmap on normalized screen coordinates."""
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)  # y-axis flipped (origin top-left)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)

    if len(xs) < 5:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        return

    # Draw slot regions
    for slot, (nx, ny) in SLOT_NORM.items():
        r = ANIMAL_NORM / 2
        rect = plt.Rectangle((nx - r, ny - r), 2*r, 2*r,
                              fill=False, edgecolor="gray", linestyle="--", linewidth=0.8)
        ax.add_patch(rect)
        ax.text(nx, ny, slot, ha="center", va="center", fontsize=7, color="gray")

    # KDE heatmap
    xg = np.linspace(0, 1, resolution)
    yg = np.linspace(0, 1, resolution)
    xx, yy = np.meshgrid(xg, yg)
    positions = np.vstack([xx.ravel(), yy.ravel()])
    values    = np.vstack([np.clip(xs, 0, 1), np.clip(ys, 0, 1)])
    try:
        kde = gaussian_kde(values, bw_method=bandwidth)
        zz  = kde(positions).reshape(resolution, resolution)
        ax.imshow(zz, extent=[0, 1, 1, 0], origin="upper",
                  cmap="hot", alpha=0.75, aspect="auto")
    except Exception:
        ax.scatter(xs, ys, s=1, alpha=0.3, color="red")


def plot_event_heatmaps(trial_events, gaze,
                        filter_by=None,   # e.g. {"domain": "cooking"}
                        segments=None):   # list from EVENT_SEGMENTS
    """
    Generate one figure with one column per event segment.
    Aggregates gaze across all matching trials.
    """
    if segments is None:
        segments = ["CHOICE1", "CHOICE2", "FEEDBACK"]

    seg_gaze = {s: {"x": [], "y": []} for s in segments}

    for ev in trial_events:
        if filter_by:
            if not all(ev.get(k) == v for k, v in filter_by.items()):
                continue

        windows = {
            "ITI"         : (ev["iti_start"],      ev.get("domain_start",  np.nan)),
            "DOMAIN_ONSET": (ev["domain_start"],   ev.get("choice1_start", np.nan)),
            "CHOICE1"     : (ev["choice1_start"],  ev["choice1_end"]),
            "CHOICE2"     : (ev["choice2_start"],  ev["choice2_end"]),
            "FEEDBACK"    : (ev["feedback_start"], ev.get("feedback_end",  np.nan)),
        }

        for seg in segments:
            t0, t1 = windows[seg]
            g = get_gaze_window(gaze, t0, t1)
            seg_gaze[seg]["x"].extend(g["x_norm"].tolist())
            seg_gaze[seg]["y"].extend(g["y_norm"].tolist())

    title_prefix = str(filter_by) if filter_by else "all trials"
    fig, axes = plt.subplots(1, len(segments), figsize=(5 * len(segments), 5))
    if len(segments) == 1:
        axes = [axes]

    for ax, seg in zip(axes, segments):
        xs = np.array(seg_gaze[seg]["x"])
        ys = np.array(seg_gaze[seg]["y"])
        n  = len(xs)
        draw_heatmap(ax, xs, ys, title=f"{seg}\n(n={n} gaze pts)", bandwidth=0.025)

    fig.suptitle(f"Gaze heatmap — {title_prefix}", fontsize=12)
    plt.tight_layout()
    return fig


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Computing flip_time offset...")
    offset = get_flip_offset()
    print(f"  offset = {offset:.3f} s")

    print("Extracting trial events...")
    trial_events = extract_trial_events()
    print(f"  {len(trial_events)} trials loaded")

    print("Loading gaze data...")
    gaze = load_gaze(offset)
    print(f"  {len(gaze)} valid gaze samples")

    # ── Figure 1: all trials, CHOICE1 / CHOICE2 / FEEDBACK ────────────────────
    fig1 = plot_event_heatmaps(trial_events, gaze,
                               segments=["CHOICE1", "CHOICE2", "FEEDBACK"])
    fig1.savefig("heatmap_all_trials.png", dpi=150, bbox_inches="tight")
    plt.close(fig1)

    # ── Figure 2: by domain ────────────────────────────────────────────────────
    for domain in ["cooking", "repairing", "tennis"]:
        fig = plot_event_heatmaps(trial_events, gaze,
                                  filter_by={"domain": domain},
                                  segments=["CHOICE1", "CHOICE2", "FEEDBACK"])
        fig.savefig(f"heatmap_{domain}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    print("Done. Figures saved.")
