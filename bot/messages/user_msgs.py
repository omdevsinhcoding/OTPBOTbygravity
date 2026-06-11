"""
Premium, eye-catching user-facing message templates.
Uses HTML parse mode for rich formatting.
"""

from __future__ import annotations
from bot.utils.time_helpers import format_ist


def welcome_message(first_name: str) -> str:
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"    🌟 <b>Welcome to OTP Hub</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Hey <b>{first_name}</b>! 👋\n\n"
        f"Before we get started, we need to\n"
        f"verify that you're a real human.\n\n"
        f"🔐 <b>Tap the button below</b> to complete\n"
        f"a quick verification.\n\n"
        f"<i>This helps us keep the service safe\n"
        f"and fraud-free for everyone.</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def already_verified_message() -> str:
    return (
        "✅ <b>Already Verified!</b>\n\n"
        "You've already completed verification.\n"
        "Let's continue where you left off! 🚀"
    )


def verification_success() -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ✅ <b>Verification Complete!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎉 Great! You're verified as human.\n\n"
        "Now let's get you registered.\n"
        "Please provide your details below 👇\n"
    )


def verification_failed() -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ❌ <b>Verification Failed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "We couldn't verify your identity.\n\n"
        "⚠️ <b>Possible reasons:</b>\n"
        "• Location permission was denied\n"
        "• Captcha answer was incorrect\n"
        "• Session expired\n\n"
        "<i>Please try again by sending /start</i>\n"
    )


def ask_full_name() -> str:
    return (
        "📋 <b>Registration — Step 1/3</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 Please enter your <b>Full Name</b>:\n\n"
        "<i>Type your name below to continue.</i>"
    )


def ask_whatsapp() -> str:
    return (
        "📋 <b>Registration — Step 2/3</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Please enter your <b>WhatsApp number</b>:\n\n"
        "<i>Include country code (e.g., +1 234 567 8900)</i>"
    )


def ask_services() -> str:
    return (
        "📋 <b>Registration — Step 3/3</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎬 Select the <b>services</b> you need OTPs for.\n\n"
        "Tap to select, then hit <b>Submit</b> ✨\n"
    )


def registration_complete(full_name: str) -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎉 <b>Registration Submitted!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Thank you, <b>{full_name}</b>!\n\n"
        "📋 Your request has been submitted\n"
        "to our admin for review.\n\n"
        "⏳ <b>Status:</b> <code>Pending Approval</code>\n\n"
        "You'll be notified as soon as the\n"
        "admin reviews your application.\n\n"
        "<i>Sit tight — this won't take long! 🙂</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def pending_message() -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏳ <b>Pending Review</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your registration is still being\n"
        "reviewed by the admin.\n\n"
        "📋 <b>Status:</b> <code>Pending</code>\n\n"
        "<i>We'll notify you once there's an update!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def approved_message(services: list) -> str:
    svc_list = ""
    for svc in services:
        svc_list += f"    {svc.emoji} {svc.display_name or svc.name}\n"

    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎉 <b>You're Approved!</b> 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Congratulations! 🥳 The admin has\n"
        "approved your request.\n\n"
        "🎬 <b>Your Services:</b>\n"
        f"{svc_list}\n"
        "You can now access OTPs for your\n"
        "assigned services below 👇\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def declined_message(custom_msg: str = "") -> str:
    reason = custom_msg or (
        "The admin has reviewed your request\n"
        "and decided not to approve it at this time."
    )
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  😔 <b>Request Declined</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{reason}\n\n"
        "📋 <b>Status:</b> <code>Declined</code>\n\n"
        "Don't worry — you can re-apply\n"
        "by tapping the button below.\n\n"
        "<i>Make sure your details are correct\n"
        "before re-submitting.</i> 💡\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def banned_message(reason: str = "") -> str:
    extra = f"\n\n📝 <b>Reason:</b> {reason}" if reason else ""
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🚫 <b>Access Restricted</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your access to this bot has been\n"
        "restricted by the administrator.\n"
        f"{extra}\n\n"
        "<i>If you believe this is an error,\n"
        "please contact support.</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def service_menu_header() -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎬 <b>Your Services</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap a service to fetch the latest OTP,\n"
        "or hit ⚡ <b>Latest OTP</b> for the most\n"
        "recent matching message.\n"
    )


def no_otp_found(service_name: str = "") -> str:
    svc = f" for <b>{service_name}</b>" if service_name else ""
    return (
        f"😕 <b>No OTP Found</b>{svc}\n\n"
        "There are no recent OTPs matching\n"
        "your assigned services right now.\n\n"
        "<i>Try again in a moment!</i>"
    )


def session_expired_message() -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏰ <b>Session Expired</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your verification session has expired.\n\n"
        "🔐 For security, sessions are only valid\n"
        "for <b>10 minutes</b>.\n\n"
        "Please complete verification again\n"
        "to continue using the bot 👇\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

