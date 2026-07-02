# function/phases/feedback.py
"""
Feedback gauge — displays the target score (-3 … +3) instantly 
and holds for FB_TIME seconds.

Gauge layout (viewed head-on):
  -3 at lower-left  (~225° standard math)
   0 at top         ( 90° standard math)
  +3 at lower-right (~-45° / 315° standard math)

PsychoPy needle orientation (clockwise from "up"):
  ori = (score / 3) * 135
"""

import math

from psychopy import visual, core

from function.config.settings import FB_TIME
from utils.event_utils import check_escape


_GAUGE_RADIUS = 160
_NEEDLE_LEN   = 140
_GAUGE_COLOR  = 'white'
_NEEDLE_COLOR = '#FF4444'


def _score_to_ori(score: float) -> float:
    """Map score (-3..+3) to PsychoPy clockwise-from-up degrees."""
    return (score / 3.0) * 135.0


def _build_gauge(win: visual.Window) -> list:
    """Build all static gauge stims: arc, tick marks, numeric labels, pivot."""
    stims = []

    # Outer circle (full ring — only the upper arc is visible in practice)
    stims.append(visual.Circle(
        win, radius=_GAUGE_RADIUS,
        lineColor=_GAUGE_COLOR, fillColor=None, lineWidth=2, edges=72,
    ))

    for val in range(-3, 4):
        ori = _score_to_ori(val)
        # Convert PsychoPy ori back to standard math angle for (x, y) coordinates
        math_rad = math.radians(90.0 - ori)
        x = _GAUGE_RADIUS * math.cos(math_rad)
        y = _GAUGE_RADIUS * math.sin(math_rad)

        stims.append(visual.Line(
            win,
            start=(x * 0.82, y * 0.82),
            end=(x, y),
            lineColor=_GAUGE_COLOR, lineWidth=2,
        ))
        stims.append(visual.TextStim(
            win, text=str(val),
            pos=(x * 1.28, y * 1.28),
            color=_GAUGE_COLOR, height=22,
        ))

    # Centre pivot dot
    stims.append(visual.Circle(
        win, radius=7, pos=(0, 0),
        fillColor=_GAUGE_COLOR, lineColor=None,
    ))

    return stims


def run_feedback(
    win: visual.Window,
    global_clock: core.Clock,
    score: float,
) -> None:
    """
    Display the gauge with the needle pointing directly at *score* for FB_TIME seconds (no animation).
    """
    gauge_stims = _build_gauge(win)
    target_ori  = _score_to_ori(score)

    needle = visual.Line(
        win,
        start=(0, 0),
        end=(0, _NEEDLE_LEN),
        lineColor=_NEEDLE_COLOR,
        lineWidth=5,
    )
    
    # 처음부터 바늘의 각도를 목표 점수에 맞게 고정합니다.
    needle.ori = target_ori

    clock = core.Clock()
    
    # 설정된 시간(FB_TIME) 동안 화면을 유지하며 ESC 입력을 감지합니다.
    while clock.getTime() < FB_TIME:
        for stim in gauge_stims:
            stim.draw()
        needle.draw()
        win.flip()
        check_escape(win)