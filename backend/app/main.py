"""
TrainMaster – FastAPI application entry point.

Mounts all routers, configures CORS, starts background services,
and wires up WebSocket handlers for duel mode.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.routers import auth, quizzes, attempts, leaderboard, admin, duel, flags

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log.info("trainmaster.startup", env=settings.ENV)
    await init_db()
    yield
    log.info("trainmaster.shutdown")


app = FastAPI(
    title="TrainMaster API",
    version="1.0.0",
    description="Quiz-bowl training platform with AI answer validation.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – tighten ALLOW_ORIGINS in production via env var
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router,         prefix="/api/auth",        tags=["auth"])
app.include_router(quizzes.router,      prefix="/api/quizzes",     tags=["quizzes"])
app.include_router(attempts.router,     prefix="/api/attempts",    tags=["attempts"])
app.include_router(leaderboard.router,  prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(admin.router,        prefix="/api/admin",       tags=["admin"])
app.include_router(flags.router,        prefix="/api/flags",       tags=["flags"])
app.include_router(duel.router,         prefix="/ws",              tags=["duel"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
