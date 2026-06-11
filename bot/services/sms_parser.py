"""
SMS fetching and service-matching engine.
Fetches SMS from the external API and classifies them by service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import httpx

from bot.config import settings
from bot.db.models import Service


@dataclass
class ParsedSMS:
    """A single parsed SMS with service classification."""
    sender: str
    text: str
    sim: str
    sent_stamp: int
    received_stamp: int
    received_at: str
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    service_emoji: str = "📦"
    otp_code: Optional[str] = None


# Common OTP regex patterns
OTP_PATTERNS = [
    re.compile(r"(?:code|otp|pin|verification)\s*(?:is|:)?\s*(\d{4,8})", re.IGNORECASE),
    re.compile(r"\b(\d{4,8})\b.*(?:code|otp|pin|verify)", re.IGNORECASE),
    re.compile(r"(?:use|enter|type)\s+(?:code\s+)?(\d{4,8})", re.IGNORECASE),
    re.compile(r"\b(\d{4,8})\b"),  # fallback — any 4-8 digit number
]


def extract_otp(text: str) -> Optional[str]:
    """Extract OTP code from SMS text using pattern matching."""
    for pattern in OTP_PATTERNS[:-1]:  # Try specific patterns first
        match = pattern.search(text)
        if match:
            return match.group(1)
    # Fallback: look for standalone digit groups (skip phone numbers)
    digits = re.findall(r"\b(\d{4,8})\b", text)
    for d in digits:
        # Skip if it looks like a phone number or amount
        if len(d) >= 4 and not text.lower().count("rs."):
            return d
    return None


def classify_sms(sms_data: dict, services: list[Service]) -> ParsedSMS:
    """Classify a single SMS against known services."""
    parsed = ParsedSMS(
        sender=sms_data.get("from", ""),
        text=sms_data.get("text", ""),
        sim=sms_data.get("sim", ""),
        sent_stamp=sms_data.get("sentStamp", 0),
        received_stamp=sms_data.get("receivedStamp", 0),
        received_at=sms_data.get("receivedAt", ""),
    )

    sender_lower = parsed.sender.lower()
    text_lower = parsed.text.lower()

    for svc in services:
        matched = False

        # Check sender patterns
        if svc.sender_patterns:
            for pattern in svc.sender_patterns:
                if pattern.lower() in sender_lower:
                    matched = True
                    break

        # Check keywords in text
        if not matched and svc.keywords:
            for keyword in svc.keywords:
                if keyword.lower() in text_lower:
                    matched = True
                    break

        if matched:
            parsed.service_id = svc.id
            parsed.service_name = svc.display_name or svc.name
            parsed.service_emoji = svc.emoji
            parsed.otp_code = extract_otp(parsed.text)
            break

    return parsed


async def fetch_all_sms() -> list[dict]:
    """Fetch all SMS from the API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.SMS_API_BASE}/sms/")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
    except Exception:
        return []


async def fetch_latest_sms() -> Optional[dict]:
    """Fetch the latest SMS from the API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.SMS_API_BASE}/sms/latest")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data")
    except Exception:
        return None


async def get_matched_sms_for_user(services: list[Service], user_service_ids: set[int]) -> list[ParsedSMS]:
    """Fetch all SMS and return only those matching user's assigned services."""
    all_sms = await fetch_all_sms()
    results = []
    for sms_data in all_sms:
        parsed = classify_sms(sms_data, services)
        if parsed.service_id and parsed.service_id in user_service_ids:
            results.append(parsed)
    return results


async def get_latest_matched_sms(services: list[Service], user_service_ids: set[int]) -> Optional[ParsedSMS]:
    """Fetch all SMS and return the most recent one that matches user's assigned services."""
    all_sms = await fetch_all_sms()
    for sms_data in all_sms:
        parsed = classify_sms(sms_data, services)
        if parsed.service_id and parsed.service_id in user_service_ids and parsed.otp_code:
            return parsed
    return None


async def get_otp_for_service(services: list[Service], target_service_id: int) -> Optional[ParsedSMS]:
    """Get the latest OTP for a specific service."""
    all_sms = await fetch_all_sms()
    for sms_data in all_sms:
        parsed = classify_sms(sms_data, services)
        if parsed.service_id == target_service_id and parsed.otp_code:
            return parsed
    return None
