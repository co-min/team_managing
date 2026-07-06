import random
import threading

from psychopy import core

from initiate import initiate
from utils.inter_trial import run_gaussian_iti
from function.config.settings import P1_TRIALS, P2_TRIALS, P3_TRIALS
from function.io.data_loader import load_all_data
from function.io.frame_logger import make_frame_log, get_rows
from function.io.frame_saver import save_frame_log
from function.io.metadata import save_trial_metadata
from function.io.path_builder import build_trial_save_dir
from function.io.subject_csv import append_trial_row, append_frame_rows
from function.config.window_factory import get_shared_factory
from function.phases.phase1 import run_phase1_trial
from function.phases.phase2 import run_phase2_trial
from function.phases.phase3 import run_phase3_trial
from function.phases.feedback import run_feedback
from utils.labjack_trigger import TRIG_P1_FEEDBACK, TRIG_P2_FEEDBACK, TRIG_P3_FEEDBACK


DOMAINS = ['cooking', 'repairing', 'tennis']

_SCHEDULE_SEED = 42
_TRIG_FEEDBACK = {'phase_1': TRIG_P1_FEEDBACK, 'phase_2': TRIG_P2_FEEDBACK, 'phase_3': TRIG_P3_FEEDBACK}


def _generate_schedules(animal_groups):
    """
    Build per-domain, per-phase lists of animal orderings.

    animal_groups[g][s] = the s-th char_ani slot's animal in group g.
    Each slot (A/B/C/D) independently cycles through its n_g animals
    in balanced blocks, so every animal appears equally often.

    Block structure: n_trials // n_g blocks, each block of n_g trials
    contains each slot-animal exactly once (shuffled within the block).
    Position order within each trial is also randomised.

    Returns
    -------
    p1_schedule : {domain: [char_order_t0, ...]}  length = P1_TRIALS
    p2_schedule : {domain: [char_order_t0, ...]}  length = P2_TRIALS
    """
    rng      = random.Random(_SCHEDULE_SEED)
    n_g      = len(animal_groups)     # number of groups (3)
    n_s      = len(animal_groups[0])  # number of char_ani slots (4)

    # per_slot[s] = [animal_for_slot_s_in_group_0, group_1, group_2]
    per_slot = [[animal_groups[g][s] for g in range(n_g)] for s in range(n_s)]

    def make_schedule(n_trials):
        order = []
        for _ in range(n_trials // n_g):
            # Each slot shuffles its n_g animals independently for this block
            shuffled = [rng.sample(per_slot[s], n_g) for s in range(n_s)]
            for t in range(n_g):
                trial = [shuffled[s][t] for s in range(n_s)]
                rng.shuffle(trial)   # randomise up/down/left/right positions
                order.append(trial)
        return order

    p1 = {d: make_schedule(P1_TRIALS) for d in DOMAINS}
    p2 = {d: make_schedule(P2_TRIALS) for d in DOMAINS}
    # p3 = {d: make_schedule(P3_TRIALS) for d in DOMAINS}
    # return p1, p2, p3
    return p1, p2


def _persist_trial(subject_id, record, rows, save_dir):
    """Flush one trial's data to disk — runs in a background thread during the next ITI."""
    append_trial_row(subject_id, record)
    append_frame_rows(subject_id, rows)
    save_frame_log(rows, save_dir)


def _get_feedback_score(score, c1, c2, domain):
    return score.get(tuple(sorted([c1, c2])), {}).get(domain, 0)


def _run_phase_trials(
    phase, n_trials, schedule, run_fn, data_dict,
    domain, win, global_clock, subject_id, handle, cumul, score,
):
    """
    Run all trials for one phase/domain pair.

    File I/O for each trial is offloaded to a background thread so that
    saving overlaps with the following ITI instead of blocking it.
    The thread is joined after the ITI (before the next trial begins),
    guaranteeing writes complete before the next save starts.
    """
    save_thread = None

    for trial_i in range(n_trials):
        char_order   = schedule[domain][trial_i]
        stim_pair_id = f"{domain}_{phase}_t{trial_i:02d}"
        frame_log    = make_frame_log(phase=phase, trial_id=trial_i, stim_pair_id=stim_pair_id)

        run_gaussian_iti(win, global_clock, frame_log)  # saves from previous trial run here

        if save_thread:
            save_thread.join()  # must finish before this trial's saves can start

        result = run_fn(win, global_clock, frame_log, data_dict, domain, char_order, handle)

        fb_score = 0
        if result:
            fb_score = _get_feedback_score(score, result['choice1'], result['choice2'], domain)
            cumul[domain][phase] += int(round(fb_score)) + 4
            run_feedback(win, fb_score, domain,
                         cumulative_score=cumul[domain][phase],
                         handle=handle, trig_code=_TRIG_FEEDBACK[phase])

        _, record = save_trial_metadata(
            subject_id=subject_id, phase=phase, domain=domain,
            trial_id=trial_i, stim_pair_id=stim_pair_id,
            char_order=char_order, result=result, feedback_score=fb_score,
            elapsed_time=global_clock.getTime(),
        )
        rows     = get_rows(frame_log)
        save_dir = build_trial_save_dir(subject_id, phase, domain, stim_pair_id)
        save_thread = threading.Thread(
            target=_persist_trial, args=(subject_id, record, rows, save_dir), daemon=True,
        )
        save_thread.start()

    if save_thread:
        save_thread.join()  # last trial's saves must complete before phase ends


def main() -> None:
    ctx          = initiate()
    win          = ctx.win
    subject_id   = ctx.subject_id
    handle       = ctx.handle
    global_clock = core.Clock()

    competence, synergy, score, animal_groups = load_all_data()
    get_shared_factory(win, animal_groups)
    p1_schedule, p2_schedule = _generate_schedules(animal_groups)
    cumul = {d: {'phase_1': 0, 'phase_2': 0} for d in DOMAINS}

    # Phase 1: domain 1, 2, 3 순서로 각 18 trials (총 54 trials)
    for domain in DOMAINS:
        _run_phase_trials('phase_1', P1_TRIALS, p1_schedule, run_phase1_trial,
                            competence, domain, win, global_clock, subject_id, handle, cumul, score)

    # Phase 2: domain 1, 2, 3 순서로 각 18 trials (총 54 trials)
    for domain in DOMAINS:
        _run_phase_trials('phase_2', P2_TRIALS, p2_schedule, run_phase2_trial,
                            synergy, domain, win, global_clock, subject_id, handle, cumul, score)


    win.close()
    core.quit()


if __name__ == "__main__":
    main()
