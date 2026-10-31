
from pathlib import Path
import math
import pandas as pd


from pathlib import Path
import math
import pandas as pd

from app.core.config import (
    DATA_FOLDER,
    COMPANY_FILE,
    GROUP_FILE,
    VALUE_UNIT_FILE,
)
# ============================================================
# HELPER FUNCTIONS
# ============================================================

def finite_number(value, decimals=4):
    """Convert a value to a finite rounded number, or None."""
    number = pd.to_numeric(value, errors="coerce")

    if pd.isna(number):
        return None

    number = float(number)

    if not math.isfinite(number):
        return None

    return round(number, decimals)


def load_company_data():
    """Load existing company-level IMS analysis."""
    if not COMPANY_FILE.exists():
        raise FileNotFoundError(
            f"Company analysis file not found: {COMPANY_FILE}"
        )

    df = pd.read_csv(COMPANY_FILE)
    df.columns = df.columns.astype(str).str.strip()

    required = [
        "COMPANY",
        "VAL MAT SEP'25",
        "VAL MAT SEP'24",
        "Sales Change",
        "Growth (%)",
        "Market Share 2025 (%)",
        "Market Share 2024 (%)",
        "Share Change (pp)",
        "Contribution to Market Growth (%)",
        "Competitive Category",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            f"Missing company columns: {missing}"
        )

    df["COMPANY"] = df["COMPANY"].astype(str).str.strip()

    return df


# ============================================================
# COMPANY LOOKUP
# ============================================================

def find_company(company_name):
    """Find a company by its exact name, ignoring capitalization."""
    if not str(company_name).strip():
        return {
            "status": "invalid_input",
            "message": "Please provide a company name.",
        }

    df = load_company_data()
    requested = str(company_name).strip().casefold()

    matches = df[
        df["COMPANY"].str.casefold() == requested
    ].copy()

    if matches.empty:
        suggestions = df[
            df["COMPANY"].str.contains(
                str(company_name).strip(),
                case=False,
                regex=False,
                na=False,
            )
        ]["COMPANY"].head(10).tolist()

        return {
            "status": "not_found",
            "company": company_name,
            "suggestions": suggestions,
            "message": "No exact company match found.",
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "company": company_name,
            "matches": matches["COMPANY"].tolist(),
            "message": "Multiple matching records found.",
        }

    row = matches.iloc[0]

    return {
        "status": "success",
        "company": row["COMPANY"],
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "sales_2025": finite_number(row["VAL MAT SEP'25"]),
        "sales_2024": finite_number(row["VAL MAT SEP'24"]),
        "sales_change": finite_number(row["Sales Change"]),
        "growth_percent": finite_number(row["Growth (%)"]),

        # These values are already expressed as percentages
        # in the source file. Do not multiply them by 100.
        "market_share_2025_percent": finite_number(
            row["Market Share 2025 (%)"]
        ),
        "market_share_2024_percent": finite_number(
            row["Market Share 2024 (%)"]
        ),
        "share_change_percentage_points": finite_number(
            row["Share Change (pp)"]
        ),
        "contribution_to_market_growth_percent": finite_number(
            row["Contribution to Market Growth (%)"]
        ),
        "competitive_category": row["Competitive Category"],
        "data_source": str(COMPANY_FILE),
    }


# ============================================================
# COMPANY RANKINGS
# ============================================================

def top_companies(limit=10, sort_by="sales"):
    """
    Rank companies by sales, growth, or market share.

    sort_by options:
        sales
        growth
        market_share
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError("Limit must be an integer between 1 and 100.")

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    sort_columns = {
        "sales": "VAL MAT SEP'25",
        "growth": "Growth (%)",
        "market_share": "Market Share 2025 (%)",
    }

    if sort_by not in sort_columns:
        raise ValueError(
            "sort_by must be 'sales', 'growth', or 'market_share'."
        )

    df = load_company_data()
    column = sort_columns[sort_by]

    df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=[column])

    # Growth can be infinite when previous-year sales were zero.
    if sort_by == "growth":
        df = df[df[column].map(math.isfinite)]

    df = df.sort_values(column, ascending=False).head(limit)

    companies = []

    for _, row in df.iterrows():
        companies.append({
            "company": row["COMPANY"],
            "sales_2025": finite_number(row["VAL MAT SEP'25"]),
            "sales_2024": finite_number(row["VAL MAT SEP'24"]),
            "sales_change": finite_number(row["Sales Change"]),
            "growth_percent": finite_number(row["Growth (%)"]),
            "market_share_2025_percent": finite_number(
                row["Market Share 2025 (%)"]
            ),
            "competitive_category": row["Competitive Category"],
        })

    return {
        "status": "success",
        "ranking": sort_by,
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "companies": companies,
        "data_source": str(COMPANY_FILE),
    }


# ============================================================
# COMPANY PERFORMANCE BY THERAPEUTIC GROUP
# ============================================================

def company_group_analysis(company_name, limit=20):
    """
    Analyze all therapeutic groups and return ranked subsets.

    ``groups`` remains the top ``limit`` groups by current-period
    sales for compatibility with existing callers.

    Separate full-dataset rankings expose growth contributors,
    declining groups, and the fastest-growing groups so declines
    are not hidden by the sales ranking.

    Contribution percentages use company-level net sales change
    as the denominator. They are undefined when company net sales
    change is zero or unavailable.
    """
    if not GROUP_FILE.exists():
        raise FileNotFoundError(
            f"Group analysis file not found: {GROUP_FILE}"
        )

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError("Limit must be a positive integer.")

    if limit < 1:
        raise ValueError("Limit must be a positive integer.")

    df = pd.read_csv(GROUP_FILE)
    df.columns = df.columns.astype(str).str.strip()

    required = [
        "COMPANY",
        "GROUP",
        "VAL MAT SEP'25",
        "VAL MAT SEP'24",
        "Sales Change",
        "Growth (%)",
    ]

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing group-analysis columns: {missing}"
        )

    df["COMPANY"] = df["COMPANY"].astype(str).str.strip()

    requested = str(company_name).strip().casefold()

    matches = df[
        df["COMPANY"].str.casefold() == requested
    ].copy()

    if matches.empty:
        return {
            "status": "not_found",
            "company": company_name,
            "message": (
                "No exact company match found in group analysis."
            ),
        }

    numeric_columns = [
        "VAL MAT SEP'25",
        "VAL MAT SEP'24",
        "Sales Change",
        "Growth (%)",
    ]

    for column in numeric_columns:
        matches[column] = pd.to_numeric(
            matches[column],
            errors="coerce",
        )

    # Derive sales change from period values only when the source
    # Sales Change value is missing.
    derived_change = (
        matches["VAL MAT SEP'25"] -
        matches["VAL MAT SEP'24"]
    )

    matches["Sales Change"] = matches["Sales Change"].where(
        matches["Sales Change"].notna(),
        derived_change,
    )

    # Retrieve the company's net sales change for the denominator.
    company_result = find_company(
        matches.iloc[0]["COMPANY"]
    )

    company_net_change = None

    if (
        isinstance(company_result, dict)
        and company_result.get("status") == "success"
    ):
        company_net_change = finite_number(
            company_result.get("sales_change")
        )

        # Fallback to period sales if Sales Change is unavailable.
        if company_net_change is None:
            company_sales_2025 = finite_number(
                company_result.get("sales_2025")
            )

            company_sales_2024 = finite_number(
                company_result.get("sales_2024")
            )

            if (
                company_sales_2025 is not None
                and company_sales_2024 is not None
            ):
                company_net_change = finite_number(
                    company_sales_2025 - company_sales_2024
                )

    def record(row):
        sales_change = finite_number(row["Sales Change"])

        contribution = None

        if (
            company_net_change not in (None, 0)
            and sales_change is not None
        ):
            contribution = finite_number(
                (sales_change / company_net_change) * 100
            )

        return {
            "group": str(row["GROUP"]).strip(),
            "sales_2025": finite_number(
                row["VAL MAT SEP'25"]
            ),
            "sales_2024": finite_number(
                row["VAL MAT SEP'24"]
            ),
            "sales_change": sales_change,
            "growth_percent": finite_number(
                row["Growth (%)"]
            ),
            "contribution_to_company_net_sales_change_percent":
                contribution,
        }

    all_records = [
        record(row)
        for _, row in matches.iterrows()
    ]

    all_records = [
        item for item in all_records
        if item["group"]
    ]

    # Rank every therapeutic group by 2025 sales.
    by_sales = sorted(
        all_records,
        key=lambda item: (
            item["sales_2025"]
            if item["sales_2025"] is not None
            else float("-inf")
        ),
        reverse=True,
    )

    # Include every group with positive sales change.
    growth_contributors = sorted(
        (
            item for item in all_records
            if (
                item["sales_change"] is not None
                and item["sales_change"] > 0
            )
        ),
        key=lambda item: item["sales_change"],
        reverse=True,
    )

    # Include every group with negative sales change.
    declining_groups = sorted(
        (
            item for item in all_records
            if (
                item["sales_change"] is not None
                and item["sales_change"] < 0
            )
        ),
        key=lambda item: item["sales_change"],
    )

    # Rank groups by positive growth percentage.
    fastest_growing = sorted(
        (
            item for item in all_records
            if (
                item["growth_percent"] is not None
                and item["growth_percent"] > 0
            )
        ),
        key=lambda item: item["growth_percent"],
        reverse=True,
    )

    return {
        "status": "success",
        "company": matches.iloc[0]["COMPANY"],
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "ranking": (
            "therapeutic groups by MAT Sep 2025 sales"
        ),
        "total_groups": len(all_records),
        "company_net_sales_change": company_net_change,

        # Compatibility: existing callers still receive top N.
        "groups": by_sales[:limit],

        # Full rankings and diagnostic subsets.
        "ranking_by_sales": by_sales,
        "largest_growth_contributors": growth_contributors,
        "growth_contributors": growth_contributors,
        "declining_groups": declining_groups,
        "largest_decliners": declining_groups,
        "fastest_growing_groups": fastest_growing[:10],
        "fastest_growing_material_groups": fastest_growing[:10],

        "ranking_notes": {
            "groups": (
                f"Top {min(limit, len(by_sales))} groups "
                "by 2025 sales."
            ),
            "declining_groups": (
                "All groups with negative sales change, "
                "ranked by most negative change."
            ),
            "contribution_denominator": (
                "Company-level net sales change for the same period."
            ),
            "contribution_unavailable_when": (
                "Company-level net sales change is zero or unavailable."
            ),
        },

        "data_source": str(GROUP_FILE),
    }


# ============================================================
# COMPANY VALUE AND UNIT ANALYSIS
# ============================================================

def company_value_unit_analysis(company_name):
    """Retrieve value and unit performance for a company."""
    if not VALUE_UNIT_FILE.exists():
        raise FileNotFoundError(
            f"Value/unit analysis file not found: {VALUE_UNIT_FILE}"
        )

    df = pd.read_csv(VALUE_UNIT_FILE)
    df.columns = df.columns.astype(str).str.strip()

    df["COMPANY"] = (
        df["COMPANY"].astype(str).str.strip()
    )

    requested = str(company_name).strip().casefold()

    matches = df[
        df["COMPANY"].str.casefold() == requested
    ]

    if matches.empty:
        return {
            "status": "not_found",
            "company": company_name,
            "message": (
                "No exact company match found in value/unit analysis."
            ),
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "company": company_name,
            "matches": matches["COMPANY"].tolist(),
        }

    row = matches.iloc[0]

    return {
        "status": "success",
        "company": row["COMPANY"],
        "value_sales_2025": finite_number(
            row["VAL MAT SEP'25"]
        ),
        "value_sales_2024": finite_number(
            row["VAL MAT SEP'24"]
        ),
        "value_growth_percent": finite_number(
            row["Growth (%)"]
        ),
        "units_2025": finite_number(
            row["CTUNT MAT SEP'25"]
        ),
        "units_2024": finite_number(
            row["CTUNT MAT SEP'24"]
        ),
        "unit_change": finite_number(
            row["Unit Change"]
        ),
        "unit_growth_percent": finite_number(
            row["Unit Growth (%)"]
        ),
        "data_source": str(VALUE_UNIT_FILE),
    }


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: COMPANY LOOKUP — ALKEM*")
    print("=" * 60)
    print(find_company("ALKEM*"))

    print("\n" + "=" * 60)
    print("TEST 2: TOP 10 COMPANIES BY SALES")
    print("=" * 60)

    ranking_result = top_companies(
        limit=10,
        sort_by="sales",
    )

    for rank, company in enumerate(
        ranking_result["companies"],
        start=1,
    ):
        print(
            f"{rank}. {company['company']} | "
            f"2025 sales: {company['sales_2025']} | "
            f"Growth: {company['growth_percent']}%"
        )

    print("\n" + "=" * 60)
    print("TEST 3: ALKEM* THERAPEUTIC GROUPS")
    print("=" * 60)

    group_result = company_group_analysis("ALKEM*")

    if group_result["status"] == "success":
        for group in group_result["groups"]:
            print(
                f"{group['group']} | "
                f"2025 sales: {group['sales_2025']} | "
                f"Growth: {group['growth_percent']}%"
            )
    else:
        print(group_result)

    print("\n" + "=" * 60)
    print("TEST 4: ALKEM* VALUE AND UNIT ANALYSIS")
    print("=" * 60)

    print(company_value_unit_analysis("ALKEM*"))

    print("\nAll company-analysis tests completed.")
