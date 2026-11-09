"""Stage 4: build the output table and write the output files.

Every run first deletes all three output files, so a stale file from an
earlier run can never be mistaken for the current result.
"""
import pandas as pd

from src.config import (
    HALT_REPORT_NAME, IDENTIFIERS, NOT_MEASURES, PROCESSED_NAME, REJECTS_NAME,
)


def output_columns(schema_columns):
    measures = [c["name"] for c in schema_columns if c["name"] not in NOT_MEASURES]
    return ["period", *IDENTIFIERS, *measures, "Remarks"]


def build_output(kept, schema_columns):
    types = {c["name"]: c["type"] for c in schema_columns}
    columns = output_columns(schema_columns)
    df = pd.DataFrame([record for _, _, record in kept], columns=columns)
    for name in columns:
        if types.get(name) == "integer":
            df[name] = pd.to_numeric(df[name]).astype("Int64")
        elif types.get(name) == "decimal":
            df[name] = pd.to_numeric(df[name]).astype("float64")
    return df.sort_values(["period", "district_code"]).reset_index(drop=True)


def clear_outputs(processed_dir, quarantine_dir):
    for path in (
        processed_dir / PROCESSED_NAME,
        quarantine_dir / REJECTS_NAME,
        quarantine_dir / HALT_REPORT_NAME,
    ):
        path.unlink(missing_ok=True)


def write_processed(processed_dir, df):
    df.to_csv(processed_dir / PROCESSED_NAME, index=False, encoding="utf-8", lineterminator="\n")


def write_rejects(quarantine_dir, rejects):
    if not rejects:
        return
    df = pd.DataFrame(
        [
            {"source_row": row, "reject_reason": reason, "raw_values": ",".join(fields)}
            for row, reason, fields in sorted(rejects, key=lambda item: item[0])
        ]
    )
    df.to_csv(quarantine_dir / REJECTS_NAME, index=False, encoding="utf-8", lineterminator="\n")


def write_halt_report(quarantine_dir, message):
    (quarantine_dir / HALT_REPORT_NAME).write_text(message + "\n", encoding="utf-8")
    