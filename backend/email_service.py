"""Email sending via Resend API.

All functions are no-ops when RESEND_API_KEY is not set — callers must check
``email_available()`` before deciding whether to proceed or degrade gracefully.
"""
from __future__ import annotations

import logging

import httpx

from config import _getenv

logger = logging.getLogger(__name__)

RESEND_API_KEY: str | None = _getenv("RESEND_API_KEY")
EMAIL_FROM: str = _getenv("EMAIL_FROM", "datathink <noreply@datathink.co>") or "datathink <noreply@datathink.co>"
# Use FRONTEND_BASE_URL for links in emails so they go to the right place
FRONTEND_BASE_URL: str = _getenv("FRONTEND_BASE_URL", _getenv("APP_BASE_URL", "http://localhost:5173")) or "http://localhost:5173"

_RESEND_SEND_URL = "https://api.resend.com/emails"


def email_available() -> bool:
    return bool(RESEND_API_KEY)


async def send_verification_email(to_email: str, verification_token: str) -> bool:
    """Send an email verification link. Returns True on success, False on failure."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping verification email to %s", to_email)
        return False

    verify_url = f"{FRONTEND_BASE_URL.rstrip('/')}/auth/verify-email?token={verification_token}"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Inter, -apple-system, sans-serif; background: #F7F7F5; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 40px; border: 1px solid #E5E3DE;">
    <h1 style="font-size: 1.4rem; font-weight: 700; color: #1A1A18; margin: 0 0 8px;">Verify your email</h1>
    <p style="color: #6B6862; line-height: 1.6; margin: 0 0 24px;">
      Click the button below to verify your email address for datathink.
      This link expires in <strong>24 hours</strong>.
    </p>
    <a href="{verify_url}"
       style="display: inline-block; background: #5B6AF0; color: #fff; text-decoration: none;
              padding: 14px 28px; border-radius: 12px; font-weight: 600; font-size: 0.95rem;">
      Verify email address
    </a>
    <p style="color: #9B9790; font-size: 0.82rem; margin: 24px 0 0; line-height: 1.5;">
      If you didn't create a datathink account, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #E5E3DE; margin: 24px 0;">
    <p style="color: #9B9790; font-size: 0.78rem; margin: 0;">
      datathink &mdash; Data interview practice
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Verify your datathink email\n\n"
        f"Click the link below to verify your email address (expires in 24 hours):\n\n"
        f"{verify_url}\n\n"
        f"If you didn't create a datathink account, ignore this email."
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _RESEND_SEND_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": EMAIL_FROM,
                    "to": [to_email],
                    "subject": "Verify your datathink email",
                    "html": html_body,
                    "text": text_body,
                },
            )
        if resp.status_code in (200, 201):
            logger.info("Verification email sent to %s", to_email)
            return True
        logger.error("Resend API error %s: %s", resp.status_code, resp.text)
        return False
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)
        return False


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset email. Returns True on success, False on failure."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping password reset email to %s", to_email)
        return False

    reset_url = f"{FRONTEND_BASE_URL.rstrip('/')}/auth/reset-password?token={reset_token}"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Inter, -apple-system, sans-serif; background: #F7F7F5; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 40px; border: 1px solid #E5E3DE;">
    <h1 style="font-size: 1.4rem; font-weight: 700; color: #1A1A18; margin: 0 0 8px;">Reset your password</h1>
    <p style="color: #6B6862; line-height: 1.6; margin: 0 0 24px;">
      Click the button below to set a new password for your datathink account.
      This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #5B6AF0; color: #fff; text-decoration: none;
              padding: 14px 28px; border-radius: 12px; font-weight: 600; font-size: 0.95rem;">
      Reset password
    </a>
    <p style="color: #9B9790; font-size: 0.82rem; margin: 24px 0 0; line-height: 1.5;">
      If you didn't request this, you can ignore this email — your password won't change.
      <br>The link will expire automatically.
    </p>
    <hr style="border: none; border-top: 1px solid #E5E3DE; margin: 24px 0;">
    <p style="color: #9B9790; font-size: 0.78rem; margin: 0;">
      datathink &mdash; Data interview practice
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Reset your datathink password\n\n"
        f"Click the link below to set a new password (expires in 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, ignore this email."
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _RESEND_SEND_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": EMAIL_FROM,
                    "to": [to_email],
                    "subject": "Reset your datathink password",
                    "html": html_body,
                    "text": text_body,
                },
            )
        if resp.status_code in (200, 201):
            logger.info("Password reset email sent to %s", to_email)
            return True
        logger.error("Resend API error %s: %s", resp.status_code, resp.text)
        return False
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
