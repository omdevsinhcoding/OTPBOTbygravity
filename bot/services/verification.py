"""
Verification utilities — token generation.
reCAPTCHA validation is handled by the verification server backend.
"""

from __future__ import annotations

import secrets


def generate_verification_token() -> str:
    """Generate a secure random verification token."""
    return secrets.token_urlsafe(32)
