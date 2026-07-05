import random
import threading

from psychopy import core

from initiate import initiate
from utils.inter_trial import run_gaussian_iti
from function.config.settings import P1_TRIALS, P2_TRIALS
from function.io.data_loader import load_all_data
from function.io.frame_logger import make_frame_log, get_rows
from function.io.frame_saver import save_frame_log
from function.io.metadata import save_trial_metadata
from function.io.path_builder import build_trial_save_dir
from function.io.subject_csv import append_trial_row, append_frame_rows
from function.phases.phase1 import run_phase1_trial
from function.phases.phase2 import run_phase2_trial
from function.phases.feedback import run_feedback
from utils.labjack_trigger import TRIG_P1_FEEDBACK, TRIG_P2_FEEDBACK


DOMAINS = ['cooking', 'repairing', 'tennis']

_SCHEDULE_SEED = 42
_ANIMALS       = ['duck', 'frog', 'panda', 'rabbit']
_TRIG_FEEDBACK = {'phase_1': TRIG_P1_FEEDBACK, 'phase_2': TRIG_P2_FEEDBACK}


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
        )
        rows     = get_rows(frame_log)
        save_dir = build_trial_save_dir(subject_id, phase, stim_pair_id)
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

    competence, synergy, score = load_all_data()
    p1_schedule, p2_schedule   = _generate_schedules()
    cumul = {d: {'phase_1': 0, 'phase_2': 0} for d in DOMAINS}

    for domain in DOMAINS:
        _run_phase_trials('phase_1', P1_TRIALS, p1_schedule, run_phase1_trial,
                          competence, domain, win, global_clock, subject_id, handle, cumul, score)
        _run_phase_trials('phase_2', P2_TRIALS, p2_schedule, run_phase2_trial,
                          synergy, domain, win, global_clock, subject_id, handle, cumul, score)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
