"""
Usage:
    python analysis/plot_block_LR.py sub-009
    python analysis/plot_block_LR.py 009

Fits a per-phase linear regression of mean_feedback_score over session order
and saves: data/<sub>/plot_block_LR.png
"""

import sys
import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

ROOT = Path(__file__).resolve().parents[1]

PHASE_STYLE = {
    "phase_1": dict(label="Phase 1 (Competence)", color="#4A90D9", marker="o"),
    "phase_2": dict(label="Phase 2 (Synergy)",    color="#E8813A", marker="s"),
}


def fit_lr(x_data, y_data):
    X = np.array(x_data).reshape(-1, 1)
    y = np.array(y_data)
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    return model.coef_[0], model.intercept_, r2_score(y, y_pred), y_pred


def main():
    parser = argparse.ArgumentParser(
        description="Per-phase linear regression of mean feedback score over blocks."
    )
    parser.add_argument("sub", help="Subject ID (e.g. sub-009, 009, or 9)")
    args = parser.parse_args()

    sub = args.sub.strip()
    if not sub.startswith("sub-"):
        sub = f"sub-{sub.zfill(3)}"

    summary_path = ROOT / "data" / sub / "summary.json"
    if not summary_path.exists():
        print(f"[ERROR] File not found: {summary_path}")
        sys.exit(1)

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group blocks by phase, sorted by block index
    phase_blocks: dict[str, list] = {}
    for bname, bdata in sorted(
        data["by_block"].items(), key=lambda kv: int(kv[0].split("_")[1])
    ):
        phase = bdata["phase"]
        phase_blocks.setdefault(phase, []).append((bname, bdata["mean_feedback_score"]))

    fig, ax = plt.subplots(figsize=(8, 5))

    for phase in sorted(phase_blocks.keys()):
        blocks = phase_blocks[phase]
        x_data = list(range(len(blocks)))
        y_data = [score for _, score in blocks]
        block_names = [name for name, _ in blocks]

        slope, intercept, r2, y_pred = fit_lr(x_data, y_data)
        style = PHASE_STYLE.get(phase, dict(label=phase, color="gray", marker="o"))

        legend_label = (
            f"{style['label']}\n"
            f"Y = {slope:.3f}X + {intercept:.3f}  |  $R^2$ = {r2:.3f}"
        )

        ax.scatter(x_data, y_data, color=style["color"], s=80, zorder=3,
                   marker=style["marker"], edgecolors="white", linewidths=0.5)
        ax.plot(x_data, y_pred, color=style["color"], linewidth=2, label=legend_label)

        for xi, (bname, score) in zip(x_data, blocks):
            ax.annotate(bname, (xi, score), textcoords="offset points",
                        xytext=(6, 4), fontsize=8, color=style["color"])

        print(f"\n--- {sub} | {phase} ---")
        print(f"  Blocks : {block_names}")
        print(f"  Scores : {[round(v, 4) for v in y_data]}")
        print(f"  Slope  : {slope:.4f}  Intercept : {intercept:.4f}  R² : {r2:.4f}")
        print(f"  Equation: Y = {slope:.4f} * X + {intercept:.4f}")

    n_sessions = max(len(v) for v in phase_blocks.values())
    ax.set_xticks(range(n_sessions))
    ax.set_xticklabels([f"Session {i + 1}" for i in range(n_sessions)], fontsize=10)
    ax.set_xlabel("Session order within phase", fontsize=11)
    ax.set_ylabel("Mean Feedback Score", fontsize=11)
    ax.set_title(
        f"{sub}  —  Phase 1 vs Phase 2  Linear Regression",
        fontsize=13, fontweight="bold",
    )
    ax.legend(fontsize=9, framealpha=0.9, loc="upper left")
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    out_path = ROOT / "data" / sub / "plot_block_LR.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[saved] {out_path}")


if __name__ == "__main__":
    main()
