"""
Sandbox harness executed inside a subprocess.

Reads a JSON payload from stdin, runs user code in a restricted namespace,
and writes a JSON result to stdout.

Two modes:
  - "algorithm": run solve(*args) against test cases
  - "data": run solve(**dataframes) and return DataFrame as JSON
"""
import json
import sys
import traceback
import io

try:
    import resource
    # Memory cap: 512 MB virtual address space
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    # CPU cap: 6 seconds (slightly above the 5s subprocess timeout so the
    # timeout fires first, but this catches any slippage and prevents a
    # tight CPU loop from monopolising a core).
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
except Exception:
    pass


_MAX_STDOUT_BYTES = 64 * 1024        # 64 KB per run
_MAX_RESULT_ITEMS = 10_000           # max items in a returned list
_MAX_RESULT_JSON_BYTES = 512 * 1024  # 512 KB serialised result


class _BoundedStringIO(io.StringIO):
    """StringIO that silently truncates writes beyond _MAX_STDOUT_BYTES."""

    def write(self, s: str) -> int:
        remaining = _MAX_STDOUT_BYTES - self.tell()
        if remaining <= 0:
            return 0
        if len(s) > remaining:
            s = s[:remaining] + "\n[output truncated]"
        return super().write(s)


def _run_algorithm(user_code: str, test_cases: list) -> dict:
    namespace: dict = {}
    try:
        exec(compile(user_code, "<user_code>", "exec"), namespace)  # noqa: S102
    except Exception as e:
        return {"error": f"Code error: {e}", "results": []}

    solve_fn = namespace.get("solve")
    if solve_fn is None:
        return {"error": "No 'solve' function found in your code.", "results": []}

    results = []
    for case in test_cases:
        args = case.get("input", [])
        expected = case.get("expected")
        stdout_capture = _BoundedStringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture
        try:
            actual = solve_fn(*args)
            # Guard against enormous return values
            if isinstance(actual, (list, tuple)) and len(actual) > _MAX_RESULT_ITEMS:
                raise ValueError(f"Result has {len(actual):,} items — limit is {_MAX_RESULT_ITEMS:,}")
            passed = _compare(actual, expected)
            results.append({
                "input": args,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "stdout": stdout_capture.getvalue(),
                "error": None,
            })
        except Exception:
            results.append({
                "input": args,
                "expected": expected,
                "actual": None,
                "passed": False,
                "stdout": stdout_capture.getvalue(),
                "error": traceback.format_exc(limit=5),
            })
        finally:
            sys.stdout = old_stdout

    return {"error": None, "results": results}


def _compare(actual, expected) -> bool:
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return abs(float(actual) - float(expected)) < 1e-6
        except (TypeError, ValueError):
            return False
    # Sort lists for unordered comparison only if expected is also a list
    # and doesn't seem to represent an ordered sequence (heuristic: compare sorted)
    if isinstance(actual, list) and isinstance(expected, list):
        try:
            return sorted(actual) == sorted(expected) or actual == expected
        except TypeError:
            return actual == expected
    return actual == expected


def _run_data(user_code: str, dataframes_spec: dict, csv_dir: str) -> dict:
    import pandas as pd
    import numpy as np

    # Load DataFrames from CSV files
    dataframes: dict = {}
    for var_name, csv_filename in dataframes_spec.items():
        csv_path = f"{csv_dir}/{csv_filename}"
        try:
            dataframes[var_name] = pd.read_csv(csv_path)
        except Exception as e:
            return {"error": f"Failed to load {csv_filename}: {e}", "result": None, "print_output": ""}

    # Inject pandas + numpy into user namespace
    namespace: dict = {"pd": pd, "np": np}
    try:
        exec(compile(user_code, "<user_code>", "exec"), namespace)  # noqa: S102
    except Exception as e:
        return {"error": f"Code error: {e}", "result": None, "print_output": ""}

    solve_fn = namespace.get("solve")
    if solve_fn is None:
        return {"error": "No 'solve' function found in your code.", "result": None, "print_output": ""}

    stdout_capture = _BoundedStringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture
    try:
        result = solve_fn(**dataframes)
    except Exception:
        sys.stdout = old_stdout
        return {
            "error": traceback.format_exc(limit=5),
            "result": None,
            "print_output": stdout_capture.getvalue(),
        }
    finally:
        sys.stdout = old_stdout

    print_output = stdout_capture.getvalue()

    # Convert result to JSON-serializable form
    if isinstance(result, pd.DataFrame):
        result_json = result.to_dict(orient="records")
        columns = list(result.columns)
    elif isinstance(result, np.ndarray):
        df = pd.DataFrame({"result": result.flatten()})
        result_json = df.to_dict(orient="records")
        columns = ["result"]
    elif isinstance(result, pd.Series):
        df = result.reset_index(drop=True).to_frame(name="result")
        result_json = df.to_dict(orient="records")
        columns = ["result"]
    else:
        return {"error": f"solve() must return a DataFrame, Series, or ndarray, got {type(result).__name__}", "result": None, "print_output": print_output}

    if len(result_json) > _MAX_RESULT_ITEMS:
        return {"error": f"Result has {len(result_json):,} rows — limit is {_MAX_RESULT_ITEMS:,}", "result": None, "print_output": print_output}

    return {
        "error": None,
        "result": {"columns": columns, "rows": result_json},
        "print_output": print_output,
    }


def main():
    payload = json.loads(sys.stdin.read())
    mode = payload.get("mode", "algorithm")
    user_code = payload.get("code", "")

    if mode == "algorithm":
        test_cases = payload.get("test_cases", [])
        output = _run_algorithm(user_code, test_cases)
    elif mode == "data":
        dataframes_spec = payload.get("dataframes", {})
        csv_dir = payload.get("csv_dir", ".")
        output = _run_data(user_code, dataframes_spec, csv_dir)
    else:
        output = {"error": f"Unknown mode: {mode}"}

    sys.stdout.write(json.dumps(output))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
