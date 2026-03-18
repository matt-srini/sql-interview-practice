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
    # Existing hard question becomes order 1
    q(
        id=51,
        order=1,
        title="Top 3 Salaries per Department",
        difficulty="hard",
        description=(
            "Find the top 3 highest salaries in each department. Return department name, employee name, and salary. "
            "Order results by department name, then salary descending."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, e.name AS employee, e.salary "
            "FROM ("
            "  SELECT *, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk "
            "  FROM employees"
            ") e "
            "JOIN departments d ON e.department_id = d.id "
            "WHERE e.rnk <= 3 "
            "ORDER BY department, salary DESC"
        ),
        solution_query=(
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM (\n"
            "    SELECT *,\n"
            "           DENSE_RANK() OVER (\n"
            "               PARTITION BY department_id\n"
            "               ORDER BY salary DESC\n"
            "           ) AS rnk\n"
            "    FROM employees\n"
            ") e\n"
            "JOIN departments d ON e.department_id = d.id\n"
            "WHERE e.rnk <= 3\n"
            "ORDER BY department, salary DESC;"
        ),
        explanation=(
            "DENSE_RANK assigns ranks by salary within each department. Filtering rnk <= 3 keeps the top earners per department."
        ),
    ),

    q(
        id=54,
        order=4,
        title="Top 2 Orders Per Customer (Window + Filter)",
        difficulty="hard",
        description=(
            "Return the top 2 highest-amount orders per customer. Return customer_id, order_id, amount, and rank. "
            "Order by customer_id then rank."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, id AS order_id, amount, rnk "
            "FROM (\n"
            "  SELECT *, DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk\n"
            "  FROM orders\n"
            ") t "
            "WHERE rnk <= 2 "
            "ORDER BY customer_id, rnk, order_id"
        ),
        solution_query=(
            "SELECT customer_id, id AS order_id, amount, rnk\n"
            "FROM (\n"
            "    SELECT *,\n"
            "           DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk\n"
            "    FROM orders\n"
            ") t\n"
            "WHERE rnk <= 2\n"
            "ORDER BY customer_id, rnk, order_id;"
        ),
        explanation="Window-rank orders per customer and keep the top 2.",
    ),
    q(
        id=52,
        order=2,
        title="Second Highest Salary Per Department",
        difficulty="hard",
        description=(
            "Return each department name and the second-highest distinct salary in that department as `second_salary`. "
            "If a department has fewer than 2 distinct salaries, return NULL for that department."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH ranked AS (\n"
            "  SELECT department_id, salary, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk\n"
            "  FROM employees\n"
            ")\n"
            "SELECT d.name AS department, MAX(CASE WHEN r.rnk = 2 THEN r.salary END) AS second_salary\n"
            "FROM departments d\n"
            "LEFT JOIN ranked r ON r.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY d.name"
        ),
        solution_query=(
            "WITH ranked AS (\n"
            "    SELECT\n"
            "        department_id,\n"
            "        salary,\n"
            "        DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk\n"
            "    FROM employees\n"
            ")\n"
            "SELECT\n"
            "    d.name AS department,\n"
            "    MAX(CASE WHEN r.rnk = 2 THEN r.salary END) AS second_salary\n"
            "FROM departments d\n"
            "LEFT JOIN ranked r ON r.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY d.name;"
        ),
        explanation="Rank salaries per department, then pick the salary where rank = 2.",
    ),
    q(
        id=64,
        order=14,
        title="Identify Salary Outliers (>= 1.5x Dept Median)",
        difficulty="hard",
        description=(
            "Find employees whose salary is at least 1.5x their department median salary. Return department, employee, salary, median_salary."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH med AS (\n"
            "  SELECT department_id, MEDIAN(salary) AS median_salary\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary, m.median_salary\n"
            "FROM employees e\n"
            "JOIN med m ON m.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary >= 1.5 * m.median_salary\n"
            "ORDER BY department, e.salary DESC"
        ),
        solution_query=(
            "WITH med AS (\n"
            "    SELECT department_id, MEDIAN(salary) AS median_salary\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            ")\n"
            "SELECT\n"
            "    d.name AS department,\n"
            "    e.name AS employee,\n"
            "    e.salary,\n"
            "    m.median_salary\n"
            "FROM employees e\n"
            "JOIN med m ON m.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary >= 1.5 * m.median_salary\n"
            "ORDER BY department, e.salary DESC;"
        ),
        explanation="Compute department medians in a CTE, then filter employees using that statistic.",
    ),
    q(
        id=60,
        order=10,
        title="Department Salary Distribution (NTILE)",
        difficulty="hard",
        description=(
            "Within each department, bucket employees into 4 salary quartiles (1=lowest) using NTILE(4). Return department, employee, salary, quartile."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, e.name AS employee, e.salary, "
            "NTILE(4) OVER (PARTITION BY e.department_id ORDER BY e.salary) AS quartile "
            "FROM employees e "
            "JOIN departments d ON d.id = e.department_id "
            "ORDER BY department, quartile, salary, employee"
        ),
        solution_query=(
            "SELECT\n"
            "    d.name AS department,\n"
            "    e.name AS employee,\n"
            "    e.salary,\n"
            "    NTILE(4) OVER (PARTITION BY e.department_id ORDER BY e.salary) AS quartile\n"
            "FROM employees e\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, quartile, salary, employee;"
        ),
        explanation="NTILE splits ordered rows into N roughly equal-sized buckets per partition.",
    ),
    q(
        id=59,
        order=9,
        title="Department Top Earner Share Of Department Total",
        difficulty="hard",
        description=(
            "For each department, compute (top salary) / (total department salary) as `top_earner_share`. Return department and share (0-1)."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH stats AS (\n"
            "  SELECT department_id, MAX(salary) AS top_salary, SUM(salary) AS total_salary\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, (s.top_salary * 1.0) / s.total_salary AS top_earner_share\n"
            "FROM stats s\n"
            "JOIN departments d ON d.id = s.department_id\n"
            "ORDER BY department"
        ),
        solution_query=(
            "WITH stats AS (\n"
            "    SELECT department_id, MAX(salary) AS top_salary, SUM(salary) AS total_salary\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            ")\n"
            "SELECT\n"
            "    d.name AS department,\n"
            "    (s.top_salary * 1.0) / s.total_salary AS top_earner_share\n"
            "FROM stats s\n"
            "JOIN departments d ON d.id = s.department_id\n"
            "ORDER BY department;"
        ),
        explanation="Compute per-department aggregates then divide to get the share.",
    ),
    q(
        id=65,
        order=15,
        title="Find Customers With Increasing Order Amounts",
        difficulty="hard",
        description=(
            "Find customers who have at least 3 orders where each order amount is strictly greater than the previous one (by date). Return customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH ordered AS (\n"
            "  SELECT\n"
            "    customer_id,\n"
            "    CAST(date AS DATE) AS date,\n"
            "    amount,\n"
            "    LAG(amount) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id) AS prev_amount\n"
            "  FROM orders\n"
            "), flags AS (\n"
            "  SELECT customer_id,\n"
            "         SUM(CASE WHEN prev_amount IS NOT NULL AND amount > prev_amount THEN 1 ELSE 0 END) AS increasing_steps\n"
            "  FROM ordered\n"
            "  GROUP BY customer_id\n"
            ")\n"
            "SELECT customer_id\n"
            "FROM flags\n"
            "WHERE increasing_steps >= 2\n"
            "ORDER BY customer_id"
        ),
        solution_query=(
            "WITH ordered AS (\n"
            "    SELECT\n"
            "        customer_id,\n"
            "        CAST(date AS DATE) AS date,\n"
            "        amount,\n"
            "        LAG(amount) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id) AS prev_amount\n"
            "    FROM orders\n"
            "),\n"
            "flags AS (\n"
            "    SELECT\n"
            "        customer_id,\n"
            "        SUM(CASE WHEN prev_amount IS NOT NULL AND amount > prev_amount THEN 1 ELSE 0 END) AS increasing_steps\n"
            "    FROM ordered\n"
            "    GROUP BY customer_id\n"
            ")\n"
            "SELECT customer_id\n"
            "FROM flags\n"
            "WHERE increasing_steps >= 2\n"
            "ORDER BY customer_id;"
        ),
        explanation=(
            "A customer with 3 strictly increasing orders has at least 2 increasing transitions. We count those transitions using LAG + CASE + SUM."
        ),
    ),
    q(
        id=66,
        order=16,
        title="Longest Gap Between Orders Per Customer",
        difficulty="hard",
        description=(
            "For each customer, compute the maximum number of days between consecutive orders. Return customer_id and max_gap_days."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH gaps AS (\n"
            "  SELECT\n"
            "    customer_id,\n"
            "    DATE_DIFF('day', LAG(CAST(date AS DATE)) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id), CAST(date AS DATE)) AS gap_days\n"
            "  FROM orders\n"
            ")\n"
            "SELECT customer_id, MAX(gap_days) AS max_gap_days\n"
            "FROM gaps\n"
            "GROUP BY customer_id\n"
            "ORDER BY customer_id"
        ),
        solution_query=(
            "WITH gaps AS (\n"
            "    SELECT\n"
            "        customer_id,\n"
            "        DATE_DIFF(\n"
            "            'day',\n"
            "            LAG(CAST(date AS DATE)) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id),\n"
            "            CAST(date AS DATE)\n"
            "        ) AS gap_days\n"
            "    FROM orders\n"
            ")\n"
            "SELECT customer_id, MAX(gap_days) AS max_gap_days\n"
            "FROM gaps\n"
            "GROUP BY customer_id\n"
            "ORDER BY customer_id;"
        ),
        explanation="Compute per-row gaps with LAG, then take MAX per customer.",
    ),
    q(
        id=58,
        order=8,
        title="Customer Revenue Contribution (Percent Of Total)",
        difficulty="hard",
        description=(
            "Compute each customer's total spend and the percentage of overall revenue they contribute as `pct_total_revenue`. Include customers with 0."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "WITH totals AS (\n"
            "  SELECT c.id AS customer_id, c.name, COALESCE(SUM(o.amount), 0) AS total_spend\n"
            "  FROM customers c\n"
            "  LEFT JOIN orders o ON o.customer_id = c.id\n"
            "  GROUP BY c.id, c.name\n"
            "), grand AS (\n"
            "  SELECT SUM(total_spend) AS grand_total FROM totals\n"
            ")\n"
            "SELECT t.customer_id, t.name, t.total_spend,\n"
            "  CASE WHEN g.grand_total = 0 THEN 0 ELSE ROUND(100.0 * t.total_spend / g.grand_total, 2) END AS pct_total_revenue\n"
            "FROM totals t\n"
            "CROSS JOIN grand g\n"
            "ORDER BY pct_total_revenue DESC, t.customer_id"
        ),
        solution_query=(
            "WITH totals AS (\n"
            "    SELECT c.id AS customer_id, c.name, COALESCE(SUM(o.amount), 0) AS total_spend\n"
            "    FROM customers c\n"
            "    LEFT JOIN orders o ON o.customer_id = c.id\n"
            "    GROUP BY c.id, c.name\n"
            "),\n"
            "grand AS (\n"
            "    SELECT SUM(total_spend) AS grand_total FROM totals\n"
            ")\n"
            "SELECT\n"
            "    t.customer_id,\n"
            "    t.name,\n"
            "    t.total_spend,\n"
            "    CASE\n"
            "        WHEN g.grand_total = 0 THEN 0\n"
            "        ELSE ROUND(100.0 * t.total_spend / g.grand_total, 2)\n"
            "    END AS pct_total_revenue\n"
            "FROM totals t\n"
            "CROSS JOIN grand g\n"
            "ORDER BY pct_total_revenue DESC, t.customer_id;"
        ),
        explanation="Compute totals per customer, compute a grand total, then divide totals by the grand total.",
    ),
    q(
        id=71,
        order=21,
        title="Employees In Departments With >= 5 Employees",
        difficulty="hard",
        description=(
            "Return employees (id, name) who belong to departments that have at least 5 employees. Order by department then id."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH dept_counts AS (\n"
            "  SELECT department_id, COUNT(*) AS cnt\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.id, e.name\n"
            "FROM employees e\n"
            "JOIN dept_counts dc ON dc.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE dc.cnt >= 5\n"
            "ORDER BY department, e.id"
        ),
        solution_query=(
            "WITH dept_counts AS (\n"
            "    SELECT department_id, COUNT(*) AS cnt\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.id, e.name\n"
            "FROM employees e\n"
            "JOIN dept_counts dc ON dc.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE dc.cnt >= 5\n"
            "ORDER BY department, e.id;"
        ),
        explanation="Aggregate department sizes, then filter employees by departments meeting the threshold.",
    ),
    q(
        id=55,
        order=5,
        title="Top Customer Per Month",
        difficulty="hard",
        description=(
            "For each month, find the customer with the highest total spend in that month. Return month, customer_id, spend."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH month_totals AS (\n"
            "  SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, customer_id, SUM(amount) AS spend\n"
            "  FROM orders\n"
            "  GROUP BY 1, 2\n"
            "), ranked AS (\n"
            "  SELECT *, DENSE_RANK() OVER (PARTITION BY month ORDER BY spend DESC) AS rnk\n"
            "  FROM month_totals\n"
            ")\n"
            "SELECT month, customer_id, spend\n"
            "FROM ranked\n"
            "WHERE rnk = 1\n"
            "ORDER BY month, customer_id"
        ),
        solution_query=(
            "WITH month_totals AS (\n"
            "    SELECT\n"
            "        DATE_TRUNC('month', CAST(date AS DATE)) AS month,\n"
            "        customer_id,\n"
            "        SUM(amount) AS spend\n"
            "    FROM orders\n"
            "    GROUP BY 1, 2\n"
            "),\n"
            "ranked AS (\n"
            "    SELECT *, DENSE_RANK() OVER (PARTITION BY month ORDER BY spend DESC) AS rnk\n"
            "    FROM month_totals\n"
            ")\n"
            "SELECT month, customer_id, spend\n"
            "FROM ranked\n"
            "WHERE rnk = 1\n"
            "ORDER BY month, customer_id;"
        ),
        explanation="Aggregate spend per (month, customer), rank within month, and keep rank=1.",
    ),
    q(
        id=56,
        order=6,
        title="Cumulative Revenue By Month",
        difficulty="hard",
        description=(
            "Compute revenue per month and the running cumulative revenue across months. Return month, revenue, cumulative_revenue."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH monthly AS (\n"
            "  SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, SUM(amount) AS revenue\n"
            "  FROM orders\n"
            "  GROUP BY 1\n"
            ")\n"
            "SELECT month, revenue, SUM(revenue) OVER (ORDER BY month) AS cumulative_revenue\n"
            "FROM monthly\n"
            "ORDER BY month"
        ),
        solution_query=(
            "WITH monthly AS (\n"
            "    SELECT DATE_TRUNC('month', CAST(date AS DATE)) AS month, SUM(amount) AS revenue\n"
            "    FROM orders\n"
            "    GROUP BY 1\n"
            ")\n"
            "SELECT month, revenue, SUM(revenue) OVER (ORDER BY month) AS cumulative_revenue\n"
            "FROM monthly\n"
            "ORDER BY month;"
        ),
        explanation="Aggregate by month first, then apply a window SUM to the monthly rows.",
    ),
    q(
        id=72,
        order=22,
        title="Employees Without Matching Department (Data Quality)",
        difficulty="hard",
        description=(
            "Return employees whose department_id does not exist in the departments table. Return employee id, name, department_id."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT e.id, e.name, e.department_id "
            "FROM employees e "
            "LEFT JOIN departments d ON d.id = e.department_id "
            "WHERE d.id IS NULL "
            "ORDER BY e.id"
        ),
        solution_query=(
            "SELECT e.id, e.name, e.department_id\n"
            "FROM employees e\n"
            "LEFT JOIN departments d ON d.id = e.department_id\n"
            "WHERE d.id IS NULL\n"
            "ORDER BY e.id;"
        ),
        explanation="A left join with a NULL check surfaces foreign keys with no dimension row.",
    ),
    q(
        id=73,
        order=23,
        title="Employees Who Earn More Than Their Manager (Self-Join Pattern)",
        difficulty="hard",
        description=(
            "(Concept question) Treat the employee with the smallest id in each department as the 'manager'. "
            "Return employees in each department who earn more than that manager. Return department, employee, salary, manager_salary."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH managers AS (\n"
            "  SELECT department_id, MIN(id) AS manager_id\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            "), mgr_salary AS (\n"
            "  SELECT m.department_id, e.salary AS manager_salary\n"
            "  FROM managers m\n"
            "  JOIN employees e ON e.id = m.manager_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary, ms.manager_salary\n"
            "FROM employees e\n"
            "JOIN mgr_salary ms ON ms.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary > ms.manager_salary\n"
            "ORDER BY department, e.salary DESC"
        ),
        solution_query=(
            "WITH managers AS (\n"
            "    SELECT department_id, MIN(id) AS manager_id\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            "),\n"
            "mgr_salary AS (\n"
            "    SELECT m.department_id, e.salary AS manager_salary\n"
            "    FROM managers m\n"
            "    JOIN employees e ON e.id = m.manager_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary, ms.manager_salary\n"
            "FROM employees e\n"
            "JOIN mgr_salary ms ON ms.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary > ms.manager_salary\n"
            "ORDER BY department, e.salary DESC;"
        ),
        explanation="This demonstrates a self-join style pattern using a derived 'manager' per department.",
    ),
    q(
        id=74,
        order=24,
        title="Customers With No Orders Using NOT EXISTS",
        difficulty="hard",
        description=(
            "Return customers (id, name) who have no orders, using NOT EXISTS (anti-semi join)."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT c.id, c.name "
            "FROM customers c "
            "WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id) "
            "ORDER BY c.id"
        ),
        solution_query=(
            "SELECT c.id, c.name\n"
            "FROM customers c\n"
            "WHERE NOT EXISTS (\n"
            "    SELECT 1 FROM orders o WHERE o.customer_id = c.id\n"
            ")\n"
            "ORDER BY c.id;"
        ),
        explanation="NOT EXISTS is a robust anti-join pattern that avoids NULL pitfalls of NOT IN.",
    ),
    q(
        id=68,
        order=18,
        title="Customers Who Ordered In Every Month Present",
        difficulty="hard",
        description=(
            "Return customers who have at least one order in every month that exists in the orders table. Return customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH months AS (\n"
            "  SELECT DISTINCT DATE_TRUNC('month', CAST(date AS DATE)) AS month FROM orders\n"
            "), cust_months AS (\n"
            "  SELECT customer_id, DATE_TRUNC('month', CAST(date AS DATE)) AS month\n"
            "  FROM orders\n"
            "  GROUP BY 1, 2\n"
            ")\n"
            "SELECT cm.customer_id\n"
            "FROM cust_months cm\n"
            "GROUP BY cm.customer_id\n"
            "HAVING COUNT(DISTINCT cm.month) = (SELECT COUNT(*) FROM months)\n"
            "ORDER BY cm.customer_id"
        ),
        solution_query=(
            "WITH months AS (\n"
            "    SELECT DISTINCT DATE_TRUNC('month', CAST(date AS DATE)) AS month\n"
            "    FROM orders\n"
            "),\n"
            "cust_months AS (\n"
            "    SELECT customer_id, DATE_TRUNC('month', CAST(date AS DATE)) AS month\n"
            "    FROM orders\n"
            "    GROUP BY 1, 2\n"
            ")\n"
            "SELECT cm.customer_id\n"
            "FROM cust_months cm\n"
            "GROUP BY cm.customer_id\n"
            "HAVING COUNT(DISTINCT cm.month) = (SELECT COUNT(*) FROM months)\n"
            "ORDER BY cm.customer_id;"
        ),
        explanation="Relational division: count months per customer and compare to total distinct months.",
    ),
    q(
        id=53,
        order=3,
        title="Top 1 Employee Per Department With Tie Handling",
        difficulty="hard",
        description=(
            "Return the highest-paid employee(s) per department. If there are ties, return all tied employees."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH ranked AS (\n"
            "  SELECT *, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk\n"
            "  FROM employees\n"
            ")\n"
            "SELECT d.name AS department, r.name AS employee, r.salary\n"
            "FROM ranked r\n"
            "JOIN departments d ON d.id = r.department_id\n"
            "WHERE r.rnk = 1\n"
            "ORDER BY department, employee"
        ),
        solution_query=(
            "WITH ranked AS (\n"
            "    SELECT *, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rnk\n"
            "    FROM employees\n"
            ")\n"
            "SELECT d.name AS department, r.name AS employee, r.salary\n"
            "FROM ranked r\n"
            "JOIN departments d ON d.id = r.department_id\n"
            "WHERE r.rnk = 1\n"
            "ORDER BY department, employee;"
        ),
        explanation="Use DENSE_RANK to keep all ties for rank 1.",
    ),
    q(
        id=61,
        order=11,
        title="Employees Above 90th Percentile In Department",
        difficulty="hard",
        description=(
            "Return employees whose salary is at or above the 90th percentile within their department. Return department, employee, salary."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH p AS (\n"
            "  SELECT department_id, QUANTILE_CONT(salary, 0.9) AS p90\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN p ON p.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary >= p.p90\n"
            "ORDER BY department, e.salary DESC"
        ),
        solution_query=(
            "WITH p AS (\n"
            "    SELECT department_id, QUANTILE_CONT(salary, 0.9) AS p90\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN p ON p.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "WHERE e.salary >= p.p90\n"
            "ORDER BY department, e.salary DESC;"
        ),
        explanation="Compute per-department percentile, then filter employees above it.",
    ),
    q(
        id=67,
        order=17,
        title="Customers With Orders In Consecutive Months",
        difficulty="hard",
        description=(
            "Find customers who placed orders in at least two consecutive months (e.g., Jan and Feb, Feb and Mar). Return customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH m AS (\n"
            "  SELECT DISTINCT customer_id, DATE_TRUNC('month', CAST(date AS DATE)) AS month\n"
            "  FROM orders\n"
            "), seq AS (\n"
            "  SELECT customer_id, month,\n"
            "         LAG(month) OVER (PARTITION BY customer_id ORDER BY month) AS prev_month\n"
            "  FROM m\n"
            ")\n"
            "SELECT DISTINCT customer_id\n"
            "FROM seq\n"
            "WHERE prev_month IS NOT NULL AND DATE_DIFF('month', prev_month, month) = 1\n"
            "ORDER BY customer_id"
        ),
        solution_query=(
            "WITH m AS (\n"
            "    SELECT DISTINCT customer_id, DATE_TRUNC('month', CAST(date AS DATE)) AS month\n"
            "    FROM orders\n"
            "),\n"
            "seq AS (\n"
            "    SELECT customer_id, month,\n"
            "           LAG(month) OVER (PARTITION BY customer_id ORDER BY month) AS prev_month\n"
            "    FROM m\n"
            ")\n"
            "SELECT DISTINCT customer_id\n"
            "FROM seq\n"
            "WHERE prev_month IS NOT NULL\n"
            "  AND DATE_DIFF('month', prev_month, month) = 1\n"
            "ORDER BY customer_id;"
        ),
        explanation="Reduce to distinct (customer, month) then use LAG and a month diff to detect consecutiveness.",
    ),
    q(
        id=75,
        order=25,
        title="Employees With Same Name Across Tables (Set Operation)",
        difficulty="hard",
        description=(
            "Return names that appear both as an employee name and a customer name, using INTERSECT. (Hint: likely none.)"
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, CUSTOMERS_SCHEMA),
        dataset_files=["employees.csv", "customers.csv"],
        expected_query=(
            "(SELECT DISTINCT name FROM employees) "
            "INTERSECT "
            "(SELECT DISTINCT name FROM customers) "
            "ORDER BY name"
        ),
        solution_query=(
            "(SELECT DISTINCT name FROM employees)\n"
            "INTERSECT\n"
            "(SELECT DISTINCT name FROM customers)\n"
            "ORDER BY name;"
        ),
        explanation="INTERSECT finds values present in both sets.",
    ),
    q(
        id=63,
        order=13,
        title="Department With Highest Salary Variance",
        difficulty="hard",
        description=(
            "Return the department with the largest salary variance (VAR_SAMP). Return department and variance."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, VAR_SAMP(e.salary) AS salary_variance "
            "FROM departments d "
            "JOIN employees e ON e.department_id = d.id "
            "GROUP BY d.name "
            "ORDER BY salary_variance DESC "
            "LIMIT 1"
        ),
        solution_query=(
            "SELECT d.name AS department, VAR_SAMP(e.salary) AS salary_variance\n"
            "FROM departments d\n"
            "JOIN employees e ON e.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY salary_variance DESC\n"
            "LIMIT 1;"
        ),
        explanation="Compute variance per department and take the max.",
    ),
    q(
        id=62,
        order=12,
        title="Employees With Salary Z-Score Within Department",
        difficulty="hard",
        description=(
            "Compute a z-score for each employee salary within their department: (salary - avg) / stddev_samp. Return department, employee, salary, z."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, e.name AS employee, e.salary, "
            "(e.salary - AVG(e.salary) OVER (PARTITION BY e.department_id)) / NULLIF(STDDEV_SAMP(e.salary) OVER (PARTITION BY e.department_id), 0) AS z "
            "FROM employees e "
            "JOIN departments d ON d.id = e.department_id "
            "ORDER BY department, z DESC"
        ),
        solution_query=(
            "SELECT\n"
            "    d.name AS department,\n"
            "    e.name AS employee,\n"
            "    e.salary,\n"
            "    (e.salary - AVG(e.salary) OVER (PARTITION BY e.department_id))\n"
            "      / NULLIF(STDDEV_SAMP(e.salary) OVER (PARTITION BY e.department_id), 0) AS z\n"
            "FROM employees e\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, z DESC;"
        ),
        explanation="Window AVG and STDDEV compute per-department stats; NULLIF avoids division by zero.",
    ),
    q(
        id=69,
        order=19,
        title="Customers Who Never Bought Above Their Average",
        difficulty="hard",
        description=(
            "Find customers where none of their orders is above their own average order amount. Return customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH avg_amt AS (\n"
            "  SELECT customer_id, AVG(amount) AS avg_amount\n"
            "  FROM orders\n"
            "  GROUP BY customer_id\n"
            ")\n"
            "SELECT a.customer_id\n"
            "FROM avg_amt a\n"
            "WHERE NOT EXISTS (\n"
            "  SELECT 1 FROM orders o WHERE o.customer_id = a.customer_id AND o.amount > a.avg_amount\n"
            ")\n"
            "ORDER BY a.customer_id"
        ),
        solution_query=(
            "WITH avg_amt AS (\n"
            "    SELECT customer_id, AVG(amount) AS avg_amount\n"
            "    FROM orders\n"
            "    GROUP BY customer_id\n"
            ")\n"
            "SELECT a.customer_id\n"
            "FROM avg_amt a\n"
            "WHERE NOT EXISTS (\n"
            "    SELECT 1\n"
            "    FROM orders o\n"
            "    WHERE o.customer_id = a.customer_id\n"
            "      AND o.amount > a.avg_amount\n"
            ")\n"
            "ORDER BY a.customer_id;"
        ),
        explanation="Compute per-customer averages then use NOT EXISTS to ensure no order exceeds that average.",
    ),
    q(
        id=70,
        order=20,
        title="Employees In Top 2 Departments By Total Salary",
        difficulty="hard",
        description=(
            "Find employees who work in the top 2 departments by total salary. Return department, employee, salary."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "WITH dept_totals AS (\n"
            "  SELECT department_id, SUM(salary) AS total_salary\n"
            "  FROM employees\n"
            "  GROUP BY department_id\n"
            "), top_depts AS (\n"
            "  SELECT department_id\n"
            "  FROM dept_totals\n"
            "  ORDER BY total_salary DESC\n"
            "  LIMIT 2\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN top_depts td ON td.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, e.salary DESC"
        ),
        solution_query=(
            "WITH dept_totals AS (\n"
            "    SELECT department_id, SUM(salary) AS total_salary\n"
            "    FROM employees\n"
            "    GROUP BY department_id\n"
            "),\n"
            "top_depts AS (\n"
            "    SELECT department_id\n"
            "    FROM dept_totals\n"
            "    ORDER BY total_salary DESC\n"
            "    LIMIT 2\n"
            ")\n"
            "SELECT d.name AS department, e.name AS employee, e.salary\n"
            "FROM employees e\n"
            "JOIN top_depts td ON td.department_id = e.department_id\n"
            "JOIN departments d ON d.id = e.department_id\n"
            "ORDER BY department, e.salary DESC;"
        ),
        explanation="Rank departments by total salary, take top 2, then join back to employees.",
    ),
    q(
        id=57,
        order=7,
        title="Orders Needed To Reach Target (Cumulative Threshold)",
        difficulty="hard",
        description=(
            "For each customer, order their orders by date and find the first order where their running total reaches at least 5000. "
            "Return customer_id, order_id, date, running_total. If a customer never reaches 5000, they should not appear."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "WITH rt AS (\n"
            "  SELECT\n"
            "    customer_id,\n"
            "    id AS order_id,\n"
            "    CAST(date AS DATE) AS date,\n"
            "    SUM(amount) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id) AS running_total\n"
            "  FROM orders\n"
            "), hits AS (\n"
            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY date, order_id) AS rn\n"
            "  FROM rt\n"
            "  WHERE running_total >= 5000\n"
            ")\n"
            "SELECT customer_id, order_id, date, running_total\n"
            "FROM hits\n"
            "WHERE rn = 1\n"
            "ORDER BY customer_id"
        ),
        solution_query=(
            "WITH rt AS (\n"
            "    SELECT\n"
            "        customer_id,\n"
            "        id AS order_id,\n"
            "        CAST(date AS DATE) AS date,\n"
            "        SUM(amount) OVER (PARTITION BY customer_id ORDER BY CAST(date AS DATE), id) AS running_total\n"
            "    FROM orders\n"
            "),\n"
            "hits AS (\n"
            "    SELECT\n"
            "        *,\n"
            "        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY date, order_id) AS rn\n"
            "    FROM rt\n"
            "    WHERE running_total >= 5000\n"
            ")\n"
            "SELECT customer_id, order_id, date, running_total\n"
            "FROM hits\n"
            "WHERE rn = 1\n"
            "ORDER BY customer_id;"
        ),
        explanation="Compute a running total per customer, then pick the first row where it crosses the target using ROW_NUMBER.",
    ),
]
