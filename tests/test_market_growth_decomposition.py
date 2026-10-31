from app.agents.market_growth_decomposition import build_market_growth_decomposition
from app.agents.commercial_diagnosis import build_commercial_diagnosis


def test_market_growth_decomposition_reconciles_and_quantifies_gap():
    result = build_market_growth_decomposition("ALKEM*")

    assert result["status"] == "success"
    assert result["reconciliation"]["reconciles_within_tolerance"] is True
    assert round(result["market"]["growth_percent"], 2) == 7.80
    assert round(result["company_performance"]["growth_percent"], 2) == 6.71
    assert round(result["decomposition"]["growth_gap_percentage_points"], 2) == -1.09
    assert round(result["decomposition"]["sales_gap_vs_market_growth"], 2) == 96.75


def test_commercial_diagnosis_includes_market_decomposition():
    result = build_commercial_diagnosis("ALKEM*", ["CIPLA", "SUN*"])

    assert result["status"] == "success"
    assert result["market_growth_decomposition"]["status"] == "success"
    signals = result["executive_diagnosis"]["observed_signals"]
    assert any(signal.get("signal") == "Company growth versus total-market growth" for signal in signals)
    assert any("below-market growth gap" in item.get("question", "") for item in result["investigation_priorities"])
