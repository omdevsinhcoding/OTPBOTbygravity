"""
Handlers for the new Main Menu (both ReplyKeyboard and InlineKeyboard).
"""

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.settings_repo import SettingsRepo, AdminRepo
from bot.db.repositories.user_repo import UserRepo

router = Router(name="menu")

# We can reuse the same functions for both Message (Reply Keyboard) and CallbackQuery (Inline Keyboard)

@router.message(F.text == "🛒 Request New Service")
async def msg_request_service(message: Message, session: AsyncSession):
    await _handle_request_service(message, message.from_user.id, session)

@router.callback_query(F.data == "menu_request_service")
async def cb_request_service(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await _handle_request_service(callback.message, callback.from_user.id, session)

async def _handle_request_service(message: Message, telegram_id: int, session: AsyncSession):
    """Handle Request New Service logic."""
    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        await message.answer("User not found. Please /start the bot.")
        return

    # Check if verification is enabled in settings
    settings_repo = SettingsRepo(session)
    verification_enabled_str = await settings_repo.get("verification_enabled")
    verification_enabled = (verification_enabled_str or "true").lower() == "true"

    if verification_enabled and not user.is_verified:
        # User needs to verify
        from bot.keyboards.user_kb import request_contact_keyboard
        await message.answer(
            "⚠️ You must verify your account before requesting services.\n\n"
            "Please share your contact number to proceed:",
            reply_markup=request_contact_keyboard()
        )
        return

    # If verified (or verification disabled), show services list
    from bot.db.repositories.service_repo import ServiceRepo
    from bot.keyboards.user_kb import request_services_list_keyboard
    
    service_repo = ServiceRepo(session)
    services = list(await service_repo.get_all_active())
    
    if not services:
        await message.answer("No active services are available right now.")
        return
        
    await message.answer(
        "📦 Please select a service you want to request:",
        reply_markup=request_services_list_keyboard(services)
    )

@router.message(F.text == "📋 Recent Viewed OTPs")
async def msg_recent_otps(message: Message, session: AsyncSession):
    await _handle_recent_otps(message, message.from_user.id, session)

@router.callback_query(F.data == "menu_recent_otps")
async def cb_recent_otps(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await _handle_recent_otps(callback.message, callback.from_user.id, session)

async def _handle_recent_otps(message: Message, telegram_id: int, session: AsyncSession, page: int = 1):
    """Handle Recent Viewed OTPs logic."""
    from bot.db.repositories.otp_log_repo import OTPLogRepo
    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        await message.answer("User not found.")
        return
        
    otp_repo = OTPLogRepo(session)
    total_pages = await otp_repo.get_total_pages(user.id)
    if total_pages == 0:
        await message.answer("You haven't viewed any OTPs recently.")
        return
        
    logs = await otp_repo.get_recent_otps_paginated(user.id, page=page)
    
    text = f"📋 **Recent Viewed OTPs (Page {page}/{total_pages})**\n\n"
    for log in logs:
        time_str = log.viewed_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        text += f"📦 {log.service.display_name or log.service.name}\n"
        text += f"🔑 `{log.otp_value}`\n"
        text += f"🕒 {time_str}\n\n"
        
    # TODO: Build Pagination Keyboard
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "💎 Subscription")
async def msg_subscription(message: Message, session: AsyncSession):
    await _handle_subscription(message, message.from_user.id, session)

@router.callback_query(F.data == "menu_subscription")
async def cb_subscription(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await _handle_subscription(callback.message, callback.from_user.id, session)

async def _handle_subscription(message: Message, telegram_id: int, session: AsyncSession):
    from bot.db.repositories.service_repo import ServiceRepo
    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        return
        
    service_repo = ServiceRepo(session)
    assignments = await service_repo.get_user_assignments(user.id)
    
    if not assignments:
        await message.answer("💎 You do not have any active subscriptions.")
        return
        
    text = "💎 **Your Active Subscriptions**\n\n"
    for a in assignments:
        svc = await service_repo.get_by_id(a.service_id)
        if not svc:
            continue
        
        valid_str = "Lifetime"
        if a.valid_until:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if a.valid_until < now:
                valid_str = "❌ Expired"
            else:
                days_left = (a.valid_until - now).days
                valid_str = f"{days_left} days left (until {a.valid_until.strftime('%Y-%m-%d')})"
        
        text += f"📦 **{svc.display_name or svc.name}**\nStatus: {valid_str}\n\n"
        
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🆘 Support")
async def msg_support(message: Message, session: AsyncSession):
    await _handle_support(message, session)

@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await _handle_support(callback.message, session)

async def _handle_support(message: Message, session: AsyncSession):
    settings_repo = SettingsRepo(session)
    visible = await settings_repo.get("support_visible")
    if visible == "false":
        await message.answer("Support is currently disabled.")
        return
        
    text = await settings_repo.get("support_text") or "🆘 Contact our support team for help."
    buttons_raw = await settings_repo.get("support_buttons")
    
    import json
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = None
    if buttons_raw:
        try:
            buttons_data = json.loads(buttons_raw)
            inline_kb = [[InlineKeyboardButton(text=b["label"], url=b["url"])] for b in buttons_data]
            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)
        except Exception:
            pass
            
    await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "📢 Our Channels")
async def msg_channels(message: Message, session: AsyncSession):
    await _handle_channels(message, session)

@router.callback_query(F.data == "menu_channels")
async def cb_channels(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    await _handle_channels(callback.message, session)

async def _handle_channels(message: Message, session: AsyncSession):
    settings_repo = SettingsRepo(session)
    channels = await settings_repo.get_all_channels()
    
    if not channels:
        await message.answer("No channels available.")
        return
        
    text = "📢 **Join our official channels:**\n\n"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    inline_kb = []
    for ch in channels:
        if ch.is_active and ch.channel_url:
            inline_kb.append([InlineKeyboardButton(text=f"{ch.emoji} {ch.channel_name or 'Channel'}", url=ch.channel_url)])
            
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb) if inline_kb else None
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
