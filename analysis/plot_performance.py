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
import re
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

# Phase 1 blocks (1-indexed): 1, 3, 5
# Phase 2 blocks (1-indexed): 2, 4, 6
PHASE1_BLOCK_LABELS = [1, 3, 5]
PHASE2_BLOCK_LABELS = [2, 4, 6]

# Old-format: domain → virtual block label
#   Phase 1: cooking=1, repairing=3, tennis=5
#   Phase 2: cooking=2, repairing=4, tennis=6
OLD_FMT_BLOCK = {
    ("phase_1", "cooking"):   1,
    ("phase_1", "repairing"): 3,
    ("phase_1", "tennis"):    5,
    ("phase_2", "cooking"):   2,
    ("phase_2", "repairing"): 4,
    ("phase_2", "tennis"):    6,
}

_BLOCK_RE = re.compile(r"^block(\d+)_")
_OLD_RE   = re.compile(r"^(cooking|repairing|tennis)_phase_")


def assign_block_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect which format the stim_pair_id uses and assign block_label (1-indexed).
    New format: block{N}_phase_*  →  block_label = N + 1
    Old format: {domain}_phase_*  →  virtual block from OLD_FMT_BLOCK
    Mixed: each row is handled individually.
    Returns a filtered copy (rows with a valid block_label only).
    """
    labels = []
    for _, row in df.iterrows():
        sid = str(row["stim_pair_id"])
        m = _BLOCK_RE.match(sid)
        if m:
            labels.append(int(m.group(1)) + 1)
        elif _OLD_RE.match(sid):
            key = (row["phase"], row["domain"])
            labels.append(OLD_FMT_BLOCK.get(key))
        else:
            labels.append(None)

    df = df.copy()
    df["block_label"] = labels
    return df[df["block_label"].notna()].copy()


def xtick_label(row) -> str:
    abbr = DOMAIN_ABBR.get(row["domain"], row["domain"][:2].title())
    a1 = row.get("choice1_animal")
    a2 = row.get("choice2_animal")
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

    # ── Best-score reference lines per domain ──────────────────────────────
    present_domains = block_df["domain"].unique()
    drawn_domains: set[str] = set()
    for domain in present_domains:
        if domain not in best_score_by_domain:
            continue
        best = best_score_by_domain[domain]
        color = DOMAIN_COLOR.get(domain, "gray")
        ax.axhline(best, color=color, linewidth=1.4, linestyle="--",
                   alpha=0.85, zorder=1)
        drawn_domains.add(domain)

    # ── Score dots ─────────────────────────────────────────────────────────
    for i, row in block_df.iterrows():
        color = DOMAIN_COLOR.get(row["domain"], "gray")
        score = row["feedback_score"]
        if pd.isna(score):
            ax.scatter(i, 0, marker="x", color="crimson", s=60,
                       linewidths=1.5, zorder=3)
        else:
            ax.scatter(i, score, color=color, s=70, zorder=3,
                       edgecolors="white", linewidths=0.6)
            ax.text(i, score + 0.25, f"{score:.0f}",
                    ha="center", va="bottom", fontsize=6.5, color=color)

    # ── X-axis labels ──────────────────────────────────────────────────────
    labels = [xtick_label(row) for _, row in block_df.iterrows()]
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(labels, rotation=45, ha="right",
                       fontsize=6.5, linespacing=1.3)

    # ── Axes styling ───────────────────────────────────────────────────────
    ax.set_xlim(-0.7, n - 0.3)
    ax.set_ylim(0, 12)
    ax.set_yticks(range(0, 13, 2))
    ax.set_ylabel("Score", fontsize=9)
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    # ── Best-score right-edge annotation ───────────────────────────────────
    for domain in drawn_domains:
        best = best_score_by_domain[domain]
        color = DOMAIN_COLOR.get(domain, "gray")
        abbr = DOMAIN_ABBR.get(domain, domain[:2].title())
        ax.annotate(f"best {abbr}: {best:.0f}",
                    xy=(n - 0.3, best), xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=6, color=color, va="center")


def build_figure(phase_label: str, phase_df: pd.DataFrame,
                 block_labels: list, best_by_domain: dict,
                 sub: str) -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(22, 6.5))
    fig.suptitle(f"{sub}  —  {phase_label}", fontsize=13,
                 fontweight="bold", y=1.01)

    for ax, blk in zip(axes, block_labels):
        blk_data = phase_df[phase_df["block_label"] == blk].copy()
        plot_block(ax, blk_data, blk, best_by_domain)

    # ── Legend ─────────────────────────────────────────────────────────────
    domain_patches = [
        mpatches.Patch(color=c, label=d.capitalize())
        for d, c in DOMAIN_COLOR.items()
        if d in best_by_domain or any(phase_df["domain"] == d)
    ]
    no_resp = mlines.Line2D([], [], color="crimson", marker="x",
                            linestyle="None", markersize=7,
                            label="No response")
    best_line = mlines.Line2D([], [], color="gray", linestyle="--",
                              linewidth=1.4, label="Best score (per domain)")
    fig.legend(handles=domain_patches + [no_resp, best_line],
               loc="upper right", fontsize=8.5, framealpha=0.9,
               bbox_to_anchor=(1.0, 1.0))

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

    p1_df = df[df["phase"] == "phase_1"].copy()
    p2_df = df[df["phase"] == "phase_2"].copy()

    # Best possible score = max observed per domain across all blocks for that phase
    p1_best = p1_df.groupby("domain")["feedback_score"].max().to_dict()
    p2_best = p2_df.groupby("domain")["feedback_score"].max().to_dict()

    out_dir = ROOT / "data" / sub
    out_dir.mkdir(parents=True, exist_ok=True)

    fig1 = build_figure(
        "Phase 1  (Competence  —  blocks 1 · 3 · 5)",
        p1_df, PHASE1_BLOCK_LABELS, p1_best, sub,
    )
    p1_path = out_dir / "plot_phase1.png"
    fig1.savefig(p1_path, dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print(f"[Phase 1] saved -> {p1_path}")

    fig2 = build_figure(
        "Phase 2  (Synergy  —  blocks 2 · 4 · 6)",
        p2_df, PHASE2_BLOCK_LABELS, p2_best, sub,
    )
    p2_path = out_dir / "plot_phase2.png"
    fig2.savefig(p2_path, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"[Phase 2] saved -> {p2_path}")


if __name__ == "__main__":
    main()
