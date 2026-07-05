"""
figure.py
---------
Trial-by-trial accuracy figure.

Layout:
  - 3 subplots (one per domain: cooking / repairing / tennis)
  - X: sequential trial number within domain  (1–30)
        phase_1 = trials  1–12
        phase_2 = trials 13–24
        phase_3 = trials 25–30
  - Y: accuracy (proportion correct across subjects)
  - Dots  = per-trial accuracy, coloured by phase
  - Error = ±1 SEM across subjects
  - Black line = centred rolling average (window=3)
  - Background shading by phase
  - Dashed horizontal line at chance (0.5)
"""

import platform
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

# ── Korean font ───────────────────────────────────────────────────────────────
_FONT = "AppleGothic" if platform.system() == "Darwin" else "Malgun Gothic"
plt.rcParams["font.family"] = _FONT
plt.rcParams["axes.unicode_minus"] = False

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")

PHASES   = ["phase_1", "phase_2", "phase_3"]
DOMAINS  = ["cooking", "repairing", "tennis"]

PHASE_N      = {"phase_1": 12, "phase_2": 12, "phase_3": 6}
PHASE_OFFSET = {"phase_1": 0,  "phase_2": 12, "phase_3": 24}  # 0-based start

DOMAIN_KR = {"cooking": "요리 (Cooking)", "repairing": "수리 (Repairing)", "tennis": "테니스 (Tennis)"}
PHASE_KR  = {"phase_1": "Phase 1\n(능력 단서)", "phase_2": "Phase 2\n(시너지 단서)", "phase_3": "Phase 3\n(단서 없음)"}
PHASE_COL = {"phase_1": "#4C72B0", "phase_2": "#DD8452", "phase_3": "#55A868"}


# ── Data loading & preprocessing ──────────────────────────────────────────────

def load_trials(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Concatenate all sub-*/trials.csv files."""
    files = sorted(data_dir.glob("sub-*/trials.csv"))
    if not files:
        raise FileNotFoundError(f"trials.csv not found under {data_dir}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Drop timeout trials (response_made == False / 'False' / NaN)
    - Add is_correct  (feedback_score > 0)
    - Add domain_trial (1-indexed sequential trial number within domain)
    """
    df = df.copy()

    # CSV stores Python bools as strings "True"/"False"
    df["response_made"] = df["response_made"].map(
        lambda v: v if isinstance(v, bool) else str(v).strip().lower() == "true"
    )
    df = df[df["response_made"]].copy()

    df["feedback_score"] = pd.to_numeric(df["feedback_score"], errors="coerce")
    df = df.dropna(subset=["feedback_score"])

    df["is_correct"]   = df["feedback_score"] > 0
    df["domain_trial"] = df["phase"].map(PHASE_OFFSET) + df["trial_id"] + 1  # 1-indexed

    return df


# ── Accuracy aggregation ──────────────────────────────────────────────────────

def compute_trial_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (domain, phase, domain_trial): mean accuracy and SEM across subjects.
    """
    agg = (
        df.groupby(["domain", "phase", "domain_trial"])["is_correct"]
        .agg(accuracy="mean", acc_sem="sem", n="count")
        .reset_index()
    )
    return agg


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_accuracy_per_trial(
    df_acc: pd.DataFrame,
    rolling_window: int = 3,
    figsize: tuple = (13, 9),
) -> plt.Figure:
    """
    Three-panel figure: one subplot per domain.

    Parameters
    ----------
    df_acc         : output of compute_trial_accuracy()
    rolling_window : window size for centred rolling average
    figsize        : figure size in inches
    """
    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True, sharey=True)

    for ax, domain in zip(axes, DOMAINS):
        d = df_acc[df_acc["domain"] == domain].sort_values("domain_trial")

        # Phase background shading
        for phase in PHASES:
            start = PHASE_OFFSET[phase] + 1
            end   = PHASE_OFFSET[phase] + PHASE_N[phase]
            ax.axvspan(start - 0.5, end + 0.5, alpha=0.08, color=PHASE_COL[phase], zorder=0)

        # Per-trial scatter + SEM error bars (coloured by phase)
        for phase in PHASES:
            sub = d[d["phase"] == phase]
            ax.scatter(
                sub["domain_trial"], sub["accuracy"],
                color=PHASE_COL[phase], s=40, alpha=0.85, zorder=3,
            )
            ax.errorbar(
                sub["domain_trial"], sub["accuracy"],
                yerr=sub["acc_sem"].fillna(0),
                fmt="none", color=PHASE_COL[phase], alpha=0.45, capsize=3, zorder=2,
            )

        # Centred rolling average
        if len(d) >= rolling_window:
            roll = (
                d.set_index("domain_trial")["accuracy"]
                .rolling(rolling_window, center=True, min_periods=1)
                .mean()
            )
            ax.plot(roll.index, roll.values,
                    color="black", linewidth=2.0, zorder=4, solid_capstyle="round")

        # Chance level
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.9, alpha=0.7, zorder=1)

        # Phase boundary lines
        for boundary in [12.5, 24.5]:
            ax.axvline(boundary, color="dimgray", linestyle=":", linewidth=1.1, zorder=1)

        ax.set_ylabel("정답률", fontsize=10)
        ax.set_title(DOMAIN_KR.get(domain, domain),
                     fontsize=11, fontweight="bold", loc="left", pad=4)
        ax.set_ylim(-0.05, 1.12)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.spines[["top", "right"]].set_visible(False)

    # Phase label annotations above top subplot
    for phase in PHASES:
        mid = PHASE_OFFSET[phase] + PHASE_N[phase] / 2 + 0.5
        axes[0].text(
            mid, 1.03,
            PHASE_KR[phase].replace("\n", " "),
            ha="center", va="bottom", fontsize=8.5,
            color=PHASE_COL[phase], fontweight="bold",
            transform=axes[0].get_xaxis_transform(),
        )

    # X axis
    axes[-1].set_xlabel("Domain 내 Trial 번호", fontsize=10)
    axes[-1].set_xlim(0.5, 30.5)
    axes[-1].set_xticks(range(1, 31))
    axes[-1].set_xticklabels(
        [str(i) if i in {1, 3, 6, 9, 12, 13, 15, 18, 21, 24, 25, 27, 30} else ""
         for i in range(1, 31)],
        fontsize=8,
    )

    # Legend
    patch_handles = [
        mpatches.Patch(color=PHASE_COL[p], alpha=0.6, label=PHASE_KR[p].replace("\n", " "))
        for p in PHASES
    ]
    line_handles = [
        plt.Line2D([0], [0], color="black", linewidth=2.0,
                   label=f"이동평균 (window={rolling_window})"),
        plt.Line2D([0], [0], color="gray", linestyle="--",
                   linewidth=0.9, label="Chance (0.5)"),
    ]
    fig.legend(
        handles=patch_handles + line_handles,
        loc="lower center", ncol=5,
        bbox_to_anchor=(0.5, -0.01), fontsize=8.5,
        frameon=True, framealpha=0.9,
    )

    n_subs = df_acc["n"].max() if "n" in df_acc.columns else "?"
    fig.suptitle(
        f"Domain별 Trial-by-Trial 정답률  (N ≈ {n_subs}명)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.97])
    return fig


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df_raw = load_trials()
    df     = preprocess(df_raw)
    df_acc = compute_trial_accuracy(df)

    fig = plot_accuracy_per_trial(df_acc, rolling_window=3)
    fig.savefig("accuracy_per_trial.png", dpi=150, bbox_inches="tight")
    plt.show()
    print(f"\n저장 완료: accuracy_per_trial.png")
    print(f"총 피험자 수: {df['subject_id'].nunique()}")
    print(f"총 trial 수: {len(df)}")
    print(f"\n=== Domain × Phase 별 평균 정답률 ===")
    print(
        df.groupby(["domain", "phase"])["is_correct"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "accuracy", "count": "n_trials"})
        .round(3)
    )
