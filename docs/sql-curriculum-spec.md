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
- Each question must test **1–2 core concepts max**
- Every question must be:
  - Deterministic
  - Evaluatable via result comparison
  - Free of ambiguity

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

### Window Functions
- ROW_NUMBER
- RANK / DENSE_RANK
- LEAD / LAG
- Running totals

### Advanced Query Design
- CTEs
- Multi-step transformations

### Analytical Patterns
- Top-N per group
- Time-based analysis
- Cohort-style logic (basic)

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
- Each question should test **1–2 core concepts max**
- Avoid combining unrelated concepts

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