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

# ── layout ───────────────────────────────────────────────────────────────────

_GOLD   = "#FFD700"
_SILVER = "#C0C0C0"
_BRONZE = "#CD7F32"
_BLUE   = "#4FC3F7"
_GREEN  = "#4CAF50"
_GRAY   = "#AAAAAA"

_RANK_COLORS = [_GOLD, _SILVER, _BRONZE, _BLUE]
_RANK_LABELS = ["1위", "2위", "3위", "4위"]

_ROW_W      = 720
_ROW_H      = 68
_ROW_STEP   = 85       # vertical gap between rows
_ROW_TOP_Y  = 110      # y of rank-1 row
_LABEL_X    = -260
_SCORE_X    =  240


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
    rank_label: str,
    subject_id: str,
    accuracy: float,
    y: float,
    color: str,
    is_me: bool,
) -> list:
    me_tag   = "  <- 나" if is_me else ""
    bg_color = "#2d3050" if is_me else "#1e1e1e"
    line_w   = 2 if is_me else 0

    stims = [
        visual.Rect(win, width=_ROW_W, height=_ROW_H, pos=(0, y),
                    fillColor=bg_color,
                    lineColor=color if is_me else None,
                    lineWidth=line_w),
        visual.TextStim(win,
                        text=f"{rank_label}   Sub-{subject_id}{me_tag}",
                        pos=(_LABEL_X, y),
                        color=color if is_me else "white",
                        height=36, bold=is_me, font=FONT,
                        anchorHoriz="left"),
        visual.TextStim(win,
                        text=f"{accuracy * 100:.1f}%",
                        pos=(_SCORE_X, y),
                        color=color, height=36, bold=True, font=FONT,
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

    # ── build stims ───────────────────────────────────────────────────────────
    stims: list = [
        visual.TextStim(win, text="실험이 끝났습니다!",
                        pos=(0, 340), color=_GOLD, height=66, bold=True, font=FONT),
        visual.TextStim(win, text="수고하셨습니다.",
                        pos=(0, 265), color="white", height=42, font=FONT),
        visual.TextStim(win, text="순위표  (정답률 기준)",
                        pos=(0, 195), color=_GRAY, height=34, font=FONT),
    ]

    # Top-4 rows
    for i, entry in enumerate(sorted_entries[:4]):
        y      = _ROW_TOP_Y - i * _ROW_STEP
        color  = _RANK_COLORS[i]
        is_me  = entry["subject_id"] == subject_id
        stims += _row_stims(win, _RANK_LABELS[i], entry["subject_id"],
                            entry["accuracy"], y, color, is_me)

    # If current subject is outside top-4, show them separately below
    if my_rank > 4:
        ellipsis_y = _ROW_TOP_Y - 4 * _ROW_STEP + 10
        my_y       = ellipsis_y - _ROW_STEP + 10
        stims.append(
            visual.TextStim(win, text="...", pos=(0, ellipsis_y),
                            color=_GRAY, height=36, font=FONT)
        )
        stims += _row_stims(win, f"{my_rank}위", subject_id,
                            my_acc, my_y, _GREEN, is_me=True)

    # Personal summary line
    stims += [
        visual.TextStim(
            win,
            text=f"내 총 점수: {int(cumulative_score)}점     |     정답률: {my_acc * 100:.1f}%     |     전체 {total}명 중 {my_rank}위",
            pos=(0, -355),
            color=_GRAY, height=34, font=FONT,
        ),
        visual.TextStim(win, text="[Space] 키를 눌러 종료",
                        pos=(0, -420), color=_GRAY, height=32, font=FONT),
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
