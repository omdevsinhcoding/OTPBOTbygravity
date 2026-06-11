"""
SQLAlchemy ORM models — full database schema for TPBOT.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
#  USERS
# ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    verification_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    verification_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    service_requests: Mapped[list["UserServiceRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    service_assignments: Mapped[list["UserServiceAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_status", "status"),
    )


# ──────────────────────────────────────────────
#  ADMIN USERS
# ──────────────────────────────────────────────
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="admin", server_default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ──────────────────────────────────────────────
#  SERVICES
# ──────────────────────────────────────────────
class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    sender_patterns: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📦")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ──────────────────────────────────────────────
#  USER ↔ SERVICE REQUESTS (what user asked for)
# ──────────────────────────────────────────────
class UserServiceRequest(Base):
    __tablename__ = "user_service_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="service_requests")
    service: Mapped["Service"] = relationship()

    __table_args__ = (
        Index("idx_user_service_requests_user_id", "user_id"),
    )


# ──────────────────────────────────────────────
#  USER ↔ SERVICE ASSIGNMENTS (admin approved)
# ──────────────────────────────────────────────
class UserServiceAssignment(Base):
    __tablename__ = "user_service_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="service_assignments")
    service: Mapped["Service"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_user_service_assignment"),
        Index("idx_user_service_assignments_user_id", "user_id"),
    )


# ──────────────────────────────────────────────
#  APPROVAL ACTIONS (admin audit trail)
# ──────────────────────────────────────────────
class ApprovalAction(Base):
    __tablename__ = "approval_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ──────────────────────────────────────────────
#  VERIFICATION SESSIONS
# ──────────────────────────────────────────────
class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    captcha_answer: Mapped[str] = mapped_column(String(20), nullable=False)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ──────────────────────────────────────────────
#  BOT SETTINGS (key-value store)
# ──────────────────────────────────────────────
class BotSetting(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ──────────────────────────────────────────────
#  CHANNEL SETTINGS
# ──────────────────────────────────────────────
class ChannelSetting(Base):
    __tablename__ = "channel_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    emoji: Mapped[str] = mapped_column(String(10), default="📢")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ──────────────────────────────────────────────
#  OTP LOGS (For Recent Viewed OTPs)
# ──────────────────────────────────────────────
class OTPLog(Base):
    __tablename__ = "otp_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    otp_value: Mapped[str] = mapped_column(String(50), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    user: Mapped["User"] = relationship()
    service: Mapped["Service"] = relationship()


# ──────────────────────────────────────────────
#  BROADCASTS
# ──────────────────────────────────────────────
class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    button_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_filter: Mapped[str] = mapped_column(String(20), default="all", server_default="all")
    sent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ──────────────────────────────────────────────
#  AUDIT LOGS
# ──────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


# ──────────────────────────────────────────────
#  BANS
# ──────────────────────────────────────────────
class Ban(Base):
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    banned_by: Mapped[int] = mapped_column(BigInteger, default=0)
    banned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
