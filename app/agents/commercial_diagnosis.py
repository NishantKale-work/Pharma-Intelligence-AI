
from typing import Any

from app.agents.company_deep_dive import build_company_deep_dive
from app.agents.market_growth_decomposition import build_market_growth_decomposition
from app.agents.therapeutic_group_decomposition import build_therapeutic_group_decomposition


def _number(value: Any) -> float | None:
    """Convert a value to a finite number."""
    try:
        number = float(value)

        if number != number or abs(number) == float("inf"):
            return None

        return number

    except (TypeError, ValueError):
        return None


def _top_groups(
    groups: dict,
    ranking: str,
    limit: int = 3,
) -> list[dict]:
    """Safely retrieve a therapeutic-group ranking."""
    if groups.get("status") != "success":
        return []

    items = groups.get(ranking, [])

    if not isinstance(items, list):
        return []

    return items[:limit]


def _diagnose_company(metrics: dict, value_units: dict) -> dict:
    """Interpret sales, market share and unit performance."""
    growth = _number(metrics.get("growth_percent"))
    share_change = _number(
        metrics.get("share_change_percentage_points")
    )

    unit_growth = _number(
        value_units.get("calculated_unit_growth_percent")
    )

    value_growth = _number(
        value_units.get("calculated_value_growth_percent")
    )

    findings = []
    hypotheses = []
    limitations = []

    if growth is not None and share_change is not None:
        if growth > 0 and share_change < 0:
            findings.append({
                "signal": "Growing sales, declining market share",
                "interpretation": (
                    "Sales value increased, but the company's "
                    "share of the market decreased."
                ),
                "priority": "High",
            })

            hypotheses.extend([
                {
                    "hypothesis": (
                        "Competitors may be growing faster."
                    ),
                    "evidence_needed": (
                        "Compare company growth with competitor growth "
                        "and total market growth."
                    ),
                },
                {
                    "hypothesis": (
                        "Growth may be concentrated in a limited "
                        "number of therapeutic groups."
                    ),
                    "evidence_needed": (
                        "Review group-level sales changes and "
                        "contributions to net sales growth."
                    ),
                },
            ])

        elif growth > 0 and share_change > 0:
            findings.append({
                "signal": "Growing sales and gaining market share",
                "interpretation": (
                    "Sales value increased alongside market-share gains."
                ),
                "priority": "Positive",
            })

        elif growth < 0 and share_change < 0:
            findings.append({
                "signal": "Declining sales and market share",
                "interpretation": (
                    "Both sales value growth and market-share "
                    "movement were negative."
                ),
                "priority": "High",
            })

        elif growth < 0 and share_change > 0:
            findings.append({
                "signal": "Declining sales but gaining market share",
                "interpretation": (
                    "Sales value declined even though market share "
                    "increased. Validate the underlying market trend."
                ),
                "priority": "Review",
            })

    if value_growth is not None and unit_growth is not None:
        if value_growth > unit_growth:
            findings.append({
                "signal": "Value growth exceeds unit growth",
                "interpretation": (
                    "Sales value grew faster than units. Aggregate "
                    "value per unit may have increased."
                ),
                "priority": "Review",
            })

            limitations.append(
                "Value growth exceeding unit growth does not prove "
                "a price increase. Product mix, pricing and unit "
                "definitions can influence the result."
            )

        elif value_growth < unit_growth:
            findings.append({
                "signal": "Unit growth exceeds value growth",
                "interpretation": (
                    "Units grew faster than sales value. Investigate "
                    "product mix and value realization."
                ),
                "priority": "Review",
            })

    if unit_growth is not None and unit_growth < 0:
        findings.append({
            "signal": "Declining unit volume",
            "interpretation": (
                "Reported units declined year over year, even if "
                "sales value may have increased."
            ),
            "priority": "Review",
        })

        hypotheses.append({
            "hypothesis": (
                "Value growth may be masking weaker unit performance."
            ),
            "evidence_needed": (
                "Validate unit trends by brand, product and "
                "therapeutic group."
            ),
        })

    if not findings:
        findings.append({
            "signal": "Insufficient diagnostic signals",
            "interpretation": (
                "The available metrics do not support a clear "
                "performance diagnosis."
            ),
            "priority": "Review",
        })

    return {
        "observed_signals": findings,
        "hypotheses_to_investigate": hypotheses,
        "limitations": limitations,
    }


def build_commercial_diagnosis(
    company: str = "ALKEM*",
    competitors: list[str] | None = None,
    therapeutic_group_limit: int = 10,
    min_group_sales: float = 10.0,
) -> dict:
    """
    Build an evidence-led commercial diagnosis from existing analytics.

    This function identifies observable performance patterns and
    investigation priorities. It does not claim to establish causation.
    """
    report = build_company_deep_dive(
        company=company,
        competitors=competitors,
        therapeutic_group_limit=therapeutic_group_limit,
        min_group_sales=min_group_sales,
    )

    if report.get("status") != "success":
        return {
            "status": "error",
            "report_type": "Commercial Diagnosis",
            "message": "Unable to build the commercial diagnosis.",
            "details": report,
        }

    metrics = report.get("company", {})
    value_units = report.get("value_vs_units", {})
    groups = report.get("therapeutic_groups", {})
    scorecard = report.get("competitor_scorecard", {})

    company_diagnosis = _diagnose_company(
        metrics,
        value_units,
    )
    market_decomposition = build_market_growth_decomposition(company)
    therapeutic_market_decomposition = build_therapeutic_group_decomposition(company)
    if market_decomposition.get("status") == "success":
        decomposition = market_decomposition.get("decomposition", {})
        gap = _number(decomposition.get("growth_gap_percentage_points"))
        market_growth = _number(decomposition.get("market_growth_percent"))
        company_growth = _number(decomposition.get("company_growth_percent"))
        if gap is not None and market_growth is not None and company_growth is not None:
            company_diagnosis["observed_signals"].append({
                "signal": "Company growth versus total-market growth",
                "interpretation": (
                    f"Company growth was {company_growth:.2f}% versus market growth of "
                    f"{market_growth:.2f}%, a gap of {gap:.2f} percentage points."
                ),
                "priority": "High" if gap < 0 else "Positive" if gap > 0 else "Neutral",
                "evidence_type": "calculated_fact",
            })
            company_diagnosis["market_growth_hypothesis_note"] = (
                "A below-market growth rate is consistent with share loss; it does not by itself explain the underlying cause."
            )

    growth_contributors = _top_groups(
        groups,
        "largest_growth_contributors",
    )

    declining_groups = _top_groups(
        groups,
        "declining_groups",
    )

    fastest_growing_groups = _top_groups(
        groups,
        "fastest_growing_material_groups",
    )

    investigations = []

    growth = _number(metrics.get("growth_percent"))
    share_change = _number(
        metrics.get("share_change_percentage_points")
    )

    if (
        growth is not None
        and share_change is not None
        and growth > 0
        and share_change < 0
    ):
        investigations.append({
            "priority": "High",
            "question": (
                "Why is sales growth not translating into "
                "market-share gains?"
            ),
            "actions": [
                "Compare company growth against total market growth.",
                "Compare growth and share movement against competitors.",
                "Identify therapeutic groups contributing to growth "
                "and those offsetting it.",
            ],
            "evidence": {
                "sales_growth_percent": growth,
                "share_change_percentage_points": share_change,
            },
        })

    if market_decomposition.get("status") == "success":
        decomposition = market_decomposition.get("decomposition", {})
        gap = _number(decomposition.get("growth_gap_percentage_points"))
        if gap is not None and gap < 0:
            investigations.append({
                "priority": "High",
                "question": "Which factors explain the below-market growth gap?",
                "actions": [
                    "Separate performance by therapeutic group against each group's market growth.",
                    "Compare Alkem's group-level share movement with market-group share and growth.",
                    "Use brand-level, volume, price/mix and distribution data to test possible drivers.",
                ],
                "evidence": {
                    "company_growth_percent": decomposition.get("company_growth_percent"),
                    "market_growth_percent": decomposition.get("market_growth_percent"),
                    "growth_gap_percentage_points": gap,
                    "sales_gap_vs_market_growth": decomposition.get("sales_gap_vs_market_growth"),
                },
            })

    if therapeutic_market_decomposition.get("status") == "success":
        group_summary = therapeutic_market_decomposition.get("summary", {})
        negative_gaps = therapeutic_market_decomposition.get("largest_negative_growth_gaps", [])
        share_losers = therapeutic_market_decomposition.get("largest_within_group_share_declines", [])
        benchmark_gaps = therapeutic_market_decomposition.get("largest_negative_sales_gaps_vs_group_market_benchmark", [])
        growth_gap_bridge = therapeutic_market_decomposition.get("growth_gap_bridge", {})
        if negative_gaps or share_losers or benchmark_gaps:
            investigations.append({
                "priority": "High",
                "question": "Which material therapeutic groups are underperforming their own markets?",
                "actions": [
                    "Prioritize groups with the largest negative company-versus-group-market growth gaps.",
                    "Review within-group share declines alongside company sales changes and competitor trends.",
                    "Validate the most material group findings with brand/product-level data before assigning causes.",
                ],
                "evidence": {
                    "group_decomposition_summary": group_summary,
                    "largest_negative_growth_gaps": negative_gaps[:5],
                    "largest_within_group_share_declines": share_losers[:5],
                    "largest_sales_gaps_vs_group_market_benchmark": benchmark_gaps[:5],
                    "growth_gap_bridge": growth_gap_bridge,
                },
            })

    if growth_contributors:
        investigations.append({
            "priority": "Medium",
            "question": (
                "How dependent is company growth on its largest "
                "therapeutic-group contributors?"
            ),
            "actions": [
                "Review the largest contributors to absolute sales change.",
                "Assess whether growth is broad-based across groups.",
                "Validate findings with brand-level or product-level data."
            ],
            "evidence": growth_contributors,
        })

    if declining_groups:
        investigations.append({
            "priority": "Medium",
            "question": (
                "Which declining therapeutic groups warrant "
                "commercial investigation?"
            ),
            "actions": [
                "Prioritize groups by absolute sales decline.",
                "Review competitor performance within those groups.",
                "Investigate brand-level trends before assigning causes.",
            ],
            "evidence": declining_groups,
        })

    if fastest_growing_groups:
        investigations.append({
            "priority": "Opportunity review",
            "question": (
                "Which materially growing therapeutic groups "
                "merit further opportunity assessment?"
            ),
            "actions": [
                "Validate the sustainability of observed growth.",
                "Assess the company's position against competitors.",
                "Review market size and brand-level performance."
            ],
            "evidence": fastest_growing_groups,
        })

    if not investigations:
        investigations.append({
            "priority": "Review",
            "question": (
                "What additional evidence is needed to identify "
                "the main commercial performance drivers?"
            ),
            "actions": [
                "Review company and competitor metrics.",
                "Validate therapeutic-group trends.",
                "Obtain brand-level or market-level data if required.",
            ],
            "evidence": {},
        })

    return {
        "status": "success",
        "report_type": "Commercial Diagnosis",
        "company": metrics.get("company", company),
        "data_period": report.get("data_period"),
        "executive_diagnosis": company_diagnosis,
        "market_growth_decomposition": market_decomposition,
        "therapeutic_group_market_decomposition": therapeutic_market_decomposition,
        "therapeutic_group_analysis": {
            "status": groups.get("status"),
            "largest_growth_contributors": growth_contributors,
            "largest_declines": declining_groups,
            "fastest_growing_material_groups": fastest_growing_groups,
            "total_groups": groups.get("total_groups"),
        },
        "competitor_analysis": scorecard,
        "investigation_priorities": investigations,
        "limitations": report.get("limitations", []) + [
            "Observed associations do not establish causation.",
            "Competitor rankings depend on the metrics and weights used.",
            "Therapeutic-group findings do not explain brand-level drivers.",
            "Market-growth decomposition is descriptive and does not establish causation.",
            "Therapeutic-group comparisons require exact group-label matching and do not establish brand-level causes.",
        ] + company_diagnosis["limitations"],
        "underlying_analysis": report,
    }


if __name__ == "__main__":
    import json

    diagnosis = build_commercial_diagnosis(
        company="ALKEM*",
        competitors=["CIPLA", "SUN*"],
    )

    print(
        json.dumps(
            diagnosis,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
