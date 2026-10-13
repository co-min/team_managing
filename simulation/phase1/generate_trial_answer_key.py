"""
Phase 1 — full trial info + correct-answer key.

Dumps every Phase 1 trial a real participant would see (block, trial,
domain, the 4 animals presented and their true competence scores for that
domain) together with the ground-truth "correct answer": the pair of
presented animals whose sc_<domain> value in the score table is highest.

Mirrors main.py's _generate_block_schedules() exactly (same seed, same
shuffle order) — see simulation/phase1/v01_minimal/simulate_v01_minimal.py
for why this is reproduced here instead of imported from main.py (importing
main.py pulls in psychopy/initiate hardware side effects).
"""

import itertools
import random
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import os
os.chdir(PROJECT_ROOT)

from function.config.settings import (  # noqa: E402
    CHAR_CODE, DOMAINS, P1_TRIALS, P2_TRIALS, P2_DOMAINS,
    BLOCK_PHASES, DOMAIN_ORDER, MISSION_MODE,
)
from function.io.data_loader import load_all_data  # noqa: E402

SCHEDULE_SEED = 42

OUT_CSV = Path(__file__).resolve().parent / "outputs" / "results" / "phase1_trial_schedule_with_answer.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)


def generate_block_schedules(animal_groups, block_phases):
    """Verbatim copy of main.py's _generate_block_schedules()."""
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


def main():
    competence, synergy, score, animal_groups, _p2_score = load_all_data()
    block_schedules = generate_block_schedules(animal_groups, BLOCK_PHASES)
    phase1_block_indices = [i for i, p in enumerate(BLOCK_PHASES) if p == "phase_1"]

    rows = []
    global_trial = 0
    for block_index in phase1_block_indices:
        for trial_index, trial_info in enumerate(block_schedules[block_index]):
            domain = trial_info["domain"]
            char_order = trial_info["char_order"]            # animal names, presentation order
            char_codes = [CHAR_CODE[name] for name in char_order]
            code_to_animal = dict(zip(char_codes, char_order))

            # ── Correct answer: the presented pair with the highest sc_<domain> ──
            best_pair, best_score = None, None
            for code_i, code_j in itertools.combinations(char_codes, 2):
                key = tuple(sorted([code_i, code_j]))
                s = score[key][domain]
                if best_score is None or s > best_score:
                    best_pair, best_score = key, s

            row = {"block": block_index, "trial": trial_index, "global_trial": global_trial, "domain": domain}
            for slot, animal_name in enumerate(char_order, start=1):
                code = char_codes[slot - 1]
                row[f"animal_{slot}"] = animal_name
                row[f"char_{slot}"] = code
                # competence in every domain, not just the one shown this trial
                for d in DOMAINS:
                    row[f"competence_{slot}_{d}"] = competence[code][d]

            # ── Score (= domain-dependent) for every one of the 6 possible pairs ──
            for code_i, code_j in itertools.combinations(sorted(char_codes), 2):
                key = tuple(sorted([code_i, code_j]))
                row[f"score_{code_i}{code_j}"] = score[key][domain]

            # ── Synergy (= ground-truth, domain-independent) for the same 6 pairs ──
            for code_i, code_j in itertools.combinations(sorted(char_codes), 2):
                key = tuple(sorted([code_i, code_j]))
                row[f"synergy_{code_i}{code_j}"] = synergy[key]

            row["correct_char1"]   = best_pair[0]
            row["correct_char2"]   = best_pair[1]
            row["correct_animal1"] = code_to_animal[best_pair[0]]
            row["correct_animal2"] = code_to_animal[best_pair[1]]
            row["correct_score"]   = best_score
            rows.append(row)
            global_trial += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(df)} Phase 1 trials (blocks {phase1_block_indices}) -> {OUT_CSV}")


if __name__ == "__main__":
    main()
