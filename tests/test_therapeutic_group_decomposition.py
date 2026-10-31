from app.agents.therapeutic_group_decomposition import build_therapeutic_group_decomposition
from app.agents.commercial_diagnosis import build_commercial_diagnosis
from app.agents.commercial_coordinator import coordinate_commercial_diagnosis


def test_therapeutic_group_decomposition_matches_all_alkem_groups():
    result = build_therapeutic_group_decomposition("ALKEM*")
    assert result["status"] == "success"
    assert result["matching"]["company_group_rows"] == 153
    assert result["matching"]["matched_groups"] == 153
    assert result["matching"]["unmatched_groups"] == []
    assert result["summary"]["material_groups_analyzed"] > 0
    assert result["largest_negative_growth_gaps"]
    assert result["largest_within_group_share_declines"]
    for row in result["groups"]:
        assert row["group"]
        assert row["classification"]


def test_group_growth_gap_and_share_change_are_arithmetically_consistent():
    result = build_therapeutic_group_decomposition("ALKEM*")
    row = next(item for item in result["groups"] if item["group"].startswith("A02B "))
    assert round(row["company_growth_percent"], 2) == 10.54
    assert round(row["market_group_growth_percent"], 2) == 5.79
    assert round(row["growth_gap_percentage_points"], 2) == 4.75
    assert row["within_group_share_change_percentage_points"] is not None


def test_commercial_diagnosis_and_coordinator_include_group_decomposition():
    diagnosis = build_commercial_diagnosis("ALKEM*", ["CIPLA", "SUN*"])
    assert diagnosis["status"] == "success"
    decomposition = diagnosis["therapeutic_group_market_decomposition"]
    assert decomposition["status"] == "success"
    assert decomposition["matching"]["matched_groups"] == 153
    assert any(
        item.get("question") == "Which material therapeutic groups are underperforming their own markets?"
        for item in diagnosis["investigation_priorities"]
    )

    coordinated = coordinate_commercial_diagnosis(diagnosis)
    assert coordinated["specialist_analysis"]["status"] == "success"
    therapeutic_agent = next(
        item for item in coordinated["specialist_analysis"]["agents"]
        if item["agent"] == "therapeutic_groups"
    )
    assert therapeutic_agent["status"] == "success"
    assert therapeutic_agent["evidence"]["market_decomposition_summary"]
    assert coordinated["coordinated_summary"]["therapeutic_group_decomposition_summary"]


def test_group_sales_gap_ranking_and_bridge_reconcile():
    result = build_therapeutic_group_decomposition("ALKEM*")
    assert result["status"] == "success"

    negative = result["largest_negative_sales_gaps_vs_group_market_benchmark"]
    positive = result["largest_positive_sales_gaps_vs_group_market_benchmark"]
    assert negative
    assert positive
    assert all(
        negative[index]["sales_vs_group_market_growth_benchmark"]
        <= negative[index + 1]["sales_vs_group_market_growth_benchmark"]
        for index in range(len(negative) - 1)
    )
    assert all(
        positive[index]["sales_vs_group_market_growth_benchmark"]
        >= positive[index + 1]["sales_vs_group_market_growth_benchmark"]
        for index in range(len(positive) - 1)
    )

    bridge = result["growth_gap_bridge"]
    assert abs(bridge["bridge_reconciliation_residual"]) < 1e-6
    assert round(bridge["actual_vs_total_market_growth_benchmark_sales_gap"], 2) == -96.75
    assert round(
        bridge["within_group_relative_performance_effect"] + bridge["group_mix_effect_vs_total_market"], 6
    ) == round(bridge["actual_vs_total_market_growth_benchmark_sales_gap"], 6)
