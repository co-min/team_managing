import platform
from pathlib import Path
import pandas as pd

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
_STIMULI = ROOT_DIR / 'stimuli'

# ─── Mode ─────────────────────────────────────────────────────────────────────
# MODE 1 : competence_table.csv       + score_table.csv        (3 domains)
# MODE 2 : competence_table_domain2.csv + score_table_domain2.csv (2 domains)
# MODE 3 : phase1 competency obs. 3 domains 18 trials / phase2 synergy obs. 2 domains 16 trials
MISSION_MODE = 4

# DOMAIN_ORDER: order in which domains are presented within a trial
#   'random'     — fixed-seed random shuffle
#   'sequential' — grouped in DOMAINS order
DOMAIN_ORDER = 'random'

# ─── Shared constants (referenced by mode config below) ──────────────────────
_D3_COMP  = _STIMULI / 'domain3' / 'competence_table.csv'
_D3_SCORE = _STIMULI / 'domain3' / 'score_table.csv'
_D2_COMP  = _STIMULI / 'domain2' / 'competence_table_domain2.csv'
_D2_SCORE = _STIMULI / 'domain2' / 'score_table_domain2.csv'
_D3_RANKED_SCORE = _STIMULI / 'domain3' / 'score_table_ranked.csv'


_DOMAINS_3 = ['cooking', 'repairing', 'tennis']
_DOMAINS_2 = ['cooking', 'repairing']

_COLOR_3 = {1: '#F44336', 2: '#FFEB3B', 3: '#4CAF50'}           # 3-level
_COLOR_4 = {1: '#F44336', 2: '#FF9800', 3: '#FFEB3B', 4: '#4CAF50'}  # 4-level

P3_TRIALS = 6  # common across all modes

if MISSION_MODE == 1:
    COMPETENCE_CSV    = _D3_COMP
    P2_COMPETENCE_CSV = _D3_COMP
    SCORE_CSV         = _D3_SCORE
    P2_SCORE_CSV      = _D3_SCORE
    DOMAINS           = _DOMAINS_3
    P2_DOMAINS        = _DOMAINS_3
    P1_TRIALS         = 18
    P2_TRIALS         = 18
    COMPETENCE_COLOR  = _COLOR_3
elif MISSION_MODE == 2:
    COMPETENCE_CSV    = _D2_COMP
    P2_COMPETENCE_CSV = _D2_COMP
    SCORE_CSV         = _D2_SCORE
    P2_SCORE_CSV      = _D2_SCORE
    DOMAINS           = _DOMAINS_2
    P2_DOMAINS        = _DOMAINS_2
    P1_TRIALS         = 16
    P2_TRIALS         = 16
    COMPETENCE_COLOR  = _COLOR_4
elif  MISSION_MODE == 3:
    COMPETENCE_CSV    = _D3_COMP
    SCORE_CSV         = _D3_SCORE
    P2_COMPETENCE_CSV = _D2_COMP
    P2_SCORE_CSV      = _D2_SCORE
    DOMAINS           = _DOMAINS_3
    P2_DOMAINS        = _DOMAINS_2
    P1_TRIALS         = 18
    P2_TRIALS         = 16
    COMPETENCE_COLOR  = _COLOR_3

else:
    COMPETENCE_CSV    = _D3_COMP
    SCORE_CSV         = _D3_RANKED_SCORE
    P2_COMPETENCE_CSV = _D3_COMP
    P2_SCORE_CSV      = _D3_RANKED_SCORE
    DOMAINS           = _DOMAINS_3
    P2_DOMAINS        = _DOMAINS_3
    P1_TRIALS         = 18
    P2_TRIALS         = 18
    COMPETENCE_COLOR  = _COLOR_3    


# ─── Window ───────────────────────────────────────────────────────────────────
WINDOW_SIZE      = (1470, 956)   # TODO: adjust to your display
WINDOW_UNITS     = "pix"
WINDOW_FULLSCR   = True          # Set True for actual experiment
BACKGROUND_COLOR = "#2b2b2b"     # Dark gray matching PDF screenshots
MONITOR_NAME     = "testMonitor" # TODO: calibrate your monitor
SCREEN_NUMBER    = 1

# ─── Timing ──────────────────────────────────────────────────────────────────
MAX_RESPONSE_TIME    = 30.0     # seconds; None = unlimited
ITI_DURATION         = 1     # inter-trial interval (seconds)
CHOICE_GAP           = 0.5      # seconds between Choice 1 and Choice 2
FRAME_RATE           = 60       # Hz – used for frame log sanity checks
DOMAIN_ONSET_DURATION = 0.7     # seconds domain image is shown before choices appear

# ─── Text ────────────────────────────────────────────────────────────────────
FONT       = "AppleGothic" if platform.system() == "Darwin" else "Malgun Gothic"
TEXT_COLOR = "white"

# ─── Hover ITI ───────────────────────────────────────────────────────────────
HOVER_ITI_MIN_DISPLAY = 0.3     # seconds before button becomes active
HOVER_ITI_DWELL_TIME  = 0.5    # seconds of continuous hover to proceed
HOVER_BUTTON_RADIUS   = 45     # pixels
HOVER_BUTTON_LABEL    = "+"
HOVER_PROMPT_TEXT     = "Please look at the center."

# ─── Colours ─────────────────────────────────────────────────────────────────
WHITE_COLOR = "white"
GREEN_COLOR = "green"

# ─── Event Keys ──────────────────────────────────────────────────────────────
ARROW_OFFSET = 70
ARROW_RADIUS = 40

# ─── Feedback ────────────────────────────────────────────────────────────────
FB_TIME = 3.5


# Animal name -> char_ani code — derived from competence CSV for the active MODE
_comp_df  = pd.read_csv(COMPETENCE_CSV, skipinitialspace=True)
CHAR_CODE  = dict(zip(_comp_df['animal'].str.strip(), _comp_df['char_ani'].str.strip()))
ANIMAL_CODE = {v: k for k, v in CHAR_CODE.items()}

# Competence score -> border colour
# low: red 1.0~3.0 / middle: yellow 3.5~6.0 / high: green 6.5~9.0
def get_comp_color(score: float) -> str:
    if score <= 3.0:
        return COMPETENCE_COLOR[1]
    elif score <= 6.0:
        return COMPETENCE_COLOR[2]
    else:
        return COMPETENCE_COLOR[3]


# Synergy score -> block fill colour (dynamically built from CSVs)
_syn_df   = pd.read_csv(_STIMULI / 'synergy' / 'synergy_table.csv', skipinitialspace=True)
_color_df = pd.read_csv(_STIMULI / 'color_type' / 'synergy_color.csv', skipinitialspace=True)
_scores   = sorted(_syn_df['synergy_score'].unique())
_colors   = _color_df.sort_values('id')['color'].str.strip().tolist()
SYNERGY_COLOR = dict(zip(_scores, _colors))


# ─── Phase instructions ───────────────────────────────────────────────────────
# ({block_num}/{total_blocks} filled in at runtime)
INST_PHASE1 = """\
[{block_num} / {total_blocks}]

In this phase, you will see each animal's individual competence.
Think about their hidden teamwork and try to find the two animals with a perfect score.

Press [Space] to start"""

INST_PHASE2 = """\
[{block_num} / {total_blocks} blocks]

In this phase, you will see the animals' teamwork/synergy.
Predict their hidden competence and try to find the two animals with a perfect score.

Press [Space] to start"""


# ─── Practice ────────────────────────────────────────────────────────────────
PRACTICE_MODE      = False   # True: run a practice session before the main experiment / False: skip it
PRACTICE_DOMAINS   = ['cooking', 'repairing']
PRACTICE_P1_TRIALS = 4      # total number of Phase 1 practice trials
PRACTICE_P2_TRIALS = 4      # total number of Phase 2 practice trials

INST_PRACTICE_PHASE1 = (
    "Practice Phase 1: Competence\n\n"
    "Think about their hidden teamwork. Which two animals have a perfect score?\n\n"
    "Press [Space] to start"
)

INST_PRACTICE_PHASE2 = (
    "Practice Phase 2: Synergy\n\n"
    "Considering their competence, pick two animals to maximize the score.\n\n"
    "Press [Space] to start"
)

INST_PRACTICE_END     = "Practice is over.\nThe main experiment will begin shortly."
PRACTICE_END_DURATION = 3.0


# ─── Neon eyetracker ─────────────────────────────────────────────────────────
# Set USE_NEON=False to run without the eyetracker (NullNeonClient is used).
USE_NEON = True

NEON_DISCOVERY_TIMEOUT_S      = 10.0  # seconds to search for Companion device
NEON_RETRY_INTERVAL_S         = 1.0   # seconds between failed send retries
NEON_SHUTDOWN_FLUSH_TIMEOUT_S = 5.0   # seconds to wait for queue drain on exit

# AprilTag positions and size in PsychoPy 'height' units.
# height=1.0 spans the full screen height; for 1470×956 the X range is ≈ ±0.77.
# Positions are at screen edges so they do not overlap experiment stimuli.
# Adjust if your stimulus layout uses those areas.
NEON_APRILTAG_SIZE = 0.08
NEON_APRILTAG_POSITIONS = (
    (-0.70,  0.43),   # top-left
    ( 0.70,  0.43),   # top-right
    (-0.74,  0.00),   # mid-left
    ( 0.74,  0.00),   # mid-right
    # (0.3, 0.43),
    # (-0.3, 0.43),
    (-0.70, -0.43),   # bottom-left
    ( 0.70, -0.43),   # bottom-right
)
