
import json
import re
from typing import Any

from app.llm.llm_client import generate_response
from app.agents.tools import calculate_sales_growth
from app.agents.market_data import get_brand_sales
from app.agents.company_analysis import (
    load_company_data,
    find_company,
    top_companies,
    company_group_analysis,
    company_value_unit_analysis,
)
from app.agents.market_share_analysis import (
    market_share_movers,
    company_share_rank,
)


ALLOWED_ACTIONS = {
    "general_answer",
    "sales_growth",
    "market_share",
    "competitor_comparison",
    "competitor_intelligence",
    "company_analysis",
    "top_companies",
    "company_group_analysis",
    "company_value_unit_analysis",
    "market_share_movers",
    "company_share_rank",
    "commercial_diagnosis",
    "clarify",
}


PLANNER_PROMPT = """
You are Pharma Commercial Intelligence AI, a pharmaceutical
commercial analytics assistant.

Choose one action:
- general_answer: greetings and conceptual questions
- sales_growth: brand sales growth
- market_share: general market-share questions
- competitor_comparison: compare companies
- competitor_intelligence: broad competitor benchmarking
- company_analysis: company performance
- top_companies: company ranking
- company_group_analysis: performance by therapeutic group
- company_value_unit_analysis: sales value versus units
- market_share_movers: market-share gainers or decliners
- company_share_rank: company share-change rank
- commercial_diagnosis: investigate a commercial trend using
  multiple sources of evidence
- clarify: genuinely ambiguous questions

For questions asking why a company is underperforming, growing slowly,
losing share, or experiencing an unexplained trend, select
commercial_diagnosis.

Return only a JSON object with action, reasoning and required_inputs.
Never invent figures or claim tools have run.
"""


# ---------------------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------------------

def extract_json(text: str) -> dict:
    """Parse a JSON object from the model response."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The model returned an empty response.")

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)

        if not match:
            raise ValueError("The model response did not contain JSON.")

        result = json.loads(match.group(0))

    if not isinstance(result, dict):
        raise ValueError("The model response must be a JSON object.")

    return result


def normalize_text(value: Any) -> str:
    """Normalize text for company-name matching."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def safe_number(value: Any):
    """Return a finite float or None."""
    try:
        number = float(value)

        if number != number or number in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return number

    except (TypeError, ValueError):
        return None


def format_number(value: Any, decimals: int = 2) -> str:
    """Format a number safely for a commercial report."""
    number = safe_number(value)

    if number is None:
        return "unavailable"

    return f"{number:,.{decimals}f}"


def json_safe(value: Any):
    """Convert common analytical values to JSON-safe values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (ValueError, TypeError):
            pass

    if isinstance(value, float):
        if value != value or value in (
            float("inf"),
            float("-inf"),
        ):
            return None

    return value


# ---------------------------------------------------------------------
# COMPANY AND QUESTION EXTRACTION
# ---------------------------------------------------------------------

def get_company_names() -> list[str]:
    """Load company names from the existing analysis dataset."""
    data = load_company_data()

    if data is None or data.empty or "COMPANY" not in data.columns:
        return []

    return sorted(
        data["COMPANY"].dropna().astype(str).unique().tolist(),
        key=len,
        reverse=True,
    )


def extract_companies(question: str) -> list[str]:
    """Find known company names mentioned in a question."""
    normalized_question = normalize_text(question)
    matches = []

    for company in get_company_names():
        normalized_company = normalize_text(company)

        if (
            normalized_company
            and normalized_company in normalized_question
            and company not in matches
        ):
            matches.append(company)

    return matches


def extract_company(question: str):
    """Return the first recognized company in the question."""
    companies = extract_companies(question)
    return companies[0] if companies else None


def extract_brand(question: str):
    """Extract a brand name from a question."""
    patterns = [
        r"\bfor\s+brand\s+([A-Za-z0-9][A-Za-z0-9._-]*)",
        r"\bbrand\s+([A-Za-z0-9][A-Za-z0-9._-]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)

        if match:
            return match.group(1).strip(".,?!")

    return None


def extract_limit(question: str, default: int = 10) -> int:
    """Extract a ranking limit such as 'top 5'."""
    match = re.search(
        r"\btop\s+(\d+)\b",
        question,
        flags=re.IGNORECASE,
    )

    if not match:
        return default

    return max(1, min(int(match.group(1)), 100))


def extract_sort_by(question: str) -> str:
    """Choose sales or growth for company rankings."""
    text = question.lower()

    growth_terms = (
        "growth",
        "growing fastest",
        "fastest growing",
        "growth rate",
    )

    if any(term in text for term in growth_terms):
        return "growth"

    return "sales"


# ---------------------------------------------------------------------
# INTENT DETECTION AND PLANNING
# ---------------------------------------------------------------------

def is_greeting(question: str) -> bool:
    """Recognize common greetings and conversational messages."""
    text = question.lower().strip(" !?.,")
    greetings = {
        "hi",
        "hello",
        "hey",
        "hi bro",
        "hello bro",
        "hey bro",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "thank you bro",
        "who are you",
        "what can you do",
        "help",
    }

    return text in greetings


def is_diagnostic_question(question: str) -> bool:
    """Identify questions requiring multi-source investigation."""
    text = question.lower()

    terms = (
        "why ",
        "why is",
        "why are",
        "what caused",
        "what could explain",
        "possible reasons",
        "root cause",
        "drivers of",
        "explain why",
        "what is driving",
        "what might be driving",
        "despite",
        "underperforming",
        "growing slower",
        "slower than the market",
        "what should we investigate",
        "what explains",
        "what should the commercial team investigate",
        "what is behind",
        "what are the drivers",
        "diagnose",
        "commercial diagnosis",
    )

    return any(term in text for term in terms)


def plan_action(question: str) -> dict:
    """Plan a request, using deterministic routing where appropriate."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    lower = question.lower()

    if is_greeting(question):
        return {
            "question": question,
            "action": "general_answer",
            "reasoning": "Greeting or conversational message.",
            "required_inputs": [],
        }

    if is_diagnostic_question(question):
        return {
            "question": question,
            "action": "commercial_diagnosis",
            "reasoning": (
                "Investigate the commercial trend using multiple "
                "analytical sources."
            ),
            "required_inputs": ["company"],
        }

    rank_terms = ("rank", "ranking", "position among", "ranked")
    share_terms = ("share", "alkem", "cipla", "sun pharma", "company")

    if any(term in lower for term in rank_terms) and any(
        term in lower for term in share_terms
    ):
        return {
            "question": question,
            "action": "company_share_rank",
            "reasoning": "The user asks for a company's share-change rank.",
            "required_inputs": ["company"],
        }

    mover_terms = (
        "gainer",
        "gainers",
        "decliner",
        "decliners",
        "loser",
        "losers",
        "share gain",
        "share loss",
        "share decline",
        "market share movers",
        "market-share movers",
    )

    if any(term in lower for term in mover_terms):
        return {
            "question": question,
            "action": "market_share_movers",
            "reasoning": "The user asks about market-share movers.",
            "required_inputs": ["direction", "limit"],
        }

    prompt = (
        f"{PLANNER_PROMPT}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        "Return the JSON object now."
    )

    model_plan = extract_json(generate_response(prompt))
    action = model_plan.get("action")

    if action not in ALLOWED_ACTIONS:
        action = (
            "company_analysis"
            if extract_company(question)
            else "general_answer"
        )

    return {
        "question": question,
        "action": action,
        "reasoning": str(model_plan.get("reasoning", "")),
        "required_inputs": model_plan.get("required_inputs", []),
    }


def extract_parameters(question: str, action: str) -> dict:
    """Extract parameters required by analytical tools."""
    parameters = {}
    companies = extract_companies(question)

    if action in {
        "competitor_comparison",
        "competitor_intelligence",
    } and len(companies) >= 2:
        parameters["companies"] = companies

    if action in {
        "company_analysis",
        "company_group_analysis",
        "company_value_unit_analysis",
        "company_share_rank",
        "commercial_diagnosis",
    }:
        company = extract_company(question)

        if company:
            parameters["company"] = company

    if action == "sales_growth":
        brand = extract_brand(question)

        if brand:
            parameters["brand"] = brand

    if action == "top_companies":
        parameters["limit"] = extract_limit(question)
        parameters["sort_by"] = extract_sort_by(question)

    if action == "company_group_analysis":
        parameters["limit"] = extract_limit(question, default=20)

    if action == "market_share_movers":
        parameters["limit"] = extract_limit(question)

        loser_terms = (
            "decliner",
            "decliners",
            "loser",
            "losers",
            "losing",
            "lost share",
            "share loss",
            "share decline",
        )

        parameters["direction"] = (
            "losers"
            if any(term in question.lower() for term in loser_terms)
            else "gainers"
        )

    return parameters


# ---------------------------------------------------------------------
# COMPANY COMPARISON
# ---------------------------------------------------------------------

def validate_company_metrics(result: dict) -> dict:
    """
    Recalculate company sales growth and share movement.

    The raw tool results remain available, but derived metrics use the
    underlying period values when those values are available.
    """
    validated = dict(result)

    sales_2025 = safe_number(result.get("sales_2025"))
    sales_2024 = safe_number(result.get("sales_2024"))

    if sales_2025 is not None and sales_2024 is not None:
        sales_change = sales_2025 - sales_2024
        validated["sales_change"] = sales_change

        if sales_2024 != 0:
            validated["growth_percent"] = (
                sales_change / abs(sales_2024)
            ) * 100
        else:
            validated["growth_percent"] = None

    share_2025 = safe_number(
        result.get("market_share_2025_percent")
    )
    share_2024 = safe_number(
        result.get("market_share_2024_percent")
    )

    if share_2025 is not None and share_2024 is not None:
        validated["share_change_percentage_points"] = (
            share_2025 - share_2024
        )

    return validated


def compare_companies(companies: list) -> dict:
    """Compare companies using validated sales and share metrics."""
    if not isinstance(companies, list) or len(companies) < 2:
        return {
            "status": "needs_input",
            "message": "Please specify at least two companies to compare.",
        }

    companies = list(dict.fromkeys(companies))[:5]

    if len(companies) < 2:
        return {
            "status": "needs_input",
            "message": "Please specify two different companies.",
        }

    rows = []

    for company in companies:
        result = find_company(company)

        if (
            not isinstance(result, dict)
            or result.get("status") != "success"
        ):
            return {
                "status": "error",
                "message": (
                    f"Could not retrieve company data for {company}."
                ),
                "company_result": result,
            }

        result = validate_company_metrics(result)

        rows.append({
            "company": result.get("company", company),
            "sales_2025": result.get("sales_2025"),
            "sales_2024": result.get("sales_2024"),
            "sales_change": result.get("sales_change"),
            "growth_percent": result.get("growth_percent"),
            "market_share_2025_percent": result.get(
                "market_share_2025_percent"
            ),
            "market_share_2024_percent": result.get(
                "market_share_2024_percent"
            ),
            "share_change_percentage_points": result.get(
                "share_change_percentage_points"
            ),
            "competitive_category": result.get("competitive_category"),
        })

    ranked = sorted(
        rows,
        key=lambda row: (
            row["growth_percent"] is not None,
            row["growth_percent"]
            if row["growth_percent"] is not None
            else float("-inf"),
        ),
        reverse=True,
    )

    return {
        "status": "success",
        "comparison": "MAT Sep 2025 vs MAT Sep 2024",
        "companies": rows,
        "ranked_by_growth": [row["company"] for row in ranked],
        "data_source": "IMS_Company_Analysis.csv",
    }


# ---------------------------------------------------------------------
# TOOL EXECUTION
# ---------------------------------------------------------------------

def execute_plan(plan: dict, tool_inputs: dict | None = None) -> dict:
    """Execute a supported analytical action."""
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a dictionary.")

    action = plan.get("action")
    inputs = tool_inputs or {}

    if not isinstance(inputs, dict):
        raise ValueError("Tool inputs must be a dictionary.")

    if action in {"competitor_comparison", "competitor_intelligence"}:
        result = compare_companies(inputs.get("companies", []))

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "general_answer":
        answer = generate_response(
            "You are Pharma Commercial Intelligence AI, a friendly "
            "pharmaceutical commercial analytics chatbot. Respond "
            "naturally to greetings and conversational messages. When "
            "asked what you can do, explain that you can analyse company "
            "performance, market share, therapeutic groups, sales growth "
            "and competitors using available data. Never invent company "
            "figures. Keep simple greetings brief.\n\n"
            f"User message: {plan.get('question', '')}"
        )

        return {
            "action": action,
            "status": "success",
            "answer": answer,
        }

    if action == "company_analysis":
        company = inputs.get("company")

        if not company:
            return {
                "action": action,
                "status": "needs_input",
                "missing_inputs": ["company"],
                "message": "Which company should I analyse?",
            }

        result = find_company(company)

        if isinstance(result, dict) and result.get("status") == "success":
            result = validate_company_metrics(result)

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "company_group_analysis":
        company = inputs.get("company")

        if not company:
            return {
                "action": action,
                "status": "needs_input",
                "missing_inputs": ["company"],
                "message": "Which company should I analyse?",
            }

        result = company_group_analysis(
            company,
            limit=inputs.get("limit", 20),
        )

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "company_value_unit_analysis":
        company = inputs.get("company")

        if not company:
            return {
                "action": action,
                "status": "needs_input",
                "missing_inputs": ["company"],
                "message": "Which company should I analyse?",
            }

        result = company_value_unit_analysis(company)

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "top_companies":
        result = top_companies(
            limit=inputs.get("limit", 10),
            sort_by=inputs.get("sort_by", "sales"),
        )

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "market_share_movers":
        direction = inputs.get("direction", "gainers")

        if direction not in {"gainers", "losers"}:
            direction = "gainers"

        result = market_share_movers(
            direction=direction,
            limit=inputs.get("limit", 10),
        )

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "company_share_rank":
        company = inputs.get("company")

        if not company:
            return {
                "action": action,
                "status": "needs_input",
                "missing_inputs": ["company"],
                "message": "Which company should I rank?",
            }

        result = company_share_rank(company)

        return {
            "action": action,
            "status": result.get("status", "unknown"),
            "result": result,
        }

    if action == "sales_growth":
        brand = inputs.get("brand")

        if brand:
            result = get_brand_sales(
                brand_name=brand,
                company=inputs.get("company"),
            )

            return {
                "action": action,
                "status": result.get("status", "unknown"),
                "result": result,
            }

        if "previous_sales" not in inputs or "current_sales" not in inputs:
            return {
                "action": action,
                "status": "needs_input",
                "missing_inputs": ["previous_sales", "current_sales"],
                "message": (
                    "Provide a brand name or both previous_sales "
                    "and current_sales."
                ),
            }

        result = calculate_sales_growth(
            previous_sales=inputs["previous_sales"],
            current_sales=inputs["current_sales"],
        )

        return {
            "action": action,
            "status": "success",
            "result": result,
            "data_source": "user_supplied_values",
        }

    if action == "clarify":
        return {
            "action": action,
            "status": "needs_input",
            "message": "Could you clarify what you want to investigate?",
        }

    return {
        "action": action,
        "status": "not_implemented",
        "message": f"The action '{action}' is not implemented.",
    }


def _safe_execute(action: str, inputs: dict) -> dict:
    """Run one tool and capture its errors without losing other results."""
    try:
        return execute_plan(
            {
                "action": action,
                "question": f"Investigation tool: {action}",
            },
            inputs,
        )

    except Exception as exc:
        return {
            "action": action,
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }


# ---------------------------------------------------------------------
# COMMERCIAL DIAGNOSIS: EVIDENCE COLLECTION
# ---------------------------------------------------------------------

def _build_diagnostic_evidence(
    question: str,
    company: str,
    competitors: list[str],
) -> dict:
    """Gather company, therapeutic-group, value/unit and competitor data."""
    analyses = {
        "company_performance": _safe_execute(
            "company_analysis",
            {"company": company},
        ),
        "therapeutic_groups": _safe_execute(
            "company_group_analysis",
            {"company": company, "limit": 20},
        ),
        "value_vs_units": _safe_execute(
            "company_value_unit_analysis",
            {"company": company},
        ),
    }

    comparison_companies = list(
        dict.fromkeys([company, *competitors])
    )[:5]

    if len(comparison_companies) >= 2:
        analyses["competitor_comparison"] = _safe_execute(
            "competitor_intelligence",
            {"companies": comparison_companies},
        )

    return {
        "question": question,
        "company": company,
        "competitors": competitors,
        "data_period": "MAT Sep 2025 vs MAT Sep 2024",
        "analyses": analyses,
        "data_limitations": [
            (
                "Aggregate sales and market-share data show patterns "
                "but do not prove causation."
            ),
            (
                "Brand, prescription, pricing, promotion, distribution "
                "and stock availability causes must not be asserted "
                "without corresponding evidence."
            ),
            (
                "Failed tools indicate missing evidence, not proof "
                "that a factor had no effect."
            ),
        ],
    }


def _unwrap_result(tool_output: Any) -> dict:
    """Return the underlying result from an execute_plan response."""
    if not isinstance(tool_output, dict):
        return {}

    result = tool_output.get("result")

    if isinstance(result, dict):
        return result

    return tool_output


def _extract_group_records(
    group_result: dict,
    preferred_keys: list[str],
) -> list[dict]:
    """
    Extract records from the actual group-analysis schema.

    The existing company analysis module uses 'declining_groups'
    for negative contributors. Several fallback names are supported
    for compatibility with alternative output schemas.
    """
    if not isinstance(group_result, dict):
        return []

    for key in preferred_keys:
        value = group_result.get(key)

        if isinstance(value, list):
            return [
                item for item in value
                if isinstance(item, dict)
            ]

    return []


def _build_group_driver_analysis(group_output: dict) -> dict:
    """
    Summarize the biggest positive and negative group-level changes.

    Group records and their sales changes come from the existing
    company_group_analysis tool. Ranking and summaries are calculated
    in Python, not generated by the LLM.
    """
    groups = _unwrap_result(group_output)

    if groups.get("status") != "success":
        return {
            "status": "unavailable",
            "message": groups.get(
                "message",
                "Therapeutic-group analysis did not return success.",
            ),
            "largest_growth_contributors": [],
            "largest_decliners": [],
            "fastest_growing_groups": [],
            "notes": [],
        }

    growth_records = _extract_group_records(
        groups,
        [
            "largest_growth_contributors",
            "growth_contributors",
            "largest_contributors",
        ],
    )

    decline_records = _extract_group_records(
        groups,
        [
            "declining_groups",
            "largest_decliners",
            "decliners",
            "declining",
            "largest_declining_groups",
        ],
    )

    fastest_records = _extract_group_records(
        groups,
        [
            "fastest_growing_material_groups",
            "fastest_growing_groups",
            "fastest_growing",
        ],
    )

    # If the tool returned a ranking but no dedicated contributor list,
    # calculate rankings from the returned group records.
    all_records = _extract_group_records(
        groups,
        [
            "ranking_by_sales",
            "groups",
            "evidence",
        ],
    )

    if not all_records:
        all_records = growth_records + decline_records + fastest_records

    deduplicated = {}

    for item in all_records + growth_records + decline_records:
        group_name = str(item.get("group", "")).strip()

        if group_name:
            deduplicated[group_name.casefold()] = item

    all_records = list(deduplicated.values())

    if not growth_records:
        growth_records = [
            item for item in all_records
            if (safe_number(item.get("sales_change")) or 0) > 0
        ]

    if not decline_records:
        decline_records = [
            item for item in all_records
            if (safe_number(item.get("sales_change")) or 0) < 0
        ]

    growth_records = sorted(
        growth_records,
        key=lambda item: safe_number(item.get("sales_change"))
        if safe_number(item.get("sales_change")) is not None
        else float("-inf"),
        reverse=True,
    )

    decline_records = sorted(
        decline_records,
        key=lambda item: safe_number(item.get("sales_change"))
        if safe_number(item.get("sales_change")) is not None
        else float("inf"),
    )

    fastest_records = sorted(
        fastest_records,
        key=lambda item: safe_number(item.get("growth_percent"))
        if safe_number(item.get("growth_percent")) is not None
        else float("-inf"),
        reverse=True,
    )

    def compact(records: list[dict]) -> list[dict]:
        output = []

        for item in records[:5]:
            output.append({
                "group": item.get("group"),
                "sales_2024": safe_number(item.get("sales_2024")),
                "sales_2025": safe_number(item.get("sales_2025")),
                "sales_change": safe_number(item.get("sales_change")),
                "growth_percent": safe_number(item.get("growth_percent")),
                "contribution_to_company_net_sales_change_percent":
                    safe_number(
                        item.get(
                            "contribution_to_company_net_sales_change_percent"
                        )
                    ),
            })

        return output

    notes = []

    if not growth_records:
        notes.append(
            "No positive therapeutic-group changes were available "
            "in the returned records."
        )

    if not decline_records:
        notes.append(
            "No negative therapeutic-group changes were available "
            "in the returned records."
        )

    return {
        "status": "success",
        "company": groups.get("company"),
        "total_groups": groups.get("total_groups"),
        "company_net_sales_change": safe_number(
            groups.get("company_net_sales_change")
        ),
        "largest_growth_contributors": compact(growth_records),
        "largest_decliners": compact(decline_records),
        "fastest_growing_groups": compact(fastest_records),
        "notes": notes,
        "source_ranking_notes": groups.get("ranking_notes", {}),
    }


# ---------------------------------------------------------------------
# PYTHON-VERIFIED FACTS AND COMMERCIAL DRIVER CALCULATIONS
# ---------------------------------------------------------------------

def _build_verified_facts(
    company_output: dict,
    group_analysis: dict,
) -> list[dict]:
    """Build factual statements from calculated metrics and tool data."""
    company_result = _unwrap_result(company_output)
    company_result = validate_company_metrics(company_result)

    facts = []

    sales_2024 = safe_number(company_result.get("sales_2024"))
    sales_2025 = safe_number(company_result.get("sales_2025"))
    sales_change = safe_number(company_result.get("sales_change"))
    growth = safe_number(company_result.get("growth_percent"))

    share_2024 = safe_number(
        company_result.get("market_share_2024_percent")
    )
    share_2025 = safe_number(
        company_result.get("market_share_2025_percent")
    )
    share_change = safe_number(
        company_result.get("share_change_percentage_points")
    )

    company_name = company_result.get("company", "Selected company")

    if sales_2024 is not None and sales_2025 is not None:
        facts.append({
            "type": "company_sales",
            "company": company_name,
            "sales_2024": sales_2024,
            "sales_2025": sales_2025,
            "sales_change": sales_change,
            "growth_percent": growth,
            "statement": (
                f"{company_name} sales changed from "
                f"{format_number(sales_2024)} to "
                f"{format_number(sales_2025)}, a change of "
                f"{format_number(sales_change)} "
                f"({format_number(growth)}%)."
            ),
        })

    if share_2024 is not None and share_2025 is not None:
        facts.append({
            "type": "market_share",
            "share_2024_percent": share_2024,
            "share_2025_percent": share_2025,
            "change_percentage_points": share_change,
            "statement": (
                f"Market share changed from "
                f"{format_number(share_2024, 4)}% to "
                f"{format_number(share_2025, 4)}%, a movement of "
                f"{format_number(share_change, 4)} percentage points."
            ),
        })

    if growth is not None and share_change is not None:
        if growth > 0 and share_change < 0:
            facts.append({
                "type": "performance_pattern",
                "statement": (
                    "Sales value increased while market share declined. "
                    "This establishes a divergence between absolute "
                    "sales growth and relative share performance; it "
                    "does not establish the cause."
                ),
            })

        elif growth < 0 and share_change < 0:
            facts.append({
                "type": "performance_pattern",
                "statement": (
                    "Sales value and market share both declined."
                ),
            })

        elif growth > 0 and share_change > 0:
            facts.append({
                "type": "performance_pattern",
                "statement": (
                    "Sales value increased and market share also rose."
                ),
            })

    if group_analysis.get("status") == "success":
        for driver in group_analysis.get(
            "largest_growth_contributors", []
        )[:3]:
            if driver.get("group") is None:
                continue

            facts.append({
                "type": "therapeutic_group_growth",
                **driver,
                "statement": (
                    f"{driver['group']} recorded a sales change of "
                    f"{format_number(driver.get('sales_change'))} "
                    f"and growth of "
                    f"{format_number(driver.get('growth_percent'))}%."
                ),
            })

        for driver in group_analysis.get("largest_decliners", [])[:3]:
            if driver.get("group") is None:
                continue

            facts.append({
                "type": "therapeutic_group_decline",
                **driver,
                "statement": (
                    f"{driver['group']} recorded a sales change of "
                    f"{format_number(driver.get('sales_change'))} "
                    f"and growth of "
                    f"{format_number(driver.get('growth_percent'))}%."
                ),
            })

    return facts


def _build_driver_summary(
    company_output: dict,
    group_analysis: dict,
) -> dict:
    """
    Calculate the observed commercial growth pattern.

    Positive and negative group contributions are kept separate.
    Contribution percentages use the company's net sales change as
    the denominator and can exceed 100% when declines offset growth.
    """
    company_result = validate_company_metrics(
        _unwrap_result(company_output)
    )

    company_change = safe_number(company_result.get("sales_change"))
    company_growth = safe_number(company_result.get("growth_percent"))
    share_change = safe_number(
        company_result.get("share_change_percentage_points")
    )

    positive_groups = group_analysis.get(
        "largest_growth_contributors", []
    )
    negative_groups = group_analysis.get("largest_decliners", [])

    positive_sum = sum(
        safe_number(item.get("sales_change")) or 0
        for item in positive_groups
    )

    negative_sum = sum(
        safe_number(item.get("sales_change")) or 0
        for item in negative_groups
    )

    # These are sums of the returned ranked groups, not necessarily
    # totals across every therapeutic group in the dataset.
    ranked_group_net_change = positive_sum + negative_sum

    positive_share = None
    negative_share = None

    if company_change not in (None, 0):
        positive_share = positive_sum / company_change * 100
        negative_share = negative_sum / company_change * 100

    pattern = "insufficient_data"

    if company_growth is not None and share_change is not None:
        if company_growth > 0 and share_change < 0:
            pattern = "sales_growth_with_share_decline"
        elif company_growth > 0 and share_change > 0:
            pattern = "sales_growth_with_share_gain"
        elif company_growth < 0 and share_change < 0:
            pattern = "sales_decline_with_share_decline"
        elif company_growth < 0 and share_change > 0:
            pattern = "sales_decline_with_share_gain"
        else:
            pattern = "mixed_or_flat"

    return {
        "company_sales_change": company_change,
        "company_growth_percent": company_growth,
        "market_share_change_percentage_points": share_change,
        "performance_pattern": pattern,
        "largest_positive_groups": positive_groups[:5],
        "largest_negative_groups": negative_groups[:5],
        "sum_of_returned_positive_group_changes": positive_sum,
        "sum_of_returned_negative_group_changes": negative_sum,
        "net_change_across_returned_ranked_groups": ranked_group_net_change,
        "positive_group_change_as_percent_of_company_net_change":
            positive_share,
        "negative_group_change_as_percent_of_company_net_change":
            negative_share,
        "interpretation_caveat": (
            "The positive and negative sums reflect the group records "
            "returned by the analysis tool. They are not necessarily "
            "full-company totals if the tool returned only a limited "
            "ranking. Contribution percentages may exceed 100% or be "
            "negative because group declines offset growth."
        ),
    }


def _build_hypotheses(
    company_output: dict,
    group_analysis: dict,
    value_unit_output: dict,
) -> list[dict]:
    """Create evidence-linked hypotheses without claiming causation."""
    company_result = validate_company_metrics(
        _unwrap_result(company_output)
    )
    value_unit = _unwrap_result(value_unit_output)

    growth = safe_number(company_result.get("growth_percent"))
    share_change = safe_number(
        company_result.get("share_change_percentage_points")
    )

    hypotheses = []

    if growth is not None and share_change is not None:
        if growth > 0 and share_change < 0:
            hypotheses.append({
                "hypothesis": (
                    "The company may be growing more slowly than the "
                    "relevant market."
                ),
                "evidence": (
                    "Sales value increased while market share declined."
                ),
                "confidence": "plausible, not proven",
                "next_test": (
                    "Calculate total-market growth for the same period "
                    "and compare it with company growth."
                ),
            })

            if group_analysis.get("status") == "success":
                hypotheses.append({
                    "hypothesis": (
                        "Growth may be concentrated in some therapeutic "
                        "groups while other groups offset the gains."
                    ),
                    "evidence": (
                        "The group analysis provides ranked positive "
                        "and negative sales changes."
                    ),
                    "confidence": "testable with available group data",
                    "next_test": (
                        "Compare the largest growth contributors and "
                        "decliners, then examine group-level market share."
                    ),
                })

        elif growth < 0 and share_change < 0:
            hypotheses.append({
                "hypothesis": (
                    "The company may be losing ground in the market "
                    "as its absolute sales decline."
                ),
                "evidence": (
                    "Company sales growth and share movement are both "
                    "negative."
                ),
                "confidence": "observed pattern; cause unknown",
                "next_test": (
                    "Compare group-level performance and competitor "
                    "growth over the same period."
                ),
            })

    value_growth = safe_number(
        value_unit.get("calculated_value_growth_percent")
    )
    unit_growth = safe_number(
        value_unit.get("calculated_unit_growth_percent")
    )

    if value_growth is not None and unit_growth is not None:
        if value_growth > unit_growth:
            hypotheses.append({
                "hypothesis": (
                    "Sales value may be increasing faster than volume."
                ),
                "evidence": (
                    f"Calculated value growth is {value_growth:.2f}% "
                    f"and calculated unit growth is {unit_growth:.2f}%."
                ),
                "confidence": "directional indicator",
                "next_test": (
                    "Check product mix, price and unit definitions. "
                    "Aggregate value-per-unit movement alone does not "
                    "prove a price increase."
                ),
            })

        elif unit_growth > value_growth:
            hypotheses.append({
                "hypothesis": (
                    "Unit growth may be outpacing sales value growth."
                ),
                "evidence": (
                    f"Calculated unit growth is {unit_growth:.2f}% "
                    f"and calculated value growth is {value_growth:.2f}%."
                ),
                "confidence": "directional indicator",
                "next_test": (
                    "Investigate product mix and value per unit; "
                    "do not assume discounting without price evidence."
                ),
            })

    return hypotheses


def _build_priority_investigations(
    group_analysis: dict,
    analyses: dict,
    company_output: dict,
) -> list[dict]:
    """Prioritize follow-up analyses based on available evidence."""
    company_result = validate_company_metrics(
        _unwrap_result(company_output)
    )

    growth = safe_number(company_result.get("growth_percent"))
    share_change = safe_number(
        company_result.get("share_change_percentage_points")
    )

    priorities = []

    if growth is not None and share_change is not None:
        if growth > 0 and share_change < 0:
            priorities.append({
                "priority": 1,
                "investigation": "Benchmark company growth against market growth",
                "reason": (
                    "Sales increased but market share declined. "
                    "The relevant market's growth rate is needed to "
                    "test whether it grew faster."
                ),
                "data_needed": [
                    "Total market sales for both periods",
                    "Company sales for the same periods",
                ],
            })

    if group_analysis.get("status") == "success":
        priorities.append({
            "priority": len(priorities) + 1,
            "investigation": "Quantify therapeutic-group growth drivers",
            "reason": (
                "Rank positive and negative group sales changes "
                "to identify where the net movement originates."
            ),
            "data_needed": [
                "Complete group-level sales for both periods",
                "Group-level market share, if available",
            ],
        })

    if analyses.get("competitor_comparison"):
        competitor_result = analyses["competitor_comparison"]

        if competitor_result.get("status") == "success":
            priorities.append({
                "priority": len(priorities) + 1,
                "investigation": "Compare competitors on a like-for-like basis",
                "reason": (
                    "Competitor context can help test whether the "
                    "company is lagging peers, but does not prove cause."
                ),
                "data_needed": [
                    "Comparable company growth",
                    "Comparable market-share changes",
                    "Same period and market definition",
                ],
            })

    if analyses.get("value_vs_units", {}).get("status") == "success":
        priorities.append({
            "priority": len(priorities) + 1,
            "investigation": "Separate value growth from unit growth",
            "reason": (
                "This helps identify whether value and volume are "
                "moving at different rates."
            ),
            "data_needed": [
                "Value and unit sales by period",
                "Consistent unit definitions",
                "Product mix and price data for causal analysis",
            ],
        })

    priorities.append({
        "priority": len(priorities) + 1,
        "investigation": "Investigate operational and brand-level causes",
        "reason": (
            "Aggregate company and group data do not establish "
            "the cause of a performance change."
        ),
        "data_needed": [
            "Brand-level sales and market share",
            "Distribution and availability",
            "Prescription or demand indicators where relevant",
            "Pricing and promotion data",
        ],
    })

    return priorities


# ---------------------------------------------------------------------
# LLM SYNTHESIS
# ---------------------------------------------------------------------

def _fallback_diagnostic_answer(
    company_output: dict,
    group_analysis: dict,
    driver_summary: dict,
    hypotheses: list[dict],
    priorities: list[dict],
) -> str:
    """Produce a useful deterministic answer if the LLM fails."""
    company_result = validate_company_metrics(
        _unwrap_result(company_output)
    )

    company = company_result.get("company", "The selected company")
    growth = safe_number(company_result.get("growth_percent"))
    share_change = safe_number(
        company_result.get("share_change_percentage_points")
    )

    lines = [
        f"### Short answer\n{company}'s observed commercial pattern "
        "is summarized below using the available dataset."
    ]

    lines.append("\n### What the data shows")

    if growth is not None:
        lines.append(f"- Sales growth: {growth:+.2f}%.")

    if share_change is not None:
        lines.append(
            f"- Market-share movement: {share_change:+.4f} percentage "
            "points."
        )

    positive = driver_summary.get("largest_positive_groups", [])
    negative = driver_summary.get("largest_negative_groups", [])

    if positive:
        lines.append("\n### Largest positive group changes")
        for item in positive[:3]:
            lines.append(
                f"- {item.get('group')}: sales change "
                f"{format_number(item.get('sales_change'))}; growth "
                f"{format_number(item.get('growth_percent'))}%."
            )

    if negative:
        lines.append("\n### Largest negative group changes")
        for item in negative[:3]:
            lines.append(
                f"- {item.get('group')}: sales change "
                f"{format_number(item.get('sales_change'))}; growth "
                f"{format_number(item.get('growth_percent'))}%."
            )

    if not positive and not negative:
        lines.append(
            "- Therapeutic-group driver records were not available."
        )

    lines.append("\n### Possible explanations to test")

    if hypotheses:
        for item in hypotheses:
            lines.append(
                f"- {item['hypothesis']} "
                f"Evidence: {item['evidence']} "
                f"Next test: {item['next_test']}"
            )
    else:
        lines.append(
            "- The available metrics do not support a specific "
            "commercial hypothesis yet."
        )

    lines.append("\n### Recommended next steps")

    for item in priorities[:5]:
        lines.append(
            f"{item['priority']}. {item['investigation']} — "
            f"{item['reason']}"
        )

    lines.append(
        "\nThese are descriptive findings and hypotheses to test. "
        "The aggregate data does not prove pricing, promotion, "
        "distribution, availability or competitor actions caused "
        "the observed performance."
    )

    return "\n".join(lines)


def _synthesize_diagnostic_answer(evidence: dict) -> str:
    """Write a grounded commercial explanation using verified evidence only."""

    analyses = evidence.get("analyses", {})

    company_output = analyses.get("company_performance", {})
    group_output = analyses.get("therapeutic_groups", {})
    value_unit_output = analyses.get("value_vs_units", {})

    group_analysis = _build_group_driver_analysis(group_output)

    driver_summary = _build_driver_summary(
        company_output,
        group_analysis,
    )

    verified_facts = _build_verified_facts(
        company_output,
        group_analysis,
    )

    hypotheses = _build_hypotheses(
        company_output,
        group_analysis,
        value_unit_output,
    )

    priorities = _build_priority_investigations(
        group_analysis,
        analyses,
        company_output,
    )

    evidence["group_driver_analysis"] = group_analysis
    evidence["driver_summary"] = driver_summary
    evidence["verified_facts"] = verified_facts
    evidence["hypotheses"] = hypotheses
    evidence["priority_investigations"] = priorities

    answer = _fallback_diagnostic_answer(
        company_output=company_output,
        group_analysis=group_analysis,
        driver_summary=driver_summary,
        hypotheses=hypotheses,
        priorities=priorities,
    )

    # Ensure the diagnostic uses clear, deterministic growth wording.
    company_result = company_output.get("result", company_output)

    sales_2024 = safe_number(company_result.get("sales_2024"))
    sales_2025 = safe_number(company_result.get("sales_2025"))

    if sales_2024 is not None and sales_2024 != 0 and sales_2025 is not None:
        growth_percent = ((sales_2025 - sales_2024) / sales_2024) * 100

        old_growth_line = f"Sales growth: {growth_percent:+.2f}%."
        new_growth_line = f"Sales growth: {growth_percent:.2f}% growth."

        answer = answer.replace(old_growth_line, new_growth_line)

    return answer
# ---------------------------------------------------------------------
# MAIN AGENT ENTRY POINT
# ---------------------------------------------------------------------

def run_agent(
    question: str,
    tool_inputs: dict | None = None,
    conversation_history: list | None = None,
) -> dict:
    """
    Main agent entry point.

    Preserves the dashboard's coordinated_summary structure.
    This agent handles commercial analytics and diagnosis only.
    """
    if not isinstance(question, str) or not question.strip():
        return {
            "plan": {"action": "clarify", "question": ""},
            "inputs": {},
            "execution": {
                "action": "clarify",
                "status": "needs_input",
                "message": "Ask me a commercial intelligence question.",
                "missing_inputs": ["question"],
            },
        }

    question = question.strip()
    supplied_inputs = dict(tool_inputs or {})

    try:
        plan = plan_action(question)

        extracted_inputs = extract_parameters(
            question,
            plan["action"],
        )
        extracted_inputs.update(supplied_inputs)

        # Support the dashboard's existing competitor field.
        if (
            "companies" not in extracted_inputs
            and extracted_inputs.get("competitors")
        ):
            extracted_inputs["companies"] = (
                extracted_inputs["competitors"]
            )

        if plan["action"] == "general_answer":
            execution = execute_plan(plan, extracted_inputs)
            answer = execution.get(
                "answer",
                execution.get("message", ""),
            )

            return {
                "plan": plan,
                "inputs": extracted_inputs,
                "execution": execution,
                "answer": answer,
            }

        company = (
            extracted_inputs.get("company")
            or extract_company(question)
        )

        competitors = (
            extracted_inputs.get("competitors")
            or extracted_inputs.get("companies")
            or []
        )

        if isinstance(competitors, str):
            competitors = [competitors]

        if not isinstance(competitors, list):
            competitors = []

        if plan["action"] == "commercial_diagnosis":
            if not company:
                return {
                    "plan": plan,
                    "inputs": extracted_inputs,
                    "execution": {
                        "action": "commercial_diagnosis",
                        "status": "needs_input",
                        "message": (
                            "Which company should I investigate? "
                            "You can choose one in the sidebar."
                        ),
                        "missing_inputs": ["company"],
                    },
                }

            competitors = [
                item for item in competitors
                if item
                and normalize_text(item) != normalize_text(company)
            ]

            evidence = _build_diagnostic_evidence(
                question=question,
                company=company,
                competitors=competitors,
            )

            if conversation_history:
                evidence["conversation_context"] = (
                    conversation_history[-8:]
                )

            answer = _synthesize_diagnostic_answer(evidence)

            analyses = evidence.get("analyses", {})
            company_output = analyses.get("company_performance", {})
            group_output = analyses.get("therapeutic_groups", {})

            group_analysis = _build_group_driver_analysis(group_output)

            verified_facts = _build_verified_facts(
                company_output,
                group_analysis,
            )

            hypotheses = _build_hypotheses(
                company_output,
                group_analysis,
                analyses.get("value_vs_units", {}),
            )

            priorities = _build_priority_investigations(
                group_analysis,
                analyses,
                company_output,
            )

            summary = {
                "company": company,
                "data_period": evidence["data_period"],
                "answer": answer,
                "verified_facts": verified_facts,
                "interpretations_and_hypotheses": hypotheses,
                "priority_investigations": priorities,
                "limitations": evidence["data_limitations"],
            }

            result = {
                "company": company,
                "data_period": evidence["data_period"],
                "coordinated_summary": summary,
                "investigation_evidence": evidence,
            }

            execution = {
                "action": "commercial_diagnosis",
                "status": "success",
                "answer": answer,
                "result": result,
            }

            return {
                "plan": {
                    **plan,
                    "action": "commercial_diagnosis",
                },
                "inputs": extracted_inputs,
                "execution": execution,
                "answer": answer,
                "coordinated_summary": summary,
            }

        execution = execute_plan(plan, extracted_inputs)
        answer = execution.get("answer")

        return {
            "plan": plan,
            "inputs": extracted_inputs,
            "execution": execution,
            "answer": answer,
        }

    except Exception as exc:
        message = (
            f"The agent encountered an error: {type(exc).__name__}: {exc}"
        )

        return {
            "plan": {
                "action": "error",
                "question": question,
            },
            "inputs": supplied_inputs,
            "execution": {
                "action": "error",
                "status": "error",
                "message": message,
            },
            "answer": message,
        }


# ---------------------------------------------------------------------
# RESPONSE FORMATTING AND TERMINAL CHAT
# ---------------------------------------------------------------------

def format_result(response: dict) -> str:
    """Format an agent response for the chat interface."""
    execution = response.get("execution", {})

    if not isinstance(execution, dict):
        return "The agent returned an invalid response."

    answer = (
        response.get("answer")
        or execution.get("answer")
    )

    if answer:
        return str(answer)

    if execution.get("status") != "success":
        return execution.get(
            "message",
            "The analysis could not be completed.",
        )

    result = execution.get("result", {})

    if isinstance(result, dict) and result.get("coordinated_summary"):
        summary = result["coordinated_summary"]

        if summary.get("answer"):
            return str(summary["answer"])

    if isinstance(result, dict):
        return json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return str(result)


def interactive_chat():
    """Run the terminal chatbot."""
    print("=" * 60)
    print("PHARMA COMMERCIAL INTELLIGENCE AI")
    print("=" * 60)
    print(
        "Ask about company performance, sales, market share, "
        "therapeutic groups and competitors."
    )
    print("Try: Why is ALKEM* growing slower than the market?")
    print("Type 'exit' to quit.")

    history = []

    while True:
        try:
            question = input("\nYou: ").strip()

            if not question:
                continue

            if question.lower() in {"exit", "quit", "bye"}:
                print("AI: See you, bro!")
                break

            print("\nAI: Investigating...")

            response = run_agent(
                question,
                conversation_history=history,
            )

            answer = format_result(response)
            print(f"\nAI:\n{answer}")

            history.append({
                "role": "user",
                "content": question,
            })
            history.append({
                "role": "assistant",
                "content": answer,
            })

            history = history[-12:]

        except KeyboardInterrupt:
            print("\nChat ended. See you, bro!")
            break

        except Exception as exc:
            print(f"\nError: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    interactive_chat()
