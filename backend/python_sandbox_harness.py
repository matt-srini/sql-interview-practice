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
import types

try:
    import resource
    # Memory cap: 512 MB virtual address space
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    # CPU cap: a backstop above the longest subprocess wall timeout (data mode's
    # 12s, so 15s sits just above it). The per-mode wall timeout in python_evaluator
    # is the primary guard and fires first; this only catches a tight CPU loop that
    # slips past it.
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
except Exception:
    pass


_MAX_STDOUT_BYTES = 64 * 1024        # 64 KB per run
_MAX_RESULT_ITEMS = 10_000           # max items in a returned list (algorithm mode)
_MAX_RESULT_JSON_BYTES = 512 * 1024  # 512 KB serialised result
# Data (pandas) mode: the grader compares the FULL result and the evaluator returns
# only a ~200-row preview to the client (see python_evaluator), so the row count here
# is just a high safety bound against pathological outputs — legitimate per-row
# transformations over the largest dataset (events ≈ 45k rows) sit well under it.
_MAX_DATA_RESULT_ROWS = 100_000


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
        expected = case.get("expected") if "expected" in case else case.get("expected_output")
        tol = case.get("tolerance", 1e-6)
        stdout_capture = _BoundedStringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture
        try:
            actual = solve_fn(*args)
            if isinstance(actual, types.GeneratorType):
                actual = list(actual)
            # Guard against enormous return values.
            # Exception: when the expected output is a matching-size list/tuple (e.g.
            # a generator-spec hidden test), allow the comparison — the 512 MB memory
            # limit and CPU timeout are the real safety bounds in that case.
            if isinstance(actual, (list, tuple)) and len(actual) > _MAX_RESULT_ITEMS:
                if isinstance(expected, (list, tuple)) and len(expected) == len(actual):
                    passed = _compare(actual, expected, tol)
                    results.append({
                        "input": f"<{len(args)} arg(s)>",
                        "expected": f"<{len(expected):,} items>",
                        "actual": f"<{len(actual):,} items>",
                        "passed": passed,
                        "stdout": stdout_capture.getvalue(),
                        "error": None,
                    })
                    continue
                raise ValueError(f"Result has {len(actual):,} items — limit is {_MAX_RESULT_ITEMS:,}")
            passed = _compare(actual, expected, tol)
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

    print_output = "\n".join(r["stdout"] for r in results if r.get("stdout"))
    return {"error": None, "results": results, "print_output": print_output}


def _normalize(value):
    """Normalize containers and dict-key types to compensate for JSON serialization limits.

    JSON loses two Python type distinctions that matter for grading:
    - Tuples serialize to arrays, indistinguishable from lists.
    - Dict keys are always strings, even when authored as integers.
    Applied recursively so nested structures are handled correctly.
    """
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        normalized = {}
        for k, v in value.items():
            if isinstance(k, str):
                try:
                    k = int(k)
                except ValueError:
                    pass
            normalized[k] = _normalize(v)
        return normalized
    return value


def _compare(actual, expected, tolerance: float = 1e-6) -> bool:
    # Honor a test case's declared numeric tolerance (e.g. statistics Monte-Carlo /
    # numerical-method answers), never grading STRICTER than the 1e-6 default — so a
    # tighter declared tolerance can't break a currently-passing question, while a
    # larger one accepts correct-but-approximate answers as the author intended.
    eff_tol = max(tolerance, 1e-6)

    def _num_close(a, e) -> bool:
        # `a == e` first so exact / infinite values match (abs(inf-inf) is nan).
        try:
            return a == e or abs(float(a) - float(e)) <= eff_tol
        except (TypeError, ValueError):
            return False

    if isinstance(expected, float) or isinstance(actual, float):
        return _num_close(actual, expected)
    actual_n = _normalize(actual)
    expected_n = _normalize(expected)
    # Element-wise numeric tolerance for equal-length numeric sequences, preserving
    # the original order-insensitive matching (sorted) AND order-sensitive matching.
    if (isinstance(actual_n, list) and isinstance(expected_n, list)
            and len(actual_n) == len(expected_n) and actual_n
            and all(isinstance(a, (int, float)) for a in actual_n)
            and all(isinstance(e, (int, float)) for e in expected_n)):
        def _within(seq_a, seq_b):
            return all(_num_close(a, e) for a, e in zip(seq_a, seq_b))
        return _within(actual_n, expected_n) or _within(sorted(actual_n), sorted(expected_n))
    if isinstance(actual_n, list) and isinstance(expected_n, list):
        try:
            return sorted(actual_n) == sorted(expected_n) or actual_n == expected_n
        except TypeError:
            return actual_n == expected_n
    return actual_n == expected_n


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

    # Inject pandas + numpy into user namespace, with I/O functions stubbed
    # out as defense-in-depth (the AST guard is the primary control; this
    # ensures filesystem/network access is impossible even if the guard is
    # somehow bypassed at the source-code level).
    def _blocked_io(*_args, **_kwargs):
        raise PermissionError("File and network I/O is not allowed in the sandbox.")

    _PANDAS_IO = [
        "read_csv", "read_table", "read_fwf", "read_json", "read_html",
        "read_xml", "read_excel", "read_parquet", "read_feather", "read_orc",
        "read_sas", "read_spss", "read_stata", "read_hdf", "read_sql",
        "read_sql_table", "read_sql_query", "read_clipboard", "read_pickle",
    ]
    _NUMPY_IO = [
        "load", "loadtxt", "genfromtxt", "fromfile",
        "save", "savez", "savez_compressed", "savetxt",
    ]

    safe_pd = pd
    safe_np = np
    for _fn in _PANDAS_IO:
        try:
            setattr(safe_pd, _fn, _blocked_io)
        except (AttributeError, TypeError):
            pass
    for _fn in _NUMPY_IO:
        try:
            setattr(safe_np, _fn, _blocked_io)
        except (AttributeError, TypeError):
            pass

    namespace: dict = {"pd": safe_pd, "np": safe_np}
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

    if len(result_json) > _MAX_DATA_RESULT_ROWS:
        return {"error": f"Result has {len(result_json):,} rows — limit is {_MAX_DATA_RESULT_ROWS:,}", "result": None, "print_output": print_output}

    return {
        "error": None,
        "result": {"columns": columns, "rows": result_json},
        "print_output": print_output,
    }


def _json_default(o):
    """Serialize types json.dumps cannot handle natively.

    Mirrors the SQL evaluator's `_to_json_native`: pandas.Timestamp / datetime /
    date all expose ``isoformat()`` and become ISO strings; numpy scalars expose
    ``item()`` and become native Python scalars. This is what lets a pandas
    question return a date/time column without crashing the harness — the grader
    then date-normalizes the ISO strings in ``evaluator.normalize_dataframe`` so a
    user is not penalized for a trivial datetime-vs-date representation difference.
    Import-free (duck-typed) so the algorithm mode pays no import cost.
    """
    iso = getattr(o, "isoformat", None)
    if callable(iso):
        return iso()
    item = getattr(o, "item", None)  # numpy scalars (np.int64/np.float64/np.bool_)
    if callable(item):
        return item()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


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

    sys.stdout.write(json.dumps(output, default=_json_default))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
