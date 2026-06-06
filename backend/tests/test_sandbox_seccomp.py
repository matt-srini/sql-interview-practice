"""The sandbox subprocess installs a seccomp filter that denies network egress.

Railway's managed platform grants no NET_ADMIN / custom --security-opt, so a
container-level egress firewall is unavailable; we apply a per-process seccomp
filter inside the sandbox instead (python_evaluator._install_seccomp_filter).

The BLOCK assertion is Linux-only and requires libseccomp — it is the real proof,
and it runs in CI (ubuntu + libseccomp2). On a non-Linux dev host (macOS) the
filter is a no-op, so the block test skips; the "evals still work" test runs
everywhere to prove the preexec path isn't broken.
"""
import json
import sys
from pathlib import Path

import pytest

from python_evaluator import _spawn_harness, evaluate_python_code

BACKEND = Path(__file__).resolve().parent.parent


def _seccomp_available() -> bool:
    """True iff this host can install a seccomp filter (Linux + libseccomp present)."""
    if sys.platform != "linux":
        return False
    try:
        import pyseccomp as _s
        _s.SyscallFilter(_s.ALLOW)  # constructs → loads libseccomp.so via ctypes (does NOT load into this proc)
        return True
    except Exception:
        return False


def _load(qid: int, base: str) -> dict:
    for diff in ("easy", "medium", "hard"):
        for q in json.loads((BACKEND / "content" / base / f"{diff}.json").read_text()):
            if q.get("id") == qid:
                return q
    raise AssertionError(f"{qid} not found")


def test_evals_still_work_with_seccomp_preexec():
    """The preexec (setsid + chdir + seccomp filter) must not break execution."""
    q = _load(23058, "python_questions")
    assert evaluate_python_code(q["expected_code"], q)["correct"] is True


@pytest.mark.skipif(not _seccomp_available(),
                    reason="seccomp requires Linux + libseccomp (runs in CI, skipped on macOS dev)")
def test_socket_creation_is_denied_in_sandbox():
    """A socket() call inside the sandbox must be blocked by the seccomp filter.

    We call the harness directly (bypassing python_guard) — exactly what a guard
    escape would achieve — and assert the network syscall is denied, not that the
    guard rejected the import.
    """
    code = (
        "import socket\n"
        "def solve():\n"
        "    try:\n"
        "        socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "        return 'SOCKET_CREATED'\n"
        "    except (PermissionError, OSError) as e:\n"
        "        return 'BLOCKED'\n"
    )
    payload = {"mode": "algorithm", "code": code,
               "test_cases": [{"input": [], "expected": "BLOCKED"}]}
    res = _spawn_harness(payload)
    assert res.get("results"), res
    actual = res["results"][0]["actual"]
    assert actual == "BLOCKED", (
        f"socket() was NOT blocked by seccomp — sandbox can open network sockets. got={actual!r}"
    )


@pytest.mark.skipif(not _seccomp_available(),
                    reason="seccomp requires Linux + libseccomp (runs in CI, skipped on macOS dev)")
def test_outbound_connect_is_denied_in_sandbox():
    """An outbound connect() must fail — the egress block, end to end."""
    code = (
        "import socket\n"
        "def solve():\n"
        "    try:\n"
        "        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "        s.settimeout(2)\n"
        "        s.connect(('1.1.1.1', 80))\n"
        "        return 'CONNECTED'\n"
        "    except (PermissionError, OSError) as e:\n"
        "        return 'BLOCKED'\n"
    )
    payload = {"mode": "algorithm", "code": code,
               "test_cases": [{"input": [], "expected": "BLOCKED"}]}
    res = _spawn_harness(payload)
    assert res.get("results"), res
    assert res["results"][0]["actual"] == "BLOCKED", "outbound connect() was NOT blocked"
