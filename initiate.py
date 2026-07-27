
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from psychopy import core
from labjack import ljm
from utils.screen_utils import get_subject_info
from function.config.window_factory import create_window
from function.config.settings import (
    USE_NEON,
    NEON_DISCOVERY_TIMEOUT_S,
    NEON_RETRY_INTERVAL_S,
    NEON_APRILTAG_POSITIONS,
    NEON_APRILTAG_SIZE,
)
from function.io.path_builder import get_subject_dir
from utils.neon_client import NeonEventClient, NullNeonClient, create_neon_apriltags

try:
    from eye_func import initiate_eyelink
except ImportError:
    initiate_eyelink = None


@dataclass
class ExperimentContext:
    subject_id:        str
    session_id:        str
    win:               Any
    global_clock:      Any
    el_tracker:        Optional[Any]
    handle:            Any
    neon_client:       Any              # NeonEventClient | NullNeonClient
    neon_recording_id: Optional[str]
    apriltags:         List = field(default_factory=list)


def initiate() -> ExperimentContext:
    """Run all pre-experiment setup and return initialized state."""
    info       = get_subject_info()
    subject_id = info["subject_id"]
    session_id = datetime.now().strftime("%Y%m%dT%H%M%S")

    win          = create_window()
    global_clock = core.Clock()

    el_tracker = initiate_eyelink(win, get_subject_dir(subject_id)) if initiate_eyelink else None

    # ── LabJack ───────────────────────────────────────────────────────────────
    handle = None
    try:
        handle = ljm.openS("T4", "ANY", "ANY")
        print(" LabJack connected")
        print("Connected:", ljm.getHandleInfo(handle))
        ljm.eWriteNames(
            handle, 4,
            ["EIO_DIRECTION", "EIO_STATE", "CIO_DIRECTION", "CIO_STATE"],
            [0xFF, 0, 0x0F, 0],
        )
    except Exception as e:
        print(f" LabJack not found → running without TTL ({e})")
        handle = None
    print("LabJack handle:", handle)

    # ── Neon eyetracker ───────────────────────────────────────────────────────
    apriltags         = []
    neon_recording_id = None

    if USE_NEON:
        apriltags   = create_neon_apriltags(win, NEON_APRILTAG_POSITIONS, NEON_APRILTAG_SIZE)
        neon_client = NeonEventClient(
            subject_id=subject_id,
            session_id=session_id,
            discovery_timeout_s=NEON_DISCOVERY_TIMEOUT_S,
            retry_interval_s=NEON_RETRY_INTERVAL_S,
        )
        neon_recording_id = neon_client.start_session()
    else:
        neon_client = NullNeonClient()

    print("Initialization complete.")

    return ExperimentContext(
        subject_id=subject_id,
        session_id=session_id,
        win=win,
        global_clock=global_clock,
        el_tracker=el_tracker,
        handle=handle,
        neon_client=neon_client,
        neon_recording_id=neon_recording_id,
        apriltags=apriltags,
    )