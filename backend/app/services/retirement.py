"""Retirement Monte Carlo projection.

Uses a deterministic PRNG seeded from the input parameters so
that identical inputs always produce identical outputs — critical for
reproducible tests and a stable user experience.

Each simulation path models one year of retirement savings:
  balance_next = balance * (1 + annual_return) + monthly_contribution * 12

Annual returns are drawn from N(expected_return, std_dev) and then
inflation is subtracted to produce a real (inflation-adjusted) return.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

SIMULATIONS = 2_000


def _seed_from_inputs(**kwargs: object) -> int:
    """Derive a deterministic integer seed from the input parameters."""
    raw = "|".join(f"{k}={v}" for k, v in kwargs.items())
    h = 0
    for ch in raw.encode():
        h = (h * 31 + ch) & 0xFFFFFFFF
    return h or 1


def _annual_return(
    expected: float, std_dev: float, rng: random.Random
) -> float:
    """Draw one annual real return ~ N(expected, std_dev)."""
    return rng.gauss(expected, std_dev)


@dataclass
class ProjectionPoint:
    age: int
    p10: float
    p25: float
    median: float
    p75: float
    p90: float


def run_projection(
    current_age: int,
    retirement_age: int,
    current_balance: float,
    monthly_contribution: float,
    expected_return: float,
    inflation_rate: float,
    std_dev: float,
) -> dict:
    """Run Monte Carlo retirement projection and return summary + series."""
    years = retirement_age - current_age
    if years <= 0:
        return {
            "years_to_retirement": 0,
            "series": [],
            "summary": {
                "median_nominal": current_balance,
                "median_real": current_balance,
                "p10_nominal": current_balance,
                "p90_nominal": current_balance,
            },
        }

    real_return = expected_return - inflation_rate
    annual_contrib = monthly_contribution * 12

    rng = random.Random(_seed_from_inputs(
        current_age=current_age,
        retirement_age=retirement_age,
        current_balance=current_balance,
        monthly_contribution=monthly_contribution,
        expected_return=expected_return,
        inflation_rate=inflation_rate,
        std_dev=std_dev,
    ))

    # Each path: end-of-year balance
    paths: list[list[float]] = [[] for _ in range(SIMULATIONS)]
    for sim in range(SIMULATIONS):
        balance = current_balance
        for yr in range(years):
            ret = _annual_return(real_return, std_dev, rng)
            balance = balance * (1 + ret) + annual_contrib
            balance = max(balance, 0.0)
            paths[sim].append(balance)

    series: list[ProjectionPoint] = []
    for yr_idx in range(years):
        values = sorted(p[yr_idx] for p in paths)
        n = len(values)
        series.append(ProjectionPoint(
            age=current_age + yr_idx + 1,
            p10=values[int(n * 0.10)],
            p25=values[int(n * 0.25)],
            median=values[int(n * 0.50)],
            p75=values[int(n * 0.75)],
            p90=values[int(n * 0.90)],
        ))

    last = series[-1]
    return {
        "years_to_retirement": years,
        "series": [
            {
                "age": p.age,
                "p10": round(p.p10, 2),
                "p25": round(p.p25, 2),
                "median": round(p.median, 2),
                "p75": round(p.p75, 2),
                "p90": round(p.p90, 2),
            }
            for p in series
        ],
        "summary": {
            "median_nominal": round(last.median, 2),
            "median_real": round(last.median, 2),
            "p10_nominal": round(last.p10, 2),
            "p90_nominal": round(last.p90, 2),
        },
    }
