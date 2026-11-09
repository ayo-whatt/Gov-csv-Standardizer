# Government CSV Standardizer

A pipeline that cleans one messy government CSV file and refuses to load it silently when its structure changes. Every run either writes a standardized file, sets bad rows aside with a reason, or stops with a report, and returns an exit code that a scheduler can read.

## The problem

Open government datasets change without notice. Column names are inconsistent, values are spelled and formatted in more than one way, and a publisher can rename, add, or drop a column in a new release. A naive load keeps running and writes wrong data, so the problem goes unnoticed.

## Dataset

- **Dataset:** district-wise MGNREGA monthly data for Uttar Pradesh
- **Period:** financial year 2018-19 (April 2018 to March 2019)
- **Source, resource ID, download date, and license:** `data/SOURCES.md`
- **Raw file:** `data/raw/mgnrega_district_monthly_up_fy2018-19.csv`, kept unedited
- **Size:** 900 rows (75 districts × 12 months) and 36 columns

## What the pipeline does

Each run goes through five stages in order. A stage either passes its result to the next stage or stops the run with a reason.

1. **Read.** Decodes the file as UTF-8, with or without a byte order mark, and checks the layout: comma-separated, with the header on the first line. Any other encoding or layout halts the run. Rows whose field count differs from the header are set aside, not parsed.
2. **Check columns.** Compares column names with `config/expected_schema.json`, by name and never by position. A missing column halts the run, and the report suggests a likely rename. An added column is excluded from the output and flagged. A reordered column is accepted, because the output doesn't depend on column order.
3. **Validate rows.** Converts `fin_year` and `month` into `period`, a date for the first day of the month, using the April start of the financial year. Rows with an unknown month, a malformed financial year, a blank measure, or a non-numeric measure are quarantined with a reason.
4. **Check duplicates.** Every copy of a repeated `(period, district_code)` among the rows that passed step 3 is quarantined.
5. **Write.** Writes the standardized CSV and, when there are rejects, the quarantine file.

Each run deletes the previous run's output, quarantine, and halt files before it starts, so an old file can't be mistaken for a current result.

## Output

**Processed file:** `data/processed/mgnrega_district_monthly_up.csv`

- 35 columns: `period`, the four identifier columns, 29 measures, and `Remarks`.
- `fin_year` and `month` are replaced by `period`. The raw file keeps both.
- Natural key: `(period, district_code)`.
- Sorted by `period`, then `district_code`. No index column.
- Integer measures are written as whole numbers. Decimal measures are written as floats, so a whole value such as `3` appears as `3.0`. The value is unchanged.

**Quarantine file:** `data/quarantine/mgnrega_district_monthly_up_rejects.csv`

- One row per rejected input row, with `source_row` (the data row number, not counting the header), `reject_reason`, and `raw_values` (the original fields joined by commas).
- `raw_values` is the only place ragged rows keep their data, because they don't map to columns.
- Written only when rows are rejected.

**Halt report:** `data/quarantine/mgnrega_district_monthly_up_halt_report.txt`

- Written when a run stops at the read or column stage. It names the problem. No processed file is produced.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Clean run. No rows rejected, no new columns. |
| 1 | Halted at the read or column stage. No processed file written. |
| 2 | Completed, with one or more rows quarantined. |
| 3 | Completed, with a new column excluded from the output. |

If several outcomes apply, the most severe code is returned, in the order 1, 2, 3, 0. A run with rejected rows and a new column returns 2.

## Setup

Tested with Python 3.13. From the project root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Git Bash, activate with `source .venv/bin/activate`.

Dependencies:

- **pandas** reads the raw file and writes the output.
- **rapidfuzz** suggests likely column renames when the column check halts.
- **pytest** runs the test suite.
- **charset-normalizer** is used only by the profiling script.
- **python-dateutil**, **SQLAlchemy**, and **psycopg** are installed for planned steps. The pipeline doesn't import them yet.

## Running the pipeline

```powershell
python -m src.main data/raw/mgnrega_district_monthly_up_fy2018-19.csv
```

Run this from the project root. Two optional flags, `--processed-dir` and `--quarantine-dir`, change where the outputs are written. The run logs the rows read, written, and quarantined.

## Running the tests

```powershell
python -m pytest -v
```

The suite contains 17 tests covering each rule in `docs/design.md`. The broken test inputs are in `tests/fixtures/`. To regenerate them:

```powershell
python tests/make_broken_fixtures.py
```

## Profiling a raw file

```powershell
python src/profile_raw.py data/raw/mgnrega_district_monthly_up_fy2018-19.csv
```

This prints a report on a raw file's encoding, delimiter, column names, value counts, and date formats. It only reads the file. The report for the current file is saved in `docs/profile_output.txt`.

## Project structure

```
config/
  expected_schema.json
data/
  raw/                  input file, never edited
  processed/            pipeline output (not committed)
  quarantine/           rejected rows and reports (not committed)
  SOURCES.md
docs/
  design.md
  profile_output.txt
src/
  __init__.py
  config.py
  drift.py
  main.py
  profile_raw.py
  reader.py
  validate.py
  writer.py
tests/
  fixtures/
  make_broken_fixtures.py
  test_pipeline.py
pytest.ini
requirements.txt
README.md
```

## Design

The rules, their reasons, and the output contract are in `docs/design.md`. The code implements that document, and the tests check it. If the code and the design disagree, change the design first, then the code and tests.

## Limitations

- **One state.** Version one covers Uttar Pradesh only. Spelling variants of state names aren't handled, since this file has one state.
- **Drift is tested with a synthetic change.** The renamed-column case uses a fixture. The pipeline hasn't been run on a second release of this dataset yet.
- **Schema drift only.** Value-format changes are caught only where a row rule covers them, such as an unknown month or a non-numeric measure. There's no general check for value-format drift.
- **The layout check is simple.** It confirms the first line has more than one comma-separated field. A title line containing a comma would pass, and the column check would then halt the run.
- **Non-UTF-8 files halt.** They aren't converted. Re-export the file as UTF-8 first.
- **Duplicates are detected only among rows that pass the row checks.** If one copy of a duplicated key fails a row check, the other copy is written.
- **No database load yet.** The output is a CSV file only.

## Status

All rules in `docs/design.md` are implemented and tested. Two items remain: a drift test on a real second release, and the database load, which hasn't started.

## Planned, not built

- Load the output into PostgreSQL with upserts on `(period, district_code)`.
- Multi-state support, with canonical state names and spelling variants.
- A containerized Postgres setup with Docker Compose.
- Scheduled runs with cron, and later Airflow.