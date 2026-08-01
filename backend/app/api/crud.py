"""Shared helpers for ownership-checked CRUD routers."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

PAGE_LIMIT = 200


async def list_owned(
    db: AsyncSession,
    model,
    user: User,
    order_by=None,
    filters: Optional[list] = None,
    limit: int = PAGE_LIMIT,
):
    stmt = select(model).where(model.user_id == user.id)
    for cond in filters or []:
        stmt = stmt.where(cond)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    stmt = stmt.limit(limit)
    return (await db.execute(stmt)).scalars().all()


async def get_owned(db: AsyncSession, model, obj_id: int, user: User):
    """Fetch an object only if it belongs to the user; 404 otherwise
    (no existence leak for foreign objects)."""
    obj = await db.get(model, obj_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


async def create_owned(db: AsyncSession, model, data, user: User, **extra):
    obj = model(**data.model_dump(), user_id=user.id, **extra)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_owned(db: AsyncSession, model, obj_id: int, data, user: User):
    obj = await get_owned(db, model, obj_id, user)
    updates = data.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(obj, key, val)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_owned(db: AsyncSession, model, obj_id: int, user: User):
    obj = await get_owned(db, model, obj_id, user)
    await db.delete(obj)
    await db.commit()
    return {"status": "deleted"}
