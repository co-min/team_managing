"""
practice_loop.py
-----------------
Standalone practice mode — 3 animals, 2 domains (cooking / repairing).

Practice flow
-------------
Phase 1 (competence task) : one trial per domain, with competence-colour borders
Phase 2 (synergy task)    : one trial per domain, with live synergy-colour blocks

Entry point: run_practice(win)
"""

import math
import random
from pathlib import Path

import pandas as pd
from psychopy import visual, event, core

from function.config.settings import (
    FONT, COMPETENCE_COLOR, SYNERGY_COLOR, MAX_RESPONSE_TIME,
    PRACTICE_DOMAINS, PRACTICE_P1_TRIALS, PRACTICE_P2_TRIALS,
    INST_PRACTICE_PHASE1, INST_PRACTICE_PHASE2,
    INST_PRACTICE_END, PRACTICE_END_DURATION,
)
from function.phases.feedback import run_feedback
from utils.event_utils import check_escape
from utils.screen_utils import show_instructions



# ══════════════════════════════════════════════════════════════════════════════
# Module-level constants
# ══════════════════════════════════════════════════════════════════════════════

_PRACTICE_DIR = Path(__file__).parent
_IMAGE_DIR    = _PRACTICE_DIR / "image"

_BORDER_EXTRA = 12     # border extends this many px beyond animal image

# Arrow key → slot index  (down arrow is not used)
_KEY_TO_SLOT = {'up': 0, 'right': 1, 'left': 2}

_COLOR_IDLE   = '#0055ff'
_COLOR_HOVER  = '#00d9ff'
_COLOR_LOCKED = '#00d9ff'

_RESPONSE_LIMIT = MAX_RESPONSE_TIME


def _compute_practice_layout(win) -> dict:
    """Compute all size/position values proportional to the window size."""
    W, H = win.size
    half_h = H // 2
    half_w = W // 2

    animal_size = int(H * 0.140)
    domain_size = int(H * 0.190)
    domain_y    = int(half_h * 0.78)

    slot_top_y  = int(half_h * 0.13)
    slot_side_x = int(half_w * 0.300)
    slot_side_y = -int(half_h * 0.27)

    block_h         = int(H * 0.050)
    block_w         = animal_size + 20
    block_offset_dy = animal_size // 2 + 10 + block_h // 2

    arrow_radius = int(H * 0.028)
    arrow_y_up   = -int(half_h * 0.38)
    arrow_side_x = int(half_w * 0.063)
    arrow_side_y = -int(half_h * 0.48)

    return dict(
        animal_size        = animal_size,
        domain_size        = domain_size,
        domain_y           = domain_y,
        slot_positions     = [(0, slot_top_y), (slot_side_x, slot_side_y), (-slot_side_x, slot_side_y)],
        block_h            = block_h,
        block_w            = block_w,
        block_slot_offsets = [(0, block_offset_dy)] * 3,
        arrow_defs         = [
            (0,             arrow_y_up,   0  ),
            ( arrow_side_x, arrow_side_y, 90 ),
            (-arrow_side_x, arrow_side_y, 270),
        ],
        arrow_radius       = arrow_radius,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def _load_practice_data() -> dict:
    """
    Load the three practice CSVs and return look-up dicts.

    Returns a dict with keys:
        animals      : list[str]                     — 3 animal names (CSV order)
        char_code    : {animal: char_code}
        image_paths  : {animal: str}                 — absolute paths to practice images
        competence   : {char_code: {domain: int}}
        synergy      : {(charA, charB): float}       — sorted-tuple key
        score        : {(charA, charB): {domain: float}}
        score_ranges : {domain: (min, max)}
    """
    comp_df  = pd.read_csv(_PRACTICE_DIR / 'practice_comp_table.csv',   skipinitialspace=True)
    syn_df   = pd.read_csv(_PRACTICE_DIR / 'practice_synergy_table.csv', skipinitialspace=True)
    score_df = pd.read_csv(_PRACTICE_DIR / 'practice_score.csv',         skipinitialspace=True)

    animals   = list(comp_df['animal'].str.strip())
    char_code = dict(zip(animals, comp_df['char_ani'].str.strip()))

    # img_file column has a typo (all rows point to one file), so pair images by row order.
    image_files = sorted(_IMAGE_DIR.glob('*.png'))
    image_paths = {animal: str(path) for animal, path in zip(animals, image_files)}

    competence = {
        str(row['char_ani']).strip(): {d: int(row[d]) for d in PRACTICE_DOMAINS}
        for _, row in comp_df.iterrows()
    }

    synergy = {
        tuple(sorted([str(r['char1']).strip(), str(r['char2']).strip()])): float(r['synergy_score'])
        for _, r in syn_df.iterrows()
    }

    score = {
        tuple(sorted([str(r['char1']).strip(), str(r['char2']).strip()])):
            {d: float(r[f'sc_{d}']) for d in PRACTICE_DOMAINS}
        for _, r in score_df.iterrows()
    }

    score_ranges = {
        d: (float(score_df[f'sc_{d}'].min()), float(score_df[f'sc_{d}'].max()))
        for d in PRACTICE_DOMAINS
    }

    return dict(
        animals=animals,
        char_code=char_code,
        image_paths=image_paths,
        competence=competence,
        synergy=synergy,
        score=score,
        score_ranges=score_ranges,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Practice scene — all psychopy stimuli
# ══════════════════════════════════════════════════════════════════════════════

class _PracticeScene:
    """
    Manages all PsychoPy stimuli for the 3-animal practice display.

    Slots: 0 = top, 1 = right, 2 = left.
    Call set_domain() before the first draw().
    """

    def __init__(self, win: visual.Window, data: dict):
        layout = _compute_practice_layout(win)
        az = layout['animal_size']
        bz = az + _BORDER_EXTRA

        self._slot_positions     = layout['slot_positions']
        self._block_slot_offsets = layout['block_slot_offsets']
        self._char_order: list   = data['animals'][:]
        self._locked: set        = set()
        self._border_colors: dict = {}
        self._current_domain: str = ''

        self.animal_stims = {
            animal: visual.ImageStim(
                win, image=data['image_paths'][animal], size=(az, az), units='pix',
            )
            for animal in data['animals']
        }
        self.border_stims = {
            animal: visual.Rect(
                win, width=bz, height=bz, lineWidth=8,
                lineColor=None, fillColor=None, units='pix',
            )
            for animal in data['animals']
        }
        self.block_stims = {
            animal: visual.Rect(
                win, width=layout['block_w'], height=layout['block_h'],
                fillColor=None, lineColor=None, opacity=0, units='pix',
            )
            for animal in data['animals']
        }
        self.overlay_stims = {
            animal: visual.Rect(
                win, width=az, height=az,
                fillColor='black', lineColor=None, opacity=0.5, units='pix',
            )
            for animal in data['animals']
        }
        self.arrow_stims = [
            visual.Polygon(
                win, edges=3, radius=layout['arrow_radius'],
                pos=(dx, dy), ori=ori,
                fillColor=_COLOR_IDLE, lineColor=None,
            )
            for dx, dy, ori in layout['arrow_defs']
        ]
        self.domain_stims = {
            domain: visual.ImageStim(
                win, image=f"image/domains/{domain}.png",
                pos=(0, layout['domain_y']),
                size=(layout['domain_size'], layout['domain_size']),
            )
            for domain in PRACTICE_DOMAINS
        }

    # ── domain ────────────────────────────────────────────────────────────────

    def set_domain(self, domain: str) -> None:
        self._current_domain = domain

    # ── layout ────────────────────────────────────────────────────────────────

    def apply_layout(self, char_order: list) -> None:
        """Assign each animal to one of the 3 display slots."""
        self._char_order = list(char_order)
        for slot, animal in enumerate(char_order):
            pos = self._slot_positions[slot]
            for stim in (self.animal_stims[animal], self.border_stims[animal],
                         self.overlay_stims[animal]):
                stim.setPos(pos)
            dx, dy = self._block_slot_offsets[slot]
            self.block_stims[animal].setPos((pos[0] + dx, pos[1] + dy))

    # ── state reset ───────────────────────────────────────────────────────────

    def reset_ui(self) -> None:
        """Clear all locks, borders, and synergy blocks; reset arrows to idle."""
        self._locked.clear()
        self._border_colors.clear()
        for animal in self._char_order:
            self.border_stims[animal].lineColor = None
            self.block_stims[animal].opacity    = 0
        for arrow in self.arrow_stims:
            arrow.fillColor = _COLOR_IDLE

    # ── border control ────────────────────────────────────────────────────────

    def store_border_color(self, animal: str, color) -> None:
        """Save a border colour without revealing it; use show_border() to display."""
        self._border_colors[animal] = color

    def show_border(self, animal: str) -> None:
        """Reveal the stored border colour for this animal."""
        self.border_stims[animal].lineColor = self._border_colors.get(animal, 'white')

    def hide_border(self, animal: str) -> None:
        self.border_stims[animal].lineColor = None

    # ── arrow control ─────────────────────────────────────────────────────────

    def hover_arrow(self, slot: int) -> None:
        self.arrow_stims[slot].fillColor = _COLOR_HOVER

    def reset_arrows(self, locked_slot: int = None) -> None:
        """Reset all arrows to idle, optionally marking one slot as locked."""
        for i, arrow in enumerate(self.arrow_stims):
            arrow.fillColor = _COLOR_LOCKED if i == locked_slot else _COLOR_IDLE

    # ── animal lock ───────────────────────────────────────────────────────────

    def lock_animal(self, animal: str) -> None:
        """Overlay a dark tint to mark this animal as Choice 1 (locked)."""
        self._locked.add(animal)

    # ── rendering ─────────────────────────────────────────────────────────────

    def draw(self, show_blocks: bool = False) -> None:
        """Draw domain image → synergy blocks → animals → overlays → borders → arrows."""
        if self._current_domain:
            self.domain_stims[self._current_domain].draw()

        for animal in self._char_order:
            if show_blocks:
                self.block_stims[animal].draw()
            self.animal_stims[animal].draw()
            if animal in self._locked:
                self.overlay_stims[animal].draw()
            self.border_stims[animal].draw()

        for arrow in self.arrow_stims:
            arrow.draw()


# ══════════════════════════════════════════════════════════════════════════════
# Synergy block helper
# ══════════════════════════════════════════════════════════════════════════════

def _update_synergy_blocks(scene, char_order, pivot_slot, data, hide_slot=None):
    """
    Colour each non-pivot animal's block by its synergy score with the pivot.

    hide_slot : optional additional slot to keep hidden (e.g. already-locked Choice 1)
    """
    pivot_code = data['char_code'][char_order[pivot_slot]]

    for slot, animal in enumerate(char_order):
        scene.block_stims[animal].opacity = 0
        if slot in (pivot_slot, hide_slot):
            continue
        other_code = data['char_code'][animal]
        syn_key    = tuple(sorted([pivot_code, other_code]))
        color      = SYNERGY_COLOR.get(data['synergy'].get(syn_key, 0), 'white')
        scene.block_stims[animal].fillColor = color
        scene.block_stims[animal].opacity   = 1


# ══════════════════════════════════════════════════════════════════════════════
# Inner choice loops
# ══════════════════════════════════════════════════════════════════════════════

def _competence_choice_loop(win, scene, char_order, excluded_slot=None,
                            show_hover_border=True, confirm_wait=0.15):
    """
    Arrow-key navigation + Space-to-confirm for Phase 1 (competence) trials.

    show_hover_border : reveal the stored competence-colour border on hover
                        (False for Choice 1, True for Choice 2)

    Returns (slot_idx, animal_name, rt) or (None, None, None) on timeout.
    """
    clock        = core.Clock()
    preview_slot = None

    while True:
        check_escape(win)

        for pressed, t in event.getKeys(keyList=list(_KEY_TO_SLOT) + ['space'],
                                        timeStamped=clock):
            if pressed == 'space' and preview_slot is not None:
                if excluded_slot is not None:
                    scene.lock_animal(char_order[preview_slot])
                scene.draw(show_blocks=False)
                win.flip()
                core.wait(confirm_wait)
                return preview_slot, char_order[preview_slot], t

            slot = _KEY_TO_SLOT.get(pressed)
            if slot is not None and slot != excluded_slot:
                preview_slot = slot
                scene.reset_arrows(locked_slot=excluded_slot)
                scene.hover_arrow(slot)
                # Hide all borders, then restore locked and hovered
                for animal in char_order:
                    scene.hide_border(animal)
                if excluded_slot is not None:
                    scene.show_border(char_order[excluded_slot])
                if show_hover_border:
                    scene.show_border(char_order[slot])

        if clock.getTime() > _RESPONSE_LIMIT:
            return None, None, None

        scene.draw(show_blocks=False)
        win.flip()


def _synergy_choice_loop(win, scene, char_order, data,
                         excluded_slot=None, freeze_blocks=False, confirm_wait=0.15):
    """
    Arrow-key navigation + Space-to-confirm for Phase 2 (synergy) trials.

    freeze_blocks : if True, synergy block colours do not update on hover
                    (False for Choice 1, True for Choice 2)

    Returns (slot_idx, animal_name, rt) or (None, None, None) on timeout.
    """
    clock        = core.Clock()
    preview_slot = None

    while True:
        check_escape(win)

        for pressed, t in event.getKeys(keyList=list(_KEY_TO_SLOT) + ['space'],
                                        timeStamped=clock):
            if pressed == 'space' and preview_slot is not None:
                if excluded_slot is not None:
                    scene.lock_animal(char_order[preview_slot])
                scene.draw(show_blocks=True)
                win.flip()
                core.wait(confirm_wait)
                return preview_slot, char_order[preview_slot], t

            slot = _KEY_TO_SLOT.get(pressed)
            if slot is not None and slot != excluded_slot:
                preview_slot = slot
                scene.reset_arrows(locked_slot=excluded_slot)
                scene.hover_arrow(slot)
                if not freeze_blocks:
                    _update_synergy_blocks(
                        scene, char_order, slot, data, hide_slot=excluded_slot,
                    )

        if clock.getTime() > _RESPONSE_LIMIT:
            return None, None, None

        scene.draw(show_blocks=True)
        win.flip()


# ══════════════════════════════════════════════════════════════════════════════
# Practice trial runners
# ══════════════════════════════════════════════════════════════════════════════

def _run_phase1_trial(win, scene, data, char_order, domain):
    """
    One Phase 1 practice trial — competence task.

    Choice 1 : free pick, no border hint.
    Choice 2 : competence-colour borders appear on hover.

    Returns {'choice1': char_code, 'choice2': char_code} or None on timeout.
    """
    scene.apply_layout(char_order)
    scene.set_domain(domain)
    scene.reset_ui()

    # Choice 1 — no border hint
    slot1, animal1, _ = _competence_choice_loop(
        win, scene, char_order,
        show_hover_border=False, confirm_wait=0.15,
    )
    if animal1 is None:
        return None

    # Store competence-colour borders; keep them all hidden until hovered
    for animal in char_order:
        code  = data['char_code'][animal]
        level = data['competence'][code][domain]
        color = COMPETENCE_COLOR.get(level, 'white')
        scene.store_border_color(animal, color)
        scene.hide_border(animal)

    scene.lock_animal(animal1)
    scene.reset_arrows(locked_slot=slot1)
    scene.show_border(animal1)   # locked animal border always visible

    # Choice 2 — competence colour border appears on hover
    _, animal2, _ = _competence_choice_loop(
        win, scene, char_order,
        excluded_slot=slot1, show_hover_border=True, confirm_wait=1.0,
    )
    if animal2 is None:
        return None

    return {'choice1': data['char_code'][animal1], 'choice2': data['char_code'][animal2]}


def _run_phase2_trial(win, scene, data, char_order, domain):
    """
    One Phase 2 practice trial — synergy task.

    Choice 1 : synergy block colours update live as the player hovers.
    Choice 2 : block colours are frozen at the Choice-1 state.

    Returns {'choice1': char_code, 'choice2': char_code} or None on timeout.
    """
    scene.apply_layout(char_order)
    scene.set_domain(domain)
    scene.reset_ui()

    # Choice 1 — live synergy blocks
    slot1, animal1, _ = _synergy_choice_loop(
        win, scene, char_order, data,
        freeze_blocks=False, confirm_wait=0.15,
    )
    if animal1 is None:
        return None

    # Lock Choice 1 and seed synergy colours for Choice 2
    scene.lock_animal(animal1)
    scene.reset_arrows(locked_slot=slot1)
    _update_synergy_blocks(scene, char_order, slot1, data)

    # Choice 2 — blocks frozen
    _, animal2, _ = _synergy_choice_loop(
        win, scene, char_order, data,
        excluded_slot=slot1, freeze_blocks=True, confirm_wait=1.0,
    )
    if animal2 is None:
        return None

    return {'choice1': data['char_code'][animal1], 'choice2': data['char_code'][animal2]}


# ══════════════════════════════════════════════════════════════════════════════
# Instruction / message helpers
# ══════════════════════════════════════════════════════════════════════════════


def _show_message(win, text, duration=2.5):
    """Display a brief timed message with no input required."""
    stim  = visual.TextStim(
        win, text=text, font=FONT, color='white', height=45, wrapWidth=800, bold = True
    )
    clock = core.Clock()
    while clock.getTime() < duration:
        check_escape(win)
        stim.draw()
        win.flip()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def run_practice(win: visual.Window) -> None:
    """
    Run the full practice session (Phase 1 then Phase 2).

    Each phase runs one trial per domain (cooking + repairing = 2 trials/phase).
    No data is saved. Feedback is shown after every trial.
    """
    data  = _load_practice_data()
    scene = _PracticeScene(win, data)

    cumulative = {'total': 0.0, 'phase': 0.0}
    cumulative.update({d: 0.0 for d in PRACTICE_DOMAINS})

    def _make_trial_domains(n: int) -> list:
        """PRACTICE_DOMAINS를 순환해 n개의 도메인 리스트를 생성."""
        cycle = math.ceil(n / len(PRACTICE_DOMAINS))
        return (PRACTICE_DOMAINS * cycle)[:n]

    # ── Practice Phase 1 : competence task ───────────────────────────────────
    show_instructions(win, INST_PRACTICE_PHASE1)
    cumulative['phase'] = 0.0
    for d in PRACTICE_DOMAINS:
        cumulative[d] = 0.0

    p1_domains = _make_trial_domains(PRACTICE_P1_TRIALS)
    n_per_domain_p1 = math.ceil(PRACTICE_P1_TRIALS / len(PRACTICE_DOMAINS))
    for domain in p1_domains:
        char_order = random.sample(data['animals'], len(data['animals']))
        result     = _run_phase1_trial(win, scene, data, char_order, domain)
        if result:
            pair_key    = tuple(sorted([result['choice1'], result['choice2']]))
            trial_score = data['score'].get(pair_key, {}).get(domain, 0.0)
            cumulative['total'] += trial_score
            cumulative['phase'] += trial_score
            cumulative[domain]  += trial_score
            run_feedback(
                win, trial_score, domain,
                cumulative_score=cumulative['total'],
                phase_score=cumulative['phase'],
                domain_scores={d: cumulative[d] for d in PRACTICE_DOMAINS},
                block_domains=PRACTICE_DOMAINS,
                n_trials_per_domain=n_per_domain_p1,
                score_ranges=data['score_ranges'],
            )

    # ── Practice Phase 2 : synergy task ──────────────────────────────────────
    show_instructions(win, INST_PRACTICE_PHASE2)
    cumulative['phase'] = 0.0
    for d in PRACTICE_DOMAINS:
        cumulative[d] = 0.0

    p2_domains = _make_trial_domains(PRACTICE_P2_TRIALS)
    n_per_domain_p2 = math.ceil(PRACTICE_P2_TRIALS / len(PRACTICE_DOMAINS))
    for domain in p2_domains:
        char_order = random.sample(data['animals'], len(data['animals']))
        result     = _run_phase2_trial(win, scene, data, char_order, domain)
        if result:
            pair_key    = tuple(sorted([result['choice1'], result['choice2']]))
            trial_score = data['score'].get(pair_key, {}).get(domain, 0.0)
            cumulative['total'] += trial_score
            cumulative['phase'] += trial_score
            cumulative[domain]  += trial_score
            run_feedback(
                win, trial_score, domain,
                cumulative_score=cumulative['total'],
                phase_score=cumulative['phase'],
                domain_scores={d: cumulative[d] for d in PRACTICE_DOMAINS},
                block_domains=PRACTICE_DOMAINS,
                n_trials_per_domain=n_per_domain_p2,
                score_ranges=data['score_ranges'],
            )

    _show_message(win, INST_PRACTICE_END, duration=PRACTICE_END_DURATION)
