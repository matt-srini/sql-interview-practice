"""Reserved-domain email guard.

Backstop for the 2026-06-08 incident: the load-test harness registered
``load-*@internal.test`` virtual users against a backend holding the production
RESEND_API_KEY, firing real Resend sends to an undeliverable (.test) domain —
burning quota and generating hard bounces. ``email_service`` now refuses to send
to RFC-reserved / structurally undeliverable domains before any network call.

conftest's ``pytest_configure`` stubs ``email_service.send_verification_email`` /
``send_password_reset_email`` for the whole session, so importing them normally
would capture the mocks. We load a fresh, unpatched copy of the module to test the
real guard.
"""
import asyncio
import importlib.util

import pytest

import email_service as _patched


def _load_real_email_service():
    spec = importlib.util.spec_from_file_location("_email_service_real", _patched.__file__)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


es = _load_real_email_service()

SEND_FN_NAMES = [
    "send_verification_email",
    "send_password_reset_email",
    "send_magic_link_email",
]

RESERVED = [
    "load-abc-1@internal.test",
    "a@foo.test",
    "x@example.com",
    "x@example.net",
    "x@example.org",
    "x@host.invalid",
    "x@localhost",
    "x@dev.local",
    "no-at-sign",
    "double@@at.com",
    "@nodomain.test",
]

DELIVERABLE = [
    "matt.srini@gmail.com",
    "srinivas.assampally@gmail.com",
    "noreply@datathink.co",
    "user@sub.company.co.uk",
    "person@outlook.com",
]


class _RaisingClient:
    """Stand-in for httpx.AsyncClient that fails if the guard ever lets a send through."""

    def __init__(self, *a, **k):
        raise AssertionError("network send attempted for a reserved/undeliverable recipient")


class _FakeResp:
    status_code = 200
    text = ""


class _FakeClient:
    """Minimal async-context httpx.AsyncClient stand-in that 'succeeds'."""

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        return _FakeResp()


# --------------------------------------------------------------------------- #
# Pure predicate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("addr", RESERVED)
def test_reserved_domains_flagged(addr):
    assert es._is_undeliverable_recipient(addr) is True


@pytest.mark.parametrize("addr", DELIVERABLE)
def test_deliverable_domains_pass(addr):
    assert es._is_undeliverable_recipient(addr) is False


def test_trailing_dot_normalizes_to_real_domain():
    # A trailing root-dot is a valid FQDN form; gmail.com. -> gmail.com is deliverable.
    assert es._is_undeliverable_recipient("trailing@gmail.com.") is False


# --------------------------------------------------------------------------- #
# Send functions never touch the network for reserved recipients
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fn_name", SEND_FN_NAMES)
def test_send_blocks_reserved_without_network(fn_name, monkeypatch):
    # Key present, so we get past the no-key short-circuit and exercise the guard.
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_fake_key_for_test")
    monkeypatch.setattr(es.httpx, "AsyncClient", _RaisingClient)
    result = asyncio.run(getattr(es, fn_name)("load-xyz-7@internal.test", "tok_123"))
    assert result is False  # blocked, and _RaisingClient proves no send was attempted


@pytest.mark.parametrize("fn_name", SEND_FN_NAMES)
def test_send_proceeds_for_real_domain(fn_name, monkeypatch):
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_fake_key_for_test")
    monkeypatch.setattr(es.httpx, "AsyncClient", _FakeClient)
    result = asyncio.run(getattr(es, fn_name)("real.person@gmail.com", "tok_123"))
    assert result is True  # guard does NOT block deliverable domains


@pytest.mark.parametrize("fn_name", SEND_FN_NAMES)
def test_no_key_still_short_circuits(fn_name, monkeypatch):
    # With no key, every send is a no-op regardless of recipient.
    monkeypatch.setattr(es, "RESEND_API_KEY", None)
    monkeypatch.setattr(es.httpx, "AsyncClient", _RaisingClient)
    assert asyncio.run(getattr(es, fn_name)("real.person@gmail.com", "tok_123")) is False
