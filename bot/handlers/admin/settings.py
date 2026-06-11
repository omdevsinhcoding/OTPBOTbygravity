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

@router.callback_query(F.data == "admin:toggle_verification")
async def toggle_verification(callback: CallbackQuery, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    v_status_str = await settings_repo.get("verification_enabled")
    current_status = (v_status_str or "true").lower() == "true"
    new_status = not current_status
    await settings_repo.set("verification_enabled", "true" if new_status else "false")
    
    # Reload admin panel
    from bot.keyboards.admin_kb import admin_main_menu
    await callback.message.edit_reply_markup(reply_markup=admin_main_menu(new_status))
    await callback.answer(f"Verification turned {'ON' if new_status else 'OFF'}!")

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
        "ban_message": "🚫 Ban Message",
        "disclaimer": "📜 Disclaimer",
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
@router.callback_query(F.data == "admin:support_setup")
async def support_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    current = await settings_repo.get("support_text") or "Not configured"

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    💬  <b>SUPPORT SETTINGS</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current text:\n<i>{current[:500]}</i>\n\n"
        "Enter new support text (or type `skip` to keep current):\n",
        parse_mode="HTML"
    )
    await state.update_data(setting_key="support_text")
    await state.set_state(AdminSettingStates.waiting_support_text)
    await callback.answer()

from bot.keyboards.admin_kb import confirm_keyboard

@router.message(AdminSettingStates.waiting_support_text)
async def save_support_text(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    text = message.text.strip()
    
    if text.lower() != "skip":
        settings_repo = SettingsRepo(session)
        await settings_repo.set("support_text", text)

    await message.answer(
        "Should Support be visible as a **Persistent Reply Keyboard Button** (Static)?\n"
        "Reply with `Yes` or `No`."
    )
    await state.set_state(AdminSettingStates.waiting_support_kb)

@router.message(AdminSettingStates.waiting_support_kb)
async def save_support_kb(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    val = message.text.strip().lower()
    if val not in ["yes", "no", "y", "n"]:
        await message.answer("Please reply with Yes or No.")
        return
        
    settings_repo = SettingsRepo(session)
    await settings_repo.set("support_show_keyboard", "true" if val in ["yes", "y"] else "false")
    
    await message.answer(
        "Should Support be visible as an **Inline Keyboard Button**?\n"
        "Reply with `Yes` or `No`."
    )
    await state.set_state(AdminSettingStates.waiting_support_in)

@router.message(AdminSettingStates.waiting_support_in)
async def save_support_in(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    val = message.text.strip().lower()
    if val not in ["yes", "no", "y", "n"]:
        await message.answer("Please reply with Yes or No.")
        return
        
    settings_repo = SettingsRepo(session)
    await settings_repo.set("support_show_inline", "true" if val in ["yes", "y"] else "false")
    
    await state.clear()
    await message.answer(
        "✅ <b>Support Configuration Saved!</b>",
        reply_markup=admin_back_button()
    )

# ── Channel Settings ──
@router.callback_query(F.data == "admin:channels")
async def channel_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not callback.message:
        return
    settings_repo = SettingsRepo(session)
    channels = await settings_repo.get_all_channels()

    if channels:
        current_info = "\n".join(
            f"{ch.emoji} {ch.channel_name} (ID: <code>{ch.channel_id}</code>)\n"
            f"URL: {ch.channel_url}\n"
            f"Visible in: Static {'Yes' if ch.show_in_keyboard else 'No'} | Inline {'Yes' if ch.show_in_inline else 'No'}\n" 
            for ch in channels
        )
    else:
        current_info = "No channels configured."

    await callback.message.edit_text(
        "╔══════════════════════════════╗\n"
        "    📡  <b>CHANNEL SETTINGS</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"Current:\n{current_info}\n\n"
        "To add/update a channel, enter the <b>channel/chat ID</b>:\n\n"
        "<i>Example: -1001234567890\n"
        "Forward a message from the channel\n"
        "to @userinfobot to get the ID.</i>\n",
        parse_mode="HTML"
    )
    await state.set_state(AdminSettingStates.waiting_channel_id)
    await callback.answer()

@router.message(AdminSettingStates.waiting_channel_id)
async def save_channel_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Please enter a valid numeric channel ID.")
        return

    await state.update_data(channel_id=channel_id)
    await message.answer("Enter the **Name** for this channel (e.g., Official Updates):")
    await state.set_state(AdminSettingStates.waiting_channel_name)

@router.message(AdminSettingStates.waiting_channel_name)
async def save_channel_name(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    await state.update_data(channel_name=message.text.strip())
    
    await message.answer("Enter the **Join URL** for this channel (e.g., https://t.me/joinchat/...):")
    await state.set_state(AdminSettingStates.waiting_channel_url)

@router.message(AdminSettingStates.waiting_channel_url)
async def save_channel_url(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ Please enter a valid URL starting with http or https.")
        return
        
    await state.update_data(channel_url=url)
    
    await message.answer(
        "Should this channel be visible as a **Persistent Reply Keyboard Button** (Static)?\n"
        "Reply with `Yes` or `No`."
    )
    await state.set_state(AdminSettingStates.waiting_channel_kb)

@router.message(AdminSettingStates.waiting_channel_kb)
async def save_channel_kb(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    val = message.text.strip().lower()
    if val not in ["yes", "no", "y", "n"]:
        await message.answer("Please reply with Yes or No.")
        return
        
    await state.update_data(channel_kb=(val in ["yes", "y"]))
    
    await message.answer(
        "Should this channel be visible as an **Inline Keyboard Button**?\n"
        "Reply with `Yes` or `No`."
    )
    await state.set_state(AdminSettingStates.waiting_channel_in)

@router.message(AdminSettingStates.waiting_channel_in)
async def save_channel_in(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text: return
    val = message.text.strip().lower()
    if val not in ["yes", "no", "y", "n"]:
        await message.answer("Please reply with Yes or No.")
        return
        
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel_name = data["channel_name"]
    channel_url = data["channel_url"]
    channel_kb = data["channel_kb"]
    channel_in = (val in ["yes", "y"])

    settings_repo = SettingsRepo(session)
    await settings_repo.set_channel(
        channel_id, 
        channel_name, 
        emoji="📢", 
        url=channel_url, 
        show_in_keyboard=channel_kb, 
        show_in_inline=channel_in
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Channel Saved!</b>\n\n"
        f"Channel ID: <code>{channel_id}</code>\n\n"
        "<i>Make sure the bot is an admin in this channel.</i>\n",
        reply_markup=admin_back_button(),
    )
