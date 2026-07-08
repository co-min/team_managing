import pandas as pd

from function.config.settings import COMPETENCE_CSV, SCORE_CSV, DOMAINS


def load_all_data():
    """
    Load the three stimulus CSVs into fast-lookup dicts.

    competence : {char_code: {domain: score}}
    synergy    : {(charA, charB): float}         — sorted-tuple key
    score      : {(charA, charB): {domain: float}} — sorted-tuple key
    """
    comp_df = pd.read_csv(COMPETENCE_CSV, skipinitialspace=True)
    competence = {}
    for _, row in comp_df.iterrows():
        char = str(row['char_ani']).strip()
        competence[char] = {d: int(row[d]) for d in DOMAINS}

    n_chars       = comp_df['char_ani'].nunique()
    n_groups      = len(comp_df) // n_chars
    animal_groups = [
        list(comp_df.iloc[g * n_chars:(g + 1) * n_chars]['animal'].str.strip())
        for g in range(n_groups)
    ]

    syn_df = pd.read_csv('stimuli/synergy_table.csv', skipinitialspace=True)
    synergy = {}
    for _, row in syn_df.iterrows():
        key = tuple(sorted([str(row['char1']).strip(), str(row['char2']).strip()]))
        synergy[key] = float(row['synergy_score'])

    score_df = pd.read_csv(SCORE_CSV, skipinitialspace=True)
    score = {}
    for _, row in score_df.iterrows():
        key = tuple(sorted([str(row['char1']).strip(), str(row['char2']).strip()]))
        score[key] = {d: float(row[f'sc_{d}']) for d in DOMAINS}

    return competence, synergy, score, animal_groups
