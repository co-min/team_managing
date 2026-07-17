import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASIC_PATH = os.path.join(BASE_DIR, "comp_basic.csv")
TABLE_PATH = os.path.join(BASE_DIR, "competence_table.csv")

COMP_COLS = ["cooking", "repairing", "tennis"]

def stripped_reader(f):
    reader = csv.DictReader(f)
    reader.fieldnames = [h.strip() for h in reader.fieldnames]
    return reader

def load_basic(path):
    mapping = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = stripped_reader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            char = row["char_ani"]
            mapping[char] = {col: row[col] for col in COMP_COLS}
    return mapping

def update_table(table_path, mapping):
    rows = []
    with open(table_path, newline="", encoding="utf-8") as f:
        reader = stripped_reader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            char = row["char_ani"]
            if char in mapping:
                for col in COMP_COLS:
                    row[col] = mapping[char][col]
            rows.append(row)

    with open(table_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    mapping = load_basic(BASIC_PATH)
    print("comp_basic.csv 기준값:")
    for char, vals in mapping.items():
        print(f"  {char}: {vals}")

    update_table(TABLE_PATH, mapping)
    print("\ncompetence_table.csv 업데이트 완료.")
