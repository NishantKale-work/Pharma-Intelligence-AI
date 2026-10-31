from app.agents.company_deep_dive import (
    build_company_deep_dive,
    get_therapeutic_group_metrics,
)


def test_alkem_deep_dive_returns_required_sections():
    report = build_company_deep_dive(
        company="ALKEM*",
        competitors=["CIPLA", "SUN*"],
    )

    assert report["status"] == "success"
    assert report["company"]["company"]
    assert "therapeutic_groups" in report
    assert "competitor_scorecard" in report
    assert "value_vs_units" in report


def test_group_materiality_threshold_is_applied():
    groups = get_therapeutic_group_metrics(
        company="ALKEM*",
        min_group_sales=10.0,
    )

    assert groups["status"] == "success"

    for item in groups["fastest_growing_material_groups"]:
        assert item["sales_2025"] >= 10.0


def test_group_contributions_are_calculated():
    groups = get_therapeutic_group_metrics(
        company="ALKEM*",
        min_group_sales=10.0,
        company_sales_change=596.9945,
    )

    assert groups["status"] == "success"

    for item in groups["largest_growth_contributors"]:
        assert (
            item["contribution_to_company_net_sales_change_percent"]
            is not None
        )