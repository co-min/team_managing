# function/phases/feedback.py
"""
Feedback phase — domain-specific score display with monkey narrator.

  repairing : cleanliness level text  (stage 1=dirty → 7=clean)
  cooking   : taste-label text

Score normalisation: domain min/max from stimuli/score_table.csv → stage 1–7
"""

import csv
from psychopy import visual, core
from function.config.settings import FB_TIME, FONT, SCORE_CSV, DOMAINS
from utils.event_utils import check_escape
from utils.labjack_trigger import send_trigger_async, reset_trigger

# ── Layout constants ──────────────────────────────────────────────────────────

_MONKEY_PATH     = "image/monkey.png"
_MONKEY_SIZE     = (210, 210)
_MONKEY_POS      = (-170,   0)
_BUBBLE_POS      = ( 170,   0)
_BUBBLE_TAIL_POS = (   2,   0)
_DOMAIN_Y        = 210

_monkey_stim_cache: dict = {}

# Shared 7-step color ramp (red → green)
_RESULT_COLORS = ["#F44336", "#FF5722", "#FF9800", "#FFEB3B", "#CDDC39", "#8BC34A", "#4CAF50"]


# ── Score ranges from the active MODE's score CSV ─────────────────────────────

def _load_score_ranges() -> dict:
    col_map = {d: f'sc_{d}' for d in DOMAINS}
    ranges  = {d: [float('inf'), float('-inf')] for d in DOMAINS}
    try:
        with open(SCORE_CSV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f, skipinitialspace=True):
                for domain, col in col_map.items():
                    val = float(row[col])
                    if val < ranges[domain][0]:
                        ranges[domain][0] = val
                    if val > ranges[domain][1]:
                        ranges[domain][1] = val
    except Exception:
        return {d: (3.0, 10.0) for d in DOMAINS}
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


def _monkey_text(score: float, stage: int, cfg: dict, domain: str = '') -> str:
    comment = cfg['monkey'][stage - 1]
    _, hi = _SCORE_RANGES.get(domain, (0.0, 10.0))
    max_score = int(hi) if hi == int(hi) else hi
    return f"{max_score}점 만점에 {score:g}점이야.\n{comment}"


def _get_monkey_stim(win: visual.Window) -> 'visual.ImageStim | None':
    wid = id(win)
    if wid not in _monkey_stim_cache:
        try:
            _monkey_stim_cache[wid] = visual.ImageStim(
                win, image=_MONKEY_PATH, size=_MONKEY_SIZE, pos=_MONKEY_POS
            )
        except Exception:
            _monkey_stim_cache[wid] = None
    return _monkey_stim_cache[wid]


def _build_monkey_stims(win: visual.Window, stage: int, cfg: dict,
                        score: float = 0.0, domain: str = '') -> list:
    bubble_text  = _monkey_text(score, stage, cfg, domain)
    bubble_color = _RESULT_COLORS[stage - 1]
    stims = []
    monkey = _get_monkey_stim(win)
    if monkey is not None:
        stims.append(monkey)
    stims += [
        visual.Rect(win, width=340, height=195, pos=_BUBBLE_POS,
                    fillColor=bubble_color, lineColor=bubble_color),
        visual.ShapeStim(win, vertices=[(-33, 0), (13, 18), (13, -18)],
                         pos=_BUBBLE_TAIL_POS, fillColor=bubble_color, lineColor=bubble_color),
        visual.TextStim(win, text=bubble_text,
                        pos=_BUBBLE_POS, color='#222222', height=31, bold=True,
                        font=FONT, wrapWidth=315),
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
    'tennis': {
        'build':  _build_text_stims,
        'monkey': [
            "경기를 많이 졌어...",
            "꽤 아쉬운 경기야",
            "조금 아쉬워",
            "보통 경기야",
            "잘 했어!",
            "정말 잘 했어!",
            "완벽한 경기야!",
        ],
        'colors': _RESULT_COLORS,
        'stims':  [],
    },
}


# ── Public entry point ────────────────────────────────────────────────────────

_DOMAIN_KO_ALL = {'cooking': '요리', 'repairing': '수리', 'tennis': '테니스'}
_DOMAIN_KO = {d: _DOMAIN_KO_ALL[d] for d in DOMAINS}

def _make_domain_xs(domains: list) -> dict:
    n    = len(domains)
    step = 155 if n <= 2 else 210
    return {d: int(-step * (n - 1) / 2 + i * step) for i, d in enumerate(domains)}

_DOMAIN_XS = _make_domain_xs(DOMAINS)

# Per-domain score ceiling (used for max phase score calculation)
_MAX_SCORE_PER_TRIAL = max(hi for _, hi in _SCORE_RANGES.values())


def run_feedback(
    win: visual.Window,
    score: float,
    domain: str,
    cumulative_score: float = 0,
    phase_score: float = 0,
    domain_scores: dict = None,
    n_trials_per_domain: int = 18,
    handle=None,
    trig_code: int = 0,
) -> None:
    """Display domain-specific feedback with monkey narrator for FB_TIME seconds."""
    stage = score_to_stage(score, domain)
    cfg   = _DOMAIN.get(domain, _DOMAIN['cooking'])

    max_phase = n_trials_per_domain * len(_DOMAIN_XS) * _MAX_SCORE_PER_TRIAL

    domain_score_stims = []
    if domain_scores:
        for d, x in _DOMAIN_XS.items():
            val   = int(domain_scores.get(d, 0))
            color = "#FF9800" if d == domain else "#AAAAAA"
            domain_score_stims.append(visual.TextStim(
                win, text=f"{_DOMAIN_KO[d]}: {val}점",
                pos=(x, -185), color=color, height=27, font=FONT, bold=(d == domain),
            ))

    stims = (
        cfg['build'](win, stage, cfg)
        + _build_monkey_stims(win, stage, cfg, score=score, domain=domain)
        + domain_score_stims
        + [
            visual.TextStim(win, text=f"단계 점수: {int(phase_score)}/{int(max_phase)}점",
                            pos=(0, -235), color="#AAAAAA", height=29, font=FONT, bold=False),
            visual.TextStim(win, text=f"총 점수: {int(cumulative_score)}점",
                            pos=(0, -282), color="#FFD700", height=34, font=FONT, bold=True),
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
