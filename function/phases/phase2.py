"""
Phase 2 – Synergy Task (18 trials)

Trial flow
----------
Choice 1
  Block backgrounds stay white.
  A 4-directional ArrowKeyboard is displayed at the bottom-centre.
  Pressing an arrow key previews the corresponding animal: the other three
  blocks show their synergy score with that candidate
  (1 = green, 0 = yellow, -1 = red).  The candidate's own block stays white.
  A different arrow key switches the preview.
  Space bar confirms the current preview as Choice 1.

Choice 2
  The confirmed Choice 1 block turns blue and its arrow is dimmed.
  The remaining three animals' blocks keep the synergy scores shown during
  the preview.  The same arrow-key + space-bar mechanic picks Choice 2:
  pressing an arrow key previews the candidate; space bar confirms it
  (Choice 1 arrow excluded).

Returns {'choice1': char_code, 'choice2': char_code, 'rt1': float, 'rt2': float}
where char_code in {'A', 'B', 'C', 'D'}, or None on timeout.

Arrow → slot mapping (positions are randomised per trial via char_order)
-------------------------------------------------------------------------
  up    → slot index 0
  down  → slot index 1
  right → slot index 2
  left  → slot index 3
"""

from psychopy import event, core

from function.config.window_factory import get_shared_factory
from function.config.settings import MAX_RESPONSE_TIME
from function.io.frame_logger import FrameRecorder
from utils.arrow_keyboard import ArrowKeyboard
from utils.event_utils import check_escape

# Animal name -> char_ani code (matches the 'synergy' dict keys in main.py)
_CHAR_CODE = {'duck': 'A', 'frog': 'B', 'panda': 'C', 'rabbit': 'D'}

# Synergy score -> block fill colour
_SYNERGY_COLOR = {1: 'green', 0: 'yellow', -1: 'red'}


# Vertical offset (px) below the animal grid where the ArrowKeyboard sits
_KB_Y = 0


def run_phase2_trial(win, global_clock, frame_log, synergy, domain, char_order):
    """
    Run one Phase 2 trial.

    Parameters
    ----------
    win          : psychopy.visual.Window
    global_clock : psychopy.core.Clock  (experiment-wide)
    frame_log    : FrameLog dict (mutated in-place via FrameRecorder)
    synergy      : dict  {(charA, charB): int}  sorted-tuple key, from main._load_all_data()
    domain       : str   'cooking' | 'repairing' | 'tennis'
    char_order   : list  [up_animal, down_animal, right_animal, left_animal]

    Returns
    -------
    dict  {'choice1': char_code, 'choice2': char_code, 'rt1': float, 'rt2': float}
    or None on timeout
    """
    factory = get_shared_factory(win)
    factory.apply_layout(char_order)
    char_list = factory.char_list

    factory.update_domain(domain)
    factory.reset_ui_states()              # all block fills -> white

    kb  = ArrowKeyboard(win, pos=(0, _KB_Y))
    rec = FrameRecorder(frame_log, global_clock)

    # ── Choice 1 ──────────────────────────────────────────────────────────────
    kb.reset_colors()
    choice1_idx  = choice1_code = None
    preview_idx  = None
    preview_code = None
    rt1 = None
    clock = core.Clock()

    while choice1_code is None:
        check_escape(win)
        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space':
                if preview_idx is not None:
                    choice1_idx  = preview_idx
                    choice1_code = _CHAR_CODE[char_list[preview_idx]]
                    rt1 = t
            else:
                kb.reset_colors()
                idx = kb.select(pressed)
                if idx is not None:
                    preview_idx  = idx
                    preview_code = _CHAR_CODE[char_list[idx]]
                    for i, char_name in enumerate(char_list):
                        if i == idx:
                            factory.block_stims[char_name].setFillColor('white')
                        else:
                            code_other = _CHAR_CODE[char_name]
                            skey  = tuple(sorted([preview_code, code_other]))
                            score = synergy.get(skey, 0)
                            factory.block_stims[char_name].setFillColor(
                                _SYNERGY_COLOR.get(score, 'white')
                            )

        if choice1_code is not None:
            factory.draw_base_scene(phase_type='phase2')
            kb.draw()
            win.flip()
            core.wait(0.15)
            rec.log_final(win, {'response': True})
            break

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            return None

        factory.draw_base_scene(phase_type='phase2')
        kb.draw()
        rec.flip_and_log(win)

    # Darken the locked animal's image with a semi-transparent overlay
    factory.set_animal_locked(char_list[choice1_idx], True)

    # Set synergy-based block colours for the remaining three animals
    for i, char_name in enumerate(char_list):
        if i == choice1_idx:
            continue
        code  = _CHAR_CODE[char_name]
        key   = tuple(sorted([choice1_code, code]))
        score = synergy.get(key, 0)
        factory.block_stims[char_name].setFillColor(_SYNERGY_COLOR.get(score, 'white'))

    # ── Choice 2 ──────────────────────────────────────────────────────────────
    rec.start_segment()
    kb.reset_colors()
    kb.set_excluded(choice1_idx)
    preview2_idx = None
    rt2 = None
    clock = core.Clock()
    choice2_code = None

    while choice2_code is None:
        check_escape(win)
        for pressed, t in event.getKeys(keyList=kb.valid_keys + ['space'], timeStamped=clock):
            if pressed == 'space':
                if preview2_idx is not None:
                    choice2_code = _CHAR_CODE[char_list[preview2_idx]]
                    rt2 = t
            else:
                kb.reset_colors()
                idx = kb.select(pressed, excluded_idx=choice1_idx)
                if idx is not None:
                    preview2_idx = idx
                    preview2_code = _CHAR_CODE[char_list[idx]]
                    for i, char_name in enumerate(char_list):
                        if i == idx:
                            factory.block_stims[char_name].setFillColor('white')
                        else:
                            code_other = _CHAR_CODE[char_name]
                            skey  = tuple(sorted([preview2_code, code_other]))
                            score = synergy.get(skey, 0)
                            factory.block_stims[char_name].setFillColor(
                                _SYNERGY_COLOR.get(score, 'white')
                            )

        if choice2_code is not None:
            factory.draw_base_scene(phase_type='phase2')
            kb.draw()
            win.flip()
            core.wait(0.15)
            rec.log_final(win, {'response': True})
            break

        if MAX_RESPONSE_TIME and clock.getTime() > MAX_RESPONSE_TIME:
            rec.log_final(win, {'response': False})
            return None

        factory.draw_base_scene(phase_type='phase2')
        kb.draw()
        rec.flip_and_log(win)

    return {'choice1': choice1_code, 'choice2': choice2_code, 'rt1': rt1, 'rt2': rt2}
