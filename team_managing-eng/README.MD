# Animal Competence & Synergy Task (PsychoPy)

A PsychoPy behavioral experiment in which participants judge animals'
individual competence and pairwise synergy across several domains
(e.g. cooking, repairing, tennis). Optionally integrates with a
LabJack T4 (TTL triggers), Pupil Labs Neon (eye tracking), and
EyeLink.

> **Note for testers:** all hardware integrations are optional. If no
> LabJack / Neon / EyeLink device is connected, the task automatically
> falls back to a no-op client and runs normally — you do not need any
> special hardware to do a quick test run.

## 1. Requirements

- **Python 3.11** (required by PsychoPy in this project)
- Windows recommended (tested on Windows 10/11); should also run on macOS
- No eye tracker / LabJack required for a basic test run

## 2. Setup

```bash
git clone <this-repo>
cd team_managing-main
python set_up.py
```

`set_up.py` will:
1. Create a `.venv` using Python 3.11
2. Install everything in `requirements.txt`

Then activate the environment:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

If you'd rather set it up manually:

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Quick test run (no hardware)

Open [function/config/settings.py](function/config/settings.py) and set:

```python
WINDOW_FULLSCR = False   # so you can Alt-Tab / close the window easily
USE_NEON       = False   # skip Neon eye-tracker discovery entirely
```

LabJack connection is attempted automatically but fails silently
("LabJack not found → running without TTL") if no device is plugged in
— no config change needed there.

Then run:

```bash
python main.py
```

A dialog box will ask for a **Subject ID** and **Session** — any values
work for testing (e.g. `001` / `1`).

## 4. Controls

| Key / Action        | Effect                                  |
|----------------------|------------------------------------------|
| `Space`              | Advance past instruction screens          |
| `Escape`             | Quit the experiment at any time           |

## 5. Where results go

Output (behavioral results, frame logs, event logs) is written under a
`data/` folder created next to `main.py`, organized by subject ID.
`data/` is git-ignored, so nothing you generate during testing gets
committed.

## 6. Project structure

```
main.py                      Experiment entry point / block loop
initiate.py                  Window, LabJack, and Neon setup
set_up.py                    venv + dependency installer
function/
  config/                    settings.py (main config), window & key setup
  io/                        data loading, path building, logging, saving
  phases/                    phase1 / phase2 / phase3 trial logic, feedback
  practice/                  practice-block trials and tables
eye_func/                    EyeLink integration
utils/                       neon_client, labjack_trigger, response, screen helpers
stimuli/                     CSV tables defining animals, scores, synergy, colors
analysis/                    post-hoc ranking/analysis scripts
PsychoPy-Neon-Integration-Guide.md   Deep-dive on the Neon event-logging design
```

## 7. Experiment modes

`MISSION_MODE` in `settings.py` selects which stimulus set / trial
counts are used (1–4; see comments above the setting for details).
Domain order (`DOMAIN_ORDER`), trial counts, and instruction text are
also configured there.

## 8. Troubleshooting

- **"Python 3.11이 설치되어 있지 않습니다"** — install Python 3.11 and
  make sure `py -3.11` works, then re-run `set_up.py`.
- **Window opens fullscreen and you can't get out** — press `Escape`,
  or set `WINDOW_FULLSCR = False` in `settings.py` before running.
- **"LabJack not found" / "Neon not found" printed in the console** —
  expected and harmless when testing without that hardware.
