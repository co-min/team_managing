"""
Usage:
    python analysis/plot_performance.py sub-001
    python analysis/plot_performance.py 001

Two PNG files are saved to data/<sub>/:
  plot_phase1.png  —  Phase 1 (blocks 1, 3, 5)
  plot_phase2.png  —  Phase 2 (blocks 2, 4, 6)

Data format support:
  New format  stim_pair_id = block{N}_phase_{1,2}_t{NN}  → actual block numbers used
  Old format  stim_pair_id = {domain}_phase_{1,2}_t{NN}  → domain mapped to virtual blocks
              (cooking→1/2, repairing→3/4, tennis→5/6)
"""

import sys
import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

ROOT = Path(__file__).resolve().parents[1]

DOMAIN_COLOR = {
    "cooking":   "#E8813A",
    "repairing": "#4A90D9",
    "tennis":    "#5DB85D",
}
DOMAIN_ABBR = {
    "cooking":   "Ck",
    "repairing": "Rp",
    "tennis":    "Tn",
}

OLD_FMT_BLOCK = {
    ("phase_1", "cooking"):   1,
    ("phase_1", "repairing"): 3,
    ("phase_1", "tennis"):    5,
    ("phase_2", "cooking"):   2,
    ("phase_2", "repairing"): 4,
    ("phase_2", "tennis"):    6,
}

PHASES = [
    {
        "key":    "phase_1",
        "title":  "Phase 1  (Competence  —  blocks 1 · 3 · 5)",
        "blocks": [1, 3, 5],
        "file":   "plot_phase1.png",
    },
    {
        "key":    "phase_2",
        "title":  "Phase 2  (Synergy  —  blocks 2 · 4 · 6)",
        "blocks": [2, 4, 6],
        "file":   "plot_phase2.png",
    },
]


def assign_block_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized: detects stim_pair_id format and assigns block_label (1-indexed).
    New format: block{N}_phase_*  → N + 1
    Old format: {domain}_phase_*  → OLD_FMT_BLOCK lookup
    combine_first: new-format label takes priority; falls back to old-format.
    """
    sid = df["stim_pair_id"].astype(str)
    new_label = pd.to_numeric(sid.str.extract(r"^block(\d+)_", expand=False), errors="coerce") + 1
    old_label = pd.Series(zip(df["phase"], df["domain"]), index=df.index).map(OLD_FMT_BLOCK)

    df = df.copy()
    df["block_label"] = new_label.combine_first(old_label)
    return df[df["block_label"].notna()].copy()


def xtick_label(row) -> str:
    abbr = DOMAIN_ABBR.get(row["domain"], row["domain"][:2].title())
    a1, a2 = row.get("choice1_animal"), row.get("choice2_animal")
    if pd.isna(a1) or pd.isna(a2):
        return f"{abbr}\n(no resp.)"
    return f"{abbr}\n{a1}+{a2}"


def plot_block(ax, block_df: pd.DataFrame, block_label: int,
               best_score_by_domain: dict):
    """Draw one subplot for a single block."""
    ax.set_title(f"Block {block_label}", fontsize=11, fontweight="bold", pad=6)

    if block_df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, fontsize=10, color="gray")
        ax.set_axis_off()
        return

    block_df = block_df.reset_index(drop=True)
    n = len(block_df)

    # Best-score reference lines
    drawn_domains = set()
    for domain in block_df["domain"].unique():
        if domain not in best_score_by_domain:
            continue
        color = DOMAIN_COLOR.get(domain, "gray")
        ax.axhline(best_score_by_domain[domain], color=color, linewidth=1.4,
                   linestyle="--", alpha=0.85, zorder=1)
        drawn_domains.add(domain)

    # Score dots
    for i, row in block_df.iterrows():
        color = DOMAIN_COLOR.get(row["domain"], "gray")
        score = row["feedback_score"]
        if pd.isna(score):
            ax.scatter(i, 0, marker="x", color="crimson", s=60, linewidths=1.5, zorder=3)
        else:
            ax.scatter(i, score, color=color, s=70, zorder=3,
                       edgecolors="white", linewidths=0.6)
            ax.text(i, score + 0.25, f"{score:.1f}",
                    ha="center", va="bottom", fontsize=6.5, color=color)

    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(
        [xtick_label(row) for _, row in block_df.iterrows()],
        rotation=45, ha="right", fontsize=6.5, linespacing=1.3,
    )
    ax.set_xlim(-0.7, n - 0.3)
    ax.set_ylim(0, 12)
    ax.set_yticks(range(0, 13, 2))
    ax.set_ylabel("Score", fontsize=9)
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    # Right-edge annotation per domain
    for domain in drawn_domains:
        best = best_score_by_domain[domain]
        color = DOMAIN_COLOR.get(domain, "gray")
        abbr = DOMAIN_ABBR.get(domain, domain[:2].title())
        ax.annotate(f"best {abbr}: {best:.1f}",
                    xy=(n - 0.3, best), xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=6, color=color, va="center")


def build_figure(title: str, phase_df: pd.DataFrame,
                 block_labels: list, best_by_domain: dict,
                 sub: str) -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(22, 6.5))
    fig.suptitle(f"{sub}  —  {title}", fontsize=13, fontweight="bold", y=1.01)

    for ax, blk in zip(axes, block_labels):
        plot_block(ax, phase_df[phase_df["block_label"] == blk].copy(), blk, best_by_domain)

    domain_patches = [
        mpatches.Patch(color=c, label=d.capitalize())
        for d, c in DOMAIN_COLOR.items()
        if d in best_by_domain or (phase_df["domain"] == d).any()
    ]
    fig.legend(
        handles=domain_patches + [
            mlines.Line2D([], [], color="crimson", marker="x", linestyle="None",
                          markersize=7, label="No response"),
            mlines.Line2D([], [], color="gray", linestyle="--", linewidth=1.4,
                          label="Best score (per domain)"),
        ],
        loc="upper right", fontsize=8.5, framealpha=0.9, bbox_to_anchor=(1.0, 1.0),
    )
    plt.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(
        description="Plot per-trial performance by phase and block."
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

    out_dir = ROOT / "data" / sub
    out_dir.mkdir(parents=True, exist_ok=True)

    for phase in PHASES:
        phase_df = df[df["phase"] == phase["key"]].copy()
        best = phase_df.groupby("domain")["feedback_score"].max().to_dict()
        fig = build_figure(phase["title"], phase_df, phase["blocks"], best, sub)
        path = out_dir / phase["file"]
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"[{phase['key']}] saved -> {path}")


if __name__ == "__main__":
    main()
