"""
All ORM models in one file for simplicity.
Split into separate files under app/models/ as the project grows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True)
    username:      Mapped[str]           = mapped_column(String(64), unique=True, index=True)
    email:         Mapped[str]           = mapped_column(String(256), unique=True, index=True)
    hashed_pw:     Mapped[str]           = mapped_column(String(128))
    is_active:     Mapped[bool]          = mapped_column(Boolean, default=True)
    is_admin:      Mapped[bool]          = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=now_utc)

    attempts:      Mapped[List[Attempt]] = relationship(back_populates="user",  cascade="all, delete-orphan")
    flags:         Mapped[List[Flag]]    = relationship(back_populates="user",  cascade="all, delete-orphan")
    score:         Mapped[Optional[LeaderboardEntry]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Quizzes & Questions
# ---------------------------------------------------------------------------

class Quiz(Base):
    __tablename__ = "quizzes"

    id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
    title:        Mapped[str]             = mapped_column(String(256))
    description:  Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    timer_seconds: Mapped[int]            = mapped_column(Integer, default=30)
    is_active:    Mapped[bool]            = mapped_column(Boolean, default=True)
    created_by:   Mapped[int]             = mapped_column(ForeignKey("users.id"))
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=now_utc)

    questions:    Mapped[List[Question]]  = relationship(back_populates="quiz",    cascade="all, delete-orphan", order_by="Question.position")
    attempts:     Mapped[List[Attempt]]   = relationship(back_populates="quiz",    cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id:              Mapped[int]          = mapped_column(Integer, primary_key=True)
    quiz_id:         Mapped[int]          = mapped_column(ForeignKey("quizzes.id"))
    position:        Mapped[int]          = mapped_column(Integer, default=0)
    prompt:          Mapped[str]          = mapped_column(Text)
    correct_answer:  Mapped[str]          = mapped_column(Text)
    # Pipe-separated list of acceptable alternative answers
    alt_answers:     Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    quiz:       Mapped[Quiz]              = relationship(back_populates="questions")
    answers:    Mapped[List[Answer]]      = relationship(back_populates="question", cascade="all, delete-orphan")
    flags:      Mapped[List[Flag]]        = relationship(back_populates="question", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Attempts & Answers
# ---------------------------------------------------------------------------

class Attempt(Base):
    __tablename__ = "attempts"
    # UniqueConstraint removed – multiple attempts per user per quiz are now allowed.

    id:             Mapped[int]               = mapped_column(Integer, primary_key=True)
    user_id:        Mapped[int]               = mapped_column(ForeignKey("users.id"))
    quiz_id:        Mapped[int]               = mapped_column(ForeignKey("quizzes.id"))
    attempt_number: Mapped[int]               = mapped_column(Integer, nullable=False, default=1)
    score:          Mapped[int]               = mapped_column(Integer, default=0)
    completed_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:     Mapped[datetime]          = mapped_column(DateTime(timezone=True), default=now_utc)

    user:    Mapped[User]              = relationship(back_populates="attempts")
    quiz:    Mapped[Quiz]              = relationship(back_populates="attempts")
    answers: Mapped[List[Answer]]      = relationship(back_populates="attempt", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id:               Mapped[int]           = mapped_column(Integer, primary_key=True)
    attempt_id:       Mapped[int]           = mapped_column(ForeignKey("attempts.id"))
    question_id:      Mapped[int]           = mapped_column(ForeignKey("questions.id"))
    submitted_text:   Mapped[str]           = mapped_column(Text)
    is_correct:       Mapped[bool]          = mapped_column(Boolean, default=False)
    confidence:       Mapped[float]         = mapped_column(Float, default=0.0)
    validation_method: Mapped[str]          = mapped_column(String(32), default="fuzzy")
    points_awarded:   Mapped[int]           = mapped_column(Integer, default=0)
    answered_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=now_utc)

    attempt:   Mapped[Attempt]              = relationship(back_populates="answers")
    question:  Mapped[Question]             = relationship(back_populates="answers")


# ---------------------------------------------------------------------------
# Flags (dispute system)
# ---------------------------------------------------------------------------

class Flag(Base):
    __tablename__ = "flags"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_id:        Mapped[int]           = mapped_column(ForeignKey("users.id"))
    question_id:    Mapped[int]           = mapped_column(ForeignKey("questions.id"))
    submitted_text: Mapped[str]           = mapped_column(Text)
    reason:         Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # pending | accepted | rejected
    status:         Mapped[str]           = mapped_column(String(16), default="pending")
    reviewed_by:    Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=now_utc)

    user:     Mapped[User]                = relationship(back_populates="flags", foreign_keys=[user_id])
    question: Mapped[Question]            = relationship(back_populates="flags")


# ---------------------------------------------------------------------------
# Leaderboard (materialised view – updated on attempt completion)
# ---------------------------------------------------------------------------

class LeaderboardEntry(Base):
    __tablename__ = "leaderboard"

    id:            Mapped[int]        = mapped_column(Integer, primary_key=True)
    user_id:       Mapped[int]        = mapped_column(ForeignKey("users.id"), unique=True)
    total_points:  Mapped[int]        = mapped_column(Integer, default=0)
    quizzes_taken: Mapped[int]        = mapped_column(Integer, default=0)
    correct_answers: Mapped[int]      = mapped_column(Integer, default=0)
    updated_at:    Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped[User]                = relationship(back_populates="score")


# ---------------------------------------------------------------------------
# Duel rooms
# ---------------------------------------------------------------------------

class DuelRoom(Base):
    __tablename__ = "duel_rooms"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True)
    quiz_id:       Mapped[int]           = mapped_column(ForeignKey("quizzes.id"))
    player_a_id:   Mapped[int]           = mapped_column(ForeignKey("users.id"))
    player_b_id:   Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    # waiting | active | finished
    status:        Mapped[str]           = mapped_column(String(16), default="waiting")
    score_a:       Mapped[int]           = mapped_column(Integer, default=0)
    score_b:       Mapped[int]           = mapped_column(Integer, default=0)
    invite_code:   Mapped[str]           = mapped_column(String(8), unique=True, index=True)
    created_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=now_utc)
    finished_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    answers: Mapped[List[DuelAnswer]]    = relationship(back_populates="room", cascade="all, delete-orphan")


class DuelAnswer(Base):
    __tablename__ = "duel_answers"

    id:             Mapped[int]      = mapped_column(Integer, primary_key=True)
    room_id:        Mapped[int]      = mapped_column(ForeignKey("duel_rooms.id"))
    question_id:    Mapped[int]      = mapped_column(ForeignKey("questions.id"))
    user_id:        Mapped[int]      = mapped_column(ForeignKey("users.id"))
    submitted_text: Mapped[str]      = mapped_column(Text)
    is_correct:     Mapped[bool]     = mapped_column(Boolean, default=False)
    answered_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    room: Mapped[DuelRoom]           = relationship(back_populates="answers")
