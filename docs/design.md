# Design decisions

## Scope

Version one standardizes one raw file: district-wise MGNREGA monthly data for Uttar Pradesh, FY 2018-19. It has 900 rows (75 districts × 12 months) and 36 columns. It contains one state, so state-name matching is out of scope for version one. The README must not claim otherwise.

## Natural key

`(fin_year, month, district_code)`. The profile found zero duplicates on this key. The key uses `district_code` rather than `district_name`, because names are more likely to change between releases.

## Month handling

The profile found 12 complete month values, each with 75 rows. They appear in two forms: 3-letter abbreviations (Jan, Feb, May, Aug, Sep, Oct, Nov, Dec) and full names (March, April, June, July). The pipeline uses an explicit mapping of all 12 spellings. It does not use fuzzy matching, because the month set is closed. Any other spelling sends the row to quarantine.

## Period derivation

The financial year runs April to March. Months April through December fall in the first calendar year of the financial year. January through March fall in the second. Examples: Nov with 2018-2019 becomes 2018-11, and Feb with 2018-2019 becomes 2019-02. The April start is a fixed rule, written in code and covered by tests.

## Schema

`config/expected_schema.json` lists all 36 columns. Names are kept exactly as published, including the inconsistent casing and the misspelling `percentage_payments_gererated_within_15_days`. `state_code` and `district_code` are typed as strings so leading zeros survive.

## Failure behavior

- Column added: log it and flag the file.
- Column renamed or missing: halt, quarantine the whole file, and log the difference with a suggested match.
- Unknown month spelling: quarantine that row.
- Duplicate natural key: quarantine every copy and log the count.
- Non-numeric value in a numeric column: quarantine that row with a reason.
- `Remarks`: all 900 values are `NA` in this release. Keep the column as text.

## Open decisions

- **Drift testing on real data.** Drift detection needs a second release of this dataset. Until one is found, use a test fixture with one renamed column.
- **Multi-state data.** The project's stated problem includes misspelled state names, and this file doesn't show that. Decide whether to add a second, multi-state file before the README describes the project's full scope.