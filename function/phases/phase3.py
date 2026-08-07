"""
Phase 3 – Choice Task (no competence cues)

Identical interaction to Phase 1 but borders are NOT coloured by
competence scores — animals are shown with no visual scoring hints.
"""

from psychopy import event, core

from function.config.window_factory import get_shared_factory
from function.config.settings import MAX_RESPONSE_TIME, CHAR_CODE as _CHAR_CODE
from function.io.frame_logger import FrameRecorder
from utils.arrow_keyboard import ArrowKeyboard
from utils.event_utils import check_escape
from utils.event_dispatch import (
    callonflip_choice_onset,
    on_choice_lj, on_choice_neon,
    on_trial_end,
)


def _run_choice_loop(win, factory, keyboard, recorder, char_list, handle,
                     trial_index, slot,
                     excluded_idx=None, locked_border_idx=None,
                     neon_client=None):
    """Arrow-key preview + space-to-confirm loop for Phase 3.

    Fires callonflip_choice_onset on the first frame (async LJ latch + Neon onset).
    Fires on_choice_lj + on_choice_neon immediately on space-press.
    Returns (chosen_idx, char_code, rt) on confirm, or (None, None, None) on timeout.
    """
    response_clock  = core.Clock()
    preview_idx     = None
    _onset_pending  = True

    while True:
        check_escape(win)

        for pressed, t in event.getKeys(keyList=keyboard.valid_keys + ['space'], timeStamped=response_clock):
            if pressed == 'space' and preview_idx is not None:
                animal      = char_list[preview_idx]
                chosen_code = _CHAR_CODE[animal]
                on_choice_lj(handle, 3, slot, animal)
                on_choice_neon(neon_client, 3, trial_index, slot, animal)
                factory.draw_base_scene(phase_type='phase3')
                keyboard.draw()
                win.flip()
                core.wait(0.15)
                recorder.log_final(win, {'response': True})
                return preview_idx, chosen_code, t
            elif pressed != 'space':
                keyboard.reset_colors()
                arrow_idx = keyboard.select(pressed, excluded_idx=excluded_idx)
                if arrow_idx is not None:
                    preview_idx = arrow_idx
                    for name in char_list:
                        factory.border_stims[name].opacity = 0
                    if locked_border_idx is not None:
                        factory.border_stims[char_list[locked_border_idx]].opacity = 1
                    factory.border_stims[char_list[arrow_idx]].opacity = 1

        if MAX_RESPONSE_TIME and response_clock.getTime() > MAX_RESPONSE_TIME:
            on_choice_neon(neon_client, 3, trial_index, slot, "", outcome="TIMEOUT")
            recorder.log_final(win, {'response': False})
            return None, None, None

        factory.draw_base_scene(phase_type='phase3')
        keyboard.draw()
        if _onset_pending:
            callonflip_choice_onset(win, neon_client, handle, 3, trial_index, slot)
            _onset_pending = False
        recorder.flip_and_log(win)


def run_phase3_trial(win, global_clock, frame_log, _data, domain, char_order, handle=None, neon_client=None):
    """
    Run one Phase 3 trial.

    Parameters
    ----------
    win          : psychopy.visual.Window
    global_clock : psychopy.core.Clock  (experiment-wide)
    frame_log    : FrameLog dict (mutated in-place via FrameRecorder)
    _data        : unused — kept for uniform _run_phase_trials signature
    domain       : str   'cooking' | 'repairing' | 'tennis'
    char_order   : list  [up_animal, down_animal, right_animal, left_animal]
    neon_client  : NeonEventClient | NullNeonClient (optional)

    Returns
    -------
    dict  {'choice1': char_code, 'choice2': char_code, 'rt1': float, 'rt2': float}
    or None on timeout
    """
    trial_index = frame_log.get("trial_id", 0)

    factory = get_shared_factory(win)
    factory.apply_layout(char_order)
    char_list = factory.char_list

    factory.update_domain(domain)
    factory.reset_ui_states()

    keyboard = ArrowKeyboard(win, pos=(0, factory.center_y))
    recorder = FrameRecorder(frame_log, global_clock)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    keyboard.reset_colors()
    choice1_idx, choice1_code, rt1 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        trial_index=trial_index, slot=1,
        neon_client=neon_client,
    )
    if choice1_code is None:
        on_trial_end(neon_client, handle, 3, trial_index)
        return None

    # ── Choice 2 ──────────────────────────────────────────────────────────────
    factory.set_animal_locked(char_list[choice1_idx], True)
    for name in char_list:
        factory.border_stims[name].opacity = 0
    factory.border_stims[char_list[choice1_idx]].opacity = 1
    recorder.start_segment()
    keyboard.reset_colors()
    keyboard.set_excluded(choice1_idx)

    _, choice2_code, rt2 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        trial_index=trial_index, slot=2,
        excluded_idx=choice1_idx,
        locked_border_idx=choice1_idx,
        neon_client=neon_client,
    )
    if choice2_code is None:
        on_trial_end(neon_client, handle, 3, trial_index)
        return None

    on_trial_end(neon_client, handle, 3, trial_index)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
