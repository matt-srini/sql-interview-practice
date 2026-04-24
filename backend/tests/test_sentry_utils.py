from __future__ import annotations

import sys
import types

from fastapi import Request

from exceptions import AppError
import sentry_utils


class _FakeSentrySDK:
    def __init__(self) -> None:
        self.tags: dict[str, str] = {}
        self.contexts: dict[str, dict[str, object]] = {}
        self.user: dict[str, object] | None = None
        self.init_calls: list[dict[str, object]] = []

    def init(self, **kwargs) -> None:
        self.init_calls.append(kwargs)

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value

    def set_context(self, key: str, value: dict[str, object]) -> None:
        self.contexts[key] = value

    def set_user(self, value: dict[str, object]) -> None:
        self.user = value


def test_before_send_filters_4xx_errors() -> None:
    event = {"message": "bad request"}
    hint = {"exc_info": (None, AppError("Nope", 403), None)}

    assert sentry_utils._before_send(event, hint) is None


def test_request_and_user_context_are_attached() -> None:
    fake_sdk = _FakeSentrySDK()

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/questions/1",
        "query_string": b"draft=true",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
        "server": ("testserver", 80),
    }
    request = Request(scope)

    original_sdk = sentry_utils._sentry_sdk
    sentry_utils._sentry_sdk = fake_sdk
    try:
        sentry_utils.set_sentry_request_context(request, "req-123")
        sentry_utils.set_sentry_user(
            {"id": "user-1", "email": "user@example.com", "plan": "pro", "email_verified": True},
            is_authenticated=True,
        )
    finally:
        sentry_utils._sentry_sdk = original_sdk

    assert fake_sdk.tags["request_id"] == "req-123"
    assert fake_sdk.tags["http.method"] == "POST"
    assert fake_sdk.tags["http.path"] == "/api/questions/1"
    assert fake_sdk.tags["user.plan"] == "pro"
    assert fake_sdk.tags["user.is_authenticated"] == "true"
    assert fake_sdk.tags["user.email_verified"] == "true"
    assert fake_sdk.contexts["request_meta"]["query_string"] == "draft=true"
    assert fake_sdk.user == {"id": "user-1", "email": "user@example.com"}


def test_init_sentry_passes_release_and_sample_rate(monkeypatch) -> None:
    fake_sdk = _FakeSentrySDK()
    sentry_module = types.ModuleType("sentry_sdk")
    sentry_module.init = fake_sdk.init

    integrations_module = types.ModuleType("sentry_sdk.integrations")
    fastapi_module = types.ModuleType("sentry_sdk.integrations.fastapi")

    class FastApiIntegration:
        pass

    fastapi_module.FastApiIntegration = FastApiIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_module)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", integrations_module)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_module)
    monkeypatch.setattr(sentry_utils, "SENTRY_DSN", "https://backend@example.ingest.sentry.io/123")
    monkeypatch.setattr(sentry_utils, "SENTRY_RELEASE", "api@abc123")
    monkeypatch.setattr(sentry_utils, "SENTRY_TRACES_SAMPLE_RATE", 0.25)
    monkeypatch.setattr(sentry_utils, "_sentry_sdk", None)

    assert sentry_utils.init_sentry() is True
    assert fake_sdk.init_calls
    init_kwargs = fake_sdk.init_calls[0]
    assert init_kwargs["dsn"] == "https://backend@example.ingest.sentry.io/123"
    assert init_kwargs["environment"] == sentry_utils.ENV
    assert init_kwargs["release"] == "api@abc123"
    assert init_kwargs["traces_sample_rate"] == 0.25
    assert callable(init_kwargs["before_send"])
