"""Entry point. Runs the stages in order and returns one exit code.

Run from the project root:
    python -m src.main data/raw/mgnrega_district_monthly_up_fy2018-19.csv

Exit codes, highest severity wins (1 > 2 > 3 > 0):
    0 clean, 1 halted, 2 completed with rejected rows, 3 new column flagged
"""
import argparse
import logging
import sys
from pathlib import Path

from src.config import (
    EXIT_HALTED, EXIT_NEW_COLUMN, EXIT_OK, EXIT_REJECTS,
    ROOT, SCHEMA_PATH, Halt, load_schema,
)
from src.drift import check_drift
from src.reader import read_raw
from src.validate import validate
from src.writer import (
    build_output, clear_outputs, write_halt_report, write_processed, write_rejects,
)

log = logging.getLogger("pipeline")


def run(input_path, processed_dir, quarantine_dir, schema_path=SCHEMA_PATH):
    processed_dir, quarantine_dir = Path(processed_dir), Path(quarantine_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    clear_outputs(processed_dir, quarantine_dir)

    schema = load_schema(schema_path)
    try:
        raw = read_raw(Path(input_path))
        drift = check_drift(raw.header, schema)
    except Halt as halt:
        write_halt_report(quarantine_dir, str(halt))
        log.error("halted: %s", str(halt).splitlines()[0])
        return EXIT_HALTED

    kept, row_rejects = validate(raw.header, raw.rows, schema)
    rejects = [(row, "field count mismatch", fields) for row, fields in raw.ragged]
    rejects += row_rejects

    if drift.reordered:
        log.info("columns reordered; matched by name, output unchanged")
    if drift.added:
        log.warning("columns not in schema, excluded from output: %s", ", ".join(drift.added))

    output = build_output(kept, schema)
    write_processed(processed_dir, output)
    write_rejects(quarantine_dir, rejects)

    read_count = len(raw.rows) + len(raw.ragged)
    log.info("rows read: %d, written: %d, quarantined: %d", read_count, len(output), len(rejects))

    if rejects:
        return EXIT_REJECTS
    if drift.added:
        return EXIT_NEW_COLUMN
    return EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(description="Standardize the MGNREGA district CSV.")
    parser.add_argument("input_path")
    parser.add_argument("--processed-dir", default=str(ROOT / "data" / "processed"))
    parser.add_argument("--quarantine-dir", default=str(ROOT / "data" / "quarantine"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run(args.input_path, args.processed_dir, args.quarantine_dir)


if __name__ == "__main__":
    sys.exit(main())
    