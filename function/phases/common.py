"""Shared trial utilities used across Phase 1 and Phase 2."""

from psychopy import event, core

from utils.event_dispatch import callonflip_trial_start


def show_domain_onset(
    win, factory, recorder, handle,
    phase: int,
    neon_client, trial_index,
    duration,
):
    """Domain 이미지만 표시하는 onset 구간.

    첫 flip에서 LabJack TRIAL_START + Neon DOMAIN_ONSET 섹션을 동시에 등록.
    duration 경과 후 이벤트 버퍼를 비우고 반환.
    """
    clock = core.Clock()
    _pending = True

    recorder.start_segment("DOMAIN_ONSET")

    while clock.getTime() < duration:
        factory.draw_domain_only()
        if _pending:
            callonflip_trial_start(win, neon_client, handle, phase, trial_index)
            _pending = False
        recorder.flip_and_log(win)

    event.clearEvents()
