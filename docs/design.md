# Design decisions

## Scope

Version one standardizes one raw file: district-wise MGNREGA monthly data for Uttar Pradesh, FY 2018-19. It has 900 rows (75 districts × 12 months) and 36 columns. It contains one state, so state-name matching is out of scope for version one. The README must not claim otherwise.

## Natural key

`(period, district_code)`. The profile found zero duplicates on this key. The key uses `district_code` rather than `district_name`, because names are more likely to change between releases.

## Month handling

The profile found 12 complete month values, each with 75 rows. They appear in two forms: 3-letter abbreviations (Jan, Feb, May, Aug, Sep, Oct, Nov, Dec) and full names (March, April, June, July). The pipeline uses an explicit mapping of all 12 spellings. It does not use fuzzy matching, because the month set is closed. Any other spelling sends the row to quarantine.

## Period derivation

The financial year runs April to March. Months April through December fall in the first calendar year of the financial year. January through March fall in the second. Examples: Nov with 2018-2019 becomes 2018-11, and Feb with 2018-2019 becomes 2019-02. The April start is a fixed rule, written in code and covered by tests.

## Schema

`config/expected_schema.json` lists all 36 columns. Names are kept exactly as published, including the inconsistent casing and the misspelling `percentage_payments_gererated_within_15_days`. `state_code` and `district_code` are typed as strings so leading zeros survive.

## Failure behavior

- Column added: process the file normally. Leave the new column out of the output, since the output contract is fixed at 35 columns. Log the new column name and exit with code 3.
- Column renamed or missing: halt, quarantine the whole file, and log the difference with a suggested match.
- Unknown month spelling: quarantine that row.
- Duplicate natural key: quarantine every copy and log the count.
- Non-numeric value in a numeric column: quarantine that row with a reason.
- `Remarks`: all 900 values are `NA` in this release. Keep the column as text.
- Reordered columns: process normally, log the new order, exit 0. Columns are mapped by name, so the order doesn't change the output.
- Blank value in a measure column: quarantine the row with reason "blank measure value", exit 2. A blank is never written as zero.
- Ragged row (field count differs from the header): quarantine the row with reason "field count mismatch", exit 2. Field counts are checked before parsing, so pandas can't fill gaps silently.
- Layout not comma-separated, or header not on the first line: halt with a report naming the problem, exit 1. Nothing is guessed.

## Encoding

The pipeline accepts UTF-8 files, with or without a byte order mark (BOM). The BOM is removed on read, so it never reaches the output. Any other encoding halts the run with a report naming the problem. The pipeline doesn't guess encodings, because a wrong guess silently corrupts names. The raw file is plain ASCII, which is valid UTF-8, so it passes this rule.

## Open decisions

- **Drift testing on real data.** Drift detection needs a second release of this dataset. Until one is found, use a test fixture with one renamed column.


## Output contract

The pipeline writes one processed file per run, `data/processed/mgnrega_district_monthly_up.csv`, and overwrites it on each run. Running the pipeline twice on the same input must produce a byte-identical file.

**Columns, in this order (35 total):**
1. `period`: first day of the month in ISO format, such as `2018-11-01`. Derived from `fin_year` and `month` using the April rule.
2. `state_code`, `state_name`, `district_code`, `district_name`: as published. Codes stay strings.
3. The 29 measure columns, in raw-file order, with names unchanged.
4. `Remarks`: kept as text, unchanged.

`fin_year` and `month` are removed from the output because `period` replaces them. The raw file keeps both, so nothing is lost.

**Types:** codes and names are strings. Measures follow `config/expected_schema.json`: integer columns become `Int64`, decimal columns become `float64`, and no values are rounded. Decimal values are written in float64 form, so a whole number such as 3 appears as 3.0. The value is unchanged. Accepted for version one.

**Sort order:** `period` ascending, then `district_code` ascending. The output has no index column.

**Natural key:** `(period, district_code)`.

**Rejected rows** go to `data/quarantine/mgnrega_district_monthly_up_rejects.csv`. The file has `source_row` (the 1-based data row, excluding the header), `reject_reason`, and `raw_values` (the original fields joined by commas). `raw_values` is used because ragged rows don't map to columns. Each run deletes the old reject file first and writes a new one only if rows were rejected, so a stale file can't be mistaken for a current one.

**Halted runs:** any halt, whether from encoding, layout, or drift, deletes any existing processed output and writes `data/quarantine/mgnrega_district_monthly_up_halt_report.txt`, which names the problem.

**Exit codes:** 0 for a clean run, 1 for a halted run, 2 for a run that completed with rejected rows, 3 for a run that completed with a new column flagged.

**Run summary:** each run logs rows read, rows written, rows quarantined, and drift status.