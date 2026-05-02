"""
Quiz router:
  GET  /api/quizzes            – list active quizzes
  GET  /api/quizzes/{id}       – quiz detail (questions without answers)
  POST /api/quizzes/{id}/start – start an attempt (enforces one-per-user)
  POST /api/quizzes/{id}/answer – submit one answer during an attempt
  POST /api/quizzes/{id}/finish – complete an attempt
  GET  /api/quizzes/{id}/history – user's per-question breakdown (review mode)
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Answer, Attempt, LeaderboardEntry, Question, Quiz
from app.schemas import (
    AttemptDetailOut, AttemptOut, QuizDetailOut, QuizOut,
    SubmitAnswer, ValidationResult,
)
from app.services.validation import validate_answer as _validate

router = APIRouter()


# ---------------------------------------------------------------------------
# List quizzes
# ---------------------------------------------------------------------------

@router.get("", response_model=List[QuizOut])
async def list_quizzes(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Quiz)
        .where(Quiz.is_active == True)  # noqa: E712
        .options(selectinload(Quiz.questions))
        .order_by(Quiz.created_at.desc())
    )
    quizzes = result.scalars().all()
    out = []
    for q in quizzes:
        d = QuizOut.model_validate(q)
        d.question_count = len(q.questions)
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Quiz detail
# ---------------------------------------------------------------------------

@router.get("/{quiz_id}", response_model=QuizDetailOut)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Quiz)
        .where(Quiz.id == quiz_id, Quiz.is_active == True)  # noqa: E712
        .options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    return quiz


# ---------------------------------------------------------------------------
# Start attempt
# ---------------------------------------------------------------------------

@router.post("/{quiz_id}/start", response_model=AttemptOut, status_code=201)
async def start_attempt(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Verify quiz exists
    quiz = (await db.execute(select(Quiz).where(Quiz.id == quiz_id))).scalar_one_or_none()
    if not quiz or not quiz.is_active:
        raise HTTPException(404, "Quiz not found or inactive")

    # Enforce one-attempt-per-user
    existing_row = await db.execute(
    select(Attempt).where(
        Attempt.user_id == current_user.id,
        Attempt.quiz_id == quiz_id,
    )
)
    existing = existing_row.scalar_one_or_none()

    if existing:
    # 🔁 Attempt en cours → reprendre
        if existing.completed_at is None:
            return existing

    # 👀 Attempt terminée → review
    raise HTTPException(
        status_code=409,
        detail="Attempt already completed"
    )

    attempt = Attempt(user_id=current_user.id, quiz_id=quiz_id)
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


# ---------------------------------------------------------------------------
# Submit one answer
# ---------------------------------------------------------------------------

@router.post("/{quiz_id}/answer", response_model=ValidationResult)
async def submit_answer(
    quiz_id: int,
    body: SubmitAnswer,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Find open attempt
    attempt_row = await db.execute(
        select(Attempt).where(
            Attempt.user_id == current_user.id,
            Attempt.quiz_id == quiz_id,
            Attempt.completed_at == None,  # noqa: E711
        )
    )
    attempt = attempt_row.scalar_one_or_none()
    if not attempt:
        raise HTTPException(400, "No active attempt for this quiz")

    # Fetch question
    q_row = await db.execute(
        select(Question).where(Question.id == body.question_id, Question.quiz_id == quiz_id)
    )
    question = q_row.scalar_one_or_none()
    if not question:
        raise HTTPException(404, "Question not found")

    # Validate
    result = await _validate(body.submitted_text, question.correct_answer, question.alt_answers)
    points = settings.POINTS_PER_CORRECT if result.is_correct else 0

    # Persist
    answer = Answer(
        attempt_id=attempt.id,
        question_id=question.id,
        submitted_text=body.submitted_text,
        is_correct=result.is_correct,
        confidence=result.confidence,
        validation_method=result.method,
        points_awarded=points,
    )
    db.add(answer)

    if result.is_correct:
        attempt.score += points

    await db.commit()

    return ValidationResult(
        question_id=question.id,
        is_correct=result.is_correct,
        confidence=result.confidence,
        method=result.method,
        correct_answer=question.correct_answer,
        points_awarded=points,
    )


# ---------------------------------------------------------------------------
# Finish attempt
# ---------------------------------------------------------------------------

@router.post("/{quiz_id}/finish", response_model=AttemptOut)
async def finish_attempt(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attempt_row = await db.execute(
        select(Attempt).where(
            Attempt.user_id == current_user.id,
            Attempt.quiz_id == quiz_id,
            Attempt.completed_at == None,  # noqa: E711
        )
    )
    attempt = attempt_row.scalar_one_or_none()
    if not attempt:
        raise HTTPException(400, "No active attempt")

    attempt.completed_at = datetime.now(timezone.utc)

    # Update leaderboard
    lb_row = await db.execute(
        select(LeaderboardEntry).where(LeaderboardEntry.user_id == current_user.id)
    )
    lb = lb_row.scalar_one_or_none()
    if lb:
        lb.total_points += attempt.score
        lb.quizzes_taken += 1
        # Count correct answers for this attempt
        answers_row = await db.execute(
            select(Answer).where(Answer.attempt_id == attempt.id, Answer.is_correct == True)  # noqa: E712
        )
        lb.correct_answers += len(answers_row.scalars().all())

    await db.commit()
    await db.refresh(attempt)
    return attempt


# ---------------------------------------------------------------------------
# History / review
# ---------------------------------------------------------------------------

@router.get("/{quiz_id}/history", response_model=AttemptDetailOut)
async def get_history(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Attempt)
        .where(Attempt.user_id == current_user.id, Attempt.quiz_id == quiz_id)
        .options(selectinload(Attempt.answers))
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(404, "No attempt found for this quiz")
    return attempt
