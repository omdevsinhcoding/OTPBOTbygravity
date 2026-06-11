"""
Registration handler — FSM-based multi-step form.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db.repositories.service_repo import ServiceRepo
from bot.db.repositories.settings_repo import AuditRepo, SettingsRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.user_kb import service_selection_keyboard
from bot.loader import bot
from bot.messages.admin_msgs import new_user_request
from bot.messages.user_msgs import (
    ask_full_name,
    ask_services,
    ask_whatsapp,
    registration_complete,
)
from bot.states.registration import RegistrationStates
from bot.utils.validators import validate_full_name, validate_whatsapp
from bot.keyboards.admin_kb import user_detail_keyboard

logger = logging.getLogger(__name__)
router = Router(name="registration")


# ── Step 1: Full Name ──
@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text or not message.from_user:
        return

    valid, result = validate_full_name(message.text)
    if not valid:
        await message.answer(f"⚠️ {result}\n\nPlease enter your full name:")
        return

    await state.update_data(full_name=result)
    await message.answer(ask_whatsapp())
    await state.set_state(RegistrationStates.waiting_whatsapp)

    # Log
    audit = AuditRepo(session)
    await audit.log(message.from_user.id, "form_started", {"step": "full_name"})


# ── Step 2: WhatsApp Number ──
@router.message(RegistrationStates.waiting_whatsapp)
async def process_whatsapp(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text or not message.from_user:
        return

    valid, result = validate_whatsapp(message.text)
    if not valid:
        await message.answer(f"⚠️ {result}")
        return

    await state.update_data(whatsapp=result)

    # Fetch services for selection
    service_repo = ServiceRepo(session)
    services = await service_repo.get_all_active()
    services_list = list(services)

    if not services_list:
        await message.answer(
            "⚠️ No services are currently available.\n"
            "Please try again later or contact support."
        )
        await state.clear()
        return

    await state.update_data(selected_services=set())
    await message.answer(
        ask_services(),
        reply_markup=service_selection_keyboard(services_list),
    )
    await state.set_state(RegistrationStates.waiting_services)


# ── Step 3: Service Selection (toggle) ──
@router.callback_query(RegistrationStates.waiting_services, F.data.startswith("svc_toggle:"))
async def toggle_service(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.data or not callback.message:
        return

    service_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected: set = data.get("selected_services", set())

    if service_id in selected:
        selected.discard(service_id)
    else:
        selected.add(service_id)

    await state.update_data(selected_services=selected)

    # Re-render keyboard
    service_repo = ServiceRepo(session)
    services = await service_repo.get_all_active()
    services_list = list(services)

    await callback.message.edit_reply_markup(
        reply_markup=service_selection_keyboard(services_list, selected),
    )
    await callback.answer()


# ── Step 3: Submit Selection ──
@router.callback_query(RegistrationStates.waiting_services, F.data == "svc_submit")
async def submit_services(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.from_user or not callback.message:
        return

    data = await state.get_data()
    selected: set = data.get("selected_services", set())

    if not selected:
        await callback.answer("⚠️ Please select at least one service.", show_alert=True)
        return

    telegram_id = callback.from_user.id
    full_name = data["full_name"]
    whatsapp = data["whatsapp"]

    # Save registration
    user_repo = UserRepo(session)
    service_repo = ServiceRepo(session)
    audit_repo = AuditRepo(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("⚠️ Error — user not found.", show_alert=True)
        return

    await user_repo.update_registration(telegram_id, full_name, whatsapp)
    await service_repo.add_service_requests(user.id, list(selected))

    await audit_repo.log(telegram_id, "form_submitted", {
        "full_name": full_name,
        "whatsapp": whatsapp,
        "services": list(selected),
    })

    await state.clear()

    # Refresh user with services loaded
    user = await user_repo.get_by_telegram_id(telegram_id)

    # Get requested service objects
    all_services = await service_repo.get_all_active()
    requested = [s for s in all_services if s.id in selected]

    # ── Notify admin ──
    admin_text = new_user_request(user, requested)

    # Send to all admins
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=user_detail_keyboard(user),
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    # Send to private channel
    settings_repo = SettingsRepo(session)
    channel = await settings_repo.get_active_channel()
    if channel:
        try:
            await bot.send_message(
                channel.channel_id,
                admin_text,
                reply_markup=user_detail_keyboard(user),
            )
        except Exception as e:
            logger.error(f"Failed to post to channel {channel.channel_id}: {e}")

    # Confirm to user
    await callback.message.edit_text(registration_complete(full_name))
    await callback.answer()
