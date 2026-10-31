from app.agents.company_deep_dive import get_company_metrics


def test_alkem_company_metrics_are_available():
    result = get_company_metrics("ALKEM*")

    assert result["status"] == "success"

    metrics = result["metrics"]

    assert metrics["sales_2025"] is not None
    assert metrics["sales_2024"] is not None
    assert metrics["growth_percent"] is not None
    assert metrics["market_share_2025_percent"] is not None