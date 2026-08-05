"""
response.py
-----------
Collects keyboard or mouse responses during a phase.
Returns a ResponseResult TypedDict so callers never inspect raw dicts.
"""

from typing import TypedDict, Optional, List, Tuple

from psychopy import visual, event, core


class ResponseResult(TypedDict):
    """Outcome of a single response collection window."""
    response:     Optional[str]    # "yes"/"no"/position label/"1"–"4"
    response_idx: Optional[int]    # 0-based index for multi-choice
    rt:           Optional[float]  # seconds from onset
    timed_out:    bool
    raw_key:      Optional[str]    # the raw key name (for debugging)


def make_response(
    response:     Optional[str]   = None,
    response_idx: Optional[int]   = None,
    rt:           Optional[float] = None,
    timed_out:    bool            = False,
    raw_key:      Optional[str]   = None,
) -> ResponseResult:
    return {
        "response":     response,
        "response_idx": response_idx,
        "rt":           rt,
        "timed_out":    timed_out,
        "raw_key":      raw_key,
    }


def wait_for_key_response(
    valid_keys: List[str],
    quit_key: str = "escape",
    max_wait: Optional[float] = None,
    clock: Optional[core.Clock] = None,
) -> ResponseResult:
    """
    Block until one of *valid_keys* is pressed (or timeout / quit).

    Parameters
    ----------
    valid_keys  : keys that count as a valid response (lowercase)
    quit_key    : key that ends the experiment immediately
    max_wait    : seconds before timeout; None = wait forever
    clock       : a running core.Clock for RT measurement

    Returns
    -------
    ResponseResult
    """
    if clock is None:
        clock = core.Clock()

    event.clearEvents()
    deadline = (clock.getTime() + max_wait) if max_wait else None

    while True:
        keys = event.getKeys(timeStamped=clock)
        for key, t in keys:
            if key == quit_key:
                core.quit()
            if key in valid_keys:
                return make_response(response=key, rt=t, raw_key=key)
        if deadline and clock.getTime() >= deadline:
            return make_response(timed_out=True)
        core.wait(0.001, hogCPUperiod=0.001)


def wait_for_mouse_click(
    clickable_regions: List[Tuple[visual.BaseVisualStim, str]],
    mouse: event.Mouse,
    mouse_button: int = 0,
    quit_key: str = "escape",
    max_wait: Optional[float] = None,
    clock: Optional[core.Clock] = None,
) -> ResponseResult:
    """
    Block until the mouse clicks inside one of *clickable_regions*.

    Parameters
    ----------
    clickable_regions : list of (stim, label) where label is the response string
    mouse             : PsychoPy Mouse object
    mouse_button      : which button to watch (0 = left)
    quit_key          : keyboard key to abort experiment
    max_wait          : seconds before timeout
    clock             : running Clock for RT

    Returns
    -------
    ResponseResult
    """
    if clock is None:
        clock = core.Clock()

    mouse.clickReset()
    deadline = (clock.getTime() + max_wait) if max_wait else None

    while True:
        keys = event.getKeys()
        if quit_key in keys:
            core.quit()

        if mouse.getPressed()[mouse_button]:
            for idx, (region, label) in enumerate(clickable_regions):
                if mouse.isPressedIn(region, buttons=[mouse_button]):
                    rt = clock.getTime()
                    while mouse.getPressed()[mouse_button]:
                        core.wait(0.001)
                    return make_response(response=label, response_idx=idx, rt=rt)

        if deadline and clock.getTime() >= deadline:
            return make_response(timed_out=True)

        core.wait(0.001, hogCPUperiod=0.001)


def wait_for_mouse_release(mouse: event.Mouse, button: int = 0) -> None:
    """Block until the given mouse button is released (debounce helper)."""
    while mouse.getPressed()[button]:
        core.wait(0.001)


def confirm_click(
    win: visual.Window,
    mouse: event.Mouse,
    button: int = 0,
    redraw_fn=None,
    hold: float = 0.2,
) -> None:
    """Show the selected state briefly, then debounce the mouse release.

    Phases 0/1/2 all repeated the same post-click sequence: redraw the screen
    with the selection highlighted, flip, pause so the participant sees the
    feedback, then wait for the button to come back up before returning a
    response. This bundles that.

    Parameters
    ----------
    win       : PsychoPy Window
    mouse     : PsychoPy Mouse object
    button    : which button to wait for release on (0 = left)
    redraw_fn : optional zero-arg callback that draws the highlighted screen;
                when given it is drawn and flipped once before the pause
    hold      : seconds to display the selection before debouncing
    """
    if redraw_fn is not None:
        redraw_fn()
        win.flip()
    core.wait(hold)
    wait_for_mouse_release(mouse, button)
