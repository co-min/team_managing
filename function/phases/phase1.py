"""
Phase 1 – Competence Task

Arrow → animal mapping

"""

from psychopy import visual, event, core

from function.config.window_factory import get_shared_factory
from function.config.settings import MAX_RESPONSE_TIME, CHAR_CODE as _CHAR_CODE, COMPETENCE_COLOR as _COMPETENCE_COLOR
from function.io.frame_logger import FrameRecorder
from utils.arrow_keyboard import ArrowKeyboard
from utils.event_utils import check_escape
from utils.labjack_trigger import (
    send_trigger, send_trigger_async, reset_trigger, ANIMAL_IDX,
    TRIG_P1_STIMULUS, TRIG_P1_CHOICE1, TRIG_P1_CHOICE2,
    TRIG_P1_TRIAL_START, TRIG_P1_TRIAL_END,
)



def run_phase1_trial(win, global_clock, frame_log, competence, domain, char_order, handle=None):
    """
    Run one Phase 1 trial.

    Parameters
    ----------
    win          : psychopy.visual.Window
    global_clock : psychopy.core.Clock  (experiment-wide)
    frame_log    : FrameLog dict (mutated in-place via FrameRecorder)
    competence   : dict  {char_code: {domain: score}}  from main._load_all_data()
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

    # Reset borders to neutral – competency is hidden during choice 1
    factory.update_domain(domain)
    factory.reset_ui_states()
    for char_name in char_list:
        factory.border_stims[char_name].lineColor = 'white'

    kb  = ArrowKeyboard(win, pos=(0, factory.center_y))
    rec = FrameRecorder(frame_log, global_clock)

    send_trigger(handle, TRIG_P1_TRIAL_START)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    kb.reset_colors()
    choice1_idx = choice1_code = None
    preview_idx = None
    rt1 = None
    clock = core.Clock()

    win.callOnFlip(send_trigger_async, handle, TRIG_P1_STIMULUS)
    win.callOnFlip(reset_trigger, handle)
    while choice1_code is None:
        check_escape(win)
        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space':
                if preview_idx is not None:
                    choice1_idx  = preview_idx
                    choice1_code = _CHAR_CODE[char_list[preview_idx]]
                    rt1 = t
                    send_trigger(handle, TRIG_P1_CHOICE1 + ANIMAL_IDX[choice1_code])
            else:
                kb.reset_colors()
                idx = kb.select(pressed)
                if idx is not None:
                    preview_idx = idx
                    for name in char_list:
                        factory.border_stims[name].opacity = 0

        if choice1_code is not None:
            # Set competency colors silently so choice 2 can reveal them via hover
            for char_name in char_list:
                score = competence[_CHAR_CODE[char_name]][domain]
                factory.border_stims[char_name].lineColor = _COMPETENCE_COLOR.get(score, 'white')
            factory.draw_base_scene(phase_type='phase1')
            kb.draw()
            win.flip()
            core.wait(0.15)
            rec.log_final(win, {'response': True})
            break

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            send_trigger(handle, TRIG_P1_TRIAL_END)
            return None

        factory.draw_base_scene(phase_type='phase1')
        kb.draw()
        rec.flip_and_log(win)


    # ── Choice 2 ──────────────────────────────────────────────────────────────
    factory.set_animal_locked(char_list[choice1_idx], True)
    rec.start_segment()
    kb.reset_colors()
    kb.set_excluded(choice1_idx)
    for name in char_list:
        factory.border_stims[name].opacity = 0
    factory.border_stims[char_list[choice1_idx]].opacity = 1   
    preview2_idx = None
    rt2 = None
    clock = core.Clock()
    choice2_code = None

    win.callOnFlip(send_trigger_async, handle, TRIG_P1_STIMULUS)
    win.callOnFlip(reset_trigger, handle)
    while choice2_code is None:
        check_escape(win)
        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space':
                if preview2_idx is not None:
                    choice2_code = _CHAR_CODE[char_list[preview2_idx]]
                    rt2 = t
                    send_trigger(handle, TRIG_P1_CHOICE2 + ANIMAL_IDX[choice2_code])
            else:
                kb.reset_colors()
                idx = kb.select(pressed, excluded_idx=choice1_idx)
                if idx is not None:
                    preview2_idx = idx
                    for name in char_list:
                        factory.border_stims[name].opacity = 0
                    factory.border_stims[char_list[choice1_idx]].opacity = 1  # choice1 테두리 유지
                    factory.border_stims[char_list[idx]].opacity = 1

        if choice2_code is not None:
            factory.set_animal_locked(char_list[preview2_idx], True)
            factory.draw_base_scene(phase_type='phase1')
            kb.draw()
            win.flip()
            core.wait(0.5)
            rec.log_final(win, {'response': True})
            break

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            send_trigger(handle, TRIG_P1_TRIAL_END)
            return None

        factory.draw_base_scene(phase_type='phase1')
        kb.draw()
        rec.flip_and_log(win)

    send_trigger(handle, TRIG_P1_TRIAL_END)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
