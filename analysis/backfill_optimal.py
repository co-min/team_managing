"""
backfill_optimal.py
-------------------
기존 trials.csv에 optimal_score / is_optimal 컬럼을 소급 추가한다.

layout_up/down/right/left (4마리 이름)를 사용하므로
한 번도 선택되지 않은 동물이 있어도 정확하게 계산된다.

사용법:
    python analysis/backfill_optimal.py           # data/ 아래 전체 피험자
    python analysis/backfill_optimal.py 009 012   # 특정 피험자만
"""

import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STIM_DIR = ROOT / "stimuli"

# ── 스코어 테이블 로드 ──────────────────────────────────────────────────────────
def _load_score_dict(csv_path: Path) -> dict:
    """
    Returns {(charA, charB): {domain: score}} with sorted-tuple keys.
    """
    df = pd.read_csv(csv_path, skipinitialspace=True)
    score_cols = [c for c in df.columns if c.startswith("sc_")]
    out = {}
    for _, row in df.iterrows():
        key = tuple(sorted([str(row["char1"]).strip(), str(row["char2"]).strip()]))
        out[key] = {c[3:]: float(row[c]) for c in score_cols}  # strip "sc_"
    return out


SCORE = {
    "phase_1": _load_score_dict(STIM_DIR / "score_table.csv"),
    "phase_2": _load_score_dict(STIM_DIR / "score_table_domain2.csv"),
}

# ── CHAR_CODE 로드 (animal → char_ani) ────────────────────────────────────────
def _load_char_code() -> dict:
    df = pd.read_csv(STIM_DIR / "competence_table.csv", skipinitialspace=True)
    code = dict(zip(df["animal"].str.strip(), df["char_ani"].str.strip()))
    # phase_2 테이블도 합침 (동물 이름이 겹치면 phase_1이 우선)
    df2 = pd.read_csv(STIM_DIR / "competence_table_domain2.csv", skipinitialspace=True)
    for animal, char in zip(df2["animal"].str.strip(), df2["char_ani"].str.strip()):
        code.setdefault(animal, char)
    return code


CHAR_CODE = _load_char_code()

_LAYOUT_COLS = ["layout_up", "layout_down", "layout_right", "layout_left"]


# ── 핵심 계산 ──────────────────────────────────────────────────────────────────
def _compute_optimal_score(char_order: list, domain: str, score_data: dict):
    """C(4,2) 모든 쌍 중 해당 도메인 최고 점수와 그 쌍 키를 반환한다."""
    best_score, best_key = None, None
    for a1, a2 in combinations(char_order, 2):
        key = tuple(sorted([CHAR_CODE[a1], CHAR_CODE[a2]]))
        sc = score_data.get(key, {}).get(domain, 0.0)
        if best_score is None or sc > best_score:
            best_score, best_key = sc, key
    return best_score, best_key


def _add_optimal_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    optimal_scores = []
    is_optimals = []

    for _, row in df.iterrows():
        if not row.get("response_made", False):
            optimal_scores.append(None)
            is_optimals.append(None)
            continue

        phase = str(row["phase"])
        domain = str(row["domain"])
        score_data = SCORE.get(phase, SCORE["phase_1"])

        char_order = [str(row[c]) for c in _LAYOUT_COLS if pd.notna(row.get(c))]
        if len(char_order) < 2:
            optimal_scores.append(None)
            is_optimals.append(None)
            continue

        opt_score, opt_key = _compute_optimal_score(char_order, domain, score_data)

        c1 = str(row["choice1_code"]) if pd.notna(row.get("choice1_code")) else None
        c2 = str(row["choice2_code"]) if pd.notna(row.get("choice2_code")) else None
        if c1 and c2:
            chosen_key = tuple(sorted([c1, c2]))
            is_opt = (chosen_key == opt_key)
        else:
            is_opt = None

        optimal_scores.append(opt_score)
        is_optimals.append(is_opt)

    df["optimal_score"] = optimal_scores
    df["is_optimal"] = is_optimals
    return df


# ── 피험자별 실행 ──────────────────────────────────────────────────────────────
def backfill_subject(sub_dir: Path) -> None:
    csv_path = sub_dir / "trials.csv"
    if not csv_path.exists():
        print(f"[SKIP] {sub_dir.name}: trials.csv 없음")
        return

    df = pd.read_csv(csv_path)

    if "is_optimal" in df.columns and "optimal_score" in df.columns:
        print(f"[SKIP] {sub_dir.name}: 이미 컬럼 존재")
        return

    df = _add_optimal_columns(df)
    df.to_csv(csv_path, index=False)
    n_opt = df["is_optimal"].sum()
    n_total = df["is_optimal"].notna().sum()
    print(f"[OK]   {sub_dir.name}: {n_opt}/{n_total} optimal ({n_opt/n_total*100:.1f}%)")


def main(subject_ids: list = None) -> None:
    if subject_ids:
        dirs = [DATA_DIR / f"sub-{sid}" for sid in subject_ids]
    else:
        dirs = sorted(DATA_DIR.glob("sub-*"))

    for d in dirs:
        if d.is_dir():
            backfill_subject(d)


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
