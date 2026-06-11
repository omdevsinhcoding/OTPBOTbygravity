"""
Force Join middleware to require users to join specific channels.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.settings_repo import SettingsRepo
from bot.db.models import ChannelSetting

class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Only check on specific commands/buttons
        is_relevant = False
        if isinstance(event, Message) and event.text in ["🛒 Request New Service", "📋 Recent Viewed OTPs", "💎 Subscription"]:
            is_relevant = True
        elif isinstance(event, CallbackQuery) and event.data in ["menu_request_service", "menu_recent_otps", "menu_subscription"]:
            is_relevant = True
            
        if not is_relevant:
            return await handler(event, data)
            
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)
            
        settings_repo = SettingsRepo(session)
        
        # Check if force join is globally enabled
        force_join_enabled_str = await settings_repo.get("force_join_enabled")
        if force_join_enabled_str != "true":
            return await handler(event, data)
            
        # Get active channels
        channels = await settings_repo.get_all_channels()
        if not channels:
            return await handler(event, data)
            
        bot: Bot = data.get("bot")
        user_id = event.from_user.id
        
        unjoined_channels = []
        for ch in channels:
            if not ch.is_active or not ch.channel_url:
                continue
            try:
                # Assuming channel_id is properly set to a negative integer (e.g., -100...)
                member = await bot.get_chat_member(chat_id=ch.channel_id, user_id=user_id)
                if member.status in ["left", "kicked", "restricted"]:
                    unjoined_channels.append(ch)
            except Exception:
                # If bot is not admin in the channel, it will throw an exception
                pass
                
        if unjoined_channels:
            text = "⚠️ **You must join our channels to use this bot!**\n\nPlease join the channels below and try again:"
            buttons = []
            for ch in unjoined_channels:
                buttons.append([InlineKeyboardButton(text=f"{ch.emoji} {ch.channel_name or 'Join Channel'}", url=ch.channel_url)])
                
            buttons.append([InlineKeyboardButton(text="✅ I Joined", callback_data="check_join")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard, parse_mode="Markdown")
            elif isinstance(event, CallbackQuery):
                await event.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
                await event.answer()
            return None
            
        return await handler(event, data)
