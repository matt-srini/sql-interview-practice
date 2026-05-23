"""
Python code evaluator — spawns python_sandbox_harness.py in a subprocess,
enforces a timeout, and compares results.

Test-case generator system
--------------------------
Hidden test cases may contain generator specs instead of literal values:

    {"input": [{"gen": "random_ints", "n": 100000, "seed": 42,
                "low": 0, "high": 9999, "distribution": "zipf"},
               5],
     "expected": {"compute": "reference"}}

``_expand_test_cases()`` is called in ``evaluate_python_code()`` before
sending test cases to the sandbox harness.  The harness itself receives
only expanded literal values — it needs zero changes.

Public test cases are always all-literal; generators are hidden-only.
"""
from __future__ import annotations

import json
import logging
import os
import random as _random_module
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

from evaluator import normalize_dataframe

logger = logging.getLogger(__name__)

CODE_TIMEOUT_SECONDS = 5
HARNESS_PATH = Path(__file__).parent / "python_sandbox_harness.py"
DATASETS_DIR = Path(__file__).parent / "datasets"


# ── Generator library ────────────────────────────────────────────────────────
#
# Six generators; all use a private Random(seed) instance — never the global
# rng.  Same seed always produces identical output (deterministic).


def _gen_random_ints(
    n: int,
    seed: int,
    low: int,
    high: int,
    distribution: str = "uniform",
) -> list[int]:
    """Return n integers in [low, high] sampled by the chosen distribution.

    distribution choices
    --------------------
    "uniform"         rng.randint(low, high) for each element
    "low_cardinality" pool of ~10 values from [low, high], sampled with
                      replacement — adversarial for majority/heavy-K when
                      the solution must handle low-cardinality inputs
    "high_cardinality" rng.sample to produce near-unique values —
                      adversarial for hash-map approaches that rely on
                      low-cardinality shortcuts
    "zipf"            power-law via rng.paretovariate(1.5), clamped to
                      [low, high] — adversarial for top-K heavy-hitters
    """
    rng = _random_module.Random(seed)
    span = high - low

    if distribution == "uniform":
        return [rng.randint(low, high) for _ in range(n)]

    if distribution == "low_cardinality":
        pool_size = min(10, span + 1)
        pool = [low + rng.randint(0, span) for _ in range(pool_size)]
        return [rng.choice(pool) for _ in range(n)]

    if distribution == "high_cardinality":
        if n > span + 1:
            # Range smaller than n — fall back to uniform (all unique not possible)
            return [rng.randint(low, high) for _ in range(n)]
        return rng.sample(range(low, high + 1), n)

    if distribution == "zipf":
        result: list[int] = []
        for _ in range(n):
            # paretovariate(1.5) returns values in [1, ∞); clamp to span+1
            raw = int(rng.paretovariate(1.5))
            val = low + min(raw - 1, span)
            result.append(val)
        return result

    raise ValueError(f"unknown distribution: {distribution!r}")


def _gen_random_floats(
    n: int,
    seed: int,
    low: float,
    high: float,
) -> list[float]:
    """Return n floats uniformly sampled from [low, high]."""
    rng = _random_module.Random(seed)
    return [rng.uniform(low, high) for _ in range(n)]


def _gen_random_strings(
    n: int,
    seed: int,
    alphabet: str = "abcdefghij",
    min_len: int = 1,
    max_len: int = 20,
) -> list[str]:
    """Return n random strings drawn from alphabet with lengths in [min_len, max_len]."""
    rng = _random_module.Random(seed)
    result: list[str] = []
    for _ in range(n):
        length = rng.randint(min_len, max_len)
        result.append("".join(rng.choice(alphabet) for _ in range(length)))
    return result


def _gen_sorted_ints(
    n: int,
    seed: int,
    low: int,
    high: int,
    unique: bool = False,
) -> list[int]:
    """Return n sorted integers from [low, high].

    If unique=True, sample without replacement (raises if n > high - low + 1).
    """
    rng = _random_module.Random(seed)
    if unique:
        span = high - low + 1
        if n > span:
            raise ValueError(
                f"sorted_ints unique=True: n={n} exceeds range size {span}"
            )
        return sorted(rng.sample(range(low, high + 1), n))
    return sorted(rng.randint(low, high) for _ in range(n))


def _gen_random_pairs(
    n: int,
    seed: int,
    key_space: int,
    value_low: int = 0,
    value_high: int = 1_000_000,
) -> list[list[int]]:
    """Return [[key, value], ...] with n pairs.

    key  ∈ [0, key_space - 1], value ∈ [value_low, value_high].
    Useful for in-memory join tests and interval generation (set value_low
    > key_space to guarantee valid [start, end] intervals where start < end).
    """
    rng = _random_module.Random(seed)
    return [
        [rng.randint(0, key_space - 1), rng.randint(value_low, value_high)]
        for _ in range(n)
    ]


def _gen_random_graph(
    n_nodes: int,
    n_edges: int,
    seed: int,
    weighted: bool = False,
    directed: bool = False,
    dag: bool = False,
    weight_low: int = 1,
    weight_high: int = 100,
) -> dict:
    """Return {"nodes": [0..n_nodes-1], "edges": [[u,v]] or [[u,v,w]]}.

    If dag=True, forces directed=True and all edges satisfy u < v (so the
    node index is a valid topological order seed).
    """
    rng = _random_module.Random(seed)
    if dag:
        directed = True

    seen: set[tuple[int, int]] = set()
    edges: list[list[int]] = []
    attempts = 0
    max_attempts = n_edges * 20

    while len(edges) < n_edges and attempts < max_attempts:
        attempts += 1
        u = rng.randint(0, n_nodes - 1)
        v = rng.randint(0, n_nodes - 1)
        if u == v:
            continue
        if dag:
            u, v = min(u, v), max(u, v)
        edge_key: tuple[int, int] = (u, v) if directed else (min(u, v), max(u, v))
        if edge_key in seen:
            continue
        seen.add(edge_key)
        if weighted:
            edges.append([u, v, rng.randint(weight_low, weight_high)])
        else:
            edges.append([u, v])

    return {"nodes": list(range(n_nodes)), "edges": edges}


_GENERATORS: dict[str, Any] = {
    "random_ints": _gen_random_ints,
    "random_floats": _gen_random_floats,
    "random_strings": _gen_random_strings,
    "sorted_ints": _gen_sorted_ints,
    "random_pairs": _gen_random_pairs,
    "random_graph": _gen_random_graph,
}


# ── Test-case expansion ──────────────────────────────────────────────────────


def _expand_arg(arg: Any) -> Any:
    """Expand a generator spec dict; pass literals through unchanged."""
    if isinstance(arg, dict) and "gen" in arg:
        name = arg["gen"]
        if name not in _GENERATORS:
            raise ValueError(f"unknown generator: {name!r}")
        kwargs = {k: v for k, v in arg.items() if k != "gen"}
        return _GENERATORS[name](**kwargs)
    return arg


def _expand_test_case(tc: dict, expected_code: str) -> dict:
    """Expand generator specs in one test case; compute expected if requested.

    Invariants (enforced loudly):
    - Any generator-spec input  →  expected MUST be {"compute": "reference"}
    - {"compute": "reference"}  →  at least one arg must be a generator spec
    - public_test_cases are always all-literal; only hidden tests use generators
    """
    expanded_input = [_expand_arg(a) for a in tc["input"]]
    expected = tc.get("expected")

    has_gen = any(isinstance(a, dict) and "gen" in a for a in tc["input"])
    compute_spec = isinstance(expected, dict) and expected.get("compute") == "reference"

    if has_gen and not compute_spec:
        raise ValueError(
            'test_case with generator input must have expected={"compute":"reference"}'
        )
    if compute_spec and not has_gen:
        raise ValueError(
            'test_case with expected={"compute":"reference"} must have '
            "at least one generator-spec input"
        )

    if compute_spec:
        ns: dict = {}
        exec(expected_code, ns)  # noqa: S102 — expected_code is vetted authored content
        expected = ns["solve"](*expanded_input)

    return {"input": expanded_input, "expected": expected}


def _expand_test_cases(test_cases: list[dict], expected_code: str) -> list[dict]:
    """Expand all test cases in a list."""
    return [_expand_test_case(tc, expected_code) for tc in test_cases]


def _spawn_harness(payload: dict) -> dict:
    """Run the harness subprocess, enforce timeout, parse stdout."""
    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(HARNESS_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=CODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Code timed out after {CODE_TIMEOUT_SECONDS} seconds. Check for infinite loops."}

    duration = time.time() - start
    logger.debug("Harness completed in %.3fs", duration)

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        return {"error": f"Runtime error:\n{stderr}" if stderr else "Code execution failed."}

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"Harness produced invalid output: {proc.stdout[:200]}"}


def run_python_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user code against public test cases and return per-case results.
    Used by /run-code endpoint (shows only public test cases).

    Normalises harness keys to match the frontend contract:
      ``results``      → ``test_results``
      ``print_output`` → ``stdout``
    """
    test_cases = question.get("test_cases", [])
    public_count = question.get("public_test_cases", len(test_cases))
    public_cases = test_cases[:public_count]

    payload = {
        "mode": "algorithm",
        "code": code,
        "test_cases": public_cases,
    }
    result = _spawn_harness(payload)
    # Normalise harness keys → frontend-expected keys
    if "results" in result:
        result["test_results"] = result.pop("results")
    if "print_output" in result:
        result["stdout"] = result.pop("print_output")
    return result


def evaluate_python_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user code against ALL test cases (including hidden) for submit.
    Returns correct/incorrect verdict and per-case breakdown (hidden cases summarized).

    Hidden test cases may contain generator specs; they are expanded here
    (in the trusted evaluator process) before being sent to the sandbox
    harness.  The harness receives only expanded literal values.
    """
    test_cases = question.get("test_cases", [])
    public_count = question.get("public_test_cases", len(test_cases))

    # Expand generator specs in hidden test cases.  Public cases are always
    # all-literal so expansion is a no-op for them; we expand all for safety.
    expected_code = question.get("expected_code", "")
    try:
        test_cases = _expand_test_cases(test_cases, expected_code)
    except Exception as exc:  # pragma: no cover — authoring error, not user error
        logger.error("Test-case expansion failed for question %s: %s", question.get("id"), exc)
        return {
            "correct": False,
            "error": "Internal error: test-case expansion failed.",
            "test_results": [],
            "hidden_summary": None,
        }

    payload = {
        "mode": "algorithm",
        "code": code,
        "test_cases": test_cases,
    }
    result = _spawn_harness(payload)

    if result.get("error") and not result.get("results"):
        return {
            "correct": False,
            "error": result["error"],
            "public_results": [],
            "hidden_summary": None,
        }

    all_results = result.get("results", [])
    public_results = all_results[:public_count]
    hidden_results = all_results[public_count:]

    all_passed = all(r["passed"] for r in all_results)
    hidden_passed = sum(1 for r in hidden_results if r["passed"])
    hidden_total = len(hidden_results)

    return {
        "correct": all_passed,
        "error": result.get("error"),
        # ``test_results`` matches the frontend TestCasePanel prop name
        "test_results": public_results,
        "hidden_summary": {
            "passed": hidden_passed,
            "total": hidden_total,
        } if hidden_total > 0 else None,
    }


def run_python_data_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user pandas/numpy code and return the resulting DataFrame.
    Used by /run-code endpoint for the Pandas track.

    Normalises harness keys to match the frontend contract:
      ``print_output``      → ``stdout``
      ``result.columns``    → top-level ``columns``
      ``result.rows``       → top-level ``rows``
    The nested ``result`` dict is kept for internal use by ``evaluate_python_data_code``.
    """
    dataframes = question.get("dataframes", {})
    payload = {
        "mode": "data",
        "code": code,
        "dataframes": dataframes,
        "csv_dir": str(DATASETS_DIR),
    }
    raw = _spawn_harness(payload)
    # Normalise print_output → stdout
    if "print_output" in raw:
        raw["stdout"] = raw.pop("print_output")
    # Flatten columns/rows to top level for direct frontend access
    nested = raw.get("result") or {}
    if nested.get("columns") is not None:
        raw["columns"] = nested["columns"]
    if nested.get("rows") is not None:
        raw["rows"] = nested["rows"]
    return raw


def evaluate_python_data_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user code AND expected code, normalize both DataFrames, compare.
    """
    # Run user code
    user_output = run_python_data_code(code, question)
    if user_output.get("error"):
        return {
            "correct": False,
            "error": user_output["error"],
            "user_result": None,
            "expected_result": None,
            "stdout": user_output.get("stdout", ""),
        }

    # Run expected code (trusted, same harness but no guard needed)
    expected_code = question.get("expected_code", "")
    dataframes = question.get("dataframes", {})
    expected_payload = {
        "mode": "data",
        "code": expected_code,
        "dataframes": dataframes,
        "csv_dir": str(DATASETS_DIR),
    }
    expected_output = _spawn_harness(expected_payload)

    if expected_output.get("error"):
        logger.error("Expected code failed for question %s: %s", question.get("id"), expected_output["error"])
        return {
            "correct": False,
            "error": "Internal error: expected solution failed.",
            "user_result": None,
            "expected_result": None,
            "stdout": user_output.get("stdout", ""),
        }

    user_result = user_output.get("result")
    expected_result = expected_output.get("result")

    # Normalize and compare
    try:
        user_df = pd.DataFrame(user_result["rows"]) if user_result else pd.DataFrame()
        expected_df = pd.DataFrame(expected_result["rows"]) if expected_result else pd.DataFrame()
        correct = normalize_dataframe(user_df).equals(normalize_dataframe(expected_df))
    except Exception as e:
        logger.warning("Comparison failed: %s", e)
        correct = False

    return {
        "correct": correct,
        "error": None,
        "user_result": user_result,
        "expected_result": expected_result,
        "stdout": user_output.get("stdout", ""),
    }
