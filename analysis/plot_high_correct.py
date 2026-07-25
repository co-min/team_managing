"""
Proportion of trials where the participant chose the highest-scoring pair
(chose_optimal == 1) across blocks, split by phase.

  Phase 1 : block_0 (early) → block_2 (middle) → block_4 (late)
  Phase 2 : block_1 (early) → block_3 (middle) → block_5 (late)

Individual subject trajectories (thin lines) + group mean ± SEM (thick line).

Produces:
  high_correct_rate_by_block.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ANALYSIS_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(ANALYSIS_DIR, "..", "data")
ALL_TRIALS_CSV = os.path.join(DATA_DIR, "all_trials_with_chose_optimal.csv")

PHASE_BLOCKS = {
    "phase_1": ["block_0", "block_2", "block_4"],
    "phase_2": ["block_1", "block_3", "block_5"],
}
STAGE_LABELS = ["Early\n(B0)", "Middle\n(B2)", "Late\n(B4)"]   # updated per phase below
PHASE_LABELS = {"phase_1": "Phase 1", "phase_2": "Phase 2"}
PHASE_COLORS = {"phase_1": "#1f77b4", "phase_2": "#ff7f0e"}


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["chose_optimal"])
    df["chose_optimal"] = df["chose_optimal"].astype(int)
    return df


def compute_block_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Per-subject, per-block proportion of chose_optimal == 1."""
    return (
        df.groupby(["sub_id", "phase", "block"])["chose_optimal"]
        .mean()
        .reset_index()
        .rename(columns={"chose_optimal": "rate"})
    )


def plot_high_correct(df: pd.DataFrame, out_path: str) -> None:
    block_rates = compute_block_rate(df)
    n_subs = df["sub_id"].nunique()

    fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)

    x = np.arange(3)  # 3 blocks per phase

    for ax, (phase, blocks) in zip(axes, PHASE_BLOCKS.items()):
        color = PHASE_COLORS[phase]
        phase_df = block_rates[block_rates["phase"] == phase]

        # pivot: rows = sub_id, cols = block (in order)
        pivot = (
            phase_df.pivot(index="sub_id", columns="block", values="rate")
            .reindex(columns=blocks)
        )

        # individual subject trajectories
        for _, row in pivot.iterrows():
            ax.plot(
                x, row.values,
                "o-", color=color, alpha=0.3, linewidth=1.2, markersize=4, zorder=2,
            )

        # group mean ± SEM
        mean = pivot.mean(axis=0).values
        sem  = pivot.sem(axis=0).values

        ax.plot(
            x, mean,
            "o-", color=color, linewidth=2.8, markersize=9,
            markeredgecolor="white", markeredgewidth=1.5,
            zorder=5, label="Group mean",
        )
        ax.fill_between(
            x, mean - sem, mean + sem,
            color=color, alpha=0.2, zorder=3,
        )
        # SEM error bars on top
        ax.errorbar(
            x, mean, yerr=sem,
            fmt="none", ecolor=color, capsize=5, elinewidth=1.8, zorder=6,
        )

    

        # x-axis labels
        stage_names = [
            f"Early\n({b.replace('block_', 'B')})" for b in blocks
        ]
        stage_names[1] = stage_names[1].replace("Early", "Middle")
        stage_names[2] = stage_names[2].replace("Early", "Late")

        # chance line
        ax.axhline(1/6, color="gray", linestyle="--", linewidth=1.5,
                   alpha=0.6, zorder=1, label="Chance (1/6 ≈ 0.17)")

        ax.set_xticks(x)
        ax.set_xticklabels(stage_names, fontsize=14)
        ax.set_xlim(-0.4, 2.4)
        ax.set_ylim(0, 1.05)
        ax.set_title(PHASE_LABELS[phase], fontsize=18, fontweight="bold")
        ax.set_xlabel("Block (within phase)", fontsize=16)
        ax.tick_params(axis="y", labelsize=13)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("Proportion chose highest-scoring pair", fontsize=16)
    axes[0].legend(loc="upper left", fontsize=12)

    fig.suptitle(
        f"Learning trajectory: % Chose Highest-Score Pair  (n={n_subs} subjects)",
        fontsize=18, fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    df = load_data(ALL_TRIALS_CSV)
    print(f"Loaded {len(df)} trials from {df['sub_id'].nunique()} subjects")

    plot_high_correct(
        df,
        os.path.join(ANALYSIS_DIR, "high_correct_rate_by_block.png"),
    )
