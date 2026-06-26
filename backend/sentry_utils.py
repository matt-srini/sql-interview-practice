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
        # Boot-check: a production deploy with no DSN means the backend is
        # silently NOT capturing errors — the exact failure mode where you only
        # find out when an error you needed never showed up in Sentry. Make it
        # loud in the logs. (Not boot-FATAL: Sentry being down must not take the
        # app down — a warning is the right severity.)
        if ENV == "production":
            logger.warning(
                "Sentry DISABLED in production — SENTRY_DSN is not set; "
                "backend errors are NOT being captured"
            )
        else:
            logger.info("Sentry disabled (no SENTRY_DSN; ENV=%s)", ENV)
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
    # Confirms the backend is reporting, and surfaces the release (so a missing
    # SENTRY_RELEASE shows as "unset" rather than silently breaking regression
    # auto-reopen) and the traces rate — all visible in the Railway boot log.
    logger.info(
        "Sentry initialized (environment=%s, release=%s, traces_sample_rate=%s)",
        ENV,
        SENTRY_RELEASE or "unset",
        SENTRY_TRACES_SAMPLE_RATE,
    )
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


def capture_payment_failure(
    message: str,
    *,
    stage: str,
    provider: str | None = None,
    user_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Capture a payment-critical failure as a Sentry error-level message.

    Always no-ops when Sentry is not initialised (SENTRY_DSN unset / sdk missing).

    Tags set on every call:
      alert=payment_failure   — used as the single alert-rule filter
      payment_stage=<stage>   — e.g. "webhook_signature", "plan_resolution",
                                "plan_persist", "cancel", "switch_now"
      payment_provider=<provider>  — "razorpay" | "paddle" | None

    ``extra`` may contain non-sensitive context (event_id, event_type, resolved
    plan tier, error class name).  NEVER include secrets, raw signatures, card data,
    or PII beyond user_id.
    """
    if _sentry_sdk is None:
        return

    with _sentry_sdk.push_scope() as scope:
        scope.set_tag("alert", "payment_failure")
        scope.set_tag("payment_stage", stage)
        if provider is not None:
            scope.set_tag("payment_provider", provider)
        if user_id is not None:
            scope.set_user({"id": str(user_id)})
        if extra:
            scope.set_context("payment_failure_detail", extra)
        _sentry_sdk.capture_message(message, level="error", scope=scope)


def capture_sandbox_failure(
    message: str,
    *,
    mode: str | None = None,
    returncode: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Capture a sandbox harness infra-failure as a Sentry error-level event.

    A non-zero harness subprocess exit (OOM / OpenBLAS abort / segfault / RLIMIT kill)
    is returned to the client as a normal HTTP 200 {error} body -- NOT a 5xx, NOT an
    exception -- so without this explicit capture it is invisible to Sentry. (This is
    the exact blind spot that hid the 2026-06 OpenBLAS RLIMIT_AS abort: 0 Sentry hits
    in 90 days.) No-ops when Sentry is not initialised.

    Tags: alert=sandbox_failure (single alert-rule filter), sandbox_mode, sandbox_rc.
    """
    if _sentry_sdk is None:
        return

    with _sentry_sdk.push_scope() as scope:
        scope.set_tag("alert", "sandbox_failure")
        if mode is not None:
            scope.set_tag("sandbox_mode", str(mode))
        if returncode is not None:
            scope.set_tag("sandbox_rc", str(returncode))
        if extra:
            scope.set_context("sandbox_failure_detail", extra)
        _sentry_sdk.capture_message(message, level="error", scope=scope)


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

