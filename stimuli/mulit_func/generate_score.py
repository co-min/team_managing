import csv
import os

BASE_DIR = os.path.dirname(__file__)

def load_competence(path):
    """char_ani -> {domain: score} mapping (one entry per character type)"""
    competence = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            char = row['char_ani'].strip()
            if char not in competence:
                competence[char] = {
                    'cooking':   int(row['cooking']),
                    'repairing': int(row['repairing']),
                    'tennis':    int(row['tennis']),
                }
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
            # score = synergy * (competency_char1 + competency_char2)
            row[f'sc_{d}'] = syn * (competence[c1][d] + competence[c2][d])
        rows.append(row)
    return rows

def main():
    competence = load_competence(os.path.join(BASE_DIR, 'competence_table.csv'))
    pairs      = load_synergy(os.path.join(BASE_DIR, 'synergy_table.csv'))
    domains    = ['cooking', 'repairing', 'tennis']

    rows = generate_score_table(competence, pairs, domains)

    out_path = os.path.join(BASE_DIR, 'score_table.csv')
    fieldnames = ['pair_id', 'char1', 'char2', 'sc_cooking', 'sc_repairing', 'sc_tennis']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved → {out_path}")
    print(f"{'pair_id':>8} {'char1':>6} {'char2':>6} {'sc_cooking':>12} {'sc_repairing':>14} {'sc_tennis':>11}")
    for r in rows:
        print(f"{r['pair_id']:>8} {r['char1']:>6} {r['char2']:>6} {r['sc_cooking']:>12.4g} {r['sc_repairing']:>14.4g} {r['sc_tennis']:>11.4g}")

if __name__ == '__main__':
    main()
