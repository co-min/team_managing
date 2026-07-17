"""
Usage:
    python analysis/plot_sigmoid_block.py sub-001
    python analysis/plot_sigmoid_block.py 001

Fits a sigmoid curve to normalized trial scores (score / 12, range 0-1)
over trial order within each block. All 6 blocks are shown in one PNG.

Layout: 2 rows × 3 cols
  Row 1 (Phase 1 — Competence): Block 1, Block 3, Block 5
  Row 2 (Phase 2 — Synergy):    Block 2, Block 4, Block 6

One PNG file is saved to data/<sub>/:
  plot_sigmoid_blocks.png

Sigmoid model:  f(x) = L / (1 + exp(-k*(x - x0))) + b
"""

import sys
import argparse
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
ROOT = Path(__file__).resolve().parents[1]

SCORE_MAX = 12.0

DOMAIN_COLOR = {
    "cooking":   "#E8813A",
    "repairing": "#4A90D9",
    "tennis":    "#5DB85D",
}
OLD_FMT_BLOCK = {
    ("phase_1", "cooking"):   1,
    ("phase_1", "repairing"): 3,
    ("phase_1", "tennis"):    5,
    ("phase_2", "cooking"):   2,
    ("phase_2", "repairing"): 4,
    ("phase_2", "tennis"):    6,
}

# 2×3 grid: each cell is (row, col, block_number)
GRID_LAYOUT = [
    (0, 0, 1),
    (0, 1, 3),
    (0, 2, 5),
    (1, 0, 2),
    (1, 1, 4),
    (1, 2, 6),
]

ROW_LABELS = {
    0: "Phase 1  (Competence)",
    1: "Phase 2  (Synergy)",
}


def assign_block_label(df: pd.DataFrame) -> pd.DataFrame:
    sid = df["stim_pair_id"].astype(str)
    new_label = pd.to_numeric(sid.str.extract(r"^block(\d+)_", expand=False), errors="coerce") + 1
    old_label = pd.Series(zip(df["phase"], df["domain"]), index=df.index).map(OLD_FMT_BLOCK)
    df = df.copy()
    df["block_label"] = new_label.combine_first(old_label)
    return df[df["block_label"].notna()].copy()



def plot_block(ax, block_df: pd.DataFrame, block_num: int):
    block_df = block_df.dropna(subset=["feedback_score"]).reset_index(drop=True)

    ax.set_title(f"Block {int(block_num)}", fontsize=9, fontweight="bold", pad=4)

    if block_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="gray", fontsize=9)
        ax.set_axis_off()
        return

    block_df["norm_score"] = block_df["feedback_score"] / SCORE_MAX
    # Scatter: color by domain
    for i, row in block_df.iterrows():
        color = DOMAIN_COLOR.get(row["domain"], "gray")
        ax.scatter(i, row["norm_score"], color=color, s=45, zorder=3,
                   edgecolors="white", linewidths=0.5)


    ax.set_xlim(-1, len(block_df))
    ax.set_ylim(-0.05, 1.15)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis="y", alpha=0.3, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=7)


def main():
    parser = argparse.ArgumentParser(
        description="Sigmoid fit per block in a single PNG (2×3 grid)."
    )
    parser.add_argument("sub", help="Subject ID (e.g. sub-001, 001, or 1)")
    args = parser.parse_args()

    sub = args.sub.strip()
    if not sub.startswith("sub-"):
        sub = f"sub-{sub.zfill(3)}"

    trials_path = ROOT / "data" / sub / "trials.csv"
    if not trials_path.exists():
        print(f"[ERROR] File not found: {trials_path}")
        sys.exit(1)

    df = pd.read_csv(trials_path, on_bad_lines="skip")
    df = assign_block_label(df)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    fig.suptitle(f"{sub}  —  Sigmoid Fit per Block", fontsize=14, fontweight="bold", y=0.98)

    for row, col, blk in GRID_LAYOUT:
        ax = axes[row, col]
        block_df = df[df["block_label"] == blk].copy()
        plot_block(ax, block_df, blk)

    # Row labels on the left
    for row, label in ROW_LABELS.items():
        axes[row, 0].set_ylabel(f"{label}\n\nNorm. Score", fontsize=8)

    # Shared x-label at bottom
    for col in range(3):
        axes[1, col].set_xlabel("Trial (within block)", fontsize=8)

    # Shared legend (domain colors — patches double as sigmoid line color guide)
    domain_patches = [
        mpatches.Patch(color=c, label=d.capitalize())
        for d, c in DOMAIN_COLOR.items()
    ]
    fig.legend(handles=domain_patches,
               loc="lower center", ncol=3, fontsize=8.5,
               framealpha=0.9, bbox_to_anchor=(0.5, 0.01))

    plt.tight_layout(rect=[0, 0.06, 1, 0.97])

    out_dir = ROOT / "data" / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "plot_sigmoid_blocks.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
