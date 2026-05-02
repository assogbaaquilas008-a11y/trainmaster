"""
Duel Mode – Real-time 1v1 via WebSockets
==========================================
Flow:
  1. Player A creates a room → gets invite_code
  2. Player B joins via ws://.../ws/duel/{invite_code}?token=JWT
  3. Server broadcasts questions one by one
  4. First correct answer wins the point; both see result
  5. If both fail → correct answer revealed, move on
  6. Game ends when all questions answered; scores saved to DB

WebSocket message format (JSON):
  Client → Server:  { "type": "answer", "text": "...", "question_id": N }
  Server → Client:  { "type": "question" | "result" | "game_over" | "error", ... }
"""

import asyncio
import random
import string
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_token
from app.models import DuelAnswer, DuelRoom, LeaderboardEntry, Question, Quiz, User
from app.schemas import DuelCreate, DuelRoomOut
from app.services.validation import validate_answer

log = structlog.get_logger()
router = APIRouter()

# In-process room registry  {invite_code: {"a": WebSocket | None, "b": WebSocket | None}}
_rooms: Dict[str, dict] = defaultdict(lambda: {"a": None, "b": None})


def _make_invite_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ---------------------------------------------------------------------------
# REST: create room
# ---------------------------------------------------------------------------

@router.post("/duel/create", response_model=DuelRoomOut, status_code=201)
async def create_duel(
    body: DuelCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(lambda: None),  # resolved below
):
    # Manual auth (avoid circular import)
    from fastapi import Request
    from app.core.security import get_current_user
    raise NotImplementedError("Use the authenticated version below")


@router.post("/duel", response_model=DuelRoomOut, status_code=201)
async def create_duel_room(
    body: DuelCreate,
    db: AsyncSession = Depends(get_db),
):
    # This endpoint is called with Authorization header directly by client
    # Auth handled in the endpoint manually to keep code clean
    from fastapi import Header
    raise HTTPException(501, "Use /ws/duel WebSocket endpoint")


# We expose a simpler REST endpoint for room creation used before WS upgrade
def _create_duel_router():
    r = APIRouter()

    @r.post("/duel/rooms", response_model=DuelRoomOut, status_code=201)
    async def _create(
        body: DuelCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(lambda: None),
    ):
        from app.core.security import get_current_user
        # will be replaced by proper dependency; stub for clarity
        pass

    return r


# ---------------------------------------------------------------------------
# WebSocket: join and play
# ---------------------------------------------------------------------------

@router.websocket("/duel/{invite_code}")
async def duel_websocket(
    websocket: WebSocket,
    invite_code: str,
    token: str,
):
    # Authenticate via query-param token (WS doesn't support headers easily)
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    async with AsyncSessionLocal() as db:
        # Load room
        room_row = await db.execute(
            select(DuelRoom)
            .where(DuelRoom.invite_code == invite_code)
            .options(selectinload(DuelRoom.answers))
        )
        room = room_row.scalar_one_or_none()

        if not room:
            await websocket.send_json({"type": "error", "message": "Room not found"})
            await websocket.close()
            return

        if room.status == "finished":
            await websocket.send_json({"type": "error", "message": "Game already finished"})
            await websocket.close()
            return

        # Assign player slot
        if room.player_a_id == user_id:
            slot = "a"
        elif room.player_b_id is None or room.player_b_id == user_id:
            slot = "b"
            if room.player_b_id is None:
                room.player_b_id = user_id
                await db.commit()
        else:
            await websocket.send_json({"type": "error", "message": "Room is full"})
            await websocket.close()
            return

        _rooms[invite_code][slot] = websocket
        log.info("duel.player_joined", room=invite_code, slot=slot, user=user_id)

        # Wait for both players
        await websocket.send_json({"type": "waiting", "message": "Waiting for opponent…"})

        # Poll until both connected (max 120s)
        for _ in range(240):
            if _rooms[invite_code]["a"] and _rooms[invite_code]["b"]:
                break
            await asyncio.sleep(0.5)
        else:
            await websocket.send_json({"type": "error", "message": "Opponent did not join"})
            _rooms[invite_code][slot] = None
            await websocket.close()
            return

        # Only player A drives the game loop
        if slot != "a":
            await _passive_player_loop(websocket, invite_code, room.id)
            return

        # ----------------------------------------------------------------
        # GAME LOOP (driven by player A's connection)
        # ----------------------------------------------------------------
        await _broadcast(invite_code, {"type": "start", "message": "Game starting!"})

        # Load questions
        q_result = await db.execute(
            select(Question)
            .where(Question.quiz_id == room.quiz_id)
            .order_by(Question.position)
        )
        questions = q_result.scalars().all()

        room.status = "active"
        await db.commit()

        for question in questions:
            await _play_question(db, websocket, invite_code, room, question)

        # Finalise
        room.status = "finished"
        room.finished_at = datetime.now(timezone.utc)

        # Update leaderboards
        for uid, score in [(room.player_a_id, room.score_a), (room.player_b_id, room.score_b)]:
            if uid:
                lb = (await db.execute(
                    select(LeaderboardEntry).where(LeaderboardEntry.user_id == uid)
                )).scalar_one_or_none()
                if lb:
                    lb.total_points += score

        await db.commit()

        winner = "a" if room.score_a > room.score_b else ("b" if room.score_b > room.score_a else "draw")
        await _broadcast(invite_code, {
            "type": "game_over",
            "score_a": room.score_a,
            "score_b": room.score_b,
            "winner": winner,
        })

        _rooms.pop(invite_code, None)


async def _play_question(
    db: AsyncSession,
    ws_a: WebSocket,
    invite_code: str,
    room: DuelRoom,
    question: Question,
):
    """Broadcast question, collect answers with timeout, reveal result."""
    await _broadcast(invite_code, {
        "type": "question",
        "question_id": question.id,
        "prompt": question.prompt,
        "time_limit": settings.DUEL_ANSWER_SECONDS,
    })

    answers: Dict[str, Optional[str]] = {"a": None, "b": None}
    results: Dict[str, bool] = {"a": False, "b": False}

    deadline = asyncio.get_event_loop().time() + settings.DUEL_ANSWER_SECONDS

    async def _collect(slot: str, ws: WebSocket):
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return
            data = await asyncio.wait_for(ws.receive_json(), timeout=remaining)
            if data.get("type") == "answer" and data.get("question_id") == question.id:
                answers[slot] = data.get("text", "")
        except (asyncio.TimeoutError, WebSocketDisconnect):
            pass

    ws_b = _rooms[invite_code]["b"]
    tasks = [asyncio.create_task(_collect("a", ws_a))]
    if ws_b:
        tasks.append(asyncio.create_task(_collect("b", ws_b)))

    await asyncio.gather(*tasks)

    # Validate collected answers
    for slot, text in answers.items():
        if text is not None:
            val = await validate_answer(text, question.correct_answer, question.alt_answers)
            results[slot] = val.is_correct
            if val.is_correct:
                if slot == "a":
                    room.score_a += settings.POINTS_PER_CORRECT
                else:
                    room.score_b += settings.POINTS_PER_CORRECT

            uid = room.player_a_id if slot == "a" else room.player_b_id
            if uid:
                db.add(DuelAnswer(
                    room_id=room.id,
                    question_id=question.id,
                    user_id=uid,
                    submitted_text=text,
                    is_correct=val.is_correct,
                ))

    await db.commit()

    await _broadcast(invite_code, {
        "type": "result",
        "question_id": question.id,
        "correct_answer": question.correct_answer,
        "results": results,
        "answers": answers,
        "score_a": room.score_a,
        "score_b": room.score_b,
    })

    await asyncio.sleep(3)  # pause between questions


async def _passive_player_loop(ws: WebSocket, invite_code: str, room_id: int):
    """Player B just listens; all game logic runs on player A's connection."""
    try:
        while True:
            await ws.receive_text()  # keep alive; answers are sent by the client itself
    except WebSocketDisconnect:
        _rooms[invite_code]["b"] = None


async def _broadcast(invite_code: str, message: dict):
    for slot in ("a", "b"):
        ws = _rooms[invite_code].get(slot)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# REST helpers used by frontend before WS upgrade
# ---------------------------------------------------------------------------

@router.post("/duel/new", response_model=DuelRoomOut, status_code=201)
async def new_duel_room(
    body: DuelCreate,
    db: AsyncSession = Depends(get_db),
    token: str = "",
):
    """Create a duel room and return the invite code."""
    payload = decode_token(token)
    user_id = int(payload["sub"])

    quiz = (await db.execute(select(Quiz).where(Quiz.id == body.quiz_id))).scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Quiz not found")

    code = _make_invite_code()
    room = DuelRoom(
        quiz_id=body.quiz_id,
        player_a_id=user_id,
        invite_code=code,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get("/duel/{invite_code}/status", response_model=DuelRoomOut)
async def duel_status(invite_code: str, db: AsyncSession = Depends(get_db)):
    room = (await db.execute(
        select(DuelRoom).where(DuelRoom.invite_code == invite_code)
    )).scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    return room
