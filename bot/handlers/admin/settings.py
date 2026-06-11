"""
Admin settings handler — bot settings, channel, support, ban message, disclaimer.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.settings_repo import SettingsRepo
from bot.keyboards.admin_kb import admin_back_button, settings_keyboard
from bot.states.registration import AdminSettingStates

logger = logging.getLogger(__name__)
router = Router(name="admin_settings")


# ── Bot Settings Menu ──
@router.callback_query(F.data == "admin:settings")
async def bot_settings_menu(callback: CallbackQuery, session: AsyncSession):
    if not callback.message:
        return
    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    ⚙️  <b>BOT SETTINGS</b>\n"
        "╚══════════════════════════════╝\n\n"
        "Configure bot messages:\n",
        reply_markup=settings_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:set:(\w+)$"))
async def edit_setting(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.data or not callback.message:
        return
    key = callback.data.split(":")[2]

    settings_repo = SettingsRepo(session)
    current = await settings_repo.get(key) or "Not set"

    titles = {
        "welcome_message": "👋 Welcome Message",
        "approval_message": "✅ Approval Message",
        "decline_message": "❌ Decline Message",
    }

    await state.update_data(setting_key=key)
    await callback.message.edit_text(
        f"✏️ <b>{titles.get(key, key)}</b>\n\n"
        f"Current value:\n<i>{current[:500]}</i>\n\n"
        f"Enter the new value:\n"
    )
    await state.set_state(AdminSettingStates.waiting_value)
    await callback.answer()


@router.message(AdminSettingStates.waiting_value)
async def save_setting(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        return
    data = await state.get_data()
    key = data["setting_key"]

    settings_repo = SettingsRepo(session)
    await settings_repo.set(key, message.text.strip())

    await state.clear()
    await message.answer(
        f"✅ <b>Setting Updated!</b>\n\n"
        f"<code>{key}</code> has been saved.\n",
        reply_markup=admin_back_button(),
    )


# ── Support Settings ──
@router.callback_query(F.data == "admin:support")
async def support_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    current = await settings_repo.get("support_text") or "Not configured"

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    💬  <b>SUPPORT SETTINGS</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current:\n<i>{current[:500]}</i>\n\n"
        "Enter new support text:\n",
    )
    await state.update_data(setting_key="support_text")
    await state.set_state(AdminSettingStates.waiting_value)
    await callback.answer()


# ── Ban Message ──
@router.callback_query(F.data == "admin:ban_msg")
async def ban_msg_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    current = await settings_repo.get("ban_message") or "Not configured"

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    🚫  <b>BAN MESSAGE</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current:\n<i>{current[:500]}</i>\n\n"
        "Enter the new ban message:\n",
    )
    await state.update_data(setting_key="ban_message")
    await state.set_state(AdminSettingStates.waiting_value)
    await callback.answer()


# ── Disclaimer ──
@router.callback_query(F.data == "admin:disclaimer")
async def disclaimer_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    current = await settings_repo.get("disclaimer_text") or "Not configured"

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    📜  <b>DISCLAIMER</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current:\n<i>{current[:500]}</i>\n\n"
        "Enter the new disclaimer text:\n",
    )
    await state.update_data(setting_key="disclaimer_text")
    await state.set_state(AdminSettingStates.waiting_value)
    await callback.answer()


# ── Channel Settings ──
@router.callback_query(F.data == "admin:channel")
async def channel_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    channel = await settings_repo.get_active_channel()

    current_info = (
        f"Channel ID: <code>{channel.channel_id}</code>\n"
        f"Name: {channel.channel_name or 'N/A'}\n"
    ) if channel else "No channel configured."

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    📡  <b>CHANNEL SETTINGS</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current:\n{current_info}\n\n"
        "Enter the <b>channel/chat ID</b>:\n\n"
        "<i>Example: -1001234567890\n"
        "Forward a message from the channel\n"
        "to @userinfobot to get the ID.</i>\n",
    )
    await state.set_state(AdminSettingStates.waiting_channel_id)
    await callback.answer()


@router.message(AdminSettingStates.waiting_channel_id)
async def save_channel_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        return

    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Please enter a valid numeric channel ID.")
        return

    settings_repo = SettingsRepo(session)
    await settings_repo.set_channel(channel_id, f"Channel {channel_id}")

    await state.clear()
    await message.answer(
        f"✅ <b>Channel Updated!</b>\n\n"
        f"Channel ID: <code>{channel_id}</code>\n\n"
        "<i>Make sure the bot is an admin in this channel.</i>\n",
        reply_markup=admin_back_button(),
    )
