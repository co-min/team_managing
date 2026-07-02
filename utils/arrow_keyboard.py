"""
arrow_keyboard.py
-----------------
4-direction arrow display with keyboard response collection.
Arrows highlight when the corresponding arrow key is pressed.
"""

from typing import Optional, List, Tuple

from psychopy import visual, event, core

import function.config.settings as cfg
from function.config.key_mapping import QUIT_KEY
from utils.response import ResponseResult, make_response


# (offset_x, offset_y, orientation)  — index order: up, down, right, left
_ARROW_DEFS: List[Tuple[int, int, int]] = [
    (0,                  cfg.ARROW_OFFSET,  0  ),  # 0: up
    (0,                 -cfg.ARROW_OFFSET,  180),  # 1: down
    (cfg.ARROW_OFFSET,   0,                 90 ),  # 2: right
    (-cfg.ARROW_OFFSET,  0,                 270),  # 3: left
]

_KEY_TO_IDX: dict = {
    'up':    0,
    'down':  1,
    'right': 2,
    'left':  3,
}

_COLOR_IDLE      = '#0055ff'
_COLOR_SELECTED  = "#515253"  # lighter blue when previewing
_COLOR_CONFIRMED = '#ff8800'  # orange when confirmed by space bar


class ArrowKeyboard:
    """4-directional arrow stimuli + keyboard response collector.

    Usage
    -----
    kb = ArrowKeyboard(win)
    kb.draw()          # call each frame while waiting
    result = kb.collect(win, clock)

    result keys
    -----------
    response      : 'up' | 'down' | 'right' | 'left' | None (timeout)
    response_idx  : 0–3 matching _ARROW_DEFS order, or None
    rt            : float seconds from clock reset
    timed_out     : bool
    raw_key       : same as response (for debugging consistency)
    """

    def __init__(self, win: visual.Window, pos: Tuple[float, float] = (0, 0)):
        ox, oy = pos
        self.arrows: List[visual.Polygon] = [
            visual.Polygon(
                win,
                edges=3,
                radius=cfg.ARROW_RADIUS,
                pos=(ox + dx, oy + dy),
                ori=ori,
                fillColor=_COLOR_IDLE,
                lineColor=None,
            )
            for dx, dy, ori in _ARROW_DEFS
        ]
        self._confirmed_idx: Optional[int] = None

    @property
    def valid_keys(self) -> List[str]:
        return list(_KEY_TO_IDX.keys())

    def draw(self) -> None:
        for arrow in self.arrows:
            arrow.draw()

    def reset_colors(self) -> None:
        for i, arrow in enumerate(self.arrows):
            arrow.fillColor = _COLOR_CONFIRMED if i == self._confirmed_idx else _COLOR_IDLE

    def select(self, key: str, excluded_idx: Optional[int] = None) -> Optional[int]:
        """Highlight the arrow for *key* and return its index.

        Returns None if the key is not an arrow key or matches excluded_idx.
        """
        idx = _KEY_TO_IDX.get(key)
        if idx is None or idx == excluded_idx:
            return None
        self.arrows[idx].fillColor = _COLOR_SELECTED
        return idx

    def set_excluded(self, excluded_idx: int) -> None:
        """Mark the confirmed Choice 1 arrow orange and persist it through reset_colors()."""
        self._confirmed_idx = excluded_idx
        self.arrows[excluded_idx].fillColor = _COLOR_CONFIRMED

    def collect(
        self,
        win: visual.Window,
        clock: Optional[core.Clock] = None,
        max_wait: Optional[float] = None,
        highlight_dur: float = 0.15,
    ) -> ResponseResult:
        """Wait for an arrow key, highlight the selection, then return result.

        Parameters
        ----------
        win           : PsychoPy Window
        clock         : running Clock for RT; created fresh if None
        max_wait      : timeout seconds; defaults to cfg.MAX_RESPONSE_TIME
        highlight_dur : seconds to show the selected arrow highlighted

        Returns
        -------
        ResponseResult (see utils/response.py)
        """
        if clock is None:
            clock = core.Clock()
        if max_wait is None:
            max_wait = cfg.MAX_RESPONSE_TIME

        self.reset_colors()
        event.clearEvents()
        deadline = clock.getTime() + max_wait

        while True:
            keys = event.getKeys(
                keyList=list(_KEY_TO_IDX.keys()) + [QUIT_KEY],
                timeStamped=clock,
            )

            for key, t in keys:
                if key == QUIT_KEY:
                    win.close()
                    core.quit()

                if key in _KEY_TO_IDX:
                    idx = _KEY_TO_IDX[key]
                    self.arrows[idx].fillColor = _COLOR_SELECTED
                    self.draw()
                    win.flip()
                    core.wait(highlight_dur)
                    return make_response(
                        response=key,
                        response_idx=idx,
                        rt=t,
                        raw_key=key,
                    )

            if clock.getTime() >= deadline:
                return make_response(timed_out=True)

            core.wait(0.001, hogCPUperiod=0.001)
