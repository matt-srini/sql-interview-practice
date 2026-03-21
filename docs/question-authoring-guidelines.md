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

## 1.1 Primary Learning Objective (STRICT)

Every question must have a clear primary learning objective.

Core concepts include:
- Joins
- Aggregation (GROUP BY, HAVING)
- Window Functions
- Subqueries

These core concepts are used for:
- difficulty design
- curriculum coverage
- primary learning objective review

They are not the same thing as the learner-facing `concepts` field in the question JSON.

Guidelines:
- A question should focus on one primary concept
- Supporting concepts are allowed if they are necessary to solve the problem
- Do NOT artificially limit the number of concepts
- Avoid mixing unrelated concepts

Examples:
- Aggregation + JOIN → valid if aggregation is the main objective
- Window + aggregation → valid if sequencing depends on aggregation

Avoid:
- stacking unrelated concepts
- adding concepts without purpose

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

## 1.5 Concept Cohesion (MANDATORY)

If multiple concepts are used:
- They must belong to the same logical flow
- They must solve one unified problem

NOT allowed:
- JOIN + window + subquery + CASE arbitrarily
- artificial difficulty via concept stacking

Difficulty must come from:
- multi-stage reasoning
- transformation steps
- dependency between steps

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
- Prefer a small number of related concepts
- Concepts must be directly related
- Avoid introducing multiple independent reasoning layers

- linear reasoning:
  → join → filter → aggregate

- subqueries:
  - allowed but must be simple
  - must not introduce a second independent logic layer

- CASE:
  - allowed only as a helper

Avoid:
- combining JOIN + subquery + CASE unnecessarily
- multi-layer nested logic

---

## 2.3 Hard

Focus:
- window functions (ROW_NUMBER, RANK, etc.)
- advanced aggregations
- multi-step logic
- edge-case handling

Rules:
- Defined by multi-stage reasoning, not concept count

Every HARD question must:
- Require at least 2 dependent steps (e.g., derive → filter, aggregate → rank)
- Involve grain awareness (correct level of aggregation at each step)
- Include at least one advanced mechanism:
  - Window functions
  - Correlated subqueries (EXISTS / NOT EXISTS)
  - Multi-level aggregation
  - Conditional aggregation

- Supporting concepts are allowed if they are cohesive

Complexity must come from:
- reasoning and dependency between steps
- transformation across stages

Avoid:
- artificial complexity via unnecessary nesting
- mixing unrelated concepts

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
  "schema": {
    "users": ["user_id", "name"]
  },

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

The `concepts` field is a learner-facing reasoning tag set, not a raw SQL primitive inventory.

Each question should include:

"concepts": ["COHORT ANALYSIS", "RETENTION BY MONTH OFFSET"]

Purpose:
- categorization
- future filtering
- learning analytics
- surfacing the problem's reasoning pattern to the learner

Important:
- Tags must describe the business or analytical thinking pattern
- Do NOT use low-level SQL primitives as tags
  - avoid: `JOIN`, `GROUP BY`, `SUBQUERY`, `WINDOW FUNCTION`
  - avoid: `ROW_NUMBER`, `LAG`, `CASE`, `LEFT JOIN`
- Tags should be semantic and reusable
  - examples: `COHORT ANALYSIS`, `FUNNEL ORDER ENFORCEMENT`, `LATEST STATE DERIVATION`, `SEQUENTIAL EVENT PATTERN`
- Keep tags cohesive and short
  - target 2–4 tags per question
  - include only the dominant reasoning patterns, not every helper step
- The `concepts` field does not replace core-concept review
  - the primary SQL concept still determines difficulty and curriculum fit

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
- [ ] schema matches dataset
- [ ] no ambiguity in output

- [ ] concepts are cohesive (no unrelated mixing)
- [ ] concepts are semantic reasoning tags, not SQL primitive names
- [ ] difficulty matches reasoning depth
- [ ] question requires multi-step reasoning (for medium/hard)

---

# 14. Final Goal

Every question should:

- teach something specific
- feel like a real interview problem
- be unambiguous
- reinforce good SQL practices

---

This document is the standard for all current and future question creation.