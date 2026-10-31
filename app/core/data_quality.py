from pathlib import Path

import pandas as pd


def validate_csv(
    path: Path,
    required_columns: list[str],
) -> dict:
    """Validate a CSV file without modifying it."""

    if not path.exists():
        return {
            "status": "error",
            "file": str(path),
            "message": "File does not exist.",
        }

    try:
        df = pd.read_csv(path)

        normalized = {
            str(column).strip().casefold(): column
            for column in df.columns
        }

        missing = [
            column
            for column in required_columns
            if column.strip().casefold() not in normalized
        ]

        return {
            "status": "error" if missing else "success",
            "file": str(path),
            "rows": int(len(df)),
            "columns": list(df.columns),
            "missing_columns": missing,
            "duplicate_rows": int(df.duplicated().sum()),
            "message": (
                "Validation passed."
                if not missing
                else "Required columns are missing."
            ),
        }

    except Exception as exc:
        return {
            "status": "error",
            "file": str(path),
            "message": f"{type(exc).__name__}: {exc}",
        }


def validate_project_data() -> dict:
    """Validate the three company datasets and market therapeutic-group dataset."""

    from app.core.config import (
        COMPANY_FILE,
        GROUP_FILE,
        VALUE_UNIT_FILE,
        DATA_FOLDER,
    )

    return {
        "company_data": validate_csv(
            COMPANY_FILE,
            ["COMPANY", "VAL MAT SEP'25", "VAL MAT SEP'24", "Growth (%)"],
        ),
        "therapeutic_group_data": validate_csv(
            GROUP_FILE,
            ["COMPANY", "GROUP", "VAL MAT SEP'25", "VAL MAT SEP'24"],
        ),
        "value_unit_data": validate_csv(
            VALUE_UNIT_FILE,
            ["COMPANY", "VAL MAT SEP'25", "VAL MAT SEP'24", "CTUNT MAT SEP'25", "CTUNT MAT SEP'24"],
        ),
        "market_therapeutic_group_data": validate_csv(
            DATA_FOLDER / "IMS_Group_Analysis.csv",
            ["GROUP", "VAL MAT SEP'25", "VAL MAT SEP'24", "Growth (%)"],
        ),
    }
