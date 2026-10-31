from app.agents.company_deep_dive import build_company_deep_dive


def generate_commercial_brief(
    company: str,
    competitors: list[str] | None = None,
) -> dict:
    """Create an evidence-led commercial brief."""

    report = build_company_deep_dive(
        company=company,
        competitors=competitors,
    )

    if report.get("status") != "success":
        return report

    metrics = report["company"]
    groups = report["therapeutic_groups"]
    interpretation = report["commercial_interpretation"]

    actions = []

    growth = metrics.get("growth_percent")
    share_change = metrics.get("share_change_percentage_points")

    if (
        growth is not None
        and share_change is not None
        and growth > 0
        and share_change < 0
    ):
        actions.append({
            "priority": "High",
            "action": (
                "Investigate why sales growth is not translating "
                "into market-share gains."
            ),
            "evidence": {
                "sales_growth_percent": growth,
                "share_change_percentage_points": share_change,
            },
        })

    if groups.get("status") == "success":
        declining = groups.get("declining_groups", [])

        if declining:
            actions.append({
                "priority": "Review",
                "action": (
                    "Review the largest declining therapeutic groups "
                    "for potential commercial risks."
                ),
                "evidence": declining[:3],
            })

        contributors = groups.get("largest_growth_contributors", [])

        if contributors:
            actions.append({
                "priority": "Review",
                "action": (
                    "Assess the sustainability and concentration of "
                    "growth in the largest contributing groups."
                ),
                "evidence": contributors[:3],
            })

    return {
        "status": "success",
        "company": metrics.get("company"),
        "report_type": "Commercial Strategy Brief",
        "key_findings": interpretation["observed_findings"],
        "risks": interpretation["potential_risks"],
        "recommended_investigations": actions,
        "limitations": report["limitations"],
        "underlying_analysis": report,
    }