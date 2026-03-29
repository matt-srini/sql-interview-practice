"""
Python code evaluator — spawns python_sandbox_harness.py in a subprocess,
enforces a timeout, and compares results.
"""
from __future__ import annotations

import json
import logging
import os
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
    return result


def evaluate_python_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user code against ALL test cases (including hidden) for submit.
    Returns correct/incorrect verdict and per-case breakdown (hidden cases summarized).
    """
    test_cases = question.get("test_cases", [])
    public_count = question.get("public_test_cases", len(test_cases))

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
        "public_results": public_results,
        "hidden_summary": {
            "passed": hidden_passed,
            "total": hidden_total,
        } if hidden_total > 0 else None,
    }


def run_python_data_code(code: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run user pandas/numpy code and return the resulting DataFrame.
    Used by /run-code endpoint for the Pandas track.
    """
    dataframes = question.get("dataframes", {})
    payload = {
        "mode": "data",
        "code": code,
        "dataframes": dataframes,
        "csv_dir": str(DATASETS_DIR),
    }
    return _spawn_harness(payload)


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
            "print_output": user_output.get("print_output", ""),
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
            "print_output": user_output.get("print_output", ""),
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
        "print_output": user_output.get("print_output", ""),
    }
