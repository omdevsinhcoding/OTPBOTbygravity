"""
Standardized aiogram CallbackData classes for type-safe inline keyboards.
"""

from aiogram.filters.callback_data import CallbackData

# ── User Callbacks ──

class MenuCallback(CallbackData, prefix="menu"):
    action: str

class ReqSvcCallback(CallbackData, prefix="req_svc"):
    service_id: int

class GetOtpCallback(CallbackData, prefix="get_otp"):
    service_id: int

class CopyOtpCallback(CallbackData, prefix="copy_otp"):
    otp_text: str

class PaginationCallback(CallbackData, prefix="page"):
    target: str
    page: int

# ── Admin Callbacks ──

class AdminNavCallback(CallbackData, prefix="admin_nav"):
    target: str

class AdminUserFilterCallback(CallbackData, prefix="admin_users"):
    filter_type: str
    page: int = 0

class AdminUserActionCallback(CallbackData, prefix="admin_user_action"):
    action: str
    user_id: int

class AdminSettingCallback(CallbackData, prefix="admin_set"):
    key: str

class AdminServiceActionCallback(CallbackData, prefix="admin_svc_action"):
    action: str
    service_id: int | None = None
