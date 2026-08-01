"""Bill scheduling: next-occurrence and upcoming-bills tests."""
from __future__ import annotations

from datetime import date

from app.services.bills import next_occurrence, upcoming_bills


class _Bill:
    def __init__(self, id, name, amount, due_date, frequency, auto_pay=False):
        self.id = id
        self.name = name
        self.amount = amount
        self.due_date = due_date
        self.frequency = frequency
        self.auto_pay = auto_pay


def test_future_due_date_is_unchanged():
    due = date(2026, 8, 15)
    assert next_occurrence(due, "monthly", date(2026, 7, 31)) == due


def test_monthly_rollover_skips_nothing():
    # Due Jan 31, viewed Feb 15 -> next occurrence is Feb 28 (clamped), not Mar 31.
    assert next_occurrence(date(2026, 1, 31), "monthly", date(2026, 2, 15)) == date(2026, 2, 28)


def test_monthly_rollover_across_year_boundary():
    # Due Dec 15, viewed Jan 5 -> next occurrence is Jan 15 of the next year.
    assert next_occurrence(date(2025, 12, 15), "monthly", date(2026, 1, 5)) == date(2026, 1, 15)


def test_monthly_same_day_today():
    # Due exactly today is not rolled forward.
    due = date(2026, 7, 31)
    assert next_occurrence(due, "monthly", due) == due


def test_monthly_leap_day_clamps_to_feb_28():
    # A Feb-29 bill in a non-leap year lands on the 28th.
    assert next_occurrence(date(2024, 2, 29), "monthly", date(2026, 2, 10)) == date(2026, 2, 28)


def test_weekly_rollover():
    due = date(2026, 7, 1)  # Wednesday
    assert next_occurrence(due, "weekly", date(2026, 7, 3)) == date(2026, 7, 8)


def test_yearly_rollover():
    due = date(2020, 3, 1)
    assert next_occurrence(due, "yearly", date(2026, 3, 2)) == date(2027, 3, 1)


def test_yearly_leap_day_clamps():
    # Due Feb 29 2024, viewed Mar 1 2026: 2025 and 2026 clamp to Feb 28 and both
    # already passed, so the next valid date is Feb 28 2027.
    assert next_occurrence(date(2024, 2, 29), "yearly", date(2026, 3, 1)) == date(2027, 2, 28)


def test_one_off_past_date_stays_put():
    due = date(2026, 6, 1)  # overdue, non-recurring
    assert next_occurrence(due, "", date(2026, 7, 31)) == due


def test_upcoming_bills_sorts_and_limits():
    today = date(2026, 7, 31)
    bills = [
        _Bill(1, "Rent", 1850, date(2026, 8, 1), "monthly"),
        _Bill(2, "Netflix", 15.99, date(2026, 8, 3), "monthly"),
        _Bill(3, "Gym", 40, date(2026, 8, 30), "monthly"),
        _Bill(4, "Electricity", 120, date(2026, 8, 10), "monthly"),
    ]
    result = upcoming_bills(bills, today, limit=3)
    assert [r["name"] for r in result] == ["Rent", "Netflix", "Electricity"]
    assert result[0]["days_until"] == 1
    assert result[0]["next_due_date"] == "2026-08-01"


def test_upcoming_bills_marks_overdue():
    today = date(2026, 7, 31)
    bills = [
        _Bill(1, "Past due bill", 99, date(2026, 7, 10), ""),  # one-off, overdue
        _Bill(2, "Future", 50, date(2026, 8, 5), "monthly"),
    ]
    result = upcoming_bills(bills, today)
    assert result[0]["name"] == "Past due bill"
    assert result[0]["days_until"] < 0
