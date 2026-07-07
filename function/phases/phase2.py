"""
Phase 2 – Synergy Task 

Trial flow
----------

"""

from psychopy import event, core

from function.config.window_factory import get_shared_factory
from function.config.settings import MAX_RESPONSE_TIME, CHAR_CODE as _CHAR_CODE, SYNERGY_COLOR as _SYNERGY_COLOR
from function.io.frame_logger import FrameRecorder
from utils.arrow_keyboard import ArrowKeyboard
from utils.event_utils import check_escape
from utils.labjack_trigger import (
    send_trigger, send_trigger_async, reset_trigger, ANIMAL_IDX,
    TRIG_P2_STIMULUS, TRIG_P2_CHOICE1, TRIG_P2_CHOICE2,
    TRIG_P2_TRIAL_START, TRIG_P2_TRIAL_END,
)



def _apply_synergy_colors(factory, char_list, pivot_idx, pivot_code, synergy, also_hide_idx=None):
    """Color every non-pivot block by its synergy score with the pivot animal."""
    for i, char_name in enumerate(char_list):
        factory.border_stims[char_name].opacity = 0
        if i == pivot_idx or i == also_hide_idx:
            factory.block_stims[char_name].opacity = 0
            continue
        other_code = _CHAR_CODE[char_name]
        score = synergy.get(tuple(sorted([pivot_code, other_code])), 0)
        color = _SYNERGY_COLOR.get(score, 'white')
        factory.block_stims[char_name].setFillColor(color)
        factory.block_stims[char_name].opacity = 1


def _run_choice_loop(win, factory, kb, rec, char_list, synergy, handle,
                     stim_trig, choice_trig_base, excluded_idx=None,
                     freeze_colors=False, confirm_freeze=0.15, show_confirm_overlay=False):
    """
    Arrow-key preview + space-to-confirm loop.

    freeze_colors=True: synergy bar colors are not updated on arrow-key navigation.
    Returns (chosen_idx, char_code, rt) or (None, None, None) on timeout.
    """
    clock = core.Clock()
    preview_idx = None
    _stim_sent = False

    while True:
        check_escape(win)
        confirmed_idx = confirmed_code = confirmed_rt = None

        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space':
                if preview_idx is not None:
                    confirmed_idx  = preview_idx
                    confirmed_code = _CHAR_CODE[char_list[preview_idx]]
                    confirmed_rt   = t
                    send_trigger(handle, choice_trig_base + ANIMAL_IDX[confirmed_code])
            else:
                kb.reset_colors()
                idx = kb.select(pressed, excluded_idx=excluded_idx)
                if idx is not None:
                    preview_idx = idx
                    if not freeze_colors:
                        _apply_synergy_colors(
                            factory, char_list, idx, _CHAR_CODE[char_list[idx]], synergy,
                            also_hide_idx=excluded_idx,
                        )
                    # 바깥 하얀색 테두리
                    factory.border_stims[char_list[idx]].opacity = 0

        if confirmed_code is not None:
            factory.border_stims[char_list[confirmed_idx]].opacity = 0
            if show_confirm_overlay:
                factory.set_animal_locked(char_list[confirmed_idx], True)
            factory.draw_base_scene(phase_type='phase2')
            kb.draw()
            win.flip()
            core.wait(confirm_freeze)
            rec.log_final(win, {'response': True})
            return confirmed_idx, confirmed_code, confirmed_rt

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            return None, None, None

        factory.draw_base_scene(phase_type='phase2')
        kb.draw()
        if not _stim_sent:
            win.callOnFlip(send_trigger_async, handle, stim_trig)
            win.callOnFlip(reset_trigger, handle)
            _stim_sent = True
        rec.flip_and_log(win)


def run_phase2_trial(win, global_clock, frame_log, synergy, domain, char_order, handle=None):
    """
    Run one Phase 2 trial.

    Parameters
    ----------
    win          : psychopy.visual.Window
    global_clock : psychopy.core.Clock  (experiment-wide)
    frame_log    : FrameLog dict (mutated in-place via FrameRecorder)
    synergy      : dict  {(charA, charB): int}  sorted-tuple key, from main._load_all_data()
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

    send_trigger(handle, TRIG_P2_TRIAL_START)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    kb.reset_colors()
    choice1_idx, choice1_code, rt1 = _run_choice_loop(
        win, factory, kb, rec, char_list, synergy,
        handle, TRIG_P2_STIMULUS, TRIG_P2_CHOICE1,
    )
    if choice1_code is None:
        send_trigger(handle, TRIG_P2_TRIAL_END)
        return None

    # Lock Choice 1; seed synergy colours for Choice 2 resting state
    factory.set_animal_locked(char_list[choice1_idx], True)
    _apply_synergy_colors(factory, char_list, choice1_idx, choice1_code, synergy)

    # ── Choice 2 ──────────────────────────────────────────────────────────────
    rec.start_segment()
    kb.reset_colors()
    kb.set_excluded(choice1_idx)
    _, choice2_code, rt2 = _run_choice_loop(
        win, factory, kb, rec, char_list, synergy,
        handle, TRIG_P2_STIMULUS, TRIG_P2_CHOICE2,
        excluded_idx=choice1_idx,
        freeze_colors=True,
        confirm_freeze=0.5,
        show_confirm_overlay=True,
    )
    if choice2_code is None:
        send_trigger(handle, TRIG_P2_TRIAL_END)
        return None

    send_trigger(handle, TRIG_P2_TRIAL_END)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
