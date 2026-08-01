from __future__ import annotations
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.models.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise _INVALID_CREDENTIALS

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _INVALID_CREDENTIALS

    if payload.get("type") != "access":
        raise _INVALID_CREDENTIALS

    user_id = payload.get("sub")
    if user_id is None:
        raise _INVALID_CREDENTIALS

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _INVALID_CREDENTIALS
    return user
