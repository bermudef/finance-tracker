"""Debt payoff simulation: avalanche vs. snowball strategies.

Model
-----
- Balances accrue monthly interest (APR/12) on the full balance before payment.
- Every month each open debt receives its minimum payment (capped at the
  balance). The extra payment is applied to a single target debt in a fixed
  order decided once up front:
      avalanche: highest APR first  (minimizes total interest)
      snowball:  lowest balance first (quickest early wins, behavioral boost)
- When a debt is paid off, its minimum payment rolls into the attack pool
  from the following month — this rollover is the engine of both strategies.

The simulation is deterministic and pure (no DB access) so it can be unit
tested exhaustively.
"""

from __future__ import annotations

from typing import Any, Optional

MINIMUM_PAYMENT_FLOOR = 25.0  # debts without a stated minimum still amortize
MAX_MONTHS = 2400  # 200 years — guards against non-converging inputs
EPSILON = 0.005  # floating-point tolerance for "paid off"


def _monthly_rate(apr: float) -> float:
    return apr / 100.0 / 12.0


def _prepare(debts: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    """Copy and normalize debts; order the attack targets by strategy."""
    prepared = []
    for d in debts:
        principal = float(d.get("principal") or 0)
        if principal <= 0:
            continue  # paid-off debts don't enter the simulation
        prepared.append(
            {
                "name": str(d.get("name") or "Debt"),
                "principal": principal,
                "apr": float(d.get("interest_rate") or 0),
                "min_payment": max(
                    float(d.get("min_payment") or 0), MINIMUM_PAYMENT_FLOOR
                ),
            }
        )
    if strategy == "snowball":
        prepared.sort(key=lambda d: (d["principal"], d["apr"]))
    else:  # avalanche (default)
        prepared.sort(key=lambda d: (-d["apr"], d["principal"]))
    return prepared


def simulate_debt_payoff(
    debts: list[dict[str, Any]], extra_monthly: float, strategy: str = "avalanche"
) -> dict[str, Any]:
    """Simulate paying off `debts` with `extra_monthly` on top of minimums.

    Returns months-to-freedom, total interest paid, payoff order, and a
    month-by-month remaining-balance timeline for charting.
    """
    extra = max(float(extra_monthly), 0.0)
    prepared = _prepare(debts, strategy)
    if not prepared:
        return {
            "months_to_debt_free": 0,
            "total_interest": 0.0,
            "payoff_order": [],
            "timeline": [{"month": 0, "remaining": 0.0}],
            "did_not_converge": False,
        }

    balances = {d["name"]: d["principal"] for d in prepared}
    rates = {d["name"]: _monthly_rate(d["apr"]) for d in prepared}
    mins = {d["name"]: d["min_payment"] for d in prepared}
    targets = [d["name"] for d in prepared]

    open_debts = set(balances)
    payoff_months: dict[str, int] = {}
    attack_pool = extra
    month = 0
    total_interest = 0.0
    timeline = [{"month": 0, "remaining": round(sum(balances.values()), 2)}]

    while open_debts and month < MAX_MONTHS:
        month += 1

        # 1. Accrue interest on every open balance.
        for name in open_debts:
            interest = balances[name] * rates[name]
            balances[name] += interest
            total_interest += interest

        # 2. Pay minimums (capped at the balance).
        paid_this_month: set[str] = set()
        for name in list(open_debts):
            payment = min(balances[name], mins[name])
            balances[name] -= payment
            if balances[name] <= EPSILON:
                balances[name] = 0.0
                paid_this_month.add(name)

        # 3. Spend the attack pool on the current target, then the next, etc.
        for name in targets:
            if name not in open_debts or attack_pool <= 0:
                continue
            payment = min(balances[name], attack_pool)
            balances[name] -= payment
            attack_pool -= payment
            if balances[name] <= EPSILON:
                balances[name] = 0.0
                paid_this_month.add(name)

        # 4. Settle payoffs: record them and roll their minimums into the pool.
        for name in paid_this_month:
            if name in open_debts:
                open_debts.discard(name)
                payoff_months[name] = month
                attack_pool += mins[name]

        timeline.append({"month": month, "remaining": round(sum(balances.values()), 2)})

    return {
        "months_to_debt_free": month if not open_debts else None,
        "total_interest": round(total_interest, 2),
        "payoff_order": [
            {"name": name, "months": payoff_months[name]}
            for name in sorted(payoff_months, key=payoff_months.get)
        ],
        "timeline": timeline,
        "did_not_converge": bool(open_debts),
    }


def compare_strategies(
    debts: list[dict[str, Any]], extra_monthly: float
) -> dict[str, Any]:
    """Run both strategies and summarize which one wins on interest and time."""
    avalanche = simulate_debt_payoff(debts, extra_monthly, "avalanche")
    snowball = simulate_debt_payoff(debts, extra_monthly, "snowball")

    interest_savings = None
    months_faster = None
    if (
        not avalanche["did_not_converge"]
        and not snowball["did_not_converge"]
        and avalanche["total_interest"] is not None
        and snowball["total_interest"] is not None
    ):
        interest_savings = round(
            snowball["total_interest"] - avalanche["total_interest"], 2
        )
        months_faster = max(snowball["months_to_debt_free"] - avalanche["months_to_debt_free"], 0)

    return {
        "avalanche": avalanche,
        "snowball": snowball,
        "interest_savings": interest_savings,
        "months_faster": months_faster,
    }
