
from pathlib import Path

import pandas as pd


DATA_FILE = (
    Path(__file__).resolve().parents[3]
    / "IMS_Company_Analysis.csv"
)


def load_market_share_data() -> pd.DataFrame:
    """Load market-share data using the CSV's existing units."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Market-share dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = {
        "COMPANY",
        "Market Share 2025 (%)",
        "Market Share 2024 (%)",
        "Share Change (pp)",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    # These columns are already on their display scales in this CSV:
    # market share = percent, share change = percentage points.
    # Do NOT multiply by 100 again.
    df["market_share_2025_percent"] = pd.to_numeric(
        df["Market Share 2025 (%)"],
        errors="coerce",
    )

    df["market_share_2024_percent"] = pd.to_numeric(
        df["Market Share 2024 (%)"],
        errors="coerce",
    )

    df["share_change_percentage_points"] = pd.to_numeric(
        df["Share Change (pp)"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "COMPANY",
            "market_share_2025_percent",
            "market_share_2024_percent",
            "share_change_percentage_points",
        ]
    ).copy()

    return df


def market_share_movers(
    direction: str = "gainers",
    limit: int = 10,
) -> dict:
    """Rank companies by market-share gains or losses."""
    if direction not in {"gainers", "losers"}:
        raise ValueError(
            "direction must be 'gainers' or 'losers'."
        )

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer.")

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    limit = min(limit, 100)
    df = load_market_share_data()

    ranked = df.sort_values(
        "share_change_percentage_points",
        ascending=(direction == "losers"),
    ).head(limit)

    companies = []

    for _, row in ranked.iterrows():
        companies.append({
            "company": str(row["COMPANY"]),
            "market_share_2025_percent": round(
                float(row["market_share_2025_percent"]), 4
            ),
            "market_share_2024_percent": round(
                float(row["market_share_2024_percent"]), 4
            ),
            "share_change_percentage_points": round(
                float(row["share_change_percentage_points"]), 4
            ),
        })

    return {
        "status": "success",
        "direction": direction,
        "ranking": (
            "Largest market-share gainers"
            if direction == "gainers"
            else "Largest market-share decliners"
        ),
        "period": "MAT Sep 2025 vs MAT Sep 2024",
        "companies": companies,
        "data_source": str(DATA_FILE),
    }


def company_share_rank(company_name: str) -> dict:
    """Find a company's market-share change and rank."""
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError("Please provide a company name.")

    df = load_market_share_data()

    query = "".join(
        char.lower()
        for char in company_name
        if char.isalnum()
    )

    normalized_names = df["COMPANY"].astype(str).map(
        lambda value: "".join(
            char.lower()
            for char in value
            if char.isalnum()
        )
    )

    exact = df[normalized_names == query]

    if exact.empty:
        partial = df[
            normalized_names.str.contains(
                query,
                regex=False,
                na=False,
            )
        ]

        if len(partial) != 1:
            return {
                "status": "not_found",
                "company_query": company_name,
                "matches": (
                    partial["COMPANY"].astype(str).tolist()[:10]
                ),
                "message": (
                    "Company not found uniquely. Try the exact "
                    "company name from the IMS dataset."
                ),
            }

        exact = partial

    row = exact.iloc[0]

    sorted_df = df.sort_values(
        "share_change_percentage_points",
        ascending=False,
    ).reset_index(drop=True)

    company_key = str(row["COMPANY"])

    rank_positions = sorted_df.index[
        sorted_df["COMPANY"].astype(str) == company_key
    ]

    rank = (
        int(rank_positions[0]) + 1
        if len(rank_positions)
        else None
    )

    return {
        "status": "success",
        "company": company_key,
        "rank_by_share_change": rank,
        "companies_ranked": len(sorted_df),
        "market_share_2025_percent": round(
            float(row["market_share_2025_percent"]), 4
        ),
        "market_share_2024_percent": round(
            float(row["market_share_2024_percent"]), 4
        ),
        "share_change_percentage_points": round(
            float(row["share_change_percentage_points"]), 4
        ),
        "period": "MAT Sep 2025 vs MAT Sep 2024",
        "data_source": str(DATA_FILE),
    }


if __name__ == "__main__":
    print("\nTOP 10 MARKET-SHARE GAINERS")
    print(market_share_movers("gainers", 10))

    print("\nTOP 10 MARKET-SHARE DECLINERS")
    print(market_share_movers("losers", 10))

    print("\nALKEM MARKET-SHARE RANK")
    print(company_share_rank("ALKEM*"))
