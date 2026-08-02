"""Household management — shared finances for families and partners."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Household, HouseholdInvite, HouseholdMembership
from app.models.user import User

router = APIRouter(prefix="/households", tags=["households"])


class HouseholdCreate(BaseModel):
    name: str = Field(max_length=100, min_length=1)


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_by: int
    created_at: datetime


class HouseholdMembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    household_id: int
    user_id: int
    role: str
    joined_at: datetime


class HouseholdInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")


class HouseholdInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    household_id: int
    email: str
    role: str
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime]


class HouseholdMemberOut(HouseholdMembershipOut):
    email: str


class HouseholdInvitePendingOut(BaseModel):
    """An invite addressed to the current user, with household name for display."""

    id: int
    household_id: int
    household_name: str
    email: str
    role: str
    token: str
    created_at: datetime
    expires_at: datetime


@router.get("/invites/pending", response_model=list[HouseholdInvitePendingOut])
async def list_pending_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invites addressed to the current user that have not been accepted yet."""
    rows = (
        await db.execute(
            select(HouseholdInvite, Household.name)
            .join(Household, Household.id == HouseholdInvite.household_id)
            .where(
                HouseholdInvite.email == current_user.email,
                HouseholdInvite.accepted_at.is_(None),
            )
            .order_by(HouseholdInvite.created_at.desc())
        )
    ).all()
    return [
        {
            "id": invite.id,
            "household_id": invite.household_id,
            "household_name": household_name,
            "email": invite.email,
            "role": invite.role,
            "token": invite.token,
            "created_at": invite.created_at,
            "expires_at": invite.expires_at,
        }
        for invite, household_name in rows
    ]


@router.post("", response_model=HouseholdOut)
async def create_household(
    data: HouseholdCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new household and make the current user the owner."""
    household = Household(name=data.name, created_by=current_user.id)
    db.add(household)
    await db.commit()
    await db.refresh(household)

    # Add creator as owner member
    membership = HouseholdMembership(
        household_id=household.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(membership)
    await db.commit()

    return household


@router.get("", response_model=list[HouseholdOut])
async def list_households(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List households the current user belongs to."""
    rows = (
        await db.execute(
            select(Household)
            .join(HouseholdMembership, Household.id == HouseholdMembership.household_id)
            .where(HouseholdMembership.user_id == current_user.id)
        )
    ).scalars().all()
    return rows


@router.get("/{household_id}", response_model=HouseholdOut)
async def get_household(
    household_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a household by ID (must be a member)."""
    membership = (
        await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Household not found")

    household = await db.get(Household, household_id)
    return household


@router.get("/{household_id}/members", response_model=list[HouseholdMemberOut])
async def list_members(
    household_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List members of a household (must be a member)."""
    membership = (
        await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Household not found")

    rows = (
        await db.execute(
            select(HouseholdMembership, User.email)
            .join(User, HouseholdMembership.user_id == User.id)
            .where(HouseholdMembership.household_id == household_id)
        )
    ).all()
    return [
        {
            "id": m.id,
            "household_id": m.household_id,
            "user_id": m.user_id,
            "role": m.role,
            "joined_at": m.joined_at,
            "email": email,
        }
        for m, email in rows
    ]


@router.get("/{household_id}/invites", response_model=list[HouseholdInviteOut])
async def list_invites(
    household_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List invites for a household (owner/admin only)."""
    membership = (
        await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
                HouseholdMembership.role.in_(["owner", "admin"]),
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Only owners/admins can view invites")

    rows = (
        await db.execute(
            select(HouseholdInvite)
            .where(HouseholdInvite.household_id == household_id)
            .order_by(HouseholdInvite.created_at.desc())
        )
    ).scalars().all()
    return rows


@router.delete("/{household_id}/invites/{invite_id}")
async def cancel_invite(
    household_id: int,
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending invite (owner/admin only)."""
    membership = (
        await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
                HouseholdMembership.role.in_(["owner", "admin"]),
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Only owners/admins can cancel invites")

    invite = (
        await db.execute(
            select(HouseholdInvite).where(
                HouseholdInvite.id == invite_id,
                HouseholdInvite.household_id == household_id,
            )
        )
    ).scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    await db.delete(invite)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{household_id}/invites", response_model=HouseholdInviteOut)
async def create_invite(
    household_id: int,
    data: HouseholdInviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a user to join the household by email."""
    # Verify current user is admin/owner of this household
    membership = (
        await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
                HouseholdMembership.role.in_(["owner", "admin"]),
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Only owners/admins can invite")

    # Check if user already has an invite or membership
    existing_invite = (
        await db.execute(
            select(HouseholdInvite).where(
                HouseholdInvite.household_id == household_id,
                HouseholdInvite.email == data.email,
                HouseholdInvite.accepted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing_invite:
        raise HTTPException(status_code=400, detail="Invite already sent")

    existing_membership = (
        await db.execute(
            select(HouseholdMembership)
            .join(User, HouseholdMembership.user_id == User.id)
            .where(
                HouseholdMembership.household_id == household_id,
                User.email == data.email,
            )
        )
    ).scalar_one_or_none()
    if existing_membership:
        raise HTTPException(status_code=400, detail="User already a member")

    # Create invite
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    invite = HouseholdInvite(
        household_id=household_id,
        email=data.email,
        role=data.role,
        token=token,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    # TODO: Send email with invite link containing token

    return invite


@router.get("/invites/accept")
async def accept_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a household invite by token."""
    invite = (
        await db.execute(
            select(HouseholdInvite).where(
                HouseholdInvite.token == token,
                HouseholdInvite.accepted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")

    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite has expired")

    if invite.email != current_user.email:
        raise HTTPException(status_code=403, detail="Invite is for a different email")

    # Create membership
    membership = HouseholdMembership(
        household_id=invite.household_id,
        user_id=current_user.id,
        role=invite.role,
    )
    db.add(membership)

    # Mark invite as accepted
    invite.accepted_at = datetime.utcnow()
    await db.commit()

    return {"status": "ok", "household_id": invite.household_id}