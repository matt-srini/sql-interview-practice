"""Runtime sandbox-hardening guards (2026-06-26 audit follow-up).

Two layers beyond the AST guard:
  - _guarded_import: a runtime __import__ that denies the code-execution / native / IPC /
    introspection modules (subprocess, ctypes, socket, multiprocessing, ...), so a guard
    escape that reaches the real __import__ still cannot import them. os/sys are
    deliberately NOT denied (gated by the AST allowlist in prod; env is scrubbed; the
    file-read residual is Landlock's domain; the env-isolation tests probe via import os).
  - _install_exec_block: a seccomp filter denying execve/execveat (Linux), so a guard
    escape cannot spawn a subprocess. Linux-only; skipped elsewhere.
"""
import sys

import pytest

from python_sandbox_harness import _guarded_import, _safe_builtins, _IMPORT_DENY


def test_guarded_import_blocks_dangerous_modules():
    for mod in ("subprocess", "ctypes", "importlib", "builtins", "multiprocessing", "pickle"):
        with pytest.raises(ImportError):
            _guarded_import(mod)


def test_guarded_import_allows_safe_modules():
    # Allowlisted user imports must still work through the guarded importer.
    assert _guarded_import("math") is not None
    assert _guarded_import("collections") is not None


def test_guarded_import_allows_os_sys():
    # os/sys are deliberately NOT denied at the import backstop (see module docstring):
    # the AST allowlist gates them in prod, and the env-isolation tests probe via import os.
    assert _guarded_import("os") is not None
    assert _guarded_import("sys") is not None


def test_safe_builtins_uses_guarded_import():
    assert _safe_builtins()["__import__"] is _guarded_import


def test_import_deny_covers_core_dangerous_modules():
    for mod in ("subprocess", "ctypes", "importlib", "multiprocessing", "pickle"):
        assert mod in _IMPORT_DENY
    # os/sys/socket/resource are intentionally absent — controlled by the AST allowlist /
    # env-scrub / seccomp / RLIMIT layers, and imported as probes by the sandbox security
    # tests (test_sandbox_env_isolation, _seccomp, _resource_limits). Denying their import
    # would break those probes without adding control.
    for mod in ("os", "sys", "socket", "resource"):
        assert mod not in _IMPORT_DENY


@pytest.mark.skipif(sys.platform != "linux", reason="seccomp exec-block is Linux-only")
def test_exec_block_denies_subprocess_in_harness(tmp_path):
    """End-to-end: through the real harness, a subprocess spawn must fail (execve denied).

    Uses the guarded-but-reachable path: even if user code obtains subprocess, execve is
    blocked by the seccomp filter, so check_output cannot run a program.
    """
    from python_evaluator import _spawn_harness
    # Reach subprocess via the (now-guarded) builtins walk is blocked by the guard; here we
    # confirm the OS-level block directly: import subprocess in TRUSTED-style code is not
    # possible from user code, so we assert the filter is installed by checking that a
    # deliberately-crafted exec attempt fails. We run code that tries os.system via a chain;
    # the harness should either block import or the execve should be denied -> non-'OK'.
    code = (
        "def solve():\n"
        "    try:\n"
        "        import subprocess\n"
        "        return subprocess.check_output(['echo','X']).decode().strip()\n"
        "    except Exception as e:\n"
        "        return 'BLOCKED:' + type(e).__name__\n"
    )
    res = _spawn_harness({"mode": "algorithm", "code": code,
                          "test_cases": [{"input": [], "expected": "X"}]})
    results = res.get("results") or []
    actual = results[0].get("actual") if results else res.get("error")
    assert actual != "X", f"subprocess executed despite exec-block: {actual!r}"
