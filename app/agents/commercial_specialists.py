"""Specialist evidence extractors for the commercial diagnosis workflow.

These agents intentionally reuse outputs from existing analytics modules. They
organize validated evidence; they do not recompute metrics or infer causality.
"""
from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    except (TypeError, ValueError):
        return None


def market_agent(diagnosis: dict) -> dict:
    """Summarize total-market growth, company-vs-market gap and reconciliation."""
    decomposition = _as_dict(diagnosis.get("market_growth_decomposition"))
    market = _as_dict(decomposition.get("market"))
    company = _as_dict(decomposition.get("company_performance"))
    gap = _as_dict(decomposition.get("decomposition"))
    reconciliation = _as_dict(decomposition.get("reconciliation"))
    if decomposition.get("status") != "success":
        return {"agent": "market", "status": "unavailable", "evidence": {}, "message": decomposition.get("message", "Market decomposition unavailable.")}
    return {
        "agent": "market",
        "status": "success",
        "evidence": {
            "market_sales_2024": _num(market.get("sales_2024")),
            "market_sales_2025": _num(market.get("sales_2025")),
            "market_growth_percent": _num(market.get("growth_percent")),
            "company_growth_percent": _num(company.get("growth_percent")),
            "growth_gap_percentage_points": _num(gap.get("growth_gap_percentage_points")),
            "sales_gap_vs_market_growth": _num(gap.get("sales_gap_vs_market_growth")),
            "market_share_2024_percent": _num(gap.get("market_share_2024_percent")),
            "market_share_2025_percent": _num(gap.get("market_share_2025_percent")),
            "reconciles_within_tolerance": reconciliation.get("reconciles_within_tolerance"),
        },
        "interpretation": "Describes relative growth performance; it does not identify the cause of any growth gap.",
        "source": decomposition.get("sources", decomposition.get("source")),
    }


def company_agent(diagnosis: dict) -> dict:
    """Summarize company sales, share and value-versus-unit indicators."""
    underlying = _as_dict(diagnosis.get("underlying_analysis"))
    metrics = _as_dict(underlying.get("company"))
    units = _as_dict(underlying.get("value_vs_units"))
    if not metrics and not units:
        return {"agent": "company", "status": "unavailable", "evidence": {}, "message": "Company metrics unavailable."}
    fields = (
        "sales_2024", "sales_2025", "sales_change", "growth_percent",
        "market_share_2024_percent", "market_share_2025_percent",
        "share_change_percentage_points", "competitive_category",
    )
    evidence = {field: metrics.get(field) for field in fields if metrics.get(field) is not None}
    for field in ("units_2024", "units_2025", "unit_change", "unit_growth_percent",
                  "calculated_unit_growth_percent", "calculated_value_growth_percent",
                  "value_per_unit_change_percent"):
        if units.get(field) is not None:
            evidence[field] = units[field]
    return {
        "agent": "company", "status": "success", "evidence": evidence,
        "interpretation": "Value-versus-unit differences are descriptive; value per unit is not proof of a price increase.",
        "source": metrics.get("data_source", units.get("data_source")),
    }


def therapeutic_group_agent(diagnosis: dict) -> dict:
    """Summarize leading growth contributors and declines by therapeutic group."""
    groups = _as_dict(diagnosis.get("therapeutic_group_analysis"))
    decomposition = _as_dict(diagnosis.get("therapeutic_group_market_decomposition"))
    contributors = _as_list(groups.get("largest_growth_contributors"))
    declines = _as_list(groups.get("largest_declines"))
    fast = _as_list(groups.get("fastest_growing_material_groups"))
    if not groups and not decomposition:
        return {"agent": "therapeutic_groups", "status": "unavailable", "evidence": {}, "message": "Therapeutic-group evidence unavailable."}
    return {
        "agent": "therapeutic_groups", "status": "success",
        "evidence": {
            "total_groups": groups.get("total_groups"),
            "largest_growth_contributors": contributors,
            "largest_declines": declines,
            "fastest_growing_material_groups": fast,
            "market_decomposition_summary": decomposition.get("summary"),
            "largest_negative_growth_gaps": _as_list(decomposition.get("largest_negative_growth_gaps"))[:5],
            "largest_positive_growth_gaps": _as_list(decomposition.get("largest_positive_growth_gaps"))[:5],
            "largest_within_group_share_declines": _as_list(decomposition.get("largest_within_group_share_declines"))[:5],
        },
        "interpretation": "Group-level comparisons show where company growth differs from its group's market growth; they do not establish brand-level drivers or causality.",
        "source": ["IMS_Company_Group_Analysis.csv", "IMS_Group_Analysis.csv"],
    }


def competitor_agent(diagnosis: dict) -> dict:
    """Summarize available competitor scorecard evidence without inventing peers."""
    scorecard = _as_dict(diagnosis.get("competitor_analysis"))
    if not scorecard:
        return {"agent": "competitors", "status": "unavailable", "evidence": {}, "message": "Competitor evidence unavailable."}
    # Preserve the original scorecard structure so consumers can inspect its schema.
    return {
        "agent": "competitors", "status": "success", "evidence": scorecard,
        "interpretation": "Scorecard comparisons depend on the selected competitors, metrics, weights and eligibility rules.",
        "source": scorecard.get("data_source"),
    }


def run_commercial_specialists(diagnosis: dict) -> dict:
    """Run the four specialist evidence extractors on one diagnosis payload."""
    agents = [
        market_agent(diagnosis),
        company_agent(diagnosis),
        therapeutic_group_agent(diagnosis),
        competitor_agent(diagnosis),
    ]
    return {
        "status": "success" if any(agent["status"] == "success" for agent in agents) else "unavailable",
        "agents": agents,
        "successful_agents": [agent["agent"] for agent in agents if agent["status"] == "success"],
        "unavailable_agents": [agent["agent"] for agent in agents if agent["status"] != "success"],
        "design_note": "Specialists organize existing analytical evidence; metrics are not independently recalculated.",
    }
