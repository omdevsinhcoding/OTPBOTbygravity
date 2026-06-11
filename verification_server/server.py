"""
Verification API server — runs on VPS alongside the bot.

Security layers:
  1. CORS — only your Netlify domain can call this API
  2. Rate limiting — max 10 requests per IP per minute
  3. Token validation — only valid pending tokens accepted
  4. reCAPTCHA backend verification — Google validates the human
  5. Brute force protection — 3 max attempts per token
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from aiohttp import web
from aiohttp.web import middleware

from bot.config import settings
from bot.db import async_session
from bot.db.repositories.settings_repo import AuditRepo, VerificationRepo
from bot.db.repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)

# ── Rate limiter storage (IP -> list of timestamps) ──
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 10          # max requests
RATE_LIMIT_WINDOW = 60       # per 60 seconds


def _get_client_ip(request: web.Request) -> str:
    """Get real client IP (supports reverse proxy)."""
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip:
        ip = request.headers.get("X-Real-IP", "")
    if not ip:
        ip = request.remote or "unknown"
    return ip


def _is_rate_limited(ip: str) -> bool:
    """Check if IP has exceeded rate limit."""
    now = time.time()
    # Clean old entries
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[ip]) >= RATE_LIMIT_MAX:
        return True
    _rate_limits[ip].append(now)
    return False


# ── CORS Middleware (ONLY allows your Netlify domain) ──
@middleware
async def cors_middleware(request: web.Request, handler):
    # Get allowed origin from settings
    allowed_origin = settings.VERIFY_SITE_URL.rstrip("/")

    origin = request.headers.get("Origin", "")

    if request.method == "OPTIONS":
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    # Only allow YOUR Netlify domain (not *)
    if origin and (origin.rstrip("/") == allowed_origin or "localhost" in origin):
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ── Rate Limit Middleware ──
@middleware
async def rate_limit_middleware(request: web.Request, handler):
    ip = _get_client_ip(request)

    if _is_rate_limited(ip):
        logger.warning(f"Rate limited IP: {ip}")
        return web.json_response(
            {"error": "Too many requests. Please wait and try again."},
            status=429,
        )

    return await handler(request)


# ── Endpoints ──

async def health_check(request: web.Request) -> web.Response:
    """Health check for the verification server."""
    return web.json_response({"status": "ok", "service": "tpbot-verify"})


async def get_session_info(request: web.Request) -> web.Response:
    """
    GET /api/session?token=xxx
    Returns session status + reCAPTCHA site key (public, safe to share).
    """
    token = request.query.get("token", "")
    if not token:
        return web.json_response({"error": "Missing token"}, status=400)

    async with async_session() as session:
        v_repo = VerificationRepo(session)
        v_session = await v_repo.get_by_token(token)

        if not v_session:
            return web.json_response({"error": "Invalid or expired token"}, status=400)

        if v_session.status == "passed":
            return web.json_response({"error": "Already verified", "status": "passed"}, status=400)

        if v_session.status == "failed":
            return web.json_response({"error": "Session failed", "status": "failed"}, status=400)

        # Check max attempts (brute force protection)
        if v_session.attempts >= 3:
            return web.json_response({"error": "Too many attempts. Send /start in Telegram for a new link."}, status=429)

        # Site key is PUBLIC (designed to be shared — it's not a secret)
        return web.json_response({
            "status": "pending",
            "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
        })


async def submit_verification(request: web.Request) -> web.Response:
    """
    POST /api/verify
    Receives: token, recaptcha_token, location, user_agent
    
    Security:
      1. Validates token exists and is pending
      2. Checks attempt count (max 3)
      3. Validates reCAPTCHA with Google's backend
      4. Only then stores data
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "error": "Invalid request"}, status=400)

    token = data.get("token", "")
    recaptcha_token = data.get("recaptcha_token", "")
    location = data.get("location")
    user_agent = data.get("user_agent", "")
    screen_info = data.get("screen_info", "")

    if not token:
        return web.json_response({"success": False, "error": "Missing token"}, status=400)
    if not recaptcha_token:
        return web.json_response({"success": False, "error": "reCAPTCHA not completed"}, status=400)
    if not location or not location.get("lat"):
        return web.json_response({"success": False, "error": "Location is required"}, status=400)

    ip_address = _get_client_ip(request)

    async with async_session() as session:
        v_repo = VerificationRepo(session)
        audit_repo = AuditRepo(session)
        user_repo = UserRepo(session)

        # ── Validate token ──
        v_session = await v_repo.get_by_token(token)
        if not v_session:
            return web.json_response({"success": False, "error": "Invalid token"}, status=400)

        if v_session.status != "pending":
            return web.json_response({"success": False, "error": "Session already used"}, status=400)

        # ── Brute force check (max 3 attempts per token) ──
        if v_session.attempts >= 3:
            await v_repo.update_session(token, status="failed")
            await session.commit()
            return web.json_response(
                {"success": False, "error": "Too many attempts. Send /start for a new link."},
                status=429,
            )

        # Increment attempt counter
        await v_repo.update_session(token, attempts=v_session.attempts + 1)

        # ── Verify reCAPTCHA with Google backend ──
        # This is the KEY security step — the secret key NEVER leaves the server
        recaptcha_valid = False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://www.google.com/recaptcha/api/siteverify",
                    data={
                        "secret": settings.RECAPTCHA_SECRET_KEY,  # Secret stays on server only
                        "response": recaptcha_token,
                        "remoteip": ip_address,
                    },
                )
                result = resp.json()
                recaptcha_valid = result.get("success", False)
                logger.info(f"reCAPTCHA result for {ip_address}: {result}")
        except Exception as e:
            logger.error(f"reCAPTCHA verification error: {e}")
            await session.commit()
            return web.json_response({"success": False, "error": "Verification service error"}, status=500)

        if not recaptcha_valid:
            await session.commit()
            return web.json_response(
                {"success": False, "error": "reCAPTCHA failed. Please try again."},
                status=400,
            )

        # ── Success — store everything ──
        now = datetime.now(timezone.utc)
        await v_repo.update_session(
            token,
            status="passed",
            location=location,
            ip_address=ip_address,
            verified_at=now,
        )

        await user_repo.set_verified(
            v_session.telegram_id,
            ip=ip_address,
            location={
                **location,
                "user_agent": user_agent,
                "screen_info": screen_info,
                "verified_at": now.isoformat(),
            },
        )

        await audit_repo.log(v_session.telegram_id, "captcha_passed", {
            "ip": ip_address,
            "location": location,
            "user_agent": user_agent,
            "method": "recaptcha_v2",
        })

        await session.commit()

        # ── Trigger Admin Notification if User is Fully Registered ──
        user = await user_repo.get_by_telegram_id(v_session.telegram_id)
        if user and user.registered_at:
            from bot.loader import bot
            from bot.messages.admin_msgs import new_user_request
            from bot.keyboards.admin_kb import user_detail_keyboard
            from bot.db.repositories.service_repo import ServiceRepo
            
            service_repo = ServiceRepo(session)
            all_services = await service_repo.get_all_active()
            
            req_ids = [r.service_id for r in user.service_requests]
            requested = [s for s in all_services if s.id in req_ids]
            
            admin_text = new_user_request(user, requested)
            
            for admin_id in settings.admin_id_list:
                try:
                    await bot.send_message(
                        admin_id,
                        admin_text,
                        reply_markup=user_detail_keyboard(user),
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} after verification: {e}")

            # Send to private channel
            from bot.db.repositories.settings_repo import SettingsRepo
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
                    logger.error(f"Failed to post to channel {channel.channel_id} after verification: {e}")

        # Get bot username for deep link redirect
        bot_username = getattr(settings, '_bot_username', None)

        return web.json_response({
            "success": True,
            "message": "Verification complete! Go back to Telegram.",
            "bot_username": bot_username,
        })


async def check_verification_status(request: web.Request) -> web.Response:
    """
    GET /api/status?token=xxx
    Check if verification is complete.
    """
    token = request.query.get("token", "")
    if not token:
        return web.json_response({"verified": False}, status=400)

    async with async_session() as session:
        v_repo = VerificationRepo(session)
        v_session = await v_repo.get_by_token(token)

        if not v_session:
            return web.json_response({"verified": False}, status=400)

        return web.json_response({
            "verified": v_session.status == "passed",
            "status": v_session.status,
        })


# ── App Factory ──

def create_app() -> web.Application:
    """Create the aiohttp verification API application."""
    app = web.Application(middlewares=[
        rate_limit_middleware,   # Rate limiting FIRST
        cors_middleware,         # Then CORS
    ])
    app.router.add_get("/api/health", health_check)
    app.router.add_get("/api/session", get_session_info)
    app.router.add_post("/api/verify", submit_verification)
    app.router.add_get("/api/status", check_verification_status)
    return app


async def start_verification_server():
    """Start the verification API server."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.VERIFY_SERVER_HOST, settings.VERIFY_SERVER_PORT)
    await site.start()
    logger.info(
        f"🌐 Verification API running on "
        f"{settings.VERIFY_SERVER_HOST}:{settings.VERIFY_SERVER_PORT}"
    )
    logger.info(f"🔒 CORS restricted to: {settings.VERIFY_SITE_URL}")
    return runner
