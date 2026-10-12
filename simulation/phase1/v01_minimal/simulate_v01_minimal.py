"""
Phase 1 — v01 minimal virtual-participant simulation.

PURPOSE
-------
This is NOT the final cognitive model. It is a minimal sanity-check agent
that walks through the existing Phase 1 task (Domain -> Choice 1 ->
competence reveal -> Choice 2 -> score-table feedback -> synergy-belief
update) using deterministic argmax choices and a simple delta-rule belief
update. It exists to validate that the loop itself is wired correctly
before any richer model (softmax, Bayesian inference, multi-agent, ...)
is attempted in later versions.

WHAT IS REUSED FROM THE REAL TASK (not re-created here)
---------------------------------------------------------
- function.io.data_loader.load_all_data()   -> competence / synergy / score
                                                 tables + animal_groups
- function.config.settings.CHAR_CODE         -> animal name -> char code (A/B/C/D)
- function.config.settings.ANIMAL_CODE       -> char code -> animal name
- function.config.settings.DOMAINS           -> Phase 1 domain sequence source
- function.config.settings.get_comp_color    -> the exact red/yellow/green
                                                 competence thresholds used
                                                 by the real PsychoPy task
- function.config.settings.BLOCK_PHASES, P1_TRIALS, DOMAIN_ORDER
                                              -> block/trial structure

WHY main.py's _generate_block_schedules() IS NOT IMPORTED DIRECTLY
--------------------------------------------------------------------
main.py's top-level imports include `from psychopy import core`,
`from initiate import initiate`, and other modules that open a PsychoPy
window, talk to LabJack hardware, and connect to the Neon eye tracker.
Simply doing `from main import _generate_block_schedules` would execute
all of that at import time (or at worst require those dependencies to be
installed and hardware to be reachable) just to reach one pure function.

Instead, the schedule-generation logic is reproduced verbatim below in
`generate_block_schedules()`. It is a direct copy of main.py's
`_generate_block_schedules()` body (same RNG seed, same shuffle logic) so
that the trial schedule an agent sees here is identical to what a real
participant would see. If main.py's scheduling logic changes, this copy
must be updated to match.

GROUND-TRUTH ISOLATION
-----------------------
The agent only ever touches `competence` (to learn categorical
red/yellow/green reveals) and `score` (to get trial-by-trial feedback).
The `synergy` dict (true synergy values) is read ONLY at the very end of
the script, after every choice has already been made, purely to draw
post-hoc reference lines / print an evaluation table. It is never passed
into any choice-making function.
"""

import itertools
import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe: never needs a display to save a PNG
import matplotlib.pyplot as plt
import pandas as pd

# ─── Make the project importable regardless of current working directory ──────
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# function/io/data_loader.py loads the synergy table via a path that is
# relative to the project root ('stimuli/synergy/synergy_table.csv'), so we
# must run with that as the working directory for load_all_data() to work
# no matter where this script is launched from.
import os
os.chdir(PROJECT_ROOT)

from function.config.settings import (  # noqa: E402
    CHAR_CODE, ANIMAL_CODE, DOMAINS, P1_TRIALS, P2_TRIALS, P2_DOMAINS,
    BLOCK_PHASES, DOMAIN_ORDER, MISSION_MODE,
)
from function.io.data_loader import load_all_data  # noqa: E402

VERSION = "v01_minimal"

# ─── Output locations (per simulation/phase1/README.md conventions) ───────────
OUT_DIR       = Path(__file__).resolve().parent / "outputs"
RESULTS_DIR   = OUT_DIR / "results"
FIGURES_DIR   = OUT_DIR / "figures"
RESULTS_CSV   = RESULTS_DIR / f"{VERSION}_simulation_results.csv"
MEMORY_CSV    = RESULTS_DIR / f"{VERSION}_competence_memory.csv"
SCHEDULE_CSV  = RESULTS_DIR / f"{VERSION}_trial_schedule.csv"
FIGURE_PNG    = FIGURES_DIR / f"{VERSION}_synergy_belief_trajectory.png"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Agent assumptions for v01 (deliberately simple, see module docstring) ────
INITIAL_SYNERGY_BELIEF = 1.0   # assumption 1: every pair starts at the same belief
ALPHA                  = 0.3   # assumption 10: delta-rule learning rate

# The real task shows only a red / yellow / green competence category
# (function.config.settings.get_comp_color: <=3.0 red, <=6.0 yellow, else
# green). v01's agent cannot see the exact competence number, so it needs
# some numeric stand-in for "how good is this category" in order to use the
# V(i) = S_hat * (C_hat_i + C_hat_j) formula. These three numbers are a new
# v01 modeling choice (NOT part of the real task), set to the midpoint of
# each category's documented score range.
COMPETENCE_CATEGORY_VALUE = {
    "red":    2.0,   # midpoint of the documented low range    (1.0 - 3.0)
    "yellow": 5.0,   # midpoint of the documented middle range (3.5 - 6.0)
    "green":  8.0,   # midpoint of the documented high range   (6.5 - 9.0)
}
# Assumption 3: before any category has been observed for a given
# (animal, domain), the agent assumes the middle category.
NEUTRAL_PRIOR_VALUE = COMPETENCE_CATEGORY_VALUE["yellow"]

SCHEDULE_SEED = 42  # mirrors main.py's module-level `_SCHEDULE_SEED`


# ─── Reproduced (not imported) schedule logic — see module docstring ──────────
def generate_block_schedules(animal_groups, block_phases):
    """
    Build one trial schedule per block, exactly mirroring main.py's
    `_generate_block_schedules()`. Each schedule is a list of
    {'domain': str, 'char_order': list[str animal names]} dicts, one per trial.
    """
    rng = random.Random(SCHEDULE_SEED)
    schedules = []
    for group, phase in zip(animal_groups, block_phases):
        if MISSION_MODE == 3 and phase == "phase_2":
            n_trials, domains = P2_TRIALS, P2_DOMAINS
        else:
            n_trials, domains = P1_TRIALS, DOMAINS

        trials_per_domain = n_trials // len(domains)
        if DOMAIN_ORDER == "sequential":
            domain_sequence = [d for d in domains for _ in range(trials_per_domain)]
        else:
            domain_sequence = domains * trials_per_domain
            rng.shuffle(domain_sequence)

        schedules.append([
            {"domain": d, "char_order": rng.sample(group, len(group))}
            for d in domain_sequence
        ])
    return schedules


def true_competence_category(true_score):
    """
    Map a ground-truth competence number to the same red/yellow/green
    category boundaries the real task uses (function.config.settings.get_comp_color).
    This is the only place ground-truth competence numbers are read; the
    agent never sees `true_score` itself, only the category it maps to.
    """
    if true_score <= 3.0:
        return "red"
    elif true_score <= 6.0:
        return "yellow"
    else:
        return "green"


def believed_competence(competence_memory, char_code, domain):
    """
    The agent's numeric stand-in for how competent `char_code` is in `domain`.
    Uses the remembered category if this (animal, domain) combination has
    been revealed before; otherwise falls back to the neutral prior
    (assumption 2 and 3).
    """
    category = competence_memory.get((char_code, domain))
    if category is None:
        return NEUTRAL_PRIOR_VALUE
    return COMPETENCE_CATEGORY_VALUE[category]


def pair_key(code_a, code_b):
    """Sorted-tuple key, matching the convention used by synergy/score dicts."""
    return tuple(sorted([code_a, code_b]))


def predicted_pair_value(code_i, code_j, domain, competence_memory, synergy_belief):
    """V_hat(i, j) = S_hat(i, j) * (C_hat_i + C_hat_j) — assumption 5's formula."""
    s_hat = synergy_belief[pair_key(code_i, code_j)]
    c_hat_i = believed_competence(competence_memory, code_i, domain)
    c_hat_j = believed_competence(competence_memory, code_j, domain)
    return s_hat * (c_hat_i + c_hat_j)


# ─── Choice 1 ───────────────────────────────────────────────────────────────
def choose_choice1(char_codes, domain, competence_memory, synergy_belief):
    """
    Choice 1: no current-trial competence information is available yet
    (assumption 4). For each candidate i, its value is the BEST pair value
    obtainable with any of the other candidates present this trial
    (assumption 5). The candidate with the highest such value is chosen,
    using a deterministic argmax (assumption 11: ties go to the first
    candidate encountered in `char_codes`).
    """
    best_code = None
    best_value = None
    for code_i in char_codes:
        partners = [c for c in char_codes if c != code_i]
        best_partner_value = max(
            predicted_pair_value(code_i, code_j, domain, competence_memory, synergy_belief)
            for code_j in partners
        )
        if best_value is None or best_partner_value > best_value:
            best_value = best_partner_value
            best_code = code_i
    return best_code


# ─── Competence reveal (happens for everyone shown this trial) ────────────────
def reveal_competence(char_codes, domain, competence_table, competence_memory):
    """
    Mirrors function/phases/phase1.py: after Choice 1, the true competence
    score (for the current domain) is revealed for every animal presented
    this trial — not just the chosen one — via a colored border. Here we
    store only the red/yellow/green category in memory, never the raw number.
    """
    for code in char_codes:
        true_score = competence_table[code][domain]
        competence_memory[(code, domain)] = true_competence_category(true_score)


# ─── Choice 2 ───────────────────────────────────────────────────────────────
def choose_choice2(choice1_code, remaining_codes, domain, competence_memory, synergy_belief):
    """
    Choice 2: the hover sequence is abstracted away (assumption 7) — the
    agent simply inspects the (now revealed) competence category of each
    remaining candidate and picks the partner that maximizes the predicted
    pair value with the already-chosen Choice 1 animal (assumption 8),
    again with a deterministic argmax.
    """
    best_code = None
    best_value = None
    for code_j in remaining_codes:
        value = predicted_pair_value(choice1_code, code_j, domain, competence_memory, synergy_belief)
        if best_value is None or value > best_value:
            best_value = value
            best_code = code_j
    return best_code


# ─── Synergy belief update ───────────────────────────────────────────────────
def update_synergy_belief(synergy_belief, choice1_code, choice2_code, domain,
                           outcome, competence_memory, alpha):
    """
    Assumption 10's delta rule. `S_observed` is inferred by inverting the
    SAME formula used to make choices (V = S_hat * (C_i + C_j)): given the
    actual feedback score and the agent's own (categorical) competence
    belief for the chosen pair, the implied synergy is
        S_observed = outcome / (C_hat_i + C_hat_j).
    This keeps the model internally consistent, but note the scale of
    `outcome` depends on which score table is active (see the printed
    explanation / README notes on MISSION_MODE) — v01 does not attempt to
    rescale it to match the literal ground-truth synergy range.
    """
    key = pair_key(choice1_code, choice2_code)
    belief_before = synergy_belief[key]

    c_hat_i = believed_competence(competence_memory, choice1_code, domain)
    c_hat_j = believed_competence(competence_memory, choice2_code, domain)
    denominator = c_hat_i + c_hat_j
    observed_synergy = outcome / denominator if denominator != 0 else 0.0

    belief_after = belief_before + alpha * (observed_synergy - belief_before)
    synergy_belief[key] = belief_after
    return belief_before, belief_after, observed_synergy


def main():
    # ── Load the real task's data tables (ground truth lives only in here) ───
    competence, synergy, score, animal_groups, _p2_score = load_all_data()

    # All char-code pairs that exist, derived from the data (not hand-typed),
    # sorted so the column order is A-B, A-C, A-D, B-C, B-D, C-D.
    all_codes = sorted(competence.keys())
    all_pairs = list(itertools.combinations(all_codes, 2))

    block_schedules = generate_block_schedules(animal_groups, BLOCK_PHASES)
    phase1_block_indices = [i for i, phase in enumerate(BLOCK_PHASES) if phase == "phase_1"]

    # ── Dump the raw trial schedule (domain + animal order), independent of
    # any agent choice — this is exactly what SCHEDULE_SEED reproduces
    # identically on every run / for every participant. ──────────────────────
    schedule_rows = []
    for block_index in phase1_block_indices:
        for trial_index, trial_info in enumerate(block_schedules[block_index]):
            domain = trial_info["domain"]
            char_order = trial_info["char_order"]  # animal names, presentation order
            row = {"block": block_index, "trial": trial_index, "domain": domain}
            for slot, animal_name in enumerate(char_order, start=1):
                code = CHAR_CODE[animal_name]
                row[f"animal_{slot}"] = animal_name
                row[f"char_{slot}"] = code
                row[f"true_competence_{code}"] = competence[code][domain]
            schedule_rows.append(row)
    pd.DataFrame(schedule_rows).to_csv(SCHEDULE_CSV, index=False)

    # ── Agent state (persists across all Phase 1 blocks) ─────────────────────
    synergy_belief = {pair: INITIAL_SYNERGY_BELIEF for pair in all_pairs}
    competence_memory = {}  # (char_code, domain) -> 'red' | 'yellow' | 'green'

    rows = []
    global_trial = 0

    for block_index in phase1_block_indices:
        schedule = block_schedules[block_index]

        for trial_index, trial_info in enumerate(schedule):
            domain = trial_info["domain"]
            char_order = trial_info["char_order"]            # animal names
            char_codes = [CHAR_CODE[name] for name in char_order]

            # ── Choice 1: made with no current-trial competence info ─────────
            choice1_code = choose_choice1(char_codes, domain, competence_memory, synergy_belief)

            # ── Competence reveal: exactly as the real task reveals it ───────
            reveal_competence(char_codes, domain, competence, competence_memory)

            # ── Choice 2: candidates' categories are now visible ─────────────
            remaining_codes = [c for c in char_codes if c != choice1_code]
            choice2_code = choose_choice2(choice1_code, remaining_codes, domain,
                                           competence_memory, synergy_belief)

            # ── Feedback: read ONLY from the existing score table ────────────
            chosen_pair = pair_key(choice1_code, choice2_code)
            outcome = score[chosen_pair][domain]

            # ── Synergy-belief update for the chosen pair only ────────────────
            belief_before, belief_after, observed_synergy = update_synergy_belief(
                synergy_belief, choice1_code, choice2_code, domain, outcome,
                competence_memory, ALPHA,
            )

            # ── Record this trial ─────────────────────────────────────────────
            row = {
                "version": VERSION,
                "block": block_index,
                "trial": trial_index,
                "global_trial": global_trial,
                "domain": domain,
                "choice1": choice1_code,
                "choice2": choice2_code,
                "choice1_animal": ANIMAL_CODE[choice1_code],
                "choice2_animal": ANIMAL_CODE[choice2_code],
                "pair": f"{chosen_pair[0]}{chosen_pair[1]}",
                "outcome": outcome,
                "observed_synergy": observed_synergy,
                "belief_before": belief_before,
                "belief_after": belief_after,
            }
            for pair in all_pairs:
                row[f"belief_{pair[0]}{pair[1]}"] = synergy_belief[pair]
            rows.append(row)

            global_trial += 1
            # ── next trial ─────────────────────────────────────────────────────

    results_df = pd.DataFrame(rows)
    results_df.to_csv(RESULTS_CSV, index=False)

    # ── Save the agent's final competence memory for debugging ───────────────
    memory_rows = [
        {
            "char_code": code,
            "domain": domain,
            "category_label": category,
            "category_value": COMPETENCE_CATEGORY_VALUE[category],
        }
        for (code, domain), category in sorted(competence_memory.items())
    ]
    pd.DataFrame(memory_rows).to_csv(MEMORY_CSV, index=False)

    # ── Plot all six synergy-belief trajectories ──────────────────────────────
    # Fixed categorical colors (one per pair, never reused/cycled across runs).
    pair_colors = {
        all_pairs[0]: "#2a78d6",  # blue
        all_pairs[1]: "#eb6834",  # orange
        all_pairs[2]: "#1baf7a",  # aqua
        all_pairs[3]: "#eda100",  # yellow
        all_pairs[4]: "#e87ba4",  # magenta
        all_pairs[5]: "#008300",  # green
    }

    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    for pair in all_pairs:
        label = f"{pair[0]}{pair[1]}"
        column = f"belief_{label}"
        color = pair_colors[pair]

        # Solid line: the agent's belief trajectory (what the agent actually used).
        ax.plot(
            results_df["global_trial"], results_df[column],
            color=color, linewidth=2, label=f"belief {label}",
        )
        # Dashed horizontal line: TRUE synergy, drawn ONLY for post-hoc reference.
        # This value was never available to the agent during the simulation.
        true_value = synergy[pair]
        ax.axhline(true_value, color=color, linewidth=1, linestyle="--", alpha=0.7)

    ax.set_xlabel("trial (Phase 1 only, across all blocks)", color="#0b0b0b")
    ax.set_ylabel("synergy belief  S_hat", color="#0b0b0b")
    ax.set_title(
        "v01 minimal agent — synergy belief trajectories\n"
        "(solid = agent belief, dashed = true synergy, reference only)",
        color="#0b0b0b",
    )
    ax.tick_params(colors="#52514e")
    ax.grid(True, color="#e1e0d9", linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#c3c2b7")
    ax.legend(loc="upper left", frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(FIGURE_PNG, dpi=150)
    plt.close(fig)

    # ── Console summary ────────────────────────────────────────────────────────
    print(f"v01 minimal simulation complete — {len(results_df)} Phase 1 trials simulated "
          f"across blocks {phase1_block_indices}.\n")

    print("Choices by trial:")
    print(results_df[[
        "global_trial", "block", "trial", "domain",
        "choice1", "choice2", "pair", "outcome", "belief_after",
    ]].to_string(index=False))
    print()

    print("Final synergy beliefs (agent) vs. true synergy "
          "(ground truth — shown now ONLY for evaluation, never used during the run):")
    for pair in all_pairs:
        label = f"{pair[0]}{pair[1]}"
        print(f"  {label}:  belief = {synergy_belief[pair]:.4f}   true = {synergy[pair]:.4f}")
    print()

    print("Output files:")
    print(f"  results  : {RESULTS_CSV}")
    print(f"  memory   : {MEMORY_CSV}")
    print(f"  schedule : {SCHEDULE_CSV}")
    print(f"  figure   : {FIGURE_PNG}")


if __name__ == "__main__":
    main()
