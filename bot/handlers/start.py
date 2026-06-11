"""
/start handler — entry point, verification gate, and routing.
Supports 10-minute reCAPTCHA session expiry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.settings_repo import AuditRepo, BanRepo, SettingsRepo, VerificationRepo
from bot.db.repositories.user_repo import UserRepo
from bot.db.repositories.service_repo import ServiceRepo
from bot.keyboards.user_kb import (
    approved_services_keyboard,
    reapply_keyboard,
    verify_link_keyboard,
    refresh_status_keyboard,
    restart_keyboard,
)
from bot.messages.user_msgs import (
    already_verified_message,
    approved_message,
    ask_full_name,
    banned_message,
    declined_message,
    pending_message,
    service_menu_header,
    welcome_message,
    verification_success,
    session_expired_message,
    verification_failed,
)
from bot.services.verification import generate_verification_token
from bot.states.registration import RegistrationStates

logger = logging.getLogger(__name__)
router = Router(name="start")


def _is_session_expired(verified_at: datetime | None) -> bool:
    """Check if the verification session has expired (10 min default)."""
    if not verified_at:
        return True
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    expiry = timedelta(minutes=settings.VERIFY_SESSION_MINUTES)
    return (now - verified_at) > expiry


async def _send_verification(message: Message, session: AsyncSession, telegram_id: int, first_name: str):
    """Generate and send verification link."""
    verification_repo = VerificationRepo(session)
    audit_repo = AuditRepo(session)

    token = generate_verification_token()

    # Create session with placeholder captcha_answer (reCAPTCHA handles this now)
    await verification_repo.create_session(telegram_id, token, "recaptcha")
    await audit_repo.log(telegram_id, "captcha_opened")

    verify_url = f"{settings.VERIFY_SITE_URL}?token={token}"

    await message.answer(
        welcome_message(first_name),
        reply_markup=verify_link_keyboard(verify_url),
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, session: AsyncSession, state: FSMContext):
    """Handle /start with deep link (e.g., /start verified from auto-redirect)."""
    if not message.from_user:
        return
        
    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "there"
    
    await _process_start(message, telegram_id, username, first_name, session, state)


async def _process_start(message: Message, telegram_id: int, username: str | None, first_name: str, session: AsyncSession, state: FSMContext):
    """Core logic for starting the bot, reusable by commands and callbacks."""
    # Clear any active FSM state
    await state.clear()

    user_repo = UserRepo(session)
    ban_repo = BanRepo(session)
    audit_repo = AuditRepo(session)

    # Log /start action
    await audit_repo.log(telegram_id, "start")

    # ── Check ban ──
    if await ban_repo.is_banned(telegram_id):
        settings_repo = SettingsRepo(session)
        ban_msg = await settings_repo.get("ban_message") or ""
        await message.answer(banned_message(ban_msg))
        return

    # ── Get or create user ──
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        user = await user_repo.create(telegram_id, username)

    # Update username if changed
    if user.telegram_username != username:
        user.telegram_username = username

    # ── Check if User Needs to Register FIRST ──
    if not user.registered_at:
        # For new users, we ask for their details BEFORE verification
        await message.answer(ask_full_name())
        await state.set_state(RegistrationStates.waiting_full_name)
        return

    # ── Check verification (including 10-min session expiry) ──
    if not user.is_verified:
        await _send_verification(message, session, telegram_id, first_name)
        return

    # Check if verification session expired (10 minutes)
    verification_repo = VerificationRepo(session)
    latest_session = await verification_repo.get_latest_passed(telegram_id)

    if _is_session_expired(latest_session.verified_at if latest_session else None):
        # Session expired — just send the verification link automatically (Fixes the loop)
        await message.answer(session_expired_message())
        await _send_verification(message, session, telegram_id, first_name)
        return

    # ── Verified user — route by status ──

    if user.status == "pending":
        await message.answer(
            pending_message(),
            reply_markup=refresh_status_keyboard(),
        )
        return

    if user.status == "declined":
        settings_repo = SettingsRepo(session)
        decline_msg = await settings_repo.get("decline_message") or ""
        await message.answer(
            declined_message(decline_msg),
            reply_markup=reapply_keyboard(),
        )
        return

    if user.status == "banned":
        settings_repo = SettingsRepo(session)
        ban_msg = await settings_repo.get("ban_message") or ""
        await message.answer(banned_message(ban_msg))
        return

    if user.status == "approved":
        # Show service menu
        service_repo = ServiceRepo(session)
        assigned = await service_repo.get_assigned_services(user.id)
        assigned_list = list(assigned)

        if not assigned_list:
            await message.answer(
                "✅ You're approved but no services are assigned yet.\n"
                "Please wait for the admin to assign services."
            )
            return

        await message.answer(
            service_menu_header(),
            reply_markup=approved_services_keyboard(assigned_list),
        )
        return


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Main entry point — verification gate → routing."""
    if not message.from_user:
        return

    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "there"

    await _process_start(message, telegram_id, username, first_name, session, state)


@router.callback_query(F.data == "restart_bot")
async def callback_restart_bot(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Restart bot from an inline button."""
    if not callback.message or not callback.from_user:
        return
        
    await callback.message.delete()
    
    telegram_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name or "there"
    
    # Process start using the callback's message context so it sends a new message to the chat
    await _process_start(callback.message, telegram_id, username, first_name, session, state)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, session: AsyncSession):
    """Return to main service menu."""
    if not callback.from_user or not callback.message:
        return

    telegram_id = callback.from_user.id
    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user or user.status != "approved":
        await callback.answer("⚠️ You don't have access.", show_alert=True)
        return

    # Check session expiry
    verification_repo = VerificationRepo(session)
    latest_session = await verification_repo.get_latest_passed(telegram_id)
    if _is_session_expired(latest_session.verified_at if latest_session else None):
        await callback.message.edit_text(session_expired_message(), reply_markup=restart_keyboard())
        await callback.answer()
        return

    assigned = await service_repo.get_assigned_services(user.id)
    assigned_list = list(assigned)

    await callback.message.edit_text(
        service_menu_header(),
        reply_markup=approved_services_keyboard(assigned_list),
    )
    await callback.answer()


@router.callback_query(F.data == "refresh_menu")
async def callback_refresh_menu(callback: CallbackQuery, session: AsyncSession):
    """Refresh the service menu."""
    if not callback.from_user or not callback.message:
        return

    telegram_id = callback.from_user.id
    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user or user.status != "approved":
        await callback.answer("⚠️ You don't have access.", show_alert=True)
        return

    assigned = await service_repo.get_assigned_services(user.id)
    assigned_list = list(assigned)

    await callback.message.edit_text(
        service_menu_header(),
        reply_markup=approved_services_keyboard(assigned_list),
    )
    await callback.answer("✅ Refreshed!")


@router.callback_query(F.data == "refresh_status")
async def callback_refresh_status(callback: CallbackQuery, session: AsyncSession):
    """Check approval status without retyping /start."""
    if not callback.from_user or not callback.message:
        return

    telegram_id = callback.from_user.id
    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        await callback.message.edit_text(verification_failed(), reply_markup=restart_keyboard())
        await callback.answer()
        return

    # Check session expiry
    verification_repo = VerificationRepo(session)
    latest_session = await verification_repo.get_latest_passed(telegram_id)
    if _is_session_expired(latest_session.verified_at if latest_session else None):
        await callback.message.edit_text(session_expired_message(), reply_markup=restart_keyboard())
        await callback.answer()
        return

    if user.status == "pending":
        await callback.answer("⏳ Still pending. Please wait for admin approval.")
        return

    if user.status == "approved":
        service_repo = ServiceRepo(session)
        assigned = await service_repo.get_assigned_services(user.id)
        assigned_list = list(assigned)

        if not assigned_list:
            await callback.message.edit_text(
                "✅ You're approved but no services are assigned yet.\n"
                "Please wait for the admin to assign services."
            )
            return

        await callback.message.edit_text(
            service_menu_header(),
            reply_markup=approved_services_keyboard(assigned_list),
        )
        await callback.answer("🎉 Approved! Menu loaded.")
        return

    if user.status == "declined":
        settings_repo = SettingsRepo(session)
        decline_msg = await settings_repo.get("decline_message") or ""
        await callback.message.edit_text(
            declined_message(decline_msg),
            reply_markup=reapply_keyboard(),
        )
        await callback.answer("❌ Request declined.")
        return

    if user.status == "banned":
        settings_repo = SettingsRepo(session)
        ban_msg = await settings_repo.get("ban_message") or ""
        await callback.message.edit_text(banned_message(ban_msg))
        await callback.answer("🚫 Account banned.")
        return
