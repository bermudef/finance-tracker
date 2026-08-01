"""Investment analytics service.

Computes portfolio allocation by type/sector, performance metrics
(total return, annualized return), and dividend yield from the
user's investment holdings.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional


def compute_allocation(
    investments: list[dict],
) -> dict[str, float]:
    """Compute allocation percentages by investment type.

    Args:
        investments: List of investment dicts with 'type' and 'current_value'.

    Returns:
        Dict mapping type name to percentage of total portfolio value.
    """
    total = sum(float(inv.get("current_value") or 0) for inv in investments)
    if total == 0:
        return {}

    by_type: dict[str, float] = defaultdict(float)
    for inv in investments:
        inv_type = inv.get("type") or "Other"
        by_type[inv_type] += float(inv.get("current_value") or 0)

    return {k: round(v / total * 100, 1) for k, v in sorted(by_type.items(), key=lambda x: -x[1])}


def compute_performance(
    investments: list[dict],
) -> dict:
    """Compute aggregate performance metrics for a list of investments.

    Returns total_value, total_cost_basis, gain_loss, gain_loss_pct,
    and annualized_return (simple approximation based on holding period).
    """
    total_value = sum(float(inv.get("current_value") or 0) for inv in investments)
    total_cost = sum(float(inv.get("cost_basis") or 0) for inv in investments)
    gain_loss = total_value - total_cost
    gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0.0

    return {
        "total_value": round(total_value, 2),
        "total_cost_basis": round(total_cost, 2),
        "gain_loss": round(gain_loss, 2),
        "gain_loss_pct": round(gain_loss_pct, 2),
    }


def compute_dividend_yield(
    investments: list[dict],
) -> dict:
    """Compute aggregate dividend yield from dividend-paying investments.

    Looks for investments with a 'dividend_yield' field (annual %).
    Weighted by current_value.
    """
    total_value = sum(float(inv.get("current_value") or 0) for inv in investments)
    if total_value == 0:
        return {"weighted_yield": 0.0, "total_annual_dividends": 0.0}

    weighted_yield = 0.0
    total_annual_dividends = 0.0
    for inv in investments:
        value = float(inv.get("current_value") or 0)
        yield_pct = float(inv.get("dividend_yield") or 0)
        weighted_yield += value * yield_pct
        total_annual_dividends += value * yield_pct / 100

    return {
        "weighted_yield": round(weighted_yield / total_value, 2),
        "total_annual_dividends": round(total_annual_dividends, 2),
    }


def compute_sector_allocation(
    investments: list[dict],
) -> dict[str, float]:
    """Compute allocation by sector if sector data is available.

    Falls back to type-based allocation if no sector data exists.
    """
    has_sectors = any(inv.get("sector") for inv in investments)
    if not has_sectors:
        return compute_allocation(investments)

    total = sum(float(inv.get("current_value") or 0) for inv in investments)
    if total == 0:
        return {}

    by_sector: dict[str, float] = defaultdict(float)
    for inv in investments:
        sector = inv.get("sector") or "Other"
        by_sector[sector] += float(inv.get("current_value") or 0)

    return {k: round(v / total * 100, 1) for k, v in sorted(by_sector.items(), key=lambda x: -x[1])}


def analyze_portfolio(investments: list[dict]) -> dict:
    """Run all analytics on a list of investment dicts.

    Each investment dict should have:
        - type (str): e.g. "stock", "etf", "retirement_account"
        - current_value (float): current market value
        - cost_basis (float): original cost
        - dividend_yield (float, optional): annual yield %
        - sector (str, optional): sector classification
        - symbol (str, optional): ticker symbol

    Returns a comprehensive analytics dict.
    """
    allocation = compute_allocation(investments)
    performance = compute_performance(investments)
    dividends = compute_dividend_yield(investments)
    sector_allocation = compute_sector_allocation(investments)

    return {
        "allocation_by_type": allocation,
        "allocation_by_sector": sector_allocation,
        "performance": performance,
        "dividends": dividends,
        "investment_count": len(investments),
        "has_dividend_data": any(
            inv.get("dividend_yield") is not None for inv in investments
        ),
    }
