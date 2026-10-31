from app.dashboard_data import available_companies, build_dashboard_payload


def test_available_companies_includes_alkem():
    assert "ALKEM*" in available_companies()


def test_dashboard_payload_contains_core_metrics_and_sources():
    result = build_dashboard_payload("ALKEM*", ["CIPLA", "SUN*"])

    assert result["status"] == "success"
    assert result["company"] == "ALKEM*"
    assert result["metrics"]["market_growth_percent"] > result["metrics"]["company_growth_percent"]
    assert result["metrics"]["reconciles"] is True
    assert len(result["groups"]) > 0
    assert {"CIPLA", "SUN*"}.issubset(set(result["competitors"]["company"]))
    assert "IMS_Group_Analysis.csv" in result["sources"]


def test_dashboard_group_benchmark_is_ranked_worst_first():
    result = build_dashboard_payload("ALKEM*", ["CIPLA", "SUN*"])
    values = result["groups"]["sales_vs_group_market_growth_benchmark"].dropna().tolist()

    assert values == sorted(values)
