"""
User-facing inline keyboards.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from bot.db.models import Service


# ── MAIN MENU KEYBOARDS ──

def main_menu_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """The persistent static keyboard at the bottom."""
    buttons = [
        [KeyboardButton(text="🛒 Request New Service")],
        [KeyboardButton(text="📋 Recent Viewed OTPs"), KeyboardButton(text="💎 Subscription")],
        [KeyboardButton(text="🆘 Support"), KeyboardButton(text="📢 Our Channels")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="👑 Admin Panel")])
        
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        is_persistent=True,
    )


def main_menu_inline_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """The inline keyboard sent with the welcome message."""
    buttons = [
        [InlineKeyboardButton(text="🛒 Request New Service", callback_data="menu_request_service")],
        [
            InlineKeyboardButton(text="📋 Recent Viewed OTPs", callback_data="menu_recent_otps"),
            InlineKeyboardButton(text="💎 Subscription", callback_data="menu_subscription")
        ],
        [
            InlineKeyboardButton(text="🆘 Support", callback_data="menu_support"),
            InlineKeyboardButton(text="📢 Our Channels", callback_data="menu_channels")
        ],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_home")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def request_contact_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard to request the user's phone number during verification."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_services_list_keyboard(services: list[Service]) -> InlineKeyboardMarkup:
    """Inline list of all active services for a user to request."""
    buttons = []
    for svc in services:
        buttons.append([
            InlineKeyboardButton(
                text=f"{svc.emoji} {svc.display_name or svc.name}",
                callback_data=f"req_svc:{svc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── VERIFICATION ──
def verify_link_keyboard(verify_url: str) -> InlineKeyboardMarkup:
    """Verification button as a regular URL link."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Complete Captcha", url=verify_url)],
    ])


# ── OLD KEYBOARDS (Kept for compatibility or refactoring later) ──

def approved_services_keyboard(services: list[Service]) -> InlineKeyboardMarkup:
    """Service menu for approved users — each service is a button to fetch OTP."""
    buttons = []
    for svc in services:
        buttons.append([
            InlineKeyboardButton(
                text=f"{svc.emoji} {svc.display_name or svc.name} — Get OTP",
                callback_data=f"get_otp:{svc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⚡ Latest OTP", callback_data="latest_otp"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Back to main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Back to Menu", callback_data="main_menu")],
    ])


def otp_action_keyboard(otp_text: str, service_name: str) -> InlineKeyboardMarkup:
    """OTP display actions."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📋 Copy OTP", callback_data=f"copy_otp:{otp_text}")],
        [InlineKeyboardButton(text="⚡ Latest OTP", callback_data="latest_otp")],
        [InlineKeyboardButton(text="🏠 Back to Menu", callback_data="main_menu")],
    ])

def reapply_keyboard() -> InlineKeyboardMarkup:
    """Button for declined users to reapply."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Re-apply", callback_data="restart_bot")],
    ])

def restart_keyboard() -> InlineKeyboardMarkup:
    """Button to restart the bot."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Restart", callback_data="restart_bot")],
    ])

def refresh_status_keyboard() -> InlineKeyboardMarkup:
    """Button to refresh verification status."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Status", callback_data="refresh_status")],
    ])
