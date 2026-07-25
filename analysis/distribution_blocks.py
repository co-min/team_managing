from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Load all subjects ──────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
files = sorted(DATA_DIR.glob("sub-*/trials.csv"))
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

# ── Block number ───────────────────────────────────────────────────────────────
df["block_num"] = df["block"].str.extract(r"(\d+)").astype(int)

# ── Early / Late label (50% split within each subject × block) ─────────────────
def label_split(grp):
    grp = grp.sort_values("block_trial_id")
    n = len(grp)
    labels = ["early"] * (n // 2) + ["late"] * (n - n // 2)
    grp["split"] = labels
    return grp

df = df.groupby(["subject_id", "block"], group_keys=False).apply(label_split)

# ── Plot setup ─────────────────────────────────────────────────────────────────
DOMAINS = ["cooking", "repairing", "tennis"]
BLOCKS  = list(range(6))
PHASE1_BLOCKS = {0, 2, 4}   # tennis exists only here

COLORS = {"early": "#4C9BE8", "late": "#E8834C"}

fig, axes = plt.subplots(
    nrows=3, ncols=6,
    figsize=(22, 12),
    sharey=False,
    gridspec_kw={"hspace": 0.6, "wspace": 0.45},
)

for row_i, domain in enumerate(DOMAINS):
    for col_i, block_num in enumerate(BLOCKS):

        ax = axes[row_i][col_i]

        # Tennis only in phase-1 blocks
        if domain == "tennis" and block_num not in PHASE1_BLOCKS:
            ax.set_visible(False)
            continue

        subset = df[(df["domain"] == domain) & (df["block_num"] == block_num)]

        early_vals = subset.loc[subset["split"] == "early", "feedback_score"].dropna().values
        late_vals  = subset.loc[subset["split"] == "late",  "feedback_score"].dropna().values

        data   = [v for v in [early_vals, late_vals] if len(v) > 0]
        labels = ["early", "late"][: len(data)]

        if not data:
            ax.set_visible(False)
            continue

        parts = ax.violinplot(
            data,
            positions=range(len(data)),
            showmedians=True,
            showextrema=True,
        )

        # Color each violin
        for patch, lbl in zip(parts["bodies"], labels):
            patch.set_facecolor(COLORS[lbl])
            patch.set_alpha(0.75)
        for key in ("cmedians", "cmins", "cmaxes", "cbars"):
            if key in parts:
                parts[key].set_color("black")
                parts[key].set_linewidth(1.0)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=11)
        ax.tick_params(axis="y", labelsize=10)

        # Titles / labels
        if row_i == 0:
            ax.set_title(f"block {block_num}", fontsize=12, fontweight="bold")
        if col_i == 0:
            ax.set_ylabel(domain, fontsize=12, fontweight="bold")

# ── Legend ─────────────────────────────────────────────────────────────────────
patches = [mpatches.Patch(color=c, label=l, alpha=0.75) for l, c in COLORS.items()]
fig.legend(handles=patches, loc="lower center", ncol=2, fontsize=12, frameon=False,
           bbox_to_anchor=(0.5, 0.01))

fig.suptitle("Score Distribution by Block × Domain (early vs late)", fontsize=16, y=1.01)

plt.savefig("distribution_blocks.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: distribution_blocks.png")
