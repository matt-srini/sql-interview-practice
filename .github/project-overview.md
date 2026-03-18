

# SQL Interview Practice Platform - Project Overview


## Purpose

The SQL Interview Practice Platform helps people prepare for SQL interviews through hands-on practice. Users solve realistic SQL questions, run queries, and get instant feedback in a focused learning environment.

Recent updates:
- Challenge question bank is now JSON-backed (currently 14 easy, 11 medium, 8 hard; expanding toward 30+ per difficulty).
- Deterministic dataset generator and formal data dictionary enable scalable, high-quality content and edge-case coverage.
- Content and datasets are externalized for easier review, QA, and future expansion.


## What The Product Does

The platform combines a question bank, SQL editor, schema view, and result feedback into one workflow:

1. Pick a question by difficulty (Easy, Medium, Hard) from a growing JSON-backed catalog (currently 14 easy, 11 medium, 8 hard).
2. Read the prompt and inspect the table schema (all datasets are generated and documented for consistency and edge-case coverage).
3. Write and run SQL in a browser-based editor.
4. Submit your answer for correctness, with automatic evaluation against expected results.
5. Review the official solution and explanation.
6. Move to the next unlocked question or continue practicing.


## Core Features

- JSON-backed challenge question bank (expanding toward 30+ per difficulty)
- Deterministic dataset generator and formal data dictionary for all practice tables
- Practice mode with progression and unlocks
- Separate sample mode for quick drills (Python-backed, 3 per difficulty)
- In-browser SQL editor and tabular result view
- Automatic answer checking against expected results
- Official solution and explanation after submission
- Per-user progress tracking (session/cookie based)


## Current Scope

- Built for interview prep in SQL-heavy roles (Data Analyst, Data Engineer, Backend)
- Focused on practical learning and fast feedback rather than broad LMS features
- Designed to be lightweight and easy to run locally or deploy as a small web app
- Challenge content and datasets are now externalized for easier scaling and content QA

## Who It Is For

- Interview candidates preparing SQL rounds.
- Students strengthening SQL fundamentals.
- Developers who want structured SQL practice.


## Project Goal

Deliver a simple, reliable SQL practice experience where users can improve by solving interview-style problems and learning from immediate, clear feedback.

The platform is now architected for scalable content growth, robust data quality, and easier content management.