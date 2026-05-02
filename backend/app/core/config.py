"""
Central configuration – reads from environment variables / .env file.
All secrets are injected via env; never hardcoded.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_SECRETS_MANAGER"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./trainmaster.db"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Email (SMTP – use SendGrid/Mailgun free tier or Gmail SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@trainmaster.app"

    # AI Validation
    # Options: "local" (sentence-transformers, no API key needed)
    #          "huggingface" (HuggingFace Inference API – free tier)
    VALIDATION_BACKEND: str = "local"
    HUGGINGFACE_API_KEY: str = ""

    # Fuzzy matching threshold (0-100). Answers scoring >= this are accepted.
    FUZZY_THRESHOLD: int = 80
    # Semantic similarity threshold (0-1). Answers scoring >= this are accepted.
    SEMANTIC_THRESHOLD: float = 0.75

    # Scoring
    POINTS_PER_CORRECT: int = 10

    # Duel defaults
    DUEL_ANSWER_SECONDS: int = 15


settings = Settings()
