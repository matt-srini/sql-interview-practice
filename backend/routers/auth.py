from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from db import create_session, delete_session, get_user_credentials_by_email, merge_users
from db import upgrade_anonymous_to_registered, verify_password
from deps import clear_session_cookie, get_current_user, get_optional_current_user, set_session_cookie
from middleware.request_context import get_request_id


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
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


def _err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "request_id": get_request_id()},
    )


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
    logger.info(
        "[request_id=%s] Account created: user_id=%s",
        get_request_id(),
        user["id"],
    )
    payload = JSONResponse(
        status_code=201,
        content={"user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"]}},
    )
    set_session_cookie(payload, token)
    return payload


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session_user: dict[str, str | None] | None = Depends(get_optional_current_user),
) -> Response:
    candidate = await get_user_credentials_by_email(body.email)
    if candidate is None or not candidate["pwd_hash"] or not candidate["pwd_salt"]:
        verify_password(body.password, "0" * 64, "0" * 64)
        return _err("Invalid email or password.", status=401)

    if not verify_password(body.password, candidate["pwd_hash"], candidate["pwd_salt"]):
        return _err("Invalid email or password.", status=401)

    if session_user and session_user["id"] != candidate["id"] and session_user.get("email") is None:
        await merge_users(session_user["id"], candidate["id"])

    existing_token = request.cookies.get("session_token")
    if existing_token:
        await delete_session(existing_token)

    token = await create_session(candidate["id"])
    logger.info(
        "[request_id=%s] Sign-in: user_id=%s",
        get_request_id(),
        candidate["id"],
    )
    payload = JSONResponse(
        content={"user": {"id": candidate["id"], "email": candidate["email"], "name": candidate["name"], "plan": candidate["plan"]}}
    )
    set_session_cookie(payload, token)
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
        content={"user": {"id": session_user["id"], "email": session_user["email"], "name": session_user["name"], "plan": session_user["plan"]}}
    )


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest) -> JSONResponse:
    logger.info(
        "[request_id=%s] Magic link requested (stub, not sent): email=%s",
        get_request_id(),
        body.email,
    )
    return _err("Magic link sign-in is not yet available.", status=501)


@router.get("/oauth/{provider}")
async def oauth_redirect(provider: str) -> JSONResponse:
    supported = {"google", "github", "apple"}
    if provider not in supported:
        return _err("Unknown provider.", status=404)
    logger.info(
        "[request_id=%s] OAuth redirect requested (stub): provider=%s",
        get_request_id(),
        provider,
    )
    return _err(f"{provider.capitalize()} sign-in is not yet available.", status=501)
