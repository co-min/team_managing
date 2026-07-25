from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Load all subjects ──────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
files = sorted(DATA_DIR.glob("sub-*/trials.csv"))
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

# ── Block number ───────────────────────────────────────────────────────────────
df["block_num"] = df["block"].str.extract(r"(\d+)").astype(int)

# ── Early / Late split within (subject × block × domain) ──────────────────────
# block_trial_id is a block-wide counter across all domains, so splitting by
# (subject, block) alone reflects domain presentation order, not within-domain
# trial order. Grouping by domain as well fixes this.
def label_split_series(grp):
    sorted_idx = grp.sort_values().index
    n = len(sorted_idx)
    return pd.Series(["early"] * (n // 2) + ["late"] * (n - n // 2), index=sorted_idx)

df["split"] = df.groupby(["subject_id", "block", "domain"])["block_trial_id"].transform(label_split_series)

# ── Min-max normalization per domain × block (pooled across subjects) ──────────
_mn = df.groupby(["domain", "block_num"])["feedback_score"].transform("min")
_mx = df.groupby(["domain", "block_num"])["feedback_score"].transform("max")
df["score_norm"] = np.where(_mn == _mx, 0.5, (df["feedback_score"] - _mn) / (_mx - _mn))

# ── Plot setup ─────────────────────────────────────────────────────────────────
DOMAINS  = ["cooking", "repairing", "tennis"]
BLOCKS   = [0, 2, 4]
SUBJECTS = sorted(df["subject_id"].unique())

COLORS = {"early": "#4C9BE8", "late": "#E8834C"}

N_BINS = 10
bins        = np.linspace(0, 1, N_BINS + 1)
bin_centers = (bins[:-1] + bins[1:]) / 2
bar_w       = (bins[1] - bins[0]) * 0.4

fig, axes = plt.subplots(
    nrows=3, ncols=3,
    figsize=(20, 13),
    sharey=False,
    gridspec_kw={"hspace": 0.0, "wspace": 0.0},
)
fig.set_constrained_layout(True)
fig.set_constrained_layout_pads(hspace=0.08, wspace=0.08, h_pad=0.6, w_pad=0.8)

rng = np.random.default_rng(42)

for row_i, domain in enumerate(DOMAINS):
    for col_i, block_num in enumerate(BLOCKS):

        ax = axes[row_i][col_i]

        subset     = df[(df["domain"] == domain) & (df["block_num"] == block_num)]
        early_vals = subset.loc[subset["split"] == "early", "score_norm"].dropna().values
        late_vals  = subset.loc[subset["split"] == "late",  "score_norm"].dropna().values

        if len(early_vals) == 0 and len(late_vals) == 0:
            ax.set_visible(False)
            continue

        # ── Rate histogram ─────────────────────────────────────────────────────
        early_counts, _ = np.histogram(early_vals, bins=bins)
        late_counts,  _ = np.histogram(late_vals,  bins=bins)

        early_rate = early_counts / early_counts.sum() if early_counts.sum() > 0 else np.zeros(N_BINS)
        late_rate  = late_counts  / late_counts.sum()  if late_counts.sum()  > 0 else np.zeros(N_BINS)

        ax.bar(bin_centers - bar_w / 2, early_rate,
               width=bar_w, color=COLORS["early"], alpha=0.65)
        ax.bar(bin_centers + bar_w / 2, late_rate,
               width=bar_w, color=COLORS["late"],  alpha=0.65)

        # ── Group mean dashed lines ────────────────────────────────────────────
        if len(early_vals) > 0:
            ax.axvline(early_vals.mean(), color=COLORS["early"], lw=1.4,
                       linestyle="--", alpha=0.9, zorder=3)
        if len(late_vals) > 0:
            ax.axvline(late_vals.mean(), color=COLORS["late"], lw=1.4,
                       linestyle="--", alpha=0.9, zorder=3)

        # ── Individual subject means as strip below bars ───────────────────────
        STRIP_Y = -0.11   # lower strip so x-tick labels don't overlap
        for sub in SUBJECTS:
            sub_rows   = subset[subset["subject_id"] == sub]
            sub_early  = sub_rows.loc[sub_rows["split"] == "early", "score_norm"].mean()
            sub_late   = sub_rows.loc[sub_rows["split"] == "late",  "score_norm"].mean()

            y_jitter = rng.uniform(-0.012, 0.012)

            if not np.isnan(sub_early):
                ax.scatter(sub_early, STRIP_Y + y_jitter,
                           color=COLORS["early"], s=22, zorder=6,
                           clip_on=False, alpha=0.9, linewidths=0)
            if not np.isnan(sub_late):
                ax.scatter(sub_late, STRIP_Y + y_jitter,
                           color=COLORS["late"], s=22, marker="D", zorder=6,
                           clip_on=False, alpha=0.9, linewidths=0)
            if not np.isnan(sub_early) and not np.isnan(sub_late):
                ax.plot([sub_early, sub_late], [STRIP_Y + y_jitter] * 2,
                        color="gray", lw=0.6, alpha=0.35, zorder=5, clip_on=False)

        # ── Axes formatting ────────────────────────────────────────────────────
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.17, 0.72)   # extra bottom room for strip dots
        sparse_ticks = bin_centers[::2]   # every other bin → 5 ticks, no overlap
        ax.set_xticks(np.round(sparse_ticks, 2))
        ax.set_xticklabels([f"{v:.1f}" for v in sparse_ticks],
                           fontsize=12, rotation=30, ha="right")
        ax.tick_params(axis="y", labelsize=12)
        ax.tick_params(axis="x", pad=4)

        # mark strip-row with a thin horizontal line
        ax.axhline(0, color="black", lw=0.5, alpha=0.3)

        # n label
        ax.text(0.98, 0.97,
                f"n={len(early_vals)}/{len(late_vals)}",
                transform=ax.transAxes, fontsize=11, ha="right", va="top", color="gray")

        if row_i == 0:
            ax.set_title(f"block {block_num}", fontsize=16, fontweight="bold", pad=6)
        if col_i == 0:
            ax.set_ylabel(f"{domain}\nrate", fontsize=16, fontweight="bold", labelpad=6)
        if row_i == 2:
            ax.set_xlabel("pair value (norm.)", fontsize=14, labelpad=8)

# ── Legend ─────────────────────────────────────────────────────────────────────
bar_patches = [mpatches.Patch(color=c, label=f"{l} (bar = rate)", alpha=0.65)
               for l, c in COLORS.items()]
dot_handles = [
    plt.Line2D([0], [0], marker="o",  color="w", markerfacecolor=COLORS["early"],
               markersize=6, label="early mean (subject)"),
    plt.Line2D([0], [0], marker="D",  color="w", markerfacecolor=COLORS["late"],
               markersize=6, label="late mean (subject)"),
    plt.Line2D([0], [0], color=COLORS["early"], lw=1.4, linestyle="--", label="early group mean"),
    plt.Line2D([0], [0], color=COLORS["late"],  lw=1.4, linestyle="--", label="late group mean"),
]
fig.legend(handles=bar_patches + dot_handles,
           loc="lower center", ncol=3, fontsize=13, frameon=False,
           bbox_to_anchor=(0.5, -0.04))

fig.suptitle(
    "Score Distribution by Block × Domain  |  early vs late  (min-max norm per block)\n"
    "bars = group rate  ·  dots = subject mean  ·  dashed = group mean",
    fontsize=18, fontweight="bold",
)

out = Path(__file__).parent.parent / "distribution_blocks_phase1.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.show()
print(f"Saved: {out}")
