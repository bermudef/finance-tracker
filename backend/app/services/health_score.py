"""Financial health score: a 0-100 grade distilled from six weighted signals.

Model
-----
Each component answers one question and is normalized to a 0-100 score, then
combined with a fixed weight (the weights sum to 100):

    savings_rate      20%   Are you saving a healthy share of income? (20% rule)
    emergency_fund    20%   How many months of expenses could you survive on?
    debt_burden       20%   Are debt payments crowding out income? (DTI)
    budget_adherence  15%   Are your monthly budgets staying on track?
    credit_utilization 15%  How much of your available credit is in use? (30% rule)
    savings_goals     10%   How close are your savings goals to funded?

The pure `compute_health_score(metrics)` function has no DB access so it can be
unit tested exhaustively; the API router is responsible for gathering metrics.
"""

from __future__ import annotations

from typing import Any, Optional

# Sub-score keys, labels, and weights (must sum to 100).
COMPONENTS = [
    {"key": "savings_rate", "label": "Savings rate", "weight": 20},
    {"key": "emergency_fund", "label": "Emergency fund", "weight": 20},
    {"key": "debt_burden", "label": "Debt burden", "weight": 20},
    {"key": "budget_adherence", "label": "Budget adherence", "weight": 15},
    {"key": "credit_utilization", "label": "Credit utilization", "weight": 15},
    {"key": "savings_goals", "label": "Savings goals", "weight": 10},
]

# Debt payments at or below 10% of income are excellent; at 36% (the lender
# back-end limit) the score hits zero.
DTI_PERFECT = 0.10
DTI_ZERO = 0.36

# Debt burden status is judged on actual DTI bands, not the normalized score.
# This keeps the status text aligned with the detail line:
#     < 20%  -> on track
#     20-36% -> at risk
#     > 36%  -> over
DTI_ON_TRACK = 0.20

# A component is "on track" — healthy enough to skip its recommendation — only
# once its score is strictly over 75. The same bar applies to every component
# (savings rate, emergency fund, debt burden, budget adherence, credit
# utilization, savings goals), so a score of 75 or below still earns a
# recommendation.
ON_TRACK_SCORE = 75

# Scores at or below this value are treated as "over" for score-based statuses
# (savings rate, emergency fund, debt burden, savings goals). The score bands
# mirror the on-track cutoff: >75 on track, 50-75 at risk, <50 over.
AT_RISK_SCORE = 50

# Credit utilization is judged on the actual utilization ratio, not the
# normalized score, because the score is already 100 for anything at or under
# 30% and could not tell 20% from 26%. These bands stack on top:
#     < 25%  -> on track
#     25-30% -> at risk
#     > 30%  -> over
CREDIT_UTIL_ON_TRACK = 0.25
CREDIT_UTIL_OVER = 0.30


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _status_from_score(score: float) -> str:
    """Bucket a component score into on track / at risk / over.

    Uses the same 75 bar that gates recommendations; 50 separates "at risk"
    (actionable but not urgent) from "over" (needs immediate attention).
    """
    if score > ON_TRACK_SCORE:
        return "on_track"
    if score >= AT_RISK_SCORE:
        return "at_risk"
    return "over"


def _score_savings_rate(income: float, expense: float) -> dict[str, Any]:
    if income <= 0:
        return {"score": 0.0, "status": "over", "detail": "No income tracked this month"}
    rate = (income - expense) / income
    score = _clamp(rate / 0.20 * 100.0)
    return {
        "score": score,
        "status": _status_from_score(score),
        "detail": f"Saving {rate:.0%} of income this month (target 20%)",
    }


def _score_emergency_fund(liquid_assets: float, avg_monthly_expense: float) -> dict[str, Any]:
    if avg_monthly_expense <= 0:
        # No spending baseline — can't judge coverage; treat as neutral unless
        # there's nothing saved at all.
        return {
            "score": 50.0 if liquid_assets > 0 else 0.0,
            "status": _status_from_score(50.0 if liquid_assets > 0 else 0.0),
            "detail": "No expense baseline to compare against",
        }
    months = liquid_assets / avg_monthly_expense
    score = _clamp(months / 6.0 * 100.0)
    return {
        "score": score,
        "status": _status_from_score(score),
        "detail": f"Cash covers {months:.1f} months of expenses (target 6)",
    }


def _score_debt_burden(monthly_payments: float, monthly_income: float) -> dict[str, Any]:
    if monthly_income <= 0:
        return {"score": 0.0, "status": "over", "detail": "No income to measure debt load against"}
    dti = monthly_payments / monthly_income
    score = _clamp((DTI_ZERO - dti) / (DTI_ZERO - DTI_PERFECT) * 100.0)
    if dti > DTI_ZERO:
        status = "over"
    elif dti >= DTI_ON_TRACK:
        status = "at_risk"
    else:
        status = "on_track"
    return {
        "score": score,
        "status": status,
        "detail": f"Debt payments are {dti:.0%} of income (target under {DTI_ZERO:.0%})",
    }


def _score_budget_adherence(counts: dict[str, int]) -> dict[str, Any]:
    total = counts.get("on_track", 0) + counts.get("at_risk", 0) + counts.get("over", 0)
    if total == 0:
        return {"score": 50.0, "status": "at_risk", "detail": "No budgets set up yet"}
    # At-risk budgets count half — they may still be rescued before month-end.
    score = (counts.get("on_track", 0) + 0.5 * counts.get("at_risk", 0)) / total * 100.0
    at_risk = counts.get("at_risk", 0)
    over = counts.get("over", 0)
    detail = f"{counts.get('on_track', 0)} of {total} budgets on track"
    if at_risk:
        detail += f", {at_risk} at risk"
    if over:
        detail += f", {over} over"
    if over > 0:
        status = "over"
    elif at_risk > 0:
        status = "at_risk"
    else:
        status = "on_track"
    return {"score": score, "status": status, "detail": detail}


def _score_credit_utilization(balance: float, limit: float, card_count: int) -> dict[str, Any]:
    if card_count == 0:
        return {"score": 70.0, "status": "on_track", "detail": "No credit cards tracked"}
    if limit <= 0:
        # Cards exist but no limits are reported — we can't judge utilization.
        # Because it's a data gap rather than behavior, score it neutrally
        # instead of punishing the user with a zero.
        return {
            "score": 50.0,
            "status": "at_risk",
            "detail": "Credit cards have no reported limits",
        }
    utilization = balance / limit
    # Full marks at <=30% utilization, zero at >=60% (roughly where scores and
    # approval odds really start to suffer).
    score = _clamp((0.60 - utilization) / 0.30 * 100.0)
    if utilization > CREDIT_UTIL_OVER:
        status = "over"
    elif utilization >= CREDIT_UTIL_ON_TRACK:
        status = "at_risk"
    else:
        status = "on_track"
    return {
        "score": score,
        "status": status,
        "detail": f"Using {utilization:.0%} of available credit (target under 30%)",
    }


def _score_savings_goals(avg_progress: Optional[float], goal_count: int) -> dict[str, Any]:
    if goal_count == 0 or avg_progress is None:
        return {"score": 50.0, "status": "at_risk", "detail": "No savings goals set up yet"}
    score = _clamp(avg_progress * 100.0)
    return {
        "score": score,
        "status": _status_from_score(score),
        "detail": f"Goals are {avg_progress:.0%} funded on average",
    }


def compute_health_score(metrics: dict[str, Any]) -> dict[str, Any]:
    """Turn a metrics dict into a {score, grade, subscores, recommendations} result."""
    components = {
        "savings_rate": _score_savings_rate(
            float(metrics.get("monthly_income") or 0),
            float(metrics.get("monthly_expense") or 0),
        ),
        "emergency_fund": _score_emergency_fund(
            float(metrics.get("liquid_assets") or 0),
            float(metrics.get("avg_monthly_expense") or 0),
        ),
        "debt_burden": _score_debt_burden(
            float(metrics.get("monthly_debt_payments") or 0),
            float(metrics.get("monthly_income") or 0),
        ),
        "budget_adherence": _score_budget_adherence(
            metrics.get("budget_statuses") or {}
        ),
        "credit_utilization": _score_credit_utilization(
            float(metrics.get("credit_balance") or 0),
            float(metrics.get("credit_limit") or 0),
            int(metrics.get("credit_cards_count") or 0),
        ),
        "savings_goals": _score_savings_goals(
            metrics.get("goals_avg_progress"),
            int(metrics.get("goals_count") or 0),
        ),
    }

    subscores = []
    total = 0.0
    for comp in COMPONENTS:
        score = round(components[comp["key"]]["score"], 1)
        subscores.append(
            {
                "key": comp["key"],
                "label": comp["label"],
                "score": score,
                "weight": comp["weight"],
                "status": components[comp["key"]]["status"],
                "detail": components[comp["key"]]["detail"],
            }
        )
        total += score * comp["weight"]

    health_score = round(total / 100.0)
    if health_score >= 80:
        grade = "Excellent"
    elif health_score >= 60:
        grade = "Good"
    elif health_score >= 40:
        grade = "Fair"
    else:
        grade = "Needs work"

    recommendations = []
    for sub in sorted(subscores, key=lambda s: s["score"]):
        # A component is "on track" (no recommendation needed) only once its
        # status is on track. Credit utilization earns that only under 25%
        # utilization; anything at 25% or higher is flagged even though its
        # normalized score may still read 100.
        if sub["status"] == "on_track":
            continue
        recs = {
            "savings_rate": (
                "Aim to save at least 20% of your income. "
                + components["savings_rate"]["detail"]
            ),
            "emergency_fund": (
                "Build your emergency fund to cover 6 months of expenses. "
                + components["emergency_fund"]["detail"]
            ),
            "debt_burden": (
                "Lower your debt payments with the debt payoff optimizer. "
                + components["debt_burden"]["detail"]
            ),
            "budget_adherence": (
                "Review spending by category and rebalance your budgets. "
                + components["budget_adherence"]["detail"]
            ),
            "credit_utilization": (
                "Pay down credit card balances to stay under 30% utilization. "
                + components["credit_utilization"]["detail"]
            ),
            "savings_goals": (
                "Fund your savings goals on a schedule. "
                + components["savings_goals"]["detail"]
            ),
        }
        recommendations.append({"key": sub["key"], "text": recs[sub["key"]]})
        if len(recommendations) >= 4:
            break  # keep the list scannable

    return {
        "score": health_score,
        "grade": grade,
        "as_of": metrics.get("as_of"),
        "period_label": metrics.get("period_label"),
        "subscores": subscores,
        "recommendations": recommendations,
    }
