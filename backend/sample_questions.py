from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Optional

import pyspark_questions as pyspark_catalog
import python_data_questions as python_data_catalog
import python_questions as python_catalog

# Inline schemas and helpers (formerly from question_bank.common)
ORDERS_SCHEMA = {
    "orders": ["order_id", "user_id", "order_date", "status", "net_amount"],
}
USERS_SCHEMA = {
    "users": ["user_id", "name", "signup_date", "country"],
}
def merge_schema(*schemas):
    merged = {}
    for schema in schemas:
        for table, cols in schema.items():
            merged[table] = list(cols)
    return merged
def q(*, id, order, title, description, difficulty, schema, dataset_files, expected_query, solution_query, explanation):
    return {
        "id": id,
        "order": order,
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "schema": schema,
        "dataset_files": dataset_files,
        "expected_query": expected_query,
        "solution_query": solution_query,
        "explanation": explanation,
    }


_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def _fail(question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid question in sample_questions.py (id={int(question_id)}): {reason}")


def _table_name_from_dataset_file(dataset_file: str) -> str:
    return Path(dataset_file).stem


def _read_dataset_headers(dataset_file: str) -> set[str]:
    dataset_path = _DATASETS_DIR / dataset_file
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return {str(column) for column in next(reader)}
        except StopIteration as exc:
            raise ValueError(f"Dataset file is empty: {dataset_file}") from exc


def _enforce_sample_id_range(*, qid: int, difficulty: str) -> None:
    if difficulty == "easy":
        lo, hi = 101, 103
    elif difficulty == "medium":
        lo, hi = 201, 203
    elif difficulty == "hard":
        lo, hi = 301, 303
    else:
        _fail(qid, f"Invalid difficulty: {difficulty}")

    if not (lo <= int(qid) <= hi):
        _fail(qid, f"ID out of range for difficulty={difficulty}: expected {lo}–{hi}")


def _validate_sample_questions(questions: list[dict[str, Any]]) -> None:
    seen_ids: set[int] = set()
    by_diff: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}

    required_fields = [
        "id",
        "title",
        "description",
        "difficulty",
        "schema",
        "dataset_files",
        "expected_query",
        "solution_query",
        "explanation",
        "order",
    ]

    for qd in questions:
        qid = int(qd.get("id"))
        if qid in seen_ids:
            _fail(qid, "Duplicate question id")
        seen_ids.add(qid)

        for required in required_fields:
            if required not in qd:
                _fail(qid, f"Missing required field: {required}")

        difficulty = qd.get("difficulty")
        if difficulty not in by_diff:
            _fail(qid, f"Invalid difficulty: {difficulty}")
        _enforce_sample_id_range(qid=qid, difficulty=difficulty)
        by_diff[difficulty].append(qd)

        dataset_files = qd.get("dataset_files")
        if not isinstance(dataset_files, list) or not dataset_files:
            _fail(qid, "dataset_files must be a non-empty list")

        schema = qd.get("schema")
        if not isinstance(schema, dict) or not schema:
            _fail(qid, "schema must be a non-empty dict")

        dataset_files_set = {str(x) for x in dataset_files}
        for dataset_file in dataset_files_set:
            if not (_DATASETS_DIR / dataset_file).exists():
                _fail(qid, f"Dataset file not found: {dataset_file}")

        schema_tables = {str(t) for t in schema.keys()}
        table_headers = {
            _table_name_from_dataset_file(dataset_file): _read_dataset_headers(dataset_file)
            for dataset_file in dataset_files_set
        }

        for table in schema_tables:
            expected_file = f"{table}.csv"
            if expected_file not in dataset_files_set:
                _fail(qid, f"schema includes table '{table}' but dataset_files is missing '{expected_file}'")
            missing_columns = [column for column in schema[table] if str(column) not in table_headers[table]]
            if missing_columns:
                _fail(qid, f"schema columns not found in dataset '{expected_file}': {missing_columns}")

        for dataset_file in dataset_files_set:
            if not dataset_file.endswith(".csv"):
                _fail(qid, f"dataset_files contains non-CSV entry: {dataset_file}")
            table = _table_name_from_dataset_file(dataset_file)
            if table not in schema_tables:
                _fail(qid, f"dataset_files includes '{dataset_file}' but schema is missing table '{table}'")

    for diff in ["easy", "medium", "hard"]:
        if len(by_diff[diff]) != 3:
            _fail(-1, f"Expected exactly 3 sample questions for difficulty='{diff}', found {len(by_diff[diff])}")


SAMPLE_QUESTIONS: list[dict[str, Any]] = [
    q(
        id=101,
        order=1,
        title="Sample Easy: Count Users",
        difficulty="easy",
        description="Return the number of users in users as user_count.",
        schema=merge_schema(USERS_SCHEMA),
        dataset_files=["users.csv"],
        expected_query="SELECT COUNT(*) AS user_count FROM users",
        solution_query="SELECT COUNT(*) AS user_count\nFROM users;",
        explanation="COUNT(*) counts all rows in users.",
    ),
    q(
        id=102,
        order=2,
        title="Sample Easy: Distinct Countries",
        difficulty="easy",
        description="Return the distinct list of countries users are from, sorted alphabetically.",
        schema=merge_schema(USERS_SCHEMA),
        dataset_files=["users.csv"],
        expected_query=(
            "SELECT DISTINCT country "
            "FROM users "
            "ORDER BY country"
        ),
        solution_query=(
            "SELECT DISTINCT country\n"
            "FROM users\n"
            "ORDER BY country;"
        ),
        explanation="DISTINCT removes duplicates; ORDER BY sorts the results.",
    ),
    q(
        id=103,
        order=3,
        title="Sample Easy: Total Completed Order Amount",
        difficulty="easy",
        description="Return the sum of amounts for completed orders as total_completed_amount.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT SUM(net_amount) AS total_completed_amount "
            "FROM orders "
            "WHERE status = 'completed'"
        ),
        solution_query=(
            "SELECT SUM(net_amount) AS total_completed_amount\n"
            "FROM orders\n"
            "WHERE status = 'completed';"
        ),
        explanation="Filter to completed orders, then sum net_amount.",
    ),
    q(
        id=201,
        order=1,
        title="Sample Medium: Users With No Orders",
        difficulty="medium",
        description="Return user_id and name for users who have never placed an order.",
        schema=merge_schema(USERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["users.csv", "orders.csv"],
        expected_query=(
            "SELECT u.user_id, u.name "
            "FROM users u "
            "LEFT JOIN orders o ON o.user_id = u.user_id "
            "WHERE o.order_id IS NULL "
            "ORDER BY u.user_id"
        ),
        solution_query=(
            "SELECT u.user_id, u.name\n"
            "FROM users u\n"
            "LEFT JOIN orders o ON o.user_id = u.user_id\n"
            "WHERE o.order_id IS NULL\n"
            "ORDER BY u.user_id;"
        ),
        explanation="LEFT JOIN keeps all users; users without matching orders have NULL order_id values.",
    ),
    q(
        id=202,
        order=2,
        title="Sample Medium: Revenue By Status",
        difficulty="medium",
        description="Return each order status and total revenue for that status.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT status, SUM(net_amount) AS revenue "
            "FROM orders "
            "GROUP BY status "
            "ORDER BY status"
        ),
        solution_query=(
            "SELECT status, SUM(net_amount) AS revenue\n"
            "FROM orders\n"
            "GROUP BY status\n"
            "ORDER BY status;"
        ),
        explanation="Group by status, then sum net_amount within each status.",
    ),
    q(
        id=203,
        order=3,
        title="Sample Medium: Monthly Revenue",
        difficulty="medium",
        description="Return month and revenue, grouped by month from orders.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT DATE_TRUNC('month', CAST(order_date AS DATE)) AS month, SUM(net_amount) AS revenue "
            "FROM orders "
            "GROUP BY 1 "
            "ORDER BY 1"
        ),
        solution_query=(
            "SELECT DATE_TRUNC('month', CAST(order_date AS DATE)) AS month, SUM(net_amount) AS revenue\n"
            "FROM orders\n"
            "GROUP BY 1\n"
            "ORDER BY 1;"
        ),
        explanation="Bucket by month using DATE_TRUNC, then aggregate net_amount per bucket.",
    ),
    q(
        id=301,
        order=1,
        title="Sample Hard: Top 2 Orders Per User",
        difficulty="hard",
        description="Return each user's top 2 orders by amount using a window rank.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT user_id, order_id, amount, rnk "
            "FROM ("
            "  SELECT order_id, user_id, net_amount AS amount, DENSE_RANK() OVER (PARTITION BY user_id ORDER BY net_amount DESC) AS rnk "
            "  FROM orders"
            ") t "
            "WHERE rnk <= 2 "
            "ORDER BY user_id, rnk, order_id"
        ),
        solution_query=(
            "SELECT user_id, order_id, amount, rnk\n"
            "FROM (\n"
            "  SELECT order_id, user_id, net_amount AS amount,\n"
            "         DENSE_RANK() OVER (PARTITION BY user_id ORDER BY net_amount DESC) AS rnk\n"
            "  FROM orders\n"
            ") t\n"
            "WHERE rnk <= 2\n"
            "ORDER BY user_id, rnk, order_id;"
        ),
        explanation="Rank orders per user by net_amount, then keep the top two ranks.",
    ),
    q(
        id=302,
        order=2,
        title="Sample Hard: First Order Date Per User",
        difficulty="hard",
        description="Return each user_id and their first order date as first_order_date.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT user_id, MIN(CAST(order_date AS DATE)) AS first_order_date "
            "FROM orders "
            "GROUP BY user_id "
            "ORDER BY user_id"
        ),
        solution_query=(
            "SELECT user_id, MIN(CAST(order_date AS DATE)) AS first_order_date\n"
            "FROM orders\n"
            "GROUP BY user_id\n"
            "ORDER BY user_id;"
        ),
        explanation="Use MIN(order_date) per user_id to find the first order date.",
    ),
    q(
        id=303,
        order=3,
        title="Sample Hard: Completed Revenue By Country",
        difficulty="hard",
        description="For each country, return total completed order revenue as completed_revenue.",
        schema=merge_schema(USERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["users.csv", "orders.csv"],
        expected_query=(
            "SELECT u.country, SUM(o.net_amount) AS completed_revenue "
            "FROM users u "
            "JOIN orders o ON o.user_id = u.user_id "
            "WHERE o.status = 'completed' "
            "GROUP BY u.country "
            "ORDER BY u.country"
        ),
        solution_query=(
            "SELECT u.country, SUM(o.net_amount) AS completed_revenue\n"
            "FROM users u\n"
            "JOIN orders o ON o.user_id = u.user_id\n"
            "WHERE o.status = 'completed'\n"
            "GROUP BY u.country\n"
            "ORDER BY u.country;"
        ),
        explanation="Join users to orders, filter to completed, then sum net_amount by country.",
    ),
]


_validate_sample_questions(SAMPLE_QUESTIONS)


SAMPLE_INDEX: dict[int, dict[str, Any]] = {int(q["id"]): q for q in SAMPLE_QUESTIONS}

_TOPIC_ALIASES: dict[str, str] = {
    "sql": "sql",
    "python": "python",
    "python_data": "python_data",
    "python-data": "python_data",
    "pyspark": "pyspark",
}

_TOPIC_CATALOGS = {
    "python": python_catalog,
    "python_data": python_data_catalog,
    "pyspark": pyspark_catalog,
}
_DIFFICULTY_ORDER = ("easy", "medium", "hard")
_SAMPLE_POOL_SIZE = 3


def normalize_sample_topic(topic: str) -> str:
    normalized = _TOPIC_ALIASES.get(str(topic).strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported sample topic: {topic}")
    return normalized


def get_sample_question(question_id: int) -> Optional[dict[str, Any]]:
    return SAMPLE_INDEX.get(int(question_id))


def get_sample_question_for_topic(question_id: int, topic: str) -> Optional[dict[str, Any]]:
    normalized_topic = normalize_sample_topic(topic)
    if normalized_topic == "sql":
        return get_sample_question(question_id)

    target_id = int(question_id)
    for difficulty in _DIFFICULTY_ORDER:
        pool, _ = get_topic_sample_pool(topic=normalized_topic, difficulty=difficulty)
        for question in pool:
            if int(question["id"]) == target_id:
                return question
    return None


def get_sample_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in SAMPLE_QUESTIONS:
        grouped[q["difficulty"]].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x["order"]))
    return grouped


def get_topic_sample_pool(
    *,
    topic: str,
    difficulty: str,
) -> tuple[list[dict[str, Any]], str]:
    normalized_topic = normalize_sample_topic(topic)
    normalized_difficulty = str(difficulty).strip().lower()
    if normalized_difficulty not in _DIFFICULTY_ORDER:
        raise ValueError(f"Unsupported sample difficulty: {difficulty}")

    if normalized_topic == "sql":
        grouped = get_sample_questions_by_difficulty()
        pool = list(grouped.get(normalized_difficulty, []))
        return pool, normalized_difficulty

    grouped = _TOPIC_CATALOGS[normalized_topic].get_questions_by_difficulty()
    requested_pool = list(grouped.get(normalized_difficulty, []))
    served_difficulty = normalized_difficulty
    if not requested_pool:
        easy_pool = sorted(grouped.get("easy", []), key=lambda question: int(question.get("order", 0)))
        if normalized_difficulty == "medium":
            requested_pool = easy_pool[_SAMPLE_POOL_SIZE:_SAMPLE_POOL_SIZE * 2]
        elif normalized_difficulty == "hard":
            requested_pool = easy_pool[_SAMPLE_POOL_SIZE * 2:_SAMPLE_POOL_SIZE * 3]
        else:
            requested_pool = easy_pool[:_SAMPLE_POOL_SIZE]

    requested_pool = sorted(requested_pool, key=lambda question: int(question.get("order", 0)))
    return requested_pool[:_SAMPLE_POOL_SIZE], served_difficulty
