"""Debt CRUD — mortgage, auto, student, personal loans, etc."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Debt
from app.models.user import User
from app.schemas import DebtCreate, DebtOut, DebtUpdate

router = APIRouter(prefix="/debts", tags=["debts"])


@router.get("", response_model=list[DebtOut])
async def list_debts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_owned(db, Debt, current_user, order_by=Debt.name)


@router.post("", response_model=DebtOut)
async def create_debt(
    data: DebtCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_owned(db, Debt, data, current_user)


@router.get("/{debt_id}", response_model=DebtOut)
async def get_debt(
    debt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_owned(db, Debt, debt_id, current_user)


@router.put("/{debt_id}", response_model=DebtOut)
async def update_debt(
    debt_id: int,
    data: DebtUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_owned(db, Debt, debt_id, data, current_user)


@router.delete("/{debt_id}")
async def delete_debt(
    debt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_owned(db, Debt, debt_id, current_user)
