"""Coordinate existing commercial analytics into one evidence-led summary.

This module deliberately reuses existing specialist outputs. It does not
recalculate source metrics or infer causality from correlations.
"""
from __future__ import annotations

from typing import Any

from app.agents.commercial_specialists import run_commercial_specialists


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    except (TypeError, ValueError):
        return None


def coordinate_commercial_diagnosis(diagnosis: dict) -> dict:
    """Add a coordinated executive summary to a successful diagnosis.

    The original diagnosis payload is preserved; a new ``coordinated_summary``
    field is appended for downstream CLI, API, and dashboard consumers.
    """
    if not isinstance(diagnosis, dict):
        raise TypeError("diagnosis must be a dictionary")

    if diagnosis.get("status") != "success":
        return diagnosis

    underlying = diagnosis.get("underlying_analysis") or {}
    company = underlying.get("company") or {}
    decomposition = diagnosis.get("market_growth_decomposition") or {}
    market = decomposition.get("market") or {}
    company_perf = decomposition.get("company_performance") or {}
    gap = decomposition.get("decomposition") or {}
    groups = diagnosis.get("therapeutic_group_analysis") or {}
    group_decomposition = diagnosis.get("therapeutic_group_market_decomposition") or {}
    competitors = diagnosis.get("competitor_analysis") or {}

    company_name = diagnosis.get("company") or company.get("company") or "Company"
    company_growth = _number(company_perf.get("growth_percent"))
    market_growth = _number(market.get("growth_percent"))
    growth_gap = _number(gap.get("growth_gap_percentage_points"))
    share_change = _number(company.get("share_change_percentage_points"))
    value_units = underlying.get("value_vs_units") or {}
    unit_growth = _number(
        value_units.get("calculated_unit_growth_percent", value_units.get("unit_growth_percent"))
    )

    facts: list[str] = []
    hypotheses: list[str] = []
    priorities: list[str] = []

    if company_growth is not None:
        facts.append(f"{company_name} sales grew {company_growth:.2f}%.")
    if market_growth is not None:
        facts.append(f"The total market grew {market_growth:.2f}%.")
    if growth_gap is not None:
        if growth_gap < 0:
            facts.append(f"Company growth trailed the market by {abs(growth_gap):.2f} percentage points.")
            hypotheses.append("The below-market growth rate is consistent with the observed share decline, but does not identify its cause.")
            priorities.append("Decompose company-versus-market performance by therapeutic group and, where available, brand/product.")
        elif growth_gap > 0:
            facts.append(f"Company growth exceeded the market by {growth_gap:.2f} percentage points.")
    if share_change is not None:
        facts.append(f"Market share changed by {share_change:+.4f} percentage points.")
    if unit_growth is not None and unit_growth < 0:
        facts.append(f"Reported unit volume declined {abs(unit_growth):.2f}%.")
        hypotheses.append("Value growth may be masking weaker unit performance; the available aggregate data cannot determine whether price, mix, or product-level changes explain it.")
        priorities.append("Validate unit trends by brand/product and review price/mix effects before drawing conclusions.")

    contributors = groups.get("largest_growth_contributors") or []
    declines = groups.get("largest_declines") or []
    if contributors:
        first = contributors[0]
        name = first.get("group") or first.get("name") or "the leading therapeutic group"
        change = _number(first.get("sales_change"))
        if change is not None:
            facts.append(f"The largest listed therapeutic-group growth contributor was {name} (sales change {change:.2f}).")
        priorities.append("Check whether growth is broad-based or concentrated in a small number of therapeutic groups.")
    if declines:
        priorities.append("Investigate the largest declining therapeutic groups alongside their market and competitor trends.")

    if group_decomposition.get("status") == "success":
        group_summary = group_decomposition.get("summary") or {}
        negative_gaps = group_decomposition.get("largest_negative_growth_gaps") or []
        if negative_gaps:
            lead = negative_gaps[0]
            group_gap = _number(lead.get("growth_gap_percentage_points"))
            group_name = lead.get("group", "a therapeutic group")
            if group_gap is not None:
                facts.append(f"The largest listed negative growth gap among material therapeutic groups was {group_name} ({group_gap:.2f} percentage points versus its group market).")
            priorities.append("Prioritize material therapeutic groups where company growth trails the corresponding group market.")
        share_losers = group_decomposition.get("largest_within_group_share_declines") or []
        if share_losers:
            priorities.append("Investigate therapeutic groups with the largest within-group share declines.")
        benchmark_gaps = group_decomposition.get("largest_negative_sales_gaps_vs_group_market_benchmark") or []
        if benchmark_gaps:
            lead_gap = benchmark_gaps[0]
            gap_amount = _number(lead_gap.get("sales_vs_group_market_growth_benchmark"))
            group_name = lead_gap.get("group", "a therapeutic group")
            if gap_amount is not None:
                facts.append(f"The largest listed negative group-level sales gap versus its market-growth benchmark was {group_name} ({gap_amount:.2f} sales units).")
            priorities.append("Rank material groups by sales shortfall versus their own market-growth benchmarks, then validate with brand-level evidence.")

    if not facts:
        facts.append("The available diagnosis did not contain enough validated metrics to generate a quantitative executive summary.")
    if not priorities:
        priorities.append("Review company, market, therapeutic-group, and competitor evidence for material changes and validate any proposed explanation with more granular data.")

    specialist_analysis = run_commercial_specialists(diagnosis)

    return {
        **diagnosis,
        "specialist_analysis": specialist_analysis,
        "coordinated_summary": {
            "status": "success",
            "company": company_name,
            "data_period": diagnosis.get("data_period"),
            "verified_facts": facts,
            "interpretations_and_hypotheses": hypotheses,
            "priority_investigations": list(dict.fromkeys(priorities)),
            "market_growth": market_growth,
            "company_growth": company_growth,
            "growth_gap_percentage_points": growth_gap,
            "sales_gap_vs_market_growth": _number(gap.get("sales_gap_vs_market_growth")),
            "market_share_change_percentage_points": share_change,
            "reconciliation": decomposition.get("reconciliation"),
            "therapeutic_group_decomposition_summary": group_decomposition.get("summary"),
            "largest_therapeutic_group_growth_gaps": (group_decomposition.get("largest_negative_growth_gaps") or [])[:5],
            "largest_within_group_share_declines": (group_decomposition.get("largest_within_group_share_declines") or [])[:5],
            "largest_group_sales_gaps_vs_market_benchmark": (group_decomposition.get("largest_negative_sales_gaps_vs_group_market_benchmark") or [])[:5],
            "growth_gap_bridge": group_decomposition.get("growth_gap_bridge"),
            "limitations": [
                "The analysis describes observed relationships and does not establish causation.",
                "Therapeutic-group-level results do not by themselves identify brand-level drivers.",
                "Therapeutic-group growth gaps are descriptive and require exact label matching between IMS files.",
                "Value-versus-unit differences do not prove a price increase; mix and unit definitions may affect the result.",
            ],
        },
    }
