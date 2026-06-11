"""
Admin notification message templates — premium formatting.
"""

from __future__ import annotations

from bot.db.models import Service, User
from bot.utils.time_helpers import format_ist


def new_user_request(user: User, requested_services: list[Service]) -> str:
    svc_list = ""
    for svc in requested_services:
        svc_list += f"    {svc.emoji} {svc.display_name or svc.name}\n"
    if not svc_list:
        svc_list = "    None selected\n"

    verified = "✅ Yes" if user.is_verified else "❌ No"
    location = "✓ Submitted" if user.verification_location else "✗ Not provided"
    reg_time = format_ist(user.registered_at) if user.registered_at else "N/A"
    username = f"@{user.telegram_username}" if user.telegram_username else "N/A"

    return (
        "╔══════════════════════════════╗\n"
        "    🆕  <b>NEW USER REQUEST</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👤  <b>Name:</b>  {user.full_name or 'N/A'}\n"
        f"📱  <b>WhatsApp:</b>  {user.whatsapp_number or 'N/A'}\n"
        f"🆔  <b>Telegram:</b>  {username}\n"
        f"🔢  <b>User ID:</b>  <code>{user.telegram_id}</code>\n\n"
        f"📋  <b>Requested Services:</b>\n"
        f"{svc_list}\n"
        f"✅  <b>Verified:</b>  {verified}\n"
        f"📍  <b>Location:</b>  {location}\n"
        f"🕐  <b>Submitted:</b>  {reg_time}\n"
    )


def user_approved_admin(user: User, services: list[Service], admin_username: str = "") -> str:
    svc_list = ", ".join(f"{s.emoji}{s.display_name or s.name}" for s in services)
    return (
        f"✅ <b>User Approved</b>\n\n"
        f"👤 {user.full_name} (<code>{user.telegram_id}</code>)\n"
        f"🎬 Services: {svc_list}\n"
        f"👮 By: {admin_username or 'Admin'}\n"
    )


def user_declined_admin(user: User, admin_username: str = "") -> str:
    return (
        f"❌ <b>User Declined</b>\n\n"
        f"👤 {user.full_name} (<code>{user.telegram_id}</code>)\n"
        f"👮 By: {admin_username or 'Admin'}\n"
    )


def user_banned_admin(user: User, reason: str = "", admin_username: str = "") -> str:
    return (
        f"🚫 <b>User Banned</b>\n\n"
        f"👤 {user.full_name or user.telegram_id} (<code>{user.telegram_id}</code>)\n"
        f"📝 Reason: {reason or 'No reason specified'}\n"
        f"👮 By: {admin_username or 'Admin'}\n"
    )


def user_detail_card(user: User, assigned_services: list[Service], requested_services: list[Service]) -> str:
    status_icon = {
        "pending": "⏳",
        "approved": "✅",
        "declined": "❌",
        "banned": "🚫",
    }.get(user.status, "❓")

    verified = "✅ Yes" if user.is_verified else "❌ No"
    username = f"@{user.telegram_username}" if user.telegram_username else "N/A"
    reg_time = format_ist(user.registered_at) if user.registered_at else "N/A"
    approved_time = format_ist(user.approved_at) if user.approved_at else "N/A"

    req_list = ", ".join(f"{s.emoji}{s.display_name or s.name}" for s in requested_services) or "None"
    assign_list = ", ".join(f"{s.emoji}{s.display_name or s.name}" for s in assigned_services) or "None"

    return (
        "╔══════════════════════════════╗\n"
        "    👤  <b>USER DETAILS</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👤  <b>Name:</b>  {user.full_name or 'N/A'}\n"
        f"📱  <b>WhatsApp:</b>  {user.whatsapp_number or 'N/A'}\n"
        f"🆔  <b>Telegram:</b>  {username}\n"
        f"🔢  <b>ID:</b>  <code>{user.telegram_id}</code>\n\n"
        f"{status_icon}  <b>Status:</b>  <code>{user.status.upper()}</code>\n"
        f"🔐  <b>Verified:</b>  {verified}\n\n"
        f"📋  <b>Requested:</b>  {req_list}\n"
        f"🎬  <b>Assigned:</b>  {assign_list}\n\n"
        f"📅  <b>Registered:</b>  {reg_time}\n"
        f"✅  <b>Approved:</b>  {approved_time}\n"
    )


def dashboard_message(stats: dict) -> str:
    return (
        "╔══════════════════════════════╗\n"
        "    📊  <b>ADMIN DASHBOARD</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👥  <b>Total Users:</b>  {stats.get('total', 0)}\n"
        f"✅  <b>Approved:</b>  {stats.get('approved', 0)}\n"
        f"⏳  <b>Pending:</b>  {stats.get('pending', 0)}\n"
        f"❌  <b>Declined:</b>  {stats.get('declined', 0)}\n"
        f"🚫  <b>Banned:</b>  {stats.get('banned', 0)}\n"
        f"🔐  <b>Verified:</b>  {stats.get('verified', 0)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬  <b>Active Services:</b>  {stats.get('services', 0)}\n"
        f"📊  <b>OTP Requests:</b>  {stats.get('otp_requests', 0)}\n"
        f"📋  <b>Copy OTP:</b>  {stats.get('copy_otp', 0)}\n"
        f"⚡  <b>Latest OTP:</b>  {stats.get('latest_otp', 0)}\n"
    )


def analytics_message(stats: dict) -> str:
    return (
        "╔══════════════════════════════╗\n"
        "    📈  <b>ANALYTICS</b>\n"
        "╚══════════════════════════════╝\n\n"
        "<b>📊 User Statistics</b>\n"
        f"  ├ Total Users: {stats.get('total', 0)}\n"
        f"  ├ Approved: {stats.get('approved', 0)}\n"
        f"  ├ Pending: {stats.get('pending', 0)}\n"
        f"  ├ Declined: {stats.get('declined', 0)}\n"
        f"  ├ Banned: {stats.get('banned', 0)}\n"
        f"  └ Verified: {stats.get('verified', 0)}\n\n"
        "<b>🎬 Service Stats</b>\n"
        f"  ├ Active Services: {stats.get('services', 0)}\n"
        f"  └ Assignments: {stats.get('assignments', 0)}\n\n"
        "<b>📊 Action Counts</b>\n"
        f"  ├ /start: {stats.get('starts', 0)}\n"
        f"  ├ Captcha Opened: {stats.get('captcha_opened', 0)}\n"
        f"  ├ Captcha Passed: {stats.get('captcha_passed', 0)}\n"
        f"  ├ Forms Submitted: {stats.get('form_submitted', 0)}\n"
        f"  ├ OTP Requests: {stats.get('otp_requests', 0)}\n"
        f"  ├ Latest OTP: {stats.get('latest_otp', 0)}\n"
        f"  ├ Copy OTP: {stats.get('copy_otp', 0)}\n"
        f"  └ Re-apply: {stats.get('reapply', 0)}\n"
    )


def broadcast_sent_message(count: int) -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  📢 <b>Broadcast Sent!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Successfully sent to <b>{count}</b> users.\n"
    )
