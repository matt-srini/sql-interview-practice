from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScaleProfile:
    users: int
    categories: int
    products: int
    orders: int
    sessions: int
    tickets: int
    departments: int
    employees: int


PROFILES: dict[str, ScaleProfile] = {
    "small": ScaleProfile(
        users=600,
        categories=16,
        products=260,
        orders=4200,
        sessions=9000,
        tickets=1300,
        departments=10,
        employees=180,
    ),
    "medium": ScaleProfile(
        users=1000,
        categories=24,
        products=450,
        orders=7000,
        sessions=15000,
        tickets=2400,
        departments=14,
        employees=300,
    ),
}

COUNTRIES = ["US", "CA", "UK", "DE", "FR", "IN", "BR", "AU", "SG", "NL"]
ACQUISITION_CHANNELS = ["organic", "paid_search", "paid_social", "referral", "direct", "partner"]
PLAN_TIERS = ["free", "basic", "pro", "enterprise"]
ORDER_STATUSES = ["completed", "cancelled"]
PAYMENT_STATUS = ["paid", "failed", "refunded", "pending"]
PAYMENT_METHODS = ["card", "paypal", "bank_transfer", "wallet"]
DEVICE_TYPES = ["mobile", "desktop", "tablet"]
TRAFFIC_SOURCES = ["organic", "paid_search", "paid_social", "referral", "direct", "email"]
EVENT_TYPES = ["view_product", "add_to_cart", "start_checkout", "purchase"]
TICKET_ISSUES = ["billing", "shipping", "technical", "account", "product"]
TICKET_PRIORITY = ["low", "medium", "high", "urgent"]
TICKET_STATUS = ["open", "in_progress", "resolved"]


def _weighted_choice(rng: random.Random, items: list[str], weights: list[float]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def _random_ts(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(span, 1)))


def _choice_except(rng: random.Random, values: list[int], excluded: set[int]) -> int:
    pool = [v for v in values if v not in excluded]
    return rng.choice(pool)


def _to_date(d: datetime) -> str:
    return d.date().isoformat()


def _to_ts(d: datetime) -> str:
    return d.replace(microsecond=0).isoformat(sep=" ")


def _round_money(x: float) -> float:
    return round(x + 1e-9, 2)


def build_dataset(seed: int, profile: ScaleProfile) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)

    start_dt = datetime(2023, 1, 1, 0, 0, 0)
    end_dt = datetime(2025, 12, 31, 23, 59, 59)

    categories: list[dict[str, Any]] = []
    for i in range(1, profile.categories + 1):
        categories.append(
            {
                "category_id": i,
                "category_name": f"Category {i}",
                "parent_category": None if i % 5 else f"Category {max(1, i - 1)}",
            }
        )

    # Keep a controlled subset of categories intentionally unsold for anti-join questions.
    unsold_categories = set(
        rng.sample(
            list(range(1, profile.categories + 1)),
            k=max(1, int(math.ceil(0.10 * profile.categories))),
        )
    )

    products: list[dict[str, Any]] = []
    for i in range(1, profile.products + 1):
        launch = _random_ts(rng, start_dt - timedelta(days=365), end_dt)
        products.append(
            {
                "product_id": i,
                "product_name": f"Product {i}",
                "category_id": rng.randint(1, profile.categories),
                "brand": f"Brand {1 + ((i - 1) % 30)}",
                "price": _round_money(rng.uniform(8, 600)),
                "launch_date": None if rng.random() < 0.02 else _to_date(launch),
                "is_active": rng.random() > 0.08,
            }
        )

    sellable_product_ids = [p["product_id"] for p in products if p["category_id"] not in unsold_categories]
    if not sellable_product_ids:
        raise ValueError("Generated catalog has no sellable products; adjust profile/category configuration")

    users: list[dict[str, Any]] = []
    for i in range(1, profile.users + 1):
        signup = _random_ts(rng, start_dt - timedelta(days=180), end_dt - timedelta(days=15))
        country = _weighted_choice(
            rng,
            COUNTRIES,
            [30, 10, 10, 8, 8, 12, 7, 6, 5, 4],
        )
        channel = _weighted_choice(
            rng,
            ACQUISITION_CHANNELS,
            [30, 24, 14, 10, 16, 6],
        )
        tier = _weighted_choice(
            rng,
            PLAN_TIERS,
            [58, 23, 15, 4],
        )
        users.append(
            {
                "user_id": i,
                "name": f"User {i}",
                "email": None if rng.random() < 0.03 else f"user{i}@example.com",
                "signup_date": _to_date(signup),
                "country": country,
                "acquisition_channel": channel,
                "plan_tier": tier,
                "is_active": rng.random() > 0.14,
            }
        )

    departments: list[dict[str, Any]] = []
    regions = ["NA", "EMEA", "APAC", "LATAM"]
    for i in range(1, profile.departments + 1):
        departments.append(
            {
                "department_id": i,
                "department_name": f"Department {i}",
                "region": regions[(i - 1) % len(regions)],
            }
        )

    empty_departments = set(rng.sample(list(range(1, profile.departments + 1)), k=min(2, profile.departments // 4)))

    employees: list[dict[str, Any]] = []
    for i in range(1, profile.employees + 1):
        dept_id = _choice_except(rng, list(range(1, profile.departments + 1)), empty_departments)
        salary_base = rng.uniform(50000, 190000)
        if i % 25 == 0:
            # Deliberate ties for ranking exercises.
            salary_base = 110000.0
        hire = _random_ts(rng, start_dt - timedelta(days=1200), end_dt)
        employees.append(
            {
                "employee_id": i,
                "employee_name": f"Employee {i}",
                "email": f"employee{i}@company.com",
                "salary": _round_money(salary_base),
                "department_id": dept_id,
                "hire_date": _to_date(hire),
                "country": _weighted_choice(rng, COUNTRIES, [32, 10, 10, 9, 8, 10, 7, 6, 5, 3]),
            }
        )

    all_user_ids = list(range(1, profile.users + 1))
    users_no_sessions = set(rng.sample(all_user_ids, k=max(1, int(0.12 * profile.users))))
    session_eligible = [u for u in all_user_ids if u not in users_no_sessions]
    users_sessions_no_orders = set(
        rng.sample(session_eligible, k=max(1, int(0.08 * profile.users)))
    )
    order_eligible = [u for u in session_eligible if u not in users_sessions_no_orders]

    sessions: list[dict[str, Any]] = []
    for i in range(1, profile.sessions + 1):
        user_id = rng.choice(session_eligible)
        user_country = users[user_id - 1]["country"]
        sessions.append(
            {
                "session_id": i,
                "user_id": user_id,
                "session_start": _to_ts(_random_ts(rng, start_dt, end_dt)),
                "device_type": _weighted_choice(rng, DEVICE_TYPES, [62, 30, 8]),
                "traffic_source": _weighted_choice(rng, TRAFFIC_SOURCES, [28, 22, 12, 10, 20, 8]),
                "country": user_country,
            }
        )

    target_order_users = min(len(order_eligible), max(1, int(0.65 * profile.users)))
    order_users = set(rng.sample(order_eligible, k=target_order_users))

    orders: list[dict[str, Any]] = []
    order_items: list[dict[str, Any]] = []

    order_id = 1
    order_item_id = 1

    order_user_weights = [1 + (7 if u <= max(10, profile.users // 20) else 0) for u in sorted(order_users)]
    order_user_list = sorted(order_users)

    for _ in range(profile.orders):
        user_id = rng.choices(order_user_list, weights=order_user_weights, k=1)[0]
        order_date = _random_ts(rng, start_dt, end_dt)
        status = _weighted_choice(rng, ORDER_STATUSES, [86, 14])
        payment_status = _weighted_choice(rng, PAYMENT_STATUS, [78, 8, 10, 4])

        num_lines = rng.randint(1, 5)
        gross = 0.0
        chosen_products = rng.sample(sellable_product_ids, k=min(num_lines, len(sellable_product_ids)))
        for p in chosen_products:
            quantity = rng.randint(1, 4)
            unit_price = products[p - 1]["price"]
            line_amount = _round_money(quantity * unit_price)
            if rng.random() < 0.015:
                line_amount = _round_money(line_amount + rng.choice([-1.0, 1.0]))
            gross += line_amount
            order_items.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": p,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_amount": line_amount,
                }
            )
            order_item_id += 1

        gross = _round_money(gross)
        discount = _round_money(gross * rng.choice([0.0, 0.0, 0.05, 0.1, 0.15]))
        net = _round_money(max(gross - discount, 0.0))

        orders.append(
            {
                "order_id": order_id,
                "user_id": user_id,
                "order_date": _to_ts(order_date),
                "status": status,
                "gross_amount": gross,
                "discount_amount": discount,
                "net_amount": net,
                "payment_status": payment_status,
            }
        )
        order_id += 1

    payments: list[dict[str, Any]] = []
    payment_id = 1
    mismatch_order_ids = set(rng.sample([o["order_id"] for o in orders], k=max(1, int(0.02 * len(orders)))))

    for o in orders:
        events_for_order = 1 if rng.random() < 0.88 else 2
        paid_total = 0.0
        for n in range(events_for_order):
            pstatus = _weighted_choice(rng, ["paid", "failed", "refunded", "chargeback"], [78, 10, 10, 2])
            if events_for_order == 2 and n == 1 and pstatus == "failed":
                pstatus = "paid"

            if pstatus == "paid":
                amount = _round_money(o["net_amount"] / events_for_order)
            elif pstatus in {"refunded", "chargeback"}:
                amount = _round_money(min(o["net_amount"], rng.uniform(5, max(6, o["net_amount"]))))
            else:
                amount = _round_money(max(1.0, rng.uniform(1, max(2, o["net_amount"] * 0.5))))

            if o["order_id"] in mismatch_order_ids and pstatus == "paid":
                amount = _round_money(amount + rng.choice([-2.0, 2.0]))

            if pstatus == "paid":
                paid_total += amount

            payments.append(
                {
                    "payment_id": payment_id,
                    "order_id": o["order_id"],
                    "payment_date": _to_ts(_random_ts(rng, start_dt, end_dt)),
                    "payment_method": _weighted_choice(rng, PAYMENT_METHODS, [62, 18, 12, 8]),
                    "amount": amount,
                    "status": pstatus,
                }
            )
            payment_id += 1

    events: list[dict[str, Any]] = []
    event_id = 1
    session_rows = {s["session_id"]: s for s in sessions}
    for s in sessions:
        base_time = datetime.fromisoformat(s["session_start"])
        event_count = rng.randint(2, 8)
        include_purchase = rng.random() < 0.22
        flow = ["view_product"]
        if rng.random() < 0.65:
            flow.append("add_to_cart")
        if rng.random() < 0.45:
            flow.append("start_checkout")
        if include_purchase:
            flow.append("purchase")

        while len(flow) < event_count:
            flow.append(_weighted_choice(rng, EVENT_TYPES, [60, 20, 12, 8]))

        for idx, event_name in enumerate(flow[:event_count]):
            ts = base_time + timedelta(minutes=idx * rng.randint(1, 9))
            product_id = rng.randint(1, profile.products) if event_name != "purchase" else rng.choice([None, rng.randint(1, profile.products)])
            events.append(
                {
                    "event_id": event_id,
                    "session_id": s["session_id"],
                    "user_id": s["user_id"],
                    "event_time": _to_ts(ts),
                    "event_name": event_name,
                    "product_id": product_id,
                }
            )
            event_id += 1

    ticket_user_pool = [u for u in all_user_ids if rng.random() < 0.55]
    if not ticket_user_pool:
        ticket_user_pool = all_user_ids

    support_tickets: list[dict[str, Any]] = []
    for i in range(1, profile.tickets + 1):
        status = _weighted_choice(rng, TICKET_STATUS, [18, 22, 60])
        resolution_hours: float | None
        if status == "resolved":
            resolution_hours = _round_money(rng.uniform(1.0, 120.0))
        else:
            resolution_hours = None

        support_tickets.append(
            {
                "ticket_id": i,
                "user_id": rng.choice(ticket_user_pool),
                "created_at": _to_ts(_random_ts(rng, start_dt, end_dt)),
                "issue_type": _weighted_choice(rng, TICKET_ISSUES, [24, 17, 29, 18, 12]),
                "priority": _weighted_choice(rng, TICKET_PRIORITY, [40, 34, 20, 6]),
                "status": status,
                "resolution_hours": resolution_hours,
            }
        )

    return {
        "users": users,
        "categories": categories,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "sessions": sessions,
        "events": events,
        "support_tickets": support_tickets,
        "departments": departments,
        "employees": employees,
    }


def _assert_fk(rows: list[dict[str, Any]], key: str, valid: set[int], table: str) -> None:
    bad = [r[key] for r in rows if r[key] not in valid]
    if bad:
        raise ValueError(f"FK validation failed for {table}.{key}: {len(bad)} invalid values")


def validate_dataset(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    users = data["users"]
    orders = data["orders"]
    order_items = data["order_items"]
    payments = data["payments"]
    sessions = data["sessions"]
    events = data["events"]
    products = data["products"]
    categories = data["categories"]
    support_tickets = data["support_tickets"]
    departments = data["departments"]
    employees = data["employees"]

    user_ids = {r["user_id"] for r in users}
    order_ids = {r["order_id"] for r in orders}
    product_ids = {r["product_id"] for r in products}
    category_ids = {r["category_id"] for r in categories}
    session_ids = {r["session_id"] for r in sessions}
    dept_ids = {r["department_id"] for r in departments}

    _assert_fk(orders, "user_id", user_ids, "orders")
    _assert_fk(order_items, "order_id", order_ids, "order_items")
    _assert_fk(order_items, "product_id", product_ids, "order_items")
    _assert_fk(products, "category_id", category_ids, "products")
    _assert_fk(payments, "order_id", order_ids, "payments")
    _assert_fk(sessions, "user_id", user_ids, "sessions")
    _assert_fk(events, "session_id", session_ids, "events")
    _assert_fk(events, "user_id", user_ids, "events")
    _assert_fk([r for r in events if r["product_id"] is not None], "product_id", product_ids, "events")
    _assert_fk(support_tickets, "user_id", user_ids, "support_tickets")
    _assert_fk(employees, "department_id", dept_ids, "employees")

    users_with_sessions = {s["user_id"] for s in sessions}
    users_with_orders = {o["user_id"] for o in orders}
    users_without_sessions = len(user_ids - users_with_sessions)
    users_sessions_no_orders = len((user_ids & users_with_sessions) - users_with_orders)

    category_with_sales = {products[oi["product_id"] - 1]["category_id"] for oi in order_items}
    categories_without_sales = len(category_ids - category_with_sales)

    dept_with_employees = {e["department_id"] for e in employees}
    empty_dept = len(dept_ids - dept_with_employees)

    email_null_rate = sum(1 for u in users if u["email"] is None) / max(1, len(users))
    launch_null_rate = sum(1 for p in products if p["launch_date"] is None) / max(1, len(products))

    ticket_null_resolution = sum(1 for t in support_tickets if t["resolution_hours"] is None)

    # Sanity thresholds from v1 plan.
    if not (0.02 <= email_null_rate <= 0.06):
        raise ValueError(f"users.email null rate out of band: {email_null_rate:.3f}")
    if not (0.01 <= launch_null_rate <= 0.04):
        raise ValueError(f"products.launch_date null rate out of band: {launch_null_rate:.3f}")
    if users_without_sessions < 0.08 * len(user_ids):
        raise ValueError("Insufficient users with no sessions for anti-join coverage")
    if users_sessions_no_orders < 0.05 * len(user_ids):
        raise ValueError("Insufficient users with sessions but no orders for anti-join coverage")
    if categories_without_sales < 0.05 * len(category_ids):
        raise ValueError("Insufficient categories with no sales for anti-join coverage")
    if empty_dept < 1:
        raise ValueError("Need at least one department with zero employees")
    if ticket_null_resolution < 0.2 * len(support_tickets):
        raise ValueError("Insufficient unresolved ticket null resolution edge cases")

    return {
        "row_counts": {k: len(v) for k, v in data.items()},
        "quality_metrics": {
            "users_email_null_rate": round(email_null_rate, 4),
            "products_launch_date_null_rate": round(launch_null_rate, 4),
            "users_without_sessions": users_without_sessions,
            "users_with_sessions_but_no_orders": users_sessions_no_orders,
            "categories_without_sales": categories_without_sales,
            "empty_departments": empty_dept,
            "tickets_with_null_resolution_hours": ticket_null_resolution,
            "ticket_status_counts": Counter(t["status"] for t in support_tickets),
            "order_status_counts": Counter(o["status"] for o in orders),
            "payment_status_counts": Counter(p["status"] for p in payments),
        },
    }


def write_csv(table_name: str, rows: list[dict[str, Any]], output_dir: Path) -> None:
    if not rows:
        raise ValueError(f"No rows generated for {table_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{table_name}.csv"
    fieldnames = list(rows[0].keys())

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic v1 datasets for SQL interview content")
    parser.add_argument("--seed", type=int, default=20260318, help="Deterministic RNG seed")
    parser.add_argument(
        "--scale",
        choices=sorted(PROFILES.keys()),
        default="small",
        help="Dataset scale profile",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "datasets_generated",
        help="Output directory for generated CSV files",
    )
    parser.add_argument(
        "--metadata-file",
        type=str,
        default="dataset_metadata_v1.json",
        help="Metadata JSON file name",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = PROFILES[args.scale]

    data = build_dataset(seed=args.seed, profile=profile)
    validation = validate_dataset(data)

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for table_name, rows in data.items():
        write_csv(table_name, rows, out_dir)

    metadata = {
        "dataset_version": "v1",
        "seed": args.seed,
        "scale": args.scale,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "row_counts": validation["row_counts"],
        "quality_metrics": {
            k: dict(v) if isinstance(v, Counter) else v
            for k, v in validation["quality_metrics"].items()
        },
    }

    metadata_path = out_dir / args.metadata_file
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"[datasets] Generated v1 dataset in: {out_dir}")
    print(f"[datasets] Metadata: {metadata_path}")
    print("[datasets] Row counts:")
    for table_name, count in metadata["row_counts"].items():
        print(f"  - {table_name}: {count}")


if __name__ == "__main__":
    main()
