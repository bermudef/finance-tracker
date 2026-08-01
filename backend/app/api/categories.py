from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Category
from app.models.user import User
from app.schemas import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Category)
        .where(Category.user_id == current_user.id)
        .order_by(Category.name)
    )
    if type:
        stmt = stmt.where(Category.type == type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=CategoryOut)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.parent_id:
        parent = await db.get(Category, data.parent_id)
        if not parent or parent.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Parent category not found")
    category = Category(**data.model_dump(), user_id=current_user.id)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = await db.get(Category, category_id)
    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()
    return {"status": "deleted"}
