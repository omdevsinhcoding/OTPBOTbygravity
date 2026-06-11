"""
Admin panel — main menu and dashboard.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Service, User, UserServiceAssignment
from bot.db.repositories.settings_repo import SettingsRepo, AuditRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.admin_kb import admin_main_menu, admin_back_button
from bot.messages.admin_msgs import dashboard_message, analytics_message

logger = logging.getLogger(__name__)
router = Router(name="admin_panel")

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Open admin panel."""
    settings_repo = SettingsRepo(session)
    v_status_str = await settings_repo.get("verification_enabled")
    v_status = (v_status_str or "true").lower() == "true"
    
    await message.answer(
        "╔══════════════════════════════╗\n"
        "    🛡️  <b>ADMIN PANEL</b>\n"
        "╚══════════════════════════════╝\n\n"
        "Welcome, Admin! Choose an option:\n",
        reply_markup=admin_main_menu(v_status),
    )


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, session: AsyncSession):
    """Return to admin main menu."""
    if not callback.message:
        return
        
    settings_repo = SettingsRepo(session)
    v_status_str = await settings_repo.get("verification_enabled")
    v_status = (v_status_str or "true").lower() == "true"
    
    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    🛡️  <b>ADMIN PANEL</b>\n"
        "╚══════════════════════════════╝\n\n"
        "Welcome, Admin! Choose an option:\n",
        reply_markup=admin_main_menu(v_status),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:dashboard")
async def admin_dashboard(callback: CallbackQuery, session: AsyncSession):
    """Show dashboard with stats."""
    if not callback.message:
        return

    user_repo = UserRepo(session)
    audit_repo = AuditRepo(session)

    # Gather stats
    total = await user_repo.count_all()
    approved = await user_repo.count_by_status("approved")
    pending = await user_repo.count_by_status("pending")
    declined = await user_repo.count_by_status("declined")
    banned = await user_repo.count_by_status("banned")
    verified = await user_repo.count_verified()

    # Service count
    svc_result = await session.execute(
        select(func.count()).select_from(Service).where(Service.is_active == True)  # noqa: E712
    )
    services = svc_result.scalar_one()

    # Action counts
    otp_requests = await audit_repo.count_action("request_otp")
    copy_otp = await audit_repo.count_action("copy_otp")
    latest_otp = await audit_repo.count_action("latest_otp")

    stats = {
        "total": total,
        "approved": approved,
        "pending": pending,
        "declined": declined,
        "banned": banned,
        "verified": verified,
        "services": services,
        "otp_requests": otp_requests,
        "copy_otp": copy_otp,
        "latest_otp": latest_otp,
    }

    await callback.message.edit_text(
        dashboard_message(stats),
        reply_markup=admin_back_button(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:analytics")
async def admin_analytics(callback: CallbackQuery, session: AsyncSession):
    """Detailed analytics view."""
    if not callback.message:
        return

    user_repo = UserRepo(session)
    audit_repo = AuditRepo(session)

    total = await user_repo.count_all()
    approved = await user_repo.count_by_status("approved")
    pending = await user_repo.count_by_status("pending")
    declined = await user_repo.count_by_status("declined")
    banned = await user_repo.count_by_status("banned")
    verified = await user_repo.count_verified()

    svc_result = await session.execute(
        select(func.count()).select_from(Service).where(Service.is_active == True)  # noqa: E712
    )
    services_count = svc_result.scalar_one()

    assign_result = await session.execute(
        select(func.count()).select_from(UserServiceAssignment)
    )
    assignments = assign_result.scalar_one()

    stats = {
        "total": total,
        "approved": approved,
        "pending": pending,
        "declined": declined,
        "banned": banned,
        "verified": verified,
        "services": services_count,
        "assignments": assignments,
        "starts": await audit_repo.count_action("start"),
        "captcha_opened": await audit_repo.count_action("captcha_opened"),
        "captcha_passed": await audit_repo.count_action("captcha_passed"),
        "form_submitted": await audit_repo.count_action("form_submitted"),
        "otp_requests": await audit_repo.count_action("request_otp"),
        "latest_otp": await audit_repo.count_action("latest_otp"),
        "copy_otp": await audit_repo.count_action("copy_otp"),
        "reapply": await audit_repo.count_action("reapply"),
    }

    await callback.message.edit_text(
        analytics_message(stats),
        reply_markup=admin_back_button(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """No-op callback for decorative buttons."""
    await callback.answer()
