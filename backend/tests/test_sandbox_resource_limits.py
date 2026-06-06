"""Category-3 (resource-exhaustion) tests: infinite loops, memory bombs, fork
bombs, output floods, deep recursion.

These call the harness directly (bypassing python_guard) — i.e. they test the
RUNTIME caps that hold even if the AST guard is bypassed, which is the whole point
of defense-in-depth. The user-facing contract for every case: a clean, fast
response with the host unharmed — never a hang, a crash, or an orphaned process.

Linux-gated tests (rlimits, fork, memory) skip on macOS dev, where RLIMIT_AS/NPROC
are unreliable; they run and validate in CI (Linux). The cross-platform tests
(timeout, output, recursion) run everywhere.
"""
import json
import os
import sys
import time

import pytest

from python_evaluator import _spawn_harness

_LINUX = sys.platform == "linux"
linux_only = pytest.mark.skipif(not _LINUX, reason="RLIMITs reliable only on Linux (runs in CI)")


def _run(code: str, timeout: int = 5, expected="X") -> dict:
    """Exec `code` (defining solve()) in the sandbox; return the harness result."""
    return _spawn_harness(
        {"mode": "algorithm", "code": code, "test_cases": [{"input": [], "expected": expected}]},
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Cross-platform: timeout, output flood, recursion
# ---------------------------------------------------------------------------

def test_infinite_loop_killed_by_timeout():
    """A tight infinite loop (guard-allowed) is killed at the wall timeout."""
    start = time.time()
    res = _run("def solve():\n    while True:\n        pass", timeout=3)
    elapsed = time.time() - start
    assert "error" in res, f"infinite loop did not error: {res}"
    assert elapsed < 6, f"timeout took too long: {elapsed:.1f}s"


def test_output_flood_is_truncated_not_crashing():
    """A multi-MB print is truncated (64 KB cap), the run still returns cleanly."""
    res = _run("def solve():\n    print('A' * 5_000_000)\n    return 1", expected=1)
    # Either it returns a result with bounded stdout, or a clean error — never a hang/crash.
    assert isinstance(res, dict)
    out = json.dumps(res)
    assert len(out) < 2_000_000, "output was not truncated — full 5MB flood leaked through"


def test_deep_recursion_is_handled():
    """Unbounded recursion → RecursionError, caught and returned as a failed case."""
    res = _run("def solve():\n    return solve()", expected=1)
    assert isinstance(res, dict)
    # The per-case error is captured; the harness must not crash the whole run.
    if res.get("results"):
        assert res["results"][0]["passed"] is False
    else:
        assert "error" in res


# ---------------------------------------------------------------------------
# Linux-gated: the rlimits are actually applied
# ---------------------------------------------------------------------------

@linux_only
def test_all_rlimits_are_applied_in_the_sandbox():
    """The sandbox subprocess has AS/CPU/NPROC/FSIZE caps set (read via getrlimit)."""
    code = (
        "import resource\n"
        "def solve():\n"
        "    return {\n"
        "        'AS':    resource.getrlimit(resource.RLIMIT_AS)[0],\n"
        "        'CPU':   resource.getrlimit(resource.RLIMIT_CPU)[0],\n"
        "        'NPROC': resource.getrlimit(resource.RLIMIT_NPROC)[0],\n"
        "        'FSIZE': resource.getrlimit(resource.RLIMIT_FSIZE)[0],\n"
        "    }\n"
    )
    res = _run(code)
    assert res.get("results"), res
    limits = res["results"][0]["actual"]
    assert limits["AS"] == 512 * 1024 * 1024, f"RLIMIT_AS not 512MB: {limits['AS']}"
    assert limits["CPU"] == 14, f"RLIMIT_CPU not 14s: {limits['CPU']}"
    assert limits["NPROC"] == 256, f"RLIMIT_NPROC not 256: {limits['NPROC']}"
    assert limits["FSIZE"] == 64 * 1024 * 1024, f"RLIMIT_FSIZE not 64MB: {limits['FSIZE']}"


@linux_only
def test_memory_bomb_raises_memoryerror():
    """Allocating > 512 MB hits RLIMIT_AS → MemoryError, caught, no host OOM."""
    code = (
        "def solve():\n"
        "    try:\n"
        "        x = bytearray(600 * 1024 * 1024)\n"
        "        return 'ALLOCATED_%d' % len(x)\n"
        "    except MemoryError:\n"
        "        return 'MEMORY_CAPPED'\n"
    )
    res = _run(code, expected="MEMORY_CAPPED")
    assert res.get("results"), res
    actual = res["results"][0]["actual"]
    assert actual == "MEMORY_CAPPED", f"600MB alloc was NOT capped by RLIMIT_AS: {actual!r}"


# ---------------------------------------------------------------------------
# Linux-gated: a forked child is killed with the group on timeout (the killpg fix)
# ---------------------------------------------------------------------------

@linux_only
def test_forked_child_is_killed_with_the_group_on_timeout():
    """The killpg-on-timeout fix: a child forked by sandbox code must NOT outlive the
    timeout. Parent forks ONE child that would write a marker after the timeout, then
    the parent hangs so the wall timeout fires. With the process-group SIGKILL the
    child dies before writing; without it (old proc.kill()) the orphan survives.
    """
    marker = f"/tmp/datathink_killpg_probe_{os.getpid()}"
    try:
        if os.path.exists(marker):
            os.remove(marker)
        code = (
            "import os, time\n"
            "def solve():\n"
            f"    pid = os.fork()\n"
            "    if pid == 0:\n"            # child: sleep past the timeout, then mark survival
            "        time.sleep(4)\n"
            f"        open('{marker}', 'w').write('survived')\n"
            "        os._exit(0)\n"
            "    while True:\n"             # parent: hang so the wall timeout fires
            "        pass\n"
        )
        res = _run(code, timeout=2)
        assert "error" in res  # parent timed out
        # Wait past the child's sleep — if killpg failed, the orphan writes the marker.
        time.sleep(5)
        assert not os.path.exists(marker), (
            "a forked child SURVIVED the timeout — process-group kill is not working"
        )
    finally:
        if os.path.exists(marker):
            os.remove(marker)
