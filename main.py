import random

import pandas as pd
from psychopy import core

from initiate import initiate
from utils.inter_trial import run_gaussian_iti
from function.config.settings import P1_TRIALS, P2_TRIALS
from function.io.frame_logger import make_frame_log
from function.io.metadata import save_trial_metadata
from function.phases.phase1 import run_phase1_trial
from function.phases.phase2 import run_phase2_trial
from function.phases.feedback import run_feedback


DOMAINS = ['cooking', 'repairing', 'tennis']

# Fixed seed: all participants receive the same trial layouts (no positional bias).
_SCHEDULE_SEED = 42
_ANIMALS = ['duck', 'frog', 'panda', 'rabbit']


def _generate_schedules():
    """
    Build per-domain, per-phase lists of animal orderings.

    Each element is a 4-item permutation of _ANIMALS:
      [up_animal, down_animal, right_animal, left_animal]

    Using a fixed seed guarantees every participant sees the same
    spatial arrangement on every trial.

    Returns
    -------
    p1_schedule : {domain: [char_order_t0, char_order_t1, ...]}  length = P1_TRIALS
    p2_schedule : {domain: [char_order_t0, ...]}                 length = P2_TRIALS
    """
    rng = random.Random(_SCHEDULE_SEED)
    p1 = {d: [rng.sample(_ANIMALS, 4) for _ in range(P1_TRIALS)] for d in DOMAINS}
    p2 = {d: [rng.sample(_ANIMALS, 4) for _ in range(P2_TRIALS)] for d in DOMAINS}
    return p1, p2


def _load_all_data():
    """
    Load the three stimulus CSVs into fast-lookup dicts.

    competence  : {char_ani: {domain: score}}        e.g. {'A': {'cooking': 1, ...}}
    synergy     : {(cA, cB): int}                     sorted tuple key
    score       : {(cA, cB): {domain: int}}           sorted tuple key
    """
    comp_df = pd.read_csv('stimuli/competence_table.csv', skipinitialspace=True)
    competence = {}
    for _, row in comp_df.iterrows():
        char = str(row['char_ani']).strip()
        competence[char] = {
            'cooking':   int(row['cooking']),
            'repairing': int(row['repairing']),
            'tennis':    int(row['tennis']),
        }

    syn_df = pd.read_csv('stimuli/synergy_table.csv', skipinitialspace=True)
    synergy = {}
    for _, row in syn_df.iterrows():
        key = tuple(sorted([str(row['char1']).strip(), str(row['char2']).strip()]))
        synergy[key] = int(row['synergy_score'])

    score_df = pd.read_csv('stimuli/score_table.csv', skipinitialspace=True)
    score = {}
    for _, row in score_df.iterrows():
        key = tuple(sorted([str(row['char1']).strip(), str(row['char2']).strip()]))
        score[key] = {
            'cooking':   int(row['sc_cooking']),
            'repairing': int(row['sc_repairing']),
            'tennis':    int(row['sc_tennis']),
        }

    return competence, synergy, score


def main() -> None:
    ctx = initiate()
    win = ctx.win
    subject_id = ctx.subject_id
    global_clock = core.Clock()

    competence, synergy, score = _load_all_data()
    p1_schedule, p2_schedule = _generate_schedules()

    def get_feedback_score(c1, c2, domain):
        key = tuple(sorted([c1, c2]))
        return score.get(key, {}).get(domain, 0)

    for domain in DOMAINS:
        # # ── Phase 1: competence observable, synergy infer (12 trials) ──────────
        # for trial_i in range(P1_TRIALS):
        #     char_order = p1_schedule[domain][trial_i]
        #     stim_pair_id = f"{domain}_p1_t{trial_i:02d}"
        #     frame_log = make_frame_log(
        #         phase="phase_1",
        #         trial_id=trial_i,
        #         stim_pair_id=stim_pair_id,
        #     )
        #     run_gaussian_iti(win, global_clock, frame_log)
        #     result = run_phase1_trial(win, global_clock, frame_log, competence, domain, char_order)

        #     fb_score = 0
        #     if result:
        #         fb_score = get_feedback_score(result['choice1'], result['choice2'], domain)
        #         run_feedback(win, global_clock, fb_score)

        #     save_trial_metadata(
        #         subject_id=subject_id,
        #         phase="phase_1",
        #         domain=domain,
        #         trial_id=trial_i,
        #         stim_pair_id=stim_pair_id,
        #         char_order=char_order,
        #         result=result,
        #         feedback_score=fb_score,
        #     )

        # ── Phase 2: synergy observable, competence infer (18 trials) ──────────
        for trial_i in range(P2_TRIALS):
            char_order = p2_schedule[domain][trial_i]
            stim_pair_id = f"{domain}_p2_t{trial_i:02d}"
            frame_log = make_frame_log(
                phase="phase_2",
                trial_id=trial_i,
                stim_pair_id=stim_pair_id,
            )
            run_gaussian_iti(win, global_clock, frame_log)
            result = run_phase2_trial(win, global_clock, frame_log, synergy, domain, char_order)

            fb_score = 0
            if result:
                fb_score = get_feedback_score(result['choice1'], result['choice2'], domain)
                run_feedback(win, global_clock, fb_score)

            save_trial_metadata(
                subject_id=subject_id,
                phase="phase_2",
                domain=domain,
                trial_id=trial_i,
                stim_pair_id=stim_pair_id,
                char_order=char_order,
                result=result,
                feedback_score=fb_score,
            )

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
