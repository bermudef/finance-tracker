"""Investment CRUD — stocks, ETFs, retirement accounts, crypto, etc."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Investment
from app.models.user import User
from app.schemas import InvestmentCreate, InvestmentOut, InvestmentUpdate
from app.services.benchmark import build_comparison
from app.services.investment_analytics import analyze_portfolio

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("")
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


@router.get("/analytics")
async def investment_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Portfolio analytics: allocation, performance, and dividend yield."""
    rows = (
        await db.execute(
            select(Investment).where(Investment.user_id == current_user.id)
        )
    ).scalars().all()

    investments = [
        {
            "type": r.type,
            "current_value": float(r.current_value or 0),
            "cost_basis": float(r.cost_basis or 0),
            "symbol": r.symbol,
        }
        for r in rows
    ]

    return analyze_portfolio(investments)


@router.get("/benchmark")
async def investment_benchmark(
    years: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare the user's total investment return against the S&P 500.

    ``years`` selects the lookback window (1, 3, 5, or 10 supported by the
    bundled dataset). The user's return is measured on total cost basis,
    which is the only historical anchor the data model has.
    """
    rows = (
        await db.execute(
            select(Investment).where(Investment.user_id == current_user.id)
        )
    ).scalars().all()
    cost_basis = sum(float(r.cost_basis or 0) for r in rows)
    current_value = sum(float(r.current_value or 0) for r in rows)

    return build_comparison(cost_basis, current_value, years)


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
