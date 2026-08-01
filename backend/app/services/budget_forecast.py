"""Budget forecasting service.

Predicts next month's spending by category using a weighted moving average
of the last 6 months of historical data. Categories that are projected to
exceed their budget are flagged with a confidence level.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

MONTHS_TO_ANALYZE = 6
# Weights for the weighted moving average: more recent months get higher weight.
# Index 0 = oldest month, index 5 = most recent month.
WEIGHTS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def _month_start(d: date) -> date:
    """Return the first day of the month for a given date."""
    return d.replace(day=1)


def month_key(d: date) -> str:
    """Return a YYYY-MM key for a date."""
    return d.strftime("%Y-%m")


def forecast(
    monthly_spending: dict[str, dict[str, float]],
    budgets: dict[str, float],
) -> dict:
    """Forecast next month's spending by category.

    Args:
        monthly_spending: Mapping of category_name -> {month_key: amount}.
            Month keys are "YYYY-MM" strings. Only the last 6 months are used.
        budgets: Mapping of category_name -> budget amount for that category.

    Returns:
        A dict with:
            - forecasts: list of category forecast objects
            - flagged: list of categories projected to exceed budget
            - total_forecast: total predicted spending
            - total_budget: total budgeted spending
    """
    # Sort months descending (most recent first)
    all_months = set()
    for cat_spending in monthly_spending.values():
        all_months.update(cat_spending.keys())
    sorted_months = sorted(all_months, reverse=True)[:MONTHS_TO_ANALYZE]

    if not sorted_months:
        return {
            "forecasts": [],
            "flagged": [],
            "total_forecast": 0.0,
            "total_budget": 0.0,
        }

    forecasts = []
    flagged = []

    for category, spending_by_month in monthly_spending.items():
        # Collect spending for the analyzed months, most recent first
        values = []
        for month in sorted_months:
            values.append(spending_by_month.get(month, 0.0))

        # Weighted moving average: weight[0] is for oldest month, weight[-1] for most recent
        weighted_sum = sum(v * w for v, w in zip(values, WEIGHTS[: len(values)]))
        weight_total = sum(WEIGHTS[: len(values)])
        predicted = weighted_sum / weight_total if weight_total > 0 else 0.0

        # Standard deviation of the historical values for confidence interval
        if len(values) >= 2:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = variance ** 0.5
        else:
            std_dev = 0.0

        budget = budgets.get(category)
        will_exceed = budget is not None and predicted > budget
        confidence = "high" if std_dev < predicted * 0.2 else "medium" if std_dev < predicted * 0.5 else "low"

        forecast_entry = {
            "category": category,
            "predicted": round(predicted, 2),
            "p10": round(max(predicted - 1.28 * std_dev, 0), 2),
            "p90": round(predicted + 1.28 * std_dev, 2),
            "budget": round(budget, 2) if budget is not None else None,
            "will_exceed": will_exceed,
            "confidence": confidence,
            "months_of_data": len(values),
        }
        forecasts.append(forecast_entry)

        if will_exceed:
            flagged.append(forecast_entry)

    # Sort forecasts by predicted spending descending
    forecasts.sort(key=lambda f: f["predicted"], reverse=True)
    flagged.sort(key=lambda f: f["predicted"], reverse=True)

    total_forecast = round(sum(f["predicted"] for f in forecasts), 2)
    total_budget = round(
        sum(f["budget"] for f in forecasts if f["budget"] is not None), 2
    )

    return {
        "forecasts": forecasts,
        "flagged": flagged,
        "total_forecast": total_forecast,
        "total_budget": total_budget,
    }
