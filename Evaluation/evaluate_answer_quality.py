"""Deterministic quality checks for the Pharma Intelligence commercial agent.

This evaluation checks deterministic agent behaviour and
basic numerical validation. It does not claim to validate LLM factual accuracy.

Run from the project root:
    python Evaluation/evaluate_answer_quality.py
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.agent import (  # noqa: E402
    ALLOWED_ACTIONS,
    extract_limit,
    extract_sort_by,
    json_safe,
    plan_action,
    safe_number,
    validate_company_metrics,
)


def _check_greeting_routes_to_general_answer() -> None:
    plan = plan_action("Hello")
    assert plan.get("action") == "general_answer", plan


def _check_diagnostic_routes_to_commercial_diagnosis() -> None:
    plan = plan_action("Why is ALKEM* losing market share?")
    assert plan.get("action") == "commercial_diagnosis", plan


def _check_share_mover_routes_correctly() -> None:
    plan = plan_action("Show the top market-share decliners")
    assert plan.get("action") == "market_share_movers", plan


def _check_only_supported_actions_are_registered() -> None:
    assert all(isinstance(action, str) and action for action in ALLOWED_ACTIONS)
    assert len(ALLOWED_ACTIONS) == len(set(ALLOWED_ACTIONS))


def _check_limit_extraction() -> None:
    assert extract_limit("Show top 7 companies") == 7
    assert extract_limit("Show companies") == 10


def _check_sort_extraction() -> None:
    assert extract_sort_by("Which companies are growing fastest?") == "growth"
    assert extract_sort_by("Show companies by sales") == "sales"


def _check_safe_number() -> None:
    assert safe_number("12.5") == 12.5
    assert safe_number("not-a-number") is None
    assert safe_number(float("nan")) is None
    assert safe_number(float("inf")) is None


def _check_company_metric_recalculation() -> None:
    source = {
        "sales_2024": 100.0,
        "sales_2025": 125.0,
        "market_share_2024_percent": 10.0,
        "market_share_2025_percent": 9.5,
    }
    result = validate_company_metrics(source)
    assert math.isclose(result["sales_change"], 25.0)
    assert math.isclose(result["growth_percent"], 25.0)
    assert math.isclose(result["share_change_percentage_points"], -0.5)


def _check_json_safe_handles_non_finite_values() -> None:
    result = json_safe({"valid": 5.0, "invalid": float("nan"), "items": (1, 2)})
    assert result == {"valid": 5.0, "invalid": None, "items": [1, 2]}, result


EVALUATION_CASES: list[tuple[str, Callable[[], None]]] = [
    ("Greeting intent routing", _check_greeting_routes_to_general_answer),
    ("Commercial diagnosis intent routing", _check_diagnostic_routes_to_commercial_diagnosis),
    ("Market-share mover intent routing", _check_share_mover_routes_correctly),
    ("Supported action registry", _check_only_supported_actions_are_registered),
    ("Top-N limit extraction", _check_limit_extraction),
    ("Company ranking sort extraction", _check_sort_extraction),
    ("Safe numeric conversion", _check_safe_number),
    ("Company metric recalculation", _check_company_metric_recalculation),
    ("JSON-safe output conversion", _check_json_safe_handles_non_finite_values),
]


def evaluate_case(name: str, check: Callable[[], None]) -> dict:
    try:
        check()
        return {"case": name, "passed": True, "error": None}
    except Exception as exc:  # Keep the suite running to report all failures.
        return {
            "case": name,
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    results = [evaluate_case(name, check) for name, check in EVALUATION_CASES]
    passed = sum(item["passed"] for item in results)
    failed = len(results) - passed

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Pharma Intelligence AI Platform",
        "evaluation_type": "Deterministic commercial-agent quality checks",
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
        "limitations": [
            "These checks validate deterministic routing, parameter extraction and metric calculations.",
            "They do not validate LLM factual accuracy, the quality of generated prose, or live dataset completeness.",
            "Full integration tests should be run separately against the project's IMS datasets and configured Ollama service.",
        ],
    }

    output_path = PROJECT_ROOT / "Evaluation" / "answer_quality_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=4, ensure_ascii=False), encoding="utf-8")

    print("=" * 68)
    print("PHARMA INTELLIGENCE AI — AGENT QUALITY EVALUATION")
    print("=" * 68)
    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"[{status}] {item['case']}")
        if item["error"]:
            print(f"       {item['error']}")
    print(f"\nPassed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print(f"Report: {output_path}")
    print("Note: passing these checks is not proof of end-to-end analytical accuracy.")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
