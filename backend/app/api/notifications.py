"""Notifications CRUD — bill reminders, budget alerts, savings milestones."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str = Field(max_length=200)
    message: str
    type: str = Field(default="general", max_length=20)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    type: str
    read: bool
    created_at: datetime


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Notification)
            .where(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc())
        )
    ).scalars().all()
    return rows


@router.post("", response_model=NotificationOut)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = Notification(
        user_id=current_user.id,
        title=data.title,
        message=data.message,
        type=data.type,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        return {"status": "not_found"}
    notification.read = True
    await db.commit()
    return {"status": "ok"}


@router.patch("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Notification).where(
                Notification.user_id == current_user.id,
                Notification.read.is_(False),
            )
        )
    ).scalars().all()
    for notification in rows:
        notification.read = True
    await db.commit()
    return {"status": "ok", "marked": len(rows)}


@router.post("/generate", response_model=list[NotificationOut])
async def generate_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create notifications from live signals: bills due within a week and
    budgets that are over or at risk. An unread notification with the same
    title is not re-created, so repeated calls stay idempotent."""
    items = await generate_bill_reminders(db, current_user.id)
    items += await generate_budget_alerts(db, current_user.id)
    items += await generate_savings_milestones(db, current_user.id)

    existing = (
        await db.execute(
            select(Notification.title).where(
                Notification.user_id == current_user.id,
                Notification.read.is_(False),
            )
        )
    ).scalars().all()
    existing_titles = set(existing)

    created = []
    for item in items:
        if item["title"] in existing_titles:
            continue
        notification = Notification(
            user_id=current_user.id,
            title=item["title"],
            message=item["message"],
            type=item["type"],
        )
        db.add(notification)
        created.append(notification)

    if created:
        await db.commit()
        for notification in created:
            await db.refresh(notification)
    return created


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        return {"status": "not_found"}
    await db.delete(notification)
    await db.commit()
    return {"status": "deleted"}


async def generate_bill_reminders(
    db: AsyncSession,
    user_id: int,
) -> list[dict]:
    """Generate bill reminder notifications for bills due within 7 days."""
    from app.models.domain import Bill

    today = date.today()
    week_from_now = today + timedelta(days=7)

    bills = (
        await db.execute(
            select(Bill)
            .where(
                Bill.user_id == user_id,
                Bill.is_active.is_(True),
                Bill.due_date >= today,
                Bill.due_date <= week_from_now,
            )
        )
    ).scalars().all()

    notifications = []
    for bill in bills:
        days_until = (bill.due_date - today).days
        if days_until <= 0:
            title = f"Bill due today: {bill.name}"
            message = f"{bill.name} of {bill.amount:.2f} is due today."
        elif days_until == 1:
            title = f"Bill due tomorrow: {bill.name}"
            message = f"{bill.name} of {bill.amount:.2f} is due tomorrow."
        else:
            title = f"Bill due in {days_until} days: {bill.name}"
            message = f"{bill.name} of {bill.amount:.2f} is due in {days_until} days."

        notifications.append({"title": title, "message": message, "type": "bill_reminder"})

    return notifications


async def generate_budget_alerts(
    db: AsyncSession,
    user_id: int,
) -> list[dict]:
    """Generate budget alert notifications for over-budget categories."""
    from app.api.dashboard import compute_budget_statuses

    budgets = await compute_budget_statuses(db, user_id)
    alerts = []

    for budget in budgets:
        if budget.get("status") == "over":
            alerts.append(
                {
                    "title": f"Over budget: {budget['name']}",
                    "message": f"You've spent {budget['spent']:.2f} against a {budget['amount']:.2f} budget.",
                    "type": "budget_alert",
                }
            )
        elif budget.get("status") == "at_risk":
            alerts.append(
                {
                    "title": f"At risk: {budget['name']}",
                    "message": f"You're on pace to exceed your {budget['amount']:.2f} budget for {budget['name']}.",
                    "type": "budget_alert",
                }
            )

    return alerts


async def generate_savings_milestones(
    db: AsyncSession,
    user_id: int,
) -> list[dict]:
    """Generate milestone alerts for savings goals.

    Fires once per milestone (50%, 75%, 100%) per goal: a notification with
    the exact milestone title is looked up across read AND unread rows, so a
    goal that has already been celebrated is not celebrated again on the next
    generate call.
    """
    from app.models.domain import SavingsGoal

    goals = (
        await db.execute(
            select(SavingsGoal).where(
                SavingsGoal.user_id == user_id,
                SavingsGoal.is_active.is_(True),
            )
        )
    ).scalars().all()

    if not goals:
        return []

    # Titles already sent for this user, regardless of read state.
    existing = (
        await db.execute(
            select(Notification.title).where(Notification.user_id == user_id)
        )
    ).scalars().all()
    existing_titles = set(existing)

    notifications = []
    for goal in goals:
        target = float(goal.target_amount or 0)
        current = float(goal.current_amount or 0)
        if target <= 0:
            continue
        pct = current / target * 100

        # The highest milestone crossed, in celebration order.
        milestone = None
        if pct >= 100:
            milestone = 100
        elif pct >= 75:
            milestone = 75
        elif pct >= 50:
            milestone = 50
        if milestone is None:
            continue

        if milestone == 100:
            title = f"Savings goal achieved: {goal.name}"
            message = (
                f"You've saved {current:.2f} of your {target:.2f} target for {goal.name}. "
                f"Congratulations!"
            )
        else:
            title = f"Savings goal {milestone}% reached: {goal.name}"
            message = (
                f"{goal.name} is {pct:.1f}% funded ({current:.2f} of {target:.2f}). "
                f"Keep it going!"
            )

        if title in existing_titles:
            continue
        notifications.append({"title": title, "message": message, "type": "savings_milestone"})

    return notifications
