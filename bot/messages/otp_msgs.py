"""
OTP display message templates.
"""

from __future__ import annotations

from bot.utils.time_helpers import format_ist_from_timestamp


def otp_display(service_name: str, service_emoji: str, sms_from: str, sms_text: str,
                received_at: str | int, otp_code: str = "") -> str:
    time_str = format_ist_from_timestamp(received_at) if isinstance(received_at, (int, float)) else received_at

    otp_line = f"\n🔑  <b>OTP Code:</b>  <code>{otp_code}</code>" if otp_code else ""

    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {service_emoji} <b>{service_name} OTP</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📨  <b>From:</b>  <code>{sms_from}</code>\n"
        f"💬  <b>Message:</b>\n"
        f"<i>{sms_text}</i>\n"
        f"{otp_line}\n\n"
        f"🕐  <b>Received:</b>  {time_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
