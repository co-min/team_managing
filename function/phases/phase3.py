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
from utils.labjack_trigger import (
    send_trigger, send_trigger_async, reset_trigger, ANIMAL_IDX,
    TRIG_P3_STIMULUS, TRIG_P3_CHOICE1, TRIG_P3_CHOICE2,
    TRIG_P3_TRIAL_START, TRIG_P3_TRIAL_END,
)



def _run_choice_loop(win, factory, kb, rec, char_list, handle,
                     stim_trig, choice_trig_base,
                     excluded_idx=None, locked_border_idx=None):
    """Arrow-key preview + space-to-confirm loop for Phase 3.

    Returns (chosen_idx, char_code, rt) on confirm, or (None, None, None) on timeout.
    """
    clock = core.Clock()
    preview_idx = None
    stim_triggered = False

    while True:
        check_escape(win)

        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space' and preview_idx is not None:
                code = _CHAR_CODE[char_list[preview_idx]]
                send_trigger(handle, choice_trig_base + ANIMAL_IDX[code])
                factory.draw_base_scene(phase_type='phase3')
                kb.draw()
                win.flip()
                core.wait(0.15)
                rec.log_final(win, {'response': True})
                return preview_idx, code, t
            elif pressed != 'space':
                kb.reset_colors()
                idx = kb.select(pressed, excluded_idx=excluded_idx)
                if idx is not None:
                    preview_idx = idx
                    for name in char_list:
                        factory.border_stims[name].opacity = 0
                    if locked_border_idx is not None:
                        factory.border_stims[char_list[locked_border_idx]].opacity = 1
                    factory.border_stims[char_list[idx]].opacity = 1

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            return None, None, None

        factory.draw_base_scene(phase_type='phase3')
        kb.draw()
        if not stim_triggered:
            win.callOnFlip(send_trigger_async, handle, stim_trig)
            win.callOnFlip(reset_trigger, handle)
            stim_triggered = True
        rec.flip_and_log(win)


def run_phase3_trial(win, global_clock, frame_log, _data, domain, char_order, handle=None):
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

    Returns
    -------
    dict  {'choice1': char_code, 'choice2': char_code, 'rt1': float, 'rt2': float}
    or None on timeout
    """
    factory = get_shared_factory(win)
    factory.apply_layout(char_order)
    char_list = factory.char_list

    factory.update_domain(domain)
    factory.reset_ui_states()

    kb  = ArrowKeyboard(win, pos=(0, factory.center_y))
    rec = FrameRecorder(frame_log, global_clock)

    send_trigger(handle, TRIG_P3_TRIAL_START)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    kb.reset_colors()
    choice1_idx, choice1_code, rt1 = _run_choice_loop(
        win, factory, kb, rec, char_list, handle,
        TRIG_P3_STIMULUS, TRIG_P3_CHOICE1,
    )
    if choice1_code is None:
        send_trigger(handle, TRIG_P3_TRIAL_END)
        return None

    # ── Choice 2 ──────────────────────────────────────────────────────────────
    factory.set_animal_locked(char_list[choice1_idx], True)
    for name in char_list:
        factory.border_stims[name].opacity = 0
    factory.border_stims[char_list[choice1_idx]].opacity = 1
    rec.start_segment()
    kb.reset_colors()
    kb.set_excluded(choice1_idx)

    _, choice2_code, rt2 = _run_choice_loop(
        win, factory, kb, rec, char_list, handle,
        TRIG_P3_STIMULUS, TRIG_P3_CHOICE2,
        excluded_idx=choice1_idx,
        locked_border_idx=choice1_idx,
    )
    if choice2_code is None:
        send_trigger(handle, TRIG_P3_TRIAL_END)
        return None

    send_trigger(handle, TRIG_P3_TRIAL_END)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
