from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from config import ENV, SENTRY_DSN, SENTRY_RELEASE, SENTRY_TRACES_SAMPLE_RATE


logger = logging.getLogger(__name__)

_sentry_sdk = None


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Drop expected 4xx-style application errors before they reach Sentry."""

    exc_info = hint.get("exc_info")
    if exc_info and len(exc_info) >= 2:
        exc = exc_info[1]
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and 400 <= status_code < 500:
            return None
    return event


def init_sentry() -> bool:
    global _sentry_sdk

    if not SENTRY_DSN:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ModuleNotFoundError:
        logger.warning("SENTRY_DSN is set but sentry_sdk is not installed; skipping Sentry init")
        return False

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENV,
        release=SENTRY_RELEASE,
        integrations=[FastApiIntegration()],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        before_send=_before_send,
        send_default_pii=False,
    )
    _sentry_sdk = sentry_sdk
    return True


def sentry_enabled() -> bool:
    return _sentry_sdk is not None


def set_sentry_request_context(request: Request, request_id: str) -> None:
    if _sentry_sdk is None:
        return

    client_ip = request.client.host if request.client else None
    _sentry_sdk.set_tag("request_id", request_id)
    _sentry_sdk.set_tag("http.method", request.method)
    _sentry_sdk.set_tag("http.path", request.url.path)
    _sentry_sdk.set_context(
        "request_meta",
        {
            "path": request.url.path,
            "query_string": request.url.query or None,
            "client_ip": client_ip,
        },
    )


def set_sentry_user(user: dict[str, Any], *, is_authenticated: bool) -> None:
    if _sentry_sdk is None:
        return

    user_id = user.get("id")
    email = user.get("email")
    plan = user.get("plan")
    email_verified = user.get("email_verified")

    _sentry_sdk.set_user(
        {
            "id": str(user_id) if user_id is not None else None,
            "email": email,
        }
    )
    _sentry_sdk.set_tag("user.plan", str(plan) if plan is not None else "unknown")
    _sentry_sdk.set_tag("user.is_authenticated", "true" if is_authenticated else "false")
    if email_verified is not None:
        _sentry_sdk.set_tag("user.email_verified", "true" if email_verified else "false")

