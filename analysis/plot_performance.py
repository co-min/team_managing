"""
Performance figure for synergy/compositionality task.

Layout (per phase):
  ┌──────────────────────────────────────────────────────────┐
  │  Cumulative score lines (3 domains) + 85% threshold      │
  │  Dashed diagonal = running max possible (n × 10 → 180)   │
  │  Scatter markers = per-trial score (RdYlGn colour map)   │
  ├──────────────────────────────────────────────────────────┤
  │  Response strip: coloured tiles + 1st-choice animal abbr │
  └──────────────────────────────────────────────────────────┘

Criterion note
--------------
• Cumulative 85% (threshold=153): overall competency check at block end.
• Rolling 5-trial mean ≥ 8.5 (plotted as thin line on right y-axis):
  shows WHERE in the block learning stabilised — more sensitive than
  the end-of-block cumulative criterion.
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
from pathlib import Path

# ── configuration ──────────────────────────────────────────────────────────────
SUBJECT_ID   = sys.argv[1] if len(sys.argv) > 1 else "sub-003"
ROOT         = Path(__file__).parent.parent
DATA_PATH    = ROOT / "data" / SUBJECT_ID / "trials.csv"
OUT_PATH     = ROOT / "data" / SUBJECT_ID / "performance_figure.png"

MAX_SCORE        = 10
N_TRIALS_DOMAIN  = 18
MAX_CUMULATIVE   = MAX_SCORE * N_TRIALS_DOMAIN   # 180
THRESHOLD_PCT    = 0.85
THRESHOLD        = THRESHOLD_PCT * MAX_CUMULATIVE  # 153

ROLL_WINDOW = 5    # trials for rolling mean criterion

DOMAINS = ["cooking", "repairing", "tennis"]
PHASES  = ["phase_1", "phase_2"]
PHASE_LABELS = {
    "phase_1": "Phase 1 – Competency",
    "phase_2": "Phase 2 – Synergy",
}

DOMAIN_COLORS  = {"cooking": "#D9603B", "repairing": "#3D7DC8", "tennis": "#3BA35A"}
SCORE_CMAP     = "RdYlGn"

ANIMAL_ABBR = {
    "cat": "CAT", "panda": "PAN", "duck": "DUK", "rabbit": "RAB",
    "frog": "FRO", "chicken": "CHK", "cow": "COW", "bear": "BEA",
}

# ── load ───────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
df["trial_x"] = df["global_trial_id"] + 1   # 1-indexed for display

norm = Normalize(vmin=0, vmax=MAX_SCORE)
cmap = plt.get_cmap(SCORE_CMAP)

# ── figure ─────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 12))
fig.suptitle(
    f"Cumulative Performance by Domain — {SUBJECT_ID.replace('-', ' ').upper()}",
    fontsize=14, fontweight="bold", y=0.99,
)

outer_gs = gridspec.GridSpec(2, 1, figure=fig, hspace=0.42)

for row_idx, phase in enumerate(PHASES):
    phase_df = df[df["phase"] == phase].copy()
    x_start  = int(phase_df["trial_x"].min())
    x_end    = int(phase_df["trial_x"].max())

    inner_gs = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer_gs[row_idx],
        height_ratios=[5, 1], hspace=0.06,
    )
    ax_main  = fig.add_subplot(inner_gs[0])
    ax_strip = fig.add_subplot(inner_gs[1], sharex=ax_main)
    ax_roll  = ax_main.twinx()   # rolling accuracy (right y-axis)

    # ── cumulative score lines ─────────────────────────────────────────────
    for domain in DOMAINS:
        dom_df = (
            phase_df[phase_df["domain"] == domain]
            .sort_values("trial_id")
            .copy()
        )
        dom_df["within"] = dom_df["trial_id"] + 1
        dom_df["cumulative"] = dom_df["feedback_score"].cumsum()
        dom_df["cum_max"]    = dom_df["within"] * MAX_SCORE
        dom_df["rolling"]    = (
            dom_df["feedback_score"]
            .rolling(window=ROLL_WINDOW, min_periods=1)
            .mean()
        )

        x        = dom_df["trial_x"].values
        y        = dom_df["cumulative"].values
        cum_max  = dom_df["cum_max"].values
        color    = DOMAIN_COLORS[domain]

        # shaded gap between actual and max
        ax_main.fill_between(x, y, cum_max, alpha=0.07, color=color)

        # running-max diagonal
        ax_main.plot(x, cum_max,
                     color=color, linestyle="--", alpha=0.35, linewidth=1.2,
                     zorder=2)

        # cumulative score line
        ax_main.plot(x, y,
                     color=color, linestyle="-", linewidth=2.4,
                     label=domain.capitalize(), zorder=3)

        # per-trial markers coloured by score
        for _, r in dom_df.iterrows():
            fc = cmap(norm(r["feedback_score"]))
            ax_main.scatter(
                r["trial_x"], r["cumulative"],
                color=fc, s=62, zorder=5,
                edgecolors=color, linewidths=1.2,
            )

        # rolling mean on twin axis (subtle)
        ax_roll.plot(x, dom_df["rolling"].values,
                     color=color, linestyle=":", linewidth=1.2, alpha=0.65)

    # 85% cumulative threshold
    ax_main.axhline(
        THRESHOLD, color="crimson", linestyle="--", linewidth=1.8,
        label=f"85% criterion  ({int(THRESHOLD)} pts)", zorder=4,
    )

    # rolling threshold (right axis)
    ax_roll.axhline(
        MAX_SCORE * THRESHOLD_PCT, color="crimson",
        linestyle=":", linewidth=1.0, alpha=0.6,
    )

    # domain boundary lines + region labels
    for i, domain in enumerate(DOMAINS):
        dom_df = phase_df[phase_df["domain"] == domain]
        mid_x  = (dom_df["trial_x"].min() + dom_df["trial_x"].max()) / 2.0
        ax_main.text(
            mid_x, MAX_CUMULATIVE + 7,
            domain.capitalize(),
            ha="center", fontsize=9.5, color=DOMAIN_COLORS[domain],
            fontstyle="italic", fontweight="bold",
        )
        if i < len(DOMAINS) - 1:
            bx = dom_df["trial_x"].max() + 0.5
            ax_main.axvline(bx, color="grey", linestyle="--", alpha=0.35, linewidth=0.8)
            ax_strip.axvline(bx, color="grey", linestyle="--", alpha=0.35, linewidth=0.8)

    # axes decoration — main
    ax_main.set_title(PHASE_LABELS[phase], fontsize=11,
                      fontweight="bold", pad=20, loc="left")
    ax_main.set_ylabel("Cumulative Score", fontsize=10)
    ax_main.set_ylim(0, MAX_CUMULATIVE + 18)
    ax_main.set_yticks(range(0, MAX_CUMULATIVE + 1, 30))
    ax_main.legend(loc="upper left", fontsize=9, framealpha=0.85,
                   ncol=2, columnspacing=1.0)
    ax_main.grid(True, alpha=0.2, zorder=0)
    plt.setp(ax_main.get_xticklabels(), visible=False)

    # right y-axis (rolling mean)
    ax_roll.set_ylabel(f"Rolling {ROLL_WINDOW}-trial mean (pts)", fontsize=8,
                       color="grey", labelpad=4)
    ax_roll.set_ylim(0, MAX_SCORE + 1)
    ax_roll.set_yticks(range(0, MAX_SCORE + 1, 2))
    ax_roll.tick_params(axis="y", labelsize=7, colors="grey")
    ax_roll.spines["right"].set_color("grey")

    # ── response strip ─────────────────────────────────────────────────────
    tile_h, tile_y0 = 0.82, 0.09

    for domain in DOMAINS:
        dom_df = (
            phase_df[phase_df["domain"] == domain]
            .sort_values("trial_id")
            .copy()
        )
        for _, r in dom_df.iterrows():
            fc   = cmap(norm(r["feedback_score"]))
            rect = mpatches.FancyBboxPatch(
                (r["trial_x"] - 0.43, tile_y0), 0.86, tile_h,
                boxstyle="round,pad=0.03",
                facecolor=fc, edgecolor="white", linewidth=0.6,
            )
            ax_strip.add_patch(rect)

            txt_color = "white" if r["feedback_score"] < 6 else "#1a1a1a"
            c1 = str(r["choice1_code"])
            c2 = str(r["choice2_code"])
            # choice1 (upper, bold)
            ax_strip.text(
                r["trial_x"], tile_y0 + tile_h * 0.67, c1,
                ha="center", va="center",
                fontsize=6.5, fontweight="bold", color=txt_color,
            )
            # choice2 (lower, lighter)
            ax_strip.text(
                r["trial_x"], tile_y0 + tile_h * 0.28, c2,
                ha="center", va="center",
                fontsize=5.2, fontweight="normal", color=txt_color, alpha=0.75,
            )

    ax_strip.set_xlim(x_start - 0.6, x_end + 0.6)
    ax_strip.set_ylim(0, 1)
    ax_strip.set_yticks([0.5])
    ax_strip.set_yticklabels(["Choice\n(1st/2nd)", ], fontsize=7)
    ax_strip.set_xlabel("Trial Number", fontsize=10)

    # x-ticks every 3 trials
    ticks = list(range(x_start, x_end + 1, 3))
    if x_end not in ticks:
        ticks.append(x_end)
    ax_strip.set_xticks(ticks)
    ax_strip.set_xticklabels([str(t) for t in ticks], fontsize=8)
    ax_strip.tick_params(axis="x", length=3)
    ax_strip.spines[["top", "right"]].set_visible(False)

# ── shared colour bar (trial score) ────────────────────────────────────────────
cbar_ax = fig.add_axes([0.91, 0.10, 0.012, 0.78])
sm = ScalarMappable(cmap=SCORE_CMAP, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax)
cbar.set_label("Trial Score", fontsize=9, labelpad=6)
cbar.set_ticks(range(0, MAX_SCORE + 1, 2))
cbar.ax.tick_params(labelsize=8)

# ── save ───────────────────────────────────────────────────────────────────────
plt.subplots_adjust(left=0.06, right=0.89, top=0.96, bottom=0.06)
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
plt.close()
print(f"Saved → {OUT_PATH}")
