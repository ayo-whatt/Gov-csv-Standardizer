"""Stage 1: decode the file, check its layout, and split rows by field count.

Halts on encoding or layout problems. Rows with the wrong number of fields are
returned separately so they can be quarantined instead of parsed.
"""
import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from src.config import Halt


@dataclass
class RawFile:
    header: list
    rows: list = field(default_factory=list)    # (source_row, fields), correct width
    ragged: list = field(default_factory=list)  # (source_row, fields), wrong width


def read_raw(path: Path) -> RawFile:
    try:
        data = path.read_bytes()
    except OSError as err:
        raise Halt(f"input: cannot read {path} ({err})") from err

    try:
        # utf-8-sig accepts the file with or without a byte order mark and strips it.
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise Halt(
            f"encoding: file is not UTF-8 (first invalid byte at offset {err.start}). "
            "The file was not guessed at; re-export it as UTF-8."
        ) from err

    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as err:
        raise Halt(f"layout: file could not be parsed as CSV ({err})") from err

    if not rows:
        raise Halt("layout: file is empty")
    header = rows[0]
    if len(header) < 2:
        raise Halt(
            "layout: the first line is not a comma-separated header. "
            "Expected the column names on line 1, separated by commas."
        )

    raw = RawFile(header=header)
    for source_row, fields in enumerate(rows[1:], start=1):
        target = raw.rows if len(fields) == len(header) else raw.ragged
        target.append((source_row, fields))
    return raw
