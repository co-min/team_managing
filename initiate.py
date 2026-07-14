
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from psychopy import core
from labjack import ljm
from utils.screen_utils import get_subject_info
from function.config.window_factory import create_window
from function.io.path_builder import get_subject_dir

try:
    from eye_func import initiate_eyelink
except ImportError:
    initiate_eyelink = None


@dataclass
class ExperimentContext:
    subject_id:   str
    win:          Any
    global_clock: Any
    el_tracker:   Optional[Any]
    handle:       Any

def initiate() -> ExperimentContext:
    """Run all pre-experiment setup and return initialized state."""
    subject_id = get_subject_info()["subject_id"]


    win = create_window()
    global_clock = core.Clock()

    el_tracker = initiate_eyelink(win, get_subject_dir(subject_id)) if initiate_eyelink else None
    

    #labjack 초기화
    handle = None

    try:
        handle = ljm.openS("T4", "ANY", "ANY")
        print(" LabJack connected")
        info = ljm.getHandleInfo(handle)
        print("Connected:", info)

        names = [
            "EIO_DIRECTION",
            "EIO_STATE",
            "CIO_DIRECTION",
            "CIO_STATE"
        ]

        ljm.eWriteNames(
            handle,
            len(names),
            names,
            [0xFF, 0, 0x0F, 0]
        )

    except Exception as e:
        print(" LabJack not found → running without TTL")
        handle = None

    print("LabJack handle:", handle)
    
    print("Initialization complete.")

    return ExperimentContext(
        subject_id=subject_id,
        win=win,
        global_clock=global_clock,
        el_tracker=el_tracker,
        handle=handle,
    )