"""
Admin user management — list, view, filter users.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.service_repo import ServiceRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.admin_kb import user_detail_keyboard, user_list_keyboard
from bot.messages.admin_msgs import user_detail_card

logger = logging.getLogger(__name__)
router = Router(name="admin_users")

PAGE_SIZE = 10


@router.callback_query(F.data == "admin:manage_admins")
async def manage_admins(callback: CallbackQuery, session: AsyncSession):
    """Show list of admins and allow managing them."""
    if not callback.message:
        return
        
    from bot.db.repositories.settings_repo import AdminRepo
    admin_repo = AdminRepo(session)
    admins = await admin_repo.get_all_admins()
    
    text = "👑 **Admins Management**\n\n"
    text += f"Super Admin: `{settings.SUPER_ADMIN_ID}`\n\n"
    
    if admins:
        text += "**Database Admins:**\n"
        for a in admins:
            text += f"• `{a.telegram_id}`\n"
    else:
        text += "No additional admins configured in DB.\n"
        
    text += "\nTo add or remove an admin, use the commands:\n"
    text += "`/add_admin <id>`\n`/remove_admin <id>`"
    
    from bot.keyboards.admin_kb import admin_back_button
    await callback.message.edit_text(text, reply_markup=admin_back_button(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:users:(all|verified|pending|declined|banned|approved)(?::(\d+))?$"))
async def list_users(callback: CallbackQuery, session: AsyncSession):
    """List users filtered by status, with pagination."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    filter_type = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_repo = UserRepo(session)
    offset = page * PAGE_SIZE

    if filter_type == "all":
        users = await user_repo.get_all_users(limit=PAGE_SIZE, offset=offset)
        title = "👥 ALL USERS"
    elif filter_type == "verified":
        users = await user_repo.get_verified_users(limit=PAGE_SIZE, offset=offset)
        title = "🔐 VERIFIED USERS"
    elif filter_type == "pending":
        users = await user_repo.get_users_by_status("pending", limit=PAGE_SIZE, offset=offset)
        title = "⏳ PENDING ORDERS (USERS)"
    elif filter_type == "declined":
        users = await user_repo.get_users_by_status("declined", limit=PAGE_SIZE, offset=offset)
        title = "❌ DECLINED USERS"
    elif filter_type == "banned":
        users = await user_repo.get_users_by_status("banned", limit=PAGE_SIZE, offset=offset)
        title = "🚫 BANNED USERS"
    elif filter_type == "approved":
        users = await user_repo.get_users_by_status("approved", limit=PAGE_SIZE, offset=offset)
        title = "✅ ACTIVE USERS"
    else:
        users = []
        title = "USERS"

    users_list = list(users)

    if not users_list and page == 0:
        await callback.message.edit_text(
            f"╔══════════════════════════════╗\n"
            f"    {title}\n"
            f"╚══════════════════════════════╝\n\n"
            f"No users found in this category.\n",
            reply_markup=user_list_keyboard([], page, filter_type),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"╔══════════════════════════════╗\n"
        f"    {title}\n"
        f"╚══════════════════════════════╝\n\n"
        f"Tap a user to view details:\n",
        reply_markup=user_list_keyboard(users_list, page, filter_type),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user_detail:(\d+)$"))
async def user_detail(callback: CallbackQuery, session: AsyncSession):
    """Show detailed user information with action buttons."""
    if not callback.message or not callback.data:
        return

    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)

    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("⚠️ User not found.", show_alert=True)
        return

    # Get services
    assigned = list(await service_repo.get_assigned_services(user.id))
    requests = await service_repo.get_user_requests(user.id)
    all_services = {s.id: s for s in await service_repo.get_all()}
    requested = [all_services[r.service_id] for r in requests if r.service_id in all_services]

    msg = user_detail_card(user, assigned, requested)

    await callback.message.edit_text(
        msg,
        reply_markup=user_detail_keyboard(user),
    )
    await callback.answer()
