# function/phases/ending.py
"""
Ending screen — leaderboard ranked by perfect-score rate.

accuracy = (number of trials where feedback_score == max_trial_score) / responded_trials
"""

import csv
from pathlib import Path

from psychopy import event, visual

from function.config.settings import DATA_DIR, FONT, SCORE_CSV
from utils.event_utils import check_escape

# ── layout ───────────────────────────────────────────────────────────────────

_GOLD   = "#FFD700"
_SILVER = "#C0C0C0"
_BRONZE = "#CD7F32"
_BLUE   = "#4FC3F7"
_GREEN  = "#4CAF50"
_GRAY   = "#AAAAAA"

_RANK_COLORS = [_GOLD, _SILVER, _BRONZE, _BLUE]
_RANK_LABELS = ["1st", "2nd", "3rd", "4th"]


def _compute_layout(win: visual.Window) -> dict:
    """Derive sizes/margins from win.size so nothing overlaps regardless of resolution."""
    W, H = win.size

    row_w   = min(720, int(W * 0.6))
    row_h   = max(56, int(H * 0.062))
    row_gap = max(14, int(H * 0.018))       # gap between rows
    gap_sm  = max(10, int(H * 0.012))       # gap within a section (title <-> subtitle)
    gap_lg  = max(24, int(H * 0.030))       # gap between sections (header / table / summary)

    return dict(
        row_w=row_w, row_h=row_h, row_gap=row_gap, gap_sm=gap_sm, gap_lg=gap_lg,
        title_h=max(50, int(H * 0.058)),
        subtitle_h=max(34, int(H * 0.038)),
        header_h=max(28, int(H * 0.032)),
        ellipsis_h=max(24, int(H * 0.026)),
        summary_h=max(28, int(H * 0.032)),
        footer_h=max(26, int(H * 0.028)),
        label_x=-row_w * 0.36,
        score_x=row_w * 0.33,
    )


class _Stacker:
    """Places elements top-to-bottom, each separated by an explicit gap, then
    re-centers the whole stack vertically around y=0 so it never overlaps or
    runs off-screen regardless of how many rows are shown."""

    def __init__(self):
        self._items: list[tuple[float, float]] = []  # (gap_before, height)

    def add(self, height: float, gap_before: float = 0.0) -> int:
        self._items.append((gap_before, height))
        return len(self._items) - 1

    def resolve(self) -> list[float]:
        total = sum(gap + h for gap, h in self._items)
        cursor = total / 2
        ys = []
        for gap, h in self._items:
            cursor -= gap + h / 2
            ys.append(cursor)
            cursor -= h / 2
        return ys


# ── score helpers ─────────────────────────────────────────────────────────────

def _max_trial_score(score_csv: Path) -> float:
    """Max possible feedback_score for a single trial across all domains."""
    best = 0.0
    try:
        with open(score_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, skipinitialspace=True):
                for k, v in row.items():
                    if k.startswith("sc_"):
                        try:
                            best = max(best, float(v))
                        except ValueError:
                            pass
    except Exception:
        return 60.0
    return best if best > 0 else 60.0


def _accuracy_from_csv(trials_csv: Path, max_score: float) -> float | None:
    """Ratio of perfect-score trials to responded trials. None if file missing."""
    if not trials_csv.exists():
        return None
    perfect = responded = 0
    try:
        with open(trials_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("response_made") in ("True", "1"):
                    responded += 1
                    try:
                        if float(row.get("feedback_score", 0)) >= max_score:
                            perfect += 1
                    except ValueError:
                        pass
    except Exception:
        return None
    return (perfect / responded) if responded > 0 else 0.0


def _load_all_accuracies(data_dir: Path, max_score: float) -> list[dict]:
    entries = []
    for sub_dir in sorted(data_dir.glob("sub-*")):
        acc = _accuracy_from_csv(sub_dir / "trials.csv", max_score)
        if acc is not None:
            entries.append({"subject_id": sub_dir.name.replace("sub-", ""), "accuracy": acc})
    return entries


def _rank_of(my_acc: float, entries: list[dict]) -> tuple[int, int]:
    """(1-indexed rank, total count). Rank 1 = highest accuracy."""
    rank = sum(1 for e in entries if e["accuracy"] > my_acc) + 1
    return rank, len(entries)


# ── stim builders ─────────────────────────────────────────────────────────────

def _row_stims(
    win: visual.Window,
    L: dict,
    rank_label: str,
    subject_id: str,
    accuracy: float,
    y: float,
    color: str,
    is_me: bool,
) -> list:
    me_tag   = "  <- You" if is_me else ""
    bg_color = "#2d3050" if is_me else "#1e1e1e"
    line_w   = 2 if is_me else 0
    label_text = f"{rank_label}   Sub-{subject_id}{me_tag}"

    stims = [
        visual.Rect(win, width=L["row_w"], height=L["row_h"], pos=(0, y),
                    fillColor=bg_color,
                    lineColor=color if is_me else None,
                    lineWidth=line_w),
        visual.TextStim(win,
                        text=label_text,
                        pos=(L["label_x"], y),
                        color=color if is_me else "white",
                        height=L["row_h"] * 0.5, bold=is_me, font=FONT,
                        anchorHoriz="left",
                        # keep long ids/tags from bleeding into the score column
                        wrapWidth=L["score_x"] - L["label_x"] - L["row_w"] * 0.04),
        visual.TextStim(win,
                        text=f"{accuracy * 100:.1f}%",
                        pos=(L["score_x"], y),
                        color=color, height=L["row_h"] * 0.5, bold=True, font=FONT,
                        anchorHoriz="right"),
    ]
    return stims


# ── public entry point ────────────────────────────────────────────────────────

def run_ending(win: visual.Window, subject_id: str, cumulative_score: float) -> None:
    """Show top-4 leaderboard by accuracy and highlight current subject's rank."""
    max_score = _max_trial_score(Path(SCORE_CSV))
    entries   = _load_all_accuracies(DATA_DIR, max_score)

    # Ensure current subject uses the freshest in-memory-derived accuracy
    my_acc = _accuracy_from_csv(
        DATA_DIR / f"sub-{subject_id}" / "trials.csv", max_score
    ) or 0.0

    for e in entries:
        if e["subject_id"] == subject_id:
            e["accuracy"] = my_acc
            break
    else:
        entries.append({"subject_id": subject_id, "accuracy": my_acc})

    sorted_entries = sorted(entries, key=lambda x: x["accuracy"], reverse=True)
    my_rank, total = _rank_of(my_acc, entries)
    top_entries    = sorted_entries[:4]
    show_extra_row = my_rank > 4

    L = _compute_layout(win)

    # ── stack every element top-to-bottom so nothing can overlap ────────────
    stack = _Stacker()
    title_i    = stack.add(L["title_h"])
    subtitle_i = stack.add(L["subtitle_h"], L["gap_sm"])
    header_i   = stack.add(L["header_h"], L["gap_sm"])

    row_idx = []
    for i in range(len(top_entries)):
        gap = L["gap_lg"] if i == 0 else L["row_gap"]
        row_idx.append(stack.add(L["row_h"], gap))

    if show_extra_row:
        ellipsis_i = stack.add(L["ellipsis_h"], L["row_gap"])
        extra_i    = stack.add(L["row_h"], L["row_gap"])

    summary_i = stack.add(L["summary_h"], L["gap_lg"])
    footer_i  = stack.add(L["footer_h"], L["gap_sm"])

    ys = stack.resolve()

    # ── build stims ───────────────────────────────────────────────────────────
    stims: list = [
        visual.TextStim(win, text="The experiment is over!",
                        pos=(0, ys[title_i]), color=_GOLD,
                        height=L["title_h"] * 0.75, bold=True, font=FONT),
        visual.TextStim(win, text="Thank you for your participation.",
                        pos=(0, ys[subtitle_i]), color="white",
                        height=L["subtitle_h"] * 0.72, font=FONT),
        visual.TextStim(win, text="Leaderboard  (by accuracy)",
                        pos=(0, ys[header_i]), color=_GRAY,
                        height=L["header_h"] * 0.75, font=FONT),
    ]

    for i, entry in enumerate(top_entries):
        color = _RANK_COLORS[i]
        is_me = entry["subject_id"] == subject_id
        stims += _row_stims(win, L, _RANK_LABELS[i], entry["subject_id"],
                            entry["accuracy"], ys[row_idx[i]], color, is_me)

    # If current subject is outside top-4, show them separately below
    if show_extra_row:
        stims.append(
            visual.TextStim(win, text="...", pos=(0, ys[ellipsis_i]),
                            color=_GRAY, height=L["ellipsis_h"] * 0.8, font=FONT)
        )
        stims += _row_stims(win, L, f"{my_rank}th", subject_id,
                            my_acc, ys[extra_i], _GREEN, is_me=True)

    # Personal summary line
    stims += [
        visual.TextStim(
            win,
            text=f"My total score: {int(cumulative_score)} pts     |     Accuracy: {my_acc * 100:.1f}%     |     Rank {my_rank} of {total}",
            pos=(0, ys[summary_i]),
            color=_GRAY, height=L["summary_h"] * 0.72, font=FONT,
        ),
        visual.TextStim(win, text="Press [Space] to exit",
                        pos=(0, ys[footer_i]), color=_GRAY,
                        height=L["footer_h"] * 0.7, font=FONT),
    ]

    event.clearEvents()
    while True:
        for stim in stims:
            stim.draw()
        win.flip()
        check_escape(win)
        if event.getKeys(keyList=["space"]):
            break
    event.clearEvents()
# function/phases/ending.py
"""
Ending screen — leaderboard ranked by perfect-score rate.

정답률 = (feedback_score == max_trial_score 인 trial 수) / responded_trials
"""

import csv
from pathlib import Path

from psychopy import event, visual

from function.config.settings import DATA_DIR, FONT, SCORE_CSV
from utils.event_utils import check_escape

# ── colours ───────────────────────────────────────────────────────────────────

_GOLD   = "#FFD700"
_SILVER = "#C0C0C0"
_BRONZE = "#CD7F32"
_BLUE   = "#4FC3F7"
_GREEN  = "#4CAF50"
_GRAY   = "#AAAAAA"
_WHITE  = "#FFFFFF"

_RANK_COLORS = [_GOLD, _SILVER, _BRONZE, _BLUE]
_RANK_LABELS = ["1위", "2위", "3위", "4위"]

# ── layout ───────────────────────────────────────────────────────────────────

_ROW_W     = 1000
_ROW_H     = 62
_ROW_STEP  = 80      # vertical gap between rows
_ROW_TOP_Y = 145     # y of rank-1 row
_LABEL_X   = -450
_SCORE_X   = 420

_TITLE_Y    = 390
_SUBTITLE_Y = 290
_HEADER_Y   = 230


# ── score helpers ─────────────────────────────────────────────────────────────

def _max_trial_score(score_csv: Path) -> float:
    """Max possible feedback_score for a single trial across all domains."""
    best = 0.0
    try:
        with open(score_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, skipinitialspace=True):
                for k, v in row.items():
                    if k.startswith("sc_"):
                        try:
                            best = max(best, float(v))
                        except ValueError:
                            pass
    except Exception:
        return 60.0
    return best if best > 0 else 60.0


def _accuracy_from_csv(trials_csv: Path, max_score: float) -> float | None:
    """Ratio of perfect-score trials to responded trials. None if file missing."""
    if not trials_csv.exists():
        return None
    perfect = responded = 0
    try:
        with open(trials_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("response_made") in ("True", "1"):
                    responded += 1
                    try:
                        if float(row.get("feedback_score", 0)) >= max_score:
                            perfect += 1
                    except ValueError:
                        pass
    except Exception:
        return None
    return (perfect / responded) if responded > 0 else 0.0


def _load_all_accuracies(data_dir: Path, max_score: float) -> list[dict]:
    entries = []
    for sub_dir in sorted(data_dir.glob("sub-*")):
        acc = _accuracy_from_csv(sub_dir / "trials.csv", max_score)
        if acc is not None:
            entries.append({"subject_id": sub_dir.name.replace("sub-", ""), "accuracy": acc})
    return entries


def _rank_of(my_acc: float, entries: list[dict]) -> tuple[int, int]:
    """(1-indexed rank, total count). Rank 1 = highest accuracy."""
    rank = sum(1 for e in entries if e["accuracy"] > my_acc) + 1
    return rank, len(entries)


def _fmt_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60}분 {total % 60:02d}초"


# ── stim builders ─────────────────────────────────────────────────────────────

def _row_stims(
    win: visual.Window,
    rank_label: str,
    subject_id: str,
    accuracy: float,
    y: float,
    color: str,
    is_me: bool,
) -> list:
    me_tag   = "  ← 나" if is_me else ""
    bg_color = "#2a2f52" if is_me else "#1a1a1a"
    line_w   = 2 if is_me else 0

    return [
        visual.Rect(win, width=_ROW_W, height=_ROW_H, pos=(0, y),
                    fillColor=bg_color,
                    lineColor=color if is_me else None,
                    lineWidth=line_w),
        visual.TextStim(win,
                        text=f"{rank_label}   Sub-{subject_id}{me_tag}",
                        pos=(_LABEL_X, y),
                        color=color if is_me else _WHITE,
                        height=34, bold=is_me, font=FONT,
                        anchorHoriz="left"),
        visual.TextStim(win,
                        text=f"{accuracy * 100:.1f}%",
                        pos=(_SCORE_X, y),
                        color=color, height=34, bold=True, font=FONT,
                        anchorHoriz="right"),
    ]


# ── public entry point ────────────────────────────────────────────────────────

def run_ending(
    win: visual.Window,
    subject_id: str,
    cumulative_score: float,
    elapsed_seconds: float = 0.0,
) -> None:
    """Show top-4 leaderboard by accuracy and highlight current subject's rank."""
    max_score = _max_trial_score(Path(SCORE_CSV))
    entries   = _load_all_accuracies(DATA_DIR, max_score)

    my_acc = _accuracy_from_csv(
        DATA_DIR / f"sub-{subject_id}" / "trials.csv", max_score
    ) or 0.0

    for e in entries:
        if e["subject_id"] == subject_id:
            e["accuracy"] = my_acc
            break
    else:
        entries.append({"subject_id": subject_id, "accuracy": my_acc})

    sorted_entries = sorted(entries, key=lambda x: x["accuracy"], reverse=True)
    my_rank, total = _rank_of(my_acc, entries)

    # ── header ────────────────────────────────────────────────────────────────
    stims: list = [
        visual.TextStim(win, text="실험이 끝났습니다!",
                        pos=(0, _TITLE_Y), color=_GOLD,
                        height=50, bold=True, font=FONT),
        visual.TextStim(win, text="수고하셨습니다.",
                        pos=(0, _SUBTITLE_Y), color=_WHITE,
                        height=38, font=FONT),
        visual.TextStim(win, text="순위표  (정답률 기준)",
                        pos=(0, _HEADER_Y), color=_GRAY,
                        height=28, font=FONT),
    ]

    # ── top-4 rows ────────────────────────────────────────────────────────────
    shown = sorted_entries[:4]
    for i, entry in enumerate(shown):
        y     = _ROW_TOP_Y - i * _ROW_STEP
        color = _RANK_COLORS[i]
        is_me = entry["subject_id"] == subject_id
        stims += _row_stims(win, _RANK_LABELS[i], entry["subject_id"],
                            entry["accuracy"], y, color, is_me)

    # bottom y of the last shown row (centre)
    last_row_y = _ROW_TOP_Y - (len(shown) - 1) * _ROW_STEP

    # ── out-of-top-4 row ──────────────────────────────────────────────────────
    if my_rank > 4:
        ellipsis_y = last_row_y - _ROW_STEP
        my_y       = ellipsis_y - _ROW_STEP + 14
        stims.append(
            visual.TextStim(win, text="·  ·  ·", pos=(0, ellipsis_y),
                            color=_GRAY, height=28, font=FONT)
        )
        stims += _row_stims(win, f"{my_rank}위", subject_id,
                            my_acc, my_y, _GREEN, is_me=True)
        last_row_y = my_y

    # ── summary (dynamic, always below the last row) ──────────────────────────
    stats_y = last_row_y - _ROW_H // 2 - 48
    rank_y  = stats_y - 60
    exit_y  = rank_y  - 48

    stims += [
        visual.TextStim(
            win,
            text=(
                f"정답률  {my_acc * 100:.1f}%"
                f"   ·   총 점수  {int(cumulative_score)}점"
                f"   ·   소요시간  {_fmt_elapsed(elapsed_seconds)}"
            ),
            pos=(0, stats_y),
            color=_GRAY, height=28, font=FONT,
            wrapWidth=1400,
        ),
        visual.TextStim(
            win,
            text=f"전체 {total}명 중  {my_rank}위",
            pos=(0, rank_y),
            color=_WHITE, height=34, bold=True, font=FONT,
            wrapWidth=800,
        ),
        visual.TextStim(win, text="[ Space ] 키를 눌러 종료",
                        pos=(0, exit_y), color=_GRAY, height=28, font=FONT,
                        wrapWidth=800),
    ]

    event.clearEvents()
    while True:
        for stim in stims:
            stim.draw()
        win.flip()
        check_escape(win)
        if event.getKeys(keyList=["space"]):
            break
    event.clearEvents()
