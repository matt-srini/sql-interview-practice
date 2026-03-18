

# Question Authoring Guidelines — SQL Interview Practice Platform

## Purpose
This document defines how SQL questions must be designed, structured, and validated.

The goal is to ensure:
- high-quality learning experience
- consistency across questions
- realistic interview preparation
- unambiguous evaluation

---

# 1. Core Principles

## 1.1 Each Question Tests ONE Core Concept
Every question must have a clear focus.

Examples:
- filtering → WHERE
- aggregation → GROUP BY
- joins → JOIN
- ranking → window functions

Avoid:
- mixing too many concepts in easy/medium questions

---

## 1.2 Clarity Over Cleverness
- The problem statement must be easy to understand
- The difficulty should come from logic, not wording

Avoid:
- vague instructions
- ambiguous requirements

---

## 1.3 Deterministic Output
Every question must produce a clearly defined result set.

- No ambiguity in expected output
- No dependence on undefined ordering

If ordering matters → explicitly require it.

---

## 1.4 Real-World Context
Questions should feel like real business problems.

Examples:
- user behavior analysis
- order metrics
- revenue calculations

Avoid:
- abstract or toy-like questions

---

# 2. Difficulty Guidelines

## 2.1 Easy

Focus:
- SELECT
- WHERE
- ORDER BY
- basic GROUP BY
- simple JOIN (1 join max)

Rules:
- single-step logic
- no subqueries
- no window functions

---

## 2.2 Medium

Focus:
- multi-table JOINs
- GROUP BY + HAVING
- subqueries (basic)
- CASE statements

Rules:
- 2–3 logical steps
- moderate reasoning required

---

## 2.3 Hard

Focus:
- window functions (ROW_NUMBER, RANK, etc.)
- advanced aggregations
- multi-step logic
- edge-case handling

Rules:
- multi-layer logic
- may require optimization thinking
- can use advanced SQL features

---

# 3. SQL Style Guidelines

## 3.1 Portability (IMPORTANT)

### Easy & Medium
- Must be portable across:
  - PostgreSQL
  - MySQL
  - SQL Server

Avoid:
- engine-specific functions (e.g., DuckDB-only features)

---

### Hard
- Can use advanced SQL features
- Prefer standard SQL first
- Engine-specific usage must be justified

---

## 3.2 Query Style

Preferred:
- explicit JOIN syntax
- clear aliases
- readable formatting

Avoid:
- implicit joins
- overly nested queries (unless required)

---

# 4. Question Structure (JSON Contract)

Each question MUST follow:

{
  "id": 1001,
  "order": 1,
  "title": "Short descriptive title",
  "difficulty": "easy",
  "description": "Clear problem statement",

  "dataset_files": ["users.csv"],
  "tables": ["users"],

  "expected_query": "...",
  "solution_query": "...",
  "explanation": "...",

  "hints": [],
  "concepts": []
}

---

# 5. Description Guidelines

A good description:

- clearly defines:
  - what to compute
  - what tables to use
  - expected columns

- may include:
  - constraints
  - filters
  - business context

---

## Example (Good)

"Find the total order amount for each user who has placed at least one order. Return user_id and total_amount."

---

## Example (Bad)

"Calculate user totals."

---

# 6. Expected Query vs Solution Query

## expected_query
- used for evaluation
- must produce correct result deterministically

## solution_query
- shown to user after submission
- should be:
  - clean
  - readable
  - best-practice SQL

---

# 7. Explanation Guidelines (VERY IMPORTANT)

Each explanation must:

1. Explain the logic step-by-step
2. Clarify WHY the approach works
3. Mention key SQL concepts used

---

## Example (Good)

"This query groups rows by user_id to calculate the total order amount per user using SUM(amount). The HAVING clause ensures only users with at least one order are included."

---

## Example (Bad)

"We grouped by user_id."

---

# 8. Hints Guidelines

Hints should:
- guide thinking, not reveal answer
- be progressive (if multiple hints)

Example:
- Hint 1: "You may need to aggregate order amounts"
- Hint 2: "Consider grouping by user_id"

---

# 9. Concepts Tagging

Each question should include:

"concepts": ["GROUP BY", "JOIN"]

Purpose:
- categorization
- future filtering
- learning analytics

---

# 10. Dataset Usage Rules

- Only use valid dataset_files
- Tables must match dataset_files
- Do NOT reference non-existent tables

---

# 11. Edge Case Considerations

Think about:
- NULL values
- duplicate rows
- zero results
- ordering

Ensure evaluation handles these correctly.

---

# 12. Common Mistakes to Avoid

- ambiguous instructions
- missing ORDER BY when needed
- inconsistent column naming
- mixing difficulty levels
- overly complex easy questions
- trivial hard questions

---

# 13. Quality Checklist (MANDATORY)

Before adding a question, verify:

- [ ] ID is in correct range
- [ ] difficulty is correct
- [ ] description is clear
- [ ] expected_query is correct
- [ ] solution_query is clean
- [ ] explanation is detailed
- [ ] dataset_files exist
- [ ] tables match dataset
- [ ] no ambiguity in output

---

# 14. Final Goal

Every question should:

- teach something specific
- feel like a real interview problem
- be unambiguous
- reinforce good SQL practices

---

This document is the standard for all current and future question creation.