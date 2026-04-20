from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, field_validator

from config import (
    APP_BASE_URL,
    FRONTEND_BASE_URL,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    LOGIN_LOCKOUT_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_WINDOW_MINUTES,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
)
from db import (
    clear_login_lock_state,
    consume_email_verification_token,
    consume_password_reset_token,
    create_email_verification_token,
    create_password_reset_token,
    create_session,
    delete_session,
    get_or_create_oauth_user,
    get_user_by_email,
    get_user_credentials_by_email,
    mark_email_verified,
    merge_users,
    register_failed_login_attempt,
    update_password,
    upgrade_anonymous_to_registered,
    verify_password,
)
from deps import clear_session_cookie, get_current_user, get_optional_current_user, set_csrf_cookie, set_session_cookie
from email_service import email_available, send_password_reset_email, send_verification_email
from middleware.request_context import get_request_id


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_RESERVED_EMAIL_PREFIXES: frozenset[str] = frozenset({
    "admin", "dev", "developer", "test", "tester",
    "automation", "auto", "author",
})

# OAuth state param length (random bytes for CSRF prevention stored in session cookie)
_OAUTH_STATE_BYTES = 16

# OAuth redirect URIs — provider will redirect back here after auth
def _oauth_callback_url(provider: str) -> str:
    return f"{APP_BASE_URL}/api/auth/oauth/{provider}/callback"


# ── Pydantic models ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address")
        local = value.split("@")[0]
        if local in _RESERVED_EMAIL_PREFIXES:
            raise ValueError("That email address is not available for registration")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError("Name must be 1-100 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        msg = "Password must be at least 8 characters and include uppercase, lowercase, and a number."
        if len(value) < 8:
            raise ValueError(msg)
        if not re.search(r"[A-Z]", value):
            raise ValueError(msg)
        if not re.search(r"[a-z]", value):
            raise ValueError(msg)
        if not re.search(r"[0-9]", value):
            raise ValueError(msg)
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class MagicLinkRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address")
        return value


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        msg = "Password must be at least 8 characters and include uppercase, lowercase, and a number."
        if len(value) < 8:
            raise ValueError(msg)
        if not re.search(r"[A-Z]", value):
            raise ValueError(msg)
        if not re.search(r"[a-z]", value):
            raise ValueError(msg)
        if not re.search(r"[0-9]", value):
            raise ValueError(msg)
        return value


# ── Helpers ───────────────────────────────────────────────────────────────────

def _err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "request_id": get_request_id()},
    )


# ── Standard auth ─────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    current_user: dict[str, str | None] = Depends(get_current_user),
) -> Response:
    if current_user.get("email"):
        return _err("Unable to create account. Please try again.")

    user = await upgrade_anonymous_to_registered(
        current_user["id"],
        body.email,
        body.name,
        body.password,
    )
    if user is None:
        return _err("Unable to create account. Please try again.")

    token = await create_session(user["id"])
    logger.info("[request_id=%s] Account created: user_id=%s", get_request_id(), user["id"])

    if email_available():
        verification_token = await create_email_verification_token(user["id"])
        sent = await send_verification_email(body.email, verification_token)
        if not sent:
            logger.error("[request_id=%s] Failed to send verification email: user_id=%s", get_request_id(), user["id"])
    else:
        logger.warning("[request_id=%s] RESEND_API_KEY not configured, skipping verification email", get_request_id())

    payload = JSONResponse(
        status_code=201,
        content={"user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"], "email_verified": user.get("email_verified", False)}},
    )
    set_session_cookie(payload, token)
    set_csrf_cookie(payload, secrets.token_urlsafe(24))
    return payload


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session_user: dict[str, str | None] | None = Depends(get_optional_current_user),
) -> Response:
    candidate = await get_user_credentials_by_email(body.email)
    now = datetime.now(timezone.utc)

    if candidate is not None and candidate.get("login_locked_until") is not None:
        locked_until = candidate["login_locked_until"]
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            logger.info(
                "[request_id=%s] Login blocked by lockout: email=%s locked_until=%s",
                get_request_id(),
                body.email,
                locked_until.isoformat(),
            )
            return _err("Too many failed sign-in attempts. Please try again in a few minutes.", status=429)

    if candidate is None or not candidate["pwd_hash"] or not candidate["pwd_salt"]:
        verify_password(body.password, "0" * 64, "0" * 64)
        return _err("Invalid email or password.", status=401)

    if not verify_password(body.password, candidate["pwd_hash"], candidate["pwd_salt"]):
        await register_failed_login_attempt(
            candidate["id"],
            current_failed_attempts=int(candidate.get("failed_login_attempts") or 0),
            max_attempts=LOGIN_LOCKOUT_MAX_ATTEMPTS,
            lockout_window_minutes=LOGIN_LOCKOUT_WINDOW_MINUTES,
        )
        refreshed = await get_user_credentials_by_email(body.email)
        if refreshed is not None and refreshed.get("login_locked_until") is not None:
            locked_until = refreshed["login_locked_until"]
            logger.info(
                "[request_id=%s] Login failure updated state: email=%s attempts=%s locked_until=%s",
                get_request_id(),
                body.email,
                refreshed.get("failed_login_attempts"),
                locked_until,
            )
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                return _err("Too many failed sign-in attempts. Please try again in a few minutes.", status=429)
        return _err("Invalid email or password.", status=401)

    await clear_login_lock_state(candidate["id"])

    if session_user and session_user["id"] != candidate["id"] and session_user.get("email") is None:
        await merge_users(session_user["id"], candidate["id"])

    existing_token = request.cookies.get("session_token")
    if existing_token:
        await delete_session(existing_token)

    token = await create_session(candidate["id"])
    logger.info("[request_id=%s] Sign-in: user_id=%s", get_request_id(), candidate["id"])
    payload = JSONResponse(
        content={"user": {"id": candidate["id"], "email": candidate["email"], "name": candidate["name"], "plan": candidate["plan"], "email_verified": candidate.get("email_verified", False)}}
    )
    set_session_cookie(payload, token)
    set_csrf_cookie(payload, secrets.token_urlsafe(24))
    return payload


@router.post("/logout")
async def logout(request: Request, response: Response) -> Response:
    session_token = request.cookies.get("session_token")
    if session_token:
        await delete_session(session_token)
    payload = JSONResponse(content={"ok": True})
    clear_session_cookie(payload)
    return payload


@router.get("/me")
async def me(session_user: dict[str, str | None] | None = Depends(get_optional_current_user)) -> JSONResponse:
    if session_user is None or session_user.get("email") is None:
        return JSONResponse(status_code=401, content={"user": None})
    return JSONResponse(
        content={"user": {"id": session_user["id"], "email": session_user["email"], "name": session_user["name"], "plan": session_user["plan"], "email_verified": session_user.get("email_verified", False)}}
    )


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest) -> JSONResponse:
    """Consume an email verification token and mark the account as verified."""
    user_id = await consume_email_verification_token(body.token)
    if user_id is None:
        return _err("This verification link is invalid or has expired.", status=400)
    await mark_email_verified(user_id)
    logger.info("[request_id=%s] Email verified: user_id=%s", get_request_id(), user_id)
    return JSONResponse(content={"ok": True})


@router.post("/resend-verification")
async def resend_verification(
    current_user: dict | None = Depends(get_optional_current_user),
) -> JSONResponse:
    """Resend the verification email. Always returns success to avoid timing attacks."""
    if current_user is None or current_user.get("email") is None:
        return JSONResponse(status_code=401, content={"error": "Not authenticated", "request_id": get_request_id()})

    if current_user.get("email_verified"):
        return JSONResponse(status_code=400, content={"error": "Email is already verified.", "request_id": get_request_id()})

    if not email_available():
        logger.warning("[request_id=%s] Resend-verification: RESEND_API_KEY not configured", get_request_id())
    else:
        token = await create_email_verification_token(current_user["id"])
        sent = await send_verification_email(current_user["email"], token)
        if sent:
            logger.info("[request_id=%s] Verification email resent: user_id=%s", get_request_id(), current_user["id"])
        else:
            logger.error("[request_id=%s] Failed to resend verification email: user_id=%s", get_request_id(), current_user["id"])

    return JSONResponse(content={"ok": True})


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest) -> JSONResponse:
    logger.info("[request_id=%s] Magic link requested (stub): email=%s", get_request_id(), body.email)
    return _err("Magic link sign-in is not yet available.", status=501)


# ── Password reset ────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest) -> JSONResponse:
    """Request a password reset email. Always returns success to prevent enumeration."""
    # Look up user — don't reveal whether the email exists
    user = await get_user_by_email(body.email)
    if user is not None:
        if not email_available():
            logger.warning(
                "[request_id=%s] Forgot-password: RESEND_API_KEY not configured, cannot send reset email",
                get_request_id(),
            )
        else:
            token = await create_password_reset_token(user["id"])
            sent = await send_password_reset_email(body.email, token)
            if sent:
                logger.info("[request_id=%s] Password reset email sent: user_id=%s", get_request_id(), user["id"])
            else:
                logger.error("[request_id=%s] Failed to send reset email: user_id=%s", get_request_id(), user["id"])
    else:
        logger.info("[request_id=%s] Forgot-password: no account for email %s", get_request_id(), body.email)

    # Always return success (prevent email enumeration)
    return JSONResponse(content={"ok": True})


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest) -> JSONResponse:
    """Consume a reset token and update the user's password."""
    user_id = await consume_password_reset_token(body.token)
    if user_id is None:
        return _err("This reset link is invalid or has expired. Please request a new one.", status=400)

    await update_password(user_id, body.password)
    await mark_email_verified(user_id)
    logger.info("[request_id=%s] Password reset: user_id=%s", get_request_id(), user_id)
    return JSONResponse(content={"ok": True})


# ── OAuth ─────────────────────────────────────────────────────────────────────

@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: str, request: Request) -> JSONResponse:
    """Return the OAuth authorization URL for the given provider."""
    import secrets as _secrets

    if provider == "google":
        if not GOOGLE_CLIENT_ID:
            return _err("Google sign-in is not configured.", status=503)
        state = _secrets.token_urlsafe(_OAUTH_STATE_BYTES)
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": _oauth_callback_url("google"),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
        }
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        return JSONResponse(content={"url": url, "state": state})

    if provider == "github":
        if not GITHUB_CLIENT_ID:
            return _err("GitHub sign-in is not configured.", status=503)
        state = _secrets.token_urlsafe(_OAUTH_STATE_BYTES)
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": _oauth_callback_url("github"),
            "scope": "user:email",
            "state": state,
        }
        url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
        return JSONResponse(content={"url": url, "state": state})

    if provider == "apple":
        return _err("Apple sign-in is not yet available.", status=503)

    return _err("Unknown provider.", status=404)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request) -> RedirectResponse:
    """Handle OAuth callback — exchange code for token, upsert user, set session."""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    frontend_base = (FRONTEND_BASE_URL or APP_BASE_URL or "http://localhost:5173").rstrip("/")

    def _redirect_error(msg: str) -> RedirectResponse:
        params = urllib.parse.urlencode({"error": msg})
        return RedirectResponse(url=f"{frontend_base}/auth?{params}", status_code=302)

    if error or not code:
        return _redirect_error("OAuth sign-in was cancelled or failed.")

    try:
        if provider == "google":
            user_info = await _exchange_google_code(code)
        elif provider == "github":
            user_info = await _exchange_github_code(code)
        else:
            return _redirect_error("Unknown OAuth provider.")
    except Exception:
        logger.exception("[request_id=%s] OAuth token exchange failed: provider=%s", get_request_id(), provider)
        return _redirect_error("Sign-in failed. Please try again.")

    if not user_info:
        return _redirect_error("Could not retrieve account information from provider.")

    user = await get_or_create_oauth_user(
        provider=provider,
        provider_user_id=user_info["id"],
        email=user_info.get("email"),
        name=user_info.get("name"),
    )

    token = await create_session(user["id"])
    logger.info("[request_id=%s] OAuth sign-in: provider=%s user_id=%s", get_request_id(), provider, user["id"])

    response = RedirectResponse(url=f"{frontend_base}/", status_code=302)
    set_session_cookie(response, token)
    set_csrf_cookie(response, secrets.token_urlsafe(24))
    return response


async def _exchange_google_code(code: str) -> dict | None:
    """Exchange Google auth code for user info."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": _oauth_callback_url("google"),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            return None
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return None

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            return None
        data = userinfo_resp.json()
        return {
            "id": data.get("id"),
            "email": data.get("email"),
            "name": data.get("name"),
        }


async def _exchange_github_code(code: str) -> dict | None:
    """Exchange GitHub auth code for user info."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _oauth_callback_url("github"),
            },
        )
        if token_resp.status_code != 200:
            return None
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return None

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        if user_resp.status_code != 200:
            return None
        data = user_resp.json()

        email = data.get("email")
        if not email:
            # GitHub users may hide their primary email; fetch via /user/emails
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            if emails_resp.status_code == 200:
                for entry in emails_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry["email"]
                        break

        return {
            "id": str(data.get("id")),
            "email": email,
            "name": data.get("name") or data.get("login"),
        }
