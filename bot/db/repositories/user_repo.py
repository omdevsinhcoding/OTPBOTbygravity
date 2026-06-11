"""
User repository — data access for users table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.db.models import User, UserServiceAssignment, UserServiceRequest


class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.service_requests),
                selectinload(User.service_assignments),
            )
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.service_requests),
                selectinload(User.service_assignments),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, telegram_id: int, username: str | None = None) -> User:
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_registration(
        self,
        telegram_id: int,
        full_name: str,
        whatsapp_number: str,
    ) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        user.full_name = full_name
        user.whatsapp_number = whatsapp_number
        user.status = "pending"
        user.registered_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def set_verified(self, telegram_id: int, ip: str | None = None, location: dict | None = None) -> None:
        await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                is_verified=True,
                verification_ip=ip,
                verification_location=location,
            )
        )
        await self.session.flush()

    async def set_status(self, user_id: int, status: str) -> None:
        values = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if status == "approved":
            values["approved_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await self.session.flush()

    async def set_blocked(self, telegram_id: int, blocked: bool = True) -> None:
        await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_blocked=blocked)
        )
        await self.session.flush()

    async def get_users_by_status(self, status: str, limit: int = 50, offset: int = 0) -> Sequence[User]:
        result = await self.session.execute(
            select(User)
            .where(User.status == status)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_all_users(self, limit: int = 50, offset: int = 0) -> Sequence[User]:
        result = await self.session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_verified_users(self, limit: int = 50, offset: int = 0) -> Sequence[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_verified == True)  # noqa: E712
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_by_status(self, status: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.status == status)
        )
        return result.scalar_one()

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User)
        )
        return result.scalar_one()

    async def count_verified(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.is_verified == True)  # noqa: E712
        )
        return result.scalar_one()

    async def get_approved_users_ids(self) -> list[int]:
        result = await self.session.execute(
            select(User.telegram_id).where(User.status == "approved")
        )
        return list(result.scalars().all())

    async def get_users_by_filter(self, target_filter: str) -> list[int]:
        """Get telegram IDs by broadcast filter."""
        query = select(User.telegram_id)
        if target_filter != "all":
            query = query.where(User.status == target_filter)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def reset_for_reapply(self, telegram_id: int) -> None:
        """Reset user status for re-application."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.status = "pending"
            user.registered_at = None
            user.approved_at = None
            # Clear old service requests
            for req in user.service_requests:
                await self.session.delete(req)
            # Clear old assignments
            for assign in user.service_assignments:
                await self.session.delete(assign)
            await self.session.flush()
