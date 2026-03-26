# Python (Algorithms) Curriculum Spec

Track: **Python**
Topic key: `python`
ID range: easy 4001–4299, medium 4301–4599, hard 4601–4999
Sample IDs: easy 401–403, medium 411–413, hard 421–423

---

## Difficulty Standards

### Easy

- Single function, clear I/O contract
- No more than 1 core algorithmic concept
- Solvable with basic Python constructs: loops, conditionals, built-in types (list, dict, set, str)
- No recursion, no OOP, no complex data structures
- Test cases: 3 total (2 public, 1 hidden)
- Time complexity: O(n) or O(n log n) expected solution

### Medium

- 1–2 concepts, directly related
- May require a known data structure (stack, queue, deque, heap) or algorithm pattern (binary search, two pointers, sliding window)
- Recursion allowed
- Test cases: 5 total (2 public, 3 hidden)
- Time complexity: O(n log n) or O(n) with a non-obvious approach

### Hard

- Multi-stage reasoning: at least 2 dependent algorithmic steps
- Advanced patterns: dynamic programming, backtracking, graph traversal (BFS/DFS), monotonic stack, trie
- Test cases: 7 total (2 public, 5 hidden)
- Time complexity: O(n²) naive is not acceptable — expected solution must be O(n log n) or better

---

## Question JSON Schema

All fields required unless marked optional.

```json
{
  "id": 4001,
  "order": 1,
  "topic": "python",
  "title": "Two Sum",
  "difficulty": "easy",
  "description": "Given a list of integers `nums` and a target integer `target`, return a list containing the indices of the two numbers that add up to `target`. You may assume exactly one solution exists. You may not use the same element twice.",
  "starter_code": "def solve(nums: list, target: int) -> list:\n    # Your code here\n    pass",
  "expected_code": "def solve(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "solution_code": "def solve(nums: list, target: int) -> list:\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "explanation": "Use a hash map to store each number and its index as you iterate. For each number n, check if (target - n) is already in the map. If so, return the two indices. This runs in O(n) time with O(n) space.",
  "test_cases": [
    { "input": [[2, 7, 11, 15], 9], "expected": [0, 1] },
    { "input": [[3, 2, 4], 6], "expected": [1, 2] },
    { "input": [[3, 3], 6], "expected": [0, 1] }
  ],
  "public_test_cases": 2,
  "hints": [
    "Think about what information you need to store as you iterate.",
    "For each number n, ask: have I seen (target - n) before?"
  ],
  "concepts": ["hash map", "complement lookup"]
}
```

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | int | Yes | easy 4001–4299, medium 4301–4599, hard 4601–4999 |
| `order` | int | Yes | 1-based display order within difficulty |
| `topic` | string | Yes | Always `"python"` |
| `title` | string | Yes | ≤ 40 chars, title-case |
| `difficulty` | string | Yes | `"easy"` / `"medium"` / `"hard"` |
| `description` | string | Yes | Full problem statement. Specify expected return type and edge cases. |
| `starter_code` | string | Yes | `def solve(...):` stub with type hints + `pass`. Use `\n` for newlines. |
| `expected_code` | string | Yes | Trusted, correct solution. Used to verify test case outputs if not stored directly. |
| `solution_code` | string | Yes | Formatted, readable version shown to user after correct solve. |
| `explanation` | string | Yes | Step-by-step reasoning. Include time + space complexity. |
| `test_cases` | array | Yes | Array of `{ "input": [...positional_args], "expected": value }`. |
| `public_test_cases` | int | Yes | How many test cases are shown to the user. Rest are hidden. |
| `hints` | array | No | 1–2 hints. Progressive: first hint is vague, second more specific. |
| `concepts` | array | No | 1–3 semantic tags. Lowercase. E.g. `"hash map"`, `"two pointers"`, `"sliding window"`. |

### `test_cases.input` format

`input` is an array of positional arguments passed as `solve(*input)`. Examples:
- Single arg: `[[2, 7, 11, 15], 9]` → `solve([2,7,11,15], 9)` — outer array is args list, inner `[2,7,11,15]` is the first arg
- Two args: `[[1, 2, 3], 2]` → `solve([1,2,3], 2)`
- String arg: `["racecar"]` → `solve("racecar")`

### `test_cases.expected` format

The value returned by `solve()`. Can be any JSON-serializable type:
- Integer: `3`
- List: `[0, 1]`
- String: `"abcba"`
- Boolean: `true`
- List of lists: `[[1,2],[3,4]]`

**Float comparison:** Floats within 1e-5 are treated as equal. State expected float precision in the description.

**List comparison:** Exact element equality. If order doesn't matter, sort both in `expected_code` and document this in the description.

---

## MVP Question Bank — 30 Questions

### Easy (10) — IDs 4001–4010

| ID | Title | Core Concept | Function Signature |
|---|---|---|---|
| 4001 | Two Sum | Hash map | `solve(nums: list, target: int) -> list` |
| 4002 | Palindrome Check | String reversal / two pointers | `solve(s: str) -> bool` |
| 4003 | Reverse a List | Slicing / two pointers | `solve(nums: list) -> list` |
| 4004 | Count Vowels | String iteration | `solve(s: str) -> int` |
| 4005 | FizzBuzz | Modulo, conditionals | `solve(n: int) -> list` |
| 4006 | Fibonacci (nth) | Iteration or memoization | `solve(n: int) -> int` |
| 4007 | Remove Duplicates | Set / dict | `solve(nums: list) -> list` |
| 4008 | Anagram Check | Sorted strings / Counter | `solve(s: str, t: str) -> bool` |
| 4009 | Find Second Largest | Single pass | `solve(nums: list) -> int` |
| 4010 | Valid Parentheses | Stack | `solve(s: str) -> bool` |

### Medium (10) — IDs 4301–4310

| ID | Title | Core Concept |
|---|---|---|
| 4301 | Binary Search | Divide and conquer |
| 4302 | Merge Sorted Arrays | Two pointers |
| 4303 | Group Anagrams | Hash map + sorting |
| 4304 | Longest Common Prefix | String scanning |
| 4305 | Move Zeros | Two pointers, in-place |
| 4306 | Linked List Cycle (simulate with list) | Floyd's algorithm / set |
| 4307 | Matrix Rotation (90°) | In-place transpose |
| 4308 | Sliding Window Max | Deque |
| 4309 | Power of Two | Bit manipulation |
| 4310 | Queue via Two Stacks | Stack simulation |

### Hard (10) — IDs 4601–4610

| ID | Title | Core Concept |
|---|---|---|
| 4601 | Longest Substring Without Repeating Chars | Sliding window + set |
| 4602 | Merge Intervals | Sorting + greedy |
| 4603 | Minimum Window Substring | Sliding window + counter |
| 4604 | Trapping Rain Water | Stack / two pointers |
| 4605 | Word Break | Dynamic programming |
| 4606 | Coin Change | DP (unbounded knapsack) |
| 4607 | Number of Islands | BFS/DFS on grid |
| 4608 | LRU Cache | OrderedDict |
| 4609 | Decode Ways | DP |
| 4610 | Serialize / Deserialize BST | Tree traversal |

---

## Authoring Rules

1. **Every question must have a `def solve(...)` function.** The harness calls `solve(*test_case["input"])`. No top-level code outside the function (unless it's a helper function, which must be defined before `solve`).

2. **`starter_code` must be a syntactically valid Python stub.** Always end with `pass`.

3. **`expected_code` must be correct and deterministic.** Run it against every test case manually before committing.

4. **`test_cases` must include at least one edge case** (empty input, single element, negative number, etc.).

5. **`public_test_cases` should be 2 for all difficulties.** Hidden test cases exist to prevent hardcoding.

6. **Concepts are semantic patterns, not Python builtins.** Use `"hash map"`, not `"dict"`. Use `"sliding window"`, not `"for loop"`.

7. **Description must state the return type** and whether input is guaranteed to satisfy any constraints (e.g., "You may assume exactly one solution exists").

8. **Do not import anything in `expected_code`.** All standard Python builtins are available. If you need `collections.Counter`, write it without importing: use a dict instead, or list the constraint "assume Python standard library is available" in the description and include the import in `starter_code`.

   Exception: `from collections import deque` and `from heapq import *` are pre-available in the harness for algorithm questions. Document in `starter_code` as a comment: `# deque and heapq are available`.
