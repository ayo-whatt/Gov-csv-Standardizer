"""Stage 2: compare the file's columns with config/expected_schema.json.

Missing or renamed columns halt the run. Added columns are allowed but flagged.
Reordered columns are logged. Columns are matched by name, never by position.
"""
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from src.config import Halt


@dataclass
class Drift:
    added: list = field(default_factory=list)
    reordered: bool = False


def check_drift(header, schema_columns):
    expected = [c["name"] for c in schema_columns]
    added = [name for name in header if name not in expected]
    missing = [name for name in expected if name not in header]

    if missing:
        lines = ["drift: expected columns are missing from the file:"]
        for name in missing:
            hint = None
            if added:
                hint = process.extractOne(name, added, scorer=fuzz.WRatio, score_cutoff=70)
            note = f" (possibly renamed to '{hint[0]}')" if hint else ""
            lines.append(f"  - {name}{note}")
        if added:
            lines.append("columns not in the expected schema: " + ", ".join(added))
        raise Halt("\n".join(lines))

    known_in_file = [name for name in header if name in expected]
    return Drift(added=added, reordered=known_in_file != expected)
