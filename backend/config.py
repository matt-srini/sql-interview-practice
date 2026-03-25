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
STRIPE_SECRET_KEY = _getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = _getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_PRO = _getenv("STRIPE_PRICE_PRO")
STRIPE_PRICE_ELITE = _getenv("STRIPE_PRICE_ELITE")

RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS", "60")
RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS", "60")
REDIS_URL = _getenv("REDIS_URL")

_origins_raw = _getenv("ALLOWED_ORIGINS") or _getenv("CORS_ALLOW_ORIGINS")
ALLOWED_ORIGINS = _parse_origins(_origins_raw)


if ENV == "production" and not REDIS_URL:
	raise RuntimeError("REDIS_URL is required when ENV=production")

if ENV == "production" and not DATABASE_URL:
	raise RuntimeError("DATABASE_URL is required when ENV=production")

if ENV == "production" and not STRIPE_SECRET_KEY:
	raise RuntimeError("STRIPE_SECRET_KEY is required when ENV=production")

if ENV == "production" and not STRIPE_WEBHOOK_SECRET:
	raise RuntimeError("STRIPE_WEBHOOK_SECRET is required when ENV=production")


def get_async_database_url() -> str:
	if DATABASE_URL is None:
		raise RuntimeError("DATABASE_URL is not configured")
	if DATABASE_URL.startswith("postgresql+asyncpg://"):
		return DATABASE_URL
	if DATABASE_URL.startswith("postgresql://"):
		return DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
	return DATABASE_URL
