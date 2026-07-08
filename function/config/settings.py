import platform
from pathlib import Path
import pandas as pd

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).resolve().parents[2]
DATA_DIR        = ROOT_DIR / "data"


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


# --- Trial ---
P1_TRIALS = 8
P2_TRIALS = 8
P3_TRIALS = 6

# --- Feed back ---
FB_TIME = 3.5


# Animal name -> char_ani code — derived from competence_table.csv (no hardcoding)
_comp_df  = pd.read_csv(ROOT_DIR / 'stimuli' / 'competence_table.csv', skipinitialspace=True)
CHAR_CODE = dict(zip(_comp_df['animal'].str.strip(), _comp_df['char_ani'].str.strip()))

# Synergy score -> block fill colour
SYNERGY_COLOR = {2: 'green', 1.5: 'yellow', 1: 'red'}

COMPETENCE_COLOR = {3: 'green', 2: 'yellow', 1: 'red'}


# phase1 instruction  ({block_num}/{total_blocks} filled in at runtime)
INST_PHASE1 = """\
[{block_num} / {total_blocks}]

이번 단계에서는 능력치가 보입니다.
협력도를 고려해 동물 두 마리를 골라서 점수를 최대한 높여주세요.

[Space] 키를 눌러 시작"""

INST_PHASE2 = """\
[{block_num} / {total_blocks} 블록]

이번 단계에서는 협력도가 보입니다.
능력치를 고려해 동물 두 마리를 골라서 점수를 최대한 높여주세요

[Space] 키를 눌러 시작"""

# phase2 instruction
