# SQL Curriculum Specification (Production-Grade)

This document defines the **source-of-truth curriculum design** for the SQL Interview Practice Platform.

It is used by:
- Question Authoring Agent
- Backend validation logic (optional future)
- Human review

STRICT RULE: All questions must conform to this spec.

---

# GLOBAL PRINCIPLES

- Focus on **real-world business datasets**
  - users, orders, products, events, employees, payments
- Avoid academic or artificial problems
- Prefer **clarity over trickiness**

## Definition of Core Concept (MANDATORY)

Core concepts refer to fundamental SQL capabilities:
- Joins
- Aggregation (GROUP BY, HAVING)
- Window Functions
- Subqueries

These core concepts are the curriculum and difficulty framework.
They are not the same thing as the learner-facing `concepts` field stored on each question.

The following are NOT separate core concepts (they are patterns/usages):
- ROW_NUMBER, RANK, LAG, LEAD
- Top-N per group
- Running totals / averages
- Event sequencing

These must be treated as applications of a core concept, not additional concepts.

- EASY:
  - Focus on a single primary concept
  - Minimal transformation logic
  - No multi-step reasoning

- MEDIUM:
  - Combine related concepts in a linear flow
  - Typical pattern: join → filter → aggregate
  - Limited use of subqueries (simple and focused)

- HARD:
  - Defined by multi-stage reasoning, not concept count
  - Requires at least 2 dependent steps (e.g., derive → rank, sequence → filter)
  - May involve multiple concepts, but must have one clear primary objective
  - Complexity must come from reasoning, not stacking unrelated concepts

## Concept Cohesion Rule (STRICT)

- If multiple concepts are used, they must:
  - Belong to the same logical flow
  - Solve one unified problem

- NOT allowed:
  - Mixing unrelated concepts (e.g., JOIN + window + subquery + CASE arbitrarily)
  - Increasing difficulty by stacking independent ideas

- Difficulty must come from:
  - Multi-stage reasoning
  - Transformation steps
  - Correct sequencing and dependency between steps
- Every question must be:
  - Deterministic
  - Evaluatable via result comparison
  - Free of ambiguity

## Concept Counting Rule (STRICT)

- Only the following are counted as core concepts:
  - Joins
  - Aggregation
  - Window Functions
  - Subqueries

- Patterns and variations DO NOT increase concept count:
  - ROW_NUMBER, RANK, LAG, LEAD → count as Window Functions
  - Top-N per group → Window Function pattern
  - Running totals → Window Function pattern

- Multiple uses of the same concept still count as ONE concept

Examples:
- ROW_NUMBER + RANK → 1 concept (Window Functions)
- GROUP BY + HAVING → 1 concept (Aggregation)
- JOIN + GROUP BY → 2 concepts

## Question Metadata Tags

The `concepts` array on a question is a learner-facing metadata field.

Rules for `concepts`:
- Use semantic reasoning tags, not raw SQL primitives
- Tags should describe the analytical pattern the learner is practicing
- Keep tags cohesive and limited to the dominant patterns in the problem
- Target 2–4 tags per question

Examples of good tags:
- COHORT ANALYSIS
- RUNNING TOTAL THRESHOLD DETECTION
- LATEST STATE DERIVATION
- FUNNEL ORDER ENFORCEMENT
- CUMULATIVE CONTRIBUTION (PARETO)

Examples of bad tags:
- JOIN
- AGGREGATION
- WINDOW FUNCTION
- SUBQUERY
- ROW_NUMBER
- LAG

Important:
- Difficulty still maps to core SQL concepts and reasoning depth
- The `concepts` field is for learner guidance, filtering, and analytics
- Do not use the `concepts` field as the source of truth for concept counting

---

# DIFFICULTY TIERS

---

# 🟢 EASY (1001–1999)

## 1. Question Volume
- Target: **30–40 questions**
- Minimum viable: 20
- Rationale:
  - Covers all fundamentals
  - Allows repetition with variation
  - Avoids overfitting to patterns

---

## 2. SQL Topic Coverage
### Composition Rules (STRICT)

- Limit to 1–2 core concepts only
- Concepts must be directly related and commonly used together

Allowed patterns:
- JOIN + aggregation
- JOIN + filtering
- aggregation + HAVING

Restricted:
- JOIN + subquery + CASE together
- Multiple independent logic layers

Subqueries:
- Must be simple and focused
- Should not introduce a second independent reasoning layer

CASE WHEN:
- Allowed only as a helper, not the main complexity driver

MEDIUM should feel like:
→ combining building blocks, not solving multi-layer analytical problems

### Filtering & Selection
- SELECT specific columns (no SELECT *)
- WHERE with:
  - AND / OR
  - IN
  - BETWEEN
  - LIKE

### Sorting
- ORDER BY (ASC/DESC)

### Aggregation (Basic)
- COUNT, SUM, AVG, MIN, MAX
- Single-column GROUP BY

### Deduplication
- DISTINCT

### Joins (Intro)
- INNER JOIN (basic PK–FK)

### Null Handling
- IS NULL / IS NOT NULL

---

## 3. Table Complexity
- Tables per question: **1–2**
- Relationships:
  - One-to-many only
- Dataset:
  - Small (100–1K rows)
  - Minimal NULLs
  - Clean data

---

## 4. Learning Objectives

User should be able to:
- Write correct SELECT queries
- Filter data correctly
- Use GROUP BY properly
- Understand basic joins

### Pass vs Fail

**Pass:**
- Correct filters
- Proper grouping
- Clean result shape

**Fail:**
- Missing WHERE
- Missing GROUP BY
- Duplicate rows from bad joins

---

## 5. Failure Patterns & Feedback

| Pattern | Signal | Feedback |
|--------|--------|----------|
| Missing WHERE | Too many rows | "Check filtering conditions" |
| Missing GROUP BY | SQL error | "Add GROUP BY for non-aggregates" |
| SELECT * usage | Unnecessary columns | "Select only required columns" |
| NULL misuse | Missing rows | "Use IS NULL instead of = NULL" |

---

## 6. Progression Rules

### Prepares for:
- Multi-table joins
- Aggregation logic

### DO NOT INCLUDE:
- Subqueries
- Window functions
- CTEs
- HAVING (keep in medium)

---

# 🟡 MEDIUM (2001–2999)

## 1. Question Volume
- Target: **40–50 questions**
- Rationale:
  - Core interview difficulty
  - Covers majority of real interview patterns

---

## 2. SQL Topic Coverage
### Composition Rules (STRICT)

- Limit to 1–2 core concepts only

Complexity must come from:
- Multi-step reasoning (CTEs, transformations)
- Sequencing logic
- Partitioning and ordering

Allowed:
- Multiple CTEs
- Repeated use of the same concept (e.g., multiple window functions)

NOT allowed:
- Combining unrelated core concepts beyond 2
- Artificial complexity via nesting or mixing paradigms

Examples of BAD HARD design:
- window + subquery + CASE + aggregation without cohesion

HARD should feel like:
→ deep thinking within a concept, not many concepts at once

### Joins
- INNER JOIN
- LEFT JOIN
- Multi-table joins (2–4 tables)

### Aggregation (Advanced)
- GROUP BY (multi-column)
- HAVING

### Conditional Logic
- CASE WHEN

### Subqueries
- IN / EXISTS
- Scalar subqueries

### Filtering Enhancements
- Combined conditions
- Date filters

---

## 3. Table Complexity
- Tables per question: **2–4**
- Relationships:
  - One-to-many
  - Many-to-many (via bridge tables)

- Dataset:
  - Medium (1K–50K rows)
  - Realistic NULLs
  - Missing relationships

---

## 4. Learning Objectives

User should be able to:
- Join multiple tables correctly
- Use HAVING vs WHERE correctly
- Apply subqueries appropriately
- Handle NULLs in joins

### Pass vs Fail

**Pass:**
- Correct join type
- Correct aggregation filters
- Logical breakdown of problem

**Fail:**
- Wrong join (losing rows)
- HAVING misuse
- Overcomplicated subqueries

---

## 5. Failure Patterns & Feedback

| Pattern | Signal | Feedback |
|--------|--------|----------|
| Wrong join type | Missing rows | "Check INNER vs LEFT JOIN" |
| HAVING misuse | SQL error | "Use HAVING for aggregates" |
| Duplicate rows | Inflated counts | "Check join conditions" |
| Overuse of subqueries | Complex query | "Simplify using joins" |

---

## 6. Progression Rules

### Prepares for:
- Analytical SQL
- Window functions

### DO NOT INCLUDE:
- Window functions
- Ranking problems
- Advanced analytics

---

# 🔴 HARD (3001–3999)

## 1. Question Volume
- Target: **25–30 questions**
- Rationale:
  - High complexity
  - Focus on depth, not volume

---

## 2. SQL Topic Coverage

### Hard SQL Mechanisms (At least one required)

- Window functions (ROW_NUMBER, RANK, LAG, LEAD)
- Correlated subqueries (EXISTS / NOT EXISTS)
- Multi-level aggregation
- Conditional aggregation

### Multi-Stage Query Design (MANDATORY)

Every HARD question must:
- Require at least two dependent steps
- Involve transformation across stages (e.g., aggregate → rank, sequence → filter)
- Use CTEs or derived tables where appropriate

### Analytical Patterns

- Sequence-based logic (event ordering, first/last, transitions)
- Contribution analysis (part vs total)
- Ranking after aggregation
- Boundary comparisons (first vs latest, before vs after)

---

## 3. Table Complexity
- Tables per question: **3–5**
- Relationships:
  - Complex joins
  - Self joins

- Dataset:
  - Large (10K+ rows)
  - Many NULLs
  - Edge cases

---

## 4. Learning Objectives

User should be able to:
- Break problems into steps
- Use window functions correctly
- Handle ranking and partitions
- Write clean multi-step queries

### Pass vs Fail

**Pass:**
- Correct partitioning
- Correct ordering
- Logical decomposition

**Fail:**
- Missing ORDER BY in window
- Wrong partition
- Incorrect ranking logic

---

## 5. Failure Patterns & Feedback

| Pattern | Signal | Feedback |
|--------|--------|----------|
| Missing ORDER BY (window) | Wrong ranking | "Add ORDER BY in window" |
| Wrong PARTITION BY | Mixed groups | "Partition correctly" |
| GROUP BY misuse | Wrong logic | "Use window functions instead" |
| LIMIT misuse | Partial results | "Use ROW_NUMBER instead of LIMIT" |

---

## 6. Progression Rules

### Final Level:
- Represents real interview difficulty

### DO NOT INCLUDE:
- DB-specific syntax
- Performance tuning
- DDL (CREATE/ALTER)

---

# DATASET GUIDELINES (CRITICAL)

All questions must use:

### Core Tables (Reusable)
- users
- orders
- order_items
- products
- payments
- events
- employees

### Requirements
- Consistent schemas across questions
- Realistic relationships
- Reusable datasets across difficulties

---

# QUESTION DESIGN RULES (STRICT)

Every question MUST:

  Clarification by difficulty:
  - EASY:
    - 1 primary concept preferred
    - Up to 2 concepts allowed ONLY if tightly coupled and beginner-friendly
    - Complexity must remain low (no multi-step reasoning)
  - MEDIUM: at most 2 concepts, directly related
  - HARD:
    - Must involve multi-stage reasoning with dependent steps
    - May include multiple concepts if they are logically cohesive
    - Must have a clear primary learning objective
    - Complexity must come from reasoning and transformation, not arbitrary concept stacking

- Have:
  - Clear problem statement
  - Deterministic output
  - Expected query
  - Solution query
  - Explanation

- Avoid:
  - Ambiguity
  - Multiple interpretations
  - Non-deterministic ordering

---

# EVALUATION STRATEGY

Use **HYBRID evaluation**:

1. Result comparison (primary)
2. Query structure validation (secondary)

---

# SAMPLE QUESTIONS (SEPARATE SYSTEM)

Sample questions:
- Are NOT part of progression
- Have fixed IDs:
  - Easy: 101–103
  - Medium: 201–203
  - Hard: 301–303

They must:
- Be simpler
- Demonstrate platform usage
- Not overlap with challenge questions

---

# QUESTION QUALITY STANDARDS (ENFORCED)

All questions generated under this curriculum MUST adhere to the following quality rules.

## 1. Clarity
- The problem must be unambiguous
- Avoid vague terms like "top", "best" unless clearly defined
- Clearly define:
  - grouping level
  - sorting expectations
  - output columns

## 2. Deterministic Output
- Results must not depend on:
  - implicit ordering
  - database-specific behavior
- If ordering matters, it must be explicitly stated

## 3. Single Responsibility
- Each question must have a clear primary learning objective
- Supporting concepts are allowed if they are necessary and cohesive
- Avoid combining unrelated concepts

## 3.1 Question Tagging Standard
- Question `concepts` metadata should reflect semantic reasoning patterns
- Question `concepts` metadata should not list every SQL clause used in the solution
- Question `concepts` metadata must remain aligned with the question's main reasoning flow

## 4. Real-World Framing
- Questions must simulate realistic business scenarios
- Avoid artificial or academic phrasing

## 5. Schema Alignment
- Only use approved tables:
  - users, orders, order_items, products, payments, events, employees
- Joins must reflect realistic relationships

## 6. Evaluation Compatibility
- Queries must be:
  - executable
  - deterministic
  - comparable via result-based evaluation

## 7. Explanation Quality
- Every question must include:
  - clear reasoning
  - why the solution works
  - common pitfalls

## 8. Anti-Patterns (STRICTLY AVOID)
- SELECT *
- ambiguous grouping
- hidden assumptions
- multiple valid interpretations

---

# FINAL ENFORCEMENT RULE

This document is the contract for all question generation.

A question is valid ONLY IF:
- It satisfies curriculum coverage requirements
AND
- It satisfies all quality standards above

Any violation must result in rejection.