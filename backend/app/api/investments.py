"""Investment CRUD — stocks, ETFs, retirement accounts, crypto, etc."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Investment
from app.models.user import User
from app.schemas import InvestmentCreate, InvestmentOut, InvestmentUpdate

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("", response_model=list[InvestmentOut])
async def list_investments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_owned(db, Investment, current_user, order_by=Investment.name)


@router.post("", response_model=InvestmentOut)
async def create_investment(
    data: InvestmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_owned(db, Investment, data, current_user)


@router.get("/{investment_id}", response_model=InvestmentOut)
async def get_investment(
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_owned(db, Investment, investment_id, current_user)


@router.put("/{investment_id}", response_model=InvestmentOut)
async def update_investment(
    investment_id: int,
    data: InvestmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_owned(db, Investment, investment_id, data, current_user)


@router.delete("/{investment_id}")
async def delete_investment(
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_owned(db, Investment, investment_id, current_user)
