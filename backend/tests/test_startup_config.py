"""Unit tests for config.validate_production_config().

Each test patches module-level vars in ``config`` and calls
``config.validate_production_config()`` directly — no server startup needed.

The ``_prod_base`` fixture provides a minimal set of valid production values
(infra + Razorpay) so individual Paddle tests only need to patch the vars
relevant to the rule under test.
"""
import sys
import os
from pathlib import Path

# Ensure backend root is on sys.path (mirrors conftest.py bootstrap)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Set TESTING so config import doesn't fire prod guards
os.environ.setdefault("TESTING", "1")

import pytest
import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PROD_BASE = {
    "config.ENV": "production",
    "config.REDIS_URL": "redis://localhost:6379/0",
    "config.DATABASE_URL": "postgresql://localhost:5432/sql_practice",
    "config.RAZORPAY_KEY_ID": "rzp_live_key",
    "config.RAZORPAY_KEY_SECRET": "rzp_live_secret",
    "config.RAZORPAY_WEBHOOK_SECRET": "rzp_whsec",
}

_VALID_PADDLE = {
    "config.PADDLE_CLIENT_TOKEN": "live_client_token",
    "config.PADDLE_WEBHOOK_SECRET": "pdl_whsec",
    "config.PADDLE_PRICE_PRO": "pri_pro",
    "config.PADDLE_PRICE_ELITE": "pri_elite",
    "config.PADDLE_PRICE_LIFETIME_PRO": "pri_lt_pro",
    "config.PADDLE_PRICE_LIFETIME_ELITE": "pri_lt_elite",
    "config.PADDLE_ENVIRONMENT": "production",
}


def _apply(monkeypatch, patches: dict) -> None:
    for attr, value in patches.items():
        monkeypatch.setattr(attr, value)


# ---------------------------------------------------------------------------
# (a) Paddle fully + correctly configured → no raise
# ---------------------------------------------------------------------------

def test_paddle_fully_configured_no_raise(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, **_VALID_PADDLE})
    config.validate_production_config()  # must not raise


# ---------------------------------------------------------------------------
# (b) PADDLE_CLIENT_TOKEN set, PADDLE_WEBHOOK_SECRET missing → raises
# ---------------------------------------------------------------------------

def test_paddle_missing_webhook_secret_raises(monkeypatch):
    _apply(monkeypatch, {
        **_VALID_PROD_BASE,
        **_VALID_PADDLE,
        "config.PADDLE_WEBHOOK_SECRET": None,
    })
    with pytest.raises(RuntimeError, match="PADDLE_WEBHOOK_SECRET"):
        config.validate_production_config()


# ---------------------------------------------------------------------------
# (c) PADDLE_CLIENT_TOKEN set, PADDLE_ENVIRONMENT != 'production' → raises
# ---------------------------------------------------------------------------

def test_paddle_wrong_environment_raises(monkeypatch):
    _apply(monkeypatch, {
        **_VALID_PROD_BASE,
        **_VALID_PADDLE,
        "config.PADDLE_ENVIRONMENT": "sandbox",
    })
    with pytest.raises(RuntimeError, match="PADDLE_ENVIRONMENT"):
        config.validate_production_config()


def test_paddle_empty_environment_raises(monkeypatch):
    """An accidental blank/missing PADDLE_ENVIRONMENT defaults to 'sandbox' — still raises."""
    _apply(monkeypatch, {
        **_VALID_PROD_BASE,
        **_VALID_PADDLE,
        "config.PADDLE_ENVIRONMENT": "sandbox",
    })
    with pytest.raises(RuntimeError, match="PADDLE_ENVIRONMENT"):
        config.validate_production_config()


# ---------------------------------------------------------------------------
# (d) PADDLE_CLIENT_TOKEN set, one PADDLE_PRICE_* missing → raises
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing_var", [
    "config.PADDLE_PRICE_PRO",
    "config.PADDLE_PRICE_ELITE",
    "config.PADDLE_PRICE_LIFETIME_PRO",
    "config.PADDLE_PRICE_LIFETIME_ELITE",
])
def test_paddle_missing_price_raises(monkeypatch, missing_var):
    patches = {**_VALID_PROD_BASE, **_VALID_PADDLE, missing_var: None}
    _apply(monkeypatch, patches)
    # Extract the bare var name for the match (e.g. 'PADDLE_PRICE_PRO')
    bare = missing_var.split(".")[-1]
    with pytest.raises(RuntimeError, match=bare):
        config.validate_production_config()


# ---------------------------------------------------------------------------
# (e) PADDLE_CLIENT_TOKEN is None → no raise even when other Paddle vars missing
# ---------------------------------------------------------------------------

def test_paddle_client_token_absent_no_paddle_requirements(monkeypatch):
    """INR-only deploy: Paddle completely unset, all Paddle price vars missing → OK."""
    _apply(monkeypatch, {
        **_VALID_PROD_BASE,
        "config.PADDLE_CLIENT_TOKEN": None,
        "config.PADDLE_WEBHOOK_SECRET": None,
        "config.PADDLE_PRICE_PRO": None,
        "config.PADDLE_PRICE_ELITE": None,
        "config.PADDLE_PRICE_LIFETIME_PRO": None,
        "config.PADDLE_PRICE_LIFETIME_ELITE": None,
        "config.PADDLE_ENVIRONMENT": "sandbox",  # default — must not matter when token absent
    })
    config.validate_production_config()  # must not raise


# ---------------------------------------------------------------------------
# Existing infra + Razorpay guards still fire (regression coverage)
# ---------------------------------------------------------------------------

def test_missing_redis_raises(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, "config.REDIS_URL": None})
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        config.validate_production_config()


def test_missing_database_url_raises(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, "config.DATABASE_URL": None})
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        config.validate_production_config()


def test_missing_razorpay_key_id_raises(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, "config.RAZORPAY_KEY_ID": None})
    with pytest.raises(RuntimeError, match="RAZORPAY_KEY_ID"):
        config.validate_production_config()


def test_missing_razorpay_key_secret_raises(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, "config.RAZORPAY_KEY_SECRET": None})
    with pytest.raises(RuntimeError, match="RAZORPAY_KEY_SECRET"):
        config.validate_production_config()


def test_missing_razorpay_webhook_secret_raises(monkeypatch):
    _apply(monkeypatch, {**_VALID_PROD_BASE, "config.RAZORPAY_WEBHOOK_SECRET": None})
    with pytest.raises(RuntimeError, match="RAZORPAY_WEBHOOK_SECRET"):
        config.validate_production_config()


# ---------------------------------------------------------------------------
# Non-production env — nothing raises even with everything unset
# ---------------------------------------------------------------------------

def test_dev_env_no_raise(monkeypatch):
    monkeypatch.setattr("config.ENV", "development")
    # All production vars intentionally absent — should be a no-op
    config.validate_production_config()


def test_test_env_no_raise(monkeypatch):
    monkeypatch.setattr("config.ENV", "test")
    config.validate_production_config()
