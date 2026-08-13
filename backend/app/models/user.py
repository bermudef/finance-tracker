from __future__ import annotations
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)  # set by the verify-email flow
    verification_token = Column(String(64), nullable=True, index=True)  # single-use token
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    accounts = relationship("Account", back_populates="user")
    categories = relationship("Category", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    budgets = relationship("Budget", back_populates="user")
    notifications = relationship("Notification", back_populates="user", order_by="Notification.created_at")
    household_memberships = relationship("HouseholdMembership", back_populates="user")
    household_invites = relationship("HouseholdInvite", back_populates="creator")
    created_households = relationship("Household", foreign_keys="Household.created_by")
