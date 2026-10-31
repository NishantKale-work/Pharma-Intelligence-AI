
import json

from app.agents.company_deep_dive import (
    build_company_deep_dive,
    print_deep_dive,
)

from app.agents.commercial_strategy import (
    generate_commercial_brief,
)

from app.agents.agent import interactive_chat

from app.core.data_quality import validate_project_data


def print_json(data: dict) -> None:
    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


def run_company_deep_dive() -> None:
    company = input(
        "Company name (e.g. ALKEM*): "
    ).strip()

    competitors_text = input(
        "Competitors separated by commas (e.g. CIPLA, SUN*): "
    ).strip()

    competitors = [
        name.strip()
        for name in competitors_text.split(",")
        if name.strip()
    ]

    report = build_company_deep_dive(
        company=company,
        competitors=competitors or None,
    )

    print_deep_dive(report)


def run_commercial_strategy() -> None:
    company = input(
        "Company name (e.g. ALKEM*): "
    ).strip()

    competitors_text = input(
        "Competitors separated by commas: "
    ).strip()

    competitors = [
        name.strip()
        for name in competitors_text.split(",")
        if name.strip()
    ]

    brief = generate_commercial_brief(
        company,
        competitors or None,
    )

    print_json(brief)


def main() -> None:
    while True:
        print("\n" + "=" * 68)
        print("          PHARMA COMMERCIAL INTELLIGENCE")
        print("=" * 68)
        print("1. Company deep dive")
        print("2. Commercial strategy brief")
        print("3. Validate source datasets")
        print("4. Ask Pharma Intelligence AI")
        print("5. Exit")

        choice = input("\nSelect an option: ").strip()

        if choice == "1":
            run_company_deep_dive()

        elif choice == "2":
            run_commercial_strategy()

        elif choice == "3":
            print_json(validate_project_data())

        elif choice == "4":
            interactive_chat()

        elif choice == "5":
            print("Exiting Pharma Commercial Intelligence.")
            break

        else:
            print("Invalid option. Choose 1, 2, 3, 4 or 5.")


if __name__ == "__main__":
    main()
