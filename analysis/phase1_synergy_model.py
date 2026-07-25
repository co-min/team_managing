"""
Phase 1 Synergy Inference Model — fitting skeleton
====================================================

목적: competence가 known, synergy가 hidden인 Phase 1 trial에서
delta-rule로 synergy belief를 학습하는 참가자의 선택 데이터에서
learning rate(alpha)와 inverse temperature(beta)를 MLE로 추정.

이 파일은 "구조(skeleton)"입니다 — 실제 데이터 포맷에 맞춰
load_subject_trials()와 competence lookup 부분을 채워 넣어야 완성됩니다.
TODO 표시된 부분이 데이터 연결이 필요한 지점입니다.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from itertools import combinations

# ---------------------------------------------------------------
# 상수: role은 A~D 4개 고정, pair는 4C2 = 6개
# ---------------------------------------------------------------
ROLES = ["A", "B", "C", "D"]
ROLE_PAIRS = list(combinations(ROLES, 2))  # [('A','B'), ('A','C'), ...]


def normalize_pair(a, b):
    """(role1, role2) 순서를 항상 알파벳순으로 통일 -> belief dict key로 사용."""
    return tuple(sorted((a, b)))


# ---------------------------------------------------------------
# 1. Belief state
# ---------------------------------------------------------------
def init_beliefs():
    """모든 pair의 synergy belief를 중립값 1.0으로 초기화.
    (곱셈모델에서 1.0 = '시너지 없음'과 동치인 neutral prior)
    """
    return {pair: 1.0 for pair in ROLE_PAIRS}


def update_belief(beliefs, pair, observed_synergy, alpha):
    """Delta-rule 업데이트. 선택된 pair만 업데이트되고 나머지는 그대로 유지됨
    (bandit 구조 — 선택 안 한 pair는 피드백을 못 받으므로).
    """
    pe = observed_synergy - beliefs[pair]
    beliefs[pair] = beliefs[pair] + alpha * pe
    return pe


# ---------------------------------------------------------------
# 2. Decision value & softmax
# ---------------------------------------------------------------
def pair_value(beliefs, pair, competence_sum):
    """V(pair) = belief(synergy) x competence 합."""
    return beliefs[pair] * competence_sum


def softmax_probs(values, beta):
    """수치 안정성을 위해 max를 빼고 exponentiate."""
    values = np.asarray(values, dtype=float)
    shifted = beta * (values - values.max())
    exp_v = np.exp(shifted)
    return exp_v / exp_v.sum()


def choice1_value(beliefs, animal, partners, competence_lookup):
    """Choice 1의 value = 남은 파트너들과 짝지었을 때 V의 '평균'.
    (참가자가 최선의 파트너를 미리 내다보지 않는다는 가정 — 사용자 결정사항)
    """
    vals = []
    for partner in partners:
        pair = normalize_pair(animal, partner)
        comp_sum = competence_lookup(pair)
        vals.append(pair_value(beliefs, pair, comp_sum))
    return float(np.mean(vals))


# ---------------------------------------------------------------
# 3. Negative log-likelihood (한 명의 subject, Phase 1 trial만 사용)
# ---------------------------------------------------------------
def negative_log_likelihood(params, trials, gamma=None):
    """
    params: (alpha, beta)
    trials: block 순서대로 정렬된 trial dict의 리스트. 각 trial은 아래 필드를 가정:
        - 'block': block index (belief reset/carry-over 판단용)
        - 'animals_available': choice1 시점의 후보 animal 리스트 (role로 표현, 예: ['A','B','C','D'])
        - 'chosen_animal1': choice1에서 고른 role
        - 'partners_available': choice2 시점의 후보 partner role 리스트
        - 'chosen_partner': choice2에서 고른 role
        - 'competence_lookup': function(pair_tuple) -> competence_sum (해당 trial의 domain 기준)
        - 'score': 실제 받은 feedback 점수
    gamma: None이면 no-reset(그대로 유지) 모델. 0~1 값이면 block 전환 시
           belief를 1.0 방향으로 gamma만큼만 당겨서 시작 (carry-over 강도).
    """
    alpha, beta = params
    beliefs = init_beliefs()
    nll = 0.0
    prev_block = None
    eps = 1e-12  # log(0) 방지

    for trial in trials:
        # --- block 전환 시 carry-over 처리 ---
        if prev_block is not None and trial["block"] != prev_block:
            if gamma is not None:
                beliefs = {p: 1.0 + gamma * (b - 1.0) for p, b in beliefs.items()}
            # gamma가 None이면 아무 것도 안 함 = 이전 belief 그대로 이월(no-reset)
            # 완전 reset 모델을 만들고 싶으면 여기서 beliefs = init_beliefs()
        prev_block = trial["block"]

        comp_lookup = trial["competence_lookup"]

        # --- Choice 1 likelihood ---
        c1_values = [
            choice1_value(
                beliefs,
                animal,
                [p for p in trial["animals_available"] if p != animal],
                comp_lookup,
            )
            for animal in trial["animals_available"]
        ]
        p1 = softmax_probs(c1_values, beta)
        idx1 = trial["animals_available"].index(trial["chosen_animal1"])
        nll -= np.log(p1[idx1] + eps)

        # --- Choice 2 likelihood ---
        c2_values = [
            pair_value(
                beliefs,
                normalize_pair(trial["chosen_animal1"], partner),
                comp_lookup(normalize_pair(trial["chosen_animal1"], partner)),
            )
            for partner in trial["partners_available"]
        ]
        p2 = softmax_probs(c2_values, beta)
        idx2 = trial["partners_available"].index(trial["chosen_partner"])
        nll -= np.log(p2[idx2] + eps)

        # --- belief update (실제 선택된 pair만) ---
        chosen_pair = normalize_pair(trial["chosen_animal1"], trial["chosen_partner"])
        comp_sum = comp_lookup(chosen_pair)
        observed_synergy = trial["score"] / comp_sum
        update_belief(beliefs, chosen_pair, observed_synergy, alpha)

    return nll


# ---------------------------------------------------------------
# 4. Fitting routine (subject 1명)
# ---------------------------------------------------------------
def fit_subject(trials, gamma=None, x0=(0.3, 1.0)):
    """alpha, beta를 MLE로 추정."""
    bounds = [(1e-4, 1.0), (1e-4, 10.0)]  # alpha in (0,1], beta in (0,10]
    result = minimize(
        negative_log_likelihood,
        x0=np.array(x0),
        args=(trials, gamma),
        method="L-BFGS-B",
        bounds=bounds,
    )
    alpha_hat, beta_hat = result.x
    return {"alpha": alpha_hat, "beta": beta_hat, "nll": result.fun, "success": result.success}


# ---------------------------------------------------------------
# 5. Parameter recovery (실제 데이터 fitting 전에 반드시 확인)
# ---------------------------------------------------------------
def simulate_trials(true_alpha, true_beta, trial_template, rng=None):
    """trial_template(선택 옵션/competence/domain 구조는 실제 실험과 동일하되
    chosen_animal1/chosen_partner/score는 비어있는 trial 리스트)을 받아서
    모델이 스스로 선택하고 그 결과로 score를 생성하는 시뮬레이션.

    TODO: score 생성 시 실제 synergy_table/competence_table 기반 ground-truth를
    사용해서 Score = true_synergy(pair) x competence_sum 계산.
    """
    rng = rng or np.random.default_rng()
    beliefs = init_beliefs()
    sim_trials = []

    for template in trial_template:
        trial = dict(template)  # shallow copy
        comp_lookup = trial["competence_lookup"]

        c1_values = [
            choice1_value(beliefs, a, [p for p in trial["animals_available"] if p != a], comp_lookup)
            for a in trial["animals_available"]
        ]
        p1 = softmax_probs(c1_values, true_beta)
        chosen1 = rng.choice(trial["animals_available"], p=p1)
        trial["chosen_animal1"] = chosen1

        # 주의: partners_available은 template의 고정값이 아니라 choice1 결과에 따라
        # 동적으로 계산해야 함 (animals_available에서 방금 고른 동물만 제외).
        # 실제 raw log 기반 trial(load_subject_trials 결과)은 이미 올바른 값을 담고
        # 있지만, 시뮬레이션에서는 chosen1이 매번 달라지므로 여기서 다시 계산.
        trial["partners_available"] = [a for a in trial["animals_available"] if a != chosen1]

        c2_values = [
            pair_value(beliefs, normalize_pair(chosen1, p), comp_lookup(normalize_pair(chosen1, p)))
            for p in trial["partners_available"]
        ]
        p2 = softmax_probs(c2_values, true_beta)
        chosen2 = rng.choice(trial["partners_available"], p=p2)
        trial["chosen_partner"] = chosen2

        chosen_pair = normalize_pair(chosen1, chosen2)
        comp_sum = comp_lookup(chosen_pair)
        # TODO: true_synergy_lookup(chosen_pair) 로 교체
        true_synergy = trial.get("true_synergy_lookup", lambda p: 1.0)(chosen_pair)
        trial["score"] = true_synergy * comp_sum

        observed_synergy = trial["score"] / comp_sum
        update_belief(beliefs, chosen_pair, observed_synergy, true_alpha)

        sim_trials.append(trial)

    return sim_trials


def parameter_recovery_check(trial_template, n_sim=50, alpha_range=(0.05, 0.95), beta_range=(0.2, 5.0), seed=0):
    """true (alpha, beta)를 무작위로 뽑아 데이터를 시뮬레이션하고,
    fit_subject로 복원한 값과 비교. 상관관계가 낮으면 현재 trial 수/설계로는
    해당 파라미터를 안정적으로 추정하기 어렵다는 뜻 (poster limitation으로 보고).
    """
    rng = np.random.default_rng(seed)
    true_alphas, true_betas, rec_alphas, rec_betas = [], [], [], []

    for _ in range(n_sim):
        a_true = rng.uniform(*alpha_range)
        b_true = rng.uniform(*beta_range)
        sim_trials = simulate_trials(a_true, b_true, trial_template, rng)
        fit = fit_subject(sim_trials)

        true_alphas.append(a_true)
        true_betas.append(b_true)
        rec_alphas.append(fit["alpha"])
        rec_betas.append(fit["beta"])

    alpha_corr = np.corrcoef(true_alphas, rec_alphas)[0, 1]
    beta_corr = np.corrcoef(true_betas, rec_betas)[0, 1]
    return {"alpha_recovery_r": alpha_corr, "beta_recovery_r": beta_corr}


# =================================================================
# 6. 실제 데이터 포맷 연결: trials.csv -> 스켈레톤이 기대하는 trial dict
# =================================================================
# 실제 trials.csv 컬럼 (data/sub-{id}/trials.csv):
#   subject_id, global_trial_id, block_trial_id, block("block_0"~"block_5"),
#   phase("phase_1"/"phase_2"), domain, trial_id, stim_pair_id,
#   layout_up, layout_down, layout_right, layout_left,
#   response_made, choice1_code(A~D), choice2_code(A~D),
#   choice1_animal, choice2_animal, rt_choice1, rt_choice2,
#   feedback_score, elapsed_time, timestamp, optimal_score, is_optimal
#
# Phase 1: phase == "phase_1" (block_0, block_2, block_4)
# mission_id: block_num + 1 (block_0 → mission 1, ..., block_4 → mission 5)
# choice1_code / choice2_code 가 이미 role(A/B/C/D)이므로 roster 변환 불필요.
# layout 4열(animal 이름)을 role로 바꾸는 데 competence_table.csv 활용.


def build_competence_table(competence_csv_path):
    """competence_table.csv를 읽어 두 가지 lookup을 반환.

    Returns
    -------
    comp : dict  (mission_id, role, domain) -> float
    animal_to_role : dict  (mission_id, animal_name) -> role
        layout 컬럼의 animal 이름을 role(A~D)로 변환할 때 사용.
    """
    df = pd.read_csv(competence_csv_path)
    df.columns = [c.strip() for c in df.columns]
    df["mission_id"] = ((df["id"] - 1) // 4) + 1

    domains = [c for c in df.columns if c in {"cooking", "repairing", "tennis"}]
    comp = {}
    animal_to_role = {}
    for row in df.itertuples():
        mid = int(row.mission_id)
        role = str(row.char_ani).strip()
        animal = str(row.animal).strip()
        animal_to_role[(mid, animal)] = role
        for d in domains:
            comp[(mid, role, d)] = float(getattr(row, d))

    return comp, animal_to_role


def make_competence_lookup(comp, mission_id, domain):
    """pair(role_tuple) -> competence 합산값 함수를 반환."""
    def _lookup(role_pair):
        r1, r2 = role_pair
        return comp[(mission_id, r1, domain)] + comp[(mission_id, r2, domain)]
    return _lookup


def load_subject_trials(trials_csv_path, competence_csv_path):
    """trials.csv와 competence_table.csv로 skeleton이 기대하는 trial dict 리스트를 생성.

    Parameters
    ----------
    trials_csv_path : str
        data/sub-{id}/trials.csv 경로
    competence_csv_path : str
        stimuli/competence_table.csv 경로 (Phase 1은 3-domain 버전 사용)

    Returns
    -------
    trials : list[dict]  — negative_log_likelihood / fit_subject에 바로 전달 가능
    """
    df = pd.read_csv(trials_csv_path)
    comp, animal_to_role = build_competence_table(competence_csv_path)

    # Phase 1만, no-response 제외, trial 순서 유지
    phase1 = df[(df["phase"] == "phase_1") & (df["response_made"].astype(str) == "True")].sort_values(
        "global_trial_id"
    )

    trials = []
    for row in phase1.itertuples():
        block_num = int(row.block.split("_")[1])   # "block_0" -> 0
        mission_id = block_num + 1                 # block 0→mission 1, 2→3, 4→5
        domain = row.domain

        # layout 4열을 role로 변환
        layout_animals = [row.layout_up, row.layout_down, row.layout_right, row.layout_left]
        try:
            animals_available = [animal_to_role[(mission_id, a)] for a in layout_animals]
        except KeyError as e:
            raise KeyError(
                f"animal_to_role 실패 {e} — competence_table mission {mission_id} 확인"
            ) from e

        chosen_animal1 = str(row.choice1_code).strip()   # 이미 role (A/B/C/D)
        chosen_partner = str(row.choice2_code).strip()
        partners_available = [r for r in animals_available if r != chosen_animal1]

        comp_lookup = make_competence_lookup(comp, mission_id, domain)

        trials.append({
            "block": block_num,
            "animals_available": animals_available,
            "chosen_animal1": chosen_animal1,
            "partners_available": partners_available,
            "chosen_partner": chosen_partner,
            "competence_lookup": comp_lookup,
            "score": float(row.feedback_score),
        })

    return trials


# ---------------------------------------------------------------
# 7. synergy_table -> true_synergy_lookup (parameter recovery용)
# ---------------------------------------------------------------
def build_synergy_lookup(synergy_csv_path):
    """synergy_table.csv -> normalized_pair -> synergy_score dict."""
    df = pd.read_csv(synergy_csv_path)
    df.columns = [c.strip() for c in df.columns]
    return {
        normalize_pair(str(row.char1).strip(), str(row.char2).strip()): float(row.synergy_score)
        for row in df.itertuples()
    }


if __name__ == "__main__":
    import pathlib

    ROOT = pathlib.Path(__file__).parent.parent   # team_managing-v3/
    STIMULI = ROOT / "stimuli"
    DATA = ROOT / "data"

    comp_csv = STIMULI / "competence_table.csv"

    results = []
    for sub_dir in sorted(DATA.glob("sub-*")):
        trials_csv = sub_dir / "trials.csv"
        if not trials_csv.exists():
            continue

        subject_id = sub_dir.name  # e.g. "sub-009"
        trials = load_subject_trials(str(trials_csv), str(comp_csv))
        if not trials:
            print(f"{subject_id}: Phase 1 trial 없음, 건너뜀")
            continue

        fit = fit_subject(trials)
        results.append({"subject": subject_id, **fit})
        print(f"{subject_id}  alpha={fit['alpha']:.4f}  beta={fit['beta']:.4f}  "
              f"nll={fit['nll']:.2f}  ok={fit['success']}")

    if results:
        out = pd.DataFrame(results)
        out_path = DATA / "phase1_model_fits.csv"
        out.to_csv(out_path, index=False)
        print(f"\n결과 저장: {out_path}")