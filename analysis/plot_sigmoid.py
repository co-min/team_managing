"""
Usage:
    python analysis/plot_sigmoid.py sub-001
    python analysis/plot_sigmoid.py 001

Fits a sigmoid curve to normalized trial scores (score / 12, range 0-1)
over trial order within each phase. Phase 1 and Phase 2 are analyzed separately.

Two PNG files are saved to data/<sub>/:
  plot_sigmoid_phase1.png
  plot_sigmoid_phase2.png

Sigmoid model:  f(x) = L / (1 + exp(-k*(x - x0))) + b
  L  : amplitude  (ceiling - floor)
  x0 : inflection point (trial index)
  k  : steepness
  b  : baseline (floor)
"""

import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[1]

SCORE_MAX = 12.0

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
        "key":   "phase_1",
        "title": "Phase 1  (Competence  —  blocks 1 · 3 · 5)",
        "file":  "plot_sigmoid_phase1.png",
    },
    {
        "key":   "phase_2",
        "title": "Phase 2  (Synergy  —  blocks 2 · 4 · 6)",
        "file":  "plot_sigmoid_phase2.png",
    },
]


def assign_block_label(df: pd.DataFrame) -> pd.DataFrame:
    sid = df["stim_pair_id"].astype(str)
    new_label = pd.to_numeric(sid.str.extract(r"^block(\d+)_", expand=False), errors="coerce") + 1
    old_label = pd.Series(zip(df["phase"], df["domain"]), index=df.index).map(OLD_FMT_BLOCK)
    df = df.copy()
    df["block_label"] = new_label.combine_first(old_label)
    return df[df["block_label"].notna()].copy()


def sigmoid(x, L, x0, k, b):
    return L / (1 + np.exp(-k * (x - x0))) + b


def fit_sigmoid(x: np.ndarray, y: np.ndarray):
    """Return (popt, r2) or (None, None) on failure."""
    p0 = [max(y) - min(y), np.median(x), 0.1, min(y)]
    bounds = (
        [0,    x.min(), -5, 0],
        [1.05, x.max(),  5, 1],
    )
    try:
        popt, _ = curve_fit(sigmoid, x, y, p0=p0, bounds=bounds, maxfev=20000)
        y_pred = sigmoid(x, *popt)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        return popt, r2
    except (RuntimeError, ValueError):
        return None, None


def plot_phase(phase_df: pd.DataFrame, phase: dict, sub: str, out_dir: Path):
    phase_df = phase_df.dropna(subset=["feedback_score"]).reset_index(drop=True)

    if phase_df.empty:
        print(f"[{phase['key']}] No data — skipped")
        return

    phase_df["norm_score"] = phase_df["feedback_score"] / SCORE_MAX
    x = np.arange(len(phase_df), dtype=float)
    y = phase_df["norm_score"].values

    popt, r2 = fit_sigmoid(x, y)

    fig, ax = plt.subplots(figsize=(11, 5))

    # Scatter: color by domain
    for i, row in phase_df.iterrows():
        color = DOMAIN_COLOR.get(row["domain"], "gray")
        ax.scatter(i, row["norm_score"], color=color, s=65, zorder=3,
                   edgecolors="white", linewidths=0.6)

    # Block boundary lines
    if "block_label" in phase_df.columns:
        block_edges = phase_df.groupby("block_label").apply(lambda g: g.index.max()).sort_values()
        for blk, edge in block_edges.items():
            if edge < len(phase_df) - 1:
                ax.axvline(edge + 0.5, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)
            mid = phase_df[phase_df["block_label"] == blk].index
            if len(mid):
                ax.text(mid.to_numpy().mean(), 1.04, f"Blk {int(blk)}",
                        ha="center", fontsize=7.5, color="gray")

    # Sigmoid fit
    if popt is not None:
        x_fine = np.linspace(x.min(), x.max(), 400)
        y_fit = sigmoid(x_fine, *popt)
        L, x0, k, b = popt
        label = (
            f"Sigmoid fit  ($R^2$={r2:.3f})\n"
            f"L={L:.2f}, $x_0$={x0:.1f}, k={k:.3f}, b={b:.2f}"
        )
        ax.plot(x_fine, y_fit, color="#333333", linewidth=2, zorder=4, label=label)
        ax.axvline(x0, color="#333333", linestyle="--", alpha=0.35, linewidth=1)
        ax.annotate(f"$x_0$={x0:.1f}", xy=(x0, sigmoid(x0, *popt)),
                    xytext=(6, 6), textcoords="offset points",
                    fontsize=8, color="#333333")
    else:
        print(f"[{phase['key']}] Sigmoid fit did not converge")

    # Legend
    domain_patches = [
        mpatches.Patch(color=c, label=f"{d.capitalize()} ({DOMAIN_ABBR[d]})")
        for d, c in DOMAIN_COLOR.items()
        if (phase_df["domain"] == d).any()
    ]
    handles = domain_patches
    if popt is not None:
        import matplotlib.lines as mlines
        handles += [mlines.Line2D([], [], color="#333333", linewidth=2, label=label)]
    ax.legend(handles=handles, fontsize=8.5, framealpha=0.9, loc="lower right")

    ax.set_xlim(-1, len(phase_df))
    ax.set_ylim(-0.05, 1.12)
    ax.set_xlabel("Trial (within phase)", fontsize=11)
    ax.set_ylabel("Normalized Score  (feedback_score / 12)", fontsize=11)
    ax.set_title(f"{sub}  —  {phase['title']}  |  Sigmoid Fit", fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.3, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    out_path = out_dir / phase["file"]
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[{phase['key']}] saved -> {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Sigmoid fit on normalized trial scores (0-1) by phase."
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
        plot_phase(phase_df, phase, sub, out_dir)


if __name__ == "__main__":
    main()