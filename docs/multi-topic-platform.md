# Multi-Topic Platform — Implementation Guide

This document is the authoritative implementation reference for expanding the platform from SQL-only to four practice tracks: **SQL**, **Python**, **Python (Data)**, and **PySpark**. An agent implementing any phase of this work should read this file first.

---

## Overview

| Track | Mode | Engine | Questions |
|---|---|---|---|
| SQL | Code execution | DuckDB (existing) | 86 |
| Python | Code execution | Subprocess sandbox | 30 (MVP) |
| Python (Data) | Code execution | Subprocess sandbox | 30 (MVP) |
| PySpark | Knowledge check | None (MCQ only) | 30 (MVP) |

---

## 1. Database Migration

**File to create:** `backend/alembic/versions/YYYYMMDD_add_topic_to_progress.py`

Add `topic` column to both progress tables:

```sql
-- user_challenge_progress
ALTER TABLE user_challenge_progress
  ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'sql';
ALTER TABLE user_challenge_progress
  DROP CONSTRAINT IF EXISTS user_challenge_progress_pkey;
ALTER TABLE user_challenge_progress
  ADD PRIMARY KEY (user_id, question_id, topic);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_user_topic
  ON user_challenge_progress(user_id, topic);

-- user_sample_progress (or user_sample_seen — check actual table name in db.py)
ALTER TABLE user_sample_seen
  ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'sql';
ALTER TABLE user_sample_seen
  DROP CONSTRAINT IF EXISTS user_sample_seen_pkey;
ALTER TABLE user_sample_seen
  ADD PRIMARY KEY (user_id, topic, difficulty, question_id);
```

Valid topic values: `'sql'`, `'python'`, `'python_data'`, `'pyspark'`

---

## 2. Backend — db.py Changes

**File:** `backend/db.py`

Add `topic: str = "sql"` parameter to every function that reads or writes progress:

```python
# Before
async def get_solved_question_ids(user_id: int) -> set[int]:
    ...WHERE user_id = $1

# After
async def get_solved_question_ids(user_id: int, topic: str = "sql") -> set[int]:
    ...WHERE user_id = $1 AND topic = $2
```

Functions to update:
- `get_solved_question_ids(user_id)` → add `topic`
- `mark_question_solved(user_id, question_id)` → add `topic`
- `get_seen_sample_ids(user_id, difficulty)` → add `topic`
- `mark_sample_seen(user_id, difficulty, question_id)` → add `topic`
- Any other function querying `user_challenge_progress` or `user_sample_seen`

All call sites pass `topic` explicitly. Default `"sql"` maintains backwards compatibility for existing SQL routes.

---

## 3. Backend — New Execution Files

### 3a. `backend/python_guard.py`

AST-based validator applied before running user code. Used by both Python and Python (Data) tracks.

```python
import ast
from fastapi import HTTPException

# For Python (algorithms) track: nothing is allowed to import
BLOCKED_CALLS = {"open", "exec", "eval", "compile", "__import__", "breakpoint",
                 "input", "print"}  # print captured separately but not blocked

# For Python (Data) track: these imports are explicitly allowed
PYTHON_DATA_ALLOWED_IMPORTS = {
    "pandas", "numpy", "math", "statistics", "collections",
    "itertools", "functools", "datetime", "re"
}

def validate_python_code(code: str, topic: str = "python") -> None:
    """
    Parse code AST and raise HTTPException(400) if it contains unsafe patterns.
    topic: 'python' (algorithms) or 'python_data'
    """
    if len(code) > 5000:
        raise HTTPException(400, detail="Code too long (max 5000 chars)")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise HTTPException(400, detail=f"Syntax error: {e}")

    for node in ast.walk(tree):
        # Block all imports for python (algorithms)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and topic == "python":
            raise HTTPException(400, detail="Imports are not allowed. All standard types are pre-available.")

        # For python_data: allow only the allowlist
        if isinstance(node, (ast.Import, ast.ImportFrom)) and topic == "python_data":
            names = [a.name for a in node.names] if isinstance(node, ast.Import) \
                    else ([node.module] if node.module else [])
            for name in names:
                top = name.split(".")[0]
                if top not in PYTHON_DATA_ALLOWED_IMPORTS:
                    raise HTTPException(400, detail=f"Import '{top}' is not allowed.")

        # Block dangerous builtins
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in BLOCKED_CALLS - {"print"}:
                raise HTTPException(400, detail=f"Use of '{name}()' is not allowed.")

        # Block __class__, __bases__, __subclasses__ escape chains
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__") \
               and node.attr not in {"__init__", "__len__", "__str__", "__repr__",
                                     "__iter__", "__next__", "__getitem__", "__setitem__",
                                     "__contains__", "__eq__", "__lt__", "__le__",
                                     "__gt__", "__ge__", "__add__", "__mul__"}:
                raise HTTPException(400, detail=f"Access to '{node.attr}' is not allowed.")
```

### 3b. `backend/python_sandbox_harness.py`

Runs **inside** the subprocess. Receives question JSON and user code via stdin. Outputs JSON result to stdout.

```python
#!/usr/bin/env python3
"""
Subprocess harness. Called by python_evaluator.py as:
    python3 python_sandbox_harness.py
Reads JSON from stdin: { "mode": "algorithm"|"data", "user_code": str,
                         "test_cases": [...] | "dataframes": {...},
                         "expected_code": str }
Writes JSON to stdout: { "results": [...], "print_output": str, "error": str|null }
"""
import sys, json, io, traceback, os

# Restrict filesystem access
os.chdir("/tmp")

payload = json.load(sys.stdin)
mode = payload["mode"]
user_code = payload["user_code"]
print_buffer = io.StringIO()

def capture_print(*args, **kwargs):
    kwargs["file"] = print_buffer
    __builtins__["print"](*args, **kwargs)  # noqa

# --- ALGORITHM MODE ---
if mode == "algorithm":
    results = []
    try:
        safe_globals = {"__builtins__": {"print": capture_print, "len": len,
                        "range": range, "enumerate": enumerate, "zip": zip,
                        "map": map, "filter": filter, "sorted": sorted,
                        "reversed": reversed, "sum": sum, "min": min, "max": max,
                        "abs": abs, "round": round, "int": int, "float": float,
                        "str": str, "bool": bool, "list": list, "dict": dict,
                        "set": set, "tuple": tuple, "type": type,
                        "isinstance": isinstance, "hasattr": hasattr,
                        "getattr": getattr, "setattr": setattr,
                        "None": None, "True": True, "False": False}}
        exec(user_code, safe_globals)
        solve_fn = safe_globals.get("solve")
        if solve_fn is None:
            raise ValueError("No 'solve' function found. Define 'def solve(...):'")
        for tc in payload["test_cases"]:
            try:
                actual = solve_fn(*tc["input"])
                passed = actual == tc["expected"]
                results.append({"input": tc["input"], "expected": tc["expected"],
                                 "actual": actual, "passed": passed, "error": None})
            except Exception as e:
                results.append({"input": tc["input"], "expected": tc["expected"],
                                 "actual": None, "passed": False,
                                 "error": str(e)})
    except Exception as e:
        print(json.dumps({"results": [], "print_output": "", "error": str(e)}))
        sys.exit(0)
    print(json.dumps({"results": results,
                      "print_output": print_buffer.getvalue(), "error": None}))

# --- DATA MODE (pandas/numpy) ---
elif mode == "data":
    import pandas as pd
    import numpy as np
    datasets_dir = payload["datasets_dir"]
    dataframes = {}
    for var_name, csv_file in payload["dataframes"].items():
        dataframes[var_name] = pd.read_csv(os.path.join(datasets_dir, csv_file))

    try:
        safe_globals = {"__builtins__": __builtins__, "pd": pd, "np": np}
        exec(user_code, safe_globals)
        solve_fn = safe_globals.get("solve")
        if solve_fn is None:
            raise ValueError("No 'solve' function found. Define 'def solve(...):'")
        result = solve_fn(**dataframes)
        if isinstance(result, np.ndarray):
            result = pd.DataFrame({"result": result})
        if not isinstance(result, pd.DataFrame):
            raise ValueError("solve() must return a pandas DataFrame (or numpy array).")
        print(json.dumps({"result": result.to_json(orient="split"),
                          "print_output": print_buffer.getvalue(), "error": None}))
    except Exception as e:
        print(json.dumps({"result": None, "print_output": print_buffer.getvalue(),
                          "error": str(e)}))
```

### 3c. `backend/python_evaluator.py`

Spawns the harness subprocess, enforces timeout, runs normalization comparison.

```python
import subprocess, json, sys, os
from pathlib import Path
from evaluator import normalize_dataframe   # reuse existing normalization
import pandas as pd

HARNESS = str(Path(__file__).parent / "python_sandbox_harness.py")
DATASETS_DIR = str(Path(__file__).parent / "datasets")
TIMEOUT = 5  # seconds

def run_python_code(user_code: str, question: dict) -> dict:
    """Run user code for Python (algorithms) track against public test cases only."""
    public_n = question.get("public_test_cases", len(question["test_cases"]))
    public_cases = question["test_cases"][:public_n]
    payload = {"mode": "algorithm", "user_code": user_code, "test_cases": public_cases}
    return _run_harness(payload)

def evaluate_python_code(user_code: str, question: dict) -> dict:
    """Run against ALL test cases (including hidden) and return full verdict."""
    payload = {"mode": "algorithm", "user_code": user_code,
               "test_cases": question["test_cases"]}
    raw = _run_harness(payload)
    if raw.get("error"):
        return {"correct": False, "error": raw["error"]}
    results = raw["results"]
    correct = all(r["passed"] for r in results)
    public_n = question.get("public_test_cases", len(results))
    return {
        "correct": correct,
        "results": results[:public_n],   # only return public cases in detail
        "hidden_summary": {              # summary for hidden cases
            "total": len(results) - public_n,
            "passed": sum(1 for r in results[public_n:] if r["passed"])
        },
        "print_output": raw.get("print_output", ""),
        "solution_code": question["solution_code"] if correct else None,
        "explanation": question["explanation"] if correct else None,
    }

def run_python_data_code(user_code: str, question: dict) -> dict:
    """Run user pandas/numpy code and return DataFrame result."""
    payload = {"mode": "data", "user_code": user_code,
               "dataframes": question["dataframes"],
               "datasets_dir": DATASETS_DIR}
    raw = _run_harness(payload)
    if raw.get("error"):
        return {"error": raw["error"]}
    df = pd.read_json(raw["result"], orient="split")
    return {"columns": list(df.columns), "rows": df.head(200).values.tolist(),
            "row_limit": len(df) > 200, "print_output": raw.get("print_output", "")}

def evaluate_python_data_code(user_code: str, question: dict) -> dict:
    """Run user code + expected code, compare DataFrames."""
    payload_user = {"mode": "data", "user_code": user_code,
                    "dataframes": question["dataframes"], "datasets_dir": DATASETS_DIR}
    payload_exp = {"mode": "data", "user_code": question["expected_code"],
                   "dataframes": question["dataframes"], "datasets_dir": DATASETS_DIR}
    raw_user = _run_harness(payload_user)
    if raw_user.get("error"):
        return {"correct": False, "error": raw_user["error"]}
    raw_exp = _run_harness(payload_exp)  # trusted code; error here = author bug

    user_df = pd.read_json(raw_user["result"], orient="split")
    exp_df = pd.read_json(raw_exp["result"], orient="split")

    user_norm = normalize_dataframe(user_df)
    exp_norm = normalize_dataframe(exp_df)
    correct = user_norm.equals(exp_norm)

    return {
        "correct": correct,
        "user_result": {"columns": list(user_df.columns),
                        "rows": user_df.head(200).values.tolist()},
        "expected_result": {"columns": list(exp_df.columns),
                            "rows": exp_df.head(200).values.tolist()},
        "print_output": raw_user.get("print_output", ""),
        "solution_code": question["solution_code"] if correct else None,
        "explanation": question["explanation"] if correct else None,
    }

def _run_harness(payload: dict) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, HARNESS],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=TIMEOUT
        )
        return json.loads(proc.stdout.decode())
    except subprocess.TimeoutExpired:
        return {"error": "Time limit exceeded (5s). Check for infinite loops."}
    except Exception as e:
        return {"error": f"Execution error: {e}"}
```

---

## 4. Backend — New Catalog Loaders

### 4a. `backend/python_questions.py`

Mirror of `backend/questions.py`. Key differences:
- ID range: easy 4001–4299, medium 4301–4599, hard 4601–4999
- Required fields: `id`, `order`, `title`, `difficulty`, `description`, `starter_code`, `expected_code`, `solution_code`, `explanation`, `test_cases`, `public_test_cases`
- Optional fields: `hints`, `concepts`
- Content dir: `backend/content/python_questions/`
- No `dataset_files` or `schema` validation (algorithms use scalar inputs)

Expose: `get_python_question(id)`, `get_all_python_questions()`, `get_python_questions_by_difficulty()`

### 4b. `backend/python_data_questions.py`

Mirror of `backend/questions.py`. Key differences:
- ID range: easy 5001–5999, medium 6001–6999, hard 7001–7999
- Required fields same as SQL plus: `dataframes` (dict mapping var name → csv file), `starter_code`, `expected_code`
- Validates that all CSV files in `dataframes` values exist in `backend/datasets/`
- Content dir: `backend/content/python_data_questions/`

Expose: `get_python_data_question(id)`, `get_all_python_data_questions()`, `get_python_data_questions_by_difficulty()`

### 4c. `backend/pyspark_questions.py`

Simpler loader — no execution validation needed.
- ID range: easy 11001–11999, medium 12001–12999, hard 13001–13999
- Required fields: `id`, `order`, `title`, `difficulty`, `type`, `description`, `options` (array of 4), `correct_option` (int 0–3), `explanation`
- Optional fields: `code_snippet`, `hints`, `concepts`
- Valid `type` values: `"mcq"`, `"predict_output"`, `"debug"`, `"optimization"`
- Content dir: `backend/content/pyspark_questions/`

Expose: `get_pyspark_question(id)`, `get_all_pyspark_questions()`, `get_pyspark_questions_by_difficulty()`

---

## 5. Backend — New Routers

### 5a. `backend/routers/python_questions.py`

```
GET  /api/python/catalog          → catalog with user's solve state (topic='python')
GET  /api/python/questions/{id}   → question detail (omits expected_code, solution_code)
POST /api/python/run-code         → { code, question_id } → run against public test cases
POST /api/python/submit           → { code, question_id } → run all test cases, mark solved
```

`run-code` response:
```json
{
  "results": [
    { "input": [[2,7,11,15], 9], "expected": [0,1], "actual": [0,1], "passed": true }
  ],
  "print_output": ""
}
```

`submit` response (correct):
```json
{
  "correct": true,
  "results": [...public cases...],
  "hidden_summary": { "total": 3, "passed": 3 },
  "print_output": "",
  "solution_code": "def solve(...):\n    ...",
  "explanation": "..."
}
```

### 5b. `backend/routers/python_data_questions.py`

```
GET  /api/python-data/catalog
GET  /api/python-data/questions/{id}
POST /api/python-data/run-code    → { code, question_id } → { columns, rows, row_limit, print_output }
POST /api/python-data/submit      → { code, question_id } → { correct, user_result, expected_result, print_output, solution_code, explanation }
```

### 5c. `backend/routers/pyspark_questions.py`

```
GET  /api/pyspark/catalog
GET  /api/pyspark/questions/{id}   → returns question without correct_option
POST /api/pyspark/submit           → { selected_option: int, question_id: int }
                                     → { correct: bool, explanation: str }
```

No `/run-code` endpoint (nothing to run).

`submit` logic:
```python
@router.post("/api/pyspark/submit")
async def submit_pyspark(req: PySparkSubmitRequest, user=Depends(get_current_user)):
    q = get_pyspark_question(req.question_id)
    correct = req.selected_option == q["correct_option"]
    if correct:
        await mark_question_solved(user.id, req.question_id, topic="pyspark")
    return { "correct": correct, "explanation": q["explanation"] }
```

### 5d. `backend/routers/dashboard.py`

```
GET /api/dashboard   → per-topic solve stats + recent activity + concepts
```

```python
@router.get("/api/dashboard")
async def get_dashboard(user=Depends(get_current_user)):
    # For each topic, get solved IDs and compute stats
    topics = ["sql", "python", "python_data", "pyspark"]
    catalogs = {
        "sql": get_questions_by_difficulty(),
        "python": get_python_questions_by_difficulty(),
        "python_data": get_python_data_questions_by_difficulty(),
        "pyspark": get_pyspark_questions_by_difficulty(),
    }
    tracks = {}
    concepts_by_track = {}
    for topic in topics:
        solved_ids = await get_solved_question_ids(user.id, topic=topic)
        cat = catalogs[topic]
        tracks[topic] = {
            "solved": len(solved_ids),
            "total": sum(len(v) for v in cat.values()),
            "by_difficulty": {
                d: {"solved": sum(1 for q in qs if q["id"] in solved_ids),
                    "total": len(qs)}
                for d, qs in cat.items()
            }
        }
        # Collect concepts from solved questions
        solved_concepts = []
        for qs in cat.values():
            for q in qs:
                if q["id"] in solved_ids:
                    solved_concepts.extend(q.get("concepts", []))
        concepts_by_track[topic] = list(dict.fromkeys(solved_concepts))  # dedupe, ordered

    recent = await get_recent_activity(user.id, limit=10)  # new db.py function
    return {"tracks": tracks, "concepts_by_track": concepts_by_track,
            "recent_activity": recent}
```

Add to `db.py`:
```python
async def get_recent_activity(user_id: int, limit: int = 10) -> list[dict]:
    """Return last N solved questions across all topics, ordered by solved_at desc."""
    rows = await pool.fetch(
        """SELECT topic, question_id, solved_at FROM user_challenge_progress
           WHERE user_id = $1 ORDER BY solved_at DESC LIMIT $2""",
        user_id, limit
    )
    # Enrich with title and difficulty from the appropriate catalog
    ...
```

---

## 6. Backend — main.py Changes

```python
# In lifespan startup, after existing init:
from python_questions import load_python_questions
from python_data_questions import load_python_data_questions
from pyspark_questions import load_pyspark_questions
load_python_questions()
load_python_data_questions()
load_pyspark_questions()

# Register new routers:
from routers.python_questions import router as python_router
from routers.python_data_questions import router as python_data_router
from routers.pyspark_questions import router as pyspark_router
from routers.dashboard import router as dashboard_router
app.include_router(python_router)
app.include_router(python_data_router)
app.include_router(pyspark_router)
app.include_router(dashboard_router)
```

---

## 7. Backend — models.py Additions

```python
class RunCodeRequest(BaseModel):
    code: str
    question_id: int

class SubmitCodeRequest(BaseModel):
    code: str
    question_id: int

class PySparkSubmitRequest(BaseModel):
    selected_option: int   # 0–3
    question_id: int
```

---

## 8. Content Directories

Create these directories and initial files:

```
backend/content/python_questions/
  schemas.json          # validation config (id ranges, required fields)
  easy.json             # array of 10 easy Python algorithm questions
  medium.json
  hard.json

backend/content/python_data_questions/
  schemas.json
  easy.json             # array of 10 easy pandas/numpy questions
  medium.json
  hard.json

backend/content/pyspark_questions/
  schemas.json
  easy.json             # array of 10 easy PySpark MCQ questions
  medium.json
  hard.json
```

See `docs/python-curriculum-spec.md`, `docs/python-data-curriculum-spec.md`, and `docs/pyspark-curriculum-spec.md` for question authoring specs.

See `docs/python-question-authoring.md` for JSON schema and field-by-field authoring rules.

---

## 9. Frontend — Route Changes

**File:** `frontend/src/App.js`

```jsx
// New routes to add:
<Route path="/dashboard" element={<ProgressDashboard />} />
<Route path="/practice/:topic" element={<AppShell />}>
  <Route index element={<TrackHubPage />} />
  <Route path="questions/:id" element={<QuestionPage />} />
</Route>

// Legacy redirects:
<Route path="/practice" element={<Navigate to="/practice/sql" replace />} />
<Route path="/practice/questions/:id"
       element={<LegacySQLRedirect />} />  // redirects to /practice/sql/questions/:id

// Sample routes (update existing):
// /sample/:difficulty → /sample/:topic/:difficulty
<Route path="/sample/:topic/:difficulty" element={<SampleQuestionPage />} />
```

`:topic` URL values: `sql`, `python`, `python-data`, `pyspark`

Internal topic keys (used in API calls and context): `sql`, `python`, `python_data`, `pyspark`

Mapping: URL `python-data` → API/context `python_data`

---

## 10. Frontend — New and Modified Components

### 10a. `frontend/src/contexts/TopicContext.js` (new)

```jsx
import { createContext, useContext } from 'react';

export const TopicContext = createContext('sql');
export const useTopic = () => useContext(TopicContext);

// Topic metadata used throughout the UI:
export const TRACK_META = {
  sql: {
    label: 'SQL',
    description: 'Write queries against realistic datasets',
    badge: 'DuckDB sandbox',
    editorLang: 'sql',
    apiPrefix: '/api',           // /api/catalog, /api/questions/:id, /api/run-query, /api/submit
    runEndpoint: '/api/run-query',
    submitEndpoint: '/api/submit',
    questionField: 'query',      // field name in submit request body
    color: '#5B6AF0',
  },
  python: {
    label: 'Python',
    description: 'Algorithms, data structures, problem solving',
    badge: 'Python sandbox',
    editorLang: 'python',
    apiPrefix: '/api/python',
    runEndpoint: '/api/python/run-code',
    submitEndpoint: '/api/python/submit',
    questionField: 'code',
    color: '#3776AB',
  },
  python_data: {
    label: 'Python (Data)',
    description: 'pandas & numpy data manipulation',
    badge: 'pandas sandbox',
    editorLang: 'python',
    apiPrefix: '/api/python-data',
    runEndpoint: '/api/python-data/run-code',
    submitEndpoint: '/api/python-data/submit',
    questionField: 'code',
    color: '#E10098',
  },
  pyspark: {
    label: 'PySpark',
    description: 'Spark concepts, architecture, optimization',
    badge: 'Conceptual · MCQ',
    editorLang: null,            // no editor for PySpark
    apiPrefix: '/api/pyspark',
    runEndpoint: null,           // no run-code
    submitEndpoint: '/api/pyspark/submit',
    questionField: 'selected_option',
    color: '#E25A1C',
  },
};

// URL topic slug → internal key
export const slugToTopic = (slug) =>
  ({ 'sql': 'sql', 'python': 'python', 'python-data': 'python_data', 'pyspark': 'pyspark' }[slug] ?? 'sql');
```

### 10b. `frontend/src/components/CodeEditor.js` (rename from SQLEditor.js)

```jsx
import Editor from '@monaco-editor/react';

export default function CodeEditor({ value, onChange, language = 'sql', height = '340px', readOnly = false }) {
  return (
    <Editor
      height={height}
      language={language}
      theme="vs-dark"
      value={value}
      onChange={onChange}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        readOnly,
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        lineNumbers: 'on',
      }}
    />
  );
}
```

Update all imports of `SQLEditor` → `CodeEditor`. Pass `language={meta.editorLang}` where `meta = TRACK_META[topic]`.

### 10c. `frontend/src/components/TestCasePanel.js` (new)

Used by Python (algorithms) track to show test case results.

```jsx
// Props: { results: [{input, expected, actual, passed, error}], hiddenSummary: {total, passed} }
// Shows each public test case as a collapsible row: green check or red X, input, expected, actual
// Below public results: "Hidden tests: 3/5 passed" summary (if hiddenSummary provided)
```

UI layout:
```
TEST CASES
  ✓ Case 1   [2,7,11,15], 9  →  expected [0,1]  got [0,1]
  ✓ Case 2   [3,2,4], 6     →  expected [1,2]  got [1,2]
  Hidden: 3/3 passed
```

### 10d. `frontend/src/components/PrintOutputPanel.js` (new)

```jsx
// Props: { output: string }
// Renders in a styled <pre> block below the editor if output is non-empty
// Title: "Output (stdout)"
// Hidden if output is empty string
```

### 10e. `frontend/src/components/VariablesPanel.js` (new)

```jsx
// Props: { dataframes: { df_users: { rows: 600, columns: [...] }, ... } }
// Shows available variables and their shapes
// Populated from the question's `dataframes` field + dataset metadata
// Rendered in the left context panel (replacing SchemaViewer for python_data track)
```

UI layout (compact):
```
AVAILABLE VARIABLES
  df_users        DataFrame  600 rows × 8 cols
  df_orders       DataFrame  4200 rows × 6 cols
```

### 10f. `frontend/src/components/MCQPanel.js` (new)

Used exclusively by the PySpark track.

```jsx
// Props: { options: string[], onSubmit: (selectedIndex) => void,
//          result: { correct, explanation } | null, submitted: bool }
// Renders 4 labeled radio options (A / B / C / D)
// Submit button → disabled after submit
// After submit: highlight correct answer green, selected wrong answer red
// Always show explanation text after submit (correct or not)
```

UI layout:
```
  ○ A  df.filter(df.age > 30)
  ○ B  df.select('name', 'age')
  ● C  df.count()             ← selected
  ○ D  df.withColumn(...)

  [Submit answer]

  --- post-submit ---
  ✓ Correct!
  Explanation: count() triggers a full DAG evaluation...
```

### 10g. `frontend/src/components/TrackProgressBar.js` (new)

```jsx
// Props: { solved: number, total: number, label?: string, size?: 'sm'|'md' }
// Renders a horizontal bar + "23 / 86" label
// Used in LandingPage tiles, TrackHubPage, ProgressDashboard, SidebarNav header
```

### 10h. `frontend/src/pages/TrackHubPage.js` (new)

Rendered at `/practice/:topic` when no question is selected (the index route of AppShell).

```jsx
// Reads topic from URL param, fetches /api/:topic/catalog and /api/dashboard
// Renders:
//   - Track name + description
//   - Overall progress bar (TrackProgressBar)
//   - Per-difficulty progress bars (easy / medium / hard)
//   - "Continue where I left off" button → navigate to next unlocked question
//   - "CONCEPTS IN THIS TRACK" — all unique concept tags across all questions
//   - "MY SOLVED CONCEPTS" — concept tags from solved questions only
```

### 10i. `frontend/src/pages/ProgressDashboard.js` (new)

Rendered at `/dashboard`.

```jsx
// Fetches GET /api/dashboard
// Renders:
//   - "MY PROGRESS" heading
//   - 4 track cards (2×2 grid) each showing: label, solved/total, progress bar,
//     per-difficulty breakdown (easy/medium/hard solved/total)
//   - "CONCEPTS WORKED ON" section: tag pills grouped by track
//   - "RECENT ACTIVITY" list: last 10 solved, each showing track badge + question title + date
```

---

## 11. Frontend — Modified Components

### `AppShell.js`

Changes:
1. Read `topic` slug from `useParams()`, convert to internal key via `slugToTopic()`
2. Wrap tree in `<TopicContext.Provider value={topic}>`
3. Add track switcher in topbar: a `<select>` or popover dropdown listing all 4 tracks + "← All Tracks" link
4. Update topbar title: `{TRACK_META[topic].label} Practice`
5. Update sidebar badge: `{TRACK_META[topic].badge}`

Track switcher markup:
```jsx
<div className="track-switcher">
  <span className="track-label">{TRACK_META[topic].label} Practice</span>
  <span className="track-caret">▾</span>
  {/* dropdown */}
  <div className="track-dropdown">
    {Object.entries(TRACK_META).map(([key, meta]) => (
      <a key={key} href={`/practice/${topicToSlug(key)}`}>{meta.label}</a>
    ))}
    <hr />
    <a href="/">← All Tracks</a>
  </div>
</div>
```

### `SidebarNav.js`

Changes:
1. Add track summary at top of sidebar: `{solved} solved · {total} questions` (from catalog totals)
2. Add topic label chip at top: `SQL` / `Python` / etc.
3. No other structural changes (catalog API returns same `groups` shape)

### `LandingPage.js`

Complete redesign. Key sections:

**Topbar:** Add `[Dashboard]` link (→ `/dashboard`) for logged-in users. Change "SQL Interview Practice" → "Data Interview Practice".

**Hero (logged-out):**
```
kicker: "SQL · Python · PySpark · pandas"
headline: "Get sharp at data interviews."
copy: "Four tracks covering the full data engineering interview stack."
CTA: [Explore tracks ↓]
```

**Hero (logged-in):** Minimal — just "Welcome back, {name}" with link to dashboard.

**Track tiles (2×2 grid):**
```jsx
// Fetch /api/dashboard for logged-in users to get per-track progress
// For each of the 4 tracks:
<div className="track-tile track-tile--{topic}">
  <div className="track-tile-header">
    <span className="track-name">{label}</span>
    <span className="track-description">{description}</span>
  </div>
  {/* logged-in only: */}
  <TrackProgressBar solved={solved} total={total} />
  <span className="track-count">{solved} / {total} solved</span>
  <a href={`/practice/${slug}`} className="track-cta btn-secondary">
    {solved > 0 ? 'Continue →' : 'Start →'}
  </a>
</div>
```

CSS classes to add to `App.css`: `.track-tiles`, `.track-tile`, `.track-tile--sql`, `.track-tile--python`, `.track-tile--python-data`, `.track-tile--pyspark`, `.track-tile-header`, `.track-progress-bar`, `.track-cta`, `.track-switcher`, `.track-dropdown`.

Design tokens for track colors (add to `:root`):
```css
--track-sql:          #5B6AF0;
--track-python:       #3776AB;
--track-python-data:  #E10098;
--track-pyspark:      #E25A1C;
```

### `QuestionPage.js`

Changes (topic-aware branching):

```jsx
const { topic: topicSlug, id } = useParams();
const topic = slugToTopic(topicSlug);
const meta = TRACK_META[topic];

// Editor language
<CodeEditor language={meta.editorLang} ... />  // null = no editor (PySpark)

// Initial editor value
const defaultCode = question.starter_code ?? '-- Write your SQL query here';

// Run button: hidden for PySpark (meta.runEndpoint === null)
// Submit for PySpark: POSTs { selected_option, question_id }
// Submit for others: POSTs { code, question_id } (or { query, question_id } for SQL)

// Result area: switch on topic
{topic === 'pyspark' && <MCQPanel ... />}
{(topic === 'sql' || topic === 'python_data') && <ResultsTable ... />}
{topic === 'python' && <TestCasePanel ... />}
{(topic === 'python' || topic === 'python_data') && <PrintOutputPanel ... />}

// Context panel (left of editor):
{topic === 'sql' && <SchemaViewer ... />}
{topic === 'python_data' && <VariablesPanel ... />}
{/* Python and PySpark: no context panel */}
```

### `catalogContext.js`

```jsx
// Accept topic param
function CatalogProvider({ topic, children }) {
  // Fetch /api/{topic}/catalog
  const apiPrefix = TRACK_META[topic].apiPrefix;
  const url = `${apiPrefix}/catalog`;
  ...
}
```

---

## 12. Implementation Phases

### Phase 1 — Python (Algorithms) end-to-end

Order of implementation:

1. Alembic migration: add `topic` to progress tables
2. `db.py`: add `topic` param to progress functions
3. `python_guard.py` — AST validator
4. `python_sandbox_harness.py` — algorithm mode
5. `python_evaluator.py` — `run_python_code()` + `evaluate_python_code()`
6. `python_questions.py` — catalog loader
7. `backend/content/python_questions/` — schemas.json + easy.json (10 questions, see curriculum spec)
8. `backend/routers/python_questions.py` — all 4 endpoints
9. `backend/models.py` — add `RunCodeRequest`, `SubmitCodeRequest`
10. `backend/main.py` — register router + load catalog on startup
11. `frontend/src/contexts/TopicContext.js`
12. `frontend/src/components/CodeEditor.js` (rename + language prop)
13. `frontend/src/components/TestCasePanel.js`
14. `frontend/src/components/PrintOutputPanel.js`
15. `frontend/src/App.js` — add `/practice/:topic/questions/:id` routes + legacy redirects
16. `frontend/src/pages/QuestionPage.js` — topic-aware branching
17. `frontend/src/catalogContext.js` — accept topic param

**Milestone:** `GET /api/python/catalog` returns 10 easy questions. `POST /api/python/run-code` with `import os` returns guard error. `/practice/python/questions/4001` shows Python editor + test case panel.

### Phase 2 — Python (Data) end-to-end

1. `python_sandbox_harness.py` — data mode (if not already combined with algorithm mode)
2. `python_data_questions.py` — catalog loader
3. `backend/content/python_data_questions/` — schemas.json + easy.json (10 questions)
4. `backend/routers/python_data_questions.py`
5. `backend/main.py` — register router
6. `frontend/src/components/VariablesPanel.js`
7. `QuestionPage.js` — python_data branch (VariablesPanel, ResultsTable, PrintOutput)

**Milestone:** `/practice/python-data/questions/5001` runs pandas code, shows DataFrame result.

### Phase 3 — PySpark end-to-end

1. `pyspark_questions.py` — catalog loader
2. `backend/content/pyspark_questions/` — schemas.json + easy.json (10 MCQ questions)
3. `backend/routers/pyspark_questions.py` — catalog + GET question + POST submit
4. `backend/main.py` — register router
5. `frontend/src/components/MCQPanel.js`
6. `QuestionPage.js` — pyspark branch (MCQPanel, no editor, no run button)

**Milestone:** `/practice/pyspark/questions/11001` shows MCQ, submitting correct answer returns `correct: true` + explanation.

### Phase 4 — Multi-track UI + Dashboard

1. `frontend/src/pages/TrackHubPage.js`
2. `frontend/src/pages/ProgressDashboard.js`
3. `frontend/src/components/TrackProgressBar.js`
4. `backend/routers/dashboard.py` — `GET /api/dashboard`
5. `db.py` — `get_recent_activity()` function
6. `LandingPage.js` — full redesign (4-tile grid, progress-aware)
7. `AppShell.js` — track switcher dropdown, back link
8. `SidebarNav.js` — track summary header
9. `App.js` — add `/dashboard` route, update `/practice` route
10. `App.css` — track color tokens, tile styles, switcher styles, progress bar styles

**Milestone:** Landing page shows 4 track tiles with live progress. `/dashboard` shows cross-track stats. Track switcher in topbar works.

### Phase 5 — Content + Hardening

1. Expand all tracks to full curriculum (see curriculum spec docs)
2. Sample question routes for Python, Python (Data), PySpark
3. Rate limit adjustment: lower `/run-code` limit (20 req/60s) separate from general API
4. `CLAUDE.md` + all docs updated

---

## 13. Verification Checklist

**Backend:**
- `GET /health` — healthy
- `GET /api/python/catalog` — returns 10 easy Python questions, no `expected_code` or `solution_code` in response
- `POST /api/python/run-code` `{"code":"import os", "question_id":4001}` → 400 guard error within 1s
- `POST /api/python/run-code` `{"code":"def solve(n,t):\n return [0,1]", "question_id":4001}` → test case results
- `POST /api/python/submit` correct solution → `{"correct":true, "solution_code":"..."}` + `user_challenge_progress` row inserted with `topic='python'`
- `POST /api/python/run-code` `{"code":"while True: pass", "question_id":4001}` → timeout error within 6s
- `GET /api/python-data/catalog` — returns questions
- `POST /api/python-data/run-code` → DataFrame JSON + `print_output` field
- `GET /api/pyspark/questions/11001` → question without `correct_option`
- `POST /api/pyspark/submit` `{"selected_option":2,"question_id":11001}` → `{"correct":true,"explanation":"..."}`
- `GET /api/dashboard` — all 4 tracks in response, concept lists, recent activity

**Frontend:**
- `/` — 4 track tiles visible; logged-in user sees progress bars
- `/dashboard` — cross-track progress visible
- `/practice/sql` — TrackHub shows SQL progress, concepts, continue button
- `/practice/python/questions/4001` — Python editor, starter code pre-filled, test case panel visible, no SchemaViewer
- `/practice/python-data/questions/5001` — VariablesPanel shows df names/shapes, ResultsTable shows result
- `/practice/pyspark/questions/11001` — no editor, 4 radio options, submit reveals explanation
- `/practice/questions/1001` → redirects to `/practice/sql/questions/1001`
- Track switcher dropdown → all 4 tracks listed, navigation works

---

## 14. Files Changed Summary

| File | Status | Change |
|---|---|---|
| `backend/alembic/versions/YYYYMMDD_add_topic_to_progress.py` | **NEW** | DB migration |
| `backend/db.py` | **MODIFY** | `topic` param on progress functions + `get_recent_activity()` |
| `backend/models.py` | **MODIFY** | Add `RunCodeRequest`, `SubmitCodeRequest`, `PySparkSubmitRequest` |
| `backend/main.py` | **MODIFY** | Register new routers, load new catalogs in lifespan |
| `backend/python_guard.py` | **NEW** | AST safety validator |
| `backend/python_sandbox_harness.py` | **NEW** | Subprocess harness (algorithm + data modes) |
| `backend/python_evaluator.py` | **NEW** | Executor + comparator for Python tracks |
| `backend/python_questions.py` | **NEW** | Catalog loader for Python algorithms |
| `backend/python_data_questions.py` | **NEW** | Catalog loader for Python (Data) |
| `backend/pyspark_questions.py` | **NEW** | Catalog loader for PySpark MCQs |
| `backend/routers/python_questions.py` | **NEW** | `/api/python/*` endpoints |
| `backend/routers/python_data_questions.py` | **NEW** | `/api/python-data/*` endpoints |
| `backend/routers/pyspark_questions.py` | **NEW** | `/api/pyspark/*` endpoints |
| `backend/routers/dashboard.py` | **NEW** | `GET /api/dashboard` |
| `backend/content/python_questions/` | **NEW** | schemas.json, easy/medium/hard.json |
| `backend/content/python_data_questions/` | **NEW** | schemas.json, easy/medium/hard.json |
| `backend/content/pyspark_questions/` | **NEW** | schemas.json, easy/medium/hard.json |
| `frontend/src/App.js` | **MODIFY** | New routes, legacy redirects |
| `frontend/src/contexts/TopicContext.js` | **NEW** | Topic context + TRACK_META |
| `frontend/src/catalogContext.js` | **MODIFY** | Accept topic param |
| `frontend/src/pages/LandingPage.js` | **MODIFY** | 4-tile redesign |
| `frontend/src/pages/QuestionPage.js` | **MODIFY** | Topic-aware branching |
| `frontend/src/pages/TrackHubPage.js` | **NEW** | `/practice/:topic` landing |
| `frontend/src/pages/ProgressDashboard.js` | **NEW** | `/dashboard` |
| `frontend/src/components/AppShell.js` | **MODIFY** | Track switcher, topic-aware branding |
| `frontend/src/components/SidebarNav.js` | **MODIFY** | Track summary header |
| `frontend/src/components/CodeEditor.js` | **NEW** (rename) | Language prop, replaces SQLEditor.js |
| `frontend/src/components/TestCasePanel.js` | **NEW** | Test case pass/fail display |
| `frontend/src/components/PrintOutputPanel.js` | **NEW** | stdout display |
| `frontend/src/components/VariablesPanel.js` | **NEW** | Available DataFrames display |
| `frontend/src/components/MCQPanel.js` | **NEW** | MCQ radio + explanation reveal |
| `frontend/src/components/TrackProgressBar.js` | **NEW** | Reusable progress bar |
| `frontend/src/App.css` | **MODIFY** | Track color tokens, tile styles, switcher, progress bar |
| `CLAUDE.md` | **MODIFY** | Update platform description, all new routes, new API, new files |
