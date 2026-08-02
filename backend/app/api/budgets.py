from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Budget, Category
from app.models.user import User
from app.schemas import BudgetCreate, BudgetOut, BudgetUpdate

router = APIRouter(prefix="/budgets", tags=["budgets"])

BUDGET_EXPORT_COLUMNS = ["name", "category", "amount", "period", "rollover"]


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Budget)
        .where(Budget.user_id == current_user.id)
        .order_by(Budget.name)
    )
    return result.scalars().all()


@router.get("/export")
async def export_budgets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the user's budgets as CSV."""
    rows = (
        await db.execute(
            select(Budget)
            .where(Budget.user_id == current_user.id)
            .order_by(Budget.name)
        )
    ).scalars().all()

    category_names: dict[int, str] = {}
    if rows:
        category_ids = {b.category_id for b in rows if b.category_id}
        if category_ids:
            category_names = {
                c.id: c.name
                for c in (await db.execute(select(Category).where(Category.id.in_(category_ids)))).scalars()
            }

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=BUDGET_EXPORT_COLUMNS)
    writer.writeheader()
    for b in rows:
        writer.writerow(
            {
                "name": b.name,
                "category": category_names.get(b.category_id) or "",
                "amount": f"{float(b.amount):.2f}",
                "period": b.period,
                "rollover": str(bool(b.rollover)),
            }
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=budgets.csv"},
    )


@router.post("", response_model=BudgetOut)
async def create_budget(
    data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    budget = Budget(**data.model_dump(), user_id=current_user.id)
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = await db.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Budget not found")
    updates = data.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"]:
        category = await db.get(Category, updates["category_id"])
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    for key, value in updates.items():
        setattr(budget, key, value)
    await db.commit()
    await db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = await db.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    await db.commit()
    return {"status": "deleted"}
