# function/phases/feedback.py
"""
Feedback phase — domain-specific score display with monkey narrator.

  repairing : cleanliness level text  (stage 1=dirty → 7=clean)
  tennis    : scoreboard text         (3:0 loss → 0:3 win)
  cooking   : taste-label text

Score normalisation: domain min/max from stimuli/score_table.csv → stage 1–7
"""

import csv
from psychopy import visual, core
from function.config.settings import FB_TIME, FONT
from utils.event_utils import check_escape
from utils.labjack_trigger import send_trigger_async, reset_trigger

# ── Layout constants ──────────────────────────────────────────────────────────

_MONKEY_PATH     = "image/monkey.png"
_MONKEY_SIZE     = (160, 160)
_MONKEY_POS      = (-130,   0)
_BUBBLE_POS      = ( 130,   0)
_BUBBLE_TAIL_POS = (   2,   0)
_DOMAIN_Y        = 160

# Shared 7-step color ramp (red → green)
_RESULT_COLORS = ["#F44336", "#FF5722", "#FF9800", "#FFEB3B", "#CDDC39", "#8BC34A", "#4CAF50"]


# ── Score ranges from score_table.csv ────────────────────────────────────────

def _load_score_ranges(csv_path: str = "stimuli/score_table.csv") -> dict:
    ranges  = {d: [float('inf'), float('-inf')] for d in ('cooking', 'repairing', 'tennis')}
    col_map = {'cooking': 'sc_cooking', 'repairing': 'sc_repairing', 'tennis': 'sc_tennis'}
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f, skipinitialspace=True):
                for domain, col in col_map.items():
                    val = float(row[col])
                    if val < ranges[domain][0]:
                        ranges[domain][0] = val
                    if val > ranges[domain][1]:
                        ranges[domain][1] = val
    except Exception:
        return {'cooking': (3.0, 10.0), 'repairing': (4.0, 10.0), 'tennis': (2.0, 8.0)}
    return {d: (v[0], v[1]) for d, v in ranges.items()}


_SCORE_RANGES = _load_score_ranges()


def score_to_stage(score: float, domain: str) -> int:
    """Normalise raw score to stage 1–7 using domain min/max from score_table."""
    lo, hi = _SCORE_RANGES.get(domain, (3.0, 9.0))
    if hi == lo:
        return 4
    return max(1, min(7, int(1 + (score - lo) / (hi - lo) * 6 + 0.5)))


# ── Domain builders ───────────────────────────────────────────────────────────


def _build_text_stims(win: visual.Window, stage: int, cfg: dict) -> list:
    """Generic builder for domains described by a list of stim specs."""
    idx, color = stage - 1, cfg['colors'][stage - 1]
    return [
        visual.TextStim(win, text=cfg[s['key']][idx], pos=s['pos'],
                        color=color, height=s['height'], bold=True, font=FONT)
        for s in cfg['stims']
    ]


def _monkey_text(domain: str, score: float, stage: int, cfg: dict) -> str:
    """Compose bubble text: actual score for cooking/repairing, game score for tennis."""
    comment = cfg['monkey'][stage - 1]
    if domain == 'tennis':
        return comment
    _, max_score = _SCORE_RANGES.get(domain, (0.0, 10.0))
    return f"{int(max_score)}점 만점에 {score:g}점이야.\n{comment}"


def _build_monkey_stims(win: visual.Window, stage: int, cfg: dict,
                        domain: str = '', score: float = 0.0) -> list:
    bubble_text  = _monkey_text(domain, score, stage, cfg)
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


# ── Domain configuration ──────────────────────────────────────────────────────

_DOMAIN: dict[str, dict] = {
    'repairing': {
        'build':  _build_text_stims,
        'monkey': [
            "아직 많이 지저분해...",
            "꽤 지저분해",
            "조금 지저분해",
            "청소 상태가 보통이야",
            "조금 깨끗해!",
            "꽤 깨끗해!",
            "완벽하게 깨끗해!",
        ],
        'colors': _RESULT_COLORS,
        'stims':  [],
    },
    'tennis': {
        'build':  _build_text_stims,
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
        'build':  _build_text_stims,
        'monkey': [
            "이 요리는 맛없어...",
            "이 요리는 별로야",
            "조금 아쉬워",
            "이 요리는 보통이야",
            "맛있어!",
            "정말 맛있어!",
            "최고야!",
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
    phase_score: float = 0,
    handle=None,
    trig_code: int = 0,
) -> None:
    """Display domain-specific feedback with monkey narrator for FB_TIME seconds."""
    stage = score_to_stage(score, domain)
    cfg   = _DOMAIN.get(domain, _DOMAIN['cooking'])

    stims = (
        cfg['build'](win, stage, cfg)
        + _build_monkey_stims(win, stage, cfg, domain=domain, score=score)
        + [
            visual.TextStim(win, text=f"단계 누적 점수: {int(phase_score)}점",
                            pos=(0, -145), color="#FFF4F4", height=28, font=FONT, bold=True),
            visual.TextStim(win, text=f"총 누적 점수: {int(cumulative_score)}점",
                            pos=(0, -185), color="#FFD700", height=26, font=FONT, bold=True),
        ]
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
