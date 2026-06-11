"""
Auth middleware — admin guard check.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings

from bot.db.repositories.settings_repo import AdminRepo

class AdminGuardMiddleware(BaseMiddleware):
    """
    Blocks non-admin users from admin-only handlers.
    Applied ONLY to the admin router.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if not user_id:
            return

        is_super_admin = str(user_id) == str(settings.SUPER_ADMIN_ID)
        
        session = data.get("session")
        if session:
            admin_repo = AdminRepo(session)
            db_admin = await admin_repo.get_admin(user_id)
            if db_admin or is_super_admin:
                data["admin_user"] = db_admin
                data["is_super_admin"] = is_super_admin
                return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Admin access only.", show_alert=True)
        return
