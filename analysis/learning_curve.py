"""
Group-level learning curve (n=3, sub-010 excluded as floor performer),
split by phase.

phase_1 = blocks 0, 2, 4  (same task structure, animal SET changes each block)
phase_2 = blocks 1, 3, 5

x-axis : phase-relative cumulative trial (cumulative trial count computed
         WITHIN each phase only, so both phase curves start at trial 1 and are
         directly comparable in terms of within-condition learning rate).
y-axis : accuracy (is_optimal), smoothed with a rolling mean per subject,
         then averaged across subjects (with SEM band).

Block boundaries (where the animal set switches, within a phase) are marked
with vertical dashed lines.
"""
import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent / "group_learning_curve_phase1_vs_phase2_n3.png"
ROLL_WINDOW = 5  # trials, per-subject smoothing before averaging across subjects
EXCLUDE_SUBJECTS = {}  # floor performer (near-chance throughout) -> excluded

# ---- 1. load & concatenate subjects (excluding floor performer) ----------
files = sorted(glob.glob(str(DATA_DIR / "sub-*" / "trials.csv")))

dfs = []
for f in files:
    d = pd.read_csv(f)
    d["subject_id"] = d["subject_id"].astype(str).str.zfill(3)
    if d["subject_id"].iloc[0] in EXCLUDE_SUBJECTS:
        continue
    dfs.append(d)
df = pd.concat(dfs, ignore_index=True)
df["is_optimal"] = df["is_optimal"].astype(bool).astype(int)

# ---- 2. phase-relative cumulative trial index -----------------------------
# global_trial_id already reflects chronological order within a subject, so
# sorting by it within (subject, phase) and ranking 1..N reproduces the
# block-concatenation order (block_0 -> block_2 -> block_4 for phase_1, etc.)
df = df.sort_values(["subject_id", "phase", "global_trial_id"])
df["phase_trial"] = df.groupby(["subject_id", "phase"]).cumcount() + 1

# block boundaries within each phase (for vertical reference lines)
boundaries = {}
block_orders = {}
for phase, g in df[df.subject_id == df.subject_id.iloc[0]].groupby("phase"):
    block_sizes = g.groupby("block", sort=False)["phase_trial"].count()
    block_order = list(g.drop_duplicates("block")["block"])
    sizes_in_order = [block_sizes[b] for b in block_order]
    cum = np.cumsum(sizes_in_order)[:-1]  # boundary AFTER each block except last
    boundaries[phase] = cum
    block_orders[phase] = block_order

# ---- 3. per-subject rolling accuracy, then average across subjects --------
def smoothed_curve(sub_df):
    sub_df = sub_df.sort_values("phase_trial")
    return sub_df.set_index("phase_trial")["is_optimal"].rolling(
        ROLL_WINDOW, min_periods=1
    ).mean()

curves = {}  # phase -> DataFrame (rows=phase_trial, cols=subject_id)
for phase, g in df.groupby("phase"):
    per_subj = {}
    for sid, sg in g.groupby("subject_id"):
        per_subj[sid] = smoothed_curve(sg)
    curves[phase] = pd.DataFrame(per_subj)

# ---- 4. plot ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.5))

colors = {"phase_1": "#1f77b4", "phase_2": "#ff7f0e"}
labels = {"phase_1": "Phase 1 (blocks 0,2,4)", "phase_2": "Phase 2 (blocks 1,3,5)"}

for phase in ["phase_1", "phase_2"]:
    mat = curves[phase]
    mean = mat.mean(axis=1)
    sem = mat.std(axis=1, ddof=1) / np.sqrt(mat.shape[1])
    x = mean.index.values

    for col in mat.columns:
        ax.plot(x, mat[col], color=colors[phase], alpha=0.2, linewidth=1)

    ax.plot(x, mean, color=colors[phase], linewidth=2.5, label=labels[phase])
    ax.fill_between(x, mean - sem, mean + sem, color=colors[phase], alpha=0.2)

    blk_order = block_orders[phase]
    n_trials = curves[phase].shape[0]
    bounds_ext = [1] + [int(b) + 1 for b in boundaries[phase]] + [n_trials]
    trans = ax.get_xaxis_transform()  # x=data coords, y=axes fraction
    y_label = 1.12 if phase == "phase_1" else 1.04

    for i, blk in enumerate(blk_order):
        mid = (bounds_ext[i] + bounds_ext[i + 1]) / 2
        ax.text(mid, y_label, f"{blk}", ha="center", va="bottom",
                fontsize=15, color=colors[phase], fontweight="bold",
                transform=trans, clip_on=False)

    for b in boundaries[phase]:
        ax.axvline(b + 0.5, color=colors[phase], linestyle="--", linewidth=1.5, alpha=0.8)

ax.set_xlabel("Cumulative trial (within phase)", fontsize=18, bold=True)
ax.set_ylabel("Accuracy", fontsize=18, bold=True)
ax.set_ylim(0, 1.05)
ax.tick_params(axis='both', labelsize=15)
excl_note = f", sub-{'/'.join(sorted(EXCLUDE_SUBJECTS))} excluded" if EXCLUDE_SUBJECTS else ""
fig.suptitle(f"Group learning curve — Phase 1 vs Phase 2 (n={df.subject_id.nunique()})",
             fontsize=21, y=0.97, fontweight="bold")
ax.legend(loc="lower right", fontsize=14)
ax.grid(alpha=0.3)
fig.subplots_adjust(left=0.10, right=0.97, bottom=0.11, top=0.79)
fig.savefig(OUT_PATH, dpi=150)
print("saved:", OUT_PATH)
print("n subjects:", df.subject_id.nunique(), sorted(df.subject_id.unique()))
print("phase_1 trials/phase:", curves["phase_1"].shape[0], " phase_2 trials/phase:", curves["phase_2"].shape[0])
print("block boundaries:", {k: list(v) for k, v in boundaries.items()})