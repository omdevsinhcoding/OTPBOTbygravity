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
        "Just enter the <b>Service Name</b> and I'll configure the rest!\n\n"
        "<i>Example: Netflix, Hotstar, SonyLIV</i>\n"
    )
    await state.set_state(AdminServiceStates.waiting_name)
    await callback.answer()


@router.message(AdminServiceStates.waiting_name)
async def process_service_name(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        return
        
    raw_name = message.text.strip()
    
    # Smart auto-configuration
    name_clean = raw_name.lower().replace(" ", "")
    display_name = raw_name.title()
    
    # Generate keywords based on the name (e.g. "SonyLIV" -> "sonyliv", "sony")
    keywords = [name_clean]
    if " " in raw_name:
        keywords.extend([part.lower() for part in raw_name.split()])
    
    # Add common variations
    if "hotstar" in name_clean:
        keywords.append("jiohotstar")
    
    # Guess emoji based on keywords
    emoji = "📦"
    if any(k in name_clean for k in ["netflix", "hotstar", "sonyliv", "prime", "movie", "tv", "video"]):
        emoji = "🎬"
    elif any(k in name_clean for k in ["whatsapp", "telegram", "chat", "message"]):
        emoji = "💬"
    elif any(k in name_clean for k in ["insta", "snap", "facebook", "twitter", "social"]):
        emoji = "📱"
    elif any(k in name_clean for k in ["google", "microsoft", "apple", "mail"]):
        emoji = "🌐"

    service_repo = ServiceRepo(session)
    service = await service_repo.create(
        name=name_clean,
        display_name=display_name,
        keywords=keywords,
        sender_patterns=[],
        emoji=emoji,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Service Auto-Created!</b>\n\n"
        f"{emoji} <b>{service.display_name}</b>\n"
        f"🔍 Auto-Keywords: {', '.join(service.keywords or [])}\n\n"
        f"<i>(You can edit these from the Services menu if needed)</i>",
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
