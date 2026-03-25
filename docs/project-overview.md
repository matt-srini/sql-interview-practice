# SQL Interview Practice Platform - Project Overview

## Purpose

This project provides a focused SQL interview practice environment where users solve realistic SQL problems, run queries against controlled datasets, and receive immediate correctness feedback.


## What the Product Does

The application combines a question catalog, SQL editor, schema viewer, and result comparison workflow:

1. Enter through either the challenge track or the sample track.
2. Read the prompt and inspect the schema for the current question.
3. Write SQL in the browser-based editor.
4. Run the query against the preloaded in-memory DuckDB execution engine.
5. Submit the answer for evaluation against the expected result (normalized, order-sensitive if needed).
6. Review the official solution and explanation.
7. Progress, plans, and billing state are handled through PostgreSQL-backed identity, entitlement, and Stripe flows.


## Current Scope

Current committed content:
- Challenge questions: 86 total (easy: 30, medium: 30, hard: 26)
- Sample questions: 9 total (3 per difficulty)

Current platform capabilities:
- JSON-backed challenge question catalog (backend/content/questions/)
- Python-backed sample question catalog (backend/sample_questions.py)
- Unified unlock policy combining plan tier and solve history
- Separate sample progression tracking
- Read-only SQL validation and shared in-memory DuckDB execution
- Result normalization and correctness evaluation (case-insensitive columns, float tolerance, null handling, order-sensitive if needed)
- Schema/header validation for question content against committed datasets
- Semantic reasoning tags surfaced as pill badges on question pages
- Progressive hint reveal flow before solution display
- Unified anonymous and registered identity backed by PostgreSQL sessions and users
- Real Stripe checkout and verified webhook handling with audit logging
- Structured request_id logging and standardized API error responses
- Single-service production deployment path where FastAPI serves both UI and API

## Dataset Coverage

The current committed datasets span several business domains:
- users, sessions, and events for behavioral analysis
- categories, products, orders, order_items, and payments for commerce analysis
- support_tickets for operations and service analysis
- departments and employees for HR-style questions

The current committed snapshot includes 11 CSV files in backend/datasets/ and a metadata file at backend/datasets/dataset_metadata_v1.json.

## Who It Is For

- Interview candidates preparing for SQL rounds
- Students strengthening SQL fundamentals
- Developers who want structured, feedback-driven SQL practice

## Project Goal

Maintain a small, reliable SQL practice platform with realistic datasets, safe execution, clear feedback, and documentation that stays aligned with the live repository state.

For the detailed architecture and current-state reference, see docs/project-blueprint.md.
