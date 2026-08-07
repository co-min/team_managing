"""
event_dispatch.py
-----------------
Unified event dispatcher — fires LabJack TTL and Neon section events from a
single call site so both timelines stay aligned.

Functions prefixed 'callonflip_' register callbacks for the next win.flip().
Functions prefixed 'on_' fire immediately (key-press responses, boundaries).

Phase integer mapping: 1 = phase_1, 2 = phase_2, 3 = phase_3
"""

from utils.labjack_trigger import (
    send_trigger,
    send_trigger_async,
    reset_trigger,
    ANIMAL_IDX,
    TRIG_TASK_START, TRIG_TASK_END,
    TRIG_P1_BLOCK_START, TRIG_P2_BLOCK_START, TRIG_P3_BLOCK_START,
    TRIG_P1_TRIAL_START, TRIG_P2_TRIAL_START, TRIG_P3_TRIAL_START,
    TRIG_P1_TRIAL_END,   TRIG_P2_TRIAL_END,   TRIG_P3_TRIAL_END,
    TRIG_P3_STIMULUS,
    TRIG_P1_CHOICE_ONSET, TRIG_P2_CHOICE_ONSET,
    TRIG_P1_CHOICE1, TRIG_P1_CHOICE2,
    TRIG_P2_CHOICE1, TRIG_P2_CHOICE2,
    TRIG_P3_CHOICE1, TRIG_P3_CHOICE2,
    TRIG_P1_FEEDBACK, TRIG_P2_FEEDBACK, TRIG_P3_FEEDBACK,
)
from utils.neon_client import section_start_events, section_end_events

# ── Lookup tables ─────────────────────────────────────────────────────────────

PHASE_INT = {'phase_1': 1, 'phase_2': 2, 'phase_3': 3}

_BLOCK_START_TRIG = {
    'phase_1': TRIG_P1_BLOCK_START,
    'phase_2': TRIG_P2_BLOCK_START,
    'phase_3': TRIG_P3_BLOCK_START,
}
_TRIAL_START_TRIG = {1: TRIG_P1_TRIAL_START, 2: TRIG_P2_TRIAL_START, 3: TRIG_P3_TRIAL_START}
_TRIAL_END_TRIG   = {1: TRIG_P1_TRIAL_END,   2: TRIG_P2_TRIAL_END,   3: TRIG_P3_TRIAL_END}
_FEEDBACK_TRIG    = {1: TRIG_P1_FEEDBACK,     2: TRIG_P2_FEEDBACK,    3: TRIG_P3_FEEDBACK}

# (phase, slot) → LJ onset code. Missing keys = no LJ trigger (e.g. P1/P2 choice2).
# P3 fires TRIG_P3_STIMULUS for both choice slots via async pulse.
_CHOICE_ONSET_TRIG = {
    (1, 1): TRIG_P1_CHOICE_ONSET,
    (2, 1): TRIG_P2_CHOICE_ONSET,
    (3, 1): TRIG_P3_STIMULUS,
    (3, 2): TRIG_P3_STIMULUS,
}
_CHOICE_BASE = {
    (1, 1): TRIG_P1_CHOICE1, (1, 2): TRIG_P1_CHOICE2,
    (2, 1): TRIG_P2_CHOICE1, (2, 2): TRIG_P2_CHOICE2,
    (3, 1): TRIG_P3_CHOICE1, (3, 2): TRIG_P3_CHOICE2,
}


# ── Session / Task ────────────────────────────────────────────────────────────

def on_task_start(neon, lj_handle) -> None:
    send_trigger(lj_handle, TRIG_TASK_START)
    neon.enqueue_events("TASK_START", metadata={"task_type": "session"})


def on_task_end(neon, lj_handle) -> None:
    send_trigger(lj_handle, TRIG_TASK_END)
    neon.enqueue_events("TASK_END", metadata={"task_type": "session"})


# ── Block ─────────────────────────────────────────────────────────────────────

def on_block_start(neon, lj_handle, phase: str, block_index: int) -> None:
    """phase is 'phase_1', 'phase_2', or 'phase_3'."""
    send_trigger(lj_handle, _BLOCK_START_TRIG.get(phase, 0))
    neon.enqueue_events(
        f"P{PHASE_INT.get(phase, 0)}_BLOCK_{block_index:02d}_START",
        metadata={"task_type": "block", "phase": phase, "trial_index": block_index},
    )


# ── Trial ─────────────────────────────────────────────────────────────────────

def callonflip_trial_start(win, neon, lj_handle, phase: int, trial_index: int) -> None:
    """Register trial-start events for the next win.flip() (domain-onset frame)."""
    win.callOnFlip(send_trigger, lj_handle, _TRIAL_START_TRIG[phase])
    neon.call_on_flip(
        win,
        section_start_events(trial_index, f"P{phase}_DOMAIN_ONSET", first=True),
        task_type="trial", phase=phase, trial_index=trial_index,
    )


def on_trial_end(neon, lj_handle, phase: int, trial_index: int) -> None:
    """Fire immediately after the last choice (or on timeout)."""
    send_trigger(lj_handle, _TRIAL_END_TRIG[phase])
    neon.enqueue_events(
        f"TRIAL_{trial_index:03d}_P{phase}_END",
        metadata={"task_type": "trial", "phase": phase, "trial_index": trial_index},
    )


# ── Choice onset (stimulus appears on screen) ─────────────────────────────────

def callonflip_choice_onset(win, neon, lj_handle, phase: int, trial_index: int, slot: int) -> None:
    """Register choice-onset events for the next win.flip().

    LabJack trigger is only sent for (phase, slot) entries in _CHOICE_ONSET_TRIG.
    P3 uses send_trigger_async + reset_trigger (latch pulse); P1/P2 use send_trigger.
    """
    lj_code = _CHOICE_ONSET_TRIG.get((phase, slot))
    if lj_code is not None:
        if phase == 3:
            win.callOnFlip(send_trigger_async, lj_handle, lj_code)
            win.callOnFlip(reset_trigger, lj_handle)
        else:
            win.callOnFlip(send_trigger, lj_handle, lj_code)
    neon.call_on_flip(
        win,
        section_start_events(trial_index, f"P{phase}_CHOICE{slot}"),
        task_type="trial", phase=phase, trial_index=trial_index,
    )


# ── Choice response ───────────────────────────────────────────────────────────

def on_choice_lj(lj_handle, phase: int, slot: int, animal: str) -> None:
    """Send LabJack animal-encoded choice trigger. Call immediately on key press."""
    send_trigger(lj_handle, _CHOICE_BASE[(phase, slot)] + ANIMAL_IDX[animal])


def on_choice_neon(
    neon, phase: int, trial_index: int, slot: int, animal: str,
    outcome: str = "RESPONSE",
) -> None:
    """Enqueue Neon choice+animal event immediately (no flip needed)."""
    label = f"P{phase}_CHOICE{slot}_{animal.upper()}_{outcome}"
    neon.enqueue_events(
        section_end_events(trial_index, label),
        metadata={"task_type": "trial", "phase": phase, "trial_index": trial_index},
    )


# ── Feedback ──────────────────────────────────────────────────────────────────

def callonflip_feedback(win, neon, lj_handle, phase: int, trial_index: int) -> None:
    """Register feedback-onset events for the next win.flip()."""
    win.callOnFlip(send_trigger, lj_handle, _FEEDBACK_TRIG.get(phase, 0))
    neon.call_on_flip(
        win,
        section_start_events(trial_index, f"P{phase}_FEEDBACK", first=True),
        task_type="feedback", phase=phase, trial_index=trial_index,
    )
