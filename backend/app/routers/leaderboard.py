"""Leaderboard endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import LeaderboardEntry, User
from app.schemas import LeaderboardRow

router = APIRouter()


@router.get("", response_model=List[LeaderboardRow])
async def get_leaderboard(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(LeaderboardEntry)
        .options(selectinload(LeaderboardEntry.user))
        .order_by(LeaderboardEntry.total_points.desc())
        .limit(limit)
    )
    entries = result.scalars().all()

    rows = []
    for rank, entry in enumerate(entries, start=1):
        rows.append(
            LeaderboardRow(
                rank=rank,
                user_id=entry.user_id,
                username=entry.user.username,
                total_points=entry.total_points,
                quizzes_taken=entry.quizzes_taken,
                correct_answers=entry.correct_answers,
            )
        )
    return rows
