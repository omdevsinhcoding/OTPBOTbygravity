"""
Admin panel inline keyboards — premium, organized layout.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.db.models import Service, User


def admin_main_menu(verification_status: bool = True) -> InlineKeyboardMarkup:
    """Admin panel home — premium 18-button grid layout."""
    v_toggle = "🟢 Verification ON" if verification_status else "🔴 Verification OFF"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Dashboard", callback_data="admin:dashboard"),
            InlineKeyboardButton(text="👑 Admins Management", callback_data="admin:manage_admins"),
        ],
        [
            InlineKeyboardButton(text="🛍️ Pending Orders", callback_data="admin:users:pending"),
            InlineKeyboardButton(text="👥 Total Users", callback_data="admin:users:all"),
        ],
        [
            InlineKeyboardButton(text="✅ Active Users", callback_data="admin:users:approved"),
            InlineKeyboardButton(text="🎬 Services Setup", callback_data="admin:services"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Bot Settings", callback_data="admin:settings"),
            InlineKeyboardButton(text=v_toggle, callback_data="admin:toggle_verification"),
        ],
        [
            InlineKeyboardButton(text="📢 Setup Channels", callback_data="admin:channels"),
            InlineKeyboardButton(text="🆘 Setup Support", callback_data="admin:support_setup"),
        ],
        [
            InlineKeyboardButton(text="✉️ Send Mass Message", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="👋 Welcome Message", callback_data="admin:set:welcome_message"),
        ],
        [
            InlineKeyboardButton(text="📈 Analytics", callback_data="admin:analytics"),
            InlineKeyboardButton(text="🚫 Ban Message", callback_data="admin:set:ban_message"),
        ],
        [
            InlineKeyboardButton(text="✅ Approval Message", callback_data="admin:set:approval_message"),
            InlineKeyboardButton(text="❌ Decline Message", callback_data="admin:set:decline_message"),
        ],
        [
            InlineKeyboardButton(text="📜 Disclaimer", callback_data="admin:set:disclaimer"),
            InlineKeyboardButton(text="🏠 Close Panel", callback_data="main_menu"),
        ]
    ])


def admin_back_button() -> InlineKeyboardMarkup:
    """Back to admin panel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin:home")],
    ])


def user_list_keyboard(users: list, page: int = 0, filter_type: str = "all") -> InlineKeyboardMarkup:
    """Paginated user list with action buttons."""
    buttons = []
    for user in users:
        status_icon = {
            "pending": "⏳",
            "approved": "✅",
            "declined": "❌",
            "banned": "🚫",
        }.get(user.status, "❓")
        verified = "🔐" if user.is_verified else "🔓"

        name = user.full_name or user.telegram_username or str(user.telegram_id)
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {verified} {name}",
                callback_data=f"admin:user_detail:{user.id}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"admin:users:{filter_type}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}", callback_data="noop"))
    nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"admin:users:{filter_type}:{page + 1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_detail_keyboard(user: User) -> InlineKeyboardMarkup:
    """Detailed user management actions."""
    buttons = []
    if user.status == "pending":
        buttons.append([
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin:approve:{user.id}"),
            InlineKeyboardButton(text="❌ Decline", callback_data=f"admin:decline:{user.id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🎬 Assign Services", callback_data=f"admin:assign_svc:{user.id}"),
        ])
    elif user.status == "approved":
        buttons.append([
            InlineKeyboardButton(text="🎬 Modify Services", callback_data=f"admin:assign_svc:{user.id}"),
            InlineKeyboardButton(text="❌ Revoke", callback_data=f"admin:decline:{user.id}"),
        ])
    elif user.status == "declined":
        buttons.append([
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin:approve:{user.id}"),
        ])

    if user.status != "banned":
        buttons.append([
            InlineKeyboardButton(text="🚫 Ban User", callback_data=f"admin:ban:{user.id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔓 Unban User", callback_data=f"admin:unban:{user.id}"),
        ])

    buttons.append([
        InlineKeyboardButton(text="◀️ Back", callback_data="admin:users:all"),
        InlineKeyboardButton(text="🏠 Admin Home", callback_data="admin:home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_assign_keyboard(services: list[Service], assigned_ids: set[int], user_id: int) -> InlineKeyboardMarkup:
    """Service assignment picker for admin — multi-select."""
    buttons = []
    for svc in services:
        check = "✅" if svc.id in assigned_ids else "⬜"
        buttons.append([
            InlineKeyboardButton(
                text=f"{check} {svc.emoji} {svc.display_name or svc.name}",
                callback_data=f"admin:svc_toggle:{user_id}:{svc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="💾 Save & Approve", callback_data=f"admin:svc_save:{user_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Cancel", callback_data=f"admin:user_detail:{user_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def services_management_keyboard(services: list[Service]) -> InlineKeyboardMarkup:
    """Service list for admin management."""
    buttons = []
    for svc in services:
        active = "🟢" if svc.is_active else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{active} {svc.emoji} {svc.display_name or svc.name}",
                callback_data=f"admin:svc_detail:{svc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Create New Service", callback_data="admin:svc_create"),
    ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin:home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Individual service management."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Edit Name", callback_data=f"admin:svc_edit:{service_id}:name"),
            InlineKeyboardButton(text="🏷️ Edit Keywords", callback_data=f"admin:svc_edit:{service_id}:keywords"),
        ],
        [
            InlineKeyboardButton(text="📡 Edit Senders", callback_data=f"admin:svc_edit:{service_id}:senders"),
            InlineKeyboardButton(text="😀 Edit Emoji", callback_data=f"admin:svc_edit:{service_id}:emoji"),
        ],
        [
            InlineKeyboardButton(text="🔄 Toggle Active", callback_data=f"admin:svc_toggle_active:{service_id}"),
            InlineKeyboardButton(text="🗑️ Delete", callback_data=f"admin:svc_delete:{service_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Back", callback_data="admin:services")],
    ])


def broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Broadcast target selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 All Users", callback_data="bc_target:all"),
            InlineKeyboardButton(text="✅ Approved", callback_data="bc_target:approved"),
        ],
        [
            InlineKeyboardButton(text="⏳ Pending", callback_data="bc_target:pending"),
            InlineKeyboardButton(text="❌ Declined", callback_data="bc_target:declined"),
        ],
        [InlineKeyboardButton(text="◀️ Cancel", callback_data="admin:home")],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirm/cancel for destructive actions."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm:{action}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="admin:home"),
        ],
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    """Bot settings menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Welcome Message", callback_data="admin:set:welcome_message")],
        [InlineKeyboardButton(text="✅ Approval Message", callback_data="admin:set:approval_message")],
        [InlineKeyboardButton(text="❌ Decline Message", callback_data="admin:set:decline_message")],
        [InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin:home")],
    ])
