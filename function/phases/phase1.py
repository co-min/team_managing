"""Phase 1 – Competence Task (Arrow → animal mapping)"""

from psychopy import event, core

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


def _run_choice_loop(
    win, factory, keyboard, recorder, char_list, handle,
    stim_trig, choice_trig_base,
    excluded_idx=None, locked_idx=None, confirm_wait=0.15, lock_on_confirm=False,
    show_hover_border=True,
):
    """
    Arrow-key preview + space-to-confirm loop.
    Returns (chosen_idx, char_code, rt) or (None, None, None) on timeout.
    """
    response_clock = core.Clock()
    preview_idx    = None
    stim_triggered = False

    while True:
        check_escape(win)

        for pressed, t in event.getKeys(keyList=keyboard.valid_keys + ['space'], timeStamped=response_clock):
            if pressed == 'space':
                if preview_idx is not None:
                    chosen_code = _CHAR_CODE[char_list[preview_idx]]
                    send_trigger(handle, choice_trig_base + ANIMAL_IDX[chosen_code])
                    if lock_on_confirm:
                        factory.set_animal_locked(char_list[preview_idx], True)
                    factory.draw_base_scene(phase_type='phase1')
                    keyboard.draw()
                    win.flip()
                    core.wait(confirm_wait)
                    recorder.log_final(win, {'response': True})
                    return preview_idx, chosen_code, t
            else:
                keyboard.reset_colors()
                arrow_idx = keyboard.select(pressed, excluded_idx=excluded_idx)
                if arrow_idx is not None:
                    preview_idx = arrow_idx
                    for name in char_list:
                        factory.hide_border(name)
                    if locked_idx is not None:
                        factory.show_border(char_list[locked_idx])
                    if show_hover_border:
                        factory.show_border(char_list[arrow_idx])

        if MAX_RESPONSE_TIME and response_clock.getTime() > MAX_RESPONSE_TIME:
            recorder.log_final(win, {'response': False})
            return None, None, None

        factory.draw_base_scene(phase_type='phase1')
        keyboard.draw()
        if not stim_triggered:
            win.callOnFlip(send_trigger_async, handle, stim_trig)
            win.callOnFlip(reset_trigger, handle)
            stim_triggered = True
        recorder.flip_and_log(win)


def run_phase1_trial(win, global_clock, frame_log, competence, domain, char_order, handle=None):
    """
    Run one Phase 1 trial.
    Returns dict {'choice1', 'choice2', 'rt1', 'rt2'} or None on timeout.
    """
    factory = get_shared_factory(win)
    factory.apply_layout(char_order)
    char_list = factory.char_list
    factory.update_domain(domain)
    factory.reset_ui_states()

    keyboard = ArrowKeyboard(win, pos=(0, factory.center_y))
    recorder = FrameRecorder(frame_log, global_clock)
    send_trigger(handle, TRIG_P1_TRIAL_START)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    keyboard.reset_colors()
    choice1_idx, choice1_code, rt1 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        TRIG_P1_STIMULUS, TRIG_P1_CHOICE1, confirm_wait=0.15,
        show_hover_border=False,
    )
    if choice1_code is None:
        send_trigger(handle, TRIG_P1_TRIAL_END)
        return None

    # Apply competence colors (hide_border로 숨김; Choice 2 호버 시 show_border로 표시)
    for char_name in char_list:
        factory.set_border_color(char_name, _COMPETENCE_COLOR.get(
            competence[_CHAR_CODE[char_name]][domain], 'white'
        ))
        factory.hide_border(char_name)

    # ── Choice 2 ──────────────────────────────────────────────────────────────
    factory.set_animal_locked(char_list[choice1_idx], True)
    recorder.start_segment()
    keyboard.reset_colors()
    keyboard.set_excluded(choice1_idx)
    factory.show_border(char_list[choice1_idx])

    _, choice2_code, rt2 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        TRIG_P1_STIMULUS, TRIG_P1_CHOICE2,
        excluded_idx=choice1_idx, locked_idx=choice1_idx,
        confirm_wait=1.0, lock_on_confirm=True,
    )
    if choice2_code is None:
        send_trigger(handle, TRIG_P1_TRIAL_END)
        return None

    send_trigger(handle, TRIG_P1_TRIAL_END)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
