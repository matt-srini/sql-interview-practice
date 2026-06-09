"""
audit_code_tracks.py — Phase 3 execution-based blind audit of the 3 CODE tracks
(SQL / Python / Pandas). These tracks were never audited in Phases 1-2 (MCQ-only).

The oracle is EXECUTION, not model opinion. The stored expected answer is already
execution-validated at authoring time, so we do NOT re-check "does it run." Phase 3
hunts a DIFFERENT defect class: AMBIGUOUS / NON-UNIQUE / UNDER-SPECIFIED prompts and
WRONG expected outputs.

Two layers per question:

  (1) DETERMINISTIC expected-reproduction check (free, no model):
      * Python: run the stored expected_code against its OWN test_cases via the real
        evaluator. A failure means expected_code disagrees with a stored expected
        value → WRONG EXPECTED OUTPUT (high-confidence key defect).
      * SQL / Pandas: expected is computed live from expected_query/expected_code, so
        there is no static answer to contradict — we only confirm it executes and
        returns rows (catches a broken reference).

  (2) BLIND-SOLVE + EXECUTE (gpt-5-mini external solver):
      * Give the solver ONLY the prompt the user sees (description / schema /
        starter_code / dataframes / public test cases) — NOT expected_*/solution_*/
        explanation/hidden cases.
      * Run the candidate through the SAME guard + evaluator a real user hits
        (sql_guard via evaluate(); python_guard explicitly for py/pandas).
      * candidate reproduces (matches expected) → key good, prompt unambiguous enough.
        candidate runs but yields a DIFFERENT result → AMBIGUITY / non-unique-answer
        candidate (flag). candidate guard-rejected though logically sound → guard_reject
        (the SQL CROSS JOIN lesson). candidate repeatedly fails → under-specified (flag).
      * A second blind-solve attempt is made on any non-reproduce, so solver flakiness
        (2nd attempt reproduces) is not mistaken for genuine ambiguity.

Every flag is recorded WITH the candidate solution + error so Opus can adjudicate
against source. Resumable per-question via a sidecar. Output: a JSON report.

Usage
-----
python backend/scripts/audit_code_tracks.py --track python --scope all
python backend/scripts/audit_code_tracks.py --track sql --limit 4 --output _smoke.json
python backend/scripts/audit_code_tracks.py --no-solve   # deterministic layer only (free)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env", override=True)
except ImportError:
    pass

import openai  # noqa: E402

import database  # noqa: E402
from evaluator import evaluate, run_query  # noqa: E402
from python_evaluator import (  # noqa: E402
    evaluate_python_code, evaluate_pandas_code, run_pandas_code,
)
from python_guard import validate_code  # noqa: E402
from exceptions import BadRequestError  # noqa: E402

# ---------------------------------------------------------------------------
TRACKS: dict[str, dict[str, str]] = {
    "sql":    {"dir": "content/questions",            "kind": "sql"},
    "python": {"dir": "content/python_questions",     "kind": "python"},
    "pandas": {"dir": "content/pandas_questions", "kind": "pandas"},
    # Statistics-numerical: graded via python_evaluator.evaluate_python_code (same as
    # the Python track), but the candidate guard runs under the "statistics" allowlist
    # (numpy/statistics allowed). Only the numerical subtype is code; conceptual is MCQ
    # and is covered by the MCQ harness.
    "statistics": {"dir": "content/statistics_questions", "kind": "python",
                   "subtype": "numerical", "guard_topic": "statistics"},
}
DIFFICULTIES = ["easy", "medium", "hard"]
TRACK_ORDER = list(TRACKS.keys())

SOLVER_MODEL = "gpt-5-mini"
SOLVE_BUDGET = 3000
MAX_RETRIES = 5
BACKOFF_BASE = 4

_TOKEN_LOCK = threading.Lock()
_TOKENS = {"in": 0, "out": 0, "calls": 0}

# The shared in-memory DuckDB golden connection is NOT safe for concurrent
# execution across threads (cursors share one connection → segfaults). Serialize
# all SQL engine access with this lock so API calls can still parallelize.
_DUCKDB_LOCK = threading.Lock()


def _rec(usage: Any) -> None:
    if usage is None:
        return
    with _TOKEN_LOCK:
        _TOKENS["in"] += getattr(usage, "prompt_tokens", 0) or 0
        _TOKENS["out"] += getattr(usage, "completion_tokens", 0) or 0
        _TOKENS["calls"] += 1


def _cost(t: dict[str, int]) -> float:
    return (t["in"] * 0.25 + t["out"] * 2.0) / 1_000_000  # gpt-5-mini pricing


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------
def load_questions(track: str, difficulties: list[str], scope: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    track_dir = BACKEND_DIR / TRACKS[track]["dir"]
    for diff in difficulties:
        fp = track_dir / f"{diff}.json"
        if not fp.exists():
            continue
        subtype = TRACKS[track].get("subtype")
        for q in json.loads(fp.read_text(encoding="utf-8")):
            if subtype is not None and q.get("subtype") != subtype:
                continue  # statistics: numerical (code) only; conceptual is MCQ
            mock = bool(q.get("mock_only", False))
            if scope == "practice" and mock:
                continue
            if scope == "mock" and not mock:
                continue
            q["_track"] = track
            q["_difficulty"] = diff
            out.append(q)
    return out


# ---------------------------------------------------------------------------
# Blind-solver (gpt-5-mini)
# ---------------------------------------------------------------------------
def _client() -> openai.OpenAI:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("ERROR: OPENAI_API_KEY missing.", file=sys.stderr)
        sys.exit(1)
    return openai.OpenAI(api_key=key, timeout=180.0, max_retries=0)


SQL_SYS = ("You are an expert analytics SQL engineer. Write a single read-only SELECT "
           "query (DuckDB dialect) that answers the task. Output ONLY the SQL inside a "
           "```sql code block — no prose, no explanation.")
PY_SYS = ("You are an expert Python engineer. Implement the required function exactly as "
          "specified. Output ONLY the complete Python code inside a ```python code block "
          "— no prose. Do not import anything unless essential; the grader runs algorithm "
          "code with no imports allowed.")
PD_SYS = ("You are an expert pandas engineer. Implement the required solve(**dataframes) "
          "function. Output ONLY the complete Python code inside a ```python code block — "
          "no prose. Only pandas (as pd) and numpy (as np) are available.")


def build_solver_prompt(q: dict[str, Any], kind: str) -> tuple[str, str]:
    desc = (q.get("description") or "").strip()
    title = (q.get("title") or "").strip()
    if kind == "sql":
        schema = q.get("schema", {})
        schema_txt = "\n".join(f"  {t}({', '.join(cols)})" for t, cols in schema.items())
        user = (f"Task: {title}\n\n{desc}\n\nTables and columns:\n{schema_txt}\n\n"
                "Return the SQL SELECT query that produces the required result.")
        return SQL_SYS, user
    if kind == "python":
        starter = (q.get("starter_code") or "").strip()
        # Public test cases are visible to the user — include them.
        pub_n = q.get("public_test_cases")
        tcs = q.get("test_cases", [])
        if isinstance(pub_n, int):
            tcs = tcs[:pub_n]
        ex = "\n".join(
            f"  solve({', '.join(json.dumps(a) for a in tc.get('input', []))}) == "
            f"{json.dumps(tc.get('expected', tc.get('expected_output')))}"
            for tc in tcs[:4]
        )
        user = (f"Task: {title}\n\n{desc}\n\nStarter signature:\n{starter}\n\n"
                f"Examples:\n{ex}\n\nImplement the complete `solve` function.")
        return PY_SYS, user
    # pandas
    starter = (q.get("starter_code") or "").strip()
    schema = q.get("schema", {})
    schema_txt = "\n".join(f"  {v}({', '.join(cols)})" for v, cols in schema.items())
    dfs = q.get("dataframes", {})
    df_txt = ", ".join(f"{var} (from {csv})" for var, csv in dfs.items())
    user = (f"Task: {title}\n\n{desc}\n\nDataFrames passed as kwargs: {df_txt}\n"
            f"Columns:\n{schema_txt}\n\nStarter signature:\n{starter}\n\n"
            "Implement the complete `solve` function returning the required DataFrame.")
    return PD_SYS, user


_FENCE = re.compile(r"```(?:sql|python|py)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code(raw: str) -> str:
    m = _FENCE.search(raw)
    code = m.group(1).strip() if m else raw.strip()
    return code


def solve_blind(client: openai.OpenAI, q: dict[str, Any], kind: str) -> str:
    system, user = build_solver_prompt(q, kind)

    def _one(budget: int) -> tuple[str, str, Any]:
        resp = client.chat.completions.create(
            model=SOLVER_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_completion_tokens=budget,
        )
        ch = resp.choices[0]
        return (ch.message.content or "").strip(), getattr(ch, "finish_reason", "") or "", resp.usage

    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            text, finish, usage = _one(SOLVE_BUDGET)
            if (not text) and finish == "length":
                _rec(usage)
                text, finish, usage = _one(SOLVE_BUDGET * 2)
            _rec(usage)
            return extract_code(text)
        except (openai.RateLimitError, openai.APITimeoutError,
                openai.APIConnectionError, openai.InternalServerError) as exc:
            last = exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                last = exc
            else:
                raise
        wait = min(60, BACKOFF_BASE * (2 ** attempt)) + attempt * 0.7
        print(f"  [retry] solve attempt {attempt+1} ({type(last).__name__}) wait {wait:.1f}s",
              file=sys.stderr, flush=True)
        time.sleep(wait)
    raise RuntimeError(f"solver failed after {MAX_RETRIES}") from last


# ---------------------------------------------------------------------------
# Execution oracles
# ---------------------------------------------------------------------------
def deterministic_check(q: dict[str, Any], kind: str) -> dict[str, Any]:
    """Free expected-reproduction / sanity check. Returns {ok, detail, defect}."""
    try:
        if kind == "python":
            res = evaluate_python_code(q.get("expected_code", ""), q)
            if res.get("error"):
                return {"ok": False, "defect": "expected_runtime_error",
                        "detail": str(res["error"])[:300]}
            if not res.get("correct"):
                hs = res.get("hidden_summary")
                pub = [r for r in res.get("test_results", []) if not r.get("passed")]
                return {"ok": False, "defect": "wrong_expected_output",
                        "detail": f"expected_code fails own tests; hidden={hs}; "
                                  f"failed_public={[ (r.get('input'), r.get('expected'), r.get('actual')) for r in pub][:3]}"}
            return {"ok": True, "defect": None, "detail": "expected_code reproduces all test cases"}

        if kind == "pandas":
            out = run_pandas_code(q.get("expected_code", ""), q)
            if out.get("error"):
                return {"ok": False, "defect": "expected_runtime_error", "detail": str(out["error"])[:300]}
            rows = (out.get("result") or {}).get("rows", out.get("rows"))
            n = len(rows) if rows is not None else 0
            return {"ok": True, "defect": None, "detail": f"expected_code runs, {n} rows"}

        # sql
        with _DUCKDB_LOCK:
            res = run_query(q.get("expected_query", ""), q)
        return {"ok": True, "defect": None, "detail": f"expected_query runs, {len(res['rows'])} rows"}
    except Exception as exc:
        return {"ok": False, "defect": "expected_runtime_error", "detail": f"{type(exc).__name__}: {exc}"[:300]}


def run_candidate(q: dict[str, Any], kind: str, code: str) -> dict[str, Any]:
    """Execute candidate vs stored expected through the real guard+evaluator.

    Returns {status, detail} where status ∈
      reproduces | mismatch | guard_reject | candidate_error
    """
    if not code.strip():
        return {"status": "candidate_error", "detail": "solver returned empty code"}
    try:
        if kind == "sql":
            # evaluate() runs the candidate through sql_guard (raises BadRequestError on reject)
            with _DUCKDB_LOCK:
                res = evaluate(code, q["expected_query"], q)
            return {"status": "reproduces" if res["correct"] else "mismatch",
                    "detail": "result match" if res["correct"] else "result differs"}
        if kind == "python":
            guard_topic = TRACKS.get(q.get("_track"), {}).get("guard_topic", "python")
            errs = validate_code(code, guard_topic)
            if errs:
                return {"status": "guard_reject", "detail": "; ".join(errs)[:300]}
            res = evaluate_python_code(code, q)
            if res.get("error") and not res.get("test_results"):
                return {"status": "candidate_error", "detail": str(res["error"])[:300]}
            return {"status": "reproduces" if res.get("correct") else "mismatch",
                    "detail": f"hidden={res.get('hidden_summary')}"}
        # pandas
        errs = validate_code(code, "pandas")
        if errs:
            return {"status": "guard_reject", "detail": "; ".join(errs)[:300]}
        res = evaluate_pandas_code(code, q)
        if res.get("error"):
            return {"status": "candidate_error", "detail": str(res["error"])[:300]}
        return {"status": "reproduces" if res.get("correct") else "mismatch",
                "detail": "result match" if res.get("correct") else "result differs"}
    except BadRequestError as exc:
        return {"status": "guard_reject", "detail": str(exc)[:300]}
    except Exception as exc:
        return {"status": "candidate_error", "detail": f"{type(exc).__name__}: {exc}"[:300]}


# ---------------------------------------------------------------------------
# Per-question pipeline
# ---------------------------------------------------------------------------
def process_question(q: dict[str, Any], client: openai.OpenAI | None,
                     do_solve: bool, attempts: int) -> dict[str, Any]:
    kind = TRACKS[q["_track"]]["kind"]
    det = deterministic_check(q, kind)

    solve_results: list[dict[str, Any]] = []
    final_status = "skipped"
    if do_solve and client is not None:
        for i in range(attempts):
            try:
                code = solve_blind(client, q, kind)
            except Exception as exc:
                solve_results.append({"attempt": i + 1, "status": "solver_api_error",
                                      "detail": str(exc)[:200], "code": ""})
                final_status = "solver_api_error"
                continue
            run = run_candidate(q, kind, code)
            solve_results.append({"attempt": i + 1, "status": run["status"],
                                  "detail": run["detail"], "code": code[:2000]})
            final_status = run["status"]
            if run["status"] == "reproduces":
                break  # solved — no need for more attempts

    # Overall verdict
    if not det["ok"]:
        verdict = "DETERMINISTIC_DEFECT"
    elif final_status in ("reproduces", "skipped"):
        verdict = "ok"
    elif final_status == "guard_reject":
        verdict = "GUARD_REJECT"
    elif final_status == "solver_api_error":
        verdict = "solver_api_error"
    else:  # mismatch / candidate_error after all attempts
        verdict = "BLIND_FLAG"

    return {
        "id": q.get("id"),
        "track": q["_track"],
        "difficulty": q["_difficulty"],
        "mock_only": bool(q.get("mock_only", False)),
        "title": q.get("title", ""),
        "deterministic_ok": det["ok"],
        "deterministic_defect": det["defect"],
        "deterministic_detail": det["detail"],
        "blind_final_status": final_status,
        "blind_attempts": solve_results,
        "verdict": verdict,
    }


def is_clean(r: dict[str, Any]) -> bool:
    # Don't checkpoint API-error questions (retry on resume); deterministic-only is fine.
    return r.get("blind_final_status") != "solver_api_error"


# ---------------------------------------------------------------------------
# Orchestration (resumable sidecar)
# ---------------------------------------------------------------------------
def run(questions, client, do_solve, attempts, workers, output_path):
    sidecar = Path(str(output_path) + ".partial.jsonl")
    lock = threading.Lock()
    done: dict[int, dict[str, Any]] = {}
    if sidecar.exists():
        for line in sidecar.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("id") is not None:
                    done[r["id"]] = r
            except json.JSONDecodeError:
                pass
        if done:
            print(f"[resume] {len(done)} done loaded", file=sys.stderr, flush=True)

    remaining = [q for q in questions if q.get("id") not in done]
    total = len(questions)
    print(f"[audit] {len(done)} done, {len(remaining)} to go (total {total}), workers={workers}",
          file=sys.stderr, flush=True)

    if remaining:
        completed = 0

        def task(q):
            r = process_question(q, client, do_solve, attempts)
            if is_clean(r):
                with lock:
                    with open(sidecar, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            return r

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(task, q): q for q in remaining}
            for fut in as_completed(futs):
                try:
                    r = fut.result()
                    done[r["id"]] = r
                except Exception as exc:
                    print(f"  [error] {futs[fut].get('id')}: {exc}", file=sys.stderr, flush=True)
                completed += 1
                if completed % 10 == 0 or completed == len(remaining):
                    print(f"[audit] {len(done)}/{total} …", file=sys.stderr, flush=True)

    results = list(done.values())
    results.sort(key=lambda r: (TRACK_ORDER.index(r["track"]) if r["track"] in TRACK_ORDER else 9,
                                r["id"] if r["id"] is not None else 0))
    return results


def write_report(results, output_path, track, scope, do_solve):
    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    with _TOKEN_LOCK:
        tok = dict(_TOKENS)
    flagged = [r for r in results if r["verdict"] not in ("ok", "skipped", "solver_api_error")]
    report = {
        "meta": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "phase": "phase3-code-execution",
            "solver_model": SOLVER_MODEL if do_solve else None,
            "track": track, "scope": scope, "do_solve": do_solve,
            "total": len(results), "counts_by_verdict": counts,
            "flagged_ids": sorted(r["id"] for r in flagged),
            "token_usage": tok, "est_cost_usd": round(_cost(tok), 4),
        },
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {output_path}", file=sys.stderr, flush=True)

    print("\n" + "=" * 56, file=sys.stderr)
    print(f"CODE AUDIT SUMMARY  track={track} scope={scope}", file=sys.stderr)
    print("=" * 56, file=sys.stderr)
    for v, n in sorted(counts.items()):
        print(f"  {v:<22} {n:>5}", file=sys.stderr)
    print(f"  tokens in/out={tok['in']}/{tok['out']} ({tok['calls']} calls) "
          f"≈ ${_cost(tok):.4f}", file=sys.stderr)
    if flagged:
        print(f"\nFlagged ({len(flagged)}):", file=sys.stderr)
        for r in flagged:
            print(f"  {r['id']:<7} {r['track']:<7} {r['difficulty']:<7} mock={int(r['mock_only'])} "
                  f"{r['verdict']:<22} {r['deterministic_defect'] or r['blind_final_status']}",
                  file=sys.stderr)
    else:
        print("\nNo flags.", file=sys.stderr)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--track", choices=list(TRACKS.keys()), required=True)
    p.add_argument("--difficulty", choices=DIFFICULTIES, default=None)
    p.add_argument("--scope", choices=["practice", "mock", "all"], default="all")
    p.add_argument("--no-solve", action="store_true", help="Deterministic layer only (free).")
    p.add_argument("--attempts", type=int, default=2, help="Blind-solve attempts before flagging.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--output", default=None)
    return p.parse_args()


def main():
    args = parse_args()
    database.init_query_engine()  # SQL needs the DuckDB golden connection
    diffs = [args.difficulty] if args.difficulty else DIFFICULTIES
    questions = load_questions(args.track, diffs, args.scope)
    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        print("No questions matched.", file=sys.stderr)
        sys.exit(0)

    do_solve = not args.no_solve
    client = _client() if do_solve else None
    output_path = Path(args.output) if args.output else \
        SCRIPT_DIR / f"audit_code_{args.track}_{args.scope}.json"

    print(f"\n{'='*56}\n  Track: {args.track}  scope={args.scope}  Q={len(questions)}\n"
          f"  solve={do_solve} attempts={args.attempts} workers={args.workers}\n"
          f"  output={output_path}\n{'='*56}\n", file=sys.stderr, flush=True)

    results = run(questions, client, do_solve, args.attempts, args.workers, output_path)
    write_report(results, output_path, args.track, args.scope, do_solve)


if __name__ == "__main__":
    main()
