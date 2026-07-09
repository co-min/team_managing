# function/phases/feedback.py
"""
Feedback phase — domain-specific score display with monkey narrator.

  repairing : cleanliness level text  (stage 1=dirty → 7=clean)
  cooking   : taste-label text

Score normalisation: domain min/max from stimuli/score_table.csv → stage 1–7
"""

import csv
from psychopy import visual, core
from function.config.settings import FB_TIME, FONT, SCORE_CSV, DOMAINS, MISSION_MODE
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

def _load_score_ranges(csv_path=None, domains=None) -> dict:
    if csv_path is None:
        csv_path = SCORE_CSV
    if domains is None:
        domains = DOMAINS
    col_map = {d: f'sc_{d}' for d in domains}
    ranges  = {d: [float('inf'), float('-inf')] for d in domains}
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
        return {d: (3.0, 10.0) for d in domains}
    return {d: (v[0], v[1]) for d, v in ranges.items()}


_SCORE_RANGES = _load_score_ranges()

if MISSION_MODE == 3:
    from function.config.settings import P2_SCORE_CSV, P2_DOMAINS
    P2_SCORE_RANGES = _load_score_ranges(P2_SCORE_CSV, P2_DOMAINS)
else:
    P2_SCORE_RANGES = _SCORE_RANGES


def score_to_stage(score: float, domain: str, score_ranges: dict = None) -> int:
    """Normalise raw score to stage 1–7 using domain min/max from score_table."""
    ranges = score_ranges if score_ranges is not None else _SCORE_RANGES
    lo, hi = ranges.get(domain, (3.0, 9.0))
    if hi == lo:
        return 4
    return max(1, min(7, int(1 + (score - lo) / (hi - lo) * 6 + 0.5)))


# ── Domain builders ───────────────────────────────────────────────────────────


def _build_text_stims(win: visual.Window, stage: int, domain_cfg: dict) -> list:
    """Generic builder for domains described by a list of stim specs."""
    stage_idx   = stage - 1
    stage_color = domain_cfg['colors'][stage_idx]
    return [
        visual.TextStim(win, text=domain_cfg[s['key']][stage_idx], pos=s['pos'],
                        color=stage_color, height=s['height'], bold=True, font=FONT)
        for s in domain_cfg['stims']
    ]


def _monkey_text(score: float, stage: int, domain_cfg: dict, domain: str = '',
                 score_ranges: dict = None) -> str:
    comment = domain_cfg['monkey'][stage - 1]
    ranges = score_ranges if score_ranges is not None else _SCORE_RANGES
    _, hi = ranges.get(domain, (0.0, 10.0))
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


def _build_monkey_stims(win: visual.Window, stage: int, domain_cfg: dict,
                        score: float = 0.0, domain: str = '',
                        score_ranges: dict = None) -> list:
    bubble_text  = _monkey_text(score, stage, domain_cfg, domain, score_ranges)
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
    n_domains = len(domains)
    x_spacing = 155 if n_domains <= 2 else 210
    return {d: int(-x_spacing * (n_domains - 1) / 2 + i * x_spacing) for i, d in enumerate(domains)}

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
    block_domains: list = None,
    handle=None,
    trig_code: int = 0,
    score_ranges: dict = None,
) -> None:
    """Display domain-specific feedback with monkey narrator for FB_TIME seconds."""
    active_ranges  = score_ranges if score_ranges is not None else _SCORE_RANGES
    stage          = score_to_stage(score, domain, active_ranges)
    domain_cfg     = _DOMAIN.get(domain, _DOMAIN['cooking'])

    active_domains = block_domains if block_domains is not None else DOMAINS
    domain_xs      = _make_domain_xs(active_domains)
    domain_ko      = {d: _DOMAIN_KO_ALL[d] for d in active_domains}
    max_score_per_trial = max(hi for _, hi in active_ranges.values())
    max_phase = n_trials_per_domain * len(domain_xs) * max_score_per_trial

    domain_score_stims = []
    if domain_scores:
        for d, x in domain_xs.items():
            val   = float(domain_scores.get(d, 0))
            color = "#FF9800" if d == domain else "#AAAAAA"
            domain_score_stims.append(visual.TextStim(
                win, text=f"{domain_ko[d]}: {val}점",
                pos=(x, -185), color=color, height=27, font=FONT, bold=(d == domain),
            ))

    stims = (
        domain_cfg['build'](win, stage, domain_cfg)
        + _build_monkey_stims(win, stage, domain_cfg, score=score, domain=domain,
                              score_ranges=active_ranges)
        + domain_score_stims
        + [
            visual.TextStim(win, text=f"단계 점수: {int(phase_score)}/{int(max_phase)}점",
                            pos=(0, -235), color="#AAAAAA", height=29, font=FONT, bold=False),
            visual.TextStim(win, text=f"총 점수: {float(cumulative_score)}점",
                            pos=(0, -282), color="#FFD700", height=34, font=FONT, bold=True),
        ]
    )

    clock           = core.Clock()
    trigger_sent    = False
    while clock.getTime() < FB_TIME:
        for stim in stims:
            stim.draw()
        if not trigger_sent:
            win.callOnFlip(send_trigger_async, handle, trig_code)
            win.callOnFlip(reset_trigger, handle)
            trigger_sent = True
        win.flip()
        check_escape(win)
