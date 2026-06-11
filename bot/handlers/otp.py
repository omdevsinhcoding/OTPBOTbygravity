"""
OTP handler — fetch and display OTPs for approved users.
Enforces 10-minute verification session check before every action.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.service_repo import ServiceRepo
from bot.db.repositories.settings_repo import AuditRepo, VerificationRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.user_kb import back_to_menu_keyboard, otp_action_keyboard, restart_keyboard
from bot.messages.otp_msgs import otp_display
from bot.messages.user_msgs import no_otp_found, session_expired_message
from bot.services.sms_parser import get_latest_matched_sms, get_otp_for_service

logger = logging.getLogger(__name__)
router = Router(name="otp")


async def _check_session(callback: CallbackQuery, session: AsyncSession, telegram_id: int) -> bool:
    """Returns True if session is valid, False if expired."""
    v_repo = VerificationRepo(session)
    latest = await v_repo.get_latest_passed(telegram_id)
    if not latest or not latest.verified_at:
        await callback.message.edit_text(session_expired_message(), reply_markup=restart_keyboard())
        await callback.answer()
        return False
    verified_at = latest.verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - verified_at) > timedelta(minutes=settings.VERIFY_SESSION_MINUTES):
        await callback.message.edit_text(session_expired_message(), reply_markup=restart_keyboard())
        await callback.answer()
        return False
    return True


@router.callback_query(F.data.startswith("get_otp:"))
async def handle_get_otp(callback: CallbackQuery, session: AsyncSession):
    """Fetch OTP for a specific service."""
    if not callback.from_user or not callback.message or not callback.data:
        return

    telegram_id = callback.from_user.id
    service_id = int(callback.data.split(":")[1])

    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    audit_repo = AuditRepo(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user or user.status != "approved":
        await callback.answer("⚠️ You don't have access.", show_alert=True)
        return

    # Check session expiry
    if not await _check_session(callback, session, telegram_id):
        return

    # Check user has this service assigned
    assigned = await service_repo.get_assigned_services(user.id)
    assigned_ids = {s.id for s in assigned}
    if service_id not in assigned_ids:
        await callback.answer("⚠️ This service is not assigned to you.", show_alert=True)
        await audit_repo.log(telegram_id, "restricted_action_attempt", {
            "action": "get_otp",
            "service_id": service_id,
        })
        return

    # Log OTP request
    await audit_repo.log(telegram_id, "request_otp", {"service_id": service_id})

    # Fetch all services for matching
    all_services = list(await service_repo.get_all_active())

    # Get OTP
    sms = await get_otp_for_service(all_services, service_id)

    if not sms:
        service = await service_repo.get_by_id(service_id)
        svc_name = service.display_name if service else "Unknown"
        await callback.message.edit_text(
            no_otp_found(svc_name),
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    msg = otp_display(
        service_name=sms.service_name or "Unknown",
        service_emoji=sms.service_emoji,
        sms_from=sms.sender,
        sms_text=sms.text,
        received_at=sms.received_stamp,
        otp_code=sms.otp_code or "",
    )

    await callback.message.edit_text(
        msg,
        reply_markup=otp_action_keyboard(sms.otp_code or "", sms.service_name or ""),
    )
    await callback.answer()


@router.callback_query(F.data == "latest_otp")
async def handle_latest_otp(callback: CallbackQuery, session: AsyncSession):
    """Fetch the latest OTP matching user's assigned services."""
    if not callback.from_user or not callback.message:
        return

    telegram_id = callback.from_user.id

    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    audit_repo = AuditRepo(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user or user.status != "approved":
        await callback.answer("⚠️ You don't have access.", show_alert=True)
        return

    # Check session expiry
    if not await _check_session(callback, session, telegram_id):
        return

    await audit_repo.log(telegram_id, "latest_otp")

    # Get assigned services
    assigned = await service_repo.get_assigned_services(user.id)
    assigned_ids = {s.id for s in assigned}
    all_services = list(await service_repo.get_all_active())

    # Fetch latest matched
    sms = await get_latest_matched_sms(all_services, assigned_ids)

    if not sms:
        await callback.message.edit_text(
            no_otp_found(),
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    msg = otp_display(
        service_name=sms.service_name or "Unknown",
        service_emoji=sms.service_emoji,
        sms_from=sms.sender,
        sms_text=sms.text,
        received_at=sms.received_stamp,
        otp_code=sms.otp_code or "",
    )

    await callback.message.edit_text(
        msg,
        reply_markup=otp_action_keyboard(sms.otp_code or "", sms.service_name or ""),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("copy_otp:"))
async def handle_copy_otp(callback: CallbackQuery, session: AsyncSession):
    """Copy OTP code — send as copiable message."""
    if not callback.from_user or not callback.data:
        return

    otp_code = callback.data.split(":", 1)[1]
    telegram_id = callback.from_user.id

    audit_repo = AuditRepo(session)
    await audit_repo.log(telegram_id, "copy_otp", {"otp": otp_code})

    await callback.answer(f"📋 OTP: {otp_code}", show_alert=True)
