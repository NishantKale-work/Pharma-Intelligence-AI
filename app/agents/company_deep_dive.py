from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.agents.company_analysis import (
    find_company,
    company_value_unit_analysis,
    GROUP_FILE,
)

from app.agents.competitor_scorecard import (
    build_weighted_scorecard,
)

from app.core.config import (
    DEFAULT_COMPANY,
    DEFAULT_COMPETITORS,
    DEFAULT_GROUP_LIMIT,
    DEFAULT_MIN_GROUP_SALES,
    DATA_PERIOD,
)


def safe_number(value: Any):
    """Convert a value to a finite float."""

    try:
        number = float(value)

        if pd.isna(number) or number in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return number

    except (TypeError, ValueError):
        return None


def normalize_name(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().casefold()


def get_column(
    df: pd.DataFrame,
    candidates: list[str],
):
    """Find a column without depending on capitalization."""

    columns = {
        str(column).strip().casefold(): column
        for column in df.columns
    }

    for candidate in candidates:
        match = columns.get(candidate.strip().casefold())

        if match is not None:
            return match

    return None


def get_company_metrics(company: str) -> dict:
    """Retrieve validated company-level metrics."""

    try:
        result = find_company(company)

        if not isinstance(result, dict):
            return {
                "status": "error",
                "message": "Unexpected company-analysis result.",
            }

        if result.get("status") != "success":
            return result

        numeric_fields = [
            "sales_2025",
            "sales_2024",
            "sales_change",
            "growth_percent",
            "market_share_2025_percent",
            "market_share_2024_percent",
            "share_change_percentage_points",
            "contribution_to_market_growth_percent",
        ]

        metrics = {
            "company": result.get("company", company),
            "comparison": result.get("comparison"),
            "competitive_category": result.get(
                "competitive_category"
            ),
            "data_source": result.get(
                "data_source",
                "IMS_Company_Analysis.csv",
            ),
        }

        for field in numeric_fields:
            metrics[field] = safe_number(result.get(field))

        return {
            "status": "success",
            "metrics": metrics,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }


def get_value_unit_metrics(company: str) -> dict:
    """Compare value growth with unit growth."""

    try:
        result = company_value_unit_analysis(company)

        if not isinstance(result, dict):
            return {
                "status": "error",
                "message": "Unexpected value-unit result.",
            }

        if result.get("status") != "success":
            return result

        output = dict(result)

        value_2025 = safe_number(
            result.get("value_sales_2025")
        )
        value_2024 = safe_number(
            result.get("value_sales_2024")
        )
        units_2025 = safe_number(result.get("units_2025"))
        units_2024 = safe_number(result.get("units_2024"))

        # Support alternate names from existing modules.
        value_2025 = (
            value_2025
            if value_2025 is not None
            else safe_number(result.get("sales_2025"))
        )
        value_2024 = (
            value_2024
            if value_2024 is not None
            else safe_number(result.get("sales_2024"))
        )
        units_2025 = (
            units_2025
            if units_2025 is not None
            else safe_number(result.get("ctunt_2025"))
        )
        units_2024 = (
            units_2024
            if units_2024 is not None
            else safe_number(result.get("ctunt_2024"))
        )

        value_growth = None
        unit_growth = None
        value_per_unit_change = None

        if value_2024 not in (None, 0) and value_2025 is not None:
            value_growth = (
                (value_2025 / value_2024) - 1
            ) * 100

        if units_2024 not in (None, 0) and units_2025 is not None:
            unit_growth = (
                (units_2025 / units_2024) - 1
            ) * 100

        if (
            value_2025 is not None
            and value_2024 not in (None, 0)
            and units_2025 not in (None, 0)
            and units_2024 not in (None, 0)
        ):
            previous_value_per_unit = value_2024 / units_2024
            current_value_per_unit = value_2025 / units_2025

            value_per_unit_change = (
                current_value_per_unit
                / previous_value_per_unit - 1
            ) * 100

        output.update({
            "calculated_value_growth_percent": value_growth,
            "calculated_unit_growth_percent": unit_growth,
            "value_per_unit_change_percent": value_per_unit_change,
            "value_per_unit_caveat": (
                "Aggregate value per unit is not proof of a price "
                "increase. Product mix, pricing and unit definitions "
                "can all influence this indicator."
            ),
        })

        return output

    except Exception as exc:
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }


def get_therapeutic_group_metrics(
    company: str,
    limit: int = DEFAULT_GROUP_LIMIT,
    min_group_sales: float = DEFAULT_MIN_GROUP_SALES,
    company_sales_change: float | None = None,
) -> dict:
    """
    Rank groups by sales, absolute contribution, growth rate and decline.

    The materiality threshold uses current-period sales in the same
    units as the source CSV. It does not remove groups from other rankings.
    """

    try:
        if not GROUP_FILE.exists():
            return {
                "status": "error",
                "message": f"Group data not found: {GROUP_FILE}",
            }

        df = pd.read_csv(GROUP_FILE)

        company_col = get_column(df, ["COMPANY"])
        group_col = get_column(
            df, ["GROUP", "THERAPEUTIC GROUP", "PRODUCT GROUP"]
        )
        current_col = get_column(
            df, ["VAL MAT SEP'25", "VAL MAT SEP’25"]
        )
        previous_col = get_column(
            df, ["VAL MAT SEP'24", "VAL MAT SEP’24"]
        )
        change_col = get_column(df, ["Sales Change"])
        growth_col = get_column(df, ["Growth (%)"])

        required = {
            "COMPANY": company_col,
            "GROUP": group_col,
            "current sales": current_col,
            "previous sales": previous_col,
        }

        missing = [
            name for name, column in required.items()
            if column is None
        ]

        if missing:
            return {
                "status": "error",
                "message": (
                    "Missing columns: " + ", ".join(missing)
                ),
                "available_columns": list(df.columns),
            }

        matching = df[
            df[company_col].apply(normalize_name)
            == normalize_name(company)
        ].copy()

        if matching.empty:
            # Allow a name such as ALKEM to match ALKEM*.
            search_name = normalize_name(company).replace("*", "")

            matching = df[
                df[company_col].apply(normalize_name).str.replace(
                    "*", "", regex=False
                ).str.contains(
                    search_name,
                    regex=False,
                    na=False,
                )
            ].copy()

        if matching.empty:
            return {
                "status": "error",
                "message": f"No group records found for {company}.",
            }

        matching[current_col] = pd.to_numeric(
            matching[current_col], errors="coerce"
        )
        matching[previous_col] = pd.to_numeric(
            matching[previous_col], errors="coerce"
        )

        calculated_change = matching[current_col] - matching[previous_col]

        if change_col is not None:
            supplied_change = pd.to_numeric(
                matching[change_col], errors="coerce"
            )
            matching["_change"] = supplied_change.fillna(
                calculated_change
            )
        else:
            matching["_change"] = calculated_change

        calculated_growth = (
            matching["_change"]
            / matching[previous_col].where(
                matching[previous_col] != 0
            )
        ) * 100

        if growth_col is not None:
            matching["_growth"] = pd.to_numeric(
                matching[growth_col], errors="coerce"
            ).fillna(calculated_growth)
        else:
            matching["_growth"] = calculated_growth

        matching["_group"] = matching[group_col].astype(str)

        if company_sales_change is None:
            company_result = find_company(company)

            if (
                isinstance(company_result, dict)
                and company_result.get("status") == "success"
            ):
                company_sales_change = safe_number(
                    company_result.get("sales_change")
                )

        def to_records(frame: pd.DataFrame) -> list[dict]:
            records = []

            for _, row in frame.iterrows():
                change = safe_number(row["_change"])

                contribution = None
                if company_sales_change not in (None, 0) and change is not None:
                    contribution = (
                        change / company_sales_change
                    ) * 100

                records.append({
                    "group": row["_group"],
                    "sales_2025": safe_number(row[current_col]),
                    "sales_2024": safe_number(row[previous_col]),
                    "sales_change": change,
                    "growth_percent": safe_number(row["_growth"]),
                    "contribution_to_company_net_sales_change_percent":
                        contribution,
                })

            return records

        limit = max(1, min(int(limit), 100))
        min_group_sales = max(0.0, float(min_group_sales))

        by_sales = matching.sort_values(
            current_col, ascending=False, na_position="last"
        )

        contributors = matching[
            matching["_change"] > 0
        ].sort_values(
            "_change", ascending=False, na_position="last"
        )

        fastest = matching[
            (matching[previous_col] > 0)
            & (matching["_growth"] > 0)
            & (matching["_growth"].notna())
        ].sort_values(
            "_growth", ascending=False, na_position="last"
        )

        material_fastest = fastest[
            fastest[current_col] >= min_group_sales
        ]

        declining = matching[
            matching["_change"] < 0
        ].sort_values(
            "_change", ascending=True, na_position="last"
        )

        return {
            "status": "success",
            "company": company,
            "total_groups": int(len(matching)),
            "minimum_sales_threshold": min_group_sales,
            "company_net_sales_change": company_sales_change,
            "ranking_by_sales": to_records(by_sales.head(limit)),
            "largest_growth_contributors": to_records(
                contributors.head(limit)
            ),
            "fastest_growing_groups": to_records(
                fastest.head(limit)
            ),
            "fastest_growing_material_groups": to_records(
                material_fastest.head(limit)
            ),
            "declining_groups": to_records(declining.head(limit)),
            "data_source": str(GROUP_FILE),
            "ranking_notes": {
                "contribution": (
                    "Group sales change divided by company net sales "
                    "change. Contributions can exceed 100% or be "
                    "negative because declining groups offset growth."
                ),
                "materiality": (
                    "The minimum-sales threshold applies only to the "
                    "material fastest-growing ranking."
                ),
            },
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }


def get_competitor_metrics(companies: list[str]) -> dict:
    try:
        return build_weighted_scorecard(companies)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }


def interpret_company_metrics(metrics: dict) -> dict:
    """Generate descriptive findings without claiming causation."""

    growth = metrics.get("growth_percent")
    share_change = metrics.get("share_change_percentage_points")

    findings = []
    risks = []
    investigations = []

    if growth is not None:
        findings.append(
            f"Sales value growth: {growth:+.2f}%."
        )

    if share_change is not None:
        findings.append(
            f"Market-share movement: {share_change:+.4f} percentage "
            "points."
        )

    if growth is not None and share_change is not None:
        if growth > 0 and share_change < 0:
            risks.append(
                "Sales value is growing while market share is declining."
            )
            investigations.extend([
                "Check whether competitors are growing faster.",
                "Identify which therapeutic groups are driving growth.",
                "Compare the company's growth with total market growth.",
            ])

        elif growth > 0 and share_change > 0:
            findings.append(
                "Sales growth is accompanied by market-share gains."
            )

        elif growth < 0 and share_change < 0:
            risks.append(
                "Both sales growth and market-share movement are negative."
            )

    return {
        "observed_findings": findings,
        "potential_risks": risks,
        "hypotheses_to_investigate": investigations,
        "caveat": (
            "These are descriptive interpretations. The dataset alone "
            "does not prove why performance changed."
        ),
    }


def interpret_therapeutic_groups(groups: dict) -> list[str]:
    if groups.get("status") != "success":
        return [
            "Therapeutic-group analysis unavailable: "
            + groups.get("message", "Unknown error")
        ]

    insights = []

    contributors = groups.get("largest_growth_contributors", [])
    fastest = groups.get("fastest_growing_material_groups", [])
    declining = groups.get("declining_groups", [])

    if contributors:
        item = contributors[0]
        contribution = item.get(
            "contribution_to_company_net_sales_change_percent"
        )

        message = (
            f"Largest absolute growth contributor: {item['group']} "
            f"({item['sales_change']:,.2f} sales change)."
        )

        if contribution is not None:
            message += (
                f" This equals {contribution:.1f}% of company net "
                "sales change."
            )

        insights.append(message)

    if fastest:
        item = fastest[0]
        insights.append(
            f"Fastest-growing material group: {item['group']} "
            f"({item['growth_percent']:.2f}% growth)."
        )

    if declining:
        item = declining[0]
        insights.append(
            f"Largest group-level decline: {item['group']} "
            f"({item['sales_change']:,.2f})."
        )

    if not insights:
        insights.append(
            "No material positive or negative group signals were found."
        )

    return insights


def build_company_deep_dive(
    company: str = DEFAULT_COMPANY,
    competitors: list[str] | None = None,
    therapeutic_group_limit: int = DEFAULT_GROUP_LIMIT,
    min_group_sales: float = DEFAULT_MIN_GROUP_SALES,
) -> dict:
    """Build a complete company commercial-intelligence report."""

    if not isinstance(company, str) or not company.strip():
        return {
            "status": "error",
            "message": "Please provide a company name.",
        }

    company = company.strip()

    if competitors is None:
        competitors = DEFAULT_COMPETITORS.copy()

    if not isinstance(competitors, list):
        return {
            "status": "error",
            "message": "Competitors must be a list.",
        }

    competitors = [
        name.strip()
        for name in competitors
        if isinstance(name, str) and name.strip()
    ]

    all_competitors = list(dict.fromkeys([company] + competitors))

    company_result = get_company_metrics(company)

    if company_result.get("status") != "success":
        return {
            "status": "error",
            "message": f"Could not analyse {company}.",
            "details": company_result,
        }

    metrics = company_result["metrics"]

    value_units = get_value_unit_metrics(company)

    groups = get_therapeutic_group_metrics(
        company=company,
        limit=therapeutic_group_limit,
        min_group_sales=min_group_sales,
        company_sales_change=metrics.get("sales_change"),
    )

    scorecard = get_competitor_metrics(all_competitors)

    return {
        "status": "success",
        "report_type": "Pharma Commercial Intelligence",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_period": DATA_PERIOD,
        "company": metrics,
        "value_vs_units": value_units,
        "therapeutic_groups": groups,
        "competitor_scorecard": scorecard,
        "commercial_interpretation": interpret_company_metrics(metrics),
        "therapeutic_group_insights": interpret_therapeutic_groups(
            groups
        ),
        "limitations": [
            "The report uses the supplied IMS dataset and its definitions.",
            "Group contributions are based on absolute sales-value changes.",
            "Value-per-unit movement is not proof of price changes.",
            "Weighted competitor scores depend on the chosen weights.",
            "Findings do not establish the cause of observed performance.",
        ],
    }


def print_deep_dive(report: dict) -> None:
    """Print a readable company report."""

    import json

    print("\n" + "=" * 76)
    print("PHARMA INTELLIGENCE | COMPANY DEEP DIVE")
    print("=" * 76)

    if report.get("status") != "success":
        print("ERROR:", report.get("message"))
        print(json.dumps(report, indent=2, default=str))
        return

    company = report["company"]

    print("Company:", company.get("company"))
    print("Period:", report.get("data_period"))

    print("\n1. COMPANY PERFORMANCE")
    for key in (
        "sales_2024",
        "sales_2025",
        "sales_change",
        "growth_percent",
        "market_share_2024_percent",
        "market_share_2025_percent",
        "share_change_percentage_points",
        "competitive_category",
    ):
        print(f"{key}: {company.get(key)}")

    print("\n2. COMMERCIAL INTERPRETATION")
    for finding in report["commercial_interpretation"]["observed_findings"]:
        print("-", finding)

    for risk in report["commercial_interpretation"]["potential_risks"]:
        print("- Risk:", risk)

    for idea in report["commercial_interpretation"][
        "hypotheses_to_investigate"
    ]:
        print("- Investigate:", idea)

    print("\n3. VALUE VERSUS UNITS")
    print(json.dumps(report["value_vs_units"], indent=2, default=str))

    print("\n4. THERAPEUTIC-GROUP INSIGHTS")
    for insight in report["therapeutic_group_insights"]:
        print("-", insight)

    print("\n5. THERAPEUTIC-GROUP RANKINGS")
    groups = report["therapeutic_groups"]

    if groups.get("status") == "success":
        print("Total groups:", groups["total_groups"])
        print(
            "Minimum sales threshold:",
            groups["minimum_sales_threshold"],
        )

        for ranking_name in (
            "ranking_by_sales",
            "largest_growth_contributors",
            "fastest_growing_material_groups",
            "declining_groups",
        ):
            print(f"\n{ranking_name.upper()}")

            for item in groups.get(ranking_name, []):
                print(
                    f"- {item['group']} | "
                    f"Sales: {item['sales_2025']} | "
                    f"Change: {item['sales_change']} | "
                    f"Growth: {item['growth_percent']}% | "
                    f"Contribution to company net change: "
                    f"{item['contribution_to_company_net_sales_change_percent']}"
                )
    else:
        print("Unavailable:", groups.get("message"))

    print("\n6. COMPETITOR SCORECARD")
    print(json.dumps(
        report["competitor_scorecard"],
        indent=2,
        default=str,
    ))

    print("\n7. LIMITATIONS")
    for limitation in report["limitations"]:
        print("-", limitation)

    print("=" * 76)


if __name__ == "__main__":
    report = build_company_deep_dive(
        company="ALKEM*",
        competitors=["CIPLA", "SUN*"],
    )
    print_deep_dive(report)