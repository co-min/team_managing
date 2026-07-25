"""
Reaction time (rt_choice1 + rt_choice2) comparison: bad score vs good score trials.

  - Good score : chose_optimal == 1  (picked the true ground-truth optimal pair)
  - Bad score  : chose_optimal == 0
  - RT         : total decision time = rt_choice1 + rt_choice2
  - Blocks run 0-5 (phase_1: 0,2,4 / phase_2: 1,3,5) interleaved

Produces four figures:
  rt_good_vs_bad.png       — bar + violin by score type x phase, individual dots
  rt_per_subject.png       — paired per-subject mean RT (bad vs good), per phase
  rt_by_block.png          — RT line plot across block 0-5, good vs bad, ± SEM
  rt_per_subject_block.png — per-subject lines across blocks, good vs bad
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(ANALYSIS_DIR, "..", "data")
ALL_TRIALS_CSV = os.path.join(DATA_DIR, "all_trials_with_chose_optimal.csv")

# Outlier RT cap (seconds).  Trials above this are excluded.
RT_CAP = 30.0

PHASE_LABELS  = {"phase_1": "Phase 1", "phase_2": "Phase 2"}
SCORE_COLORS  = {"good": "#2ca02c", "bad": "#d62728"}
PHASE_COLORS  = {"phase_1": "#1f77b4", "phase_2": "#ff7f0e"}

# Block chronological order and their phase membership
BLOCK_ORDER = ["block_0", "block_1", "block_2", "block_3", "block_4", "block_5"]
BLOCK_PHASE  = {
    "block_0": "phase_1", "block_2": "phase_1", "block_4": "phase_1",
    "block_1": "phase_2", "block_3": "phase_2", "block_5": "phase_2",
}

# Within-phase session index (0-2) for linear regression x-axis
BLOCK_SESSION = {
    "block_0": 0, "block_2": 1, "block_4": 2,
    "block_1": 0, "block_3": 1, "block_5": 2,
}

# Style for the 4 regression lines (phase × score_type)
LR_LINE_STYLE = {
    ("phase_1", "good"): dict(color="#4A90D9", linestyle="-",  marker="o", label="Phase 1 – Optimal"),
    ("phase_1", "bad"):  dict(color="#4A90D9", linestyle="--", marker="s", label="Phase 1 – Suboptimal"),
    ("phase_2", "good"): dict(color="#E8813A", linestyle="-",  marker="o", label="Phase 2 – Optimal"),
    ("phase_2", "bad"):  dict(color="#E8813A", linestyle="--", marker="s", label="Phase 2 – Suboptimal"),
}

# ---------------------------------------------------------------------------
# Statistical helper
# ---------------------------------------------------------------------------
def sig_stars(p: float) -> str:
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    else:
        return "ns"


def add_sig_bracket(ax, x1: float, x2: float, y_top: float,
                    t_stat: float, p_val: float,
                    h: float = 0.4, fontsize: int = 13) -> float:
    """Draw a paired-test significance bracket between x1 and x2.

    Returns the y coordinate of the top of the bracket (useful for setting ylim).
    """
    stars = sig_stars(p_val)
    if p_val < 0.05:
        label = f"{stars}  t={t_stat:.2f}, p={p_val:.3f}"
    else:
        label = f"ns  t={t_stat:.2f}, p={p_val:.3f}"

    y_line = y_top
    y_text = y_top + h * 0.3

    ax.plot([x1, x1, x2, x2],
            [y_line, y_line + h * 0.5, y_line + h * 0.5, y_line],
            lw=1.8, color="black", clip_on=False)
    ax.text((x1 + x2) / 2, y_text + h * 0.5, label,
            ha="center", va="bottom", fontsize=fontsize,
            color="black", clip_on=False)

    return y_text + h * 0.5


# ---------------------------------------------------------------------------
# 1. Load & preprocess
# ---------------------------------------------------------------------------
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Drop rows without valid RTs or chose_optimal label
    df = df.dropna(subset=["rt_choice1", "rt_choice2", "chose_optimal"])
    df["chose_optimal"] = df["chose_optimal"].astype(int)

    # Total RT = first choice + second choice
    df["rt_total"] = df["rt_choice1"] + df["rt_choice2"]

    # Remove extreme RT outliers based on total RT
    df = df[df["rt_total"] <= RT_CAP].copy()

    # Score-quality label
    df["score_type"] = df["chose_optimal"].map({1: "good", 0: "bad"})

    return df


# ---------------------------------------------------------------------------
# 2. Per-subject mean RT (bad / good) per phase
# ---------------------------------------------------------------------------
def subject_means(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby(["sub_id", "phase", "score_type"])["rt_total"]
        .mean()
        .reset_index()
        .rename(columns={"rt_total": "mean_rt"})
    )
    return agg


def subject_means_block(df: pd.DataFrame) -> pd.DataFrame:
    """Per-subject mean RT grouped by block × score_type."""
    agg = (
        df.groupby(["sub_id", "block", "score_type"])["rt_total"]
        .mean()
        .reset_index()
        .rename(columns={"rt_total": "mean_rt"})
    )
    return agg


# ---------------------------------------------------------------------------
# 3. Figure A — bar+violin: RT by score_type × phase  (+paired t-test brackets)
# ---------------------------------------------------------------------------
def plot_rt_by_score_and_phase(df: pd.DataFrame, out_path: str) -> None:
    phases      = ["phase_1", "phase_2"]
    score_types = ["bad", "good"]

    # Group positions
    n_phases     = len(phases)
    group_width  = 0.35          # width of each score-type bar within a phase group
    gap          = 0.15          # gap between score-type bars within a phase
    phase_step   = 1.0           # distance between phase centres

    centres = np.arange(n_phases) * phase_step
    offsets = {
        "bad":  -group_width / 2,
        "good":  group_width / 2,
    }

    sub_means = subject_means(df)

    fig, ax = plt.subplots(figsize=(8, 6))

    bar_tops = {}  # (pi, st) -> bar top for bracket positioning

    for pi, phase in enumerate(phases):
        phase_subs = sub_means[sub_means["phase"] == phase]

        for st in score_types:
            xc   = centres[pi] + offsets[st]
            vals = phase_subs[phase_subs["score_type"] == st]["mean_rt"].values

            if len(vals) == 0:
                continue

            mean_ = vals.mean()
            sem_  = vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0

            bar_tops[(pi, st)] = mean_ + sem_

            # Bar
            ax.bar(
                xc, mean_,
                width=group_width - gap,
                color=SCORE_COLORS[st],
                alpha=0.75,
                yerr=sem_,
                capsize=5,
                error_kw={"linewidth": 1.5, "ecolor": "black"},
                label=f"{'Bad score (suboptimal)' if st == 'bad' else 'Good score (optimal)'}"
                      if pi == 0 else "_nolegend_",
                zorder=2,
            )

            # Violin overlay
            if len(vals) >= 3:
                parts = ax.violinplot(
                    vals,
                    positions=[xc],
                    widths=group_width - gap,
                    showmeans=False,
                    showmedians=True,
                    showextrema=False,
                )
                for pc in parts["bodies"]:
                    pc.set_facecolor(SCORE_COLORS[st])
                    pc.set_alpha(0.25)
                    pc.set_edgecolor("none")
                parts["cmedians"].set_color("black")
                parts["cmedians"].set_linewidth(1.5)

            # Individual subject dots
            jitter = np.random.default_rng(42).uniform(-0.06, 0.06, len(vals))
            ax.scatter(
                np.full(len(vals), xc) + jitter,
                vals,
                color=SCORE_COLORS[st],
                edgecolors="white",
                s=55,
                linewidths=0.8,
                zorder=5,
            )

    # Connect paired subject dots (bad → good) per phase
    for pi, phase in enumerate(phases):
        phase_subs = sub_means[sub_means["phase"] == phase]
        paired = phase_subs.pivot(index="sub_id", columns="score_type", values="mean_rt").dropna()
        for _, row in paired.iterrows():
            xb = centres[pi] + offsets["bad"]
            xg = centres[pi] + offsets["good"]
            ax.plot(
                [xb, xg], [row["bad"], row["good"]],
                color="gray", alpha=0.35, linewidth=1, zorder=3,
            )

    # --- Paired t-test brackets ---
    y_bracket_starts = []
    phase_results = {}
    for pi, phase in enumerate(phases):
        phase_subs = sub_means[sub_means["phase"] == phase]
        paired = phase_subs.pivot(index="sub_id", columns="score_type", values="mean_rt").dropna()

        if len(paired) >= 2 and "bad" in paired.columns and "good" in paired.columns:
            bad_v  = paired["bad"].values
            good_v = paired["good"].values
            t_stat, p_val = stats.ttest_rel(bad_v, good_v)
            phase_results[phase] = (t_stat, p_val, len(paired))

            xb = centres[pi] + offsets["bad"]
            xg = centres[pi] + offsets["good"]

            # bracket starts just above the highest visible data point in this phase
            y_start = max(bad_v.max(), good_v.max()) + 0.5
            y_bracket_starts.append(y_start)

            y_end = add_sig_bracket(ax, xb, xg, y_start, t_stat, p_val,
                                    h=0.6, fontsize=13)

    # Extend ylim to show brackets
    if y_bracket_starts:
        ax.set_ylim(bottom=0, top=max(y_bracket_starts) + 2.5)

    # Axes decoration
    ax.set_xticks(centres)
    ax.set_xticklabels([PHASE_LABELS[p] for p in phases], fontsize=16)
    ax.set_ylabel("Mean RT – total (choice1 + choice2, s)", fontsize=16)
    ax.set_title(
        f"Reaction Time: Bad vs Good Score\n"
        f"(RT cap {RT_CAP}s, n={df['sub_id'].nunique()} subjects)",
        fontsize=21,
        fontweight="bold",
    )
    ax.tick_params(axis="y", labelsize=14)
    ax.grid(axis="y", alpha=0.3)

    # Legend — placed below the x-axis to avoid overlap with significance brackets
    legend_patches = [
        mpatches.Patch(color=SCORE_COLORS["bad"],  label="Bad score (suboptimal)"),
        mpatches.Patch(color=SCORE_COLORS["good"], label="Good score (optimal)"),
    ]
    ax.legend(handles=legend_patches, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), fontsize=14, ncol=2, frameon=True)

    fig.tight_layout(rect=[0, 0.10, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")

    # Print bracket stats
    print("\n--- Paired t-test (bad vs good RT) per phase ---")
    for phase, (t, p, n) in phase_results.items():
        w_stat, w_p = stats.wilcoxon(
            subject_means(df).query(f"phase == '{phase}' and score_type == 'bad'")["mean_rt"].values,
            subject_means(df).query(f"phase == '{phase}' and score_type == 'good'")["mean_rt"].values,
        )
        print(f"  {PHASE_LABELS[phase]}  n={n}: "
              f"paired t({n-1})={t:.3f}, p={p:.4f} {sig_stars(p)}  |  "
              f"Wilcoxon W={w_stat:.1f}, p={w_p:.4f} {sig_stars(w_p)}")


# ---------------------------------------------------------------------------
# 4. Figure B — per-subject paired lines (bad vs good), faceted by phase
# ---------------------------------------------------------------------------
def plot_rt_per_subject(df: pd.DataFrame, out_path: str) -> None:
    sub_means = subject_means(df)
    phases    = ["phase_1", "phase_2"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 6), sharey=True)

    for ax, phase in zip(axes, phases):
        phase_df = sub_means[sub_means["phase"] == phase]
        pivot    = phase_df.pivot(index="sub_id", columns="score_type", values="mean_rt").dropna()

        for _, row in pivot.iterrows():
            ax.plot(
                [0, 1], [row["bad"], row["good"]],
                "o-", color="steelblue", alpha=0.55, linewidth=1.2, markersize=5,
            )

        # Group means
        gm = pivot.mean()
        ge = pivot.sem()
        ax.errorbar(
            [0, 1], [gm.get("bad", np.nan), gm.get("good", np.nan)],
            yerr=[ge.get("bad", np.nan), ge.get("good", np.nan)],
            fmt="D-", color="black", linewidth=2.5, markersize=8,
            capsize=5, zorder=10, label="Group mean ± SEM",
        )

        # Paired t-test annotation
        if len(pivot) >= 2 and "bad" in pivot.columns and "good" in pivot.columns:
            t_stat, p_val = stats.ttest_rel(pivot["bad"].values, pivot["good"].values)
            stars = sig_stars(p_val)
            ax.text(
                0.5, 0.97,
                f"paired t({len(pivot)-1})={t_stat:.2f}\np={p_val:.3f}  {stars}",
                ha="center", va="top", transform=ax.transAxes,
                fontsize=13, color="black",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
            )

        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Bad score\n(suboptimal)", "Good score\n(optimal)"], fontsize=14)
        ax.set_title(PHASE_LABELS[phase], fontsize=16)
        ax.tick_params(axis="y", labelsize=14)
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)

    axes[0].set_ylabel("Mean RT – total (choice1 + choice2, s)", fontsize=15)
    axes[0].legend(loc="upper right", fontsize=12)

    fig.suptitle(
        f"Per-subject RT: Bad vs Good Score  (n={df['sub_id'].nunique()})",
        fontsize=16,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 5. Figure C — line plot: mean RT across blocks 0-5, good vs bad ± SEM
# ---------------------------------------------------------------------------
def plot_rt_by_block(df: pd.DataFrame, out_path: str) -> None:
    sub_means = subject_means_block(df)
    xs = np.arange(len(BLOCK_ORDER))

    fig, ax = plt.subplots(figsize=(10, 6))

    # Phase background shading
    phase1_xs = [i for i, b in enumerate(BLOCK_ORDER) if BLOCK_PHASE[b] == "phase_1"]
    phase2_xs = [i for i, b in enumerate(BLOCK_ORDER) if BLOCK_PHASE[b] == "phase_2"]
    for xi in phase1_xs:
        ax.axvspan(xi - 0.45, xi + 0.45, color=PHASE_COLORS["phase_1"], alpha=0.10, zorder=0)
    for xi in phase2_xs:
        ax.axvspan(xi - 0.45, xi + 0.45, color=PHASE_COLORS["phase_2"], alpha=0.10, zorder=0)

    for st in ["bad", "good"]:
        means, sems = [], []
        for blk in BLOCK_ORDER:
            vals = sub_means[
                (sub_means["block"] == blk) & (sub_means["score_type"] == st)
            ]["mean_rt"].values
            if len(vals) == 0:
                means.append(np.nan)
                sems.append(np.nan)
            else:
                means.append(np.nanmean(vals))
                sems.append(np.nanstd(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)

        means = np.array(means)
        sems  = np.array(sems)

        ax.errorbar(
            xs, means, yerr=sems,
            fmt="o-",
            color=SCORE_COLORS[st],
            linewidth=2,
            markersize=8,
            capsize=4,
            label=f"{'Optimal' if st == 'good' else 'Suboptimal'} (mean ± SEM)",
            zorder=3,
        )

        # Individual subject dots (jittered)
        rng = np.random.default_rng(42)
        for xi, blk in enumerate(BLOCK_ORDER):
            vals = sub_means[
                (sub_means["block"] == blk) & (sub_means["score_type"] == st)
            ]["mean_rt"].values
            jitter = rng.uniform(-0.12, 0.12, len(vals))
            ax.scatter(
                xi + jitter, vals,
                color=SCORE_COLORS[st], alpha=0.35, s=28,
                edgecolors="none", zorder=2,
            )

    ax.text(np.mean(phase1_xs), 1.01, "Phase 1",
            ha="center", va="bottom",
            color=PHASE_COLORS["phase_1"], fontsize=14, fontweight="bold",
            transform=ax.get_xaxis_transform(), clip_on=False)
    ax.text(np.mean(phase2_xs), 1.01, "Phase 2",
            ha="center", va="bottom",
            color=PHASE_COLORS["phase_2"], fontsize=14, fontweight="bold",
            transform=ax.get_xaxis_transform(), clip_on=False)

    ax.set_xticks(xs)
    ax.set_xticklabels([f"Block {i}" for i in range(len(BLOCK_ORDER))], fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax.set_ylabel("Mean RT – total (choice1 + choice2, s)", fontsize=15)
    ax.set_xlabel("Block", fontsize=15)
    ax.set_title(
        f"RT across Blocks: Optimal vs Suboptimal choices\n"
        f"(RT cap {RT_CAP}s, n={df['sub_id'].nunique()} subjects)",
        fontsize=16,
    )
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=13)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 6. Figure D — per-subject lines across blocks, good vs bad
# ---------------------------------------------------------------------------
def plot_rt_per_subject_block(df: pd.DataFrame, out_path: str) -> None:
    sub_means = subject_means_block(df)
    subjects  = sorted(df["sub_id"].unique())
    xs        = np.arange(len(BLOCK_ORDER))

    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharey=True, sharex=True)
    axes_flat = axes.flatten()

    for ai, sub in enumerate(subjects):
        ax  = axes_flat[ai]
        sdf = sub_means[sub_means["sub_id"] == sub]

        for st in ["bad", "good"]:
            vals = [
                sdf[(sdf["block"] == blk) & (sdf["score_type"] == st)]["mean_rt"].values
                for blk in BLOCK_ORDER
            ]
            ys = np.array([v[0] if len(v) > 0 else np.nan for v in vals])
            ax.plot(xs, ys, "o-", color=SCORE_COLORS[st],
                    linewidth=1.8, markersize=6, alpha=0.85,
                    label=("Optimal" if st == "good" else "Suboptimal"))

        # Phase background
        for xi, blk in enumerate(BLOCK_ORDER):
            color = PHASE_COLORS[BLOCK_PHASE[blk]]
            ax.axvspan(xi - 0.45, xi + 0.45, color=color, alpha=0.08, zorder=0)

        ax.set_title(sub, fontsize=12)
        ax.set_xticks(xs)
        ax.set_xticklabels([str(i) for i in range(len(BLOCK_ORDER))], fontsize=11)
        ax.tick_params(axis="y", labelsize=11)
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)

    # Hide unused panels
    for ai in range(len(subjects), len(axes_flat)):
        axes_flat[ai].set_visible(False)

    axes[0][0].set_ylabel("Mean RT (s)", fontsize=13)
    axes[1][0].set_ylabel("Mean RT (s)", fontsize=13)

    legend_patches = [
        mpatches.Patch(color=SCORE_COLORS["bad"],  label="Suboptimal"),
        mpatches.Patch(color=SCORE_COLORS["good"], label="Optimal"),
        mpatches.Patch(color=PHASE_COLORS["phase_1"], alpha=0.3, label="Phase 1"),
        mpatches.Patch(color=PHASE_COLORS["phase_2"], alpha=0.3, label="Phase 2"),
    ]
    fig.legend(handles=legend_patches, loc="lower right", fontsize=12, ncol=2)
    fig.supxlabel("Block (0–5)", fontsize=14)
    fig.suptitle(
        f"Per-subject RT across Blocks  (n={df['sub_id'].nunique()})",
        fontsize=16,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 7. Figure E — Linear regression: RT across sessions, phase × score_type
# ---------------------------------------------------------------------------
def plot_rt_lr_by_phase_score(df: pd.DataFrame, out_path: str) -> None:
    sub_means = subject_means_block(df)
    sub_means["session_idx"] = sub_means["block"].map(BLOCK_SESSION)
    sub_means["phase"]       = sub_means["block"].map(BLOCK_PHASE)

    xs = np.array([0, 1, 2])
    fig, ax = plt.subplots(figsize=(9, 6))

    for (phase, st), style in LR_LINE_STYLE.items():
        grp = sub_means[(sub_means["phase"] == phase) & (sub_means["score_type"] == st)]

        # Individual subject lines (faint background)
        for _, sdf in grp.groupby("sub_id"):
            sdf_s = sdf.sort_values("session_idx")
            ax.plot(
                sdf_s["session_idx"], sdf_s["mean_rt"],
                color=style["color"], linestyle=style["linestyle"],
                alpha=0.15, linewidth=0.9, zorder=1,
            )

        # Group mean ± SEM per session
        means, sems = [], []
        for xi in xs:
            vals = grp[grp["session_idx"] == xi]["mean_rt"].dropna().values
            means.append(np.nanmean(vals) if len(vals) > 0 else np.nan)
            sems.append(np.nanstd(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
        means = np.array(means)
        sems  = np.array(sems)

        # Linear regression over group means
        valid = ~np.isnan(means)
        if valid.sum() >= 2:
            slope, intercept, r, p, _ = stats.linregress(xs[valid], means[valid])
            y_pred = slope * xs + intercept
            eq_label = (
                f"{style['label']}\n"
                f"β={slope:+.3f}, R²={r**2:.3f}, p={p:.3f}"
            )
        else:
            y_pred = means
            eq_label = style["label"]

        # Regression line
        ax.plot(
            xs, y_pred,
            color=style["color"], linestyle=style["linestyle"],
            linewidth=2, zorder=3,
        )

        # Group mean dots + error bars
        ax.errorbar(
            xs, means, yerr=sems,
            fmt=style["marker"],
            color=style["color"],
            markersize=8, capsize=4,
            elinewidth=1.5, linewidth=0,
            markeredgecolor="white", markeredgewidth=0.6,
            label=eq_label, zorder=4,
        )

    ax.set_xticks(xs)
    ax.set_xticklabels(["Session 1", "Session 2", "Session 3"], fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax.set_xlabel("Session order within phase", fontsize=15)
    ax.set_ylabel("Mean RT – total (choice1 + choice2, s)", fontsize=15)
    ax.set_title(
        f"RT Linear Regression: Phase × Score Type\n"
        f"(RT cap {RT_CAP}s, n={df['sub_id'].nunique()} subjects)",
        fontsize=16,
    )
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=11, framealpha=0.9, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 8. Normalized RT linear regression (per-subject z-score)
# ---------------------------------------------------------------------------
def normalize_rt_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Z-score rt_total per subject using each subject's global mean and SD."""
    df = df.copy()
    stats_per_sub = df.groupby("sub_id")["rt_total"].agg(["mean", "std"])
    df = df.join(stats_per_sub.rename(columns={"mean": "_mu", "std": "_sd"}), on="sub_id")
    df["rt_norm"] = (df["rt_total"] - df["_mu"]) / df["_sd"]
    df = df.drop(columns=["_mu", "_sd"])
    return df


def subject_means_block_norm(df: pd.DataFrame) -> pd.DataFrame:
    """Per-subject mean normalized RT grouped by block × score_type."""
    agg = (
        df.groupby(["sub_id", "block", "score_type"])["rt_norm"]
        .mean()
        .reset_index()
        .rename(columns={"rt_norm": "mean_rt"})
    )
    return agg


def plot_rt_lr_normalized(df: pd.DataFrame, out_path: str) -> None:
    df_norm    = normalize_rt_zscore(df)
    sub_means  = subject_means_block_norm(df_norm)
    sub_means["session_idx"] = sub_means["block"].map(BLOCK_SESSION)
    sub_means["phase"]       = sub_means["block"].map(BLOCK_PHASE)

    xs = np.array([0, 1, 2])
    fig, ax = plt.subplots(figsize=(9, 6))

    for (phase, st), style in LR_LINE_STYLE.items():
        grp = sub_means[(sub_means["phase"] == phase) & (sub_means["score_type"] == st)]

        for _, sdf in grp.groupby("sub_id"):
            sdf_s = sdf.sort_values("session_idx")
            ax.plot(
                sdf_s["session_idx"], sdf_s["mean_rt"],
                color=style["color"], linestyle=style["linestyle"],
                alpha=0.15, linewidth=0.9, zorder=1,
            )

        means, sems = [], []
        for xi in xs:
            vals = grp[grp["session_idx"] == xi]["mean_rt"].dropna().values
            means.append(np.nanmean(vals) if len(vals) > 0 else np.nan)
            sems.append(np.nanstd(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
        means = np.array(means)
        sems  = np.array(sems)

        valid = ~np.isnan(means)
        if valid.sum() >= 2:
            slope, intercept, r, p, _ = stats.linregress(xs[valid], means[valid])
            y_pred = slope * xs + intercept
            eq_label = (
                f"{style['label']}\n"
                f"β={slope:+.3f}, R²={r**2:.3f}, p={p:.3f}"
            )
        else:
            y_pred = means
            eq_label = style["label"]

        ax.plot(
            xs, y_pred,
            color=style["color"], linestyle=style["linestyle"],
            linewidth=2, zorder=3,
        )
        ax.errorbar(
            xs, means, yerr=sems,
            fmt=style["marker"],
            color=style["color"],
            markersize=8, capsize=4,
            elinewidth=1.5, linewidth=0,
            markeredgecolor="white", markeredgewidth=0.6,
            label=eq_label, zorder=4,
        )

    ax.axhline(0, color="gray", linewidth=0.8, linestyle=":")
    ax.set_xticks(xs)
    ax.set_xticklabels(["Early\n(Session 1)", "Middle\n(Session 2)", "Late\n(Session 3)"], fontsize=14)
    ax.tick_params(axis="y", labelsize=14)
    ax.set_xlabel("Session order within phase", fontsize=15)
    ax.set_ylabel("Normalized RT (z-score per subject)", fontsize=15)
    ax.set_title(
        f"RT Linear Regression (Normalized): Phase × Score Type\n"
        f"(RT cap {RT_CAP}s, n={df['sub_id'].nunique()} subjects, per-subject z-score)",
        fontsize=16,
    )
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=11, framealpha=0.9, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 9. Summary statistics  (with paired t-test + Wilcoxon per phase)
# ---------------------------------------------------------------------------
def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print("RT summary (mean ± SD) by score_type × phase")
    print("=" * 70)
    summary = (
        df.groupby(["phase", "score_type"])["rt_total"]
        .agg(n="count", mean="mean", std="std", median="median")
        .round(3)
    )
    print(summary.to_string())

    print("\n--- Per-subject means ---")
    sm = subject_means(df)
    pivot = sm.pivot_table(index=["sub_id", "phase"], columns="score_type", values="mean_rt")
    pivot["diff (bad-good)"] = pivot.get("bad", np.nan) - pivot.get("good", np.nan)
    print(pivot.round(3).to_string())

    print("\n--- Paired t-test & Wilcoxon signed-rank (bad vs good RT) per phase ---")
    for phase in ["phase_1", "phase_2"]:
        phase_sm = sm[sm["phase"] == phase]
        paired = phase_sm.pivot(index="sub_id", columns="score_type", values="mean_rt").dropna()
        if len(paired) < 2:
            print(f"  {PHASE_LABELS[phase]}: insufficient data")
            continue
        bad_v  = paired["bad"].values
        good_v = paired["good"].values
        t_stat, t_p = stats.ttest_rel(bad_v, good_v)
        w_stat, w_p = stats.wilcoxon(bad_v, good_v)
        d = (bad_v - good_v).mean() / (bad_v - good_v).std(ddof=1)  # Cohen's d
        print(f"  {PHASE_LABELS[phase]}  (n={len(paired)}):")
        print(f"    Paired t-test : t({len(paired)-1})={t_stat:.3f}, p={t_p:.4f} {sig_stars(t_p)}")
        print(f"    Wilcoxon      : W={w_stat:.1f},            p={w_p:.4f} {sig_stars(w_p)}")
        print(f"    Cohen's d     : {d:.3f}")
        print(f"    Mean diff (bad−good): {(bad_v - good_v).mean():.3f} s "
              f"± {(bad_v - good_v).std(ddof=1):.3f}")

    print("\n" + "=" * 70)
    print("RT summary by score_type × block")
    print("=" * 70)
    summary_block = (
        df.groupby(["block", "score_type"])["rt_total"]
        .agg(n="count", mean="mean", std="std", median="median")
        .reindex(pd.MultiIndex.from_product(
            [BLOCK_ORDER, ["bad", "good"]],
            names=["block", "score_type"]
        ))
        .round(3)
    )
    print(summary_block.to_string())
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = load_data(ALL_TRIALS_CSV)
    print(f"Loaded {len(df)} trials from {df['sub_id'].nunique()} subjects "
          f"(after RT cap {RT_CAP}s)")

    print_summary(df)

    plot_rt_by_score_and_phase(
        df,
        os.path.join(ANALYSIS_DIR, "rt_good_vs_bad.png"),
    )
    plot_rt_per_subject(
        df,
        os.path.join(ANALYSIS_DIR, "rt_per_subject.png"),
    )

    plot_rt_by_block(
        df,
        os.path.join(ANALYSIS_DIR, "rt_by_block.png"),
    )
    plot_rt_per_subject_block(
        df,
        os.path.join(ANALYSIS_DIR, "rt_per_subject_block.png"),
    )
    plot_rt_lr_by_phase_score(
        df,
        os.path.join(ANALYSIS_DIR, "rt_by_block_stage.png"),
    )
    plot_rt_lr_normalized(
        df,
        os.path.join(ANALYSIS_DIR, "rt_per_subject_stage.png"),
    )
