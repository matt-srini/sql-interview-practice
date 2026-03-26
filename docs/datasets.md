# Datasets

> **Navigation:** [Docs index](./README.md) · [Project blueprint](./project-blueprint.md)

All datasets live in `backend/datasets/`. They are committed CSV files loaded into a single in-memory DuckDB engine at startup. The generator and metadata are the authoritative source of truth.

- **Generator:** `backend/scripts/generate_v1_datasets.py`
- **Metadata:** `backend/datasets/dataset_metadata_v1.json`
- **Current snapshot:** version v1 · seed 20260318 · scale small

---

## Tables

### users
Models the user/account dimension for the platform's business data.

| Column | Notes |
|---|---|
| user_id | |
| name | |
| email | nullable |
| signup_date | |
| country | |
| acquisition_channel | |
| plan_tier | |
| is_active | |

Row count: 600 · Range: 600–1000

Use cases: signup analysis, country/channel segmentation, activity filtering, anti-join exercises (users with no orders, users with no sessions).

---

### categories
Models the product category taxonomy.

| Column | Notes |
|---|---|
| category_id | |
| category_name | |
| parent_category | nullable |

Row count: 16 · Range: 16–24

Includes intentionally unsold categories for anti-join and coverage-gap questions.

---

### products
Models the product catalog.

| Column | Notes |
|---|---|
| product_id | |
| product_name | |
| category_id | FK → categories |
| brand | |
| price | |
| launch_date | nullable |
| is_active | |

Row count: 260 · Range: 260–450

Supports catalog analytics, category joins, active/inactive filtering, null launch-date handling.

---

### orders
Models order headers.

| Column | Notes |
|---|---|
| order_id | |
| user_id | FK → users |
| order_date | |
| status | |
| gross_amount | |
| discount_amount | |
| net_amount | |
| payment_status | |

Row count: 4200 · Range: 4200–7000

Supports order-volume, discount, net-revenue, and lifecycle-status analysis. The legacy `amount` column is no longer used.

---

### order_items
Models line items within orders.

| Column | Notes |
|---|---|
| order_item_id | |
| order_id | FK → orders |
| product_id | FK → products |
| quantity | |
| unit_price | |
| line_amount | |

Row count: 12665 · Range: 12000–21000

Supports basket analysis, product revenue, item-level joins, order-detail aggregation.

---

### payments
Models payment events attached to orders.

| Column | Notes |
|---|---|
| payment_id | |
| order_id | FK → orders |
| payment_date | |
| payment_method | |
| amount | |
| status | paid / failed / refunded / chargeback |

Row count: 4737 · Range: 4700–7900

Includes deliberate amount mismatches for reconciliation-style questions.

---

### sessions
Models user web sessions.

| Column | Notes |
|---|---|
| session_id | |
| user_id | FK → users |
| session_start | |
| device_type | |
| traffic_source | |
| country | |

Row count: 9000 · Range: 9000–15000

Supports traffic-source analysis, device segmentation, user activity and funnel questions.

---

### events
Models event streams within sessions.

| Column | Notes |
|---|---|
| event_id | |
| session_id | FK → sessions |
| user_id | FK → users |
| event_time | |
| event_name | view_product / add_to_cart / start_checkout / purchase |
| product_id | nullable on some purchase events |

Row count: 44964 · Range: 45000–75000

Supports funnel analysis. `product_id` nulls on purchase events are intentional for null-handling questions.

---

### support_tickets
Models customer support cases.

| Column | Notes |
|---|---|
| ticket_id | |
| user_id | FK → users |
| created_at | |
| issue_type | |
| priority | |
| status | |
| resolution_hours | nullable for unresolved tickets |

Row count: 1300 · Range: 1300–2400

Supports SLA timing, unresolved ticket analysis, issue mix, priority breakdowns.

---

### departments
Models the HR department dimension.

| Column | Notes |
|---|---|
| department_id | |
| department_name | |
| region | |

Row count: 10 · Range: 10–14

Includes deliberate empty departments (no employees) for anti-join and headcount-gap questions.

---

### employees
Models employee records.

| Column | Notes |
|---|---|
| employee_id | |
| employee_name | |
| email | |
| salary | intentional ties for ranking exercises |
| department_id | FK → departments |
| hire_date | |
| country | |

Row count: 180 · Range: 180–300

Supports ranking, compensation analysis, department aggregation, hire-date analysis, window functions.

---

## Intentional edge cases

The generator deliberately produces these conditions to support interview-style questions:

- Users with no sessions
- Users with sessions but no orders
- Categories with no sales
- Departments with no employees
- Null emails (users)
- Null product launch dates
- Null `resolution_hours` for unresolved tickets
- Salary ties in employees
- Mixed payment statuses
- Small payment amount mismatches for reconciliation questions

---

## Scale profiles

The generator supports two profiles:

| Profile | Description |
|---|---|
| `small` | Current committed snapshot |
| `medium` | Roughly 1.5–2× row counts |

To regenerate: `python backend/scripts/generate_v1_datasets.py`
