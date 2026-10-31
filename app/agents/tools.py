
import math


def calculate_sales_growth(
    previous_sales: float,
    current_sales: float
) -> dict:
    """
    Calculate sales growth between two periods.

    Note:
    This function calculates growth from supplied values.
    It does not fetch data from a pharmaceutical dataset.
    """

    # Validate the inputs
    try:
        previous_sales = float(previous_sales)
        current_sales = float(current_sales)
    except (TypeError, ValueError):
        raise ValueError("Sales values must be valid numbers.")

    if not math.isfinite(previous_sales) or not math.isfinite(current_sales):
        raise ValueError("Sales values must be finite numbers.")

    if previous_sales < 0 or current_sales < 0:
        raise ValueError("Sales values cannot be negative.")

    # Calculate the absolute change in sales
    absolute_change = current_sales - previous_sales

    # Percentage growth is undefined when previous sales are zero
    if previous_sales == 0:
        return {
            "previous_sales": previous_sales,
            "current_sales": current_sales,
            "absolute_change": absolute_change,
            "growth_percent": None,
            "status": "undefined",
            "message": (
                "Percentage growth cannot be calculated "
                "because previous sales were zero."
            )
        }

    # Calculate percentage growth
    growth_percent = (
        (current_sales - previous_sales)
        / previous_sales
    ) * 100

    # Classify the sales movement
    if growth_percent > 0:
        status = "growth"
    elif growth_percent < 0:
        status = "decline"
    else:
        status = "no_change"

    return {
        "previous_sales": previous_sales,
        "current_sales": current_sales,
        "absolute_change": round(absolute_change, 2),
        "growth_percent": round(growth_percent, 2),
        "status": status,
        "message": (
            f"Sales {status.replace('_', ' ')} by "
            f"{abs(round(growth_percent, 2))}%."
        )
    }


if __name__ == "__main__":
    # Synthetic test data, not actual pharma market data
    test_cases = [
        (100, 120),
        (100, 80),
        (100, 100),
        (0, 50),
    ]

    for previous, current in test_cases:
        print(f"\nPrevious sales: {previous}")
        print(f"Current sales: {current}")

        result = calculate_sales_growth(previous, current)
        print(result)
