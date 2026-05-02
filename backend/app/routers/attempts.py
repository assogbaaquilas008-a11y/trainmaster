"""Attempts router – user quiz history."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Attempt
from app.schemas import AttemptDetailOut, AttemptOut

router = APIRouter()


@router.get("/mine", response_model=List[AttemptOut])
async def my_attempts(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Attempt)
        .where(Attempt.user_id == current_user.id)
        .order_by(Attempt.started_at.desc())
    )
    return result.scalars().all()


@router.get("/mine/{attempt_id}", response_model=AttemptDetailOut)
async def my_attempt_detail(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Attempt)
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
        .options(selectinload(Attempt.answers))
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        from fastapi import HTTPException
        raise HTTPException(404, "Attempt not found")
    return attempt
