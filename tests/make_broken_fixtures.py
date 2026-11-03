"""Create one broken fixture per failure rule in docs/design.md.

Each file is clean_sample.csv with exactly one change, so each test
isolates one rule. Run from the project root:
    python tests/make_broken_fixtures.py
"""

from pathlib import Path

import pandas as pd

FIXTURES = Path("tests/fixtures")
clean = pd.read_csv(FIXTURES / "clean_sample.csv", dtype=str, keep_default_na=False)
nov_3112 = (clean["month"] == "Nov") & (clean["district_code"] == "3112")


def save(df, name):
    df.to_csv(FIXTURES / name, index=False)
    print(f"wrote {name}: {len(df)} rows, {df.shape[1]} columns")


# Drift: added column -> log and flag
added = clean.copy()
added["Extra_Note"] = "x"
save(added, "added_column.csv")

# Drift: renamed column -> halt (rapidfuzz should suggest the new name)
save(clean.rename(columns={"Total_Exp": "Total_Expenditure"}), "renamed_column.csv")

# Drift: missing column -> halt
save(clean.drop(columns=["Remarks"]), "missing_column.csv")

# Unknown month spelling -> quarantine that row, no fuzzy matching
bad_month = clean.copy()
bad_month.loc[nov_3112, "month"] = "Sept"
save(bad_month, "unknown_month.csv")

# Duplicate natural key -> quarantine every copy
dup_row = clean.loc[nov_3112].copy()
dup_row["Wages"] = "1"  # different value, so the two rows conflict
save(pd.concat([clean, dup_row], ignore_index=True), "duplicate_key.csv")

# Non-numeric value in a measure column -> quarantine that row
bad_number = clean.copy()
bad_number.loc[nov_3112, "Wages"] = "--"
save(bad_number, "non_numeric.csv")

# Encoding: UTF-8 with BOM -> accept and strip the BOM on read
clean.to_csv(FIXTURES / "bom_utf8.csv", index=False, encoding="utf-8-sig")
print("wrote bom_utf8.csv: UTF-8 with BOM")

# Encoding: Windows-1252 bytes that are invalid UTF-8 -> halt
# The baseline is pure ASCII, which is valid in any encoding, so this
# fixture needs one accented character to test anything.
cp1252 = clean.copy()
cp1252.loc[cp1252["district_name"] == "BULANDSHAHR", "district_name"] = "BULANDSHÁHR"
cp1252.to_csv(FIXTURES / "cp1252_accented.csv", index=False, encoding="cp1252")
print("wrote cp1252_accented.csv: Windows-1252 bytes")
