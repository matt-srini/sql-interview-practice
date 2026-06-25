from __future__ import annotations

import logging
import os
from pathlib import Path


def _getenv(name: str, default: str | None = None) -> str | None:
	value = os.getenv(name)
	if value is None or value.strip() == "":
		return default
	return value


def _stripped(v: str | None) -> str | None:
	"""Strip leading/trailing whitespace from a config string value.

	Pasted secrets often carry a trailing newline; stripping at read-time
	prevents silent HMAC mismatches that are hard to debug in production.
	None passes through unchanged.
	"""
	return v.strip() if isinstance(v, str) else v


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

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = Path(_getenv("FRONTEND_DIST_DIR", str(BACKEND_DIR.parent / "frontend" / "dist")))


# ---------------------------------------------------------------------------
# Environment / runtime settings
# ---------------------------------------------------------------------------

ENV = (_getenv("ENV", "development") or "development").strip().lower()

IS_DEV = ENV == "development"
IS_PROD = ENV == "production"

DATABASE_URL = _getenv("DATABASE_URL", "postgresql://localhost:5432/sql_practice")

# Postgres connection pool, per app replica (SQLAlchemy AsyncAdaptedQueuePool).
# Each request makes several short DB calls; once the event loop is no longer blocked
# by code execution (see offload.py), real request concurrency rises and the old
# default of 5 + 10 overflow became the next bottleneck. Defaults below give one
# replica up to DB_POOL_SIZE + DB_MAX_OVERFLOW connections — keep the total across all
# replicas comfortably under the managed-Postgres max_connections. DB_POOL_TIMEOUT is
# how long a request waits for a free connection before failing (fail fast → 503,
# rather than hang for the SQLAlchemy 30s default under saturation).
DB_POOL_SIZE = _get_int("DB_POOL_SIZE", "10")
DB_MAX_OVERFLOW = _get_int("DB_MAX_OVERFLOW", "20")
DB_POOL_TIMEOUT = _get_int("DB_POOL_TIMEOUT", "10")
DB_POOL_RECYCLE_SECONDS = _get_int("DB_POOL_RECYCLE_SECONDS", "1800")

# Razorpay (replaces Stripe — India-friendly)
RAZORPAY_KEY_ID = _stripped(_getenv("RAZORPAY_KEY_ID"))
RAZORPAY_KEY_SECRET = _stripped(_getenv("RAZORPAY_KEY_SECRET"))
RAZORPAY_WEBHOOK_SECRET = _stripped(_getenv("RAZORPAY_WEBHOOK_SECRET"))
# Subscription plan IDs (recurring) — created in Razorpay dashboard
RAZORPAY_PLAN_PRO   = _stripped(_getenv("RAZORPAY_PLAN_PRO"))
RAZORPAY_PLAN_ELITE = _stripped(_getenv("RAZORPAY_PLAN_ELITE"))
# Lifetime amounts are one-time Orders — amount in paise (₹1 = 100 paise)
RAZORPAY_AMOUNT_LIFETIME_PRO   = _get_int("RAZORPAY_AMOUNT_LIFETIME_PRO", "1199900")  # ₹11,999
RAZORPAY_AMOUNT_LIFETIME_ELITE = _get_int("RAZORPAY_AMOUNT_LIFETIME_ELITE", "1999900") # ₹19,999
RAZORPAY_CURRENCY = _getenv("RAZORPAY_CURRENCY", "INR")

RAZORPAY_PLAN_PRO_USD              = _getenv("RAZORPAY_PLAN_PRO_USD")
RAZORPAY_PLAN_ELITE_USD            = _getenv("RAZORPAY_PLAN_ELITE_USD")
RAZORPAY_AMOUNT_LIFETIME_PRO_USD   = _get_int("RAZORPAY_AMOUNT_LIFETIME_PRO_USD", "14900")  # $149
RAZORPAY_AMOUNT_LIFETIME_ELITE_USD = _get_int("RAZORPAY_AMOUNT_LIFETIME_ELITE_USD", "24900") # $249

# Paddle (global rail — Merchant of Record for non-INR customers).
# India checks out through Razorpay above; the rest of the world goes through
# Paddle, which is the Merchant of Record and collects + remits global VAT/GST/
# sales tax on our behalf. All values are unset by default, so the Paddle
# endpoints return 503 until configured — exactly like the Razorpay USD plan IDs.
PADDLE_ENVIRONMENT      = (_getenv("PADDLE_ENVIRONMENT", "sandbox") or "sandbox").strip().lower()
PADDLE_CLIENT_TOKEN     = _stripped(_getenv("PADDLE_CLIENT_TOKEN"))     # client-side token for Paddle.js
PADDLE_API_KEY          = _stripped(_getenv("PADDLE_API_KEY"))          # server-side API key (reserved — cancel/portal later)
PADDLE_WEBHOOK_SECRET   = _stripped(_getenv("PADDLE_WEBHOOK_SECRET"))   # notification-destination signing secret
# Price IDs (USD) from the Paddle catalog — recurring (pro/elite) + one-time (lifetime_*)
PADDLE_PRICE_PRO            = _stripped(_getenv("PADDLE_PRICE_PRO"))
PADDLE_PRICE_ELITE          = _stripped(_getenv("PADDLE_PRICE_ELITE"))
PADDLE_PRICE_LIFETIME_PRO   = _stripped(_getenv("PADDLE_PRICE_LIFETIME_PRO"))
PADDLE_PRICE_LIFETIME_ELITE = _stripped(_getenv("PADDLE_PRICE_LIFETIME_ELITE"))

RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS", "60")
RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS", "60")
REDIS_URL = _getenv("REDIS_URL")

# Auth endpoint-specific rate limits
AUTH_RATE_LIMIT_REQUESTS = _get_int("AUTH_RATE_LIMIT_REQUESTS", "20")
AUTH_RATE_LIMIT_WINDOW_SECONDS = _get_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
AUTH_TOKEN_ISSUE_RATE_LIMIT_REQUESTS = _get_int("AUTH_TOKEN_ISSUE_RATE_LIMIT_REQUESTS", "5")
AUTH_TOKEN_ISSUE_RATE_LIMIT_WINDOW_SECONDS = _get_int("AUTH_TOKEN_ISSUE_RATE_LIMIT_WINDOW_SECONDS", "300")

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

# Base URLs
# APP_BASE_URL: backend server base (used for OAuth callback URIs — must match what you register with providers)
# FRONTEND_BASE_URL: where to redirect users after OAuth (defaults to APP_BASE_URL in production single-service deploys)
APP_BASE_URL = _getenv("APP_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = _getenv("FRONTEND_BASE_URL", "http://localhost:5173")
CANONICAL_BASE_URL = _getenv("CANONICAL_BASE_URL", "https://datathink.co")

# OAuth providers
GOOGLE_CLIENT_ID = _getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = _getenv("GOOGLE_REDIRECT_URI")
GITHUB_CLIENT_ID = _getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = _getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = _getenv("GITHUB_REDIRECT_URI")

# Admin operations (grant plan overrides, etc.)
# Set a strong random value in production: python -c "import secrets; print(secrets.token_urlsafe(32))"
ADMIN_SECRET = _getenv("ADMIN_SECRET")

# Email / password reset
RESEND_API_KEY = _getenv("RESEND_API_KEY")
EMAIL_FROM = _getenv("EMAIL_FROM", "datathink <noreply@datathink.co>")
MAGIC_LINK_TTL_MINUTES = _get_int("MAGIC_LINK_TTL_MINUTES", "10")
OAUTH_STATE_TTL_MINUTES = _get_int("OAUTH_STATE_TTL_MINUTES", "5")

_origins_raw = _getenv("ALLOWED_ORIGINS") or _getenv("CORS_ALLOW_ORIGINS")
ALLOWED_ORIGINS = _parse_origins(_origins_raw)

if (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET) and not GOOGLE_REDIRECT_URI:
	if IS_PROD:
		raise RuntimeError("GOOGLE_REDIRECT_URI is required when Google OAuth is configured in production")
	logger.warning("GOOGLE_REDIRECT_URI is not set; Google OAuth may fail with redirect_uri_mismatch")

if (GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET) and not GITHUB_REDIRECT_URI:
	if IS_PROD:
		raise RuntimeError("GITHUB_REDIRECT_URI is required when GitHub OAuth is configured in production")
	logger.warning("GITHUB_REDIRECT_URI is not set; GitHub OAuth may fail with redirect_uri_mismatch")


def validate_production_config() -> None:
	"""Assert that all required env vars are set when running in production.

	Called once at module import so a misconfigured deploy fails loudly at
	startup rather than silently at the first request.  The function reads
	module-level config vars so it can be unit-tested by monkeypatching them
	(e.g. ``monkeypatch.setattr('config.PADDLE_CLIENT_TOKEN', 'live_x')``).

	Non-production environments are left entirely unchecked — importing
	``config`` in tests never raises here.
	"""
	if ENV != "production":
		return

	# ── Infrastructure ────────────────────────────────────────────────────────
	if not REDIS_URL:
		raise RuntimeError("REDIS_URL is required when ENV=production")

	if not DATABASE_URL:
		raise RuntimeError("DATABASE_URL is required when ENV=production")

	# ── Razorpay (always required in production) ──────────────────────────────
	if not RAZORPAY_KEY_ID:
		raise RuntimeError("RAZORPAY_KEY_ID is required when ENV=production")

	if not RAZORPAY_KEY_SECRET:
		raise RuntimeError("RAZORPAY_KEY_SECRET is required when ENV=production")

	if not RAZORPAY_WEBHOOK_SECRET:
		raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is required when ENV=production")

	# ── Razorpay subscription plan IDs (required for Pro/Elite subscribe flow) ─
	# Without these the subscription-create endpoint 500s at runtime.
	if not RAZORPAY_PLAN_PRO:
		raise RuntimeError("RAZORPAY_PLAN_PRO is required when ENV=production")

	if not RAZORPAY_PLAN_ELITE:
		raise RuntimeError("RAZORPAY_PLAN_ELITE is required when ENV=production")

	# ── Transactional email (password reset + email verification) ─────────────
	if not RESEND_API_KEY:
		raise RuntimeError("RESEND_API_KEY is required when ENV=production")

	# ── Admin secret (plan override operations) ───────────────────────────────
	# Must be set AND at least 32 characters (CLAUDE.md: "strong random value, ≥32 bytes").
	if not ADMIN_SECRET:
		raise RuntimeError("ADMIN_SECRET is required when ENV=production")
	if len(ADMIN_SECRET) < 32:
		raise RuntimeError(
			"ADMIN_SECRET must be at least 32 characters when ENV=production"
		)

	# ── Paddle (only required when the Paddle rail is enabled) ───────────────
	# Gate on PADDLE_CLIENT_TOKEN: if that is set, Paddle is live and the
	# rest of its config must be complete.  INR-only deploys leave all Paddle
	# vars unset and boot without error.
	if PADDLE_CLIENT_TOKEN:
		if not PADDLE_WEBHOOK_SECRET:
			raise RuntimeError(
				"PADDLE_WEBHOOK_SECRET is required when PADDLE_CLIENT_TOKEN is set"
			)

		missing_prices = [
			name
			for name, val in (
				("PADDLE_PRICE_PRO", PADDLE_PRICE_PRO),
				("PADDLE_PRICE_ELITE", PADDLE_PRICE_ELITE),
				("PADDLE_PRICE_LIFETIME_PRO", PADDLE_PRICE_LIFETIME_PRO),
				("PADDLE_PRICE_LIFETIME_ELITE", PADDLE_PRICE_LIFETIME_ELITE),
			)
			if not val
		]
		if missing_prices:
			raise RuntimeError(
				f"The following Paddle price IDs are required when PADDLE_CLIENT_TOKEN is set: "
				f"{', '.join(missing_prices)}"
			)

		if PADDLE_ENVIRONMENT != "production":
			raise RuntimeError(
				f'PADDLE_ENVIRONMENT must be "production" when Paddle is live; '
				f'got "{PADDLE_ENVIRONMENT}"'
			)


validate_production_config()


def get_async_database_url() -> str:
	if DATABASE_URL is None:
		raise RuntimeError("DATABASE_URL is not configured")
	if DATABASE_URL.startswith("postgresql+asyncpg://"):
		return DATABASE_URL
	if DATABASE_URL.startswith("postgresql://"):
		return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
	return DATABASE_URL
