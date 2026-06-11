"""
Repository for managing OTP view logs.
"""

from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import OTPLog


class OTPLogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_otp_view(self, user_id: int, service_id: int, otp_value: str) -> OTPLog:
        """Log that a user viewed an OTP."""
        log = OTPLog(
            user_id=user_id,
            service_id=service_id,
            otp_value=otp_value,
            viewed_at=datetime.now(timezone.utc)
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_recent_otps_paginated(self, user_id: int, page: int = 1, per_page: int = 5) -> list[OTPLog]:
        """Fetch paginated recent OTPs for a user, joined with Service name."""
        offset = (page - 1) * per_page
        result = await self.session.execute(
            select(OTPLog)
            .options(selectinload(OTPLog.service))
            .where(OTPLog.user_id == user_id)
            .order_by(OTPLog.viewed_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all())

    async def get_total_pages(self, user_id: int, per_page: int = 5) -> int:
        """Get the total number of pages for pagination."""
        result = await self.session.execute(
            select(func.count(OTPLog.id))
            .where(OTPLog.user_id == user_id)
        )
        total_items = result.scalar_one()
        return max(1, (total_items + per_page - 1) // per_page)
