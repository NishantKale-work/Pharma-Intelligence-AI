from app.agents.commercial_specialists import (
    company_agent,
    competitor_agent,
    market_agent,
    run_commercial_specialists,
    therapeutic_group_agent,
)
from app.agents.commercial_coordinator import coordinate_commercial_diagnosis


def sample_diagnosis():
    return {
        "status": "success",
        "company": "ALKEM*",
        "market_growth_decomposition": {
            "status": "success",
            "market": {"sales_2024": 1000, "sales_2025": 1100, "growth_percent": 10},
            "company_performance": {"growth_percent": 8},
            "decomposition": {"growth_gap_percentage_points": -2, "sales_gap_vs_market_growth": 20},
            "reconciliation": {"reconciles_within_tolerance": True},
        },
        "underlying_analysis": {
            "company": {"sales_2024": 100, "sales_2025": 108, "growth_percent": 8, "share_change_percentage_points": -0.1},
            "value_vs_units": {"calculated_unit_growth_percent": -1.2, "value_per_unit_change_percent": 9.3},
        },
        "therapeutic_group_analysis": {
            "total_groups": 2,
            "largest_growth_contributors": [{"group": "A02B", "sales_change": 10}],
            "largest_declines": [{"group": "M05C", "sales_change": -3}],
            "fastest_growing_material_groups": [],
        },
        "competitor_analysis": {"status": "success", "companies": [{"company": "SUN*", "growth_percent": 12}]},
    }


def test_each_specialist_returns_domain_evidence():
    diagnosis = sample_diagnosis()
    assert market_agent(diagnosis)["evidence"]["market_growth_percent"] == 10
    assert company_agent(diagnosis)["evidence"]["calculated_unit_growth_percent"] == -1.2
    assert therapeutic_group_agent(diagnosis)["evidence"]["largest_declines"][0]["group"] == "M05C"
    assert competitor_agent(diagnosis)["evidence"]["companies"][0]["company"] == "SUN*"


def test_specialist_orchestrator_reports_success_and_unavailable_agents():
    result = run_commercial_specialists(sample_diagnosis())
    assert result["status"] == "success"
    assert result["successful_agents"] == ["market", "company", "therapeutic_groups", "competitors"]
    assert result["unavailable_agents"] == []


def test_coordinator_includes_specialist_analysis_without_losing_summary():
    result = coordinate_commercial_diagnosis(sample_diagnosis())
    assert result["specialist_analysis"]["status"] == "success"
    assert result["coordinated_summary"]["growth_gap_percentage_points"] == -2
