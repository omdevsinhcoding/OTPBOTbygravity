"""
Auth middleware — admin guard check.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings


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

        if user_id and user_id not in settings.admin_id_list:
            # Silently ignore non-admin access attempts
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Admin access only.", show_alert=True)
            return

        return await handler(event, data)
