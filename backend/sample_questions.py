from __future__ import annotations

from typing import Any, Optional

from question_bank.common import (
    CUSTOMERS_SCHEMA,
    DEPARTMENTS_SCHEMA,
    EMPLOYEES_SCHEMA,
    ORDERS_SCHEMA,
    merge_schema,
    q,
)


SAMPLE_QUESTIONS: list[dict[str, Any]] = [
    q(
        id=1001,
        order=1,
        title="Sample Easy: Highest Salary",
        difficulty="easy",
        description="Return the highest salary from employees as max_salary.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT MAX(salary) AS max_salary FROM employees",
        solution_query="SELECT MAX(salary) AS max_salary FROM employees;",
        explanation="Use MAX to pick the largest salary value.",
    ),
    q(
        id=1002,
        order=2,
        title="Sample Easy: Engineering Employees",
        difficulty="easy",
        description="Return employee names who belong to the Engineering department, sorted by name.",
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT e.name "
            "FROM employees e "
            "JOIN departments d ON d.id = e.department_id "
            "WHERE d.name = 'Engineering' "
            "ORDER BY e.name"
        ),
        solution_query=(
            "SELECT e.name\n"
            "FROM employees e\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE d.name = 'Engineering'\n"
            "ORDER BY e.name;"
        ),
        explanation="Join employees to departments and filter to Engineering.",
    ),
    q(
        id=1003,
        order=3,
        title="Sample Easy: Total Order Amount",
        difficulty="easy",
        description="Return the sum of all order amounts as total_amount.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query="SELECT SUM(amount) AS total_amount FROM orders",
        solution_query="SELECT SUM(amount) AS total_amount FROM orders;",
        explanation="Use SUM over the amount column.",
    ),
    q(
        id=2001,
        order=1,
        title="Sample Medium: Customers With No Orders",
        difficulty="medium",
        description="Return customer id and name for customers who have never placed an order.",
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name "
            "FROM customers c "
            "LEFT JOIN orders o ON o.customer_id = c.id "
            "WHERE o.id IS NULL "
            "ORDER BY c.id"
        ),
        solution_query=(
            "SELECT c.id, c.name\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON o.customer_id = c.id\n"
            "WHERE o.id IS NULL\n"
            "ORDER BY c.id;"
        ),
        explanation="LEFT JOIN keeps all customers; missing orders become NULL.",
    ),
    q(
        id=2002,
        order=2,
        title="Sample Medium: Monthly Revenue",
        difficulty="medium",
        description="Return month and revenue, grouped by month from orders.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, SUM(amount) AS revenue "
            "FROM orders "
            "GROUP BY 1 "
            "ORDER BY 1"
        ),
        solution_query=(
            "SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, SUM(amount) AS revenue\n"
            "FROM orders\n"
            "GROUP BY 1\n"
            "ORDER BY 1;"
        ),
        explanation="Bucket rows by month and aggregate with SUM.",
    ),
    q(
        id=2003,
        order=3,
        title="Sample Medium: Above Average Orders",
        difficulty="medium",
        description="Return order id and amount for orders above the overall average amount.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, amount "
            "FROM orders "
            "WHERE amount > (SELECT AVG(amount) FROM orders) "
            "ORDER BY amount DESC, id"
        ),
        solution_query=(
            "SELECT id, amount\n"
            "FROM orders\n"
            "WHERE amount > (SELECT AVG(amount) FROM orders)\n"
            "ORDER BY amount DESC, id;"
        ),
        explanation="Compare each amount to the scalar average subquery.",
    ),
    q(
        id=3001,
        order=1,
        title="Sample Hard: Top 2 Orders Per Customer",
        difficulty="hard",
        description="Return each customer's top 2 order amounts using a window rank.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, id AS order_id, amount, rnk "
            "FROM ("
            "  SELECT id, customer_id, amount, DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk "
            "  FROM orders"
            ") t "
            "WHERE rnk <= 2 "
            "ORDER BY customer_id, rnk, order_id"
        ),
        solution_query=(
            "SELECT customer_id, id AS order_id, amount, rnk\n"
            "FROM (\n"
            "  SELECT id, customer_id, amount,\n"
            "         DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk\n"
            "  FROM orders\n"
            ") t\n"
            "WHERE rnk <= 2\n"
            "ORDER BY customer_id, rnk, order_id;"
        ),
        explanation="Rank by customer and filter to the top two ranks.",
    ),
    q(
        id=3002,
        order=2,
        title="Sample Hard: Second Highest Salary Per Department",
        difficulty="hard",
        description="Return department and its second-highest distinct salary.",
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH ranked AS ("
            "  SELECT department_id, salary, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk "
            "  FROM employees"
            ") "
            "SELECT d.name AS department, MAX(CASE WHEN r.rnk = 2 THEN r.salary END) AS second_salary "
            "FROM departments d "
            "LEFT JOIN ranked r ON r.department_id = d.id "
            "GROUP BY d.name "
            "ORDER BY d.name"
        ),
        solution_query=(
            "WITH ranked AS (\n"
            "  SELECT department_id, salary,\n"
            "         DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk\n"
            "  FROM employees\n"
            ")\n"
            "SELECT d.name AS department, MAX(CASE WHEN r.rnk = 2 THEN r.salary END) AS second_salary\n"
            "FROM departments d\n"
            "LEFT JOIN ranked r ON r.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY d.name;"
        ),
        explanation="DENSE_RANK by department then select rank 2 salary.",
    ),
    q(
        id=3003,
        order=3,
        title="Sample Hard: Top Earner Share",
        difficulty="hard",
        description="For each department, return top salary divided by total salary as top_earner_share.",
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH stats AS ("
            "  SELECT department_id, MAX(salary) AS top_salary, SUM(salary) AS total_salary "
            "  FROM employees "
            "  GROUP BY department_id"
            ") "
            "SELECT d.name AS department, (s.top_salary * 1.0) / s.total_salary AS top_earner_share "
            "FROM stats s "
            "JOIN departments d ON d.id = s.department_id "
            "ORDER BY department"
        ),
        solution_query=(
            "WITH stats AS (\n"
            "  SELECT department_id, MAX(salary) AS top_salary, SUM(salary) AS total_salary\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, (s.top_salary * 1.0) / s.total_salary AS top_earner_share\n"
            "FROM stats s\n"
            "JOIN departments d ON d.id = s.department_id\n"
            "ORDER BY department;"
        ),
        explanation="Compute top and total salary per department, then divide.",
    ),
]


SAMPLE_INDEX: dict[int, dict[str, Any]] = {int(q["id"]): q for q in SAMPLE_QUESTIONS}


def get_sample_question(question_id: int) -> Optional[dict[str, Any]]:
    return SAMPLE_INDEX.get(int(question_id))


def get_sample_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in SAMPLE_QUESTIONS:
        grouped[q["difficulty"]].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x["order"]))
    return grouped
