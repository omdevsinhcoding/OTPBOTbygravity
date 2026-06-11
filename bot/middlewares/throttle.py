"""
Throttle middleware — basic rate limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottleMiddleware(BaseMiddleware):
    """Simple in-memory rate limiter per user."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_action: dict[int, float] = defaultdict(float)

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

        if user_id:
            now = time.monotonic()
            if now - self.last_action[user_id] < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Please slow down.", show_alert=False)
                return
            self.last_action[user_id] = now

        return await handler(event, data)
