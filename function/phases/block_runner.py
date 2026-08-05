"""Block-level trial orchestration — schedule execution and I/O."""

import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

from function.io.frame_logger import make_frame_log, get_rows
from function.io.frame_saver import save_frame_log
from function.io.metadata import save_trial_metadata
from function.io.path_builder import build_trial_save_dir
from function.io.subject_csv import append_trial_row, append_frame_rows
from function.io.summary import save_experiment_summary
from function.phases.feedback import run_feedback
from function.config.settings import CHAR_CODE as _CHAR_CODE
from function.config.window_factory import get_shared_factory
from utils.inter_trial import run_gaussian_iti
from utils.labjack_trigger import (
    send_trigger,
    TRIG_P1_BLOCK_START, TRIG_P2_BLOCK_START, TRIG_P3_BLOCK_START,
)

_BLOCK_START_TRIG = {
    'phase_1': TRIG_P1_BLOCK_START,
    'phase_2': TRIG_P2_BLOCK_START,
    'phase_3': TRIG_P3_BLOCK_START,
}


@dataclass
class BlockConfig:
    trial_runner: Callable
    data_dict: dict
    block_domains: List[str]
    score_data: dict
    score_ranges: Optional[dict]


# ── helpers ───────────────────────────────────────────────────────────────────

def _persist_trial(subject_id, record, rows, save_dir):
    """Flush one trial's data to disk — called from a background daemon thread."""
    append_trial_row(subject_id, record)
    append_frame_rows(subject_id, rows)
    save_frame_log(rows, save_dir)


def _handle_result(result, domain, cumulative, cfg, win, handle, feedback_trig, n_per_domain, char_order=None, neon_client=None):
    """Update cumulative scores and show feedback. Returns the feedback score (0 if no result)."""
    if not result:
        return 0

    score = cfg.score_data.get(tuple(sorted([result['choice1'], result['choice2']])), {}).get(domain, 0)
    cumulative['total'] += score
    cumulative['phase'] += score
    cumulative[domain]  += score

    # char_ani codes (A/B/C/D) repeat across animals, so map via the trial's char_order
    if char_order:
        code_to_animal = {_CHAR_CODE[a]: a for a in char_order}
        animal1 = code_to_animal.get(result['choice1'])
        animal2 = code_to_animal.get(result['choice2'])
    else:
        animal1 = animal2 = None

    run_feedback(
        win, score, domain,
        cumulative_score=cumulative['total'],
        phase_score=cumulative['phase'],
        domain_scores={d: cumulative[d] for d in cfg.block_domains},
        n_trials_per_domain=n_per_domain,
        block_domains=cfg.block_domains,
        handle=handle,
        trig_code=feedback_trig,
        score_ranges=cfg.score_ranges,
        animal1=animal1,
        animal2=animal2,
        neon_client=neon_client,
    )
    return score


def _launch_save_thread(
    subject_id, block_index, phase, domain, trial_index,
    stim_pair_id, char_order, result, fb_score, frame_log, global_clock,
    session_id=None, neon_recording_id=None,
    win_size=None, slot_info=None,
):
    _, record = save_trial_metadata(
        subject_id=subject_id, block_i=block_index, phase=phase, domain=domain,
        trial_id=trial_index, stim_pair_id=stim_pair_id,
        char_order=char_order, result=result, feedback_score=fb_score,
        elapsed_time=global_clock.getTime(),
        session_id=session_id, neon_recording_id=neon_recording_id,
        win_size=win_size,
        slot_coords=slot_info.get('slot_coords') if slot_info else None,
        animal_size_px=slot_info.get('animal_size_px') if slot_info else None,
    )
    rows     = get_rows(frame_log)
    save_dir = build_trial_save_dir(subject_id, block_index, phase, domain, stim_pair_id)

    t = threading.Thread(target=_persist_trial, args=(subject_id, record, rows, save_dir), daemon=True)
    t.start()
    return t


# ── entry point ───────────────────────────────────────────────────────────────

def run_block_trials(
    block_index, phase, block_schedule, cfg,
    win, global_clock, subject_id, handle, cumulative, feedback_trig,
    neon_client=None,
):
    """
    Run all trials for one block.

    block_schedule : list of {'domain': str, 'char_order': list[str]}
    cfg            : BlockConfig — runner, data, domains, scores, ranges
    neon_client    : NeonEventClient | NullNeonClient (optional)
    File I/O is offloaded to a background thread during the following ITI.
    """
    n_per_domain      = len(block_schedule) // len(cfg.block_domains)
    save_thread       = None
    session_id        = getattr(neon_client, 'session_id',   None)
    neon_recording_id = getattr(neon_client, 'recording_id', None)
    slot_info         = get_shared_factory(win).get_slot_info()
    win_size          = (int(win.size[0]), int(win.size[1]))

    send_trigger(handle, _BLOCK_START_TRIG.get(phase, 0))
    neon_client.enqueue_events(
        "BLOCK_START",
        metadata={"task_type": "block", "phase": phase, "trial_index": block_index},
    )

    for trial_index, trial_info in enumerate(block_schedule):
        domain       = trial_info['domain']
        char_order   = trial_info['char_order']
        stim_pair_id = f"block{block_index}_{phase}_t{trial_index:02d}"
        frame_log    = make_frame_log(phase=phase, trial_id=trial_index, stim_pair_id=stim_pair_id)

        run_gaussian_iti(win, global_clock, frame_log)
        if save_thread:
            save_thread.join()

        result = cfg.trial_runner(
            win, global_clock, frame_log, cfg.data_dict, domain, char_order, handle,
            neon_client=neon_client,
        )

        fb_score = _handle_result(
            result, domain, cumulative, cfg, win, handle,
            feedback_trig, n_per_domain, char_order=char_order,
            neon_client=neon_client,
        )

        save_thread = _launch_save_thread(
            subject_id, block_index, phase, domain, trial_index,
            stim_pair_id, char_order, result, fb_score, frame_log, global_clock,
            session_id=session_id, neon_recording_id=neon_recording_id,
            win_size=win_size, slot_info=slot_info,
        )

    if save_thread:
        save_thread.join()

    save_experiment_summary(subject_id)
