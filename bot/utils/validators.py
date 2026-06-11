"""
Input validators for registration form.
"""

from __future__ import annotations

import re


def validate_full_name(name: str) -> tuple[bool, str]:
    """Validate full name — 2-100 chars, letters and spaces only."""
    name = name.strip()
    if len(name) < 2:
        return False, "Name is too short. Please enter at least 2 characters."
    if len(name) > 100:
        return False, "Name is too long. Please keep it under 100 characters."
    if not re.match(r"^[a-zA-Z\s\.\'\-]+$", name):
        return False, "Name should contain only letters, spaces, dots, hyphens, and apostrophes."
    return True, name


def validate_whatsapp(number: str) -> tuple[bool, str]:
    """Validate WhatsApp number — allow digits, +, spaces, dashes."""
    number = number.strip()
    cleaned = re.sub(r"[\s\-\(\)]", "", number)
    if not re.match(r"^\+?\d{10,15}$", cleaned):
        return False, (
            "Invalid WhatsApp number.\n"
            "Please enter a valid number with country code.\n"
            "Example: +91 98765 43210"
        )
    return True, cleaned
