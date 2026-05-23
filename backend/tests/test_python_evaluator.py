"""Unit tests for the generator / expansion layer in python_evaluator.py.

TestGeneratorExpansion — 7 cases covering the full expansion contract.
"""
from __future__ import annotations

import textwrap

import pytest

# Import the helpers under test directly — no HTTP layer needed
from python_evaluator import (
    _GENERATORS,
    _expand_arg,
    _expand_test_case,
    _expand_test_cases,
    _gen_random_graph,
    _gen_random_ints,
    _gen_sorted_ints,
)


class TestGeneratorExpansion:
    """Acceptance tests for the generator registry and test-case expansion."""

    # ── Test 1 ───────────────────────────────────────────────────────────────
    def test_literal_passthrough_unchanged(self):
        """Test 1: Literal input + literal expected passes through unchanged."""
        tc = {"input": [42, [1, 2, 3]], "expected": 6}
        result = _expand_test_case(tc, "def solve(x, lst): return sum(lst)")
        assert result["input"] == [42, [1, 2, 3]]
        assert result["expected"] == 6

    # ── Test 2 ───────────────────────────────────────────────────────────────
    def test_random_ints_with_compute_reference_is_deterministic(self):
        """Test 2: random_ints + compute=reference is deterministic (same seed → same output)."""
        expected_code = textwrap.dedent("""
            def solve(nums):
                return sum(nums)
        """)
        tc = {
            "input": [
                {"gen": "random_ints", "n": 5000, "seed": 99, "low": 0, "high": 1000}
            ],
            "expected": {"compute": "reference"},
        }

        result1 = _expand_test_case(tc, expected_code)
        result2 = _expand_test_case(tc, expected_code)

        assert result1["input"][0] == result2["input"][0], "Same seed must produce same input"
        assert result1["expected"] == result2["expected"], "Same input must produce same expected"
        assert len(result1["input"][0]) == 5000
        assert isinstance(result1["expected"], int)

    # ── Test 3 ───────────────────────────────────────────────────────────────
    def test_random_graph_dag_all_edges_satisfy_u_less_than_v(self):
        """Test 3: random_graph with dag=True — all edges have u < v."""
        graph = _gen_random_graph(n_nodes=200, n_edges=500, seed=7, dag=True)

        assert "nodes" in graph
        assert "edges" in graph
        assert graph["nodes"] == list(range(200))

        for edge in graph["edges"]:
            u, v = edge[0], edge[1]
            assert u < v, f"DAG edge {edge} violates u < v"

        # No self-loops
        assert all(e[0] != e[1] for e in graph["edges"])

    # ── Test 4 ───────────────────────────────────────────────────────────────
    def test_invariant_gen_input_requires_compute_reference(self):
        """Test 4: generator input + literal expected → raises ValueError."""
        tc = {
            "input": [{"gen": "random_ints", "n": 100, "seed": 1, "low": 0, "high": 10}],
            "expected": 42,          # literal — violates invariant
        }
        with pytest.raises(ValueError, match="compute.*reference"):
            _expand_test_case(tc, "def solve(x): return sum(x)")

    # ── Test 5 ───────────────────────────────────────────────────────────────
    def test_invariant_compute_reference_requires_gen_input(self):
        """Test 5: compute=reference without generator input → raises ValueError."""
        tc = {
            "input": [[1, 2, 3]],    # all literal — violates invariant
            "expected": {"compute": "reference"},
        }
        with pytest.raises(ValueError, match="generator-spec input"):
            _expand_test_case(tc, "def solve(lst): return sum(lst)")

    # ── Test 6 ───────────────────────────────────────────────────────────────
    def test_unknown_generator_name_raises(self):
        """Test 6: unknown generator name → raises ValueError."""
        tc = {
            "input": [{"gen": "nonexistent_generator", "n": 10, "seed": 1}],
            "expected": {"compute": "reference"},
        }
        with pytest.raises(ValueError, match="unknown generator"):
            _expand_test_case(tc, "def solve(x): return x")

    # ── Test 7 ───────────────────────────────────────────────────────────────
    def test_e2e_expansion_and_reference_execution(self):
        """Test 7: end-to-end expansion + reference computation.

        Mimics a Top-K Heavy Hitters hidden test.  Uses a synthetic question
        dict to stay independent of the real JSON files (which are converted
        in separate commits).  Verifies determinism across two expansion runs.
        """
        from python_evaluator import _expand_test_case

        expected_code = textwrap.dedent("""
            from collections import Counter
            def solve(events, k):
                return [x for x, _ in Counter(events).most_common(k)]
        """)

        tc = {
            "input": [
                {
                    "gen": "random_ints",
                    "n": 10_000,
                    "seed": 42,
                    "low": 0,
                    "high": 99,
                    "distribution": "zipf",
                },
                5,   # k — literal
            ],
            "expected": {"compute": "reference"},
        }

        expanded = _expand_test_case(tc, expected_code)

        # Structural checks
        assert isinstance(expanded["input"][0], list), "Generator output should be a list"
        assert len(expanded["input"][0]) == 10_000
        assert expanded["input"][1] == 5, "Literal args pass through unchanged"

        top5 = expanded["expected"]
        assert isinstance(top5, list), "Expected should be a list of top-K items"
        assert len(top5) == 5

        # All returned items must actually appear in the events
        event_set = set(expanded["input"][0])
        assert all(item in event_set for item in top5)

        # Determinism: same spec → identical result on a second expansion
        expanded2 = _expand_test_case(tc, expected_code)
        assert expanded["input"][0] == expanded2["input"][0]
        assert expanded["expected"] == expanded2["expected"]


class TestGeneratorProperties:
    """Property tests for the six individual generator functions."""

    def test_random_ints_uniform_range(self):
        vals = _gen_random_ints(n=1000, seed=1, low=5, high=15, distribution="uniform")
        assert len(vals) == 1000
        assert all(5 <= v <= 15 for v in vals)

    def test_random_ints_low_cardinality_bounded(self):
        vals = _gen_random_ints(n=1000, seed=2, low=0, high=100, distribution="low_cardinality")
        assert len(vals) == 1000
        # Should use at most ~10 distinct values
        assert len(set(vals)) <= 15  # allow small variance in pool construction

    def test_random_ints_high_cardinality_near_unique(self):
        vals = _gen_random_ints(n=500, seed=3, low=0, high=10_000, distribution="high_cardinality")
        assert len(vals) == 500
        assert len(set(vals)) == 500  # exactly unique (rng.sample)

    def test_random_ints_zipf_all_in_range(self):
        vals = _gen_random_ints(n=1000, seed=4, low=0, high=99, distribution="zipf")
        assert len(vals) == 1000
        assert all(0 <= v <= 99 for v in vals)

    def test_sorted_ints_is_sorted(self):
        vals = _gen_sorted_ints(n=200, seed=5, low=0, high=1000)
        assert vals == sorted(vals)
        assert len(vals) == 200

    def test_sorted_ints_unique_no_duplicates(self):
        vals = _gen_sorted_ints(n=100, seed=6, low=0, high=999, unique=True)
        assert len(vals) == len(set(vals))
        assert vals == sorted(vals)

    def test_sorted_ints_unique_raises_if_too_large(self):
        with pytest.raises(ValueError, match="exceeds range size"):
            _gen_sorted_ints(n=1001, seed=7, low=0, high=999, unique=True)

    def test_all_six_generators_in_registry(self):
        expected = {
            "random_ints",
            "random_floats",
            "random_strings",
            "sorted_ints",
            "random_pairs",
            "random_graph",
        }
        assert set(_GENERATORS.keys()) == expected
