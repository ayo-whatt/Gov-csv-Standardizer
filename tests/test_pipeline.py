"""Tests for every rule in docs/design.md.

Each test runs the full pipeline on one input and checks the exit code and
the output, quarantine, or halt report it produces.
"""
from pathlib import Path

import pandas as pd

from src.config import (
    EXIT_HALTED, EXIT_NEW_COLUMN, EXIT_OK, EXIT_REJECTS,
    HALT_REPORT_NAME, PROCESSED_NAME, REJECTS_NAME,
)
from src.main import run

FIXTURES = Path(__file__).parent / "fixtures"
CLEAN = FIXTURES / "clean_sample.csv"
EXPECTED_PERIODS = (
    [f"2018-{m:02d}-01" for m in range(4, 13)]
    + [f"2019-{m:02d}-01" for m in range(1, 4)]
)


def read_csv_text(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def write_variant(tmp_path, name, content):
    """Write a test input under tmp_path/input. Accepts a DataFrame or raw text."""
    path = tmp_path / "input" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, pd.DataFrame):
        content.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    else:
        path.write_text(content, encoding="utf-8", newline="\n")
    return path


def run_on(path, tmp_path):
    processed = tmp_path / "output" / "processed"
    quarantine = tmp_path / "output" / "quarantine"
    code = run(path, processed, quarantine)
    return code, processed, quarantine


def read_rejects(quarantine):
    return read_csv_text(quarantine / REJECTS_NAME)


def nov_3112_variant(tmp_path, name, column, value):
    df = read_csv_text(CLEAN)
    mask = (df["month"] == "Nov") & (df["district_code"] == "3112")
    df.loc[mask, column] = value
    return write_variant(tmp_path, name, df)


# --- Clean path -------------------------------------------------------------

def test_clean_baseline_passes(tmp_path):
    code, processed, _ = run_on(CLEAN, tmp_path)
    assert code == EXIT_OK
    out = read_csv_text(processed / PROCESSED_NAME)
    assert len(out) == 24
    assert len(out.columns) == 35
    assert list(out.columns[:6]) == [
        "period", "state_code", "state_name", "district_code", "district_name",
        "Approved_Labour_Budget",
    ]
    assert out.columns[-1] == "Remarks"


def test_period_follows_april_start(tmp_path):
    _, processed, _ = run_on(CLEAN, tmp_path)
    out = read_csv_text(processed / PROCESSED_NAME)
    periods = sorted(out.loc[out["district_code"] == "3112", "period"])
    assert periods == EXPECTED_PERIODS


def test_output_is_byte_identical_across_runs(tmp_path):
    _, first, _ = run_on(CLEAN, tmp_path / "a")
    _, second, _ = run_on(CLEAN, tmp_path / "b")
    assert (first / PROCESSED_NAME).read_bytes() == (second / PROCESSED_NAME).read_bytes()


def test_bom_file_accepted(tmp_path):
    code, processed, _ = run_on(FIXTURES / "bom_utf8.csv", tmp_path)
    assert code == EXIT_OK
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 24


# --- Encoding and layout (halt) ---------------------------------------------

def test_non_utf8_halts(tmp_path):
    code, processed, quarantine = run_on(FIXTURES / "cp1252_accented.csv", tmp_path)
    assert code == EXIT_HALTED
    assert not (processed / PROCESSED_NAME).exists()
    assert "encoding" in (quarantine / HALT_REPORT_NAME).read_text(encoding="utf-8")


def test_semicolon_layout_halts(tmp_path):
    text = CLEAN.read_text(encoding="utf-8").replace(",", ";")
    code, _, quarantine = run_on(write_variant(tmp_path, "semicolon.csv", text), tmp_path)
    assert code == EXIT_HALTED
    assert "layout" in (quarantine / HALT_REPORT_NAME).read_text(encoding="utf-8")


def test_header_not_on_first_line_halts(tmp_path):
    text = "MGNREGA district report UP\n" + CLEAN.read_text(encoding="utf-8")
    code, _, quarantine = run_on(write_variant(tmp_path, "title_line.csv", text), tmp_path)
    assert code == EXIT_HALTED
    assert "layout" in (quarantine / HALT_REPORT_NAME).read_text(encoding="utf-8")


# --- Drift ------------------------------------------------------------------

def test_added_column_flagged_and_excluded(tmp_path):
    code, processed, _ = run_on(FIXTURES / "added_column.csv", tmp_path)
    assert code == EXIT_NEW_COLUMN
    out = read_csv_text(processed / PROCESSED_NAME)
    assert len(out) == 24
    assert "Extra_Note" not in out.columns


def test_renamed_column_halts_with_suggestion(tmp_path):
    code, processed, quarantine = run_on(FIXTURES / "renamed_column.csv", tmp_path)
    assert code == EXIT_HALTED
    assert not (processed / PROCESSED_NAME).exists()
    report = (quarantine / HALT_REPORT_NAME).read_text(encoding="utf-8")
    assert "Total_Exp" in report
    assert "Total_Expenditure" in report


def test_missing_column_halts(tmp_path):
    code, _, quarantine = run_on(FIXTURES / "missing_column.csv", tmp_path)
    assert code == EXIT_HALTED
    assert "Remarks" in (quarantine / HALT_REPORT_NAME).read_text(encoding="utf-8")


def test_reordered_columns_pass_with_identical_output(tmp_path):
    _, base_processed, _ = run_on(CLEAN, tmp_path / "base")
    df = read_csv_text(CLEAN)
    reordered = write_variant(tmp_path, "reordered.csv", df[df.columns[::-1]])
    code, processed, _ = run_on(reordered, tmp_path / "reordered_run")
    assert code == EXIT_OK
    pd.testing.assert_frame_equal(
        read_csv_text(processed / PROCESSED_NAME),
        read_csv_text(base_processed / PROCESSED_NAME),
    )


# --- Row rules (quarantine) -------------------------------------------------

def test_unknown_month_quarantined(tmp_path):
    path = nov_3112_variant(tmp_path, "unknown_month.csv", "month", "Sept")
    code, processed, quarantine = run_on(path, tmp_path)
    assert code == EXIT_REJECTS
    rejects = read_rejects(quarantine)
    assert len(rejects) == 1
    assert "unknown month" in rejects.loc[0, "reject_reason"]
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 23


def test_duplicate_key_quarantines_every_copy(tmp_path):
    df = read_csv_text(CLEAN)
    dup = df[(df["month"] == "Nov") & (df["district_code"] == "3112")].copy()
    dup["Wages"] = "1"
    path = write_variant(tmp_path, "duplicate_key.csv", pd.concat([df, dup], ignore_index=True))
    code, processed, quarantine = run_on(path, tmp_path)
    assert code == EXIT_REJECTS
    rejects = read_rejects(quarantine)
    assert len(rejects) == 2
    assert set(rejects["reject_reason"]) == {"duplicate natural key (period, district_code)"}
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 23


def test_non_numeric_quarantined(tmp_path):
    path = nov_3112_variant(tmp_path, "non_numeric.csv", "Wages", "--")
    code, processed, quarantine = run_on(path, tmp_path)
    assert code == EXIT_REJECTS
    assert "non-numeric value in Wages" in read_rejects(quarantine).loc[0, "reject_reason"]
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 23


def test_blank_measure_quarantined(tmp_path):
    path = nov_3112_variant(tmp_path, "blank.csv", "Wages", "")
    code, processed, quarantine = run_on(path, tmp_path)
    assert code == EXIT_REJECTS
    assert read_rejects(quarantine).loc[0, "reject_reason"] == "blank measure value"
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 23


def test_ragged_row_quarantined(tmp_path):
    lines = CLEAN.read_text(encoding="utf-8").splitlines()
    lines[3] += ",extra"  # data row 3 now has one field too many
    path = write_variant(tmp_path, "ragged.csv", "\n".join(lines) + "\n")
    code, processed, quarantine = run_on(path, tmp_path)
    assert code == EXIT_REJECTS
    rejects = read_rejects(quarantine)
    assert len(rejects) == 1
    assert rejects.loc[0, "source_row"] == "3"
    assert rejects.loc[0, "reject_reason"] == "field count mismatch"
    assert len(read_csv_text(processed / PROCESSED_NAME)) == 23


# --- Run hygiene ------------------------------------------------------------

def test_stale_outputs_are_removed(tmp_path):
    lines = CLEAN.read_text(encoding="utf-8").splitlines()
    lines[3] += ",extra"
    bad = write_variant(tmp_path, "ragged.csv", "\n".join(lines) + "\n")
    run_on(bad, tmp_path)
    code, _, quarantine = run_on(CLEAN, tmp_path)
    assert code == EXIT_OK
    assert not (quarantine / REJECTS_NAME).exists()
    