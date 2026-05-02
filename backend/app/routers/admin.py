"""
Admin endpoints (require is_admin=True):
  POST /api/admin/quizzes          – create quiz (JSON body or file upload)
  PUT  /api/admin/quizzes/{id}     – update quiz metadata
  DELETE /api/admin/quizzes/{id}   – soft-delete quiz
  GET  /api/admin/flags            – list pending flags
  POST /api/admin/flags/{id}/review – accept/reject a flag
  GET  /api/admin/users            – list users
  POST /api/admin/users/{id}/grant – add/remove points manually
  GET  /api/admin/stats            – aggregate statistics
"""

import json
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models import Answer, Attempt, Flag, LeaderboardEntry, Question, Quiz, User
from app.schemas import (
    FlagOut, FlagReview, QuizAdminDetailOut, QuizCreate, QuizOut, QuizUpdate, UserOut,
)
from app.services.email import notify_new_quiz

router = APIRouter()


# ---------------------------------------------------------------------------
# Quiz management
# ---------------------------------------------------------------------------

@router.post("/quizzes", response_model=QuizOut, status_code=201)
async def create_quiz(
    body: QuizCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    quiz = Quiz(
        title=body.title,
        description=body.description,
        timer_seconds=body.timer_seconds,
        created_by=admin.id,
    )
    db.add(quiz)
    await db.flush()

    for idx, q in enumerate(body.questions):
        db.add(Question(
            quiz_id=quiz.id,
            position=idx,
            prompt=q.prompt,
            correct_answer=q.correct_answer,
            alt_answers=q.alt_answers,
        ))

    await db.commit()
    await db.refresh(quiz)

    # Notify all active users in background
    background_tasks.add_task(_notify_users, db, quiz.title, quiz.id)

    return quiz


@router.post("/quizzes/upload", response_model=QuizOut, status_code=201)
async def upload_quiz_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Upload a quiz as a JSON file. Expected format:
    {
      "title": "...", "description": "...", "timer_seconds": 30,
      "questions": [{"prompt": "...", "correct_answer": "...", "alt_answers": "alt1|alt2"}]
    }
    """
    try:
        content = await file.read()
        data = json.loads(content)
        body = QuizCreate(**data)
    except (json.JSONDecodeError, Exception) as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}")

    return await create_quiz(body, background_tasks, db, admin)


@router.get("/quizzes", response_model=List[QuizAdminDetailOut])
async def list_all_quizzes(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .order_by(Quiz.created_at.desc())
    )
    return result.scalars().all()


@router.put("/quizzes/{quiz_id}", response_model=QuizOut)
async def update_quiz(
    quiz_id: int,
    body: QuizUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    quiz = (await db.execute(select(Quiz).where(Quiz.id == quiz_id))).scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(quiz, field, value)

    await db.commit()
    await db.refresh(quiz)
    return quiz


@router.delete("/quizzes/{quiz_id}", status_code=204)
async def delete_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    quiz = (await db.execute(select(Quiz).where(Quiz.id == quiz_id))).scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Quiz not found")
    quiz.is_active = False  # soft delete
    await db.commit()


# ---------------------------------------------------------------------------
# Flag review
# ---------------------------------------------------------------------------

@router.get("/flags", response_model=List[FlagOut])
async def list_flags(
    status_filter: Optional[str] = "pending",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    q = select(Flag)
    if status_filter:
        q = q.where(Flag.status == status_filter)
    result = await db.execute(q.order_by(Flag.created_at.desc()))
    return result.scalars().all()


@router.post("/flags/{flag_id}/review", response_model=FlagOut)
async def review_flag(
    flag_id: int,
    body: FlagReview,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    flag = (await db.execute(select(Flag).where(Flag.id == flag_id))).scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Flag not found")

    flag.status = body.status
    flag.reviewed_by = admin.id

    if body.status == "accepted":
        # Award points retroactively
        lb = (await db.execute(
            select(LeaderboardEntry).where(LeaderboardEntry.user_id == flag.user_id)
        )).scalar_one_or_none()
        if lb:
            lb.total_points += settings.POINTS_PER_CORRECT
            lb.correct_answers += 1

        # Update the answer record if it exists
        answer_result = await db.execute(
            select(Answer).where(
                Answer.question_id == flag.question_id,
                Answer.submitted_text == flag.submitted_text,
            )
        )
        for ans in answer_result.scalars().all():
            if ans.attempt.user_id == flag.user_id:
                ans.is_correct = True
                ans.points_awarded = settings.POINTS_PER_CORRECT

    if body.update_correct_answer:
        q = (await db.execute(
            select(Question).where(Question.id == flag.question_id)
        )).scalar_one_or_none()
        if q:
            q.correct_answer = body.update_correct_answer

    await db.commit()
    await db.refresh(flag)
    return flag


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users/{user_id}/grant")
async def grant_points(
    user_id: int,
    points: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    lb = (await db.execute(
        select(LeaderboardEntry).where(LeaderboardEntry.user_id == user_id)
    )).scalar_one_or_none()
    if not lb:
        raise HTTPException(404, "User not found")
    lb.total_points = max(0, lb.total_points + points)
    await db.commit()
    return {"user_id": user_id, "new_total": lb.total_points}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    total_users   = (await db.execute(select(func.count(User.id)))).scalar()
    total_quizzes = (await db.execute(select(func.count(Quiz.id)))).scalar()
    total_attempts = (await db.execute(select(func.count(Attempt.id)))).scalar()
    pending_flags = (await db.execute(
        select(func.count(Flag.id)).where(Flag.status == "pending")
    )).scalar()

    return {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "pending_flags": pending_flags,
    }


# ---------------------------------------------------------------------------
# Background task helper
# ---------------------------------------------------------------------------

async def _notify_users(db: AsyncSession, quiz_title: str, quiz_id: int) -> None:
    """Fetch all active user emails and send quiz notification."""
    result = await db.execute(select(User.email).where(User.is_active == True))  # noqa: E712
    emails = [row[0] for row in result.all()]
    if emails:
        await notify_new_quiz(emails, quiz_title, quiz_id)
