from app.agents.commercial_coordinator import coordinate_commercial_diagnosis


def test_coordinator_preserves_existing_payload_and_separates_facts_from_hypotheses():
    source = {
        "status": "success",
        "company": "ALKEM*",
        "data_period": "MAT Sep 2025 vs MAT Sep 2024",
        "underlying_analysis": {
            "company": {"share_change_percentage_points": -0.0399},
            "value_vs_units": {"calculated_unit_growth_percent": -1.4465},
        },
        "market_growth_decomposition": {
            "status": "success",
            "market": {"growth_percent": 7.8},
            "company_performance": {"growth_percent": 6.71},
            "decomposition": {
                "growth_gap_percentage_points": -1.09,
                "sales_gap_vs_market_growth": 96.75,
            },
            "reconciliation": {"reconciles_within_tolerance": True},
        },
        "therapeutic_group_analysis": {
            "largest_growth_contributors": [{"group": "A02B", "sales_change": 143.47}],
            "largest_declines": [{"group": "M05C", "sales_change": -5.27}],
        },
        "competitor_analysis": {},
    }
    result = coordinate_commercial_diagnosis(source)
    summary = result["coordinated_summary"]

    assert result["company"] == "ALKEM*"
    assert result["market_growth_decomposition"] == source["market_growth_decomposition"]
    assert summary["growth_gap_percentage_points"] == -1.09
    assert any("trailed the market" in fact for fact in summary["verified_facts"])
    assert summary["interpretations_and_hypotheses"]
    assert summary["priority_investigations"]
    assert any("does not establish causation" in item for item in summary["limitations"])


def test_coordinator_returns_errors_unchanged():
    source = {"status": "error", "message": "missing data"}
    assert coordinate_commercial_diagnosis(source) is source
