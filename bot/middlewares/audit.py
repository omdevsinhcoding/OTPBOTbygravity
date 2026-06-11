"""
Audit logging middleware — logs every user action.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.db.repositories.settings_repo import AuditRepo


class AuditMiddleware(BaseMiddleware):
    """Logs user interactions for analytics and audit trail."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        telegram_id = None
        action = None
        details = None

        if isinstance(event, Message) and event.from_user:
            telegram_id = event.from_user.id
            if event.text and event.text.startswith("/"):
                action = event.text.split()[0].lower()
            else:
                action = "message"
        elif isinstance(event, CallbackQuery) and event.from_user:
            telegram_id = event.from_user.id
            action = f"callback:{event.data}" if event.data else "callback"

        # Log the action (non-blocking, best-effort)
        if session and telegram_id and action:
            try:
                audit = AuditRepo(session)
                await audit.log(telegram_id, action, details)
            except Exception:
                pass  # Don't block user flow on audit failure

        return await handler(event, data)
