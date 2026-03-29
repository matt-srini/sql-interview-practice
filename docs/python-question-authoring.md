# Python Track Question Authoring Guidelines

This file covers authoring rules for all three new code-based tracks: Python (algorithms), Pandas, and PySpark. For PySpark, also see `docs/pyspark-curriculum-spec.md`.

---

## Schemas

Each track has its own `schemas.json` in its content directory. This file configures the catalog loader's validation rules.

### `backend/content/python_questions/schemas.json`

```json
{
  "id_ranges": {
    "easy":   { "min": 4001, "max": 4299 },
    "medium": { "min": 4301, "max": 4599 },
    "hard":   { "min": 4601, "max": 4999 }
  },
  "required_fields": [
    "id", "order", "topic", "title", "difficulty",
    "description", "starter_code", "expected_code", "solution_code",
    "explanation", "test_cases", "public_test_cases"
  ],
  "optional_fields": ["hints", "concepts"],
  "difficulty_files": {
    "easy":   "easy.json",
    "medium": "medium.json",
    "hard":   "hard.json"
  }
}
```

### `backend/content/python_data_questions/schemas.json`

```json
{
  "id_ranges": {
    "easy":   { "min": 5001, "max": 5999 },
    "medium": { "min": 6001, "max": 6999 },
    "hard":   { "min": 7001, "max": 7999 }
  },
  "required_fields": [
    "id", "order", "topic", "title", "difficulty",
    "description", "dataset_files", "schema", "dataframes",
    "starter_code", "expected_code", "solution_code", "explanation"
  ],
  "optional_fields": ["hints", "concepts"],
  "difficulty_files": {
    "easy":   "easy.json",
    "medium": "medium.json",
    "hard":   "hard.json"
  }
}
```

### `backend/content/pyspark_questions/schemas.json`

```json
{
  "id_ranges": {
    "easy":   { "min": 11001, "max": 11999 },
    "medium": { "min": 12001, "max": 12999 },
    "hard":   { "min": 13001, "max": 13999 }
  },
  "required_fields": [
    "id", "order", "topic", "title", "difficulty",
    "type", "description", "options", "correct_option", "explanation"
  ],
  "optional_fields": ["code_snippet", "hints", "concepts"],
  "valid_types": ["mcq", "predict_output", "debug", "optimization"],
  "difficulty_files": {
    "easy":   "easy.json",
    "medium": "medium.json",
    "hard":   "hard.json"
  }
}
```

---

## easy.json Structure

Each JSON file is an array of question objects. Example `easy.json` for Python (algorithms):

```json
[
  {
    "id": 4001,
    "order": 1,
    "topic": "python",
    "title": "Two Sum",
    "difficulty": "easy",
    "description": "...",
    "starter_code": "def solve(nums: list, target: int) -> list:\n    # Your code here\n    pass",
    "expected_code": "def solve(nums, target):\n    ...",
    "solution_code": "def solve(nums: list, target: int) -> list:\n    ...",
    "explanation": "...",
    "test_cases": [
      { "input": [[2, 7, 11, 15], 9], "expected": [0, 1] }
    ],
    "public_test_cases": 2,
    "hints": ["..."],
    "concepts": ["hash map"]
  }
]
```

---

## ID Assignment

IDs must be unique across **all** question files in all tracks (including SQL). Before assigning an ID, check that it doesn't already exist in:
- `backend/content/questions/easy.json`, `medium.json`, `hard.json` (SQL, 1001–3999)
- `backend/content/python_questions/` (4001–4999)
- `backend/content/python_data_questions/` (5001–7999)
- `backend/content/pyspark_questions/` (11001–13999)

Sample question IDs:
- Python algorithms samples: 401–423
- Pandas samples: 501–723
- PySpark samples: 4501–4723

---

## Writing Good Questions

### Python (Algorithms)

**Do:**
- Use realistic problem framing (not "return true if the string is a palindrome" — instead frame it as a real use case: "Given a username, check if it reads the same forwards and backwards for vanity URL validation.")
- Keep function signatures consistent: always `def solve(...):`
- Have at least one edge case in test_cases: empty list, single element, all duplicates, zero, negative numbers

**Don't:**
- Require knowledge of Python 3.12+ features
- Require any imported library
- Write test cases that are solvable by brute force O(n²) if the question's intended solution is O(n)

### Pandas

**Do:**
- Use the real dataset tables (with their actual column names and data types)
- Specify exactly which columns the output should contain
- Specify sort order explicitly in the description
- Make the question answerable with at most 3 real-world pandas techniques

**Don't:**
- Require knowledge of internal pandas implementation details
- Assume specific pandas version behavior for edge cases
- Use `apply()` in expected solutions unless the question teaches `apply()`

### PySpark

**Do:**
- Anchor the question in a real-world scenario (not "what does filter() return")
- Make distractors represent actual misconceptions engineers have
- For `predict_output`, keep the code snippet runnable mentally with 3–5 sample rows

**Don't:**
- Ask about default configuration values (trivia)
- Use deprecated Spark APIs (RDD-based API, `sc.parallelize` — unless specifically teaching migration)
- Write optimization questions where all 4 options would be correct in some scenario

---

## Testing Your Questions Before Committing

### Python (Algorithms)

Run your `expected_code` manually:
```python
# Copy expected_code into a Python REPL and call solve() with each test case
exec(expected_code)
for tc in test_cases:
    result = solve(*tc["input"])
    assert result == tc["expected"], f"Failed: {result} != {tc['expected']}"
print("All test cases passed")
```

### Pandas

Run your `expected_code` against the real CSVs:
```python
import pandas as pd
# Load the DataFrames
df_users = pd.read_csv("backend/datasets/users.csv")
# ... add others as needed

exec(expected_code)
result = solve(df_users=df_users)
print(result.head(10))
print(result.dtypes)
print(result.shape)
```

Verify:
- Column names match what the description says
- Row count is reasonable (not 0, not unexpectedly huge)
- No NaN values where not expected
- Float values round correctly

### PySpark

Check that `correct_option` is 0-indexed correctly. Read through all 4 options and confirm:
- The correct option is unambiguously correct
- The 3 wrong options are plausible but clearly incorrect when explained
- The explanation covers all 4 options

---

## Diff Rules (adding questions)

When adding new questions:
1. Add to the appropriate `easy.json`, `medium.json`, or `hard.json` array
2. Assign the next available ID in the range
3. Set `order` to the next available integer (check the highest `order` in the file)
4. Run `pytest backend/tests/` — the catalog loader tests will catch schema violations
5. Test the question end-to-end via the API before committing

When modifying existing questions:
- Do not change `id` or `order`
- Do not change `topic` or `difficulty`
- If changing `test_cases`, ensure `public_test_cases` is still ≤ `len(test_cases)`
- If changing `expected_code`, re-run all test cases

---

## Locating Existing Questions

```bash
# Find all Python algorithm questions
cat backend/content/python_questions/easy.json | python3 -c "import json,sys; [print(q['id'], q['title']) for q in json.load(sys.stdin)]"

# Find all Python Data questions with a specific concept
grep -r "groupby" backend/content/python_data_questions/

# Check for duplicate IDs across all tracks
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    qs = json.load(open(f))
    all_ids.extend(q['id'] for q in qs)
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"
```
