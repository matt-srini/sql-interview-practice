"""Deterministic regression for the OpenBLAS RLIMIT_AS abort (2026-06-26 audit).

Reproduces the prod failure on ANY Linux runner (even 2-core CI) by forcing a high
OPENBLAS_NUM_THREADS plus a tight RLIMIT_AS, instead of needing a real many-core host:
OpenBLAS sizes its scratch-buffer pool to the thread count, so 32 threads reserve ~1 GB
of virtual AS -- far above a 256 MB cap -> abort. With the pin (=1) it needs ~tens of MB
-> success. This is the high-core condition the 2026-06-08 load test could not hit.
"""
import os
import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_AS is Linux-only")

_SNIPPET = textwrap.dedent('''
    import resource
    TIGHT_AS = 256 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (TIGHT_AS, TIGHT_AS))
    import numpy as np            # triggers OpenBLAS init
    a = np.ones((64, 64)); _ = a @ a   # force a BLAS call
    print("ok")
''').strip()


def _run_with_blas_threads(n: int):
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "OPENBLAS_NUM_THREADS": str(n),
        "OMP_NUM_THREADS": str(n),
        "MKL_NUM_THREADS": str(n),
        "NUMEXPR_NUM_THREADS": str(n),
    }
    return subprocess.run([sys.executable, "-c", _SNIPPET], env=env,
                          capture_output=True, text=True, timeout=30)


def test_high_thread_count_aborts_under_tight_rlimit():
    """The pre-fix prod condition (many-core host): OpenBLAS overruns the AS cap -> abort."""
    p = _run_with_blas_threads(32)
    assert p.returncode != 0, (
        f"expected a non-zero exit (OpenBLAS abort) at 32 threads under 256MB RLIMIT_AS, "
        f"got 0. If this regresses, the abort threshold moved -- raise the thread count or "
        f"lower TIGHT_AS. stdout={p.stdout!r} stderr={p.stderr[:300]!r}")


def test_pinned_thread_count_succeeds_under_tight_rlimit():
    """The fix: one BLAS thread fits comfortably under the same cap."""
    p = _run_with_blas_threads(1)
    assert p.returncode == 0 and "ok" in p.stdout, (
        f"numpy import + BLAS call should succeed with OPENBLAS_NUM_THREADS=1 under 256MB, "
        f"got rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr[:300]!r}")


def test_sandbox_env_pins_blas_threads():
    """Regression guard: _sandbox_env must keep exporting the four *_NUM_THREADS=1 pins."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from python_evaluator import _sandbox_env
    env = _sandbox_env()
    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        assert env.get(k) == "1", f"{k} pin missing from _sandbox_env()"
