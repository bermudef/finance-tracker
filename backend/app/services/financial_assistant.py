"""AI financial assistant — rule-based natural-language queries.

Parses user questions to identify intent, fetches relevant data
from the user's financial dashboard, and generates a natural-language
response. No external AI API is needed — the assistant is fully
self-contained and deterministic.
"""
from __future__ import annotations

import re
from typing import Optional

# Keywords that map to intents
INTENT_KEYWORDS = {
    "spending": [
        "spend", "spending", "expense", "expenses", "where did",
        "where does", "money going", "cost", "costs",
    ],
    "saving": [
        "save", "saving", "savings", "am i saving", "should i save",
        "enough savings", "emergency fund",
    ],
    "net_worth": [
        "net worth", "worth", "total value", "how much do i have",
        "balance", "balances",
    ],
    "budget": [
        "budget", "budgeting", "over budget", "at risk", "on track",
        "can i afford", "afford",
    ],
    "debt": [
        "debt", "debts", "owe", "loan", "loans", "mortgage", "credit card",
        "pay off", "paydown", "pay down", "debt payoff",
    ],
    "investment": [
        "invest", "investment", "investments", "portfolio", "stock",
        "stocks", "etf", "etfs", "return", "perform", "performance",
    ],
    "income": [
        "income", "earn", "earning", "salary", "paycheck", "make",
        "makes", "money coming in",
    ],
    "retirement": [
        "retire", "retirement", "retiree", "nest egg", "401k", "ira",
        "retirement account",
    ],
    "tax": [
        "tax", "taxable", "tax liability", "tax estimate", "quarterly",
        "irs", "deduction", "deductions",
    ],
    "health": [
        "health", "financial health", "score", "grade", "how healthy",
        "money health", "signal", "signals",
    ],
}

# Responses for each intent when no specific data is available
DEFAULT_RESPONSES = {
    "spending": "I don't have enough spending data yet. Add some transactions and categories to get insights.",
    "saving": "I don't have enough savings data yet. Add your accounts and savings goals to get a saving assessment.",
    "net_worth": "I don't have enough data to calculate your net worth yet. Add accounts and investments to get started.",
    "budget": "I don't have enough budget data yet. Set up budgets and add transactions to see if you're on track.",
    "debt": "I don't see any debt in your profile yet. Add your debts to get payoff strategies and insights.",
    "investment": "I don't have any investments in your profile yet. Add your holdings to see performance and allocation.",
    "income": "I don't have enough income data yet. Add your accounts and transactions to see your income breakdown.",
    "retirement": "I don't have enough retirement data yet. Add your retirement accounts and contributions to get a projection.",
    "tax": "I don't have enough data to estimate your taxes yet. Add income and investment details for a tax estimate.",
    "health": "I don't have enough data to calculate your financial health score yet. Add accounts, budgets, and goals to get a score.",
}


def _detect_intent(question: str) -> Optional[str]:
    """Detect the user's intent from their question."""
    question_lower = question.lower().strip()

    # Check for compound questions (multiple intents)
    intents_found = []
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in question_lower:
                intents_found.append(intent)
                break

    if not intents_found:
        return None

    # Return the most specific intent (prioritize non-generic keywords)
    priority = [
        "spending", "saving", "net_worth", "budget", "debt",
        "investment", "income", "retirement", "tax", "health",
    ]
    for p in priority:
        if p in intents_found:
            return p

    return intents_found[0]


def _extract_amount(question: str) -> Optional[float]:
    """Extract a dollar amount from the question."""
    patterns = [
        r"\$(\d[\d,]*)",  # $1,000 or $1000
        r"(\d[\d,]*)\s*dollars?",  # 1000 dollars
        r"(\d[\d,]*)\s*USD",  # 1000 USD
    ]
    for pattern in patterns:
        match = re.search(pattern, question.replace(",", ""))
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _generate_response(intent: str, data: dict) -> str:
    """Generate a natural-language response based on intent and data."""
    if intent == "spending":
        monthly_expense = data.get("monthly_expense", 0)
        if monthly_expense == 0:
            return DEFAULT_RESPONSES["spending"]
        return (
            f"Your spending this month is {format_currency(monthly_expense)}. "
            f"Your net cash flow is {format_currency(data.get('monthly_net', 0))} "
            f"(income {format_currency(data.get('monthly_income', 0))} minus expenses)."
        )

    elif intent == "saving":
        savings_rate = data.get("savings_rate")
        if savings_rate is None:
            return DEFAULT_RESPONSES["saving"]
        return (
            f"Your savings rate is {savings_rate:.1f}%. "
            + ("That's a strong savings rate — you're on track!" if savings_rate >= 20
               else "Consider increasing your savings rate to build a stronger financial foundation.")
        )

    elif intent == "net_worth":
        net_worth = data.get("net_worth", 0)
        if net_worth == 0:
            return DEFAULT_RESPONSES["net_worth"]
        return f"Your current net worth is {format_currency(net_worth)}."

    elif intent == "budget":
        over_count = data.get("over_budget_count", 0)
        at_risk_count = data.get("at_risk_count", 0)
        if over_count == 0 and at_risk_count == 0:
            return "All your budgets are on track this month. Great job!"
        parts = []
        if over_count > 0:
            parts.append(f"{over_count} budget(s) over limit")
        if at_risk_count > 0:
            parts.append(f"{at_risk_count} budget(s) at risk")
        return f"Budget alert: {', '.join(parts)}. Review your spending to get back on track."

    elif intent == "debt":
        total_debt = data.get("total_debt", 0)
        if total_debt == 0:
            return DEFAULT_RESPONSES["debt"]
        return (
            f"You have {format_currency(total_debt)} in total debt. "
            f"Consider using the debt payoff optimizer to compare avalanche vs. snowball strategies."
        )

    elif intent == "investment":
        total_value = data.get("investment_value", 0)
        gain_loss = data.get("investment_gain_loss", 0)
        if total_value == 0:
            return DEFAULT_RESPONSES["investment"]
        sign = "+" if gain_loss >= 0 else ""
        return (
            f"Your investments are worth {format_currency(total_value)} "
            f"with a total gain/loss of {sign}{format_currency(gain_loss)}."
        )

    elif intent == "income":
        monthly_income = data.get("monthly_income", 0)
        if monthly_income == 0:
            return DEFAULT_RESPONSES["income"]
        return f"Your monthly income is {format_currency(monthly_income)}."

    elif intent == "retirement":
        projection = data.get("retirement_projection")
        if projection is None:
            return DEFAULT_RESPONSES["retirement"]
        return (
            f"Based on your current savings and contributions, "
            f"your projected retirement balance is {format_currency(projection)}."
        )

    elif intent == "tax":
        tax_liability = data.get("tax_liability")
        if tax_liability is None:
            return DEFAULT_RESPONSES["tax"]
        return (
            f"Your estimated annual tax liability is {format_currency(tax_liability)}. "
            f"Quarterly estimated payments would be approximately {format_currency(tax_liability / 4)}."
        )

    elif intent == "health":
        health = data.get("health")
        if health is None:
            return DEFAULT_RESPONSES["health"]
        return (
            f"Your financial health score is {health['score']}/100 ({health['grade']}). "
            f"Key areas: {', '.join(health.get('signals', []))}."
        )

    return "I'm not sure I understand. Try asking about your spending, savings, net worth, budget, debt, investments, income, retirement, taxes, or financial health."


def format_currency(value: float) -> str:
    """Format a number as currency."""
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.0f}k"
    return f"${value:,.2f}"


def answer_question(question: str, dashboard_data: dict) -> dict:
    """Answer a natural-language financial question using dashboard data.

    Args:
        question: The user's natural-language question.
        dashboard_data: The user's dashboard data dict.

    Returns:
        A dict with 'intent', 'question', and 'answer' keys.
    """
    intent = _detect_intent(question)
    if intent is None:
        return {
            "intent": "unknown",
            "question": question,
            "answer": (
                "I can help with questions about your spending, savings, net worth, "
                "budget, debt, investments, income, retirement, taxes, or financial health. "
                "Try asking something like 'Where is my money going?' or 'Am I saving enough?'"
            ),
        }

    # Build a data context from the dashboard
    data_context = {
        "monthly_income": dashboard_data.get("monthly", {}).get("income", 0),
        "monthly_expense": abs(dashboard_data.get("monthly", {}).get("expense", 0)),
        "monthly_net": dashboard_data.get("monthly", {}).get("net", 0),
        "net_worth": dashboard_data.get("net_worth", 0),
        "total_debt": dashboard_data.get("debt", {}).get("total", 0),
        "investment_value": dashboard_data.get("investments", {}).get("total_value", 0),
        "investment_gain_loss": dashboard_data.get("investments", {}).get("gain_loss", 0),
        "over_budget_count": sum(
            1 for b in dashboard_data.get("budgets", []) if b.get("status") == "over"
        ),
        "at_risk_count": sum(
            1 for b in dashboard_data.get("budgets", []) if b.get("status") == "at_risk"
        ),
        "savings_rate": None,
        "retirement_projection": None,
        "tax_liability": None,
        "health": dashboard_data.get("health"),
    }

    # Compute savings rate if we have income and expense data
    monthly_income = data_context["monthly_income"]
    monthly_expense = data_context["monthly_expense"]
    if monthly_income > 0:
        savings = monthly_income - monthly_expense
        data_context["savings_rate"] = (savings / monthly_income) * 100

    answer = _generate_response(intent, data_context)

    return {
        "intent": intent,
        "question": question,
        "answer": answer,
    }
