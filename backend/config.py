from __future__ import annotations

import os
from pathlib import Path


def _getenv(name: str, default: str | None = None) -> str | None:
	value = os.getenv(name)
	if value is None or value.strip() == "":
		return default
	return value


def _get_int(name: str, default: str) -> int:
	value = _getenv(name, default)
	try:
		return int(value)  # type: ignore[arg-type]
	except (TypeError, ValueError) as exc:
		raise RuntimeError(f"{name} must be a valid integer") from exc


def _get_float(name: str, default: str) -> float:
	value = _getenv(name, default)
	try:
		return float(value)  # type: ignore[arg-type]
	except (TypeError, ValueError) as exc:
		raise RuntimeError(f"{name} must be a valid float") from exc


def _parse_origins(configured: str | None) -> list[str]:
	if configured:
		return [origin.strip() for origin in configured.split(",") if origin.strip()]
	return [
		"http://localhost:3000",
		"http://localhost:5173",
		"http://127.0.0.1:3000",
		"http://127.0.0.1:5173",
	]


# ---------------------------------------------------------------------------
# Paths used by SPA/static serving
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = Path(_getenv("FRONTEND_DIST_DIR", str(BACKEND_DIR.parent / "frontend" / "dist")))


# ---------------------------------------------------------------------------
# Environment / runtime settings
# ---------------------------------------------------------------------------

ENV = (_getenv("ENV", "development") or "development").strip().lower()

IS_DEV = ENV == "development"
IS_PROD = ENV == "production"

DATABASE_URL = _getenv("DATABASE_URL", "postgresql://localhost:5432/sql_practice")

# Razorpay (replaces Stripe — India-friendly)
RAZORPAY_KEY_ID = _getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = _getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = _getenv("RAZORPAY_WEBHOOK_SECRET")
# Subscription plan IDs (recurring) — created in Razorpay dashboard
RAZORPAY_PLAN_PRO   = _getenv("RAZORPAY_PLAN_PRO")
RAZORPAY_PLAN_ELITE = _getenv("RAZORPAY_PLAN_ELITE")
# Lifetime amounts are one-time Orders — amount in paise (₹1 = 100 paise)
RAZORPAY_AMOUNT_LIFETIME_PRO   = _get_int("RAZORPAY_AMOUNT_LIFETIME_PRO", "799900")   # ₹7999
RAZORPAY_AMOUNT_LIFETIME_ELITE = _get_int("RAZORPAY_AMOUNT_LIFETIME_ELITE", "1499900") # ₹14999
RAZORPAY_CURRENCY = _getenv("RAZORPAY_CURRENCY", "INR")

RAZORPAY_PLAN_PRO_USD              = _getenv("RAZORPAY_PLAN_PRO_USD")
RAZORPAY_PLAN_ELITE_USD            = _getenv("RAZORPAY_PLAN_ELITE_USD")
RAZORPAY_AMOUNT_LIFETIME_PRO_USD   = _get_int("RAZORPAY_AMOUNT_LIFETIME_PRO_USD", "8900")   # $89
RAZORPAY_AMOUNT_LIFETIME_ELITE_USD = _get_int("RAZORPAY_AMOUNT_LIFETIME_ELITE_USD", "16900") # $169

RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS", "60")
RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS", "60")
REDIS_URL = _getenv("REDIS_URL")

# Auth hardening
LOGIN_LOCKOUT_MAX_ATTEMPTS = _get_int("LOGIN_LOCKOUT_MAX_ATTEMPTS", "5")
LOGIN_LOCKOUT_WINDOW_MINUTES = _get_int("LOGIN_LOCKOUT_WINDOW_MINUTES", "15")

# Security
SECURE_COOKIES = (_getenv("SECURE_COOKIES", "true" if IS_PROD else "false") or "false").strip().lower() in {"1", "true", "yes", "on"}

# Observability
SENTRY_DSN = _getenv("SENTRY_DSN")
SENTRY_RELEASE = _getenv("SENTRY_RELEASE")
SENTRY_TRACES_SAMPLE_RATE = _get_float("SENTRY_TRACES_SAMPLE_RATE", "0.0")
VITE_SENTRY_DSN = _getenv("VITE_SENTRY_DSN")
VITE_POSTHOG_KEY = _getenv("VITE_POSTHOG_KEY")
VITE_POSTHOG_HOST = _getenv("VITE_POSTHOG_HOST")

# Frontend runtime config
VITE_BACKEND_URL = _getenv("VITE_BACKEND_URL")

# OAuth providers
GOOGLE_CLIENT_ID = _getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = _getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = _getenv("GITHUB_CLIENT_SECRET")

# Email / password reset
RESEND_API_KEY = _getenv("RESEND_API_KEY")
EMAIL_FROM = _getenv("EMAIL_FROM", "datanest <noreply@datanest.app>")

# Base URLs
# APP_BASE_URL: backend server base (used for OAuth callback URIs — must match what you register with providers)
# FRONTEND_BASE_URL: where to redirect users after OAuth (defaults to APP_BASE_URL in production single-service deploys)
APP_BASE_URL = _getenv("APP_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = _getenv("FRONTEND_BASE_URL", "http://localhost:5173")

_origins_raw = _getenv("ALLOWED_ORIGINS") or _getenv("CORS_ALLOW_ORIGINS")
ALLOWED_ORIGINS = _parse_origins(_origins_raw)


if ENV == "production" and not REDIS_URL:
	raise RuntimeError("REDIS_URL is required when ENV=production")

if ENV == "production" and not DATABASE_URL:
	raise RuntimeError("DATABASE_URL is required when ENV=production")

if ENV == "production" and not RAZORPAY_KEY_ID:
	raise RuntimeError("RAZORPAY_KEY_ID is required when ENV=production")

if ENV == "production" and not RAZORPAY_KEY_SECRET:
	raise RuntimeError("RAZORPAY_KEY_SECRET is required when ENV=production")

if ENV == "production" and not RAZORPAY_WEBHOOK_SECRET:
	raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is required when ENV=production")


def get_async_database_url() -> str:
	if DATABASE_URL is None:
		raise RuntimeError("DATABASE_URL is not configured")
	if DATABASE_URL.startswith("postgresql+asyncpg://"):
		return DATABASE_URL
	if DATABASE_URL.startswith("postgresql://"):
		return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
	return DATABASE_URL
