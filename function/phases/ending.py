# function/phases/ending.py
"""
Ending screen — leaderboard ranked by perfect-score rate.

정답률 = (feedback_score == max_trial_score 인 trial 수) / responded_trials
"""

import csv
from pathlib import Path

from psychopy import event, visual

from function.config.settings import DATA_DIR, FONT, SCORE_CSV
from function.config.strings import t
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
    return t("ending_elapsed_fmt", m=total // 60, s=total % 60)


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
    me_tag   = t("ending_me_tag") if is_me else ""
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
        visual.TextStim(win, text=t("ending_title"),
                        pos=(0, _TITLE_Y), color=_GOLD,
                        height=50, bold=True, font=FONT),
        visual.TextStim(win, text=t("ending_subtitle"),
                        pos=(0, _SUBTITLE_Y), color=_WHITE,
                        height=38, font=FONT),
        visual.TextStim(win, text=t("ending_leaderboard_header"),
                        pos=(0, _HEADER_Y), color=_GRAY,
                        height=28, font=FONT),
    ]

    # ── top-4 rows ────────────────────────────────────────────────────────────
    shown = sorted_entries[:4]
    for i, entry in enumerate(shown):
        y     = _ROW_TOP_Y - i * _ROW_STEP
        color = _RANK_COLORS[i]
        is_me = entry["subject_id"] == subject_id
        stims += _row_stims(win, t("ending_rank_label", rank=i + 1), entry["subject_id"],
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
        stims += _row_stims(win, t("ending_rank_label", rank=my_rank), subject_id,
                            my_acc, my_y, _GREEN, is_me=True)
        last_row_y = my_y

    # ── summary (dynamic, always below the last row) ──────────────────────────
    stats_y = last_row_y - _ROW_H // 2 - 48
    rank_y  = stats_y - 60
    exit_y  = rank_y  - 48

    stims += [
        visual.TextStim(
            win,
            text=t("ending_stats",
                   accuracy=f"{my_acc * 100:.1f}%",
                   score=int(cumulative_score),
                   elapsed=_fmt_elapsed(elapsed_seconds)),
            pos=(0, stats_y),
            color=_GRAY, height=28, font=FONT,
            wrapWidth=1400,
        ),
        visual.TextStim(
            win,
            text=t("ending_rank_summary", total=total, rank=my_rank),
            pos=(0, rank_y),
            color=_WHITE, height=34, bold=True, font=FONT,
            wrapWidth=800,
        ),
        visual.TextStim(win, text=t("ending_exit_prompt"),
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
