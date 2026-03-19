

# Copilot Instructions — SQL Interview Practice Platform

## Purpose
These instructions define how GitHub Copilot (or any coding agent) must behave when making changes to this repository.

The goal is to ensure:
- consistency
- safety
- minimal regressions
- production-quality changes
- traceable commits

---

# 1. Core Principles (MANDATORY)

## 1.1 Make Minimal, Surgical Changes
- Only change what is explicitly required.
- Do NOT refactor unrelated code.
- Do NOT introduce new abstractions unless explicitly requested.

---

## 1.2 Preserve Architecture
This project has a locked architecture. Do NOT modify:

- FastAPI routing structure
- DuckDB execution model (isolated per query)
- JSON-backed challenge question system
- Sample vs Challenge separation
- API contracts and response shapes

---

## 1.3 Do Not Introduce New Patterns Without Approval
Avoid:
- new frameworks
- new design patterns
- large structural refactors

Unless explicitly asked.

---

# 2. Project-Specific Rules

## 2.1 Question System

### Challenge Questions
- Stored in: backend/content/questions/*.json
- Must follow ID ranges:
  - easy:   1001–1999
  - medium: 2001–2999
  - hard:   3001–3999

### Sample Questions
- Stored in: backend/sample_questions.py
- Must follow ID ranges:
  - easy:   101–103
  - medium: 201–203
  - hard:   301–303

### Strict Separation
- NEVER mix sample and challenge question sources
- NEVER reuse IDs across systems

---

## 2.2 Dataset System

- CSVs live in: backend/datasets/
- Generated via: backend/scripts/generate_v1_datasets.py
- Schema defined in: DATA_DICTIONARY_V1.md

Rules:
- Do NOT create duplicate datasets (e.g., orders_v2.csv)
- Do NOT modify schema without updating generator + data dictionary
- Questions must only reference valid dataset files

---

## 2.3 SQL Execution

- Queries must remain read-only
- Execution must stay:
  - isolated per request
  - scoped to question dataset_files
- Do NOT bypass sql_guard.py

---

## 2.4 API Behavior

- Error responses MUST follow:
{ "error": "...", "request_id": "..." }

- Do NOT leak stack traces
- Always include X-Request-ID header

---

# 3. Logging Rules

- Use structured logging format:
[request_id=<id>] message

- Do NOT log sensitive data
- Include context (question_id, user_id where applicable)

---

# 4. Validation Rules

Whenever modifying questions or datasets:

You MUST ensure:
- ID ranges are respected
- IDs are unique
- dataset_files exist
- schema matches dataset
- no cross-contamination between sample and challenge

Fail fast on violations.

---

# 5. Testing Rules

## 5.1 Always Update Tests When Needed
- If behavior changes → update tests
- If IDs change → update test expectations

---

## 5.2 Always Run Tests (conceptually)
Ensure:
pytest
would pass after changes.

---

## 5.3 Keep Core Docs Updated

Whenever a significant change affects user-facing behavior, architecture, datasets, execution model, deployment flow, project structure, question inventory, or any documented workflow, you MUST review whether these files need updates:
- README.md
- docs/project-overview.md
- docs/project-blueprint.md

If any of those files are affected, you MUST update them in the same task.

Examples that require documentation review:
- backend or frontend architecture changes
- route or API behavior changes
- dataset additions, removals, schema changes, or scale-profile changes
- question-bank count or organization changes
- deployment or environment-variable changes
- major workflow or project-structure changes

Rules:
- Do NOT leave these docs stale after significant relevant changes.
- Keep README.md concise and operator-focused.
- Keep docs/project-overview.md as a short product/state summary.
- Keep docs/project-blueprint.md as the detailed current-state reference.
- If a significant change does not require updates to one or more of these files, explicitly verify that they remain accurate.

---

# 6. Git & Change Management (MANDATORY)

## 6.1 After Every Non-Trivial Change

You MUST provide:

### 1. Final Clear Commit Command

Format:
git commit -m "<type>: <short description>"

Rules:
- This must be a single clear command the user can copy/paste directly.
- Once provided in the response, it must not be altered or paraphrased elsewhere in that same response.
- It must match the short commit title used in the structured commit summary.

---

### 2. Commit Message Summary

Format:
<type>: <short description>

- bullet point summary of changes
- include impacted modules

Rules:
- Keep this structured summary alongside the final clear commit command.
- Do NOT replace this summary with the command; both are required.

Types:
- feat
- fix
- refactor
- docs
- chore

---

### 3. Git Diff Output

Generate a diff of ALL changes:

git diff > gitdiff.log

Rules:
- MUST include all modified files
- MUST EXCLUDE changes to gitdiff.log itself

---

## 6.2 Small Changes Exception

If change is:
- 1–2 lines
- trivial typo

Then commit + diff can be skipped.

---

## 6.3 Do NOT Modify gitdiff.log Manually
- It must always reflect actual git diff
- Never fabricate or partially generate it

---

# 7. Code Quality Expectations

## Backend (FastAPI)
- Keep functions small and focused
- Avoid global state unless necessary
- Use clear error handling
- Prefer explicit over implicit

---

## Frontend (React)
- Do NOT introduce new state management libraries
- Keep components simple and readable
- Preserve existing routing and layout

---

## General
- Use clear variable names
- Avoid clever/complex code
- Optimize for readability

---

# 8. Safety Constraints

DO NOT:
- execute destructive SQL
- expose internal errors to users
- bypass validation layers
- weaken rate limiting or security

---

# 9. When Unsure

If ambiguity exists:
- choose the most minimal safe change
- do NOT assume large refactors
- document assumptions clearly

---

# 10. Output Requirements (Every Prompt)

Unless explicitly told otherwise, every response must include:

1. Summary of changes
2. Files modified
3. Final clear git commit -m command
4. Structured commit message summary
5. Git diff instructions or output

---

# 11. What NOT to Do

- Do NOT re-architect the system
- Do NOT move files unnecessarily
- Do NOT introduce breaking changes
- Do NOT “improve” unrelated areas

---

# Final Goal

Maintain a stable, production-ready SQL learning platform where:

- architecture is consistent
- content is scalable
- changes are traceable
- bugs are minimized
- documentation stays aligned with the current repository state

---

This file is the single source of truth for how automated changes should be made.