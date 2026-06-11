"""
Database engine and async session factory.
Supports Neon PostgreSQL (SSL required).
"""

import ssl as _ssl

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import settings

# Neon requires SSL — build SSL context
_connect_args = {}
if "neon.tech" in settings.database_url or "ssl=require" in settings.database_url:
    ssl_ctx = _ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = _ssl.CERT_NONE
    _connect_args["ssl"] = ssl_ctx

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
