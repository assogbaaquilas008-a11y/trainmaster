"""Auth endpoints: register, login, refresh, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, get_current_user, hash_password, verify_password,
)
from app.models import User
from app.schemas import TokenPair, UserLogin, UserOut, UserRegister

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")

    user = User(
        username=body.username,
        email=body.email,
        hashed_pw=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    # Initialise leaderboard entry
    from app.models import LeaderboardEntry
    db.add(LeaderboardEntry(user_id=user.id))

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_pw):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")

    return TokenPair(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return TokenPair(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user
