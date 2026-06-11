"""
Admin approval handler — approve, decline, ban, assign services.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.service_repo import ServiceRepo
from bot.db.repositories.settings_repo import ApprovalRepo, AuditRepo, BanRepo, SettingsRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.admin_kb import (
    admin_back_button,
    service_assign_keyboard,
    user_detail_keyboard,
)
from bot.keyboards.user_kb import approved_services_keyboard, reapply_keyboard
from bot.loader import bot
from bot.messages.admin_msgs import user_approved_admin, user_banned_admin, user_declined_admin
from bot.messages.user_msgs import approved_message, banned_message, declined_message, service_menu_header

logger = logging.getLogger(__name__)
router = Router(name="admin_approvals")

# In-memory temp storage for service assignment toggles
_assign_selections: dict[str, set[int]] = {}


@router.callback_query(F.data.regexp(r"^admin:approve:(\d+)$"))
async def approve_user(callback: CallbackQuery, session: AsyncSession):
    """Approve a user — prompt for service assignment first."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    # Get all services and user's requested services
    all_services = list(await service_repo.get_all_active())
    requests = await service_repo.get_user_requests(user.id)
    requested_ids = {r.service_id for r in requests}

    # Pre-select requested services
    key = f"{callback.from_user.id}:{user_id}"
    _assign_selections[key] = requested_ids.copy()

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    🎬  <b>ASSIGN SERVICES</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👤 User: <b>{user.full_name or user.telegram_id}</b>\n\n"
        "Select which services to assign.\n"
        "Pre-selected = user's requests.\n"
        "You can modify before saving.\n",
        reply_markup=service_assign_keyboard(all_services, requested_ids, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:assign_svc:(\d+)$"))
async def assign_services_start(callback: CallbackQuery, session: AsyncSession):
    """Open service assignment picker."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    all_services = list(await service_repo.get_all_active())

    # Get currently assigned
    assigned = await service_repo.get_assigned_services(user.id)
    assigned_ids = {s.id for s in assigned}

    # If no assignments, pre-select requests
    if not assigned_ids:
        requests = await service_repo.get_user_requests(user.id)
        assigned_ids = {r.service_id for r in requests}

    key = f"{callback.from_user.id}:{user_id}"
    _assign_selections[key] = assigned_ids.copy()

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    🎬  <b>ASSIGN SERVICES</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👤 User: <b>{user.full_name or user.telegram_id}</b>\n\n"
        "Select services to assign:\n",
        reply_markup=service_assign_keyboard(all_services, assigned_ids, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:svc_toggle:(\d+):(\d+)$"))
async def toggle_service_assignment(callback: CallbackQuery, session: AsyncSession):
    """Toggle a service in the assignment picker."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    parts = callback.data.split(":")
    user_id = int(parts[2])
    service_id = int(parts[3])

    key = f"{callback.from_user.id}:{user_id}"
    selected = _assign_selections.get(key, set())

    if service_id in selected:
        selected.discard(service_id)
    else:
        selected.add(service_id)

    _assign_selections[key] = selected

    service_repo = ServiceRepo(session)
    all_services = list(await service_repo.get_all_active())

    await callback.message.edit_reply_markup(
        reply_markup=service_assign_keyboard(all_services, selected, user_id),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:svc_save:(\d+)$"))
async def save_service_assignment(callback: CallbackQuery, session: AsyncSession):
    """Save service assignments and approve user."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    admin_id = callback.from_user.id
    admin_username = callback.from_user.username or str(admin_id)

    key = f"{admin_id}:{user_id}"
    selected = _assign_selections.pop(key, set())

    if not selected:
        await callback.answer("⚠️ Please select at least one service.", show_alert=True)
        return

    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    approval_repo = ApprovalRepo(session)
    audit_repo = AuditRepo(session)
    settings_repo = SettingsRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    # Assign services
    await service_repo.assign_services(user.id, list(selected), admin_id)

    # Update status to approved
    await user_repo.set_status(user.id, "approved")

    # Log approval
    await approval_repo.log_action(user.id, admin_id, "approved", f"Services: {list(selected)}")
    await audit_repo.log(admin_id, "admin_approve", {"user_id": user.id, "services": list(selected)})

    # Get assigned service objects
    assigned = list(await service_repo.get_assigned_services(user.id))

    # ── Notify user ──
    try:
        await bot.send_message(
            user.telegram_id,
            approved_message(assigned),
            reply_markup=approved_services_keyboard(assigned),
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user.telegram_id}: {e}")

    # ── Post to channel ──
    channel = await settings_repo.get_active_channel()
    if channel:
        try:
            await bot.send_message(
                channel.channel_id,
                user_approved_admin(user, assigned, admin_username),
            )
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")

    await callback.message.edit_text(
        f"✅ <b>User Approved!</b>\n\n"
        f"👤 {user.full_name} has been approved\n"
        f"🎬 Services: {', '.join(s.emoji + (s.display_name or s.name) for s in assigned)}\n",
        reply_markup=admin_back_button(),
    )
    await callback.answer("✅ User approved!")


@router.callback_query(F.data.regexp(r"^admin:decline:(\d+)$"))
async def decline_user(callback: CallbackQuery, session: AsyncSession):
    """Decline a user."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    admin_id = callback.from_user.id
    admin_username = callback.from_user.username or str(admin_id)

    user_repo = UserRepo(session)
    approval_repo = ApprovalRepo(session)
    audit_repo = AuditRepo(session)
    settings_repo = SettingsRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    # Update status
    await user_repo.set_status(user.id, "declined")
    await approval_repo.log_action(user.id, admin_id, "declined")
    await audit_repo.log(admin_id, "admin_decline", {"user_id": user.id})

    # Notify user
    decline_msg = await settings_repo.get("decline_message") or ""
    try:
        await bot.send_message(
            user.telegram_id,
            declined_message(decline_msg),
            reply_markup=reapply_keyboard(),
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

    # Post to channel
    channel = await settings_repo.get_active_channel()
    if channel:
        try:
            await bot.send_message(
                channel.channel_id,
                user_declined_admin(user, admin_username),
            )
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")

    await callback.message.edit_text(
        f"❌ <b>User Declined</b>\n\n"
        f"👤 {user.full_name or user.telegram_id}\n"
        f"Re-apply button sent to user.\n",
        reply_markup=admin_back_button(),
    )
    await callback.answer("❌ User declined.")


@router.callback_query(F.data.regexp(r"^admin:ban:(\d+)$"))
async def ban_user(callback: CallbackQuery, session: AsyncSession):
    """Ban a user."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    admin_id = callback.from_user.id
    admin_username = callback.from_user.username or str(admin_id)

    user_repo = UserRepo(session)
    ban_repo = BanRepo(session)
    approval_repo = ApprovalRepo(session)
    audit_repo = AuditRepo(session)
    settings_repo = SettingsRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    # Ban
    await user_repo.set_status(user.id, "banned")
    await user_repo.set_blocked(user.telegram_id, True)
    await ban_repo.ban(user.telegram_id, reason="Banned by admin", banned_by=admin_id)
    await approval_repo.log_action(user.id, admin_id, "banned")
    await audit_repo.log(admin_id, "admin_ban", {"user_id": user.id})

    # Notify user
    ban_msg = await settings_repo.get("ban_message") or ""
    try:
        await bot.send_message(user.telegram_id, banned_message(ban_msg))
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

    # Post to channel
    channel = await settings_repo.get_active_channel()
    if channel:
        try:
            await bot.send_message(
                channel.channel_id,
                user_banned_admin(user, "Banned by admin", admin_username),
            )
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")

    await callback.message.edit_text(
        f"🚫 <b>User Banned</b>\n\n"
        f"👤 {user.full_name or user.telegram_id}\n",
        reply_markup=admin_back_button(),
    )
    await callback.answer("🚫 User banned.")


@router.callback_query(F.data.regexp(r"^admin:unban:(\d+)$"))
async def unban_user(callback: CallbackQuery, session: AsyncSession):
    """Unban a user."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    user_id = int(callback.data.split(":")[2])
    admin_id = callback.from_user.id

    user_repo = UserRepo(session)
    ban_repo = BanRepo(session)
    approval_repo = ApprovalRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    await user_repo.set_status(user.id, "declined")
    await user_repo.set_blocked(user.telegram_id, False)
    await ban_repo.unban(user.telegram_id)
    await approval_repo.log_action(user.id, admin_id, "unbanned")

    await callback.message.edit_text(
        f"🔓 <b>User Unbanned</b>\n\n"
        f"👤 {user.full_name or user.telegram_id}\n"
        f"Status set to <code>declined</code>. You can now approve them.\n",
        reply_markup=admin_back_button(),
    )
    await callback.answer("🔓 User unbanned.")
