"""Shared trial utilities used across Phase 1 and Phase 2."""

from psychopy import event, core

from utils.labjack_trigger import send_trigger
from utils.neon_client import section_start_events


def show_domain_onset(
    win, factory, recorder, handle,
    trial_start_trigger,
    neon_client, trial_index,
    duration,
):
    """Domain 이미지만 표시하는 onset 구간.

    첫 flip에서:
      - trial_start_trigger 전송 (callOnFlip → 프레임 정확)
      - Neon DOMAIN_ONSET 섹션 오픈 (callOnFlip → 프레임 정확)
    duration 경과 후 이벤트 버퍼를 비우고 반환.
    """
    clock = core.Clock()
    _pending_trig = trial_start_trigger
    _pending_neon = (neon_client is not None)

    recorder.start_segment("DOMAIN_ONSET")   # labels all frames in this window

    while clock.getTime() < duration:
        factory.draw_domain_only()
        if _pending_trig is not None:
            win.callOnFlip(send_trigger, handle, _pending_trig)
            _pending_trig = None
        if _pending_neon:
            neon_client.call_on_flip(
                win,
                section_start_events(trial_index, "DOMAIN_ONSET", first=True),
                task_type="trial", phase="DOMAIN_ONSET", trial_index=trial_index,
            )
            _pending_neon = False
        recorder.flip_and_log(win)   # auto-generates "DOMAIN_ONSET_onset" on first frame

    event.clearEvents()
