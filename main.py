import random
from psychopy import core
from initiate import initiate
from function.config.settings import (
    MISSION_MODE,
    P1_TRIALS, P2_TRIALS, INST_PHASE1, INST_PHASE2,
    DOMAINS, P2_DOMAINS, DOMAIN_ORDER,
    PRACTICE_MODE, BLOCK_PHASES,
)
from function.practice.practice_loop import run_practice
from function.io.data_loader import load_all_data
from function.config.window_factory import get_shared_factory
from function.io.frame_marker import init_marker
from function.io.path_builder import get_subject_dir
from function.phases.block_runner import BlockConfig, run_block_trials
from function.phases.phase1 import run_phase1_trial
from function.phases.phase2 import run_phase2_trial
from function.phases.feedback import P2_SCORE_RANGES
from function.phases.ending import run_ending
from function.config.settings import NEON_SHUTDOWN_FLUSH_TIMEOUT_S
from function.io.metadata import save_session_metadata
from utils.labjack_trigger import send_trigger, TRIG_TASK_START
from utils.screen_utils import show_instructions
from utils.neon_client import save_neon_event_log


_SCHEDULE_SEED = 42


def _generate_block_schedules(animal_groups, block_phases):
    """Build per-block trial schedules (one schedule per animal group)."""
    rng = random.Random(_SCHEDULE_SEED)
    schedules = []
    for group, phase in zip(animal_groups, block_phases):
        if MISSION_MODE == 3 and phase == 'phase_2':
            n_trials, domains = P2_TRIALS, P2_DOMAINS
        else:
            n_trials, domains = P1_TRIALS, DOMAINS

        trials_per_domain = n_trials // len(domains)
        if DOMAIN_ORDER == 'sequential':
            domain_sequence = [d for d in domains for _ in range(trials_per_domain)]
        else:
            domain_sequence = domains * trials_per_domain
            rng.shuffle(domain_sequence)

        schedules.append([
            {'domain': d, 'char_order': rng.sample(group, len(group))}
            for d in domain_sequence
        ])
    return schedules


def _get_block_config(phase, competence, synergy, score, phase2_score) -> BlockConfig:
    if phase == 'phase_1':
        return BlockConfig(
            trial_runner=run_phase1_trial,
            data_dict=competence,
            block_domains=DOMAINS,
            score_data=score,
            score_ranges=None,
        )
    return BlockConfig(
        trial_runner=run_phase2_trial,
        data_dict=synergy,
        block_domains=P2_DOMAINS if MISSION_MODE == 3 else DOMAINS,
        score_data=phase2_score if MISSION_MODE == 3 else score,
        score_ranges=P2_SCORE_RANGES if MISSION_MODE == 3 else None,
    )


def main() -> None:
    ctx               = initiate()
    win               = ctx.win
    subject_id        = ctx.subject_id
    handle            = ctx.handle
    neon_client       = ctx.neon_client
    global_clock      = core.Clock()

    init_marker(win)

    if PRACTICE_MODE:
        run_practice(win)

    competence, synergy, score, animal_groups, phase2_score = load_all_data()
    factory = get_shared_factory(win, animal_groups)
    save_session_metadata(
        subject_id=subject_id,
        session_id=ctx.session_id,
        win_size=(int(win.size[0]), int(win.size[1])),
        slot_info=factory.get_slot_info(),
        neon_recording_id=ctx.neon_recording_id,
    )
    block_schedules = _generate_block_schedules(animal_groups, BLOCK_PHASES)
    cumulative = {'total': 0, 'phase': 0, **{d: 0 for d in DOMAINS}}

    try:
        send_trigger(handle, TRIG_TASK_START)
        neon_client.enqueue_events("TASK_START", metadata={"task_type": "experiment"})

        for block_index, (phase, block_schedule) in enumerate(zip(BLOCK_PHASES, block_schedules)):
            cfg = _get_block_config(phase, competence, synergy, score, phase2_score)
            instruction = INST_PHASE1 if phase == 'phase_1' else INST_PHASE2
            show_instructions(win, instruction.format(
                block_num=block_index + 1, total_blocks=len(BLOCK_PHASES)
            ))

            cumulative['phase'] = 0
            for d in DOMAINS:
                cumulative[d] = 0

            run_block_trials(
                block_index, phase, block_schedule, cfg,
                win, global_clock, subject_id, handle, cumulative,
                neon_client=neon_client,
            )
        run_ending(win, subject_id, cumulative['total'], global_clock.getTime())
    finally:
        neon_client.close(NEON_SHUTDOWN_FLUSH_TIMEOUT_S)
        save_neon_event_log(
            get_subject_dir(subject_id),
            neon_client.event_log,
        )

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
