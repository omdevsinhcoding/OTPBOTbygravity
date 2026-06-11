"""
Bot entry point — registers all routers, middlewares, and starts polling.
"""

from __future__ import annotations

import asyncio
import logging

from bot.config import settings
from bot.db import async_session, engine
from bot.db.models import Base
from bot.db.repositories.settings_repo import AdminRepo
from bot.loader import bot, dp

# ── Import routers ──
from bot.handlers.start import router as start_router
from bot.handlers.menu import router as menu_router
from bot.handlers.registration import router as registration_router
from bot.handlers.otp import router as otp_router
from bot.handlers.reapply import router as reapply_router
from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.users import router as admin_users_router
from bot.handlers.admin.approvals import router as admin_approvals_router
from bot.handlers.admin.services import router as admin_services_router
from bot.handlers.admin.broadcast import router as admin_broadcast_router
from bot.handlers.admin.settings import router as admin_settings_router

# ── Import middlewares ──
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.auth import AdminGuardMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.middlewares.audit import AuditMiddleware
from bot.middlewares.force_join import ForceJoinMiddleware

from aiogram import Router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup():
    """Run on bot startup — create tables, bootstrap admins."""
    logger.info("🚀 Starting TPBOT...")

    # Create tables (use Alembic in production, this is a fallback)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap admins from env
    async with async_session() as session:
        admin_repo = AdminRepo(session)
        for admin_id in settings.admin_id_list:
            await admin_repo.ensure_admin(admin_id)
        await session.commit()
        logger.info(f"✅ Admin users bootstrapped: {settings.admin_id_list}")

    # Get bot username for deep link redirects
    bot_info = await bot.get_me()
    settings._bot_username = bot_info.username
    logger.info(f"🤖 Bot username: @{bot_info.username}")

    logger.info("✅ Database ready.")


async def on_shutdown():
    """Cleanup on shutdown."""
    await engine.dispose()
    logger.info("🛑 Bot stopped.")


async def main():
    """Setup and start the bot."""
    # ── Global middlewares (applied to all handlers) ──
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottleMiddleware(rate_limit=0.3))
    dp.callback_query.middleware(ThrottleMiddleware(rate_limit=0.3))
    dp.message.middleware(AuditMiddleware())
    dp.callback_query.middleware(AuditMiddleware())
    dp.message.middleware(ForceJoinMiddleware())
    dp.callback_query.middleware(ForceJoinMiddleware())

    # ── Admin router with guard ──
    admin_router = Router(name="admin")
    admin_router.message.middleware(AdminGuardMiddleware())
    admin_router.callback_query.middleware(AdminGuardMiddleware())

    admin_router.include_router(admin_panel_router)
    admin_router.include_router(admin_users_router)
    admin_router.include_router(admin_approvals_router)
    admin_router.include_router(admin_services_router)
    admin_router.include_router(admin_broadcast_router)
    admin_router.include_router(admin_settings_router)

    # ── Register all routers ──
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(registration_router)
    dp.include_router(otp_router)
    dp.include_router(reapply_router)

    # ── Lifecycle hooks ──
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Start verification server ──
    from verification_server.server import start_verification_server
    verify_runner = await start_verification_server()

    # ── Start polling ──
    logger.info("🤖 Bot is starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await verify_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
