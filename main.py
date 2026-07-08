import random
import threading
from psychopy import core
from initiate import initiate
from utils.inter_trial import run_gaussian_iti
from function.config.settings import P1_TRIALS, INST_PHASE1, INST_PHASE2, DOMAINS, DOMAIN_ORDER
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
from utils.screen_utils import show_instructions


# Block 1/3/5: Synergy Infer, Competency Shown  → run_phase1_trial + competence data
# Block 2/4/6: Synergy Shown, Competency Infer  → run_phase2_trial + synergy data
BLOCK_PHASES = ['phase_1', 'phase_2', 'phase_1', 'phase_2', 'phase_1', 'phase_2']

_SCHEDULE_SEED = 42
_TRIG_FEEDBACK = {'phase_1': TRIG_P1_FEEDBACK, 'phase_2': TRIG_P2_FEEDBACK, 'phase_3': TRIG_P3_FEEDBACK}


def _generate_block_schedules(animal_groups):
    """
    Build per-block trial schedules (one schedule per animal group).

    Each block uses a single animal group for all P1_TRIALS (18) trials.
    Domains are distributed evenly (6 per domain) and shuffled.
    char_order is a random permutation of the block's 4 animals per trial.

    Returns
    -------
    list of len(animal_groups) lists, each containing P1_TRIALS dicts:
        {'domain': str, 'char_order': list[str]}
    """
    rng      = random.Random(_SCHEDULE_SEED)
    n_trials = P1_TRIALS  # 18

    schedules = []
    for group in animal_groups:
        n_per = n_trials // len(DOMAINS)
        if DOMAIN_ORDER == 'sequential':
            domain_seq = [d for d in DOMAINS for _ in range(n_per)]
        else:
            domain_seq = DOMAINS * n_per
            rng.shuffle(domain_seq)

        block_sched = [
            {'domain': d, 'char_order': rng.sample(group, len(group))}
            for d in domain_seq
        ]
        schedules.append(block_sched)

    return schedules


def _persist_trial(subject_id, record, rows, save_dir):
    """Flush one trial's data to disk — runs in a background thread during the next ITI."""
    append_trial_row(subject_id, record)
    append_frame_rows(subject_id, rows)
    save_frame_log(rows, save_dir)


def _get_feedback_score(score, c1, c2, domain):
    return score.get(tuple(sorted([c1, c2])), {}).get(domain, 0)


def _run_block_trials(
    block_i, phase, block_schedule, run_fn, data_dict,
    win, global_clock, subject_id, handle, cumul, score,
):
    """
    Run all 18 trials for one block.

    block_schedule : list of {'domain': str, 'char_order': list[str]}
    File I/O is offloaded to a background thread during the following ITI.
    """
    save_thread  = None
    n_per_domain = P1_TRIALS // len(DOMAINS)  # 6

    for trial_i, trial_info in enumerate(block_schedule):
        domain     = trial_info['domain']
        char_order = trial_info['char_order']
        stim_pair_id = f"block{block_i}_{phase}_t{trial_i:02d}"
        frame_log  = make_frame_log(phase=phase, trial_id=trial_i, stim_pair_id=stim_pair_id)

        run_gaussian_iti(win, global_clock, frame_log)

        if save_thread:
            save_thread.join()

        result = run_fn(win, global_clock, frame_log, data_dict, domain, char_order, handle)

        fb_score = 0
        if result:
            fb_score = _get_feedback_score(score, result['choice1'], result['choice2'], domain)
            cumul['total'] += fb_score
            cumul['phase'] += fb_score
            cumul[domain]  += fb_score
            run_feedback(win, fb_score, domain,
                         cumulative_score=cumul['total'],
                         phase_score=cumul['phase'],
                         domain_scores={d: cumul[d] for d in DOMAINS},
                         n_trials_per_domain=n_per_domain,
                         handle=handle, trig_code=_TRIG_FEEDBACK[phase])

        _, record = save_trial_metadata(
            subject_id=subject_id, block_i=block_i, phase=phase, domain=domain,
            trial_id=trial_i, stim_pair_id=stim_pair_id,
            char_order=char_order, result=result, feedback_score=fb_score,
            elapsed_time=global_clock.getTime(),
        )
        rows     = get_rows(frame_log)
        save_dir = build_trial_save_dir(subject_id, block_i, phase, domain, stim_pair_id)
        save_thread = threading.Thread(
            target=_persist_trial, args=(subject_id, record, rows, save_dir), daemon=True,
        )
        save_thread.start()

    if save_thread:
        save_thread.join()


def main() -> None:
    ctx          = initiate()
    win          = ctx.win
    subject_id   = ctx.subject_id
    handle       = ctx.handle
    global_clock = core.Clock()

    competence, synergy, score, animal_groups = load_all_data()
    get_shared_factory(win, animal_groups)
    block_schedules = _generate_block_schedules(animal_groups)
    cumul = {'total': 0, 'phase': 0, **{d: 0 for d in DOMAINS}}

    total_blocks = len(BLOCK_PHASES)
    for block_i, (phase, block_sched) in enumerate(zip(BLOCK_PHASES, block_schedules)):
        block_fmt = {'block_num': block_i + 1, 'total_blocks': total_blocks}
        if phase == 'phase_1':
            run_fn    = run_phase1_trial
            data_dict = competence
            show_instructions(win, INST_PHASE1.format(**block_fmt))
        else:
            run_fn    = run_phase2_trial
            data_dict = synergy
            show_instructions(win, INST_PHASE2.format(**block_fmt))

        cumul['phase'] = 0
        for d in DOMAINS:
            cumul[d] = 0

        _run_block_trials(
            block_i, phase, block_sched, run_fn, data_dict,
            win, global_clock, subject_id, handle, cumul, score,
        )

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
