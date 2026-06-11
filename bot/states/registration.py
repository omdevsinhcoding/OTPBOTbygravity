"""
FSM states for user registration flow and admin workflows.
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_full_name = State()
    waiting_whatsapp = State()
    waiting_services = State()


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_button_text = State()
    waiting_button_url = State()
    waiting_target = State()
    confirm = State()


class AdminServiceStates(StatesGroup):
    waiting_name = State()
    waiting_display_name = State()
    waiting_keywords = State()
    waiting_sender_patterns = State()
    waiting_emoji = State()
    edit_field = State()


class AdminSettingStates(StatesGroup):
    waiting_value = State()
    waiting_channel_id = State()
    waiting_ban_message = State()
    waiting_disclaimer = State()
    waiting_support_text = State()
