"""S&P 500 benchmark comparison.

Compares the user's total portfolio return against the S&P 500 over a
lookback window, using real monthly closes bundled with the app
(``app/data/spx_monthly.json``, fetched from Yahoo Finance on 2026-08-01).

The bundled dataset runs from 2016-08 through 2026-07, so windows of up to
10 years are supported. Returns both the raw return percentages and an
indexed series (start = 100) for charting.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

# Longest supported lookback, in years (dataset starts 2016-08).
MAX_YEARS = 10

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "spx_monthly.json"
)

_cache: Optional[list[dict[str, Any]]] = None


def load_spx_series() -> list[dict[str, Any]]:
    """Load the bundled S&P 500 monthly closes, newest last."""
    global _cache
    if _cache is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)["series"]
    return _cache


def _window(series: list[dict[str, Any]], years: int) -> list[dict[str, Any]]:
    """Slice the trailing `years` of monthly closes, start month included.

    The dataset has 12 closes per year, so the window is
    ``12 * years + 1`` points. ``years`` is clamped to MAX_YEARS first, which
    keeps the start index inside the array (10 years => index 0).
    """
    years = max(1, min(years, MAX_YEARS))
    start_index = max(len(series) - years * 12 - 1, 0)
    return series[start_index:]


def benchmark_return(years: int) -> dict[str, Any]:
    """S&P 500 total return over the trailing `years` (price only).

    Returns the start/end month labels, the raw return percentage, and an
    annualized figure so it can be compared with user numbers of any shape.
    """
    series = load_spx_series()
    window = _window(series, years)
    start = window[0]
    end = window[-1]
    start_close = float(start["close"])
    end_close = float(end["close"])
    total_return = (end_close - start_close) / start_close
    years = max(1, min(years, MAX_YEARS))

    return {
        "years": years,
        "start_month": start["month"],
        "end_month": end["month"],
        "return_pct": round(total_return * 100, 2),
        "annualized_pct": round(((1 + total_return) ** (1 / years) - 1) * 100, 2),
        "disclaimer": "S&P 500 price return only; excludes dividends.",
    }


def build_comparison(
    cost_basis: float,
    current_value: float,
    years: int,
) -> dict[str, Any]:
    """Compare the user's total portfolio return with the S&P 500.

    The user's total return is (current_value - cost_basis) / cost_basis.
    The benchmark series is the S&P 500 indexed to 100 at the window start so
    both figures can be shown side by side on one chart.
    """
    series = load_spx_series()
    window = _window(series, years)

    start_close = float(window[0]["close"])
    benchmark = [
        {"month": m["month"], "index": round(float(m["close"]) / start_close * 100, 2)}
        for m in window
    ]

    user_return = (current_value - cost_basis) / cost_basis if cost_basis > 0 else 0.0
    bench = benchmark_return(years)

    return {
        "years": bench["years"],
        "user_return_pct": round(user_return * 100, 2),
        "benchmark_return_pct": bench["return_pct"],
        "start_month": bench["start_month"],
        "end_month": bench["end_month"],
        "series": benchmark,
        "note": (
            "Your return is the gain on total cost basis; the benchmark line is "
            "the S&P 500 indexed to 100 at the start of the window."
        ),
    }
