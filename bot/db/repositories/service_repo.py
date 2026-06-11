"""
Service repository — data access for services and assignments.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Service, UserServiceAssignment, UserServiceRequest


class ServiceRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Service CRUD ──

    async def get_all_active(self) -> Sequence[Service]:
        result = await self.session.execute(
            select(Service).where(Service.is_active == True).order_by(Service.name)  # noqa: E712
        )
        return result.scalars().all()

    async def get_all(self) -> Sequence[Service]:
        result = await self.session.execute(
            select(Service).order_by(Service.name)
        )
        return result.scalars().all()

    async def get_by_id(self, service_id: int) -> Optional[Service]:
        result = await self.session.execute(
            select(Service).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Service]:
        result = await self.session.execute(
            select(Service).where(Service.name.ilike(name))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        display_name: str | None = None,
        keywords: list[str] | None = None,
        sender_patterns: list[str] | None = None,
        emoji: str = "📦",
    ) -> Service:
        service = Service(
            name=name,
            display_name=display_name or name,
            keywords=keywords or [name.lower()],
            sender_patterns=sender_patterns or [],
            emoji=emoji,
        )
        self.session.add(service)
        await self.session.flush()
        return service

    async def update_service(self, service_id: int, **kwargs) -> None:
        await self.session.execute(
            update(Service).where(Service.id == service_id).values(**kwargs)
        )
        await self.session.flush()

    async def delete_service(self, service_id: int) -> None:
        # Delete related assignments and requests first
        await self.session.execute(
            delete(UserServiceAssignment).where(UserServiceAssignment.service_id == service_id)
        )
        await self.session.execute(
            delete(UserServiceRequest).where(UserServiceRequest.service_id == service_id)
        )
        await self.session.execute(
            delete(Service).where(Service.id == service_id)
        )
        await self.session.flush()

    # ── User Service Requests ──

    async def add_service_requests(self, user_id: int, service_ids: list[int]) -> None:
        """Add service requests for a user (what user asked for)."""
        # Clear existing requests
        await self.session.execute(
            delete(UserServiceRequest).where(UserServiceRequest.user_id == user_id)
        )
        for sid in service_ids:
            self.session.add(UserServiceRequest(user_id=user_id, service_id=sid))
        await self.session.flush()

    async def get_user_requests(self, user_id: int) -> Sequence[UserServiceRequest]:
        result = await self.session.execute(
            select(UserServiceRequest)
            .where(UserServiceRequest.user_id == user_id)
        )
        return result.scalars().all()

    # ── User Service Assignments (admin approved) ──

    async def assign_services(self, user_id: int, service_ids: list[int], admin_id: int) -> None:
        """Replace all service assignments for a user."""
        await self.session.execute(
            delete(UserServiceAssignment).where(UserServiceAssignment.user_id == user_id)
        )
        for sid in service_ids:
            self.session.add(
                UserServiceAssignment(user_id=user_id, service_id=sid, assigned_by=admin_id)
            )
        await self.session.flush()

    async def get_user_assignments(self, user_id: int) -> Sequence[UserServiceAssignment]:
        result = await self.session.execute(
            select(UserServiceAssignment)
            .where(UserServiceAssignment.user_id == user_id)
        )
        return result.scalars().all()

    async def get_assigned_services(self, user_id: int) -> Sequence[Service]:
        """Get the actual Service objects assigned to a user."""
        result = await self.session.execute(
            select(Service)
            .join(UserServiceAssignment, UserServiceAssignment.service_id == Service.id)
            .where(UserServiceAssignment.user_id == user_id)
            .where(Service.is_active == True)  # noqa: E712
        )
        return result.scalars().all()
