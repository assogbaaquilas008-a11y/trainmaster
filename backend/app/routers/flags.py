"""Flags router – users dispute rejected answers."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Flag, Question
from app.schemas import FlagCreate, FlagOut

router = APIRouter()


@router.post("", response_model=FlagOut, status_code=201)
async def create_flag(
    body: FlagCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = (await db.execute(
        select(Question).where(Question.id == body.question_id)
    )).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    # Prevent duplicate flags from same user on same question
    existing = await db.execute(
        select(Flag).where(
            Flag.user_id == current_user.id,
            Flag.question_id == body.question_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "You already flagged this question")

    flag = Flag(
        user_id=current_user.id,
        question_id=body.question_id,
        submitted_text=body.submitted_text,
        reason=body.reason,
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag


@router.get("/mine", response_model=List[FlagOut])
async def my_flags(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Flag)
        .where(Flag.user_id == current_user.id)
        .order_by(Flag.created_at.desc())
    )
    return result.scalars().all()
