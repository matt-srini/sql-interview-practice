"""The user-code sandbox subprocess must NOT inherit the parent process environment,
which on production holds every secret (DATABASE_URL, RAZORPAY_KEY_SECRET, OAuth client
secrets, RESEND_API_KEY, SENTRY_DSN, ...). The AST guard is a denylist and can in
principle be bypassed; this is the defense-in-depth layer that ensures even a full guard
escape finds no secret in its environment.

These tests call the harness directly (bypassing python_guard) — exactly what a guard
escape would achieve — and assert the planted secret is invisible.
"""
import os

from python_evaluator import _sandbox_env, _spawn_harness


def _run_probe(env_key: str) -> str:
    """Exec sandbox code that reads an env var and returns it (or 'ABSENT')."""
    code = (
        "import os\n"
        "def solve():\n"
        f"    return os.environ.get('{env_key}', 'ABSENT')\n"
    )
    payload = {"mode": "algorithm", "code": code,
               "test_cases": [{"input": [], "expected": "ABSENT"}]}
    res = _spawn_harness(payload)
    assert res.get("results"), res
    return res["results"][0]["actual"]


def test_planted_secret_is_invisible_to_sandbox(monkeypatch):
    monkeypatch.setenv("FAKE_DB_SECRET", "super-secret-value")
    assert _run_probe("FAKE_DB_SECRET") == "ABSENT"


def test_real_production_secret_names_are_invisible(monkeypatch):
    # Simulate the actual prod secrets being present in the parent env.
    for name in ("DATABASE_URL", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
                 "GOOGLE_CLIENT_SECRET", "RESEND_API_KEY", "SENTRY_DSN"):
        monkeypatch.setenv(name, f"leak-{name}")
        assert _run_probe(name) == "ABSENT", f"{name} leaked into the sandbox"


def test_sandbox_env_is_a_minimal_allowlist(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://secret")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "rzp_secret")
    env = _sandbox_env()
    # No secret leaks through.
    assert "DATABASE_URL" not in env
    assert "RAZORPAY_KEY_SECRET" not in env
    assert not any("SECRET" in k or "KEY" in k or "TOKEN" in k or "DSN" in k for k in env)
    # No PYTHONPATH → user code cannot import backend app modules.
    assert "PYTHONPATH" not in env
    # Python can still start cleanly.
    assert env.get("PATH")
