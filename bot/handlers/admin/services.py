"""
Admin service CRUD handler.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.service_repo import ServiceRepo
from bot.keyboards.admin_kb import (
    admin_back_button,
    service_detail_keyboard,
    services_management_keyboard,
)
from bot.states.registration import AdminServiceStates

logger = logging.getLogger(__name__)
router = Router(name="admin_services")


@router.callback_query(F.data == "admin:services")
async def list_services(callback: CallbackQuery, session: AsyncSession):
    """List all services for management."""
    if not callback.message:
        return

    service_repo = ServiceRepo(session)
    services = list(await service_repo.get_all())

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    🎬  <b>SERVICE MANAGEMENT</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Total services: <b>{len(services)}</b>\n\n"
        "Tap a service to manage, or\n"
        "create a new one.\n",
        reply_markup=services_management_keyboard(services),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:svc_detail:(\d+)$"))
async def service_detail(callback: CallbackQuery, session: AsyncSession):
    """Show service detail with edit options."""
    if not callback.message or not callback.data:
        return

    service_id = int(callback.data.split(":")[2])
    service_repo = ServiceRepo(session)
    service = await service_repo.get_by_id(service_id)

    if not service:
        await callback.answer("⚠️ Service not found.", show_alert=True)
        return

    active = "🟢 Active" if service.is_active else "🔴 Inactive"
    keywords = ", ".join(service.keywords or [])
    senders = ", ".join(service.sender_patterns or [])

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        f"    {service.emoji}  <b>{service.display_name or service.name}</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"📛  <b>Name:</b>  {service.name}\n"
        f"🏷️  <b>Display:</b>  {service.display_name}\n"
        f"😀  <b>Emoji:</b>  {service.emoji}\n"
        f"🔍  <b>Keywords:</b>  {keywords or 'None'}\n"
        f"📡  <b>Sender Patterns:</b>  {senders or 'None'}\n"
        f"📊  <b>Status:</b>  {active}\n",
        reply_markup=service_detail_keyboard(service_id),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:svc_create")
async def create_service_start(callback: CallbackQuery, state: FSMContext):
    """Start service creation flow."""
    if not callback.message:
        return

    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ➕ <b>Create New Service</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1: Enter the <b>service name</b>\n\n"
        "<i>Example: Netflix, Sony LIV, Hotstar</i>\n"
    )
    await state.set_state(AdminServiceStates.waiting_name)
    await callback.answer()


@router.message(AdminServiceStates.waiting_name)
async def process_service_name(message: Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(name=message.text.strip())
    await message.answer(
        "Step 2: Enter the <b>display name</b>\n"
        "(or send /skip to use the same name)\n\n"
        "<i>Example: 🎬 Netflix Premium</i>"
    )
    await state.set_state(AdminServiceStates.waiting_display_name)


@router.message(AdminServiceStates.waiting_display_name)
async def process_display_name(message: Message, state: FSMContext):
    if not message.text:
        return
    data = await state.get_data()
    display = message.text.strip() if message.text.strip() != "/skip" else data["name"]
    await state.update_data(display_name=display)
    await message.answer(
        "Step 3: Enter <b>SMS keywords</b> (comma-separated)\n"
        "These are used to match incoming SMS.\n\n"
        "<i>Example: netflix, nflx</i>"
    )
    await state.set_state(AdminServiceStates.waiting_keywords)


@router.message(AdminServiceStates.waiting_keywords)
async def process_keywords(message: Message, state: FSMContext):
    if not message.text:
        return
    keywords = [k.strip().lower() for k in message.text.split(",") if k.strip()]
    await state.update_data(keywords=keywords)
    await message.answer(
        "Step 4: Enter <b>sender patterns</b> (comma-separated)\n"
        "These match the SMS sender ID.\n\n"
        "<i>Example: 56161878, NFLIX</i>\n"
        "Send /skip if none."
    )
    await state.set_state(AdminServiceStates.waiting_sender_patterns)


@router.message(AdminServiceStates.waiting_sender_patterns)
async def process_sender_patterns(message: Message, state: FSMContext):
    if not message.text:
        return
    if message.text.strip() == "/skip":
        senders = []
    else:
        senders = [s.strip() for s in message.text.split(",") if s.strip()]
    await state.update_data(sender_patterns=senders)
    await message.answer(
        "Step 5: Enter an <b>emoji</b> for this service\n\n"
        "<i>Example: 🎬, 📺, 🎯</i>\n"
        "Send /skip for default 📦"
    )
    await state.set_state(AdminServiceStates.waiting_emoji)


@router.message(AdminServiceStates.waiting_emoji)
async def process_emoji(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        return
    emoji = message.text.strip() if message.text.strip() != "/skip" else "📦"
    data = await state.get_data()

    service_repo = ServiceRepo(session)
    service = await service_repo.create(
        name=data["name"],
        display_name=data.get("display_name"),
        keywords=data.get("keywords"),
        sender_patterns=data.get("sender_patterns"),
        emoji=emoji,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Service Created!</b>\n\n"
        f"{emoji} <b>{service.display_name or service.name}</b>\n"
        f"🔍 Keywords: {', '.join(service.keywords or [])}\n"
        f"📡 Senders: {', '.join(service.sender_patterns or [])}\n",
        reply_markup=admin_back_button(),
    )


@router.callback_query(F.data.regexp(r"^admin:svc_toggle_active:(\d+)$"))
async def toggle_service_active(callback: CallbackQuery, session: AsyncSession):
    """Toggle service active/inactive."""
    if not callback.data or not callback.message:
        return

    service_id = int(callback.data.split(":")[2])
    service_repo = ServiceRepo(session)
    service = await service_repo.get_by_id(service_id)

    if not service:
        await callback.answer("⚠️ Service not found.", show_alert=True)
        return

    new_state = not service.is_active
    await service_repo.update_service(service_id, is_active=new_state)

    status = "🟢 Activated" if new_state else "🔴 Deactivated"
    await callback.answer(f"{status} {service.name}")

    # Refresh detail view
    service = await service_repo.get_by_id(service_id)
    active = "🟢 Active" if service.is_active else "🔴 Inactive"
    keywords = ", ".join(service.keywords or [])
    senders = ", ".join(service.sender_patterns or [])

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        f"    {service.emoji}  <b>{service.display_name or service.name}</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"📛  <b>Name:</b>  {service.name}\n"
        f"🏷️  <b>Display:</b>  {service.display_name}\n"
        f"😀  <b>Emoji:</b>  {service.emoji}\n"
        f"🔍  <b>Keywords:</b>  {keywords or 'None'}\n"
        f"📡  <b>Sender Patterns:</b>  {senders or 'None'}\n"
        f"📊  <b>Status:</b>  {active}\n",
        reply_markup=service_detail_keyboard(service_id),
    )


@router.callback_query(F.data.regexp(r"^admin:svc_delete:(\d+)$"))
async def delete_service(callback: CallbackQuery, session: AsyncSession):
    """Delete a service."""
    if not callback.data or not callback.message:
        return

    service_id = int(callback.data.split(":")[2])
    service_repo = ServiceRepo(session)
    service = await service_repo.get_by_id(service_id)

    if not service:
        await callback.answer("⚠️ Service not found.", show_alert=True)
        return

    name = service.display_name or service.name
    await service_repo.delete_service(service_id)

    await callback.message.edit_text(
        f"🗑️ <b>Service Deleted</b>\n\n"
        f"<code>{name}</code> has been removed.\n",
        reply_markup=admin_back_button(),
    )
    await callback.answer(f"🗑️ Deleted {name}")


@router.callback_query(F.data.regexp(r"^admin:svc_edit:(\d+):(name|keywords|senders|emoji)$"))
async def edit_service_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Start editing a service field."""
    if not callback.data or not callback.message:
        return

    parts = callback.data.split(":")
    service_id = int(parts[2])
    field = parts[3]

    await state.update_data(edit_service_id=service_id, edit_field=field)

    prompts = {
        "name": "Enter the new <b>name</b>:",
        "keywords": "Enter new <b>keywords</b> (comma-separated):",
        "senders": "Enter new <b>sender patterns</b> (comma-separated):",
        "emoji": "Enter the new <b>emoji</b>:",
    }

    await callback.message.edit_text(
        f"✏️ <b>Edit Service</b>\n\n{prompts.get(field, 'Enter new value:')}\n"
    )
    await state.set_state(AdminServiceStates.edit_field)
    await callback.answer()


@router.message(AdminServiceStates.edit_field)
async def save_service_edit(message: Message, state: FSMContext, session: AsyncSession):
    """Save the edited service field."""
    if not message.text:
        return

    data = await state.get_data()
    service_id = data["edit_service_id"]
    field = data["edit_field"]
    value = message.text.strip()

    service_repo = ServiceRepo(session)

    if field == "name":
        await service_repo.update_service(service_id, name=value, display_name=value)
    elif field == "keywords":
        keywords = [k.strip().lower() for k in value.split(",") if k.strip()]
        await service_repo.update_service(service_id, keywords=keywords)
    elif field == "senders":
        senders = [s.strip() for s in value.split(",") if s.strip()]
        await service_repo.update_service(service_id, sender_patterns=senders)
    elif field == "emoji":
        await service_repo.update_service(service_id, emoji=value)

    await state.clear()
    await message.answer(
        f"✅ Service updated successfully!",
        reply_markup=admin_back_button(),
    )
