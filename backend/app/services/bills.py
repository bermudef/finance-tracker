"""Bill scheduling helpers: computing the next occurrence of a recurring bill.

Pure functions (no DB access) so they can be unit tested exhaustively.

Semantics
---------
- A bill whose due date hasn't passed yet is "upcoming" on that date.
- Recurring bills (weekly / monthly / yearly) roll forward to their next
  occurrence once today has passed the stored due date. Day-of-month overflow
  (e.g. the 31st rolling into a 30-day month) clamps to the last valid day,
  matching how lenders actually schedule payments.
"""

from __future__ import annotations

from datetime import date, timedelta

from typing import Any, Optional

# How many upcoming bills to surface on the dashboard.
DEFAULT_LIMIT = 5


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    return (date(next_year, next_month, 1) - date(year, month, 1)).days


def next_occurrence(due_date: date, frequency: str, today: date) -> date:
    """Return the next date on or after `today` this bill is due.

    Non-recurring bills stay on their stored date (which may be in the past —
    the dashboard can still show them as overdue).
    """
    if due_date >= today:
        return due_date

    if frequency == "weekly":
        days_ahead = ((today - due_date).days + 6) // 7 * 7
        return due_date + timedelta(days=days_ahead)

    if frequency == "monthly":
        # Advance one month at a time until the (day-clamped) due date reaches
        # today. Iteration is bounded and obviously correct — no month
        # arithmetic to get wrong at year boundaries or on the 29th-31st.
        months_ahead = 1
        while True:
            year = due_date.year + (due_date.month - 1 + months_ahead) // 12
            month = (due_date.month - 1 + months_ahead) % 12 + 1
            candidate = date(year, month, min(due_date.day, _days_in_month(year, month)))
            if candidate >= today:
                return candidate
            months_ahead += 1

    if frequency == "yearly":
        years_ahead = 1
        while True:
            year = due_date.year + years_ahead
            candidate = date(year, due_date.month, min(due_date.day, _days_in_month(year, due_date.month)))
            if candidate >= today:
                return candidate
            years_ahead += 1

    return due_date  # unknown/one-off frequency: keep the stored date


def upcoming_bills(
    bills: list[Any], today: date, limit: int = DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """Sort bills by days until their next due date and return the top `limit`.

    Each bill needs `.name`, `.amount`, `.due_date`, and `.frequency`. The
    result includes `next_due_date` and `days_until` (negative = overdue).
    """
    rows = []
    for b in bills:
        due = b.due_date if b.due_date is not None else today + timedelta(days=30)
        next_due = next_occurrence(due, b.frequency or "", today)
        rows.append(
            {
                "id": b.id,
                "name": b.name,
                "amount": float(b.amount or 0),
                "frequency": b.frequency or "monthly",
                "auto_pay": bool(getattr(b, "auto_pay", False)),
                "next_due_date": next_due.isoformat(),
                "days_until": (next_due - today).days,
            }
        )
    rows.sort(key=lambda r: r["days_until"])
    return rows[:limit]
