"""
Auth router.

Fully implemented (email / password via Python stdlib, no external deps):
    POST  /api/auth/register         Create a new account
    POST  /api/auth/login            Sign in with email + password
    POST  /api/auth/logout           Invalidate the session cookie
    GET   /api/auth/me               Return the current session user

Seam stubs — return HTTP 501 until external infrastructure is configured:
    POST  /api/auth/magic-link       Requires email-delivery infrastructure
    GET   /api/auth/oauth/{provider} Requires registered OAuth app credentials

Security notes:
  - Login always returns the same generic error regardless of whether the
    email exists (no account enumeration).
  - Passwords: PBKDF2-HMAC-SHA256, 260 000 iterations, 32-byte random salt.
  - Sessions: 256-bit URL-safe random tokens in an HttpOnly, SameSite=Lax cookie.
  - Stack traces never reach the client (handled by the global exception handler
    in main.py).
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Cookie, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

import auth_db
from config import IS_PROD
from middleware.request_context import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SESSION_COOKIE = "auth_session"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 100:
            raise ValueError("Name must be 1–100 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class MagicLinkRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=IS_PROD,   # HTTPS-only in production
        max_age=30 * 24 * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=_SESSION_COOKIE, path="/")


def _err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "request_id": get_request_id()},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, response: Response) -> JSONResponse:
    user = auth_db.create_user(body.email, body.name, body.password)
    if user is None:
        # Generic message — do not reveal whether the email already exists.
        return _err("Unable to create account. Please try again.")

    token = auth_db.create_session(user["user_id"])
    _set_session_cookie(response, token)
    logger.info(
        "[request_id=%s] Account created: user_id=%s",
        get_request_id(),
        user["user_id"],
    )
    return JSONResponse(
        status_code=201,
        content={"user": {"email": user["email"], "name": user["name"]}},
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response) -> JSONResponse:
    user = auth_db.verify_credentials(body.email, body.password)
    if user is None:
        # Single generic message regardless of whether the email exists.
        return _err("Invalid email or password.", status=401)

    token = auth_db.create_session(user["user_id"])
    _set_session_cookie(response, token)
    logger.info(
        "[request_id=%s] Sign-in: user_id=%s",
        get_request_id(),
        user["user_id"],
    )
    return JSONResponse(
        content={"user": {"email": user["email"], "name": user["name"]}}
    )


@router.post("/logout")
async def logout(
    response: Response,
    auth_session: str | None = Cookie(default=None),
) -> JSONResponse:
    if auth_session:
        auth_db.delete_session(auth_session)
    _clear_session_cookie(response)
    return JSONResponse(content={"ok": True})


@router.get("/me")
async def me(
    auth_session: str | None = Cookie(default=None),
) -> JSONResponse:
    if not auth_session:
        return JSONResponse(status_code=401, content={"user": None})
    user = auth_db.get_session_user(auth_session)
    if user is None:
        return JSONResponse(status_code=401, content={"user": None})
    return JSONResponse(content={"user": {"email": user["email"], "name": user["name"]}})


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest) -> JSONResponse:
    """
    Seam: magic-link delivery requires email infrastructure (SMTP / transactional API).
    Returns 501 until configured.

    Frontend integration note: always show a success-like UI message to avoid
    email enumeration (do not reveal whether the address is registered).
    """
    logger.info(
        "[request_id=%s] Magic link requested (stub, not sent): email=%s",
        get_request_id(),
        body.email,
    )
    return _err("Magic link sign-in is not yet available.", status=501)


@router.get("/oauth/{provider}")
async def oauth_redirect(provider: str) -> JSONResponse:
    """
    Seam: OAuth flows require registered app credentials per provider.
    Returns 501 until configured.

    Implementation note: when ready, validate `provider`, build the OAuth
    authorization URL, and return a 302 redirect to the provider's auth host.
    """
    supported = {"google", "github", "apple"}
    if provider not in supported:
        return _err("Unknown provider.", status=404)
    logger.info(
        "[request_id=%s] OAuth redirect requested (stub): provider=%s",
        get_request_id(),
        provider,
    )
    return _err(
        f"{provider.capitalize()} sign-in is not yet available.", status=501
    )
