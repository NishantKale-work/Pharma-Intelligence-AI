"""Data preparation for the Pharma Commercial Intelligence dashboard.

This module intentionally contains no Streamlit dependency so its data contract
can be tested independently from the UI.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.agents.commercial_coordinator import coordinate_commercial_diagnosis
from app.agents.commercial_diagnosis import build_commercial_diagnosis
from app.agents.company_analysis import load_company_data


def available_companies() -> list[str]:
    """Return source company labels sorted alphabetically."""
    df = load_company_data()
    return sorted(df["COMPANY"].dropna().astype(str).str.strip().unique().tolist())


def _list_of_dicts(value: Any) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def build_dashboard_payload(
    company: str = "ALKEM*",
    competitors: list[str] | None = None,
) -> dict:
    """Build dashboard-ready metrics and tables using existing analytics."""
    competitors = competitors or []
    diagnosis = build_commercial_diagnosis(company, competitors)
    if diagnosis.get("status") != "success":
        return {
            "status": "error",
            "company": company,
            "message": diagnosis.get("message", "Unable to build commercial diagnosis."),
            "details": diagnosis,
        }

    coordinated = coordinate_commercial_diagnosis(diagnosis)
    market = coordinated.get("market_growth_decomposition") or {}
    market_metrics = market.get("market") or {}
    company_metrics = market.get("company_performance") or {}
    decomposition = market.get("decomposition") or {}
    underlying = coordinated.get("underlying_analysis") or {}
    value_units = underlying.get("value_vs_units") or {}
    group_decomposition = coordinated.get("therapeutic_group_market_decomposition") or {}
    competitor_analysis = coordinated.get("competitor_analysis") or {}
    summary = coordinated.get("coordinated_summary") or {}
    executive = coordinated.get("executive_diagnosis") or {}

    group_rows = _list_of_dicts(group_decomposition.get("groups"))
    group_df = pd.DataFrame(group_rows)
    if not group_df.empty:
        for column in (
            "company_growth_percent", "market_group_growth_percent",
            "growth_gap_percentage_points", "company_sales_change",
            "sales_vs_group_market_growth_benchmark",
            "within_group_share_change_percentage_points", "company_sales_2025",
        ):
            if column in group_df.columns:
                group_df[column] = pd.to_numeric(group_df[column], errors="coerce")
        group_df = group_df.sort_values(
            "sales_vs_group_market_growth_benchmark", ascending=True, na_position="last"
        )

    competitor_rows = _list_of_dicts(competitor_analysis.get("companies"))
    competitor_df = pd.DataFrame(competitor_rows)

    return {
        "status": "success",
        "company": coordinated.get("company", company),
        "data_period": coordinated.get("data_period", "MAT Sep 2025 vs MAT Sep 2024"),
        "metrics": {
            "company_sales_2024": company_metrics.get("sales_2024"),
            "company_sales_2025": company_metrics.get("sales_2025"),
            "company_sales_change": company_metrics.get("sales_change"),
            "company_growth_percent": company_metrics.get("growth_percent"),
            "market_growth_percent": market_metrics.get("growth_percent"),
            "growth_gap_percentage_points": decomposition.get("growth_gap_percentage_points"),
            "sales_gap_vs_market_growth": decomposition.get("sales_gap_vs_market_growth"),
            "market_share_2024_percent": company_metrics.get("market_share_2024_percent"),
            "market_share_2025_percent": company_metrics.get("market_share_2025_percent"),
            "share_change_percentage_points": company_metrics.get("share_change_percentage_points"),
            "unit_growth_percent": value_units.get("calculated_unit_growth_percent", value_units.get("unit_growth_percent")),
            "value_per_unit_change_percent": value_units.get("value_per_unit_change_percent"),
            "reconciles": (market.get("reconciliation") or {}).get("reconciles_within_tolerance"),
        },
        "market": market,
        "group_summary": group_decomposition.get("summary") or {},
        "growth_gap_bridge": group_decomposition.get("growth_gap_bridge") or {},
        "groups": group_df,
        "competitors": competitor_df,
        "verified_facts": summary.get("verified_facts", []),
        "hypotheses": summary.get("interpretations_and_hypotheses", executive.get("hypotheses_to_investigate", [])),
        "investigations": summary.get("priority_investigations", []),
        "limitations": summary.get("limitations", coordinated.get("limitations", [])),
        "specialists": (coordinated.get("specialist_analysis") or {}).get("successful_agents", []),
        "sources": [
            "IMS_Company_Analysis.csv",
            "IMS_Company_Group_Analysis.csv",
            "IMS_Company_Value_Unit_Analysis.csv",
            "IMS_Group_Analysis.csv",
        ],
    }
