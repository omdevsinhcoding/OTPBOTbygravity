"""
Configuration management using pydantic-settings.
Loads from .env file and environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
        """
        Async DB URL for SQLAlchemy + asyncpg.
        
        CRITICAL: asyncpg does NOT understand libpq params like
        sslmode, channel_binding, etc. We MUST strip them from the URL.
        SSL is handled separately via connect_args in db/__init__.py.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL

            # Ensure asyncpg driver
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)

            # Strip params that asyncpg doesn't understand
            url = self._strip_libpq_params(url)
            return url

        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations (keeps sslmode for psycopg2)."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Ensure plain postgresql:// for sync driver
            if "+asyncpg" in url:
                url = url.replace("+asyncpg", "")
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            # Keep sslmode here — psycopg2 DOES understand it
            return url
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def is_neon(self) -> bool:
        """Check if using Neon PostgreSQL (needs SSL)."""
        return "neon.tech" in self.DATABASE_URL.lower() if self.DATABASE_URL else False

    @property
    def needs_ssl(self) -> bool:
        """Check if the connection URL specifies SSL."""
        if not self.DATABASE_URL:
            return False
        return (
            "sslmode=require" in self.DATABASE_URL.lower()
            or "ssl=require" in self.DATABASE_URL.lower()
            or "neon.tech" in self.DATABASE_URL.lower()
        )

    @staticmethod
    def _strip_libpq_params(url: str) -> str:
        """
        Remove libpq-specific query params that asyncpg doesn't understand.
        
        asyncpg crashes on: sslmode, channel_binding, sslcert, sslkey, sslrootcert
        These are psycopg2/libpq params, NOT asyncpg params.
        """
        # Params that asyncpg does NOT accept
        LIBPQ_ONLY_PARAMS = {
            "sslmode", "channel_binding", "sslcert", "sslkey",
            "sslrootcert", "sslcrl", "sslpassword", "gsslib",
            "krbsrvname", "target_session_attrs",
        }

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove libpq-only params
        cleaned = {
            k: v for k, v in query_params.items()
            if k.lower() not in LIBPQ_ONLY_PARAMS
        }

        # Rebuild URL
        new_query = urlencode(cleaned, doseq=True)
        cleaned_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))

        return cleaned_url


settings = Settings()
