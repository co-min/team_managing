# function/config/strings.py
"""
Centralized participant-facing text (Korean / English).

Language is picked from settings.MODE_ENG at call time (imported lazily to
avoid a circular import with settings.py, which builds some of its own
constants from this module).
"""


def _lang() -> str:
    from function.config import settings
    return "en" if settings.MODE_ENG else "ko"


# ── generic key -> {lang: template} ───────────────────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {
    "hover_prompt": {
        "ko": "중앙을 응시해주세요.",
        "en": "Please look at the center.",
    },

    "inst_phase1": {
        "ko": "[{block_num} / {total_blocks}]\n\n"
              "이번 단계에서, 각자 수행하는 능력이 보여요.\n"
              "숨겨진 팀워크를 생각하면서 만점인 동물 두 마리를 찾아볼까요?\n\n"
              "[Space] 키를 눌러 시작",
        "en": "[{block_num} / {total_blocks}]\n\n"
              "In this phase, you can see each animal's individual performance.\n"
              "Think about their hidden teamwork and find the two animals with a perfect score.\n\n"
              "Press [Space] to start",
    },
    "inst_phase2": {
        "ko": "[{block_num} / {total_blocks} 블록]\n\n"
              "이번 단계에서, 협력하는 팀워크가 보여요.\n"
              "숨겨진 수행하는 능력을 예상하면서 만점인 동물 두 마리를 찾아볼까요?\n\n"
              "[Space] 키를 눌러 시작",
        "en": "[Block {block_num} / {total_blocks}]\n\n"
              "In this phase, you can see how well the animals cooperate.\n"
              "Guess their hidden individual performance and find the two animals with a perfect score.\n\n"
              "Press [Space] to start",
    },
    "inst_break": {
        "ko": "잠시 휴식 시간입니다.\n\n준비가 되면 실험자가 실험을 재개합니다.",
        "en": "Take a short break.\n\nThe experimenter will resume the task when you are ready.",
    },

    "inst_practice_phase1": {
        "ko": "연습 1단계: 보이는 능력치\n\n"
              "숨겨진 팀워크를 생각해보세요. 이 중 만점인 두 동물은 누굴까요?\n\n"
              "[Space] 키를 눌러 시작",
        "en": "Practice Phase 1: Visible Performance\n\n"
              "Think about their hidden teamwork. Which two animals have a perfect score?\n\n"
              "Press [Space] to start",
    },
    "inst_practice_phase2": {
        "ko": "연습 2단계: 보이는 팀워크\n\n"
              "숨겨진 개인 능력을 생각해보세요. 이 중 만점인 두 동물은 누굴까요?\n\n"
              "[Space] 키를 눌러 시작",
        "en": "Practice Phase 2: Visible Teamwork\n\n"
              "Think about their hidden individual performance. Which two animals have a perfect score?\n\n"
              "Press [Space] to start",
    },
    "inst_practice_end": {
        "ko": "연습이 끝났습니다.\n잠시 후 본 실험이 시작됩니다.",
        "en": "Practice is complete.\nThe main task will begin shortly.",
    },

    # ── ending screen ────────────────────────────────────────────────────────
    "ending_title":              {"ko": "게임이 끝났습니다!", "en": "The game is over!"},
    "ending_subtitle":           {"ko": "수고하셨습니다.", "en": "Well done!"},
    "ending_leaderboard_header": {"ko": "순위표  (정답률 기준)", "en": "Leaderboard  (by accuracy)"},
    "ending_me_tag":             {"ko": "  ← 나", "en": "  ← Me"},
    "ending_rank_label":         {"ko": "{rank}위", "en": "#{rank}"},
    "ending_stats": {
        "ko": "정답률  {accuracy}   ·   총 점수  {score}점   ·   소요시간  {elapsed}",
        "en": "Accuracy  {accuracy}   ·   Total Score  {score}   ·   Elapsed  {elapsed}",
    },
    "ending_rank_summary": {"ko": "전체 {total}명 중  {rank}위", "en": "Rank {rank} of {total}"},
    "ending_exit_prompt":  {"ko": "[ Space ] 키를 눌러 종료", "en": "Press [ Space ] to exit"},
    "ending_elapsed_fmt":  {"ko": "{m}분 {s:02d}초", "en": "{m}m {s:02d}s"},

    # ── feedback screen ──────────────────────────────────────────────────────
    "feedback_bubble": {
        "ko": "{max_score}점 만점에 {score}점이야.\n{comment}",
        "en": "{score} out of {max_score} points.\n{comment}",
    },
    "feedback_domain_score": {"ko": "{domain}: {score}점", "en": "{domain}: {score} pts"},
    "feedback_phase_score":  {"ko": "단계 점수: {cur}/{max}점", "en": "Phase score: {cur}/{max}"},
    "feedback_total_score":  {"ko": "총 점수: {score}점", "en": "Total score: {score}"},
}


def t(key: str, **kwargs) -> str:
    """Look up a localized string by key, formatting with kwargs if given."""
    template = _STRINGS[key][_lang()]
    return template.format(**kwargs) if kwargs else template


# ── domain display names ──────────────────────────────────────────────────────

_DOMAIN_NAMES = {
    "cooking":   {"ko": "요리", "en": "Cooking"},
    "repairing": {"ko": "수리", "en": "Repairing"},
    "tennis":    {"ko": "테니스", "en": "Tennis"},
}


def domain_name(domain: str) -> str:
    return _DOMAIN_NAMES.get(domain, {}).get(_lang(), domain)


# ── monkey narrator comments (feedback.py) ────────────────────────────────────

_MONKEY_COMMENTS = {
    "repairing": {
        "ko": ["아직 많이 지저분해...", "꽤 지저분해", "조금 지저분해",
               "청소 상태가 보통이야", "꽤 깨끗해!", "완벽하게 깨끗해!"],
        "en": ["Still very messy...", "Pretty messy", "A little messy",
               "It's an average clean", "Pretty clean!", "Perfectly clean!"],
    },
    "cooking": {
        "ko": ["이 요리는 맛없어...", "이 요리는 별로야", "조금 아쉬워",
               "이 요리는 보통이야", "정말 맛있어!", "완벽하게 최고야!"],
        "en": ["This dish tastes bad...", "This dish isn't great", "A bit disappointing",
               "This dish is average", "Really tasty!", "Absolutely perfect!"],
    },
    "tennis": {
        "ko": ["경기를 많이 졌어...", "꽤 아쉬운 경기야", "조금 아쉬워",
               "보통 경기야", "정말 잘 했어!", "완벽한 경기야!"],
        "en": ["Lost a lot of matches...", "A pretty disappointing match", "A bit disappointing",
               "An average match", "Really well played!", "A perfect match!"],
    },
}


def monkey_comment(domain: str, stage: int) -> str:
    """stage is 1-indexed (1..6)."""
    comments = _MONKEY_COMMENTS.get(domain, _MONKEY_COMMENTS["cooking"])[_lang()]
    return comments[stage - 1]
