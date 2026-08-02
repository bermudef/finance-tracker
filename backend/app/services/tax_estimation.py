"""Tax estimation service.

Estimates annual federal tax liability using 2025 tax brackets.
Handles ordinary income, long-term capital gains, and self-employment tax.
"""
from __future__ import annotations

from dataclasses import dataclass

# 2025 federal tax brackets (single filer)
TAX_BRACKETS = [
    (0, 11_925, 0.10),
    (11_925, 48_475, 0.12),
    (48_475, 103_350, 0.22),
    (103_350, 197_300, 0.24),
    (197_300, 250_525, 0.32),
    (250_525, 626_350, 0.35),
    (626_350, float("inf"), 0.37),
]

# 2025 long-term capital gains brackets (single filer)
CG_BRACKETS = [
    (0, 48_350, 0.00),
    (48_350, 533_400, 0.15),
    (533_400, float("inf"), 0.20),
]

STANDARD_DEDUCTION = 14_600  # 2025 single filer
SELF_EMPLOYMENT_TAX_RATE = 0.153  # 12.4% SS + 2.9% Medicare
SELF_EMPLOYMENT_THRESHOLD = 400  # minimum net earnings subject to SE tax


@dataclass
class TaxEstimate:
    annual_income: float
    deductions: float
    taxable_income: float
    ordinary_tax: float
    capital_gains_tax: float
    self_employment_tax: float
    total_tax: float
    effective_rate: float
    marginal_rate: float
    quarterly_estimated: float


def _tax_in_bracket(income: float, bracket_start: float, bracket_end: float, rate: float) -> float:
    """Tax owed within a single bracket."""
    if income <= bracket_start:
        return 0.0
    taxable_in_bracket = min(income, bracket_end) - bracket_start
    return taxable_in_bracket * rate


def compute_ordinary_tax(taxable_income: float) -> float:
    """Compute federal tax on ordinary income using 2025 brackets."""
    return sum(
        _tax_in_bracket(taxable_income, start, end, rate)
        for start, end, rate in TAX_BRACKETS
    )


def compute_capital_gains_tax(cg_income: float) -> float:
    """Compute federal tax on long-term capital gains using 2025 brackets."""
    return sum(
        _tax_in_bracket(cg_income, start, end, rate)
        for start, end, rate in CG_BRACKETS
    )


def compute_self_employment_tax(net_earnings: float) -> float:
    """Compute self-employment tax (15.3% on 92.35% of net earnings)."""
    if net_earnings < SELF_EMPLOYMENT_THRESHOLD:
        return 0.0
    return round(net_earnings * 0.9235 * SELF_EMPLOYMENT_TAX_RATE, 2)


def estimate_tax(
    annual_income: float = 0.0,
    capital_gains: float = 0.0,
    deductions: float = 0.0,
    self_employment_income: float = 0.0,
) -> TaxEstimate:
    """Estimate annual federal tax liability.

    Args:
        annual_income: W-2 salary, interest, dividends, etc.
        capital_gains: Long-term capital gains from investments.
        deductions: Above-the-line deductions (IRA contributions, etc.).
        self_employment_income: Net self-employment earnings.

    Returns:
        A TaxEstimate dataclass with all computed tax figures.
    """
    deductions = min(deductions, STANDARD_DEDUCTION)
    taxable_income = max(annual_income - deductions, 0)

    ordinary_tax = compute_ordinary_tax(taxable_income)
    capital_gains_tax = compute_capital_gains_tax(capital_gains)
    self_employment_tax = compute_self_employment_tax(self_employment_income)

    total_tax = ordinary_tax + capital_gains_tax + self_employment_tax
    effective_rate = (total_tax / annual_income * 100) if annual_income > 0 else 0.0

    # Marginal rate: the rate of the highest bracket reached
    marginal_rate = 0.0
    if taxable_income > 0:
        for start, end, rate in TAX_BRACKETS:
            if taxable_income > start:
                marginal_rate = rate

    quarterly_estimated = total_tax / 4

    return TaxEstimate(
        annual_income=round(annual_income, 2),
        deductions=round(deductions, 2),
        taxable_income=round(taxable_income, 2),
        ordinary_tax=round(ordinary_tax, 2),
        capital_gains_tax=round(capital_gains_tax, 2),
        self_employment_tax=round(self_employment_tax, 2),
        total_tax=round(total_tax, 2),
        effective_rate=round(effective_rate, 1),
        marginal_rate=round(marginal_rate * 100, 1),
        quarterly_estimated=round(quarterly_estimated, 2),
    )


# ---------- Tax-loss harvesting ----------

MIN_LOSS_TO_SUGGEST = 100.0  # ignore noise-sized losses
CAPITAL_GAINS_OFFSET_RATE = 0.15  # long-term capital gains rate (15% bracket)
ORDINARY_INCOME_OFFSET = 3_000.0  # max capital loss deductible vs. income per year


def suggest_loss_harvesting(investments: list[dict]) -> list[dict]:
    """Flag holdings trading below cost basis as tax-loss harvesting candidates.

    Args:
        investments: dicts with keys ``name``, ``symbol``, ``cost_basis``,
            ``current_value``, ``type``.

    Returns:
        Candidate holdings with unrealized loss and estimated tax savings,
        sorted by loss size (largest first). Empty when no holding has a
        loss above ``MIN_LOSS_TO_SUGGEST``.
    """
    candidates = []
    for holding in investments:
        cost = float(holding.get("cost_basis") or 0)
        value = float(holding.get("current_value") or 0)
        if cost <= 0:
            continue
        loss = cost - value
        if loss < MIN_LOSS_TO_SUGGEST:
            continue
        # A realized loss first offsets capital gains, then up to $3,000 of
        # ordinary income per year; the remainder carries forward. The
        # conservative estimate below assumes long-term gain rates.
        tax_savings = loss * CAPITAL_GAINS_OFFSET_RATE
        candidates.append(
            {
                "name": holding.get("name") or holding.get("symbol") or "Holding",
                "symbol": holding.get("symbol"),
                "type": holding.get("type"),
                "cost_basis": round(cost, 2),
                "current_value": round(value, 2),
                "unrealized_loss": round(loss, 2),
                "est_tax_savings": round(tax_savings, 2),
            }
        )

    candidates.sort(key=lambda c: c["unrealized_loss"], reverse=True)
    return candidates
