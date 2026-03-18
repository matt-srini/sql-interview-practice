from __future__ import annotations

from question_bank.common import (
    CUSTOMERS_SCHEMA,
    DEPARTMENTS_SCHEMA,
    EMPLOYEES_SCHEMA,
    ORDERS_SCHEMA,
    merge_schema,
    q,
)


QUESTIONS = [
    # Existing medium questions become order 1/2
    q(
        id=30,
        order=5,
        title="Customers With No Orders",
        difficulty="medium",
        description=(
            "Write a SQL query to find all customers who have never placed an order. "
            "Return the customer id and name, ordered by id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name "
            "FROM customers c "
            "LEFT JOIN orders o ON c.id = o.customer_id "
            "WHERE o.id IS NULL "
            "ORDER BY c.id"
        ),
        solution_query=(
            "SELECT c.id, c.name\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON c.id = o.customer_id\n"
            "WHERE o.id IS NULL\n"
            "ORDER BY c.id;"
        ),
        explanation=(
            "A LEFT JOIN keeps all customers. Customers without matching orders have NULLs on the orders side."
        ),
    ),
    q(
        id=39,
        order=14,
        title="Running Total of Sales",
        difficulty="medium",
        description=(
            "Calculate the running total of order amounts ordered by date. Return order id, date, amount, and running_total."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, date, amount, "
            "SUM(amount) OVER (ORDER BY CAST(date AS DATE) ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total "
            "FROM orders "
            "ORDER BY CAST(date AS DATE), id"
        ),
        solution_query=(
            "SELECT\n"
            "    id,\n"
            "    date,\n"
            "    amount,\n"
            "    SUM(amount) OVER (\n"
            "        ORDER BY CAST(date AS DATE)\n"
            "        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW\n"
            "    ) AS running_total\n"
            "FROM orders\n"
            "ORDER BY CAST(date AS DATE), id;"
        ),
        explanation=(
            "A window SUM computes a cumulative total without collapsing rows like GROUP BY would."
        ),
    ),

    # New medium questions
    q(
        id=26,
        order=1,
        title="Total Spend With Customer Names",
        difficulty="medium",
        description=(
            "Return customer id, customer name, and total spend as `total_spend`. Include customers with zero spend. "
            "Order by total_spend descending then id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name, COALESCE(SUM(o.amount), 0) AS total_spend "
            "FROM customers c "
            "LEFT JOIN orders o ON o.customer_id = c.id "
            "GROUP BY c.id, c.name "
            "ORDER BY total_spend DESC, c.id"
        ),
        solution_query=(
            "SELECT c.id, c.name, COALESCE(SUM(o.amount), 0) AS total_spend\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON o.customer_id = c.id\n"
            "GROUP BY c.id, c.name\n"
            "ORDER BY total_spend DESC, c.id;"
        ),
        explanation="LEFT JOIN keeps all customers; COALESCE converts NULL sums into 0.",
    ),
    q(
        id=33,
        order=8,
        title="Top Spending Customer",
        difficulty="medium",
        description=(
            "Return the single customer (id and name) with the highest total order amount."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name "
            "FROM customers c "
            "JOIN orders o ON o.customer_id = c.id "
            "GROUP BY c.id, c.name "
            "ORDER BY SUM(o.amount) DESC, c.id "
            "LIMIT 1"
        ),
        solution_query=(
            "SELECT c.id, c.name\n"
            "FROM customers c\n"
            "JOIN orders o ON o.customer_id = c.id\n"
            "GROUP BY c.id, c.name\n"
            "ORDER BY SUM(o.amount) DESC, c.id\n"
            "LIMIT 1;"
        ),
        explanation="Aggregate by customer and pick the max via ORDER BY ... LIMIT 1.",
    ),
    q(
        id=27,
        order=2,
        title="Monthly Revenue",
        difficulty="medium",
        description=(
            "Compute total revenue per month. Return `month` (YYYY-MM-01) and `revenue`, ordered by month."
        ),
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
        explanation="DATE_TRUNC buckets dates by month; then SUM amounts per bucket.",
    ),
    q(
        id=28,
        order=3,
        title="Orders Above Average Amount",
        difficulty="medium",
        description=(
            "Return order id and amount for orders whose amount is above the overall average order amount. Order by amount desc."
        ),
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
        explanation="Compare each row to an aggregate computed in a scalar subquery.",
    ),
    q(
        id=36,
        order=11,
        title="Employees Above Department Average",
        difficulty="medium",
        description=(
            "Return employee name, department name, and salary for employees whose salary is above their department average. "
            "Order by department then salary desc."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH dept_avg AS (\n"
            "  SELECT department_id, AVG(salary) AS avg_salary\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN dept_avg a ON a.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary > a.avg_salary\n"
            "ORDER BY department, e.salary DESC"
        ),
        solution_query=(
            "WITH dept_avg AS (\n"
            "    SELECT department_id, AVG(salary) AS avg_salary\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN dept_avg a ON a.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary > a.avg_salary\n"
            "ORDER BY department, e.salary DESC;"
        ),
        explanation="Compute department averages in a CTE, then filter employees against that average.",
    ),
    q(
        id=40,
        order=15,
        title="Order Rank Per Customer",
        difficulty="medium",
        description=(
            "For each order, compute its rank within the customer by amount descending. Return order id, customer_id, amount, and rank."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, customer_id, amount, "
            "RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk "
            "FROM orders "
            "ORDER BY customer_id, rnk, id"
        ),
        solution_query=(
            "SELECT\n"
            "    id,\n"
            "    customer_id,\n"
            "    amount,\n"
            "    RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk\n"
            "FROM orders\n"
            "ORDER BY customer_id, rnk, id;"
        ),
        explanation="RANK() assigns a 1-based rank per customer based on order amount.",
    ),
    q(
        id=32,
        order=7,
        title="Most Recent Order Per Customer",
        difficulty="medium",
        description=(
            "Return each customer_id and the date of their most recent order as `last_order_date`."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, MAX(CAST(date AS DATE)) AS last_order_date "
            "FROM orders "
            "GROUP BY customer_id "
            "ORDER BY customer_id"
        ),
        solution_query=(
            "SELECT customer_id, MAX(CAST(date AS DATE)) AS last_order_date\n"
            "FROM orders\n"
            "GROUP BY customer_id\n"
            "ORDER BY customer_id;"
        ),
        explanation="MAX(date) per customer gives the last order date.",
    ),
    q(
        id=29,
        order=4,
        title="Customers With >= 2 Orders",
        difficulty="medium",
        description=(
            "Return customer_id and order_count for customers who placed at least 2 orders. Order by customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, COUNT(*) AS order_count "
            "FROM orders "
            "GROUP BY customer_id "
            "HAVING COUNT(*) >= 2 "
            "ORDER BY customer_id"
        ),
        solution_query=(
            "SELECT customer_id, COUNT(*) AS order_count\n"
            "FROM orders\n"
            "GROUP BY customer_id\n"
            "HAVING COUNT(*) >= 2\n"
            "ORDER BY customer_id;"
        ),
        explanation="HAVING filters after grouping, keeping only customers with 2+ orders.",
    ),
    q(
        id=50,
        order=25,
        title="Departments With No Employees",
        difficulty="medium",
        description=(
            "Return departments that have zero employees. Return department id and name."
        ),
        schema=merge_schema(DEPARTMENTS_SCHEMA, EMPLOYEES_SCHEMA),
        dataset_files=["departments.csv", "employees.csv"],
        expected_query=(
            "SELECT d.id, d.name "
            "FROM departments d "
            "LEFT JOIN employees e ON e.department_id = d.id "
            "WHERE e.id IS NULL "
            "ORDER BY d.id"
        ),
        solution_query=(
            "SELECT d.id, d.name\n"
            "FROM departments d\n"
            "LEFT JOIN employees e ON e.department_id = d.id\n"
            "WHERE e.id IS NULL\n"
            "ORDER BY d.id;"
        ),
        explanation="Same anti-join pattern as customers-with-no-orders.",
    ),
    q(
        id=47,
        order=22,
        title="Salary Percent Of Department Total",
        difficulty="medium",
        description=(
            "For each employee, compute salary as a percent of their department's total salary. Return employee name, department, salary, pct_of_dept_total."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, e.name AS employee, e.salary, "
            "ROUND(100.0 * e.salary / SUM(e.salary) OVER (PARTITION BY e.department_id), 2) AS pct_of_dept_total "
            "FROM employees e "
            "JOIN departments d ON d.id = e.department_id "
            "ORDER BY department, pct_of_dept_total DESC, employee"
        ),
        solution_query=(
            "SELECT\n"
            "    d.name AS department,\n"
            "    e.name AS employee,\n"
            "    e.salary,\n"
            "    ROUND(100.0 * e.salary / SUM(e.salary) OVER (PARTITION BY e.department_id), 2) AS pct_of_dept_total\n"
            "FROM employees e\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, pct_of_dept_total DESC, employee;"
        ),
        explanation="Window SUM gives department totals without a separate GROUP BY query.",
    ),
    q(
        id=31,
        order=6,
        title="Customer First Order Date",
        difficulty="medium",
        description=(
            "Return each customer (id, name) and their first order date (or NULL if none) as first_order_date. Order by customer id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name, MIN(CAST(o.date AS DATE)) AS first_order_date "
            "FROM customers c "
            "LEFT JOIN orders o ON o.customer_id = c.id "
            "GROUP BY c.id, c.name "
            "ORDER BY c.id"
        ),
        solution_query=(
            "SELECT c.id, c.name, MIN(CAST(o.date AS DATE)) AS first_order_date\n"
            "FROM customers c\n"
            "LEFT JOIN orders o ON o.customer_id = c.id\n"
            "GROUP BY c.id, c.name\n"
            "ORDER BY c.id;"
        ),
        explanation="MIN(date) per customer returns first order; LEFT JOIN keeps customers with no orders.",
    ),
    q(
        id=37,
        order=12,
        title="Employees With Same Salary",
        difficulty="medium",
        description=(
            "Return salary values that occur for 2 or more employees, along with the count as `cnt`. Order by salary desc."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query=(
            "SELECT salary, COUNT(*) AS cnt "
            "FROM employees "
            "GROUP BY salary "
            "HAVING COUNT(*) >= 2 "
            "ORDER BY salary DESC"
        ),
        solution_query=(
            "SELECT salary, COUNT(*) AS cnt\n"
            "FROM employees\n"
            "GROUP BY salary\n"
            "HAVING COUNT(*) >= 2\n"
            "ORDER BY salary DESC;"
        ),
        explanation="Group by salary and filter groups by size.",
    ),
    q(
        id=42,
        order=17,
        title="Orders With Customer Spend Rank",
        difficulty="medium",
        description=(
            "Compute total spend per customer and rank customers by spend (1 = highest). Return customer_id, total_spend, spend_rank."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH totals AS (\n"
            "  SELECT customer_id, SUM(amount) AS total_spend\n"
            "  FROM orders\n"
            "  GROUP BY customer_id\n"
            ")\n"
            "SELECT customer_id, total_spend, DENSE_RANK() OVER (ORDER BY total_spend DESC) AS spend_rank\n"
            "FROM totals\n"
            "ORDER BY spend_rank, customer_id"
        ),
        solution_query=(
            "WITH totals AS (\n"
            "    SELECT customer_id, SUM(amount) AS total_spend\n"
            "    FROM orders\n"
            "    GROUP BY customer_id\n"
            ")\n"
            "SELECT\n"
            "    customer_id,\n"
            "    total_spend,\n"
            "    DENSE_RANK() OVER (ORDER BY total_spend DESC) AS spend_rank\n"
            "FROM totals\n"
            "ORDER BY spend_rank, customer_id;"
        ),
        explanation="Aggregate in a CTE then rank totals using a window function.",
    ),
    q(
        id=41,
        order=16,
        title="Order Amount Share Of Customer Total",
        difficulty="medium",
        description=(
            "For each order, compute its share of the customer's total spend as `pct_of_customer_total` (0-100)."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, customer_id, amount, "
            "ROUND(100.0 * amount / SUM(amount) OVER (PARTITION BY customer_id), 2) AS pct_of_customer_total "
            "FROM orders "
            "ORDER BY customer_id, id"
        ),
        solution_query=(
            "SELECT\n"
            "    id,\n"
            "    customer_id,\n"
            "    amount,\n"
            "    ROUND(100.0 * amount / SUM(amount) OVER (PARTITION BY customer_id), 2) AS pct_of_customer_total\n"
            "FROM orders\n"
            "ORDER BY customer_id, id;"
        ),
        explanation="Divide the order amount by the window-summed customer total.",
    ),
    q(
        id=44,
        order=19,
        title="Order Gaps (Days Between Orders)",
        difficulty="medium",
        description=(
            "For each customer order sorted by date, compute days since the previous order. Return customer_id, id, date, days_since_prev."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, id, CAST(date AS DATE) AS date, "
            "DATE_DIFF('day', LAG(CAST(date AS DATE)) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id), CAST(date AS DATE)) AS days_since_prev "
            "FROM orders "
            "ORDER BY customer_id, date, id"
        ),
        solution_query=(
            "SELECT\n"
            "    customer_id,\n"
            "    id,\n"
            "    CAST(date AS DATE) AS date,\n"
            "    DATE_DIFF(\n"
            "        'day',\n"
            "        LAG(CAST(date AS DATE)) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id),\n"
            "        CAST(date AS DATE)\n"
            "    ) AS days_since_prev\n"
            "FROM orders\n"
            "ORDER BY customer_id, date, id;"
        ),
        explanation="Use LAG to access the previous order date per customer, then compute a date difference.",
    ),
    q(
        id=45,
        order=20,
        title="Customers Ordering In Both Jan And Feb (INTERSECT)",
        difficulty="medium",
        description=(
            "Return customer_ids who placed at least one order in January 2024 AND at least one in February 2024, using INTERSECT."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "(SELECT DISTINCT customer_id FROM orders WHERE CAST(date AS DATE) >= DATE '2024-01-01' AND CAST(date AS DATE) < DATE '2024-02-01') "
            "INTERSECT "
            "(SELECT DISTINCT customer_id FROM orders WHERE CAST(date AS DATE) >= DATE '2024-02-01' AND CAST(date AS DATE) < DATE '2024-03-01') "
            "ORDER BY customer_id"
        ),
        solution_query=(
            "(\n"
            "  SELECT DISTINCT customer_id\n"
            "  FROM orders\n"
            "  WHERE CAST(date AS DATE) >= DATE '2024-01-01'\n"
            "    AND CAST(date AS DATE) < DATE '2024-02-01'\n"
            ")\n"
            "INTERSECT\n"
            "(\n"
            "  SELECT DISTINCT customer_id\n"
            "  FROM orders\n"
            "  WHERE CAST(date AS DATE) >= DATE '2024-02-01'\n"
            "    AND CAST(date AS DATE) < DATE '2024-03-01'\n"
            ")\n"
            "ORDER BY customer_id;"
        ),
        explanation="INTERSECT returns values present in both sets.",
    ),
    q(
        id=46,
        order=21,
        title="Customers Ordering In Jan But Not Feb (EXCEPT)",
        difficulty="medium",
        description=(
            "Return customer_ids who ordered in January 2024 but did NOT order in February 2024, using EXCEPT."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "(SELECT DISTINCT customer_id FROM orders WHERE CAST(date AS DATE) >= DATE '2024-01-01' AND CAST(date AS DATE) < DATE '2024-02-01') "
            "EXCEPT "
            "(SELECT DISTINCT customer_id FROM orders WHERE CAST(date AS DATE) >= DATE '2024-02-01' AND CAST(date AS DATE) < DATE '2024-03-01') "
            "ORDER BY customer_id"
        ),
        solution_query=(
            "(\n"
            "  SELECT DISTINCT customer_id\n"
            "  FROM orders\n"
            "  WHERE CAST(date AS DATE) >= DATE '2024-01-01'\n"
            "    AND CAST(date AS DATE) < DATE '2024-02-01'\n"
            ")\n"
            "EXCEPT\n"
            "(\n"
            "  SELECT DISTINCT customer_id\n"
            "  FROM orders\n"
            "  WHERE CAST(date AS DATE) >= DATE '2024-02-01'\n"
            "    AND CAST(date AS DATE) < DATE '2024-03-01'\n"
            ")\n"
            "ORDER BY customer_id;"
        ),
        explanation="EXCEPT removes values present in the second set from the first set.",
    ),
    q(
        id=35,
        order=10,
        title="Employees With Department Employee Count",
        difficulty="medium",
        description=(
            "Return employee name, department name, and the number of employees in the employee's department as `dept_employee_count`."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, e.name AS employee, "
            "COUNT(*) OVER (PARTITION BY e.department_id) AS dept_employee_count "
            "FROM employees e "
            "JOIN departments d ON d.id = e.department_id "
            "ORDER BY department, employee"
        ),
        solution_query=(
            "SELECT\n"
            "    d.name AS department,\n"
            "    e.name AS employee,\n"
            "    COUNT(*) OVER (PARTITION BY e.department_id) AS dept_employee_count\n"
            "FROM employees e\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, employee;"
        ),
        explanation="COUNT(*) OVER (PARTITION BY department_id) repeats the department size on each employee row.",
    ),
    q(
        id=34,
        order=9,
        title="Department Salary Totals",
        difficulty="medium",
        description=(
            "Return each department name and the total salary in that department as `total_salary`. Order by total_salary desc."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, SUM(e.salary) AS total_salary "
            "FROM departments d "
            "JOIN employees e ON e.department_id = d.id "
            "GROUP BY d.name "
            "ORDER BY total_salary DESC, department"
        ),
        solution_query=(
            "SELECT d.name AS department, SUM(e.salary) AS total_salary\n"
            "FROM departments d\n"
            "JOIN employees e ON e.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY total_salary DESC, department;"
        ),
        explanation="Join and sum salaries per department.",
    ),
    q(
        id=43,
        order=18,
        title="Orders With Customer Name + Running Total Per Customer",
        difficulty="medium",
        description=(
            "Return customer name, order id, date, amount, and the running total per customer ordered by date."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.name, o.id, CAST(o.date AS DATE) AS date, o.amount, "
            "SUM(o.amount) OVER (PARTITION BY o.customer_id ORDER BY CAST(o.date AS DATE), o.id) AS running_total "
            "FROM orders o "
            "JOIN customers c ON c.id = o.customer_id "
            "ORDER BY c.name, date, o.id"
        ),
        solution_query=(
            "SELECT\n"
            "    c.name,\n"
            "    o.id,\n"
            "    CAST(o.date AS DATE) AS date,\n"
            "    o.amount,\n"
            "    SUM(o.amount) OVER (\n"
            "        PARTITION BY o.customer_id\n"
            "        ORDER BY CAST(o.date AS DATE), o.id\n"
            "    ) AS running_total\n"
            "FROM orders o\n"
            "JOIN customers c ON c.id = o.customer_id\n"
            "ORDER BY c.name, date, o.id;"
        ),
        explanation="Partition the running total by customer so each customer has their own cumulative sum.",
    ),
    q(
        id=38,
        order=13,
        title="Orders With Amount Category",
        difficulty="medium",
        description=(
            "Classify each order as 'small' (<1000), 'medium' (1000-2999), or 'large' (>=3000). Return id, amount, category."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, amount, "
            "CASE WHEN amount < 1000 THEN 'small' "
            "     WHEN amount < 3000 THEN 'medium' "
            "     ELSE 'large' END AS category "
            "FROM orders "
            "ORDER BY id"
        ),
        solution_query=(
            "SELECT\n"
            "    id,\n"
            "    amount,\n"
            "    CASE\n"
            "        WHEN amount < 1000 THEN 'small'\n"
            "        WHEN amount < 3000 THEN 'medium'\n"
            "        ELSE 'large'\n"
            "    END AS category\n"
            "FROM orders\n"
            "ORDER BY id;"
        ),
        explanation="A CASE expression maps numeric ranges to categories.",
    ),
    q(
        id=48,
        order=23,
        title="Employees With Department Median Salary",
        difficulty="medium",
        description=(
            "Return department name and the median salary in that department as `median_salary`. Order by department."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, MEDIAN(e.salary) AS median_salary "
            "FROM departments d "
            "JOIN employees e ON e.department_id = d.id "
            "GROUP BY d.name "
            "ORDER BY d.name"
        ),
        solution_query=(
            "SELECT d.name AS department, MEDIAN(e.salary) AS median_salary\n"
            "FROM departments d\n"
            "JOIN employees e ON e.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY d.name;"
        ),
        explanation="DuckDB supports MEDIAN() as an aggregate for numeric columns.",
    ),
    q(
        id=49,
        order=24,
        title="Customer Lifetime Value Buckets",
        difficulty="medium",
        description=(
            "Compute total spend per customer and bucket them into 'none' (0), 'low' (0-1999), 'mid' (2000-4999), 'high' (>=5000). "
            "Return customer_id, total_spend, bucket."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "WITH totals AS (\n"
            "  SELECT c.id AS customer_id, COALESCE(SUM(o.amount), 0) AS total_spend\n"
            "  FROM customers c\n"
            "  LEFT JOIN orders o ON o.customer_id = c.id\n"
            "  GROUP BY c.id\n"
            ")\n"
            "SELECT customer_id, total_spend,\n"
            "  CASE\n"
            "    WHEN total_spend = 0 THEN 'none'\n"
            "    WHEN total_spend < 2000 THEN 'low'\n"
            "    WHEN total_spend < 5000 THEN 'mid'\n"
            "    ELSE 'high'\n"
            "  END AS bucket\n"
            "FROM totals\n"
            "ORDER BY customer_id"
        ),
        solution_query=(
            "WITH totals AS (\n"
            "    SELECT c.id AS customer_id, COALESCE(SUM(o.amount), 0) AS total_spend\n"
            "    FROM customers c\n"
            "    LEFT JOIN orders o ON o.customer_id = c.id\n"
            "    GROUP BY c.id\n"
            ")\n"
            "SELECT\n"
            "    customer_id,\n"
            "    total_spend,\n"
            "    CASE\n"
            "        WHEN total_spend = 0 THEN 'none'\n"
            "        WHEN total_spend < 2000 THEN 'low'\n"
            "        WHEN total_spend < 5000 THEN 'mid'\n"
            "        ELSE 'high'\n"
            "    END AS bucket\n"
            "FROM totals\n"
            "ORDER BY customer_id;"
        ),
        explanation="Compute totals in a CTE, then map totals to a bucket with CASE.",
    ),
]
