Plan: Concrete Schema Spec + CSV Generation Strategy
Moving forward with your direction, the plan now commits to high-quality relationships and edge cases while intentionally avoiding unnecessary complexity.

Core Call On Time/History
Use timestamped fact/event tables in v1.
Do not add dedicated history or snapshot tables in v1.
Derive monthly/weekly snapshots in SQL using date bucketing and windows.
This gives enough power for serious hard questions without bloating the model.

v1 Table Scope
users
orders
order_items
products
categories
payments
sessions
events
support_tickets
employees
departments
Relationship Model (clean and interview-friendly)
users 1-to-many orders, sessions, support_tickets
orders 1-to-many order_items, payments
products many-to-1 categories, referenced by order_items and optional events
sessions 1-to-many events
employees many-to-1 departments
Data Quality Requirements
Include realistic nulls:
missing emails
missing product launch dates
unresolved ticket resolution times
Include anti-join situations:
users with no sessions
users with sessions but no orders
categories with no sold products
departments with no employees
Include tie scenarios for ranking.
Include controlled reconciliation mismatches (small percentage only).
Include temporal patterns (seasonality, spikes, inactivity gaps).
Row-Count Targets (moderate, not huge)
users: 500-1200
orders: 3000-8000
order_items: 9000-24000
products: 200-600
categories: 12-30
payments: 3200-9000
sessions: 5000-18000
events: 30000-120000
support_tickets: 800-3000
employees: 120-400
departments: 8-20
Generation Strategy
Deterministic generator with fixed seed.
Generate CSVs into datasets.
Add a simple metadata artifact (seed, generation timestamp, table counts).
Include lightweight integrity checks:
FK checks
null-rate and distribution checks
row-count checks
Question Grouping Integrity
Keep 30 questions per difficulty with balanced concept distribution.
Easy/medium stay portability-first.
Hard can use advanced SQL patterns as long as outputs remain deterministic and explainable.
Relevant files
easy.json
medium.json
hard.json
schemas.json
__init__.py
evaluator.py
sql_guard.py
datasets
test_api.py
test_evaluator.py
I saved this execution-ready planning artifact to /memories/session/plan.md.

Next step I recommend: draft the actual data dictionary file (column definitions + allowed values + business semantics) and the deterministic generation spec so implementation can start cleanly.
