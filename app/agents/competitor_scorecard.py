
import math
import numpy as np
import pandas as pd

from app.agents.company_analysis import load_company_data


DEFAULT_WEIGHTS = {
    "growth": 0.40,
    "share_change": 0.35,
    "sales_scale": 0.25,
}

MAX_COMPARISON_COMPANIES = 10

# Growth above this threshold is flagged for review.
# It is NOT removed or capped.
EXTREME_GROWTH_THRESHOLD = 500.0


def validate_weights(weights=None):
    """Validate weights and normalize them to sum to 1."""

    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    required = {"growth", "share_change", "sales_scale"}

    if not isinstance(weights, dict) or set(weights) != required:
        raise ValueError(
            "Weights must contain exactly: "
            "growth, share_change, sales_scale."
        )

    normalized = {}

    for name, value in weights.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"Weight '{name}' must be a finite, "
                "non-negative number."
            )

        normalized[name] = float(value)

    total = sum(normalized.values())

    if total <= 0:
        raise ValueError(
            "At least one weight must be greater than zero."
        )

    return {
        name: value / total
        for name, value in normalized.items()
    }


def percentile_score(values):
    """
    Convert values into market-wide percentile scores from 0 to 100.

    Higher values receive higher scores. Tied values receive
    average ranks. This method is less sensitive to extreme
    values than min-max normalization.
    """

    numeric = pd.to_numeric(
        pd.Series(values), errors="coerce"
    )

    scores = numeric.rank(
        method="average",
        pct=True,
    ) * 100

    return scores


def prepare_market_scorecard(weights=None):
    """
    Calculate scores against the full eligible IMS company dataset.

    Sales scale uses log1p before percentile ranking. This makes
    sales differences between large companies more informative
    while preserving their order.

    Growth outliers are flagged, not removed or capped.
    """

    weights = validate_weights(weights)

    df = load_company_data().copy()

    required_columns = [
        "COMPANY",
        "Growth (%)",
        "Share Change (pp)",
        "VAL MAT SEP'25",
        "VAL MAT SEP'24",
        "Market Share 2025 (%)",
        "Market Share 2024 (%)",
        "Competitive Category",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    df["COMPANY"] = df["COMPANY"].astype(str).str.strip()

    numeric_columns = [
        "Growth (%)",
        "Share Change (pp)",
        "VAL MAT SEP'25",
        "VAL MAT SEP'24",
        "Market Share 2025 (%)",
        "Market Share 2024 (%)",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # All three scoring metrics must be valid and finite.
    scoring_columns = [
        "Growth (%)",
        "Share Change (pp)",
        "VAL MAT SEP'25",
    ]

    valid_mask = df["COMPANY"].ne("")

    for column in scoring_columns:
        valid_mask &= df[column].map(
            lambda value: (
                pd.notna(value)
                and math.isfinite(float(value))
            )
        )

    # Logarithmic scoring requires non-negative sales.
    valid_mask &= df["VAL MAT SEP'25"] >= 0

    df = df.loc[valid_mask].copy()

    if df.empty:
        raise ValueError(
            "No eligible companies found in the IMS dataset."
        )

    # Company names must uniquely identify records.
    duplicate_mask = df["COMPANY"].str.casefold().duplicated(
        keep=False
    )

    if duplicate_mask.any():
        duplicate_names = sorted(
            df.loc[duplicate_mask, "COMPANY"].unique().tolist()
        )

        raise ValueError(
            "Duplicate company names prevent reliable scoring: "
            f"{duplicate_names[:10]}"
        )

    # Retain source metrics.
    df["growth_percent"] = df["Growth (%)"]
    df["share_change_percentage_points"] = df["Share Change (pp)"]
    df["sales_2025"] = df["VAL MAT SEP'25"]
    df["sales_2024"] = df["VAL MAT SEP'24"]

    # Flag unusual growth without altering its value.
    df["growth_outlier_flag"] = (
        df["growth_percent"].abs()
        > EXTREME_GROWTH_THRESHOLD
    )

    # Growth and market-share change: market-wide percentiles.
    df["growth_score"] = percentile_score(
        df["growth_percent"]
    )

    df["share_change_score"] = percentile_score(
        df["share_change_percentage_points"]
    )

    # Sales scale: log-transform before calculating percentiles.
    # log1p(0) is valid, so zero sales can be scored.
    df["log_sales_2025"] = np.log1p(
        df["sales_2025"]
    )

    df["sales_scale_score"] = percentile_score(
        df["log_sales_2025"]
    )

    # Weighted total.
    df["weighted_score"] = (
        weights["growth"] * df["growth_score"]
        + weights["share_change"] * df["share_change_score"]
        + weights["sales_scale"] * df["sales_scale_score"]
    ).round(2)

    # Market-wide ranking.
    df["market_rank"] = (
        df["weighted_score"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df = df.sort_values(
        ["weighted_score", "COMPANY"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return df, weights


def build_weighted_scorecard(companies, weights=None):
    """Build a market-wide weighted competitor scorecard."""

    if not isinstance(companies, list):
        return {
            "status": "needs_input",
            "message": "Provide a list of company names.",
        }

    cleaned_companies = []

    for company in companies:
        if company is None:
            continue

        company = str(company).strip()

        if company:
            cleaned_companies.append(company)

    cleaned_companies = list(
        dict.fromkeys(cleaned_companies)
    )

    if len(cleaned_companies) < 2:
        return {
            "status": "needs_input",
            "message": (
                "Please provide at least two different companies."
            ),
        }

    if len(cleaned_companies) > MAX_COMPARISON_COMPANIES:
        return {
            "status": "needs_input",
            "message": (
                f"Compare no more than "
                f"{MAX_COMPARISON_COMPANIES} companies at once."
            ),
        }

    try:
        market_df, normalized_weights = prepare_market_scorecard(
            weights
        )
    except (FileNotFoundError, ValueError) as error:
        return {
            "status": "error",
            "message": str(error),
        }

    market_lookup = {
        str(row["COMPANY"]).casefold(): row
        for _, row in market_df.iterrows()
    }

    selected_rows = []
    not_found = []

    for requested_name in cleaned_companies:
        row = market_lookup.get(requested_name.casefold())

        if row is None:
            not_found.append(requested_name)
            continue

        selected_rows.append({
            "company": row["COMPANY"],
            "market_rank": int(row["market_rank"]),
            "eligible_market_companies": len(market_df),
            "weighted_score": float(row["weighted_score"]),
            "growth_percent": float(row["growth_percent"]),
            "share_change_percentage_points": float(
                row["share_change_percentage_points"]
            ),
            "sales_2025": float(row["sales_2025"]),
            "sales_2024": (
                float(row["sales_2024"])
                if pd.notna(row["sales_2024"])
                and math.isfinite(float(row["sales_2024"]))
                else None
            ),
            "market_share_2025_percent": (
                float(row["Market Share 2025 (%)"])
                if pd.notna(row["Market Share 2025 (%)"])
                and math.isfinite(
                    float(row["Market Share 2025 (%)"])
                )
                else None
            ),
            "market_share_2024_percent": (
                float(row["Market Share 2024 (%)"])
                if pd.notna(row["Market Share 2024 (%)"])
                and math.isfinite(
                    float(row["Market Share 2024 (%)"])
                )
                else None
            ),
            "competitive_category": row["Competitive Category"],
            "growth_outlier_flag": bool(
                row["growth_outlier_flag"]
            ),
            "component_scores": {
                "growth": round(float(row["growth_score"]), 2),
                "share_change": round(
                    float(row["share_change_score"]), 2
                ),
                "sales_scale": round(
                    float(row["sales_scale_score"]), 2
                ),
            },
        })

    if not_found:
        return {
            "status": "not_found",
            "message": (
                "Some companies were not found in the eligible "
                "market dataset. Check their exact names."
            ),
            "not_found": not_found,
            "eligible_market_company_count": len(market_df),
        }

    selected_rows.sort(
        key=lambda row: (
            row["market_rank"],
            row["company"].casefold(),
        )
    )

    flagged_companies = market_df.loc[
        market_df["growth_outlier_flag"],
        ["COMPANY", "growth_percent"],
    ]

    return {
        "status": "success",
        "report_type": "Market-Wide Weighted Competitor Scorecard",
        "period": "MAT Sep 2025 vs MAT Sep 2024",
        "weights": {
            name: round(value * 100, 1)
            for name, value in normalized_weights.items()
        },
        "normalization": (
            "Growth and share change use market-wide percentile "
            "scores. Sales use log1p transformation followed by "
            "market-wide percentile scoring."
        ),
        "scoring_scope": (
            "Market-wide: selected companies are benchmarked "
            "against the full eligible dataset."
        ),
        "growth_outlier_threshold_percent": (
            EXTREME_GROWTH_THRESHOLD
        ),
        "flagged_growth_company_count": len(flagged_companies),
        "flagged_growth_companies": [
            {
                "company": row["COMPANY"],
                "growth_percent": float(row["growth_percent"]),
            }
            for _, row in flagged_companies.iterrows()
        ],
        "score_interpretation": (
            "Relative decision-support score, not an absolute "
            "measure of company quality or future performance."
        ),
        "selected_company_count": len(selected_rows),
        "eligible_market_company_count": len(market_df),
        "companies": selected_rows,
        "data_source": "IMS_Company_Analysis.csv",
    }


if __name__ == "__main__":
    print("Preparing market-wide competitor scorecard...")

    result = build_weighted_scorecard([
        "ALKEM*",
        "CIPLA",
        "SUN*",
    ])

    if result.get("status") != "success":
        print("\nERROR")
        print(result)

    else:
        print("\nMARKET-WIDE WEIGHTED COMPETITOR SCORECARD")
        print("=" * 75)

        print("Weights:", result["weights"])
        print(
            "Eligible market companies:",
            result["eligible_market_company_count"],
        )
        print(
            "Companies flagged for extreme growth:",
            result["flagged_growth_company_count"],
        )

        print("\nSELECTED COMPANIES")
        print("-" * 75)

        for company in result["companies"]:
            print(
                f"\nMarket rank {company['market_rank']}: "
                f"{company['company']}"
            )

            print(
                f"  Weighted score: "
                f"{company['weighted_score']:.2f}/100"
            )

            print(
                f"  Growth: {company['growth_percent']:+.2f}% "
                f"(score "
                f"{company['component_scores']['growth']:.2f})"
            )

            print(
                f"  Share change: "
                f"{company['share_change_percentage_points']:+.4f} pp "
                f"(score "
                f"{company['component_scores']['share_change']:.2f})"
            )

            print(
                f"  Current sales: {company['sales_2025']:,.2f} "
                f"(score "
                f"{company['component_scores']['sales_scale']:.2f})"
            )

            print(
                f"  Category: {company['competitive_category']}"
            )

            if company["growth_outlier_flag"]:
                print(
                    "  WARNING: Growth exceeds the configured "
                    "outlier threshold; investigate the source data."
                )

        print("\nGROWTH OUTLIER REVIEW")
        print("-" * 75)

        for item in result["flagged_growth_companies"][:10]:
            print(
                f"{item['company']}: "
                f"{item['growth_percent']:.2f}%"
            )

        print("\n", result["score_interpretation"])
