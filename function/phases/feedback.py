# function/phases/feedback.py
"""
Feedback phase — domain-specific score display with monkey narrator.

  repairing : 7-segment cleanliness bar  (stage 1=dirty → 7=clean)
  tennis    : scoreboard text            (3:0 loss → 0:3 win)
  cooking   : taste-label text

Score mapping:  -3 → stage 1,  0 → stage 4,  +3 → stage 7
"""

from psychopy import visual, core
from function.config.settings import FB_TIME, FONT
from utils.event_utils import check_escape
from utils.labjack_trigger import send_trigger_async, reset_trigger

# ── Layout constants ──────────────────────────────────────────────────────────

_MONKEY_PATH     = "image/monkey.png"
_MONKEY_SIZE     = (160, 160)
_MONKEY_POS      = (-180, -80)
_BUBBLE_POS      = (80,   -60)
_BUBBLE_TAIL_POS = (-48,  -60)
_DOMAIN_Y        = 120

# Shared 7-step color ramp (red → green)
_RESULT_COLORS = ["#F44336", "#FF5722", "#FF9800", "#FFEB3B", "#CDDC39", "#8BC34A", "#4CAF50"]


# ── Domain builders ───────────────────────────────────────────────────────────



def _build_text_stims(win: visual.Window, stage: int, cfg: dict) -> list:
    """Generic builder for domains described by a list of stim specs."""
    idx, color = stage - 1, cfg['colors'][stage - 1]
    return [
        visual.TextStim(win, text=cfg[s['key']][idx], pos=s['pos'],
                        color=color, height=s['height'], bold=True, font=FONT)
        for s in cfg['stims']
    ]


def _build_monkey_stims(win: visual.Window, stage: int, cfg: dict) -> list:
    bubble_text = cfg['monkey'][stage - 1]
    bubble_color = _RESULT_COLORS[stage - 1]
    stims = []
    try:
        stims.append(visual.ImageStim(win, image=_MONKEY_PATH, size=_MONKEY_SIZE, pos=_MONKEY_POS))
    except Exception:
        pass
    stims += [
        visual.Rect(win, width=260, height=150, pos=_BUBBLE_POS,
                    fillColor=bubble_color, lineColor=bubble_color),
        visual.ShapeStim(win, vertices=[(-25, 0), (10, 14), (10, -14)],
                         pos=_BUBBLE_TAIL_POS, fillColor=bubble_color, lineColor=bubble_color),
        visual.TextStim(win, text=bubble_text,
                        pos=_BUBBLE_POS, color='#222222', height=24, bold=True,
                        font=FONT, wrapWidth=240),
    ]
    return stims


# ── Domain configuration (data + builder reference) ──────────────────────────

_DOMAIN: dict[str, dict] = {
    'repairing': {
        'build': _build_text_stims,
        'monkey': [
            "7점 만점에 1점이야.\n아직 많이 지저분해...",
            "7점 만점에 2점이야.\n꽤 지저분해",
            "7점 만점에 3점이야.\n조금 지저분해",
            "7점 만점에 4점이야.\n청소 상태가 보통이야",
            "7점 만점에 5점으로\n조금 깨끗해!",
            "7점 만점에 6점으로\n꽤 깨끗해!",
            "7점 만점에 7점으로\n완벽하게 깨끗해!",
        ],
        'colors': _RESULT_COLORS,
        'stims':  [],
            },
    'tennis': {
        'build': _build_text_stims,
        'monkey': [
            "3 : 0이야.\n완패야...",
            "3 : 1이야.\n아슬아슬하게 졌어",
            "3 : 2야.\n패배야",
            "3 : 3이야.\n무승부야",
            "2 : 3이야.\n아슬아슬하게 이겼어!",
            "1 : 3이야.\n승리야!",
            "0 : 3이야.\n완벽한 승리야!",
        ],
        'scores': ["3 : 0", "3 : 1", "3 : 2", "3 : 3", "2 : 3", "1 : 3", "0 : 3"],
        'colors': _RESULT_COLORS,
        'stims':  [],
    },
    'cooking': {
        'build': _build_text_stims,
        'monkey': [
            "7점 만점에 1점이야.\n이 요리는 맛없어...",
            "7점 만점에 2점이야.\n이 요리는 별로야",
            "7점 만점에 3점이야.\n조금 아쉬워",
            "7점 만점에 4점이야.\n이 요리는 보통이야",
            "7점 만점에 5점으로\n맛있어!",
            "7점 만점에 6점으로\n정말 맛있어!",
            "7점 만점에 7점으로\n최고야!",
        ],
        'colors': _RESULT_COLORS,
        'stims':  [],
    },
}


# ── Public entry point ────────────────────────────────────────────────────────

def run_feedback(
    win: visual.Window,
    score: float,
    domain: str,
    cumulative_score: float = 0,
    handle=None,
    trig_code: int = 0,
) -> None:
    """Display domain-specific feedback with monkey narrator for FB_TIME seconds."""
    stage = int(round(score)) + 4
    cfg   = _DOMAIN.get(domain, _DOMAIN['cooking'])

    stims = (
        cfg['build'](win, stage, cfg)
        + _build_monkey_stims(win, stage, cfg)
        + [visual.TextStim(win, text=f"누적 점수: {int(cumulative_score)}점",
                           pos=(0, -230), color="#FFF4F4", height=22, font=FONT)]
    )

    clock     = core.Clock()
    trig_sent = False
    while clock.getTime() < FB_TIME:
        for stim in stims:
            stim.draw()
        if not trig_sent:
            win.callOnFlip(send_trigger_async, handle, trig_code)
            win.callOnFlip(reset_trigger, handle)
            trig_sent = True
        win.flip()
        check_escape(win)
