# V1 Data Dictionary

This document defines the v1 dataset contract for challenge question expansion.

## Design Principles

- One coherent domain: product-commerce plus user activity and support.
- Timestamped facts/events are first-class.
- No dedicated history/snapshot tables in v1.
- Monthly/weekly snapshots should be derived in SQL queries.

## Tables

### users
- Grain: one row per user.
- Primary key: user_id.
- Columns:
  - user_id (bigint, required)
  - name (string, required)
  - email (string, nullable)
  - signup_date (date, required)
  - country (string, required)
  - acquisition_channel (string, required)
  - plan_tier (string, required)
  - is_active (boolean, required)

### categories
- Grain: one row per category.
- Primary key: category_id.
- Columns:
  - category_id (bigint, required)
  - category_name (string, required)
  - parent_category (string, nullable)

### products
- Grain: one row per product.
- Primary key: product_id.
- Foreign key: category_id -> categories.category_id.
- Columns:
  - product_id (bigint, required)
  - product_name (string, required)
  - category_id (bigint, required)
  - brand (string, required)
  - price (decimal, required)
  - launch_date (date, nullable)
  - is_active (boolean, required)

### orders
- Grain: one row per order.
- Primary key: order_id.
- Foreign key: user_id -> users.user_id.
- Columns:
  - order_id (bigint, required)
  - user_id (bigint, required)
  - order_date (timestamp, required)
  - status (string, required)
  - gross_amount (decimal, required)
  - discount_amount (decimal, required)
  - net_amount (decimal, required)
  - payment_status (string, required)

### order_items
- Grain: one row per order line item.
- Primary key: order_item_id.
- Foreign keys:
  - order_id -> orders.order_id
  - product_id -> products.product_id
- Columns:
  - order_item_id (bigint, required)
  - order_id (bigint, required)
  - product_id (bigint, required)
  - quantity (int, required)
  - unit_price (decimal, required)
  - line_amount (decimal, required)

### payments
- Grain: one row per payment event.
- Primary key: payment_id.
- Foreign key: order_id -> orders.order_id.
- Columns:
  - payment_id (bigint, required)
  - order_id (bigint, required)
  - payment_date (timestamp, required)
  - payment_method (string, required)
  - amount (decimal, required)
  - status (string, required)

### sessions
- Grain: one row per session.
- Primary key: session_id.
- Foreign key: user_id -> users.user_id.
- Columns:
  - session_id (bigint, required)
  - user_id (bigint, required)
  - session_start (timestamp, required)
  - device_type (string, required)
  - traffic_source (string, required)
  - country (string, required)

### events
- Grain: one row per event.
- Primary key: event_id.
- Foreign keys:
  - session_id -> sessions.session_id
  - user_id -> users.user_id
  - product_id -> products.product_id (nullable)
- Columns:
  - event_id (bigint, required)
  - session_id (bigint, required)
  - user_id (bigint, required)
  - event_time (timestamp, required)
  - event_name (string, required)
  - product_id (bigint, nullable)

### support_tickets
- Grain: one row per support ticket.
- Primary key: ticket_id.
- Foreign key: user_id -> users.user_id.
- Columns:
  - ticket_id (bigint, required)
  - user_id (bigint, required)
  - created_at (timestamp, required)
  - issue_type (string, required)
  - priority (string, required)
  - status (string, required)
  - resolution_hours (decimal, nullable)

### departments
- Grain: one row per department.
- Primary key: department_id.
- Columns:
  - department_id (bigint, required)
  - department_name (string, required)
  - region (string, required)

### employees
- Grain: one row per employee.
- Primary key: employee_id.
- Foreign key: department_id -> departments.department_id.
- Columns:
  - employee_id (bigint, required)
  - employee_name (string, required)
  - email (string, required)
  - salary (decimal, required)
  - department_id (bigint, required)
  - hire_date (date, required)
  - country (string, required)

## Deterministic Generation

Use the generator script:

```bash
cd backend
python scripts/generate_v1_datasets.py --seed 20260318 --scale small
```

Defaults:
- Output directory: `backend/datasets_generated`
- Metadata file: `dataset_metadata_v1.json`

To overwrite active datasets intentionally:

```bash
cd backend
python scripts/generate_v1_datasets.py --output-dir datasets --seed 20260318 --scale small
```
