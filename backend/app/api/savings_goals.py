"""Savings goal CRUD — emergency fund, vacation, house down payment, etc."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import SavingsGoal
from app.models.user import User
from app.schemas import SavingsGoalCreate, SavingsGoalOut, SavingsGoalUpdate

router = APIRouter(prefix="/savings-goals", tags=["savings-goals"])


@router.get("", response_model=list[SavingsGoalOut])
async def list_savings_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_owned(db, SavingsGoal, current_user, order_by=SavingsGoal.name)


@router.post("", response_model=SavingsGoalOut)
async def create_savings_goal(
    data: SavingsGoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_owned(db, SavingsGoal, data, current_user)


@router.get("/{goal_id}", response_model=SavingsGoalOut)
async def get_savings_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_owned(db, SavingsGoal, goal_id, current_user)


@router.put("/{goal_id}", response_model=SavingsGoalOut)
async def update_savings_goal(
    goal_id: int,
    data: SavingsGoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_owned(db, SavingsGoal, goal_id, data, current_user)


@router.delete("/{goal_id}")
async def delete_savings_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_owned(db, SavingsGoal, goal_id, current_user)
