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

Python has **dedicated sample questions** in `backend/content/sample_questions/python.json` (IDs 211–213 easy, 221–223 medium, 231–233 hard). Sample questions are completely separate from the practice and mock pools and must never duplicate practice content.

## Difficulty vocabulary

| Tier | Reasoning depth | Patterns | Complexity expected | What's out |
|---|---|---|---|---|
| **Easy** | Single algorithmic concept. Basic data structures. | Linear scan, hash-map state, basic string manipulation, list comprehensions, simple counting | O(n) or O(n log n) | Nested DP, graph algorithms |
| **Medium** | One named pattern in clean form. Recognising which pattern applies *is* the test. | Sliding window, two pointers, binary search (incl. on answer space), heap-based selection, BFS/DFS basics, 1D DP, backtracking | O(n) or O(n log n) | 2D DP, advanced graph (Dijkstra, Union-Find) |
| **Hard** | Multi-step decomposition + non-obvious data structure choice. | 2D DP, graph algorithms (Dijkstra, Union-Find, topological sort, articulation), Trie, system-design data structures (LRU cache, median-from-stream heap pair), advanced string (KMP, Aho-Corasick where motivated) | Optimal complexity required — **no O(n²) accepted at hard if O(n log n) exists** | "Hard because the constraints are weird" |

If a question's hardness comes from "you have to remember to handle the empty case AND the duplicates case AND the negative case AND..." — that's not hard, that's accumulation. Find the *one* pattern that's actually demanding.

**Every pattern above (and in the concept arc below) earns its place only if it maps to real data work — name the analogue.** Sliding window → event-stream windowing; heap top-K → heavy-hitters / hot keys; topological sort → pipeline DAG ordering & dependency resolution; Trie → key-prefix routing / dictionary tokenization; 2-D DP → record fuzzy-matching / sequence alignment / log diffing; graph connectivity & articulation → lineage criticality (single points of failure); BFS/DFS → reachability over a dependency or event graph. If you cannot name a data-work use for a pattern, it is competitive-programming trivia and does not belong here — the prime suspects are permutation/subset backtracking for its own sake, bit-manipulation tricks, and number-theory puzzles. This is the spine of the "What this track trains" framing above, applied to the ladder.

**Deprioritized — out unless a genuine data analogue is articulable:** permutation/subset/N-queens backtracking, grid-path DP (unique-paths style), bit-manipulation tricks, number-theory/math puzzles, regex-matching DP, linked-list pointer gymnastics, and standalone matrix-simulation (spiral, Sudoku). The Difficulty-vocabulary and Concept-arc tables retain the *named patterns* (2-D DP, Trie, articulation, KMP/Aho-Corasick) because each has the analogue listed above — but their puzzle realisations are not authored here.

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
| Hard | graph algorithms with a pipeline analogue (topological sort → DAG/lineage ordering; `UNION-FIND & DISJOINT SET` → record linkage; `WEIGHTED SHORTEST PATH` / Dijkstra → critical-path/latency) → 2D DP as sequence diff/alignment (edit distance for fuzzy dedup) → Trie (key-prefix routing / autocomplete) / Aho-Corasick (multi-pattern log scanning) → system-design DS (LRU, `STREAMING / ONLINE REDUCTION`: median heap, sliding-window max, Misra-Gries) → advanced state representations |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Python section](../concept-taxonomy.md#python--concept-families).

19 canonical families covering algorithmic patterns. The blocklist rejects `for loop`, `if/else`, `function`, library names alone (`heapq`, `bisect`) — describe the *pattern*, not the syntactic mechanism.

## Authoring allocation matrix

| Question kind | Where it lives | When to author |
|---|---|---|
| **Practice easy** | `easy.json` no `mock_only` | One named pattern, clean, < 50 LOC reference solution |
| **Practice medium** | `medium.json` no `mock_only` | One named pattern in non-obvious application |
| **Practice hard** | `hard.json` no `mock_only` | Pattern + data-structure choice + complexity defense |
| **Mock-only medium** | `medium.json` with `mock_only: true` | Real-world framing (event stream, dedupe a feed, build a session map) instead of abstract array problems. Any of the 19 concept families is eligible; the framing — not the pattern — differentiates mock from practice. |
| **Mock-only hard** | `hard.json` with `mock_only: true` | System-design-flavoured or multi-step decomposition. Priority families: `HEAP & PRIORITY QUEUE`, `GRAPH TRAVERSAL (BFS / DFS)`, `UNION-FIND & DISJOINT SET`, `WEIGHTED SHORTEST PATH`, `DYNAMIC PROGRAMMING (1D)`, `STREAMING / ONLINE REDUCTION` (streaming anomaly detection, window median). |
| **Mock-only chain** | Parent + 1–3 follow-ups, all `mock_only: true` | Natural pivots: scale (10⁸ input), business rule (now ignore X), data quality (handle Nones), edge case (empty input), performance (O(n²) → O(n log n)). Chains travel as atomic units in sessions — never split. |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and realism, not new patterns. A mock-only question recombines patterns the practice bank already teaches at that difficulty (or lower) under fresh, production-realistic framing — it must not clone an existing practice question and must not introduce an algorithmic pattern the curriculum never taught. If a mock would need an untaught pattern, author the practice question first.

## Coverage & sizing targets

These are the durable *targets* (what the bank ought to look like). For live counts (what it *is* right now) see the "Question bank current state" table in [`docs/content-authoring.md`](../content-authoring.md) and the content footprint in `CLAUDE.md`. **Targets are provisional — revisit against real Pro/Elite usage data.**

- **No mock-only realism family.** Python's families are pure algorithmic patterns; the candidate "lens" (complexity & memory) is **practice-gradable** via the executable harness (O(n²) times out / load-everything OOMs on sized hidden inputs) and is carried in mock by the `performance_pivot` chain dimension, never a concept tag. Empty Python set in `MOCK_ONLY_REALISM_FAMILIES` (`backend/concept_families.py`) makes this explicit.
- **Practice: lean, fully data-grounded.** Target ~80–85, with NO LeetCode-puzzle questions (deprecated set: spiral / Sudoku / rain-water / parentheses / regex DP / linked-list reversal / math-trivia / library-API trivia). One teaching arc per family per applicable tier; grow only to fix a genuine arc break, never to pad volume. Tier balance ~⅖ easy / ⅖ medium / ⅕ hard is healthy for the algorithmic curriculum.
- **Mock-only: ~90–120, hard-skewed.** Python has a finite 16-then-19-family pattern space and reskinning algorithms produces hollow clones, so the target is smaller than SQL's ~150. **~55/45 medium/hard**, **~⅓ chain members.** Natural Python chain pivots: `performance_pivot` (O(n²) → O(n log n)), `scale_pivot` (10⁸ input → now stream it), `edge_case_pivot` (empty / single / None), `data_quality_pivot` (None / dirty values in the feed). Priority families for mock: streaming windows, heavy hitters (heap top-K + Misra-Gries), sessionization, interval / uptime merging, pipeline DAG ordering, in-memory join / dedup, k-way merge of sorted streams, streaming median.

**Mock-only chain inventory (as of 2026-05-26, dimension counts updated 2026-05-26 post-audit):** 18 chains, each parent (medium) + 1 follow-up (hard) — total 36 chain-member slots, ~35% of 103 mock-only. Dimension coverage: `business_rule_pivot` 8, `scale_pivot` 6, `performance_pivot` 2, `edge_case_pivot` 1, `data_quality_pivot` 1 (= 5 of 7 universal dimensions; `ambiguity_pivot` and `stakeholder_pivot` not exercised by Python's algorithmic-pattern curriculum, which is the right call — ambiguity-under-PM-pressure and stakeholder-conflict are operational textures that fit SQL/Pandas/DE better than pure algorithm reasoning). Documentation gap caught 2026-05-26 — chain inventory was authored in Python Phase 2 but never recorded in the closeout; orphan-child bug Q23080→Q22092 surfaced during the audit (resolved same day).

**Chain dimension distribution (audited 2026-05-26):** Post-audit relabels, Python's chain dimensions concentrate on `business_rule_pivot` (8 of 18 chains, ~44%) with `scale_pivot` (6), `performance_pivot` (2), `edge_case_pivot` (1), `data_quality_pivot` (1). This is honest tagging, not variety-padding — Python is algorithmic by curriculum design, and natural interview extensions in this space ARE rule-changes ("now find non-monotone runs instead of monotone," "now count paths instead of depth") more than scale-shifts or data-quality pivots. Operational tracks (SQL, DE, DM) extend more naturally on scale/data-quality; Python extends more naturally on rule-pivots. Future audits should treat this concentration as expected for Python and not re-flag it. Five chains (22072→23059, 22085→23073, 22088→23072, 22093→23074, 22094→23076) carry an acknowledged weak parent-child bridge — relabeled to `business_rule_pivot` rather than dissolved; candidates for dissolution review if Interview Loop telemetry shows users finding these jumps jarring.

- **The bar for every mock-only question: recombination, not reskin.** A mock title that's a known practice problem with a thin business veneer is a clone, not a recombination; drop or genuinely re-author. The headline quality risk for this track is "harder named LeetCode pattern" sneaking in via mock framing.
- **Complexity enforcement is a graded property of practice.** All hard practice questions (+ complexity-sensitive medium) carry hidden generator-spec `test_cases` sized so the intended asymptotics is the only thing that survives the 5 s / 512 MB harness. See the Generator-spec schema in the Verification section.

### Per-family coverage exceptions (validator soft warnings — intentionally curated lean)

The three families below are registered in `CONCEPT_FAMILIES["python"]` but are intentionally held lean on mock-only content. The validator emits per-family coverage warnings for them; those warnings are documented here as load-bearing exceptions under rule 6 (quality override) and the anti-puzzle curation philosophy.

**`BACKTRACKING & COMBINATORIAL SEARCH` — zero mock-only (rule 4 dead-family warning expected)**

The family's canonical puzzle implementations — subset enumeration, constrained permutation generation, N-queens, Sudoku, parentheses balancing — are explicitly deprecated by this track's anti-puzzle philosophy (see Difficulty vocabulary § Deprioritized). A data-professional motivation for standalone backtracking is hard to construct without falling into "thin business-veneer over a classic puzzle" territory (the reject-on-sight criterion). The family remains registered because `BST` operations, `SERIALIZATION`, `VISITED STATE` tracking, and recursive tree traversal (`PREORDER`) are genuine data-professional patterns (tree serialization for pipeline DAGs, BST for ordered-set maintenance, visited-state tracking in graph search). One practice question (23036 "Valid Column Report Orderings") covers constrained enumeration as a single curriculum touchpoint; authoring additional mock-only would require producing the exact puzzle patterns the curriculum rejects. This is a curation-intentional low-water mark, not an authoring gap.

**`IN-PLACE TRANSFORMATION & SPACE OPTIMIZATION` — 1 mock-only (rule 2 floor warning expected)**

In-place transformation as a *standalone* challenge (matrix rotation, spiral traversal, in-place array reversal as the primary test) is puzzle territory per the Difficulty vocabulary § Deprioritized list ("standalone matrix-simulation"). The family's genuine data-professional value (space-efficient algorithms, cache-friendly access patterns, memory-bounded streaming) is already expressed in four practice questions where in-place technique appears as a secondary co-tag alongside the primary algorithmic pattern (e.g., 22018 "Priority-Partition Log Entries" — TWO POINTERS + in-place partition; 23006 "Number of Islands" — GRAPH TRAVERSAL + in-place visited-state). The single existing mock-only (23052 "In-Place N×N Matrix Rotation") is a borderline puzzle that would not be authored under today's stricter policy. Authoring three more mock-only to hit the floor-4 target would produce exactly the puzzle variants this track rejects. The memory/space-optimization reasoning that is genuinely data-professional is better carried by `STREAMING / ONLINE REDUCTION` (bounded-state and space-budget patterns) and `DYNAMIC PROGRAMMING (1D)` space-optimized variants.

**`MODULAR ARITHMETIC & NUMBER THEORY` — zero mock-only (rule 4 dead-family warning expected)**

Number theory (prime sieves, GCD/LCM puzzles, modular exponentiation, XOR tricks, power-of-two checks) is competitive-programming trivia with no durable data-professional analogue. The family is registered because two practice questions use numeric formulas that data professionals actually encounter: 21003 uses modular cycling to assign category labels (a legitimate use of `%`), and 22004 uses the Gauss sum formula to detect a missing record ID (a real data-engineering debugging pattern). Authoring mock-only content for this family would require either (a) pure number theory puzzles (banned) or (b) increasingly contrived business veneers over math tricks. Neither is acceptable. The two practice questions represent the practical boundary of this family's data-professional reach.

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
# 1. Loader + schema validation (catches ID conflicts, missing fields, taxonomy drift)
cd backend && ../.venv/bin/python -c "
from python_questions import get_all_questions, get_mock_questions_by_difficulty
qs = get_all_questions()
mqs = [q for qs2 in get_mock_questions_by_difficulty().values() for q in qs2]
print(f'Loaded {len(qs)} practice + {len(mqs)} mock questions')
"

# 2. Resolver — ZERO unresolved concept tags
cd backend && ../.venv/bin/python -c "
from python_questions import get_all_questions, get_mock_questions_by_difficulty
from concept_families import resolve_to_family, CONCEPT_FAMILIES
fams = set(CONCEPT_FAMILIES['python'].keys())
all_qs = get_all_questions() + [q for qs in get_mock_questions_by_difficulty().values() for q in qs]
unresolved = [(q['id'],t) for q in all_qs for t in q.get('concepts',[]) if resolve_to_family(t,'python') not in fams]
assert not unresolved, f'Unresolved tags: {unresolved}'
print('Resolver: UNRESOLVED=0')
"

# 3. Python evaluator tests (TestGeneratorExpansion 7-case suite + property tests)
cd backend && ../.venv/bin/python -m pytest tests/test_python_evaluator.py -q

# 4. File-size gate: du -sh backend/content/python_questions/ must be ≤ 5 MB
#    Generator specs keep large hidden tests as compact JSON dicts — never as
#    literal arrays. See generator schema below.

# 5. Complexity gate (for generator-spec questions)
#    After authoring a hidden test with {"compute":"reference"}, spot-check that
#    a naïve O(n²) approach times out and the reference completes in <1s:
cd backend && ../.venv/bin/python -c "
import time, json
from python_evaluator import _expand_arg
q = json.load(open('content/python_questions/hard.json'))[INDEX]
tc = q['test_cases'][-1]  # last tc is the generator hidden test
expanded = [_expand_arg(a) for a in tc['input']]
ns = {}; exec(q['expected_code'], ns)
t0 = time.time(); ns['solve'](*expanded); t = time.time()-t0
print(f'Reference: {t:.3f}s (must be <1s)')
"
```

## Generator-spec schema for hidden test cases

Hidden test cases use generator specs instead of literal large arrays.
The expansion happens in the trusted evaluator process; the sandbox harness
receives only expanded literal values.

```json
{
  "input": [
    {"gen": "random_ints", "n": 100000, "seed": 42, "low": 0, "high": 9999,
     "distribution": "zipf"},
    5
  ],
  "expected": {"compute": "reference"}
}
```

**Six generators** (all in `backend/python_evaluator.py`, all seeded for determinism):

| Generator | Key params | Use case |
|---|---|---|
| `random_ints` | `n, seed, low, high, distribution` | Most algorithm inputs; `distribution` ∈ `uniform` (default) / `low_cardinality` / `high_cardinality` / `zipf` |
| `random_floats` | `n, seed, low, high` | Float-based problems |
| `random_strings` | `n, seed, alphabet, min_len, max_len` | String algorithm inputs |
| `sorted_ints` | `n, seed, low, high, unique=False` | Two-pointer / binary-search inputs; `unique=True` raises if n > range |
| `random_pairs` | `n, seed, key_space, value_low, value_high` | Interval / join inputs; returns `[[k,v],…]` |
| `random_graph` | `n_nodes, n_edges, seed, weighted, directed, dag` | Graph algorithm inputs; `dag=True` → all edges have u < v |

**Invariants enforced by `_expand_test_case`:**
- Any generator-spec input → `expected` MUST be `{"compute": "reference"}`
- `{"compute": "reference"}` → at least one input arg must be a generator spec
- Public test cases (`public_test_cases`) are always all-literal; generators are hidden-only

**Sizing for complexity bite (5-second sandbox timeout):**
- Sliding window O(nk): `n ≥ 500 000` with `k ≥ 2 000` bites C-level `max(slice)` naive
- O(n²) algorithms (LIS DP, inversion count, two-sum nested loops): `n ≥ 20 000` for reliable bite
- Top-K frequency count via `list.count()`: `n ≥ 100 000` with zipf distribution bites
- LCS hash-set approach O(n): no bite path; use correctness test only
- Sorting-based O(n log n): no bite path versus reference; skip generator or use correctness test
