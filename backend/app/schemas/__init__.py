"""
Pydantic v2 schemas for all request bodies and API responses.
Grouped by domain for clarity.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Quizzes
# ---------------------------------------------------------------------------

class QuestionIn(BaseModel):
    prompt: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    alt_answers: Optional[str] = None  # pipe-separated alternatives


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: Optional[str] = None
    timer_seconds: int = Field(default=30, ge=5, le=300)
    questions: List[QuestionIn] = Field(min_length=1)


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    timer_seconds: Optional[int] = Field(default=None, ge=5, le=300)
    is_active: Optional[bool] = None


class QuestionOut(BaseModel):
    id: int
    position: int
    prompt: str
    # correct_answer is NOT included in normal play – only in admin/review

    model_config = {"from_attributes": True}


class QuestionAdminOut(QuestionOut):
    correct_answer: str
    alt_answers: Optional[str]


class QuizOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    timer_seconds: int
    is_active: bool
    created_at: datetime
    question_count: int = 0

    model_config = {"from_attributes": True}


class QuizDetailOut(QuizOut):
    questions: List[QuestionOut]


class QuizAdminDetailOut(QuizOut):
    questions: List[QuestionAdminOut]


# ---------------------------------------------------------------------------
# Attempts & Answers
# ---------------------------------------------------------------------------

class SubmitAnswer(BaseModel):
    question_id: int
    submitted_text: str = Field(min_length=0, max_length=512)


class ValidationResult(BaseModel):
    question_id: int
    is_correct: bool
    confidence: float
    method: str  # "fuzzy" | "semantic" | "exact"
    correct_answer: str  # revealed after answering
    points_awarded: int


class AttemptStart(BaseModel):
    quiz_id: int


class AttemptOut(BaseModel):
    id: int
    quiz_id: int
    score: int
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AttemptDetailOut(AttemptOut):
    answers: List[AnswerOut]


class AnswerOut(BaseModel):
    id: int
    question_id: int
    submitted_text: str
    is_correct: bool
    confidence: float
    points_awarded: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

class LeaderboardRow(BaseModel):
    rank: int
    user_id: int
    username: str
    total_points: int
    quizzes_taken: int
    correct_answers: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

class FlagCreate(BaseModel):
    question_id: int
    submitted_text: str
    reason: Optional[str] = None


class FlagOut(BaseModel):
    id: int
    question_id: int
    submitted_text: str
    reason: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FlagReview(BaseModel):
    status: str = Field(pattern="^(accepted|rejected)$")
    update_correct_answer: Optional[str] = None  # optionally fix the question


# ---------------------------------------------------------------------------
# Duel
# ---------------------------------------------------------------------------

class DuelCreate(BaseModel):
    quiz_id: int


class DuelRoomOut(BaseModel):
    id: int
    quiz_id: int
    invite_code: str
    status: str
    score_a: int
    score_b: int

    model_config = {"from_attributes": True}
