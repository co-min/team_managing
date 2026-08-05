"""Phase 1 – Competence Task (Arrow → animal mapping)"""

from psychopy import event, core

from function.config.window_factory import get_shared_factory
from function.config.settings import MAX_RESPONSE_TIME, CHOICE_GAP, DOMAIN_ONSET_DURATION, CHAR_CODE as _CHAR_CODE, get_comp_color as _get_comp_color
from function.io.frame_logger import FrameRecorder
from function.io.frame_marker import get_shared_marker
from utils.arrow_keyboard import ArrowKeyboard
from utils.labjack_trigger import (
    send_trigger, ANIMAL_IDX,
    TRIG_P1_CHOICE1, TRIG_P1_CHOICE2,
    TRIG_P1_TRIAL_START, TRIG_P1_TRIAL_END,
    TRIG_P1_CHOICE_ONSET,
)
from utils.neon_client import section_start_events, section_end_events

from function.phases.common import show_domain_onset as _show_domain_onset


def _run_choice_loop(
    win, factory, keyboard, recorder, char_list, handle,
    choice_trig_base,
    excluded_idx=None, locked_idx=None, confirm_wait=0.15, lock_on_confirm=False,
    show_hover_border=True,
    onset_trigger=None,
    neon_client=None, neon_onset_events=None, neon_segment_label=None, neon_trial_index=None,
):
    """
    Arrow-key preview + space-to-confirm loop.

    Neon section events are registered via callOnFlip at stimulus onset and
    enqueued directly at response / timeout so timestamps are as accurate as
    possible without blocking the flip loop.

    Returns (chosen_idx, char_code, rt) or (None, None, None) on timeout.
    """
    response_clock       = core.Clock()
    preview_idx          = None
    _onset_pending       = onset_trigger
    _neon_onset_pending  = (neon_client is not None and neon_onset_events is not None)

    while True:
        for pressed, t in event.getKeys(keyList=keyboard.valid_keys + ['space', 'escape'], timeStamped=response_clock):
            if pressed == 'escape':
                win.close()
                core.quit()
            if pressed == 'space':
                if preview_idx is not None:
                    chosen_code = _CHAR_CODE[char_list[preview_idx]]
                    send_trigger(handle, choice_trig_base + ANIMAL_IDX[char_list[preview_idx]])
                    if neon_client and neon_segment_label and neon_trial_index is not None:
                        neon_client.enqueue_events(
                            section_end_events(neon_trial_index, f"{neon_segment_label}_RESPONSE"),
                            metadata={"task_type": "trial", "phase": neon_segment_label,
                                      "trial_index": neon_trial_index},
                        )
                    if lock_on_confirm:
                        factory.set_animal_locked(char_list[preview_idx], True)
                    factory.draw_base_scene(phase_type='phase1')
                    keyboard.draw()
                    win.flip()
                    core.wait(confirm_wait)
                    event.clearEvents()
                    factory.draw_base_scene(phase_type='phase1')
                    keyboard.draw()
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
            if neon_client and neon_segment_label and neon_trial_index is not None:
                neon_client.enqueue_events(
                    section_end_events(neon_trial_index, f"{neon_segment_label}_TIMEOUT"),
                    metadata={"task_type": "trial", "phase": neon_segment_label,
                            "trial_index": neon_trial_index},
                )
            recorder.log_final(win, {'response': False})
            return None, None, None

        factory.draw_base_scene(phase_type='phase1')
        keyboard.draw()
        if _onset_pending is not None:
            win.callOnFlip(send_trigger, handle, _onset_pending)
            _onset_pending = None
        if _neon_onset_pending:
            neon_client.call_on_flip(
                win, neon_onset_events,
                task_type="trial", phase=neon_segment_label, trial_index=neon_trial_index,
            )
            _neon_onset_pending = False
        recorder.flip_and_log(win)


def run_phase1_trial(win, global_clock, frame_log, competence, domain, char_order, handle=None, neon_client=None):
    """
    Run one Phase 1 trial.
    Returns dict {'choice1', 'choice2', 'rt1', 'rt2'} or None on timeout.
    """
    trial_index = frame_log.get("trial_id", 0)

    event.clearEvents()
    factory = get_shared_factory(win)
    factory.apply_layout(char_order)
    char_list = factory.char_list
    factory.update_domain(domain)
    factory.reset_ui_states()

    keyboard = ArrowKeyboard(win, pos=(0, factory.center_y))
    recorder = FrameRecorder(frame_log, global_clock, photodiode=get_shared_marker())

    # ── Domain onset (동물 없이 domain만 표시) ────────────────────────────────
    _show_domain_onset(
        win, factory, recorder, handle,
        trial_start_trigger=TRIG_P1_TRIAL_START,
        neon_client=neon_client,
        trial_index=trial_index,
        duration=DOMAIN_ONSET_DURATION,
    )
    recorder.start_segment("CHOICE1")

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    # for char_name in char_list:
    #     score = competence[_CHAR_CODE[char_name]][domain]
    #     factory.set_border_color(char_name, _get_comp_color(score))

    keyboard.reset_colors()
    choice1_idx, choice1_code, rt1 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        TRIG_P1_CHOICE1, confirm_wait=0.15,
        show_hover_border=False,
        onset_trigger=TRIG_P1_CHOICE_ONSET,
        neon_client=neon_client,
        neon_onset_events=section_start_events(trial_index, "CHOICE1"),
        neon_segment_label="CHOICE1",
        neon_trial_index=trial_index,
    )
    if choice1_code is None:
        send_trigger(handle, TRIG_P1_TRIAL_END)
        return None

    # core.wait(CHOICE_GAP)

    for char_name in char_list:
        # choice2 hover 시, show_border로 표시
        score = competence[_CHAR_CODE[char_name]][domain]
        factory.set_border_color(char_name, _get_comp_color(score))

        factory.hide_border(char_name)


    # ── Choice 2 ──────────────────────────────────────────────────────────────
    factory.set_animal_locked(char_list[choice1_idx], True)
    recorder.start_segment("CHOICE2")
    keyboard.reset_colors()
    keyboard.set_excluded(choice1_idx)
    factory.show_border(char_list[choice1_idx])

    _, choice2_code, rt2 = _run_choice_loop(
        win, factory, keyboard, recorder, char_list, handle,
        TRIG_P1_CHOICE2,
        excluded_idx=choice1_idx, locked_idx=choice1_idx,
        confirm_wait=1.0, lock_on_confirm=True,
        neon_client=neon_client,
        neon_onset_events=section_start_events(trial_index, "CHOICE2"),
        neon_segment_label="CHOICE2",
        neon_trial_index=trial_index,
    )
    if choice2_code is None:
        send_trigger(handle, TRIG_P1_TRIAL_END)
        return None

    send_trigger(handle, TRIG_P1_TRIAL_END)
    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
