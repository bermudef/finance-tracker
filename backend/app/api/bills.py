"""Bill CRUD — recurring bills and subscriptions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Bill
from app.models.user import User
from app.schemas import BillCreate, BillOut, BillUpdate

router = APIRouter(prefix="/bills", tags=["bills"])


@router.get("", response_model=list[BillOut])
async def list_bills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_owned(db, Bill, current_user, order_by=Bill.due_date)


@router.post("", response_model=BillOut)
async def create_bill(
    data: BillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_owned(db, Bill, data, current_user)


@router.get("/{bill_id}", response_model=BillOut)
async def get_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_owned(db, Bill, bill_id, current_user)


@router.put("/{bill_id}", response_model=BillOut)
async def update_bill(
    bill_id: int,
    data: BillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_owned(db, Bill, bill_id, data, current_user)


@router.delete("/{bill_id}")
async def delete_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_owned(db, Bill, bill_id, current_user)
