"""
Configuration management using pydantic-settings.
Loads from .env file and environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram Bot ──
    BOT_TOKEN: str
    ADMIN_IDS: str = ""  # comma-separated telegram IDs

    # ── Neon PostgreSQL (full connection URL) ──
    DATABASE_URL: str = ""

    # Legacy individual fields (fallback if DATABASE_URL not set)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "tpbot"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    # ── SMS API ──
    SMS_API_BASE: str = "http://161.118.182.184:4000"

    # ── Verification ──
    VERIFY_SERVER_HOST: str = "0.0.0.0"
    VERIFY_SERVER_PORT: int = 8080
    VERIFY_SITE_URL: str = "https://your-app.netlify.app"

    # ── Google reCAPTCHA v2 ──
    RECAPTCHA_SITE_KEY: str = ""
    RECAPTCHA_SECRET_KEY: str = ""

    # ── Verification Session Duration ──
    VERIFY_SESSION_MINUTES: int = 10

    # ── Derived ──
    @property
    def admin_id_list(self) -> List[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def database_url(self) -> str:
        """Async DB URL for SQLAlchemy — prefers DATABASE_URL (Neon)."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Ensure it uses asyncpg driver
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Strip asyncpg driver for sync usage
            if "+asyncpg" in url:
                url = url.replace("+asyncpg", "")
            elif url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
