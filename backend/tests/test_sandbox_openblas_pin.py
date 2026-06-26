"""Regression for the OpenBLAS RLIMIT_AS abort (2026-06-26 audit).

Firm guards (load-bearing): with the pin (`OPENBLAS_NUM_THREADS=1`) numpy imports + runs a
BLAS call under a tight RLIMIT_AS (`test_pinned...`), and `_sandbox_env` keeps exporting the
four `*_NUM_THREADS=1` pins (`test_sandbox_env_pins...`).

Best-effort repro: `test_high_thread...` forces many BLAS threads under the same cap to
reproduce the prod abort without a real many-core host. The exact threshold is
OpenBLAS-build-dependent (per-thread scratch-buffer size varies), so it uses a matmul large
enough to genuinely multi-thread and SKIPS (never fails) on a runner whose OpenBLAS does not
cross the cap.
"""
import os
import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_AS is Linux-only")

def _run(n_threads: int, dim: int):
    """Import numpy + run a `dim`x`dim` matmul under a 256 MB RLIMIT_AS with the BLAS thread
    pools set to `n_threads`. A large `dim` makes the GEMM genuinely multi-thread, so the
    thread count actually drives per-thread scratch-buffer allocation (a tiny op runs
    single-threaded regardless of OPENBLAS_NUM_THREADS — the bug in the first version)."""
    snippet = textwrap.dedent(f'''
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
        import numpy as np                       # triggers OpenBLAS init
        a = np.ones(({dim}, {dim})); _ = a @ a   # force a (multi-threaded for large dim) BLAS call
        print("ok")
    ''').strip()
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "OPENBLAS_NUM_THREADS": str(n_threads),
        "OMP_NUM_THREADS": str(n_threads),
        "MKL_NUM_THREADS": str(n_threads),
        "NUMEXPR_NUM_THREADS": str(n_threads),
    }
    return subprocess.run([sys.executable, "-c", snippet], env=env,
                          capture_output=True, text=True, timeout=30)


def test_high_thread_count_aborts_under_tight_rlimit():
    """The pre-fix prod condition (many-core host): many BLAS threads overrun the AS cap.

    Best-effort repro — per-thread buffer size is OpenBLAS-build-dependent, so a runner may
    not cross 256 MB even at 128 threads; we SKIP (never fail) in that case. The pin guards
    below are the load-bearing checks. The large matmul (1024) is what makes the GEMM
    actually parallelize, so the thread count drives buffer allocation."""
    p = _run(128, 1024)
    if p.returncode == 0:
        pytest.skip("this runner's OpenBLAS did not exceed the 256MB AS cap at 128 threads "
                    "(build-dependent per-thread buffer size); abort not reproduced here")
    # non-zero exit == the OpenBLAS abort we expect when threads x buffers overrun the cap


def test_pinned_thread_count_succeeds_under_tight_rlimit():
    """The fix: one BLAS thread fits comfortably under the same cap (tiny op, ~no buffers)."""
    p = _run(1, 64)
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
