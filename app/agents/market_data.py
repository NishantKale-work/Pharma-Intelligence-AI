
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT.parent / "IMS_Brand_Analysis.csv"


def load_brand_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")
    return pd.read_csv(DATA_FILE)



def get_brand_sales(brand_name, company=None):
    df = load_brand_data()
    requested = str(brand_name).strip().casefold()

    # The BRAND field appears to contain the product name and
    # company code together, separated by multiple spaces.
    brand_parts = (
        df["BRAND"].astype(str).str.strip()
        .str.split(r"\s{2,}", n=1, regex=True)
    )

    df = df.copy()
    df["_BRAND_NAME"] = brand_parts.str[0].str.strip()
    df["_COMPANY_CODE"] = brand_parts.str[1].fillna("").str.strip()

    matches = df[
        df["_BRAND_NAME"].str.casefold() == requested
    ].copy()

    if company:
        company_key = str(company).strip().casefold()
        matches = matches[
            matches["COMPANY"].astype(str).str.strip().str.casefold().eq(company_key)
            | matches["_COMPANY_CODE"].str.casefold().eq(company_key)
        ]

    if matches.empty:
        return {
            "status": "not_found",
            "brand": brand_name,
            "message": "No exact brand-name match found.",
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "brand": brand_name,
            "matches": matches[
                ["_BRAND_NAME", "_COMPANY_CODE", "COMPANY"]
            ].head(10).to_dict(orient="records"),
            "message": "Multiple matches found. Provide a company name or code.",
        }

    row = matches.iloc[0]
    previous = float(row["VAL MAT SEP'24"])
    current = float(row["VAL MAT SEP'25"])
    change = current - previous

    growth = (
        None if previous == 0
        else round(change / previous * 100, 2)
    )

    return {
        "status": "success",
        "brand_name": row["_BRAND_NAME"],
        "company_code": row["_COMPANY_CODE"],
        "company_name": row["COMPANY"],
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "previous_sales": previous,
        "current_sales": current,
        "sales_change": round(change, 6),
        "growth_percent": growth,
        "growth_status": (
            "undefined_zero_baseline" if previous == 0
            else "growth" if change > 0
            else "decline" if change < 0
            else "no_change"
        ),
        "data_source": str(DATA_FILE),
    }


    # First, search all columns for an exact match.
    matching_rows = pd.Series(False, index=df.index)

    for column in df.columns:
        matching_rows |= (
            df[column].astype(str).str.strip().str.casefold()
            == requested
        )

    matches = df[matching_rows].copy()

    if company and "COMPANY" in matches.columns:
        matches = matches[
            matches["COMPANY"].astype(str).str.strip().str.casefold()
            == str(company).strip().casefold()
        ]

    if matches.empty:
        return {
            "status": "not_found",
            "brand": brand_name,
            "message": "No exact match found in any CSV column.",
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "brand": brand_name,
            "matches": matches.head(10).to_dict(orient="records"),
            "message": "Multiple matching rows found.",
        }

    row = matches.iloc[0]

    previous = float(row["VAL MAT SEP'24"])
    current = float(row["VAL MAT SEP'25"])
    change = current - previous

    growth = (
        None if previous == 0
        else round(change / previous * 100, 2)
    )

    return {
        "status": "success",
        "matched_row": row.to_dict(),
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "previous_sales": previous,
        "current_sales": current,
        "sales_change": round(change, 6),
        "growth_percent": growth,
        "growth_status": (
            "undefined_zero_baseline" if previous == 0
            else "growth" if change > 0
            else "decline" if change < 0
            else "no_change"
        ),
        "data_source": str(DATA_FILE),
    }


if __name__ == "__main__":
    print("Dataset:", DATA_FILE)

    df = load_brand_data()
    print("\nColumns:", df.columns.tolist())
    print("Rows loaded:", len(df))
    print("\nFirst 5 rows:")
    print(df.head().to_string())

    print("\nSearching all columns for 1-AL:")
    result = get_brand_sales("1-AL")
    print(result)
