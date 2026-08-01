"""Credit card CRUD — all endpoints ownership-checked via get_current_user."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_owned, delete_owned, get_owned, list_owned, update_owned
from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import CreditCard
from app.models.user import User
from app.schemas import CreditCardCreate, CreditCardOut, CreditCardUpdate

router = APIRouter(prefix="/credit-cards", tags=["credit-cards"])


@router.get("", response_model=list[CreditCardOut])
async def list_credit_cards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_owned(db, CreditCard, current_user, order_by=CreditCard.name)


@router.post("", response_model=CreditCardOut)
async def create_credit_card(
    data: CreditCardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_owned(db, CreditCard, data, current_user)


@router.get("/{card_id}", response_model=CreditCardOut)
async def get_credit_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_owned(db, CreditCard, card_id, current_user)


@router.put("/{card_id}", response_model=CreditCardOut)
async def update_credit_card(
    card_id: int,
    data: CreditCardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_owned(db, CreditCard, card_id, data, current_user)


@router.delete("/{card_id}")
async def delete_credit_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_owned(db, CreditCard, card_id, current_user)
