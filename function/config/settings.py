import platform
from pathlib import Path
import pandas as pd

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).resolve().parents[2]
DATA_DIR        = ROOT_DIR / "data"

# ─── Mode ─────────────────────────────────────────────────────────────────────
# MODE 1 : competence_table.csv       + score_table.csv        (3 domains)
# MODE 2 : competence_table_domain2.csv + score_table_domain2.csv (2 domains)
# MODE 3 : phase1 competency obs. 3 domains 18 trials / phase2 synergy obs. 2 domains 16 trials
MISSION_MODE = 3

# DOMAIN_ORDER: trial 내 domain 제시 순서
#   'random'     — seed 고정 랜덤 셔플
#   'sequential' — DOMAINS 순서대로 묶음
DOMAIN_ORDER = 'sequential'

if MISSION_MODE == 1:
    COMPETENCE_CSV    = ROOT_DIR / 'stimuli' / 'competence_table.csv'
    SCORE_CSV         = ROOT_DIR / 'stimuli' / 'score_table.csv'
    P2_COMPETENCE_CSV = COMPETENCE_CSV
    P2_SCORE_CSV      = SCORE_CSV
    DOMAINS           = ['cooking', 'repairing', 'tennis']
    P2_DOMAINS        = DOMAINS
    P1_TRIALS         = 18
    P2_TRIALS         = 18
    P3_TRIALS         = 6
    COMPETENCE_COLOR  = {1: '#F44336', 2: '#FFEB3B', 3: '#4CAF50'}          # 3-level
elif MISSION_MODE == 2:
    COMPETENCE_CSV    = ROOT_DIR / 'stimuli' / 'competence_table_domain2.csv'
    SCORE_CSV         = ROOT_DIR / 'stimuli' / 'score_table_domain2.csv'
    P2_COMPETENCE_CSV = COMPETENCE_CSV
    P2_SCORE_CSV      = SCORE_CSV
    DOMAINS           = ['cooking', 'repairing']
    P2_DOMAINS        = DOMAINS
    P1_TRIALS         = 16
    P2_TRIALS         = 16
    P3_TRIALS         = 6
    COMPETENCE_COLOR  = {1: '#F44336', 2: '#FF9800', 3: '#FFEB3B', 4: '#4CAF50'}  # 4-level
else:  # MISSION_MODE == 3
    COMPETENCE_CSV    = ROOT_DIR / 'stimuli' / 'competence_table.csv'
    SCORE_CSV         = ROOT_DIR / 'stimuli' / 'score_table.csv'
    P2_COMPETENCE_CSV = ROOT_DIR / 'stimuli' / 'competence_table_domain2.csv'
    P2_SCORE_CSV      = ROOT_DIR / 'stimuli' / 'score_table_domain2.csv'
    DOMAINS           = ['cooking', 'repairing', 'tennis']   # phase1 domains
    P2_DOMAINS        = ['cooking', 'repairing']              # phase2 domains
    P1_TRIALS         = 8
    P2_TRIALS         = 8
    P3_TRIALS         = 6
    COMPETENCE_COLOR  = {1: '#F44336', 2: '#FFEB3B', 3: '#4CAF50'}  
    # COMPETENCE_COLOR  = {1: '#F44336', 2: '#FF9800', 3: '#FFEB3B', 4: '#4CAF50'}  


# ─── Window ───────────────────────────────────────────────────────────────────
WINDOW_SIZE      = (1470, 956)   # TODO: adjust to your display
WINDOW_UNITS     = "pix"
WINDOW_FULLSCR   = False          # Set True for actual experiment
BACKGROUND_COLOR = "#2b2b2b"      # Dark gray matching PDF screenshots
MONITOR_NAME     = "testMonitor"  # TODO: calibrate your monitor
SCREEN_NUMBER = 1

# ─── Timing ──────────────────────────────────────────────────────────────────
MAX_RESPONSE_TIME =60.0          # seconds; None = unlimited
ITI_DURATION      = 1.5          # inter-trial interval (seconds)
FRAME_RATE        = 60           # Hz – used for frame log sanity checks

# ─── Text ────────────────────────────────────────────────────────────────────
FONT = "AppleGothic" if platform.system() == "Darwin" else "Malgun Gothic"
TEXT_COLOR       = "white"

# ─── Hover ITI ───────────────────────────────────────────────────────────────
HOVER_ITI_MIN_DISPLAY  = 0.3     # seconds before button becomes active
HOVER_ITI_DWELL_TIME   = 0.5     # seconds of continuous hover to proceed
HOVER_BUTTON_RADIUS    = 45      # pixels
HOVER_BUTTON_LABEL     = "+"
HOVER_PROMPT_TEXT      = "중앙을 응시해주세요."

# ─── Colours ─────────────────────────────────────────────────────────────────
WHITE_COLOR = "white"
GREEN_COLOR = "green"

# --- Event Keys ---
ARROW_OFFSET = 60
ARROW_RADIUS = 30


# --- Feed back ---
FB_TIME = 3.5


# Animal name -> char_ani code — derived from competence CSV for the active MODE
_comp_df  = pd.read_csv(COMPETENCE_CSV, skipinitialspace=True)
CHAR_CODE = dict(zip(_comp_df['animal'].str.strip(), _comp_df['char_ani'].str.strip()))

# Synergy score -> block fill colour
SYNERGY_COLOR = {1.4: 'green', 1.0: 'yellow', 0.8: 'red'}


# phase1 instruction  ({block_num}/{total_blocks} filled in at runtime)
INST_PHASE1 = """\
[{block_num} / {total_blocks}]

이번 단계에서는 능력치가 보입니다.
협력도를 고려해 동물 두 마리를 골라서 점수를 최대한 높여주세요.

[Space] 키를 눌러 시작"""

# phase2 instruction
INST_PHASE2 = """\
[{block_num} / {total_blocks} 블록]

이번 단계에서는 협력도가 보입니다.
능력치를 고려해 동물 두 마리를 골라서 점수를 최대한 높여주세요

[Space] 키를 눌러 시작"""



# ─── Practice ────────────────────────────────────────────────────────────────
PRACTICE_MODE    = True   # True: 본 실험 전 연습 세션 실행 / False: 건너뜀
PRACTICE_DOMAINS = ['cooking', 'repairing']

INST_PRACTICE_PHASE1 = (
    "연습 1단계: 능력치\n\n"
    "화살표 키(↑ → ←)로 원하는 동물을 선택하고\n"
    "[Space] 키로 확정하세요.\n\n"
    "[Space] 키를 눌러 시작"
)

INST_PRACTICE_PHASE2 = (
    "연습 2단계: 협력도\n\n"
    "첫 번째 동물을 고르면 협력도 색이 나타납니다.\n"
    "색을 참고해 두 번째 동물을 선택하세요.\n\n"
    "[Space] 키를 눌러 시작"
)

INST_PRACTICE_END = "연습이 끝났습니다.\n잠시 후 본 실험이 시작됩니다."
PRACTICE_END_DURATION = 3.0
