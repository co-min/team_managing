import platform
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).resolve().parents[2]
DATA_DIR        = ROOT_DIR / "data"


# ─── Window ───────────────────────────────────────────────────────────────────
WINDOW_SIZE      = (1470, 956)   # TODO: adjust to your display
WINDOW_UNITS     = "pix"
WINDOW_FULLSCR   = False          # Set True for actual experiment
BACKGROUND_COLOR = "#2b2b2b"      # Dark gray matching PDF screenshots
MONITOR_NAME     = "testMonitor"  # TODO: calibrate your monitor
SCREEN_NUMBER = 0

# ─── Timing ──────────────────────────────────────────────────────────────────
MAX_RESPONSE_TIME = 10.0          # seconds; None = unlimited
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
WHITE_COLOR    = "white"
GREEN_COLOR = "green"
BLACK_COLOR    = "black"

# --- Image objectives ---
IMG_OFFSET = 180
IMG_SIZE = (120, 120)

positions = {
            'top_far': (0, IMG_OFFSET * 3), 
            'top': (0, IMG_OFFSET),           
            'bottom': (0, -IMG_OFFSET),       
            'left': (-IMG_OFFSET, 0),        
            'right': (IMG_OFFSET, 0)          
        }


# --- Event Keys ---
ARROW_OFFSET = 60
ARROW_RADIUS = 30


# --- Trial ---
P1_TRIALS = 12
P2_TRIALS = 18

# --- Feed back ---
FB_TIME = 2


# Animal name -> char_ani code (matches the 'synergy' dict keys in main.py)
CHAR_CODE = {'duck': 'A', 'frog': 'B', 'panda': 'C', 'rabbit': 'D'}

# Synergy score -> block fill colour
SYNERGY_COLOR = {1: 'green', 0: 'yellow', -1: 'red'}

# Colour for the locked Choice 1 block
LOCKED_COLOR = '#4488ff'