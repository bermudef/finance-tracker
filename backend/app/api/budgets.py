from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Budget, Category
from app.models.user import User
from app.schemas import BudgetCreate, BudgetOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


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
