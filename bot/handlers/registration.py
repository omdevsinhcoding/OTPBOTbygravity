"""
Registration & Verification Handlers.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ContentType
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.service_repo import ServiceRepo
from bot.db.repositories.settings_repo import AuditRepo, SettingsRepo, AdminRepo
from bot.db.repositories.user_repo import UserRepo
from bot.loader import bot
from bot.messages.admin_msgs import new_user_request

logger = logging.getLogger(__name__)
router = Router(name="registration")

@router.message(F.content_type == ContentType.CONTACT)
async def process_contact(message: Message, session: AsyncSession):
    """Handle the shared contact for verification."""
    if not message.contact or not message.from_user:
        return

    # Ensure the contact matches the user sending it
    if message.contact.user_id != message.from_user.id:
        await message.answer("⚠️ Please share your own contact using the button provided.")
        return

    telegram_id = message.from_user.id
    phone_number = message.contact.phone_number
    first_name = message.from_user.first_name or "there"

    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        user = await user_repo.create(telegram_id, message.from_user.username)

    # Save phone and full name (from the contact object)
    full_name = f"{message.contact.first_name} {message.contact.last_name or ''}".strip()
    await user_repo.update_registration(telegram_id, full_name, phone_number)
    
    await message.answer("✅ Contact received!")
    
    # Trigger Captcha step
    from bot.handlers.start import _send_verification
    await _send_verification(message, session, telegram_id, first_name)


@router.callback_query(F.data.startswith("req_svc:"))
async def process_request_service(callback: CallbackQuery, session: AsyncSession):
    """Handle when a user selects a service to request."""
    if not callback.data or not callback.message:
        return

    service_id = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id

    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    audit_repo = AuditRepo(session)
    admin_repo = AdminRepo(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return

    # Create the request
    await service_repo.add_service_requests(user.id, [service_id])
    
    service = await service_repo.get_by_id(service_id)
    svc_name = service.display_name or service.name if service else "Service"

    await audit_repo.log(telegram_id, "service_requested", {"service_id": service_id})

    # Notify admins
    from bot.keyboards.admin_kb import user_detail_keyboard
    admin_text = new_user_request(user, [service] if service else [])
    
    admins = await admin_repo.get_all_admins()
    admin_ids = {a.telegram_id for a in admins}
    admin_ids.add(settings.SUPER_ADMIN_ID)

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=user_detail_keyboard(user),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    await callback.message.edit_text(
        f"✅ Your request for **{svc_name}** has been sent to the admins. "
        "You will be notified once it is approved.",
        parse_mode="Markdown"
    )
    await callback.answer()
