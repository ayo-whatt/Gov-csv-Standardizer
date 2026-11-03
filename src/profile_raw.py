"""
Profile a raw CSV before writing any pipeline code.

Run from the project root:
    python src/profile_raw.py data/raw/mgnrega_district_glance_2023-04_to_2023-08.csv
    python src/profile_raw.py <path> <header_row_index>   (default 0)

This script only reads the file. It never writes to it.
"""

import csv
import re
import sys
from pathlib import Path

import pandas as pd
from charset_normalizer import from_path

MAX_ITEMS = 60
DATE_TOKENS = {"date", "period", "month", "year", "from", "to"}
PLACE_TOKENS = {"state", "district", "ut", "uts", "region"}


def tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z]+", name.lower()) if t}


def shape(value: str) -> str:
    value = re.sub(r"[A-Za-z]", "a", value)
    return re.sub(r"\d", "9", value)


def detect_encoding(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", True
    best = from_path(path).best()
    return (best.encoding if best else "utf-8"), False


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python src/profile_raw.py <csv_path> [header_row_index]")

    path = Path(sys.argv[1])
    header_row = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    encoding, has_bom = detect_encoding(path)
    with path.open(encoding=encoding, errors="replace") as f:
        head = [f.readline() for _ in range(10)]
    sample = "".join(head)
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","

    print("== File ==")
    print(f"path: {path}")
    print(f"size: {path.stat().st_size:,} bytes")
    print(f"encoding: {encoding}")
    print(f"BOM present: {has_bom}")
    print(f"delimiter: {delimiter!r}")
    print(f"header row index: {header_row}")

    print("\n== First 10 raw lines (repr shows hidden characters) ==")
    for i, line in enumerate(head):
        print(f"{i}: {line!r}")

    df = pd.read_csv(
        path,
        encoding=encoding,
        sep=delimiter,
        header=header_row,
        dtype=str,
        keep_default_na=False,
    )

    print("\n== Shape ==")
    print(f"rows: {len(df):,}")
    print(f"columns: {df.shape[1]}")

    print("\n== Column names (repr shows spaces and casing) ==")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col!r}")

    print("\n== Column profile ==")
    for col in df.columns:
        s = df[col]
        blank = int((s.str.strip() == "").sum())
        distinct = s.nunique()
        examples = [v for v in s.unique() if v.strip()][:3]
        print(f"{col!r}: blank={blank}, distinct={distinct}, examples={examples}")

    print("\n== Duplicate rows ==")
    print(f"exact duplicates: {int(df.duplicated().sum())}")

    print("\n== State / district / region columns ==")
    for col in df.columns:
        if tokens(col) & PLACE_TOKENS:
            counts = df[col].str.strip().value_counts()
            print(f"\n{col!r}: {len(counts)} distinct values")
            for value, n in counts.head(MAX_ITEMS).items():
                print(f"  {n:>7}  {value!r}")

    print("\n== Date-like columns: value shapes (9 = digit, a = letter) ==")
    for col in df.columns:
        if tokens(col) & DATE_TOKENS:
            shapes = df[col].map(shape).value_counts()
            print(f"\n{col!r}: {len(shapes)} distinct shapes")
            for pattern, n in shapes.head(MAX_ITEMS).items():
                print(f"  {n:>7}  {pattern!r}")


if __name__ == "__main__":
    main()