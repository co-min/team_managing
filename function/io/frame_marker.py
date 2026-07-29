"""
frame_marker.py
---------------
Photodiode sync marker: white square drawn in the bottom-left corner.

Usage
-----
    marker = FrameMarker(win, size=(50, 50), n_frames=2)

    # In the flip loop (before win.flip()):
    marker.trigger()   # activate for n_frames (call once per event)
    marker.draw()      # call every frame — white when active, invisible otherwise

    # Typically used via FrameRecorder(frame_log, global_clock, photodiode=marker)
    # which handles trigger/draw automatically at onset and response/timeout.
"""

from psychopy import visual


class FrameMarker:
    """Small white square in the bottom-left corner for photodiode sync.

    Call trigger() at an event, then draw() before every win.flip().
    The square is white for n_frames, then invisible until the next trigger().
    """

    def __init__(
        self,
        win: visual.Window,
        size: tuple = (50, 50),
        n_frames: int = 2,
    ):
        self._n_frames = n_frames
        self._remaining = 0

        W, H = win.size
        # bottom-left corner, inset by half the marker size so it's fully on screen
        pos = (-W // 2 + size[0] // 2, -H // 2 + size[1] // 2)

        self._rect = visual.Rect(
            win,
            width=size[0], height=size[1],
            fillColor='white', lineColor='white',
            pos=pos, units='pix',
        )

    def trigger(self, n_frames: int = None) -> None:
        """Activate the marker for the next n_frames flips."""
        self._remaining = n_frames if n_frames is not None else self._n_frames

    def draw(self) -> None:
        """Draw white square if active, nothing otherwise. Call before win.flip()."""
        if self._remaining > 0:
            self._rect.draw()
            self._remaining -= 1


# ── Shared singleton ──────────────────────────────────────────────────────────
_shared_marker: 'FrameMarker | None' = None


def init_marker(win: 'visual.Window', size: tuple = (50, 50), n_frames: int = 2) -> FrameMarker:
    """Create and store the one shared FrameMarker. Call once in main() after win is created."""
    global _shared_marker
    _shared_marker = FrameMarker(win, size=size, n_frames=n_frames)
    return _shared_marker


def get_shared_marker() -> 'FrameMarker | None':
    """Return the shared FrameMarker, or None if init_marker() was never called."""
    return _shared_marker
