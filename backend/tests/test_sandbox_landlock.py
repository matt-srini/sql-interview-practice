"""Landlock filesystem read-scoping (2026-06-26 sandbox PRR — the file-read residual closure).

Proves the boundary via the REAL subprocess harness: with Landlock active, user code (even
bypassing the guard, as these tests do) cannot read `backend/content/**` (the answer keys)
or app source — while numpy/pandas execution still works.

NB: we never call `landlock_sandbox.restrict_reads` in-process — that would lock down the
pytest process itself. All behaviour is exercised through `_spawn_harness` (a subprocess
that exits after one run). The deny tests need Landlock ACTIVE (it fails open otherwise), so
they skip when the kernel lacks it (macOS dev / pre-5.13); CI (ubuntu-latest 6.x) has it.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import landlock_sandbox  # noqa: E402
from python_evaluator import _spawn_harness, run_pandas_code, DATASETS_DIR  # noqa: E402

_LL = landlock_sandbox.abi_version()
_BACKEND = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def _first_content_json() -> str:
    content = os.path.join(_BACKEND, "content")
    for root, _dirs, files in os.walk(content):
        for f in files:
            if f.endswith(".json"):
                return os.path.join(root, f)
    return ""


def _probe_read(abs_path: str) -> str:
    """Run sandbox code that tries to os.open(abs_path) and reports OK / DENIED:errno."""
    code = (
        "import os\n"
        "def solve():\n"
        "    try:\n"
        f"        fd = os.open({abs_path!r}, os.O_RDONLY)\n"
        "        os.close(fd)\n"
        "        return 'READ_OK'\n"
        "    except OSError as e:\n"
        "        return 'DENIED:%d' % (e.errno or 0)\n"
    )
    res = _spawn_harness({"mode": "algorithm", "code": code,
                          "test_cases": [{"input": [], "expected": "x"}]})
    results = res.get("results") or []
    return results[0].get("actual") if results else res.get("error")


@pytest.mark.skipif(not _LL, reason="Landlock unavailable on this kernel (fails open)")
def test_sandbox_cannot_read_answer_keys():
    target = _first_content_json()
    assert target, "no content/*.json found to probe"
    actual = _probe_read(target)
    assert isinstance(actual, str) and actual.startswith("DENIED"), (
        f"Landlock must deny reading the answer key {target!r}, got {actual!r}")


@pytest.mark.skipif(not _LL, reason="Landlock unavailable on this kernel (fails open)")
def test_sandbox_cannot_read_app_source():
    target = os.path.join(_BACKEND, "python_evaluator.py")
    actual = _probe_read(target)
    assert isinstance(actual, str) and actual.startswith("DENIED"), (
        f"Landlock must deny reading app source {target!r}, got {actual!r}")


def test_pandas_execution_still_works_under_landlock():
    """numpy/pandas import + a real CSV read + a DataFrame op must still succeed — Landlock
    allows the Python runtime + the datasets dir. Cross-platform: a no-op where Landlock is
    absent, a real check where it is active. Guards against an over-tight allow-list."""
    csvs = [f for f in os.listdir(DATASETS_DIR) if f.endswith(".csv")]
    assert csvs, "no dataset CSVs found"
    question = {"dataframes": {"df": csvs[0]}}
    code = (
        "import pandas as pd\n"
        "import numpy as np\n"
        "def solve(df):\n"
        "    return df.head(3).reset_index(drop=True)\n"
    )
    result = run_pandas_code(code, question)
    assert not result.get("error"), (
        f"pandas execution under Landlock failed (allow-list too tight?): {result.get('error')!r}")
    assert result.get("rows") is not None


def test_landlock_module_is_failsafe():
    """abi_version() never raises and returns an int or None (read-only; safe in-process)."""
    v = landlock_sandbox.abi_version()
    assert v is None or (isinstance(v, int) and v >= 1)
