# Python Track

> **Authoring rule, no exceptions:** Every Python question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/python_questions/*.json` bypass the difficulty arc and the concept-taxonomy contract.

## What this track trains

A working data professional writes Python every day — not LeetCode-style competitive programming, but **algorithmic reasoning applied to real problems**: dedupe a stream, build a session map, detect anomalies, run a state machine over events. The Python track tests whether a candidate can recognise the *shape* of a problem (sliding window? two pointers? dynamic programming? graph traversal?) and pick the right pattern with the right complexity.

> *Datathink philosophy applied:* A candidate who can write a one-line list comprehension is everywhere. A candidate who, given a problem, names "this is a sliding window with constraint X, O(n) achievable, here's why," and then writes it cleanly — that's the practitioner who survives the second interview round.

We are not training competitive coders. We are training data professionals who happen to need real algorithmic chops because the work demands it.

## Modality

**Executable problem-solving.** Subprocess-sandboxed Python execution. 5-second timeout. 512 MB RLIMIT_AS. AST-based pre-execution guard rejects unsafe imports / system calls. Test-case-based evaluation: candidate's function called with each test input, output compared to expected.

## Schema essentials (function shape)

Every question defines a top-level `def solve(...)` function with typed parameters. The test runner imports the candidate's module and calls `solve(*test_input)` for each test case. Return type must match the expected value exactly (type + structure + content).

```python
def solve(nums: list[int], target: int) -> int:
    # candidate fills in
    ...
```

No global mutable state. No I/O (no `print` in the function body). Determinism required.

## ID range (TXNNN scheme)

`T=2` for Python. Practice and `mock_only` share the same space within each difficulty.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 21001–21999 | `backend/content/python_questions/easy.json` |
| Medium | 22001–22999 | `backend/content/python_questions/medium.json` |
| Hard | 23001–23999 | `backend/content/python_questions/hard.json` |

Samples in `backend/content/python_questions/sample/` use `2XS` 3-digit IDs.

## Difficulty vocabulary

| Tier | Reasoning depth | Patterns | Complexity expected | What's out |
|---|---|---|---|---|
| **Easy** | Single algorithmic concept. Basic data structures. | Linear scan, hash-map state, basic string manipulation, list comprehensions, simple counting | O(n) or O(n log n) | Nested DP, graph algorithms |
| **Medium** | One named pattern in clean form. Recognising which pattern applies *is* the test. | Sliding window, two pointers, binary search (incl. on answer space), heap-based selection, BFS/DFS basics, 1D DP, backtracking | O(n) or O(n log n) | 2D DP, advanced graph (Dijkstra, Union-Find) |
| **Hard** | Multi-step decomposition + non-obvious data structure choice. | 2D DP, graph algorithms (Dijkstra, Union-Find, topological sort, articulation), Trie, system-design data structures (LRU cache, median-from-stream heap pair), advanced string (KMP, Aho-Corasick where motivated) | Optimal complexity required — **no O(n²) accepted at hard if O(n log n) exists** | "Hard because the constraints are weird" |

If a question's hardness comes from "you have to remember to handle the empty case AND the duplicates case AND the negative case AND..." — that's not hard, that's accumulation. Find the *one* pattern that's actually demanding.

**Every pattern above (and in the concept arc below) earns its place only if it maps to real data work — name the analogue.** Sliding window → event-stream windowing; heap top-K → heavy-hitters / hot keys; topological sort → pipeline DAG ordering & dependency resolution; Trie → key-prefix routing / dictionary tokenization; 2-D DP → record fuzzy-matching / sequence alignment / log diffing; graph connectivity & articulation → lineage criticality (single points of failure); BFS/DFS → reachability over a dependency or event graph. If you cannot name a data-work use for a pattern, it is competitive-programming trivia and does not belong here — the prime suspects are permutation/subset backtracking for its own sake, bit-manipulation tricks, and number-theory puzzles. This is the spine of the "What this track trains" framing above, applied to the ladder.

**Deprioritized — out unless a genuine data analogue is articulable:** permutation/subset/N-queens backtracking, grid-path DP (unique-paths style), bit-manipulation tricks, number-theory/math puzzles, regex-matching DP, linked-list pointer gymnastics, and standalone matrix-simulation (spiral, Sudoku). The Difficulty-vocabulary and Concept-arc tables retain the *named patterns* (2-D DP, Trie, articulation, KMP/Aho-Corasick) because each has the analogue listed above — but their puzzle realisations are not authored here.

**Geometric-framing note:** Questions using geometric language ("water trapped", "histogram bars") are only authored when the underlying algorithm earns its place on data-work merit — two-pointer capacity reasoning or monotonic-stack partition sizing — with the engineering use case stated explicitly in the description. The geometry is incidental scaffolding, not the lesson. *Purely* visual puzzles (spiral matrix traversal, unique grid paths) have no data analogue and remain blocked.

> **No mock-only realism family for Python.** Unlike SQL/Pandas/PySpark, Python has no business-judgment assessment lens. The candidate lens — complexity & memory-aware reasoning — is *practice-gradable* here (the executable harness times out O(n²) solutions and OOMs load-everything approaches on large inputs — see Verification), so it is taught and graded in practice, not deferred to mock. In mock chains it is exercised via the `performance_pivot` follow-up dimension, not a concept tag.

### Representative tasks per tier

Difficulty controls reasoning depth, never licenses puzzle trivia. Even easy questions should read like a small real engineering task, not "reverse a string by Fibonacci(n)".

| Tier | Representative tasks |
|---|---|
| **Easy** | Count/frequency over a feed · dedupe a list of records · parse a log line · find the first unique element · basic running totals · simple membership checks. Realistic micro-tasks an engineer actually writes. |
| **Medium** | Sliding-window over an event stream · sessionize events with two pointers · top-K frequent items · merge/schedule intervals · binary search over an answer space (min capacity / rate). Real engineering framing, one named pattern applied non-obviously. |
| **Hard** | Design an LRU cache · median-from-stream · dependency resolution (topological order) · shortest path over a state graph · rate limiter as an algorithmic problem. Senior, system-flavoured decomposition with a non-obvious data-structure choice. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Linear scan + counters → hash-map membership / frequency → indexed-sequence reasoning → string parsing basics → list/collection transforms → simple greedy |
| Medium | Sliding window over event streams (fixed + variable) → two pointers on sorted data → binary search (incl. parametric — min capacity/rate) → heap top-K (heavy hitters) → 1D DP (sequence segmentation / tokenization) → BFS/DFS over dependency or event graphs |
| Hard | graph algorithms with a pipeline analogue (topological sort → DAG/lineage ordering; Union-Find → record linkage; Dijkstra → critical-path/latency) → 2D DP as sequence diff/alignment (edit distance for fuzzy dedup) → Trie (key-prefix routing / autocomplete) / Aho-Corasick (multi-pattern log scanning) → system-design DS (LRU, median heap, sliding-window max) → advanced state representations |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Python section](../concept-taxonomy.md#python--concept-families).

16 canonical families covering algorithmic patterns. The blocklist rejects `for loop`, `if/else`, `function`, library names alone (`heapq`, `bisect`) — describe the *pattern*, not the syntactic mechanism.

## Authoring allocation matrix

| Question kind | Where it lives | When to author |
|---|---|---|
| **Practice easy** | `easy.json` no `mock_only` | One named pattern, clean, < 50 LOC reference solution |
| **Practice medium** | `medium.json` no `mock_only` | One named pattern in non-obvious application |
| **Practice hard** | `hard.json` no `mock_only` | Pattern + data-structure choice + complexity defense |
| **Mock-only medium** | `medium.json` with `mock_only: true` | Real-world framing (event stream, dedupe a feed, build a session map) instead of abstract array problems. Any of the 16 concept families is eligible; the framing — not the pattern — differentiates mock from practice. |
| **Mock-only hard** | `hard.json` with `mock_only: true` | System-design-flavoured or multi-step decomposition. Priority families: `HEAP & PRIORITY PATTERNS`, `GRAPH TRAVERSAL STRATEGY`, `RECURSION & MEMOIZATION`, `SLIDING WINDOW REASONING` (streaming anomaly detection, window median). |
| **Mock-only chain** | Parent + 1–3 follow-ups, all `mock_only: true` | Natural pivots: scale (10⁸ input), business rule (now ignore X), data quality (handle Nones), edge case (empty input), performance (O(n²) → O(n log n)). Chains travel as atomic units in sessions — never split. |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and realism, not new patterns. A mock-only question recombines patterns the practice bank already teaches at that difficulty (or lower) under fresh, production-realistic framing — it must not clone an existing practice question and must not introduce an algorithmic pattern the curriculum never taught. If a mock would need an untaught pattern, author the practice question first.

## Anti-patterns specific to Python

- **Pure LeetCode trivia** — questions where the only difficulty is recognising an obscure named algorithm with no real-world analogue. Reject.
- **Hard questions with O(n²) reference solutions** — at hard tier, if a better complexity exists, the reference must achieve it.
- **Questions testing language quirks** — `__getitem__` exotica, `==` vs `is` gotchas. Not the test.
- **String-manipulation puzzles disconnected from real work** — anagram-finding has its place; "rotate this string by Fibonacci(n)" is noise.
- **Hidden test cases that change the problem** — every behaviour a hidden test enforces must be inferable from the public description.

## JSON schema

```json
{
  "id": 22018,
  "order": 12,
  "topic": "python",
  "difficulty": "medium",
  "title": "Longest log run with at most K distinct error codes",
  "description": "You're scanning a service's log stream. Given a list `error_codes` (each entry is the error code on one log line, in time order) and an integer `k`, return the length of the longest contiguous run of log lines containing at most `k` distinct error codes — the longest stretch of stable behaviour before too many different failure modes appear.\n\nConstraints:\n- 0 <= len(error_codes) <= 10^5\n- 0 <= k <= number of distinct codes\n- Return 0 when k == 0.",
  "starter_code": "def solve(error_codes: list, k: int) -> int:\n    # Your code here\n    pass",
  "expected_code": "def solve(error_codes: list, k: int) -> int:\n    if k == 0:\n        return 0\n    from collections import defaultdict\n    counts = defaultdict(int)\n    left = best = 0\n    for right, code in enumerate(error_codes):\n        counts[code] += 1\n        while len(counts) > k:\n            counts[error_codes[left]] -= 1\n            if counts[error_codes[left]] == 0:\n                del counts[error_codes[left]]\n            left += 1\n        best = max(best, right - left + 1)\n    return best",
  "solution_code": "<same as expected_code, optionally annotated>",
  "explanation": "Sliding window with a count map over the log stream. Time O(n), space O(min(k, distinct codes)). The while-loop is O(n) amortized: each log line is added once (right) and removed at most once (left). This is the same windowed-aggregation shape used to bound any 'within a moving window' metric over an event stream.",
  "test_cases": [
    {"input": [["500", "503", "500", "429", "504"], 2], "expected": 3},
    {"input": [["504", "504"], 1], "expected": 2},
    {"input": [[], 5], "expected": 0},
    {"input": [["504", "500", "503"], 0], "expected": 0},
    {"input": [["504", "504", "429", "429", "503", "503"], 2], "expected": 4}
  ],
  "public_test_cases": [
    {"input": [["500", "503", "500", "429", "504"], 2], "expected": 3},
    {"input": [["504", "504"], 1], "expected": 2}
  ],
  "hints": [
    "The constraint is on distinct codes in a moving window — what structure tracks that count cheaply?",
    "Expand the window from the right; contract from the left when the distinct-code count exceeds k."
  ],
  "concepts": ["SLIDING WINDOW", "HASH-MAP STATE"]
}
```

Required:
- `expected_code` and `solution_code` produce identical results on all `test_cases`.
- At least one edge case in `test_cases` (empty input, boundary, degenerate input).
- `public_test_cases` = exactly 2 (user can run before submit).
- Hidden tests do not add new constraints beyond what the description states.
- Hints follow the same discipline as other tracks: name the pattern / data structure, not the implementation.

## Verification before commit

```bash
# 1. Reference solution passes all test cases
cd backend && ../.venv/bin/python -c "
import json
q = json.load(open('content/python_questions/medium.json'))[INDEX]
exec(q['expected_code'])
for tc in q['test_cases']:
    assert solve(*tc['input']) == tc['expected'], tc
print('All test cases pass')
"

# 2. Complexity ENFORCED, not eyeballed
# Hard (and complexity-sensitive medium) questions MUST include large hidden test_cases
# sized so a brute-force / O(n²) solution times out (5 s) — and, where memory is the
# lesson, so a load-everything approach trips the 512 MB RLIMIT while a streaming/
# generator solution passes. The reference solution must clear them comfortably.
# Keep public_test_cases small/illustrative; the enforcing inputs are hidden.
# Defend the time/space claim in `explanation`.

# 3. Full content validation
python scripts/validate_content.py

# 4. Python evaluator tests
cd backend && ../.venv/bin/python -m pytest tests/test_python_evaluator.py -q
```
