"""
frame_logger.py
---------------
Immutable frame-level log accumulator using TypedDict.

Usage
-----
    log = make_frame_log(phase="phase_1", trial_id=0, stim_pair_id="pair_001")
    # inside the flip loop:
    log = set_onset(log, flip_time)
    log = log_frame(log, frame_idx, flip_time, global_clock.getTime(), "stimulus_onset")
    # after loop:
    rows = get_rows(log)
"""

from typing import Any, Dict, List, Optional, TypedDict


class FrameLog(TypedDict):
    """Accumulator for per-frame log entries of one trial/phase."""
    phase:        str
    trial_id:     int
    stim_pair_id: str
    onset_time:   Optional[float]
    rows:         List[Dict[str, Any]]
    ttl_code:     Optional[int]


def make_frame_log(phase: str, trial_id: int, stim_pair_id: str) -> FrameLog:
    return {
        "phase":        phase,
        "trial_id":     trial_id,
        "stim_pair_id": stim_pair_id,
        "onset_time":   None,
        "rows":         [],
        "ttl_code":     None,
    }


def set_onset(log: FrameLog, t: float) -> FrameLog:
    """Return a new FrameLog with onset_time set to *t*."""
    log["onset_time"] = t
    return log


def log_frame(
    log: FrameLog,
    frame_idx: int,
    flip_time: float,
    global_time: float,
    event_marker: str = "",
    ttl_code: Optional[int] = None,
) -> FrameLog:
    """Return a new FrameLog with one frame entry appended."""
    elapsed = (flip_time - log["onset_time"]) if log["onset_time"] is not None else 0.0
    row: Dict[str, Any] = {
        "frame_idx":    frame_idx,
        "phase":        log["phase"],
        "trial_id":     log["trial_id"],
        "stim_pair_id": log["stim_pair_id"],
        "elapsed_time": round(elapsed, 6),
        "global_time":  round(global_time, 6),
        "flip_time":    round(flip_time, 6),
        "event_marker": event_marker,
        "ttl_code":     ttl_code,
    }

    log["rows"].append(row)
    return log


def get_rows(log: FrameLog) -> List[Dict[str, Any]]:
    """Return accumulated rows as a plain list."""
    return list(log["rows"])


class FrameRecorder:
    """Stateful wrapper that removes the per-frame logging boilerplate.

    Every phase used to repeat, inside its flip loop::

        flip_time = win.flip()
        if frame_idx == 0:
            frame_log = set_onset(frame_log, flip_time)
            marker = "stimulus_onset"
        else:
            marker = ""
        frame_log = log_frame(frame_log, frame_idx=frame_idx, flip_time=flip_time,
                              global_time=global_clock.getTime(), event_marker=marker)
        frame_idx += 1

    With a recorder that collapses to ``rec.flip_and_log(win)`` and, after the
    loop, ``rec.log_final(win, result)``. The accumulated log lives on
    ``rec.frame_log``; functions that take/return a FrameLog (e.g. ITI helpers)
    can read and reassign it directly.
    """

    def __init__(self, frame_log: FrameLog, global_clock, photodiode=None) -> None:
        self.frame_log = frame_log
        self.global_clock = global_clock
        self.idx = 0
        self.photodiode = photodiode

    def start_segment(self) -> None:
        """Mark the next ``flip_and_log`` as a new segment's first frame.

        Resets the frame counter to 0 so the next flip re-sets onset. Use when
        one phase presents several independently-timed segments through the same
        log (e.g. Phase 2's sequential option presentation).
        """
        self.idx = 0

    def flip_and_log(
        self,
        win,
        *,
        marker: Optional[str] = None,
        ttl_code: Optional[int] = None,
    ) -> float:
        """Flip the window, log the frame, and return ``flip_time``.

        On the first frame of a segment (``idx == 0``) onset is set. When
        *marker* is None the event marker defaults to ``"stimulus_onset"`` on the
        first frame and ``""`` afterwards; pass *marker* to override (e.g. a
        custom per-segment onset label).
        Pass *ttl_code* on frames where a TTL pulse was sent so the code is
        recorded in the CSV.
        """
        if self.photodiode is not None:
            if self.idx == 0:
                self.photodiode.trigger()
            self.photodiode.draw()
        flip_time = win.flip()
        if self.idx == 0:
            self.frame_log = set_onset(self.frame_log, flip_time)
        if marker is None:
            marker = "stimulus_onset" if self.idx == 0 else ""
        self.frame_log = log_frame(
            self.frame_log,
            frame_idx=self.idx,
            flip_time=flip_time,
            global_time=self.global_clock.getTime(),
            event_marker=marker,
            ttl_code=ttl_code,
        )
        self.idx += 1
        return flip_time

    def log_final(self, win, result) -> FrameLog:
        """Log the closing row after the loop and return the FrameLog.

        The marker is ``"response"`` when a response was collected, else
        ``"timeout"``.

        When a photodiode is attached, triggers it and does one additional
        flip so the sync pulse appears precisely at the response/timeout event.
        The flip_time recorded is that new flip (not win.lastFrameT).
        """
        event_marker = "response" if result["response"] else "timeout"

        if self.photodiode is not None:
            self.photodiode.trigger()
            self.photodiode.draw()
            flip_time = win.flip()
        else:
            flip_time = win.lastFrameT

        self.frame_log = log_frame(
            self.frame_log,
            frame_idx=self.idx,
            flip_time=flip_time,
            global_time=self.global_clock.getTime(),
            event_marker=event_marker,
        )
        return self.frame_log
