"""
Team Management task: build the 'chose_optimal' variable from raw trial logs
using the TRUE generative ground-truth tables (competence / synergy / score tables),
then fit a per-subject logistic regression:

    chose_optimal ~ trial_in_block * phase

Why this replaces the earlier "empirical max observed score" proxy:
  That proxy undercounts blocks where the participant only tried 1-2 of the 6
  possible pairs (explore-exploit confound: if they never tried a better pair,
  the proxy can't detect it). Using the real ground-truth score tables removes
  this bias entirely, since the true optimal pair is known regardless of what
  the participant actually chose.

Ground-truth files (5 CSVs), all keyed by role letters A/B/C/D (char_ani):
  - competence_table.csv         : Phase 1 (3 domains: cooking/repairing/tennis)
  - competence_table_domain2.csv : Phase 2 (2 domains: cooking/repairing)
  - synergy_table.csv            : SAME for both phases (pairwise synergy by role)
  - score_table.csv              : precomputed Score = Synergy * (CompA + CompB), Phase 1
  - score_table_domain2.csv      : same, Phase 2

Each block uses ONE fixed 4-animal roster (same 4 animals across all domains
within that block). Which roster/table row-group applies is found by matching
the block's actual animal names against the 'animal' column of the
phase-appropriate competence table -- NOT by row/id number (the two tables are
independently numbered).
"""

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# 1. Load ground-truth tables
# ---------------------------------------------------------------------------
def load_ground_truth(gt_dir="."):
    comp = {
        "phase_1": pd.read_csv(f"{gt_dir}/competence_table.csv", skipinitialspace=True),
        "phase_2": pd.read_csv(f"{gt_dir}/competence_table_domain2.csv", skipinitialspace=True),
    }
    score = {
        "phase_1": pd.read_csv(f"{gt_dir}/score_table.csv", skipinitialspace=True),
        "phase_2": pd.read_csv(f"{gt_dir}/score_table_domain2.csv", skipinitialspace=True),
    }
    synergy = pd.read_csv(f"{gt_dir}/synergy_table.csv", skipinitialspace=True)
    return comp, score, synergy


# ---------------------------------------------------------------------------
# 2. For one subject's trials.csv, recover the animal -> role (A/B/C/D) map
#    per block, look up the true score for the chosen pair, find the true
#    optimal pair for that block+domain, and build chose_optimal.
# ---------------------------------------------------------------------------
def build_chose_optimal(trials, comp, score):
    trials = trials.copy()
    trials["true_score"] = np.nan
    trials["chosen_pair_role"] = None
    trials["optimal_pair_role"] = None
    trials["optimal_score"] = np.nan
    trials["chose_optimal"] = np.nan
    trials["n_pairs_available"] = np.nan  # sanity: should always be 6 (4 choose 2)

    mismatches = []

    for block, sub in trials.groupby("block"):
        phase = sub["phase"].iloc[0]
        comp_t = comp[phase]
        score_t = score[phase]
        domain_cols = [c for c in score_t.columns if c.startswith("sc_")]

        # animal -> role lookup restricted to this block's actual roster
        roster_animals = sorted(set(sub["choice1_animal"]) | set(sub["choice2_animal"]))
        roster_rows = comp_t[comp_t["animal"].isin(roster_animals)]
        if len(roster_rows) != 4:
            raise ValueError(f"{block}: expected 4-animal roster, found {len(roster_rows)} "
                              f"matching rows for animals {roster_animals}")
        animal_to_role = dict(zip(roster_rows["animal"], roster_rows["char_ani"]))

        for idx, row in sub.iterrows():
            domain = row["domain"]
            sc_col = f"sc_{domain}"

            r1 = animal_to_role[row["choice1_animal"]]
            r2 = animal_to_role[row["choice2_animal"]]
            role_pair = tuple(sorted([r1, r2]))
            trials.loc[idx, "chosen_pair_role"] = "-".join(role_pair)

            # true score of the pair actually chosen
            m = score_t[(score_t["char1"] == role_pair[0]) & (score_t["char2"] == role_pair[1])]
            true_sc = m[sc_col].values[0]
            trials.loc[idx, "true_score"] = true_sc

            # sanity check against the logged feedback_score
            if not math.isclose(true_sc, row["feedback_score"], abs_tol=1e-6):
                mismatches.append((block, row["trial_id"], domain, role_pair,
                                    true_sc, row["feedback_score"]))

            # true optimal pair for this block+domain (ground truth, independent
            # of what the participant tried)
            best_row = score_t.loc[score_t[sc_col].idxmax()]
            best_pair = tuple(sorted([best_row["char1"], best_row["char2"]]))
            trials.loc[idx, "optimal_pair_role"] = "-".join(best_pair)
            trials.loc[idx, "optimal_score"] = best_row[sc_col]
            trials.loc[idx, "chose_optimal"] = int(role_pair == best_pair)
            trials.loc[idx, "n_pairs_available"] = len(score_t)

    if mismatches:
        print(f"WARNING: {len(mismatches)} trials where true_score != logged feedback_score "
              f"(check animal-role mapping). First few:")
        for m in mismatches[:5]:
            print("  ", m)
    else:
        print("Sanity check passed: true_score from ground-truth tables matches "
              "feedback_score for all trials.")

    return trials


# ---------------------------------------------------------------------------
# 3. Per-subject logistic regression: chose_optimal ~ trial_in_block * phase
#    (Newton-Raphson IRLS, no external stats package required)
# ---------------------------------------------------------------------------
def logistic_regression(df, y_col, x_cols, max_iter=50, tol=1e-8):
    X = np.column_stack([np.ones(len(df))] + [df[c].values.astype(float) for c in x_cols])
    y = df[y_col].values.astype(float)

    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        eta = X @ beta
        p = 1 / (1 + np.exp(-eta))
        W = np.clip(p * (1 - p), 1e-6, None)
        grad = X.T @ (y - p)
        H = -(X.T * W) @ X
        step = np.linalg.solve(H, grad)
        beta = beta - step
        if np.max(np.abs(step)) < tol:
            break

    eta = X @ beta
    p = 1 / (1 + np.exp(-eta))
    W = np.clip(p * (1 - p), 1e-6, None)
    FI = (X.T * W) @ X
    cov = np.linalg.inv(FI)
    se = np.sqrt(np.diag(cov))
    z = beta / se
    pval = [2 * (1 - 0.5 * (1 + math.erf(abs(zz) / math.sqrt(2)))) for zz in z]

    names = ["Intercept"] + x_cols
    result = pd.DataFrame({"term": names, "beta": beta, "SE": se, "z": z, "p": pval})
    return result


# ---------------------------------------------------------------------------
# 4. Figures
# ---------------------------------------------------------------------------
ROLL_WINDOW = 5
PHASE_COLORS = {"phase_1": "#1f77b4", "phase_2": "#ff7f0e"}
PHASE_LABELS  = {"phase_1": "Phase 1 (blocks 0,2,4)", "phase_2": "Phase 2 (blocks 1,3,5)"}
BLOCK_ORDER   = ["block_0", "block_1", "block_2", "block_3", "block_4", "block_5"]


def plot_group_learning_curve(all_df, out_path):
    """
    chose_optimal by phase-relative cumulative trial.
    Rolling mean per subject -> mean ± SEM across subjects.
    """
    df = all_df.copy()
    df = df.sort_values(["sub_id", "phase", "global_trial_id"])
    df["phase_trial"] = df.groupby(["sub_id", "phase"]).cumcount() + 1

    # block boundaries (use first subject as reference)
    ref = df[df["sub_id"] == df["sub_id"].iloc[0]]
    boundaries = {}
    for phase, g in ref.groupby("phase"):
        g = g.sort_values("phase_trial")
        sizes = g.groupby("block", sort=False)["phase_trial"].count()
        order = g.drop_duplicates("block")["block"]
        cum = np.cumsum([sizes[b] for b in order])[:-1]
        boundaries[phase] = cum

    # rolling mean per subject
    curves = {}
    for phase, gp in df.groupby("phase"):
        per_subj = {}
        for sid, sg in gp.groupby("sub_id"):
            sg = sg.sort_values("phase_trial")
            per_subj[sid] = (
                sg.set_index("phase_trial")["chose_optimal"]
                .rolling(ROLL_WINDOW, min_periods=1).mean()
            )
        curves[phase] = pd.DataFrame(per_subj)

    fig, ax = plt.subplots(figsize=(9, 5))
    for phase in ["phase_1", "phase_2"]:
        mat  = curves[phase]
        mean = mat.mean(axis=1)
        sem  = mat.std(axis=1, ddof=1) / np.sqrt(mat.shape[1])
        x    = mean.index.values

        for col in mat.columns:
            ax.plot(x, mat[col], color=PHASE_COLORS[phase], alpha=0.18, linewidth=1)

        ax.plot(x, mean, color=PHASE_COLORS[phase], linewidth=2.5,
                label=PHASE_LABELS[phase])
        ax.fill_between(x, mean - sem, mean + sem,
                        color=PHASE_COLORS[phase], alpha=0.2)

        for b in boundaries[phase]:
            ax.axvline(b + 0.5, color=PHASE_COLORS[phase],
                       linestyle="--", linewidth=0.8, alpha=0.5)

    ax.axhline(1/6, color="gray", linestyle=":", linewidth=1, label="Chance (1/6)")
    ax.set_xlabel("Cumulative trial (within phase)")
    ax.set_ylabel(f"P(chose optimal)  [{ROLL_WINDOW}-trial rolling mean]")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"Group learning curve — chose_optimal  (n={all_df['sub_id'].nunique()})")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_block_optimal_rate(all_df, out_path):
    """
    Mean ± SEM of chose_optimal per block across subjects (bar plot).
    """
    present_blocks = [b for b in BLOCK_ORDER if b in all_df["block"].unique()]
    phase_of_block = all_df.drop_duplicates("block").set_index("block")["phase"].to_dict()

    block_means = (
        all_df.groupby(["sub_id", "block"])["chose_optimal"]
        .mean()
        .reset_index()
    )
    stats = (
        block_means.groupby("block")["chose_optimal"]
        .agg(mean="mean", std="std", n="count")
        .reindex(present_blocks)
    )
    stats["sem"] = stats["std"] / np.sqrt(stats["n"])

    x     = np.arange(len(present_blocks))
    colors = [PHASE_COLORS[phase_of_block[b]] for b in present_blocks]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(x, stats["mean"], color=colors, alpha=0.8,
                  yerr=stats["sem"], capsize=4, error_kw={"linewidth": 1.5})

    # individual subject dots
    for xi, blk in zip(x, present_blocks):
        vals = block_means[block_means["block"] == blk]["chose_optimal"].values
        ax.plot(np.full(len(vals), xi) + np.random.uniform(-0.15, 0.15, len(vals)),
                vals, "o", color="black", alpha=0.5, markersize=5, zorder=5)

    ax.axhline(1/6, color="gray", linestyle=":", linewidth=1, label="Chance (1/6)")
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("block_", "B") for b in present_blocks])
    ax.set_ylabel("P(chose optimal)")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Optimal-choice rate per block  (n={all_df['sub_id'].nunique()})")

    from matplotlib.patches import Patch
    legend_els = [Patch(facecolor=PHASE_COLORS["phase_1"], label="Phase 1"),
                  Patch(facecolor=PHASE_COLORS["phase_2"], label="Phase 2")]
    ax.legend(handles=legend_els + [
        plt.Line2D([0], [0], color="gray", linestyle=":", label="Chance (1/6)")
    ], loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# 5. Run end-to-end for one subject
# ---------------------------------------------------------------------------
def run_subject(trials_csv, gt_dir="."):
    trials = pd.read_csv(trials_csv)
    comp, score, synergy = load_ground_truth(gt_dir)
    trials = build_chose_optimal(trials, comp, score)

    trials["phase_c"] = trials["phase"].map({"phase_1": 0, "phase_2": 1}).astype(float)
    trials["trial"] = trials["block_trial_id"].astype(float)
    trials["inter"] = trials["trial"] * trials["phase_c"]

    print("\nOptimal-choice rate by block:")
    print(trials.groupby("block")["chose_optimal"].mean().round(3))
    print("\nOptimal-choice rate by phase:")
    print(trials.groupby("phase")["chose_optimal"].mean().round(3))

    result = logistic_regression(trials, "chose_optimal", ["trial", "phase_c", "inter"])
    print("\nLogistic regression: chose_optimal ~ trial_in_block * phase")
    print(result.to_string(index=False))

    return trials, result


if __name__ == "__main__":
    import os, glob

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    gt_dir   = os.path.join(os.path.dirname(__file__), "..", "stimuli")
    out_dir  = os.path.join(os.path.dirname(__file__), "..", "data")

    sub_dirs = sorted(glob.glob(os.path.join(data_dir, "sub-*")))
    all_trials  = []
    all_results = []

    for sub_path in sub_dirs:
        sub_id = os.path.basename(sub_path)
        trials_csv = os.path.join(sub_path, "trials.csv")
        if not os.path.exists(trials_csv):
            print(f"\n[SKIP] {sub_id}: trials.csv not found")
            continue

        print(f"\n{'='*60}")
        print(f"  {sub_id}")
        print(f"{'='*60}")

        trials, result = run_subject(trials_csv=trials_csv, gt_dir=gt_dir)
        trials["sub_id"] = sub_id
        result["sub_id"] = sub_id
        all_trials.append(trials)
        all_results.append(result)

        trials.to_csv(os.path.join(sub_path, "trials_with_chose_optimal.csv"), index=False)

    if all_trials:
        all_df = pd.concat(all_trials, ignore_index=True)
        all_df.to_csv(os.path.join(out_dir, "all_trials_with_chose_optimal.csv"), index=False)
        pd.concat(all_results, ignore_index=True).to_csv(
            os.path.join(out_dir, "all_logistic_results.csv"), index=False)

        fig_dir = os.path.join(os.path.dirname(__file__))
        plot_group_learning_curve(
            all_df,
            os.path.join(fig_dir, "group_chose_optimal_learning_curve.png"),
        )
        plot_block_optimal_rate(
            all_df,
            os.path.join(fig_dir, "group_chose_optimal_by_block.png"),
        )
        print(f"\nDone. Processed {len(all_trials)} subjects.")
