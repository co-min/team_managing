import csv
import os
import sys

BASE_DIR = os.path.dirname(__file__)

CONFIGS = {
    'domain1': {
        'input_file':  'domain3/score_table.csv',
        'domains':     ['cooking', 'repairing', 'tennis'],
        'output_file': 'domain3/score_table_ranked.csv',
    },
    'domain2': {
        'input_file':  'domain2/score_table_domain2.csv',
        'domains':     ['cooking', 'repairing'],
        'output_file': 'domain2/score_table_ranked_domain2.csv',
    },
}


def rank_scores(rows, domains):
    """도메인별로 점수를 rank(1=최저, 6=최고)×10으로 변환"""
    result = [row.copy() for row in rows]

    for d in domains:
        col = f'sc_{d}'
        scores = [(i, float(row[col])) for i, row in enumerate(rows)]
        # 오름차순 정렬 → rank 1부터 부여
        sorted_idx = sorted(scores, key=lambda x: x[1])
        rank_map = {idx: rank + 1 for rank, (idx, _) in enumerate(sorted_idx)}
        for i, row in enumerate(result):
            row[col] = rank_map[i] * 10

    return result


def run(config_name):
    cfg = CONFIGS[config_name]
    domains = cfg['domains']
    in_path = os.path.join(BASE_DIR, cfg['input_file'])

    with open(in_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        rows = list(reader)

    ranked = rank_scores(rows, domains)

    out_path = os.path.join(BASE_DIR, cfg['output_file'])
    fieldnames = ['pair_id', 'char1', 'char2'] + [f'sc_{d}' for d in domains]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ranked)

    print(f"[{config_name}] Saved → {out_path}")
    header = f"{'pair_id':>8} {'char1':>6} {'char2':>6}" + \
             ''.join(f" {f'sc_{d}':>12}" for d in domains)
    print(header)
    for r in ranked:
        line = f"{r['pair_id']:>8} {r['char1']:>6} {r['char2']:>6}" + \
               ''.join(f" {r[f'sc_{d}']:>12}" for d in domains)
        print(line)


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(CONFIGS.keys())

    for name in targets:
        if name not in CONFIGS:
            print(f"Unknown config '{name}'. Available: {list(CONFIGS.keys())}")
            sys.exit(1)
        run(name)
        print()


if __name__ == '__main__':
    main()
