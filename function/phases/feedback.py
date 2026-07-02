# function/phases/feedback.py
"""
Feedback gauge — displays the target score (-3 … +3) instantly 
and holds for FB_TIME seconds with text intuition.

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
from utils.labjack_trigger import send_trigger_async, reset_trigger

_GAUGE_RADIUS = 160
_NEEDLE_LEN   = 140
_GAUGE_COLOR  = 'white'
_NEEDLE_COLOR = '#FF4444'


def _score_to_ori(score: float) -> float:
    """Map score (-3..+3) to PsychoPy clockwise-from-up degrees."""
    return (score / 3.0) * 135.0


def _get_feedback_details(score: float) -> tuple[str, str]:
    """점수 구간에 따른 직관적인 멘트와 색상을 반환합니다."""
    if score >= 3.0:
        return "최고예요!", "#4CAF50"       # 진한 초록
    elif score >= 1:
        return "잘했어요!", "#8BC34A"       # 연두색
    elif score >= -0.5:
        return "나쁘지 않아요!", "#FFEB3B"   # 노란색
    elif score >= -2.0:
        return "아쉬워요..", "#FF9800"      # 주황색
    else:
        return "조금 더 힘내세요!", "#F44336"  # 빨간색


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
    handle=None,
    trig_code: int = 0,
) -> None:
    """
    Display the gauge with the needle pointing directly at *score* along with intuitive text feedback for FB_TIME seconds.
    """
    gauge_stims = _build_gauge(win)
    target_ori  = _score_to_ori(score)

    # 점수에 따른 멘트와 색상 가져오기
    feedback_text, text_color = _get_feedback_details(score)

    # 바늘 설정
    needle = visual.Line(
        win,
        start=(0, 0),
        end=(0, _NEEDLE_LEN),
        lineColor=_NEEDLE_COLOR,
        lineWidth=5,
    )
    needle.ori = target_ori

    # 피드백 텍스트 자극(TextStim) 설정
    # 위치를 (0, 260)으로 변경하여 게이지와 '0' 눈금보다 위쪽에 배치합니다.
    text_stim = visual.TextStim(
        win,
        text=feedback_text,
        pos=(0, 260),     # <--- 이 부분이 수정되었습니다 (위쪽 배치)
        color=text_color,
        height=28,       
        bold=True,
        wrapWidth=400    
    )

    clock = core.Clock()
    _trig_sent = False

    while clock.getTime() < FB_TIME:
        for stim in gauge_stims:
            stim.draw()
        needle.draw()
        text_stim.draw()
        if not _trig_sent:
            win.callOnFlip(send_trigger_async, handle, trig_code)
            win.callOnFlip(reset_trigger, handle)
            _trig_sent = True
        win.flip()
        check_escape(win)