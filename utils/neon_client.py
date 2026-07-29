"""
neon_client.py
--------------
Pupil Labs Neon eyetracker integration.

Public API
----------
    NeonEventClient   — connects to Neon Companion and sends timestamped events
    NullNeonClient    — no-op drop-in used when USE_NEON=False
    section_start_events(trial_index, segment_label, first=False)
    section_end_events(trial_index, outcome)
    create_neon_apriltags(win, positions, size)
    save_neon_event_log(save_dir, event_log)

Design notes
------------
* Events are timestamped at callOnFlip / enqueue time, then transmitted by a
  background daemon thread so network I/O never blocks the PsychoPy flip loop.
* NullNeonClient has the same interface; callers need no USE_NEON branches.
* The event log records every queue insertion AND every send attempt so that
  cloud delivery can be audited offline via neon_event_log.xlsx.
"""

import queue
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

try:
    from pupil_labs.realtime_api.simple import discover_one_device as _discover_one
    _PUPIL_AVAILABLE = True
except ImportError:
    _PUPIL_AVAILABLE = False

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

try:
    import pandas as _pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


# ─── Log schema ──────────────────────────────────────────────────────────────

LOG_COLUMNS: Tuple[str, ...] = (
    "event_sequence",
    "session_id",
    "subject_id",
    "recording_id",
    "task_type",
    "phase",
    "trial_index",
    "attempt_index",
    "event_name",
    "host_timestamp_unix_ns",
    "companion_timestamp_unix_ns",
    "clock_offset_ns",
    "send_attempt",
    "send_success",
    "retried",
    "send_error",
)

_EVENT_PATH = "/api/event"
_TIME_PATH  = "/api/time"
_DEFAULT_PORT = 8080


# ─── Internal queue item ─────────────────────────────────────────────────────

class _QueueItem:
    __slots__ = ("seq", "name", "ts_ns", "session_id", "subject_id", "recording_id", "meta")

    def __init__(
        self,
        seq: int,
        name: str,
        ts_ns: int,
        session_id: str,
        subject_id: str,
        recording_id: Optional[str],
        meta: Dict,
    ):
        self.seq          = seq
        self.name         = name
        self.ts_ns        = ts_ns
        self.session_id   = session_id
        self.subject_id   = subject_id
        self.recording_id = recording_id
        self.meta         = meta


# ─── Real client ─────────────────────────────────────────────────────────────

class NeonEventClient:
    """
    Thread-safe client for the Neon Companion REST API.

    Event transmission runs on a background daemon thread so that network I/O
    never delays win.flip(). Timestamps are captured at the moment events are
    enqueued (typically inside a callOnFlip callback) so they reflect actual
    screen timing regardless of transmission latency.
    """

    def __init__(
        self,
        subject_id: str,
        session_id: str,
        discovery_timeout_s: float = 10.0,
        retry_interval_s: float = 1.0,
        max_retries: int = 3,
    ):
        if not _PUPIL_AVAILABLE:
            raise RuntimeError(
                "pupil-labs-realtime-api not installed. "
                "Run: pip install pupil-labs-realtime-api"
            )
        if not _REQUESTS_AVAILABLE:
            raise RuntimeError(
                "requests not installed. Run: pip install requests"
            )

        self.subject_id:   str            = subject_id
        self.session_id:   str            = session_id
        self.recording_id: Optional[str]  = None
        self.event_log:    List[Dict]     = []

        self._retry_interval_s = retry_interval_s
        self._max_retries      = max_retries
        self._clock_offset_ns: int = 0
        self._seq              = 0
        self._seq_lock         = threading.Lock()
        self._q: queue.Queue   = queue.Queue()

        self._device   = self._discover(discovery_timeout_s)
        self._base_url = (
            f"http://{self._device.address}"
            f":{getattr(self._device, 'port', _DEFAULT_PORT)}"
        )

        self._worker = threading.Thread(
            target=self._send_loop, daemon=True, name="NeonWorker"
        )
        self._worker.start()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _discover(self, timeout_s: float):
        print(f"[Neon] Searching for Companion device ({timeout_s:.0f}s)…")
        device = _discover_one(max_search_duration_seconds=timeout_s)
        if device is None:
            raise RuntimeError(
                "[Neon] No Companion device found. "
                "Ensure the Neon app is open and on the same Wi-Fi network."
            )
        print(f"[Neon] Found: {device.phone_name} @ {device.address}")
        return device

    def start_session(self) -> str:
        """
        Estimate clock offset, verify active recording, send SESSION_START.

        Must be called after win is created but before the first trial.
        Raises RuntimeError if no active recording is found on the Companion.
        Returns the recording_id string.
        """
        self._estimate_clock_offset()
        recording_id = self._device.recording_id
        if recording_id is None:
            raise RuntimeError(
                "[Neon] No active recording found. "
                "Start a recording in the Companion app before running the experiment."
            )
        self.recording_id = str(recording_id)
        print(f"[Neon] Recording ID: {self.recording_id}")
        self.enqueue_events(
            f"SESSION_START_{self.subject_id}_{self.session_id}",
            metadata={"task_type": "session"},
        )
        return self.recording_id

    def _estimate_clock_offset(self, n_samples: int = 5) -> None:
        offsets = []
        for _ in range(n_samples):
            t_before = time.time_ns()
            try:
                resp = _requests.get(f"{self._base_url}{_TIME_PATH}", timeout=1.0)
                t_after = time.time_ns()
                companion_ns = int(resp.json().get("timestamp", 0) * 1_000_000_000)
                offsets.append(companion_ns - (t_before + (t_after - t_before) // 2))
            except Exception:
                pass
        self._clock_offset_ns = int(sum(offsets) / len(offsets)) if offsets else 0
        print(
            f"[Neon] Clock offset: {self._clock_offset_ns / 1e6:.2f} ms "
            f"({len(offsets)}/{n_samples} samples)"
        )

    # ── Event API ────────────────────────────────────────────────────────────

    def call_on_flip(
        self,
        win,
        event_names: Union[str, Sequence[str]],
        **metadata,
    ) -> None:
        """Register events to be enqueued at the next win.flip().

        Timestamps are captured inside the callOnFlip callback, as close as
        possible to the actual screen update.
        """
        win.callOnFlip(self.enqueue_events, event_names, metadata=metadata)

    def enqueue_events(
        self,
        event_names: Union[str, Sequence[str]],
        metadata: Optional[Dict] = None,
    ) -> None:
        """Timestamp and enqueue one or more event names for transmission."""
        ts_ns = time.time_ns()
        names = (event_names,) if isinstance(event_names, str) else tuple(event_names)
        meta  = metadata or {}
        for name in names:
            with self._seq_lock:
                seq = self._seq
                self._seq += 1
            item = _QueueItem(
                seq=seq, name=name, ts_ns=ts_ns,
                session_id=self.session_id, subject_id=self.subject_id,
                recording_id=self.recording_id, meta=meta,
            )
            self._append_log(item, send_attempt=0, success=False, error="Queued")
            self._q.put(item)

    # ── Background worker ────────────────────────────────────────────────────

    def _send_loop(self) -> None:
        while True:
            item = self._q.get()
            if item is None:           # shutdown sentinel
                break
            self._transmit(item)
            self._q.task_done()

    def _transmit(self, item: _QueueItem) -> None:
        companion_ns = item.ts_ns + self._clock_offset_ns
        retried = False
        for attempt in range(1, self._max_retries + 1):
            try:
                _requests.post(
                    f"{self._base_url}{_EVENT_PATH}",
                    json={"name": item.name, "timestamp": companion_ns},
                    timeout=2.0,
                ).raise_for_status()
                self._append_log(item, attempt, True, "", companion_ns, retried)
                return
            except Exception as exc:
                retried = attempt > 1
                if attempt < self._max_retries:
                    time.sleep(self._retry_interval_s)
                else:
                    self._append_log(item, attempt, False, str(exc), companion_ns, retried)

    def _append_log(
        self,
        item: _QueueItem,
        send_attempt: int,
        success: bool,
        error: str,
        companion_ns: Optional[int] = None,
        retried: bool = False,
    ) -> None:
        self.event_log.append({
            "event_sequence":              item.seq,
            "session_id":                  item.session_id,
            "subject_id":                  item.subject_id,
            "recording_id":                item.recording_id,
            "task_type":                   item.meta.get("task_type"),
            "phase":                       item.meta.get("phase"),
            "trial_index":                 item.meta.get("trial_index"),
            "attempt_index":               item.meta.get("attempt_index"),
            "event_name":                  item.name,
            "host_timestamp_unix_ns":      item.ts_ns,
            "companion_timestamp_unix_ns": companion_ns,
            "clock_offset_ns":             self._clock_offset_ns,
            "send_attempt":                send_attempt,
            "send_success":                success,
            "retried":                     retried,
            "send_error":                  error,
        })

    # ── Shutdown ─────────────────────────────────────────────────────────────

    def close(self, flush_timeout_s: float = 5.0) -> bool:
        """Send SESSION_END, drain the queue, and stop the worker thread.

        Returns True if all events were flushed within *flush_timeout_s*.
        Call this in a finally block so it also runs on abort.
        """
        self.enqueue_events("SESSION_END", metadata={"task_type": "session"})
        try:
            self._q.join()
            flushed = True
        except Exception:
            flushed = False
        self._q.put(None)
        self._worker.join(timeout=flush_timeout_s)
        return flushed


# ─── Null client (USE_NEON=False) ────────────────────────────────────────────

class NullNeonClient:
    """Drop-in replacement used when USE_NEON=False — every method is a no-op."""

    def __init__(self, *args, **kwargs):
        self.subject_id:   str           = ""
        self.session_id:   str           = ""
        self.recording_id: Optional[str] = None
        self.event_log:    List[Dict]    = []

    def start_session(self) -> Optional[str]:
        return None

    def call_on_flip(self, win, event_names, **metadata) -> None:
        pass

    def enqueue_events(self, event_names, metadata=None) -> None:
        pass

    def close(self, flush_timeout_s: float = 5.0) -> bool:
        return True


# ─── Section event name helpers ───────────────────────────────────────────────

def section_start_events(
    trial_index: int,
    segment_label: str,
    first: bool = False,
) -> Tuple[str, ...]:
    """Return event names to open a new trial section.

    When *first* is False, prepends TRIAL_SECTION_END to close the previous
    section at the same flip timestamp.

    Example
    -------
    section_start_events(1, "CHOICE1", first=True)
        → ("TRIAL_SECTION_START", "TRIAL_001_CHOICE1")

    section_start_events(1, "CHOICE2")
        → ("TRIAL_SECTION_END", "TRIAL_SECTION_START", "TRIAL_001_CHOICE2")
    """
    prefix = () if first else ("TRIAL_SECTION_END",)
    return prefix + ("TRIAL_SECTION_START", f"TRIAL_{trial_index:03d}_{segment_label.upper()}")


def section_end_events(trial_index: int, outcome: str) -> Tuple[str, ...]:
    """Return event names to close the current trial section.

    Example
    -------
    section_end_events(1, "CHOICE1_RESPONSE")
        → ("TRIAL_001_CHOICE1_RESPONSE", "TRIAL_SECTION_END")
    """
    return (f"TRIAL_{trial_index:03d}_{outcome.upper()}", "TRIAL_SECTION_END")


# ─── AprilTag factory ─────────────────────────────────────────────────────────

def create_neon_apriltags(win, positions: Sequence, size: float = 0.10) -> List:
    """Create AprilTagStim markers at screen edges and keep them visible (AutoDraw).

    Parameters
    ----------
    win       : psychopy.visual.Window
    positions : sequence of (x, y) tuples in 'height' units
    size      : marker size in 'height' units

    Returns
    -------
    List of AprilTagStim instances. The caller must keep a reference so that
    Python does not garbage-collect them while the window is open.

    Raises RuntimeError if psychopy-eyetracker-pupil-labs is not installed.
    """
    try:
        from psychopy_eyetracker_pupil_labs.pupil_labs.stimuli import AprilTagStim
    except ImportError:
        raise RuntimeError(
            "psychopy-eyetracker-pupil-labs not installed. "
            "Run: pip install psychopy-eyetracker-pupil-labs"
        )
    tags = [
        AprilTagStim(
            win=win,
            marker_id=i,
            units="height",
            pos=pos,
            size=(size, size),
            interpolate=False,
            autoLog=False,
        )
        for i, pos in enumerate(positions)
    ]
    for tag in tags:
        tag.setAutoDraw(True)
    print(f"[Neon] {len(tags)} AprilTag markers created and set to AutoDraw.")
    return tags


# ─── Event log saver ─────────────────────────────────────────────────────────

def save_neon_event_log(save_dir: Union[str, Path], event_log: List[Dict]) -> Optional[str]:
    """Write neon_event_log.xlsx to *save_dir*.

    Returns the absolute path string, or None if saving failed.
    Safe to call from finally blocks — will not raise.
    """
    if not _PANDAS_AVAILABLE:
        print("[Neon] pandas not installed — event log not saved.")
        return None
    try:
        path = Path(save_dir) / "neon_event_log.xlsx"
        _pd.DataFrame(event_log, columns=list(LOG_COLUMNS)).to_excel(
            str(path), index=False
        )
        print(f"[Neon] Event log saved → {path}")
        return str(path)
    except Exception as exc:
        print(f"[Neon] Failed to save event log: {exc}")
        return None