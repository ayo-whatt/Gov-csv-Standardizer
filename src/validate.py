"""Stage 3: check each row, derive the period, and quarantine bad rows.

Row checks run first. Duplicate natural keys are checked last, among rows that
passed, and every copy of a duplicated key is quarantined.
"""
import re
from collections import Counter

from src.config import MONTHS, NOT_MEASURES

FIN_YEAR = re.compile(r"^(\d{4})-(\d{4})$")
INTEGER = re.compile(r"^-?\d+$")
DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


def derive_period(fin_year, month):
    """Return (period, None) on success or (None, reason). Financial years start in April."""
    match = FIN_YEAR.match(fin_year)
    if not match or int(match[2]) != int(match[1]) + 1:
        return None, f"invalid financial year '{fin_year}'"
    month_number = MONTHS.get(month)
    if month_number is None:
        return None, f"unknown month spelling '{month}'"
    start = int(match[1])
    year = start if month_number >= 4 else start + 1
    return f"{year}-{month_number:02d}-01", None


def check_values(record, types, measures):
    for name in measures:
        value = record[name]
        if value.strip() == "":
            return "blank measure value"
        pattern = INTEGER if types[name] == "integer" else DECIMAL
        if not pattern.match(value):
            return f"non-numeric value in {name}: '{value}'"
    return None


def validate(header, rows, schema_columns):
    """rows: (source_row, fields) with the correct width.

    Returns (kept, rejects):
      kept:    (source_row, fields, record), where record includes 'period'
      rejects: (source_row, reason, fields)
    """
    types = {c["name"]: c["type"] for c in schema_columns}
    measures = [name for name in types if name not in NOT_MEASURES]

    passed, rejects = [], []
    for source_row, fields in rows:
        record = dict(zip(header, fields))
        period, reason = derive_period(record["fin_year"], record["month"])
        if reason is None:
            reason = check_values(record, types, measures)
        if reason is not None:
            rejects.append((source_row, reason, fields))
            continue
        record["period"] = period
        passed.append((source_row, fields, record))

    counts = Counter((rec["period"], rec["district_code"]) for _, _, rec in passed)
    kept = []
    for source_row, fields, record in passed:
        if counts[(record["period"], record["district_code"])] > 1:
            rejects.append((source_row, "duplicate natural key (period, district_code)", fields))
        else:
            kept.append((source_row, fields, record))
    return kept, rejects
