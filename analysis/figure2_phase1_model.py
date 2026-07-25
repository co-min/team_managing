"""
figure2_phase1_model.py
=======================
Figure 2A – Phase 1 learning curve: probability of choosing a high-synergy
pair across Early / Middle / Late trial bins, separately for Block 0, 2, 4.

Goal: examine whether participants learn the hidden synergy structure over the
course of Phase 1, as evidenced by an increasing probability of selecting
high-synergy pairs as trials progress within each block.

Output files (saved to the same folder as this script):
  figure2A_phase1_learning_curve.png / .svg
  figure2A_phase1_individual_trajectories.png / .svg
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# Edit this section if your dataset uses different column names, file paths,
# or analysis parameters. Everything downstream reads from these constants.
# ═══════════════════════════════════════════════════════════════════════════

# ── Column names in the raw trials.csv files ─────────────────────────────────
# Adjust these strings to match whatever headers appear in your data.
COL_SUBJECT   = "subject_id"      # participant identifier
COL_PHASE     = "phase"           # phase label  (e.g. "phase_1")
COL_BLOCK     = "block"           # block label  (e.g. "block_0")
COL_TRIAL_IDX = "block_trial_id"  # 0-based trial index within the block (0–17)
COL_DOMAIN    = "domain"          # task domain  (cooking / repairing / tennis)
COL_ROLE1     = "choice1_code"    # role letter of the first animal chosen  (A–D)
COL_ROLE2     = "choice2_code"    # role letter of the second animal chosen (A–D)

# NOTE — expected columns that are ABSENT from the raw data:
#   • chosen_pair   : not pre-stored; constructed here from COL_ROLE1 + COL_ROLE2.
#   • synergy_level : not stored in trials.csv; derived from the synergy lookup
#                     table (see SYNERGY_TABLE path below).
#                     If your data already has a synergy-label column (e.g. "High",
#                     "Medium", "Low"), set COL_SYNERGY_LEVEL to that column name;
#                     otherwise leave it as None.
COL_SYNERGY_LEVEL = None  # e.g. "synergy_level", or None to compute from roles

# ── Phase 1 specification ────────────────────────────────────────────────────
PHASE_1_LABEL  = "phase_1"
PHASE_1_BLOCKS = ["block_0", "block_2", "block_4"]   # block labels for Phase 1

# ── Trial binning (uses 0-based block_trial_id values) ──────────────────────
# Each Phase 1 block has 18 trials (indices 0–17).
#   Trials  1– 6  → index  0– 5  → Early
#   Trials  7–12  → index  6–11  → Middle
#   Trials 13–18  → index 12–17  → Late
BIN_EDGES  = [0, 6, 12, 18]             # left-inclusive, right-exclusive cut points
BIN_LABELS = ["Early", "Middle", "Late"]

# ── High-synergy threshold ───────────────────────────────────────────────────
# The synergy lookup table has three distinct numeric scores.
# Score 1.4 = High synergy; 1.0 = Medium; 0.8 = Low.
HIGH_SYNERGY_SCORE = 1.4

# ── File and directory paths ─────────────────────────────────────────────────
ROOT          = Path(__file__).parent.parent           # project root directory
DATA_DIR      = ROOT / "data"
SYNERGY_TABLE = ROOT / "stimuli" / "synergy_table.csv"
OUT_DIR       = Path(__file__).parent                  # figures saved here

# ── Figure aesthetics ────────────────────────────────────────────────────────
BLOCK_COLORS = {
    "block_0": "#1f77b4",   # blue
    "block_2": "#ff7f0e",   # orange
    "block_4": "#2ca02c",   # green
}
BLOCK_LABELS = {
    "block_0": "Block 0",
    "block_2": "Block 2",
    "block_4": "Block 4",
}

GROUP_LW    = 2.5    # line width for group mean
IND_LW      = 0.9    # line width for individual participant lines
IND_ALPHA   = 0.25   # opacity of individual lines (low keeps them subtle)
MARKER_SIZE = 7      # data-point marker size on mean line
FIG_DPI     = 150    # PNG resolution
FIG_SIZE    = (11, 7) # (width, height) in inches for the main figure

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def sem(values):
    """
    Compute the standard error of the mean (SEM) for a collection of values.
    SEM = standard deviation / sqrt(n), using ddof=1 (sample SD).
    Returns NaN when there are fewer than 2 data points.
    """
    n = len(values)
    if n < 2:
        return np.nan
    return np.std(values, ddof=1) / np.sqrt(n)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 – LOAD RAW DATA
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 1: Loading data")
print(f"{'='*60}")

# Automatically discover every subject's trials.csv file.
# Expected folder structure: DATA_DIR / sub-XXX / trials.csv
trial_files = sorted(DATA_DIR.glob("sub-*/trials.csv"))

if not trial_files:
    sys.exit(
        f"\nERROR: No trials.csv files found in:\n  {DATA_DIR}\n"
        "Check that DATA_DIR points to the correct location."
    )

subject_dfs = []
for fpath in trial_files:
    df_sub = pd.read_csv(fpath, skipinitialspace=True)
    subject_dfs.append(df_sub)
    print(f"  Loaded: {fpath.parent.name}  ({len(df_sub)} rows)")

# Combine all subjects into a single long-format DataFrame.
df_raw = pd.concat(subject_dfs, ignore_index=True)
print(f"\nTotal rows loaded across all subjects: {len(df_raw)}")
print(f"Unique subjects: {sorted(df_raw[COL_SUBJECT].unique())}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 – INSPECT AVAILABLE COLUMNS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 2: Column inspection")
print(f"{'='*60}")

print("\nAll columns present in the combined dataset:")
print(f"  {'Column':<25} {'Dtype':<12} {'N unique':<10} Sample values")
print(f"  {'-'*65}")
for col in df_raw.columns:
    dtype    = df_raw[col].dtype
    n_unique = df_raw[col].nunique()
    sample   = list(df_raw[col].dropna().unique()[:3])
    print(f"  {col:<25} {str(dtype):<12} {n_unique:<10} {sample}")

# Verify that every column referenced in the config actually exists.
required_cols = [COL_SUBJECT, COL_PHASE, COL_BLOCK, COL_TRIAL_IDX,
                 COL_DOMAIN, COL_ROLE1, COL_ROLE2]
print("\nConfiguration → dataset column validation:")
for col in required_cols:
    status = "FOUND" if col in df_raw.columns else "MISSING — update config"
    print(f"  {col:<25} {status}")

missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    sys.exit(
        f"\nERROR: Required columns not found in data: {missing}\n"
        "Update the column-name constants at the top of this script."
    )

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – DATA QUALITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 3: Data quality checks")
print(f"{'='*60}")

issues_found = False

# ── 3a. Missing values ───────────────────────────────────────────────────────
print("\n[3a] Missing values in required columns:")
for col in required_cols:
    n_missing = df_raw[col].isna().sum()
    flag = "  <-- WARNING" if n_missing > 0 else ""
    print(f"  {col:<25}: {n_missing} missing{flag}")
    if n_missing > 0:
        issues_found = True

# ── 3b. Invalid trial indices ────────────────────────────────────────────────
# block_trial_id should be integers in [0, 17] for 18-trial blocks.
print(f"\n[3b] Checking {COL_TRIAL_IDX} range (expected 0–17):")
t_min = df_raw[COL_TRIAL_IDX].min()
t_max = df_raw[COL_TRIAL_IDX].max()
print(f"  Observed range: {t_min} – {t_max}")
bad_trials = df_raw[(df_raw[COL_TRIAL_IDX] < 0) | (df_raw[COL_TRIAL_IDX] > 17)]
if not bad_trials.empty:
    print(f"  WARNING: {len(bad_trials)} trial(s) with out-of-range indices:")
    print(bad_trials[[COL_SUBJECT, COL_BLOCK, COL_TRIAL_IDX]].head(10).to_string(index=False))
    issues_found = True
else:
    print("  All indices in 0–17. OK.")

# ── 3c. Role-code consistency ────────────────────────────────────────────────
# choice1_code and choice2_code should contain only A, B, C, or D.
print(f"\n[3c] Checking role codes (expected: A, B, C, D only):")
valid_roles = {"A", "B", "C", "D"}
for col in [COL_ROLE1, COL_ROLE2]:
    observed   = set(df_raw[col].dropna().astype(str).str.strip().unique())
    unexpected = observed - valid_roles
    print(f"  {col}: observed = {sorted(observed)}", end="")
    if unexpected:
        print(f"  WARNING: unexpected values → {sorted(unexpected)}")
        issues_found = True
    else:
        print("  OK.")

# ── 3d. Existing synergy-level column (optional) ─────────────────────────────
# If COL_SYNERGY_LEVEL is set and exists, check for inconsistent capitalisation
# or unexpected label values (e.g. "H" instead of "High").
if COL_SYNERGY_LEVEL and COL_SYNERGY_LEVEL in df_raw.columns:
    print(f"\n[3d] Checking existing '{COL_SYNERGY_LEVEL}' column:")
    raw_levels = df_raw[COL_SYNERGY_LEVEL].dropna().unique()
    print(f"  Unique raw values: {sorted(raw_levels)}")
    # Normalise capitalisation to catch "high", "HIGH", "H", etc.
    normalised       = df_raw[COL_SYNERGY_LEVEL].dropna().str.strip().str.title()
    unexpected_labels = set(normalised) - {"High", "Medium", "Low"}
    if unexpected_labels:
        print(f"  WARNING: unrecognised labels → {sorted(unexpected_labels)}")
        issues_found = True
    else:
        print("  All labels are valid (High / Medium / Low). OK.")
else:
    print(
        f"\n[3d] No pre-existing synergy-level column found in raw data. "
        "Synergy will be derived from role codes in Section 5."
    )

if issues_found:
    print("\n*** Some warnings were raised above — review before interpreting results. ***")
else:
    print("\nAll data quality checks passed.")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 – FILTER TO PHASE 1 TRIALS ONLY
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 4: Filtering to Phase 1 blocks (block_0, block_2, block_4)")
print(f"{'='*60}")

# Keep only Phase 1 rows. Filtering on both phase label and block name
# provides a double-check against potential mis-coding.
mask_p1 = (
    (df_raw[COL_PHASE] == PHASE_1_LABEL) &
    (df_raw[COL_BLOCK].isin(PHASE_1_BLOCKS))
)
df_p1 = df_raw[mask_p1].copy()

print(f"\nRows before filter : {len(df_raw)}")
print(f"Rows after filter  : {len(df_p1)}")

print("\nRow count per block after filtering:")
print(df_p1[COL_BLOCK].value_counts().sort_index().to_string())

print("\nRow count per subject after filtering:")
for sid in sorted(df_p1[COL_SUBJECT].unique()):
    n = (df_p1[COL_SUBJECT] == sid).sum()
    print(f"  Subject {sid}: {n} Phase 1 trial(s)")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 – COMPUTE SYNERGY LEVEL FROM ROLE CODES
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 5: Computing synergy level for each trial")
print(f"{'='*60}")

# Load the synergy reference table.
# Columns: pair_id, char1, char2, synergy_score
# synergy_score 2.0 = High, 1.5 = Medium, 1.0 = Low.
if not SYNERGY_TABLE.is_file():
    sys.exit(f"\nERROR: Synergy table not found at:\n  {SYNERGY_TABLE}")

synergy_df = pd.read_csv(SYNERGY_TABLE, skipinitialspace=True)
print(f"\nSynergy lookup table loaded from:\n  {SYNERGY_TABLE}")
print(synergy_df.to_string(index=False))

# Build a lookup dictionary keyed by the *sorted* role-pair tuple.
# Sorting ensures (A,C) and (C,A) both resolve to the same score —
# the order in which the participant chose the animals does not matter.
synergy_map = {}
for _, row in synergy_df.iterrows():
    r1  = str(row["char1"]).strip()
    r2  = str(row["char2"]).strip()
    key = tuple(sorted([r1, r2]))
    synergy_map[key] = float(row["synergy_score"])

print("\nSynergy lookup (sorted pair → score → level):")
for pair, score in sorted(synergy_map.items()):
    level = "High" if score == HIGH_SYNERGY_SCORE else ("Medium" if score == 1.0 else "Low")
    print(f"  {pair[0]}-{pair[1]}  →  {score}  ({level})")

# Apply the lookup to every row.
def lookup_synergy_score(row):
    """Return the numeric synergy score for the role-pair on this trial."""
    r1  = str(row[COL_ROLE1]).strip()
    r2  = str(row[COL_ROLE2]).strip()
    key = tuple(sorted([r1, r2]))
    return synergy_map.get(key, np.nan)

df_p1["synergy_score"] = df_p1.apply(lookup_synergy_score, axis=1)

# Attach a human-readable label for verification tables.
def score_to_level(score):
    """Map numeric synergy score to a descriptive label."""
    if score == 1.4:
        return "High"
    elif score == 1.0:
        return "Medium"
    elif score == 0.8:
        return "Low"
    return np.nan

df_p1["synergy_level"] = df_p1["synergy_score"].apply(score_to_level)

# Verify that every trial received a valid synergy score.
n_unmapped = df_p1["synergy_score"].isna().sum()
if n_unmapped > 0:
    print(f"\nWARNING: {n_unmapped} trial(s) could not be mapped to a synergy score.")
    print(df_p1[df_p1["synergy_score"].isna()][
        [COL_SUBJECT, COL_BLOCK, COL_TRIAL_IDX, COL_ROLE1, COL_ROLE2]
    ].head(10).to_string(index=False))
else:
    print(f"\nAll {len(df_p1)} Phase 1 trials successfully assigned a synergy score.")

print("\nSynergy level distribution (Phase 1, all subjects):")
print(df_p1["synergy_level"].value_counts().sort_index().to_string())

# ── Create the key dependent variable ────────────────────────────────────────
# chose_high_synergy = 1  →  participant selected the high-synergy pair
#                   = 0  →  participant selected a medium- or low-synergy pair
# Chance level: there are 2 high-synergy pairs out of 6 possible pairs = 1/3.
df_p1["chose_high_synergy"] = (
    df_p1["synergy_score"] == HIGH_SYNERGY_SCORE
).astype(int)

overall_prop = df_p1["chose_high_synergy"].mean()
print(f"\nOverall P(high-synergy) across Phase 1:  {overall_prop:.3f}")
print(f"Chance level (2 high-syn pairs / 6 total pairs): {1/3:.3f}")

print("\nSample rows (subject, block, trial_idx, role1, role2, synergy_level, chose_high_synergy):")
cols_show = [COL_SUBJECT, COL_BLOCK, COL_TRIAL_IDX, COL_ROLE1, COL_ROLE2,
             "synergy_level", "chose_high_synergy"]
print(df_p1[cols_show].head(12).to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 – ASSIGN TRIAL BINS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 6: Assigning trial bins (Early / Middle / Late)")
print(f"{'='*60}")

# pd.cut with right=False creates left-closed, right-open intervals:
#   [0, 6)  → Early   (block_trial_id 0–5,  i.e. trials 1–6)
#   [6, 12) → Middle  (block_trial_id 6–11, i.e. trials 7–12)
#   [12,18) → Late    (block_trial_id 12–17,i.e. trials 13–18)
# The largest index is 17, which falls in [12, 18), so nothing is excluded.
df_p1["trial_bin"] = pd.cut(
    df_p1[COL_TRIAL_IDX],
    bins=BIN_EDGES,
    labels=BIN_LABELS,
    right=False,           # intervals are [left, right)
    include_lowest=True,   # ensures index 0 is captured in the first bin
)

# Make trial_bin an ordered categorical so sorts and plots follow Early→Late.
bin_order          = pd.CategoricalDtype(categories=BIN_LABELS, ordered=True)
df_p1["trial_bin"] = df_p1["trial_bin"].astype(bin_order)

print("\nTrial-bin assignment distribution:")
print(df_p1["trial_bin"].value_counts().sort_index().to_string())

print("\nSample rows (subject, block, trial_idx, trial_bin, chose_high_synergy):")
print(df_p1[
    [COL_SUBJECT, COL_BLOCK, COL_TRIAL_IDX, "trial_bin", "chose_high_synergy"]
].head(18).to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 – PER-PARTICIPANT PROPORTIONS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 7: Computing per-participant proportions")
print(f"{'='*60}")

# For each participant × block × trial_bin cell, compute the proportion of
# trials on which they chose a high-synergy pair.
# This yields one number per cell — the within-cell accuracy for that person.
part_props = (
    df_p1
    .groupby([COL_SUBJECT, COL_BLOCK, "trial_bin"], observed=True)["chose_high_synergy"]
    .mean()
    .reset_index()
    .rename(columns={"chose_high_synergy": "prop_high_synergy"})
)
part_props["trial_bin"] = part_props["trial_bin"].astype(bin_order)

n_subj    = df_p1[COL_SUBJECT].nunique()
n_blocks  = len(PHASE_1_BLOCKS)
n_bins    = len(BIN_LABELS)
n_expected = n_subj * n_blocks * n_bins

print(f"\nExpected rows (n_subj × n_blocks × n_bins = {n_subj} × {n_blocks} × {n_bins}): {n_expected}")
print(f"Actual rows in participant-level table: {len(part_props)}")
if len(part_props) < n_expected:
    print("  NOTE: Some participant × block × bin cells have no trials and were omitted.")

print("\nPer-participant proportions:")
print(
    part_props
    .sort_values([COL_SUBJECT, COL_BLOCK, "trial_bin"])
    .to_string(index=False)
)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 – GROUP MEAN AND SEM
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 8: Computing group mean and SEM")
print(f"{'='*60}")

# Average the per-participant proportions across subjects for each
# block × trial_bin combination. SEM = SD / sqrt(N).
group_stats = (
    part_props
    .groupby([COL_BLOCK, "trial_bin"], observed=True)["prop_high_synergy"]
    .agg(
        mean=lambda x: np.mean(x),
        sem=sem,
        n="count",
    )
    .reset_index()
)
group_stats["trial_bin"] = group_stats["trial_bin"].astype(bin_order)

print("\nGroup-level summary (mean ± SEM across participants):")
print(group_stats.sort_values([COL_BLOCK, "trial_bin"]).to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 – FIGURE 2A: GROUP MEAN LEARNING CURVE
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 9: Generating Figure 2A — group mean learning curve")
print(f"{'='*60}")

fig2a, ax = plt.subplots(figsize=FIG_SIZE)

# Integer x-positions correspond to the three categorical trial-bin labels.
x_pos = np.arange(len(BIN_LABELS))  # [0, 1, 2]

for block in PHASE_1_BLOCKS:

    # Subset to this block and sort in Early → Middle → Late order.
    block_data = (
        group_stats[group_stats[COL_BLOCK] == block]
        .sort_values("trial_bin")
    )

    means = block_data["mean"].values
    sems  = block_data["sem"].values
    color = BLOCK_COLORS[block]
    label = BLOCK_LABELS[block]

    # Draw the group mean as a connected line with markers at each bin.
    ax.plot(
        x_pos, means,
        color=color,
        linewidth=GROUP_LW,
        marker="o",
        markersize=MARKER_SIZE,
        label=label,
        zorder=3,
    )

    # Overlay SEM error bars. fmt="none" suppresses a second connecting line
    # (the mean line above already handles that).
    ax.errorbar(
        x_pos, means,
        yerr=sems,
        fmt="none",
        color=color,
        linewidth=1.5,
        capsize=4,
        zorder=4,
    )

# Horizontal dashed line at chance level (2 high-syn pairs / 6 possible = 0.333).
ax.axhline(
    y=1 / 3,
    color="gray",
    linestyle="--",
    linewidth=1.0,
    alpha=0.6,
    label="Chance (1/3)",
)

# ── Axis formatting ──────────────────────────────────────────────────────────
ax.set_xticks(x_pos)
ax.set_xticklabels(BIN_LABELS, fontsize=22)
ax.set_xlim(-0.4, len(BIN_LABELS) - 0.6)

ax.set_ylim(0, 1)
ax.tick_params(axis="y", labelsize=22)
ax.set_xlabel("Trial Bin", fontsize=24, labelpad=10)
ax.set_ylabel("Probability of Choosing a High-Synergy Pair", fontsize=22, labelpad=10)
ax.set_title(
    "Phase 1: High-Synergy Choices Across Trials",
    fontsize=26, fontweight="bold", pad=15,
)

# Subtle horizontal grid lines aid reading values.
ax.yaxis.set_minor_locator(plt.MultipleLocator(0.05))
ax.grid(axis="y", which="major", alpha=0.3, linewidth=0.8)
ax.grid(axis="y", which="minor", alpha=0.1, linewidth=0.5)

# Remove top and right spines for a cleaner publication look.
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.legend(frameon=False, fontsize=20, loc="upper left")

# Sample-size annotation in the lower-right corner.
ax.text(
    0.98, 0.03,
    f"n = {n_subj}",
    transform=ax.transAxes,
    ha="right", va="bottom",
    fontsize=20, color="gray",
)

fig2a.tight_layout(pad=2.5)

# Save in both PNG (for presentations) and SVG (for vector editing).
png_2a = OUT_DIR / "figure2A_phase1_learning_curve.png"
svg_2a = OUT_DIR / "figure2A_phase1_learning_curve.svg"
fig2a.savefig(png_2a, dpi=FIG_DPI, bbox_inches="tight")
fig2a.savefig(svg_2a, bbox_inches="tight")
print(f"  Saved: {png_2a}")
print(f"  Saved: {svg_2a}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10 – SUPPLEMENTAL FIGURE: INDIVIDUAL TRAJECTORIES + GROUP MEAN
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("SECTION 10: Generating supplemental figure — individual trajectories")
print(f"{'='*60}")

subjects = sorted(df_p1[COL_SUBJECT].unique())

# One subplot per Phase 1 block, arranged in a single row.
fig_ind, axes = plt.subplots(
    1, len(PHASE_1_BLOCKS),
    figsize=(7 * len(PHASE_1_BLOCKS), 7),
    sharey=True,          # share the y-axis so panels are directly comparable
)

for ax_i, block in enumerate(PHASE_1_BLOCKS):
    ax_sub = axes[ax_i]
    color  = BLOCK_COLORS[block]

    # ── Individual participant lines ─────────────────────────────────────────
    # Each participant appears as a thin, semi-transparent line so that the
    # distribution of trajectories is visible without overwhelming the plot.
    for sid in subjects:
        ind_data = (
            part_props[
                (part_props[COL_SUBJECT] == sid) &
                (part_props[COL_BLOCK]   == block)
            ]
            .sort_values("trial_bin")
        )
        if ind_data.empty:
            continue   # skip if this subject has no data for this block

        ax_sub.plot(
            x_pos,
            ind_data["prop_high_synergy"].values,
            color=color,
            linewidth=IND_LW,
            alpha=IND_ALPHA,
            marker="o",
            markersize=3,
            zorder=2,
        )

    # ── Group mean overlay ────────────────────────────────────────────────────
    # Drawn on top of individual lines (higher zorder) so it stands out clearly.
    blk_stats = (
        group_stats[group_stats[COL_BLOCK] == block]
        .sort_values("trial_bin")
    )
    ax_sub.plot(
        x_pos,
        blk_stats["mean"].values,
        color=color,
        linewidth=GROUP_LW,
        marker="o",
        markersize=MARKER_SIZE,
        zorder=3,
    )
    ax_sub.errorbar(
        x_pos,
        blk_stats["mean"].values,
        yerr=blk_stats["sem"].values,
        fmt="none",
        color=color,
        linewidth=1.5,
        capsize=4,
        zorder=4,
    )

    # Chance reference line.
    ax_sub.axhline(1 / 3, color="gray", linestyle="--", linewidth=1.0, alpha=0.6)

    # ── Panel formatting ──────────────────────────────────────────────────────
    ax_sub.set_xticks(x_pos)
    ax_sub.set_xticklabels(BIN_LABELS, fontsize=22)
    ax_sub.set_xlim(-0.4, len(BIN_LABELS) - 0.6)
    ax_sub.set_ylim(0, 1)
    ax_sub.tick_params(axis="y", labelsize=22)
    ax_sub.set_xlabel("Trial Bin", fontsize=24, labelpad=10)
    ax_sub.set_title(BLOCK_LABELS[block], fontsize=26, fontweight="bold", color=color, pad=12)
    ax_sub.spines["top"].set_visible(False)
    ax_sub.spines["right"].set_visible(False)
    ax_sub.grid(axis="y", alpha=0.3, linewidth=0.8)

    # Only the leftmost panel needs a y-axis label (shared axis, so no repeat).
    if ax_i == 0:
        ax_sub.set_ylabel("Probability of Choosing a High-Synergy Pair", fontsize=22, labelpad=10)

# ── Shared legend at the bottom of the figure ────────────────────────────────
ind_handle = mlines.Line2D(
    [], [],
    color="gray", linewidth=IND_LW, alpha=0.6,
    label="Individual participants",
)
grp_handle = mlines.Line2D(
    [], [],
    color="gray", linewidth=GROUP_LW,
    label="Group mean ± SEM",
)
fig_ind.legend(
    handles=[ind_handle, grp_handle],
    loc="lower center",
    ncol=2,
    fontsize=20,
    frameon=False,
    bbox_to_anchor=(0.5, -0.04),
)

fig_ind.suptitle(
    "Phase 1: High-Synergy Choices — Individual Trajectories",
    fontsize=26, fontweight="bold", y=1.03,
)
fig_ind.tight_layout(pad=2.5, w_pad=3.5)

png_ind = OUT_DIR / "figure2A_phase1_individual_trajectories.png"
svg_ind = OUT_DIR / "figure2A_phase1_individual_trajectories.svg"
fig_ind.savefig(png_ind, dpi=FIG_DPI, bbox_inches="tight")
fig_ind.savefig(svg_ind, bbox_inches="tight")
print(f"  Saved: {png_ind}")
print(f"  Saved: {svg_ind}")

plt.show()
print("\nDone.")