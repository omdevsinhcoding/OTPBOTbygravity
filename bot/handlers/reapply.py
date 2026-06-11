"""
Re-apply handler — allows declined users to resubmit.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.settings_repo import AuditRepo
from bot.db.repositories.user_repo import UserRepo
from bot.messages.user_msgs import ask_full_name, verification_success
from bot.states.registration import RegistrationStates

router = Router(name="reapply")


@router.callback_query(F.data == "reapply")
async def handle_reapply(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Reset user and restart registration."""
    if not callback.from_user or not callback.message:
        return

    telegram_id = callback.from_user.id

    user_repo = UserRepo(session)
    audit_repo = AuditRepo(session)

    # Reset user for re-application
    await user_repo.reset_for_reapply(telegram_id)
    await audit_repo.log(telegram_id, "reapply")

    # Start registration flow
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  📝 <b>Re-Application</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Let's submit a fresh application!\n"
        "Please fill in your details again.\n"
    )
    await callback.message.answer(ask_full_name())
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.answer()
