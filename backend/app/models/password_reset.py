from __future__ import annotations
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.models.database import Base


class PasswordResetToken(Base):
    """Single-use, time-boxed password reset token.

    Security: only the SHA-256 hash of the raw token is stored, so a database
    leak cannot be replayed to reset passwords. The raw token is shown to the
    user once (returned in the API response in dev; emailed in production).
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
