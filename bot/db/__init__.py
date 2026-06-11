"""
Database engine and async session factory.
Supports Neon PostgreSQL with proper SSL handling for asyncpg.

WHY THIS IS NEEDED:
  asyncpg.connect() does NOT accept `sslmode=require` (that's a psycopg2/libpq param).
  Instead, asyncpg expects an `ssl=<SSLContext>` in connect_args.
  
  So we:
    1. Strip sslmode/channel_binding from the URL (done in config.py)
    2. Pass ssl=SSLContext via connect_args (done here)
"""

import ssl as _ssl
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings

logger = logging.getLogger(__name__)

# ── Build connect_args for asyncpg ──
_connect_args: dict = {}

if settings.needs_ssl:
    # Create SSL context for asyncpg (this is what asyncpg actually understands)
    ssl_ctx = _ssl.create_default_context()

    # Neon uses valid certificates, but we disable hostname check
    # to avoid issues with connection pooling endpoints
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = _ssl.CERT_NONE

    # Pass ssl context — asyncpg accepts this (NOT sslmode string)
    _connect_args["ssl"] = ssl_ctx

    logger.info("🔒 SSL enabled for database connection (Neon/cloud PostgreSQL)")

# ── Create Engine ──
# The URL from settings.database_url is already cleaned:
#   - Has postgresql+asyncpg:// scheme
#   - sslmode and channel_binding are STRIPPED
#   - SSL is handled via connect_args above
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Yield a database session."""
    async with async_session() as session:
        yield session
