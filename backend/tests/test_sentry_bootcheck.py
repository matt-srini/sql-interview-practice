"""Boot-check: init_sentry() must make a dark-in-production deploy loud.

Guards the exact failure mode where SENTRY_DSN is missing in production and the
backend silently stops capturing errors — you only notice when an error you
needed never reached Sentry.
"""
import logging

import sentry_utils


def test_init_sentry_warns_when_dsn_missing_in_production(monkeypatch, caplog):
    monkeypatch.setattr(sentry_utils, "SENTRY_DSN", "")
    monkeypatch.setattr(sentry_utils, "ENV", "production")
    monkeypatch.setattr(sentry_utils, "_sentry_sdk", None)

    with caplog.at_level(logging.WARNING, logger="sentry_utils"):
        result = sentry_utils.init_sentry()

    assert result is False
    assert "Sentry DISABLED in production" in caplog.text


def test_init_sentry_quiet_when_dsn_missing_in_dev(monkeypatch, caplog):
    monkeypatch.setattr(sentry_utils, "SENTRY_DSN", "")
    monkeypatch.setattr(sentry_utils, "ENV", "development")
    monkeypatch.setattr(sentry_utils, "_sentry_sdk", None)

    with caplog.at_level(logging.INFO, logger="sentry_utils"):
        result = sentry_utils.init_sentry()

    assert result is False
    # A missing DSN in dev is normal — must NOT raise the production alarm.
    assert "DISABLED in production" not in caplog.text
