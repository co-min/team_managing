import random
from psychopy import core
from initiate import initiate
from function.config.settings import (
    MISSION_MODE,
    P1_TRIALS, P2_TRIALS, INST_PHASE1, INST_PHASE2,
    DOMAINS, P2_DOMAINS, DOMAIN_ORDER,
)
from function.io.data_loader import load_all_data
from function.config.window_factory import get_shared_factory
from function.phases.block_runner import BlockConfig, run_block_trials
from function.phases.phase1 import run_phase1_trial
from function.phases.phase2 import run_phase2_trial
from function.phases.feedback import P2_SCORE_RANGES
from utils.labjack_trigger import TRIG_P1_FEEDBACK, TRIG_P2_FEEDBACK, TRIG_P3_FEEDBACK
from utils.screen_utils import show_instructions


# Block 1/3/5: Synergy Infer, Competency Shown  → run_phase1_trial + competence data
# Block 2/4/6: Synergy Shown, Competency Infer  → run_phase2_trial + synergy data
BLOCK_PHASES = ['phase_1', 'phase_2', 'phase_1', 'phase_2', 'phase_1', 'phase_2']

_SCHEDULE_SEED = 42
_FEEDBACK_TRIGGERS = {
    'phase_1': TRIG_P1_FEEDBACK,
    'phase_2': TRIG_P2_FEEDBACK,
    'phase_3': TRIG_P3_FEEDBACK,
}


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
    ctx          = initiate()
    win          = ctx.win
    subject_id   = ctx.subject_id
    handle       = ctx.handle
    global_clock = core.Clock()

    competence, synergy, score, animal_groups, phase2_score = load_all_data()
    get_shared_factory(win, animal_groups)
    block_schedules = _generate_block_schedules(animal_groups, BLOCK_PHASES)
    cumulative = {'total': 0, 'phase': 0, **{d: 0 for d in DOMAINS}}

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
            feedback_trig=_FEEDBACK_TRIGGERS[phase],
        )

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
