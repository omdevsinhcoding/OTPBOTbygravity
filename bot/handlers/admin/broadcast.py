"""
Admin broadcast handler.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.settings_repo import BroadcastRepo
from bot.db.repositories.user_repo import UserRepo
from bot.keyboards.admin_kb import admin_back_button, broadcast_target_keyboard
from bot.loader import bot
from bot.messages.admin_msgs import broadcast_sent_message
from bot.states.registration import AdminBroadcastStates

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")


@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast flow."""
    if not callback.message:
        return

    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  📢 <b>Send Broadcast</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Enter the <b>broadcast message</b>:\n\n"
        "<i>Supports HTML formatting</i>\n"
    )
    await state.set_state(AdminBroadcastStates.waiting_message)
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(message_text=message.text)
    await message.answer(
        "Add an <b>inline button</b>?\n\n"
        "Enter button text, or send /skip\n\n"
        "<i>Example: Visit Website</i>"
    )
    await state.set_state(AdminBroadcastStates.waiting_button_text)


@router.message(AdminBroadcastStates.waiting_button_text)
async def process_button_text(message: Message, state: FSMContext):
    if not message.text:
        return
    if message.text.strip() == "/skip":
        await state.update_data(button_text="", button_url="")
        await message.answer(
            "Select <b>target audience</b>:\n",
            reply_markup=broadcast_target_keyboard(),
        )
        await state.set_state(AdminBroadcastStates.waiting_target)
    else:
        await state.update_data(button_text=message.text.strip())
        await message.answer(
            "Enter the <b>button URL</b>:\n\n"
            "<i>Example: https://example.com</i>"
        )
        await state.set_state(AdminBroadcastStates.waiting_button_url)


@router.message(AdminBroadcastStates.waiting_button_url)
async def process_button_url(message: Message, state: FSMContext):
    if not message.text:
        return
    await state.update_data(button_url=message.text.strip())
    await message.answer(
        "Select <b>target audience</b>:\n",
        reply_markup=broadcast_target_keyboard(),
    )
    await state.set_state(AdminBroadcastStates.waiting_target)


@router.callback_query(AdminBroadcastStates.waiting_target, F.data.startswith("bc_target:"))
async def process_target(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Send the broadcast."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    target = callback.data.split(":")[1]
    data = await state.get_data()

    message_text = data["message_text"]
    button_text = data.get("button_text", "")
    button_url = data.get("button_url", "")
    admin_id = callback.from_user.id

    user_repo = UserRepo(session)
    broadcast_repo = BroadcastRepo(session)

    # Get target user IDs
    user_ids = await user_repo.get_users_by_filter(target)

    # Build keyboard
    keyboard = None
    if button_text and button_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])

    # Save broadcast record
    bc = await broadcast_repo.create(
        admin_id=admin_id,
        message_text=message_text,
        button_text=button_text,
        button_url=button_url,
        target_filter=target,
    )

    await state.clear()

    # Send to all targets
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message_text, reply_markup=keyboard)
            sent += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            logger.warning(f"Failed to send broadcast to {uid}: {e}")

    await broadcast_repo.update_sent_count(bc.id, sent)

    await callback.message.edit_text(
        broadcast_sent_message(sent),
        reply_markup=admin_back_button(),
    )
    await callback.answer(f"📢 Sent to {sent} users!")
