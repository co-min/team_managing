import csv
import os
import sys

BASE_DIR = os.path.dirname(__file__)

# ── 분기 설정 ──────────────────────────────────────────────────────────────────
# 새 도메인 추가 시 여기에만 항목을 추가하면 됨
CONFIGS = {
    'domain1': {
        'competence_file': 'competence_table.csv',
        'domains':         ['cooking', 'repairing', 'tennis'],
        'output_file':     'score_table.csv',
    },
    'domain2': {
        'competence_file': 'competence_table_domain2.csv',
        'domains':         ['cooking', 'repairing'],
        'output_file':     'score_table_domain2.csv',
    },
}
# ──────────────────────────────────────────────────────────────────────────────


def load_competence(path, domains):
    """char_ani → {domain: score} mapping (first occurrence per char type)"""
    competence = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            char = row['char_ani'].strip()
            if char not in competence:
                competence[char] = {d: int(row[d]) for d in domains}
    return competence


def load_synergy(path):
    pairs = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            pairs.append({
                'pair_id': int(row['pair_id']),
                'char1':   row['char1'].strip(),
                'char2':   row['char2'].strip(),
                'synergy': float(row['synergy_score']),
            })
    return pairs


def generate_score_table(competence, pairs, domains):
    rows = []
    for p in pairs:
        c1, c2 = p['char1'], p['char2']
        syn = p['synergy']
        row = {'pair_id': p['pair_id'], 'char1': c1, 'char2': c2}
        for d in domains:
            # score = synergy + (competency_char1 + competency_char2)
            row[f'sc_{d}'] = syn * (competence[c1][d] + competence[c2][d])
        rows.append(row)
    return rows


def run(config_name):
    cfg = CONFIGS[config_name]
    domains = cfg['domains']

    competence = load_competence(os.path.join(BASE_DIR, cfg['competence_file']), domains)
    pairs      = load_synergy(os.path.join(BASE_DIR, 'synergy_table.csv'))
    rows       = generate_score_table(competence, pairs, domains)

    out_path   = os.path.join(BASE_DIR, cfg['output_file'])
    fieldnames = ['pair_id', 'char1', 'char2'] + [f'sc_{d}' for d in domains]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[{config_name}] Saved → {out_path}")
    header = f"{'pair_id':>8} {'char1':>6} {'char2':>6}" + \
             ''.join(f" {f'sc_{d}':>12}" for d in domains)
    print(header)
    for r in rows:
        line = f"{r['pair_id']:>8} {r['char1']:>6} {r['char2']:>6}" + \
               ''.join(f" {r[f'sc_{d}']:>12.4g}" for d in domains)
        print(line)


def main():
    # 인자 없으면 전체 config 실행, 있으면 해당 config만 실행
    # 사용법: python generate_score.py domain1
    #          python generate_score.py domain2
    #          python generate_score.py          (전체)
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(CONFIGS.keys())

    for name in targets:
        if name not in CONFIGS:
            print(f"Unknown config '{name}'. Available: {list(CONFIGS.keys())}")
            sys.exit(1)
        run(name)
        print()


if __name__ == '__main__':
    main()
