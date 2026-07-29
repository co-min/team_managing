import gc

from psychopy import visual, core, event

from utils.event_utils import check_escape
from function.config.settings import (
    HOVER_ITI_MIN_DISPLAY,
    HOVER_ITI_DWELL_TIME,
    HOVER_BUTTON_RADIUS,
    HOVER_BUTTON_LABEL,
    HOVER_PROMPT_TEXT,
    WHITE_COLOR,   
    GREEN_COLOR,
    FONT,
)
from function.io.frame_logger import set_onset, log_frame
import random

def run_gaussian_iti(win, global_clock, frame_log, min_t=0.6, max_t=1.8, mean_t=1.2, sd_t=0.3):
    """지정된 가우시안 분포의 랜덤한 시간 동안 빈 화면(ITI)을 띄우고 로그를 남깁니다."""
    # ITI 시간 계산 (가우시안 분포 및 min/max 클램핑)
    iti_duration = random.gauss(mean_t, sd_t)
    iti_duration = max(min_t, min(iti_duration, max_t))

    phase_clock = core.Clock()
    frame_idx = 0

    while phase_clock.getTime() < iti_duration:
        flip_time = win.flip()

        if frame_idx == 0:
            frame_log = set_onset(frame_log, flip_time)
            marker = f"iti_onset_dur_{iti_duration:.3f}"
        else:
            marker = ""

        frame_log = log_frame(frame_log, frame_idx, flip_time, global_clock.getTime(), marker)
        frame_idx += 1
        check_escape(win)

    return frame_log

def run_hover_iti(win) -> None:
    """Show a center button; proceed when the mouse dwells over it."""
    gc.collect()
    mouse = event.Mouse(win=win)
    clock = core.Clock()
    stims = _build_stims(win)
    hover_start = None

    while True:
        check_escape(win)
        t = clock.getTime()
        hovered = t >= HOVER_ITI_MIN_DISPLAY and stims["button"].contains(mouse)

        if hovered:
            if hover_start is None:
                hover_start = t
            if t - hover_start >= HOVER_ITI_DWELL_TIME:
                # stims["button"].fillColor = GREEN_COLOR
                _draw(stims)
                win.flip()
                break
            stims["button"].lineColor = GREEN_COLOR
            stims["label"].color = GREEN_COLOR
        else:
            hover_start = None
            stims["button"].lineColor = WHITE_COLOR
            stims["label"].color = WHITE_COLOR

        _draw(stims)
        win.flip()


# ─── helpers ─────────────────────────────────────────────────────────────────

def _build_stims(win) -> dict:
    button = visual.Circle(
        win,
        radius=HOVER_BUTTON_RADIUS,
        pos=(0, 0),
        lineColor=WHITE_COLOR,
        fillColor=None,
        lineWidth=2,
    )
    label = visual.TextStim(
        win,
        text=HOVER_BUTTON_LABEL,
        font=FONT,
        pos=(0, 0),
        color=WHITE_COLOR,
        height=28,
    )
    prompt = visual.TextStim(
        win,
        text=HOVER_PROMPT_TEXT,
        font=FONT,
        pos=(0, HOVER_BUTTON_RADIUS + 60),
        color=WHITE_COLOR,
        height=22,
    )
    return {"button": button, "label": label, "prompt": prompt}


def _draw(stims) -> None:
    stims["button"].draw()
    stims["label"].draw()
    stims["prompt"].draw()
