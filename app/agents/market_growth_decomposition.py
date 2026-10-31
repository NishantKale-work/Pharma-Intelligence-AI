"""Market-growth decomposition using the supplied IMS MAT datasets.

This module reports arithmetic relationships, not causal explanations.
It reads source CSVs only; it never edits them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import COMPANY_FILE, DATA_FOLDER, DATA_PERIOD


MARKET_GROUP_FILE = DATA_FOLDER / "IMS_Group_Analysis.csv"

VALUE_2025 = "VAL MAT SEP'25"
VALUE_2024 = "VAL MAT SEP'24"


def _finite(value: Any) -> float | None:
    try:
        number = float(value)

        if pd.isna(number) or number in (float("inf"), float("-inf")):
            return None

        return number

    except (TypeError, ValueError):
        return None


def _read_sales_totals(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{label} dataset not found: {path}")

    df = pd.read_csv(path)

    missing = [
        column
        for column in (VALUE_2024, VALUE_2025)
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"{label} dataset is missing columns: {missing}")

    prior = pd.to_numeric(df[VALUE_2024], errors="coerce")
    current = pd.to_numeric(df[VALUE_2025], errors="coerce")

    if prior.isna().any() or current.isna().any():
        raise ValueError(
            f"{label} dataset contains missing or non-numeric sales values."
        )

    prior_total = float(prior.sum())
    current_total = float(current.sum())

    if prior_total <= 0:
        raise ValueError(f"{label} prior-period market total must be positive.")

    change = current_total - prior_total
    growth = (change / prior_total) * 100

    return {
        "source": path.name,
        "rows": int(len(df)),
        "sales_2024": prior_total,
        "sales_2025": current_total,
        "sales_change": change,
        "growth_percent": growth,
    }


def build_market_growth_decomposition(company: str = "ALKEM*") -> dict:
    """Compare company growth with total-market growth and quantify the gap."""

    if not isinstance(company, str) or not company.strip():
        return {
            "status": "error",
            "message": "Please provide a company name.",
        }

    try:
        market = _read_sales_totals(
            MARKET_GROUP_FILE,
            "Market therapeutic-group",
        )

        company_df = pd.read_csv(COMPANY_FILE)

        required = {"COMPANY", VALUE_2024, VALUE_2025}

        if not required.issubset(company_df.columns):
            missing = sorted(required - set(company_df.columns))
            raise ValueError(
                f"Company dataset is missing columns: {missing}"
            )

        names = (
            company_df["COMPANY"]
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        matches = company_df[
            names == company.strip().casefold()
        ]

        if matches.empty:
            return {
                "status": "error",
                "message": (
                    f"Company '{company}' was not found in "
                    f"{COMPANY_FILE.name}."
                ),
                "available_match_hint": (
                    "Use the company label exactly as it appears in the "
                    "dataset (for example, ALKEM*)."
                ),
            }

        if len(matches) > 1:
            return {
                "status": "error",
                "message": (
                    f"Company '{company}' has {len(matches)} matching rows; "
                    "company-level decomposition requires one row."
                ),
            }

        row = matches.iloc[0]

        company_2024 = _finite(row[VALUE_2024])
        company_2025 = _finite(row[VALUE_2025])

        if (
            company_2024 is None
            or company_2025 is None
            or company_2024 <= 0
        ):
            raise ValueError(
                "Company sales must be finite and prior-period sales "
                "must be positive."
            )

        company_change = company_2025 - company_2024
        company_growth = company_change / company_2024 * 100

        market_growth = market["growth_percent"]
        growth_gap = company_growth - market_growth

        expected_company_sales = company_2024 * (
            1 + market_growth / 100
        )

        sales_shortfall_vs_market_growth = (
            expected_company_sales - company_2025
        )

        market_share_2024 = (
            company_2024 / market["sales_2024"] * 100
        )

        market_share_2025 = (
            company_2025 / market["sales_2025"] * 100
        )

        share_change = market_share_2025 - market_share_2024
        market_increment = market["sales_change"]

        company_contribution_to_market_increment = (
            company_change / market_increment * 100
            if market_increment
            else None
        )

        # Cross-check the market-group total against the company-file aggregate.
        company_file_totals = _read_sales_totals(
            COMPANY_FILE,
            "Company",
        )

        reconciliation = {
            "company_file_market_sales_2024": (
                company_file_totals["sales_2024"]
            ),
            "company_file_market_sales_2025": (
                company_file_totals["sales_2025"]
            ),
            "market_group_sales_2024": market["sales_2024"],
            "market_group_sales_2025": market["sales_2025"],
            "sales_2024_difference": (
                company_file_totals["sales_2024"]
                - market["sales_2024"]
            ),
            "sales_2025_difference": (
                company_file_totals["sales_2025"]
                - market["sales_2025"]
            ),
            "reconciles_within_tolerance": (
                abs(
                    company_file_totals["sales_2024"]
                    - market["sales_2024"]
                ) < 1e-6
                and abs(
                    company_file_totals["sales_2025"]
                    - market["sales_2025"]
                ) < 1e-6
            ),
        }

        return {
            "status": "success",
            "report_type": "Market Growth Decomposition",
            "company": str(row["COMPANY"]),
            "data_period": DATA_PERIOD,
            "market": market,
            "company_performance": {
                "sales_2024": company_2024,
                "sales_2025": company_2025,
                "sales_change": company_change,
                "growth_percent": company_growth,
                "market_share_2024_percent": market_share_2024,
                "market_share_2025_percent": market_share_2025,
                "share_change_percentage_points": share_change,
            },
            "decomposition": {
                "market_growth_percent": market_growth,
                "company_growth_percent": company_growth,
                "growth_gap_percentage_points": growth_gap,
                "expected_company_sales_at_market_growth": (
                    expected_company_sales
                ),
                "actual_company_sales_2025": company_2025,
                "sales_gap_vs_market_growth": (
                    sales_shortfall_vs_market_growth
                ),
                "company_contribution_to_market_sales_increment_percent": (
                    company_contribution_to_market_increment
                ),
            },
            "reconciliation": reconciliation,
            "interpretation": [
                (
                    f"Company sales grew {company_growth:.2f}% versus "
                    f"market growth of {market_growth:.2f}%, a gap of "
                    f"{growth_gap:.2f} percentage points."
                ),
                (
                    "At the market growth rate, company sales would have "
                    f"been approximately {expected_company_sales:.2f}; "
                    f"actual sales were {company_2025:.2f}."
                ),
                (
                    "The growth gap is a descriptive comparison, not a "
                    "causal explanation of the company's performance."
                ),
            ],
            "limitations": [
                (
                    "The market total is calculated by summing rows in "
                    "IMS_Group_Analysis.csv."
                ),
                (
                    "The market and company datasets must cover the same "
                    "market scope and reporting period for a valid comparison."
                ),
                (
                    "The sales gap versus market growth is a counterfactual "
                    "benchmark, not an estimate of recoverable sales."
                ),
                (
                    "This analysis does not identify causal drivers such as "
                    "price, mix, distribution, demand, supply or portfolio changes."
                ),
            ],
            "data_sources": [
                COMPANY_FILE.name,
                MARKET_GROUP_FILE.name,
            ],
        }

    except Exception as exc:
        return {
            "status": "error",
            "report_type": "Market Growth Decomposition",
            "company": company,
            "message": f"{type(exc).__name__}: {exc}",
        }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            build_market_growth_decomposition(),
            indent=2,
            default=str,
        )
    )