"""
Usage:
    python analysis/plot_trial_LR.py sub-009
    python analysis/plot_trial_LR.py 009

Plots cumulative feedback score over trials for Phase 1 and Phase 2.
Each phase is shown in its own subplot. A dashed line marks 80% of the
final (maximum) cumulative score for that phase.

Saves: data/<sub>/plot_trial_LR.png
"""

import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

PHASE_STYLE = {
    "phase_1": {"color": "#4A90D9", "label": "Phase 1  (Competence)"},
    "phase_2": {"color": "#E8813A", "label": "Phase 2  (Synergy)"},
}

OLD_FMT_BLOCK = {
    ("phase_1", "cooking"):   1,
    ("phase_1", "repairing"): 3,
    ("phase_1", "tennis"):    5,
    ("phase_2", "cooking"):   2,
    ("phase_2", "repairing"): 4,
    ("phase_2", "tennis"):    6,
}


def assign_block_label(df: pd.DataFrame) -> pd.DataFrame:
    sid = df["stim_pair_id"].astype(str)
    new_label = pd.to_numeric(sid.str.extract(r"^block(\d+)_", expand=False), errors="coerce") + 1
    old_label = pd.Series(zip(df["phase"], df["domain"]), index=df.index).map(OLD_FMT_BLOCK)
    df = df.copy()
    df["block_label"] = new_label.combine_first(old_label)
    return df[df["block_label"].notna()].copy()


def plot_phase(ax, phase_df: pd.DataFrame, phase_key: str):
    style = PHASE_STYLE[phase_key]
    color = style["color"]

    phase_df = phase_df.sort_values("global_trial_id").reset_index(drop=True)
    phase_df["cumulative_score"] = phase_df["feedback_score"].cumsum()

    x = np.arange(1, len(phase_df) + 1)
    y = phase_df["cumulative_score"].values
    max_cum = y[-1]
    threshold = max_cum * 0.8

    # Find the first trial where cumulative score crosses 80%
    cross_idx = np.searchsorted(y, threshold)

    ax.plot(x, y, color=color, linewidth=2, label=f"Cumulative score\n(final = {max_cum:.1f})")
    ax.scatter(x, y, color=color, s=30, zorder=4, edgecolors="white", linewidths=0.5)

    # 80% threshold dashed line
    ax.axhline(threshold, color=color, linewidth=1.4, linestyle="--", alpha=0.75,
               label=f"80% of max  ({threshold:.1f})")

    # Annotate the crossing point if it exists within range
    if cross_idx < len(x):
        ax.axvline(x[cross_idx], color=color, linewidth=1.0, linestyle=":", alpha=0.6)
        ax.annotate(
            f"Trial {x[cross_idx]}",
            xy=(x[cross_idx], threshold),
            xytext=(6, 6), textcoords="offset points",
            fontsize=8, color=color,
            arrowprops=dict(arrowstyle="-", color=color, alpha=0.5),
        )

    # Block boundary shading
    if "block_label" in phase_df.columns:
        block_changes = phase_df["block_label"].ne(phase_df["block_label"].shift()).to_numpy()
        block_starts = np.where(block_changes)[0]
        for i, start in enumerate(block_starts):
            end = block_starts[i + 1] if i + 1 < len(block_starts) else len(x)
            if i % 2 == 1:
                ax.axvspan(x[start] - 0.5, x[end - 1] + 0.5, alpha=0.06, color=color, zorder=0)
            blk_label = phase_df["block_label"].iloc[start]
            ax.text((x[start] + x[end - 1]) / 2, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
                    f"Blk {int(blk_label)}", ha="center", fontsize=7, color="gray", va="bottom")

    ax.set_title(f"{style['label']}", fontsize=12, fontweight="bold")
    ax.set_xlabel("Trial", fontsize=10)
    ax.set_ylabel("Cumulative Score", fontsize=10)
    ax.set_xlim(0.5, len(x) + 0.5)
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8.5, framealpha=0.9, loc="upper left")
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    print(f"  [{phase_key}] {len(x)} trials | final cumulative: {max_cum:.2f} | "
          f"80% threshold: {threshold:.2f} | reached at trial: "
          f"{x[cross_idx] if cross_idx < len(x) else 'N/A'}")


def main():
    parser = argparse.ArgumentParser(
        description="Cumulative score over trials, split by phase."
    )
    parser.add_argument("sub", help="Subject ID (e.g. sub-009, 009, or 9)")
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

    print(f"--- 피험자 {sub} 누적 점수 분석 ---")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle(f"{sub}  —  Cumulative Feedback Score by Trial",
                 fontsize=13, fontweight="bold", y=1.02)

    for ax, phase_key in zip(axes, ["phase_1", "phase_2"]):
        phase_df = df[df["phase"] == phase_key].copy()
        if phase_df.empty:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=11, color="gray")
            ax.set_axis_off()
            continue
        plot_phase(ax, phase_df, phase_key)

    # Align y-axes to same scale for direct comparison
    ymax = max(ax.get_ylim()[1] for ax in axes)
    for ax in axes:
        ax.set_ylim(bottom=0, top=ymax)

    # Re-draw block labels now that ylim is fixed
    for ax, phase_key in zip(axes, ["phase_1", "phase_2"]):
        phase_df = df[df["phase"] == phase_key].copy()
        if phase_df.empty or "block_label" not in phase_df.columns:
            continue
        phase_df = phase_df.sort_values("global_trial_id").reset_index(drop=True)
        x = np.arange(1, len(phase_df) + 1)
        block_changes = phase_df["block_label"].ne(phase_df["block_label"].shift()).to_numpy()
        block_starts = np.where(block_changes)[0]
        for i, start in enumerate(block_starts):
            end = block_starts[i + 1] if i + 1 < len(block_starts) else len(x)
            blk_label = phase_df["block_label"].iloc[start]
            ax.text((x[start] + x[end - 1]) / 2, ymax * 0.98,
                    f"Blk {int(blk_label)}", ha="center", fontsize=7,
                    color="gray", va="top")

    plt.tight_layout()
    out_path = ROOT / "data" / sub / "plot_trial_LR.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[saved] {out_path}")


if __name__ == "__main__":
    main()
