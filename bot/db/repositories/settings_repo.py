"""
Settings, audit, and misc repositories.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import (
    AdminUser,
    ApprovalAction,
    AuditLog,
    Ban,
    BotSetting,
    Broadcast,
    ChannelSetting,
    VerificationSession,
)


class SettingsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[str]:
        result = await self.session.execute(
            select(BotSetting.value).where(BotSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> None:
        existing = await self.session.execute(
            select(BotSetting).where(BotSetting.key == key)
        )
        setting = existing.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            self.session.add(BotSetting(key=key, value=value))
        await self.session.flush()

    async def get_all(self) -> dict[str, str]:
        result = await self.session.execute(select(BotSetting))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}

    # ── Channel Settings ──

    async def get_active_channel(self) -> Optional[ChannelSetting]:
        result = await self.session.execute(
            select(ChannelSetting).where(ChannelSetting.is_active == True).limit(1)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_all_channels(self) -> Sequence[ChannelSetting]:
        result = await self.session.execute(
            select(ChannelSetting).order_by(ChannelSetting.id.asc())
        )
        return result.scalars().all()

    async def set_channel(self, channel_id: int, channel_name: str = "", channel_url: str = "", emoji: str = "📢") -> None:
        self.session.add(ChannelSetting(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_url=channel_url,
            emoji=emoji,
            is_active=True,
        ))
        await self.session.flush()

    async def clear_channels(self) -> None:
        await self.session.execute(delete(ChannelSetting))
        await self.session.flush()


class AuditRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, telegram_id: int, action: str, details: dict | None = None, ip: str | None = None) -> None:
        self.session.add(AuditLog(
            telegram_id=telegram_id,
            action=action,
            details=details,
            ip_address=ip,
        ))
        await self.session.flush()

    async def get_logs(self, telegram_id: int | None = None, action: str | None = None,
                       limit: int = 50, offset: int = 0) -> Sequence[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        if telegram_id:
            query = query.where(AuditLog.telegram_id == telegram_id)
        if action:
            query = query.where(AuditLog.action == action)
        result = await self.session.execute(query.limit(limit).offset(offset))
        return result.scalars().all()

    async def count_action(self, action: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == action)
        )
        return result.scalar_one()


class BanRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_banned(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(Ban).where(Ban.telegram_id == telegram_id)
        )
        return result.scalar_one() > 0

    async def ban(self, telegram_id: int, reason: str = "", banned_by: int = 0) -> None:
        existing = await self.session.execute(
            select(Ban).where(Ban.telegram_id == telegram_id)
        )
        if not existing.scalar_one_or_none():
            self.session.add(Ban(telegram_id=telegram_id, reason=reason, banned_by=banned_by))
            await self.session.flush()

    async def unban(self, telegram_id: int) -> None:
        await self.session.execute(
            delete(Ban).where(Ban.telegram_id == telegram_id)
        )
        await self.session.flush()

    async def get_all_bans(self) -> Sequence[Ban]:
        result = await self.session.execute(
            select(Ban).order_by(Ban.banned_at.desc())
        )
        return result.scalars().all()


class VerificationRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, telegram_id: int, token: str, captcha_answer: str) -> VerificationSession:
        session = VerificationSession(
            telegram_id=telegram_id,
            token=token,
            captcha_answer=captcha_answer,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_by_token(self, token: str) -> Optional[VerificationSession]:
        result = await self.session.execute(
            select(VerificationSession).where(VerificationSession.token == token)
        )
        return result.scalar_one_or_none()

    async def update_session(self, token: str, **kwargs) -> None:
        await self.session.execute(
            update(VerificationSession)
            .where(VerificationSession.token == token)
            .values(**kwargs)
        )
        await self.session.flush()

    async def get_latest_passed(self, telegram_id: int) -> Optional[VerificationSession]:
        """Get the most recent passed verification session for a user."""
        result = await self.session.execute(
            select(VerificationSession)
            .where(
                VerificationSession.telegram_id == telegram_id,
                VerificationSession.status == "passed",
            )
            .order_by(VerificationSession.verified_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class ApprovalRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(self, user_id: int, admin_id: int, action: str, note: str = "") -> None:
        self.session.add(ApprovalAction(
            user_id=user_id,
            admin_id=admin_id,
            action=action,
            note=note,
        ))
        await self.session.flush()

    async def get_actions_for_user(self, user_id: int) -> Sequence[ApprovalAction]:
        result = await self.session.execute(
            select(ApprovalAction)
            .where(ApprovalAction.user_id == user_id)
            .order_by(ApprovalAction.created_at.desc())
        )
        return result.scalars().all()


class BroadcastRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_id: int, message_text: str, button_text: str = "",
                     button_url: str = "", target_filter: str = "all") -> Broadcast:
        bc = Broadcast(
            admin_id=admin_id,
            message_text=message_text,
            button_text=button_text or None,
            button_url=button_url or None,
            target_filter=target_filter,
        )
        self.session.add(bc)
        await self.session.flush()
        return bc

    async def update_sent_count(self, broadcast_id: int, count: int) -> None:
        await self.session.execute(
            update(Broadcast).where(Broadcast.id == broadcast_id).values(sent_count=count)
        )
        await self.session.flush()

    async def get_all(self, limit: int = 20) -> Sequence[Broadcast]:
        result = await self.session.execute(
            select(Broadcast).order_by(Broadcast.created_at.desc()).limit(limit)
        )
        return result.scalars().all()


class AdminRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_admin(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
        return result.scalar_one() > 0

    async def get_admin(self, telegram_id: int) -> AdminUser | None:
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def ensure_admin(self, telegram_id: int, username: str = "", role: str = "super_admin") -> None:
        existing = await self.session.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
        if not existing.scalar_one_or_none():
            self.session.add(AdminUser(telegram_id=telegram_id, username=username, role=role))
            await self.session.flush()

    async def add_admin(self, telegram_id: int, username: str = "", added_by: int | None = None) -> bool:
        """Add a sub-admin. Returns True if added, False if already exists."""
        if await self.is_admin(telegram_id):
            return False
        admin = AdminUser(telegram_id=telegram_id, username=username, role="admin", added_by=added_by)
        self.session.add(admin)
        await self.session.flush()
        return True

    async def remove_admin(self, telegram_id: int) -> bool:
        """Remove a sub-admin. Returns True if removed, False if not found."""
        result = await self.session.execute(
            delete(AdminUser).where(AdminUser.telegram_id == telegram_id).returning(AdminUser.id)
        )
        await self.session.flush()
        return bool(result.scalars().first())

    async def get_all_admins(self) -> Sequence[AdminUser]:
        result = await self.session.execute(select(AdminUser).order_by(AdminUser.created_at.asc()))
        return result.scalars().all()
