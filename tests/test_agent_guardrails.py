"""Regression tests for high-impact agent calculation/output guardrails."""

from app.agents import agent


def test_validate_company_metrics_calculates_percent_growth_not_absolute_change():
    result = agent.validate_company_metrics({
        "sales_2024": 8899.2277,
        "sales_2025": 9496.2222,
        "market_share_2024_percent": 3.9518,
        "market_share_2025_percent": 3.9119,
    })
    assert round(result["sales_change"], 2) == 596.99
    assert round(result["growth_percent"], 2) == 6.71
    assert round(result["share_change_percentage_points"], 4) == -0.0399


def test_diagnostic_answer_uses_deterministic_growth_and_lists_multiple_declines(monkeypatch):
    # If the LLM is called for diagnosis, this test fails: diagnosis must be
    # rendered from verified Python values, not LLM-generated arithmetic.
    monkeypatch.setattr(
        agent,
        "generate_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not format diagnostic metrics")),
    )
    evidence = {
        "company": "ALKEM*",
        "data_period": "MAT Sep 2025 vs MAT Sep 2024",
        "data_limitations": ["Aggregate data do not prove causation."],
        "analyses": {
            "company_performance": {
                "status": "success",
                "result": {
                    "status": "success",
                    "company": "ALKEM*",
                    "sales_2024": 8899.2277,
                    "sales_2025": 9496.2222,
                    "market_share_2024_percent": 3.9518,
                    "market_share_2025_percent": 3.9119,
                },
            },
            "therapeutic_groups": {
                "status": "success",
                "result": {
                    "status": "success",
                    "company": "ALKEM*",
                    "total_groups": 10,
                    "company_net_sales_change": 596.9945,
                    "largest_growth_contributors": [{
                        "group": "A02B ANTIPEPTIC ULCERANTS",
                        "sales_2024": 1361.59,
                        "sales_2025": 1505.06,
                        "sales_change": 143.47,
                        "growth_percent": 10.54,
                        "contribution_to_company_net_sales_change_percent": 24.03,
                    }],
                    "declining_groups": [
                        {"group": "M05C ANTI-OSTEOPOROSIS PREP.", "sales_change": -5.27, "growth_percent": -2.04},
                        {"group": "A06A LAXATIVES", "sales_change": -5.08, "growth_percent": -11.80},
                        {"group": "L04B ANTI-TNF PRODUCTS", "sales_change": -5.03, "growth_percent": -63.90},
                    ],
                },
            },
            "value_vs_units": {"status": "unavailable", "message": "not supplied in fixture"},
        },
    }
    answer = agent._synthesize_diagnostic_answer(evidence)
    assert "6.71% growth" in answer
    assert "596.99% growth" not in answer
    assert "M05C ANTI-OSTEOPOROSIS PREP." in answer
    assert "A06A LAXATIVES" in answer
    assert "L04B ANTI-TNF PRODUCTS" in answer
    assert "does not prove" in answer.lower()
