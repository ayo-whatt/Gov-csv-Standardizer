"""Shared constants, exit codes, and the Halt exception."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "config" / "expected_schema.json"

PROCESSED_NAME = "mgnrega_district_monthly_up.csv"
REJECTS_NAME = "mgnrega_district_monthly_up_rejects.csv"
HALT_REPORT_NAME = "mgnrega_district_monthly_up_halt_report.txt"

# The 12 month spellings observed in the raw file. "Sept" is absent on purpose:
# an unlisted spelling is quarantined, never guessed.
MONTHS = {
    "Jan": 1, "Feb": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

IDENTIFIERS = ["state_code", "state_name", "district_code", "district_name"]
NOT_MEASURES = {"fin_year", "month", "Remarks", *IDENTIFIERS}

EXIT_OK = 0
EXIT_HALTED = 1
EXIT_REJECTS = 2
EXIT_NEW_COLUMN = 3


class Halt(Exception):
    """Raised when a run must stop. The message becomes the halt report."""


def load_schema(path=SCHEMA_PATH):
    """Return the list of {name, type} entries from the expected schema."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)["columns"]