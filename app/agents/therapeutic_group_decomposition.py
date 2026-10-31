"""Compare company therapeutic-group performance with each group's market.

The analysis matches exact GROUP labels across the company-group and market-group
IMS files. It reports observed growth gaps and within-group share movements; it
cannot establish why those differences occurred.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import DATA_FOLDER

COMPANY_GROUP_FILE = DATA_FOLDER / "IMS_Company_Group_Analysis.csv"
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


def _growth(prior: float | None, current: float | None) -> float | None:
    if prior is None or current is None or prior <= 0:
        return None
    return (current - prior) / prior * 100


def build_therapeutic_group_decomposition(
    company: str = "ALKEM*",
    limit: int = 15,
    min_company_sales_2025: float = 10.0,
) -> dict:
    """Return a group-level comparison of company growth vs market-group growth.

    ``growth_gap_percentage_points`` is company growth minus that therapeutic
    group's market growth. ``within_group_share_change_percentage_points`` is
    the company's share of the group's market sales in 2025 minus 2024.
    Groups with zero/negative prior sales do not receive a growth rate.
    """
    if not isinstance(company, str) or not company.strip():
        return {"status": "error", "message": "Please provide a company name."}
    if limit < 1:
        return {"status": "error", "message": "limit must be at least 1."}

    try:
        for path in (COMPANY_GROUP_FILE, MARKET_GROUP_FILE):
            if not path.exists():
                raise FileNotFoundError(f"Dataset not found: {path}")

        company_df = pd.read_csv(COMPANY_GROUP_FILE)
        market_df = pd.read_csv(MARKET_GROUP_FILE)
        required_company = {"COMPANY", "GROUP", VALUE_2024, VALUE_2025}
        required_market = {"GROUP", VALUE_2024, VALUE_2025}
        if not required_company.issubset(company_df.columns):
            raise ValueError(f"Company-group dataset missing columns: {sorted(required_company - set(company_df.columns))}")
        if not required_market.issubset(market_df.columns):
            raise ValueError(f"Market-group dataset missing columns: {sorted(required_market - set(market_df.columns))}")

        company_df["COMPANY"] = company_df["COMPANY"].astype(str).str.strip()
        company_df["GROUP"] = company_df["GROUP"].astype(str).str.strip()
        market_df["GROUP"] = market_df["GROUP"].astype(str).str.strip()
        company_matches = company_df[company_df["COMPANY"].str.casefold() == company.strip().casefold()].copy()
        if company_matches.empty:
            return {"status": "error", "message": f"Company '{company}' was not found in {COMPANY_GROUP_FILE.name}."}
        if company_matches["GROUP"].duplicated().any():
            return {"status": "error", "message": f"Company '{company}' has duplicate therapeutic-group rows; refusing to double-count."}
        if market_df["GROUP"].duplicated().any():
            return {"status": "error", "message": "Market-group dataset has duplicate GROUP labels; refusing to double-count."}

        for frame in (company_matches, market_df):
            frame[VALUE_2024] = pd.to_numeric(frame[VALUE_2024], errors="coerce")
            frame[VALUE_2025] = pd.to_numeric(frame[VALUE_2025], errors="coerce")
        if company_matches[[VALUE_2024, VALUE_2025]].isna().any().any():
            raise ValueError("Company-group sales contain missing or non-numeric values.")
        if market_df[[VALUE_2024, VALUE_2025]].isna().any().any():
            raise ValueError("Market-group sales contain missing or non-numeric values.")

        joined = company_matches.merge(
            market_df[["GROUP", VALUE_2024, VALUE_2025]],
            on="GROUP", how="left", validate="one_to_one", suffixes=("_company", "_market"), indicator=True,
        )
        matched = joined[joined["_merge"] == "both"].copy()
        unmatched_groups = joined.loc[joined["_merge"] != "both", "GROUP"].tolist()
        rows: list[dict] = []
        for _, row in matched.iterrows():
            c24, c25 = _finite(row[f"{VALUE_2024}_company"]), _finite(row[f"{VALUE_2025}_company"])
            m24, m25 = _finite(row[f"{VALUE_2024}_market"]), _finite(row[f"{VALUE_2025}_market"])
            cg, mg = _growth(c24, c25), _growth(m24, m25)
            expected_company_sales_at_group_growth = (
                c24 * (1 + mg / 100)
                if c24 is not None and mg is not None
                else None
            )
            sales_vs_group_growth_benchmark = (
                c25 - expected_company_sales_at_group_growth
                if c25 is not None and expected_company_sales_at_group_growth is not None
                else None
            )
            c_share24 = c24 / m24 * 100 if c24 is not None and m24 is not None and m24 > 0 else None
            c_share25 = c25 / m25 * 100 if c25 is not None and m25 is not None and m25 > 0 else None
            share_change = c_share25 - c_share24 if c_share24 is not None and c_share25 is not None else None
            rows.append({
                "group": row["GROUP"],
                "company_sales_2024": c24,
                "company_sales_2025": c25,
                "company_sales_change": c25 - c24 if c24 is not None and c25 is not None else None,
                "company_growth_percent": cg,
                "market_group_sales_2024": m24,
                "market_group_sales_2025": m25,
                "market_group_growth_percent": mg,
                "growth_gap_percentage_points": cg - mg if cg is not None and mg is not None else None,
                "expected_company_sales_2025_at_group_market_growth": expected_company_sales_at_group_growth,
                "sales_vs_group_market_growth_benchmark": sales_vs_group_growth_benchmark,
                "within_group_share_2024_percent": c_share24,
                "within_group_share_2025_percent": c_share25,
                "within_group_share_change_percentage_points": share_change,
                "classification": (
                    "Growing faster than group market" if cg is not None and mg is not None and cg > mg
                    else "Growing slower than group market" if cg is not None and mg is not None and cg < mg
                    else "Growth rates equal" if cg is not None and mg is not None
                    else "Growth comparison unavailable"
                ),
            })

        material = [r for r in rows if r["company_sales_2025"] is not None and r["company_sales_2025"] >= min_company_sales_2025]
        negative_gap = sorted(
            [r for r in material if r["growth_gap_percentage_points"] is not None and r["growth_gap_percentage_points"] < 0],
            key=lambda r: (r["growth_gap_percentage_points"], -(r["company_sales_2025"] or 0)),
        )
        positive_gap = sorted(
            [r for r in material if r["growth_gap_percentage_points"] is not None and r["growth_gap_percentage_points"] > 0],
            key=lambda r: (-r["growth_gap_percentage_points"], -(r["company_sales_2025"] or 0)),
        )
        share_losers = sorted(
            [r for r in material if r["within_group_share_change_percentage_points"] is not None and r["within_group_share_change_percentage_points"] < 0],
            key=lambda r: r["within_group_share_change_percentage_points"],
        )
        by_sales_change = sorted(material, key=lambda r: r["company_sales_change"] if r["company_sales_change"] is not None else 0)

        # Rank group-level relative sales performance against each group's own market.
        # Positive values mean company sales exceeded the group-growth benchmark;
        # negative values mean they fell short. This is a diagnostic bridge, not
        # a causal attribution of the overall company-vs-total-market growth gap.
        ranked_group_benchmark_gaps = sorted(
            [r for r in material if r["sales_vs_group_market_growth_benchmark"] is not None],
            key=lambda r: r["sales_vs_group_market_growth_benchmark"],
        )
        company_group_sales_2024 = sum(r["company_sales_2024"] or 0 for r in rows)
        company_group_sales_2025 = sum(r["company_sales_2025"] or 0 for r in rows)
        expected_group_sales_2025 = sum(
            r["expected_company_sales_2025_at_group_market_growth"]
            for r in rows
            if r["expected_company_sales_2025_at_group_market_growth"] is not None
        )
        company_sales_2024_total = float(company_matches[VALUE_2024].sum())
        company_sales_2025_total = float(company_matches[VALUE_2025].sum())
        company_total_growth = _growth(company_sales_2024_total, company_sales_2025_total)
        # Overall total-market growth benchmark comes from the same reconciled market total.
        market_sales_2024_total = float(market_df[VALUE_2024].sum())
        market_sales_2025_total = float(market_df[VALUE_2025].sum())
        total_market_growth = _growth(market_sales_2024_total, market_sales_2025_total)
        expected_company_sales_at_total_market_growth = (
            company_sales_2024_total * (1 + total_market_growth / 100)
            if total_market_growth is not None else None
        )
        actual_vs_total_market_benchmark = (
            company_sales_2025_total - expected_company_sales_at_total_market_growth
            if expected_company_sales_at_total_market_growth is not None else None
        )
        expected_group_sales_change = expected_group_sales_2025 - company_group_sales_2024
        actual_group_sales_change = company_group_sales_2025 - company_group_sales_2024
        within_group_relative_performance_effect = actual_group_sales_change - expected_group_sales_change
        group_mix_effect_vs_total_market = (
            expected_group_sales_2025 - expected_company_sales_at_total_market_growth
            if expected_company_sales_at_total_market_growth is not None else None
        )
        bridge_reconciliation_residual = (
            actual_vs_total_market_benchmark
            - (within_group_relative_performance_effect + group_mix_effect_vs_total_market)
            if actual_vs_total_market_benchmark is not None and group_mix_effect_vs_total_market is not None
            else None
        )
        # Full detail remains available; summaries are bounded for concise downstream use.
        return {
            "status": "success",
            "report_type": "Therapeutic Group Market Decomposition",
            "company": company_matches["COMPANY"].iloc[0],
            "source_company_group": COMPANY_GROUP_FILE.name,
            "source_market_group": MARKET_GROUP_FILE.name,
            "matching": {"company_group_rows": int(len(company_matches)), "matched_groups": int(len(matched)), "unmatched_groups": unmatched_groups},
            "materiality_threshold_sales_2025": float(min_company_sales_2025),
            "summary": {
                "material_groups_analyzed": len(material),
                "groups_growing_slower_than_market": len([r for r in material if r["classification"] == "Growing slower than group market"]),
                "groups_growing_faster_than_market": len([r for r in material if r["classification"] == "Growing faster than group market"]),
                "groups_with_declining_within_group_share": len(share_losers),
            },
            "largest_negative_growth_gaps": negative_gap[:limit],
            "largest_positive_growth_gaps": positive_gap[:limit],
            "largest_within_group_share_declines": share_losers[:limit],
            "largest_company_sales_declines": by_sales_change[:limit],
            "largest_company_sales_growth_contributors": list(reversed(by_sales_change[-limit:])),
            "largest_negative_sales_gaps_vs_group_market_benchmark": ranked_group_benchmark_gaps[:limit],
            "largest_positive_sales_gaps_vs_group_market_benchmark": list(reversed(ranked_group_benchmark_gaps[-limit:])),
            "growth_gap_bridge": {
                "company_group_sales_2024": company_group_sales_2024,
                "company_group_sales_2025": company_group_sales_2025,
                "company_growth_percent_from_group_rows": company_total_growth,
                "total_market_growth_percent": total_market_growth,
                "expected_company_sales_2025_at_total_market_growth": expected_company_sales_at_total_market_growth,
                "actual_company_sales_2025": company_sales_2025_total,
                "actual_vs_total_market_growth_benchmark_sales_gap": actual_vs_total_market_benchmark,
                "expected_company_group_sales_2025_at_each_group_market_growth": expected_group_sales_2025,
                "expected_group_sales_change_at_group_market_growth": expected_group_sales_change,
                "actual_company_group_sales_change": actual_group_sales_change,
                "within_group_relative_performance_effect": within_group_relative_performance_effect,
                "group_mix_effect_vs_total_market": group_mix_effect_vs_total_market,
                "bridge_reconciliation_residual": bridge_reconciliation_residual,
                "interpretation": (
                    "Within-group relative performance compares actual company group sales with the sales level implied by each group's market growth. "
                    "The group-mix effect compares that group-specific benchmark with the overall-market-growth benchmark. "
                    "These are arithmetic bridge components, not causal attribution."
                ),
            },
            "groups": sorted(material, key=lambda r: -(r["company_sales_2025"] or 0)),
            "interpretation": "A negative growth gap means the company grew more slowly than the total market for that therapeutic group. Within-group share movement is calculated from company sales divided by market-group sales.",
            "limitations": [
                "Group labels must match exactly between the company-group and market-group datasets; unmatched labels are reported.",
                "This is group-level arithmetic and does not identify brand/product-level causes.",
                "Growth rates are unavailable where prior-period sales are zero or negative.",
                "A within-group share decline is descriptive and does not establish why it happened.",
            ],
        }
    except Exception as exc:
        return {"status": "error", "report_type": "Therapeutic Group Market Decomposition", "company": company, "message": f"{type(exc).__name__}: {exc}"}
