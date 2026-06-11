"""
User-facing inline keyboards.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from bot.db.models import Service


def verify_keyboard(verify_url: str) -> InlineKeyboardMarkup:
    """Verification button that opens the captcha page."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Verify Now", web_app=WebAppInfo(url=verify_url))],
    ])


def verify_link_keyboard(verify_url: str) -> InlineKeyboardMarkup:
    """Verification button as a regular URL link."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Verify Now", url=verify_url)],
    ])


def service_selection_keyboard(services: list[Service], selected_ids: set[int] | None = None) -> InlineKeyboardMarkup:
    """Multi-select service picker for registration."""
    selected = selected_ids or set()
    buttons = []
    for svc in services:
        check = "✅" if svc.id in selected else "⬜"
        buttons.append([
            InlineKeyboardButton(
                text=f"{check} {svc.emoji} {svc.display_name or svc.name}",
                callback_data=f"svc_toggle:{svc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="✨ Submit Selection", callback_data="svc_submit"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def reapply_keyboard() -> InlineKeyboardMarkup:
    """Re-apply button for declined users."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Re-Apply", callback_data="reapply")],
    ])


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
