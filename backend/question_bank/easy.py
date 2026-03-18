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
    # 1
    q(
        id=25,
        order=25,
        title="Second Highest Salary",
        difficulty="easy",
        description=(
            "Write a SQL query to find the second highest salary from the "
            "`employees` table. If there is no second highest salary, return NULL."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query=(
            "SELECT MAX(salary) AS SecondHighestSalary "
            "FROM employees "
            "WHERE salary < (SELECT MAX(salary) FROM employees)"
        ),
        solution_query=(
            "SELECT MAX(salary) AS SecondHighestSalary\n"
            "FROM employees\n"
            "WHERE salary < (SELECT MAX(salary) FROM employees);"
        ),
        explanation=(
            "The inner subquery gets the maximum salary. The outer query then takes the "
            "maximum salary that is strictly less than that maximum, which is the second-highest."
        ),
    ),
    # 2
    q(
        id=21,
        order=21,
        title="Find Duplicate Emails",
        difficulty="easy",
        description=(
            "Write a SQL query to find all email addresses in the `employees` table that appear more than once."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query=(
            "SELECT email "
            "FROM employees "
            "GROUP BY email "
            "HAVING COUNT(*) > 1 "
            "ORDER BY email"
        ),
        solution_query=(
            "SELECT email\n"
            "FROM employees\n"
            "GROUP BY email\n"
            "HAVING COUNT(*) > 1\n"
            "ORDER BY email;"
        ),
        explanation=(
            "Group by email and keep only groups where the count is greater than 1."
        ),
    ),

    # New easy questions
    q(
        id=1,
        order=1,
        title="Highest Salary",
        difficulty="easy",
        description="Return the highest salary in the `employees` table as `max_salary`.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT MAX(salary) AS max_salary FROM employees",
        solution_query="SELECT MAX(salary) AS max_salary\nFROM employees;",
        explanation="MAX(salary) returns the highest salary value.",
    ),
    q(
        id=2,
        order=2,
        title="Lowest Salary",
        difficulty="easy",
        description="Return the lowest salary in the `employees` table as `min_salary`.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT MIN(salary) AS min_salary FROM employees",
        solution_query="SELECT MIN(salary) AS min_salary\nFROM employees;",
        explanation="MIN(salary) returns the smallest salary value.",
    ),
    q(
        id=5,
        order=5,
        title="Employees In Engineering",
        difficulty="easy",
        description=(
            "List employee names who work in the Engineering department. Return one column `name`, ordered alphabetically."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT e.name "
            "FROM employees e "
            "JOIN departments d ON e.department_id = d.id "
            "WHERE d.name = 'Engineering' "
            "ORDER BY e.name"
        ),
        solution_query=(
            "SELECT e.name\n"
            "FROM employees e\n"
            "JOIN departments d ON e.department_id = d.id\n"
            "WHERE d.name = 'Engineering'\n"
            "ORDER BY e.name;"
        ),
        explanation="Join employees to departments and filter to Engineering.",
    ),
    q(
        id=3,
        order=3,
        title="Count Employees",
        difficulty="easy",
        description="Return the number of rows in `employees` as `employee_count`.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT COUNT(*) AS employee_count FROM employees",
        solution_query="SELECT COUNT(*) AS employee_count\nFROM employees;",
        explanation="COUNT(*) counts all rows.",
    ),
    q(
        id=22,
        order=22,
        title="Employees Per Department",
        difficulty="easy",
        description=(
            "Return each department name and the number of employees in it as `employee_count`. Order by department name."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT d.name AS department, COUNT(*) AS employee_count "
            "FROM departments d "
            "JOIN employees e ON e.department_id = d.id "
            "GROUP BY d.name "
            "ORDER BY d.name"
        ),
        solution_query=(
            "SELECT d.name AS department, COUNT(*) AS employee_count\n"
            "FROM departments d\n"
            "JOIN employees e ON e.department_id = d.id\n"
            "GROUP BY d.name\n"
            "ORDER BY d.name;"
        ),
        explanation="Group by department name and count employees per group.",
    ),
    q(
        id=23,
        order=23,
        title="Average Salary",
        difficulty="easy",
        description="Return the average employee salary as `avg_salary`.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT AVG(salary) AS avg_salary FROM employees",
        solution_query="SELECT AVG(salary) AS avg_salary\nFROM employees;",
        explanation="AVG(salary) computes the mean salary.",
    ),
    q(
        id=6,
        order=6,
        title="Employees With Salary >= 90000",
        difficulty="easy",
        description=(
            "List employee id, name, and salary for employees earning at least 90000. Order by salary descending."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query=(
            "SELECT id, name, salary "
            "FROM employees "
            "WHERE salary >= 90000 "
            "ORDER BY salary DESC, id"
        ),
        solution_query=(
            "SELECT id, name, salary\n"
            "FROM employees\n"
            "WHERE salary >= 90000\n"
            "ORDER BY salary DESC, id;"
        ),
        explanation="Filter by salary threshold and order by salary.",
    ),
    q(
        id=4,
        order=4,
        title="Distinct Departments In Employees",
        difficulty="easy",
        description="Return the distinct department_id values present in `employees`, ordered ascending.",
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT DISTINCT department_id FROM employees ORDER BY department_id",
        solution_query="SELECT DISTINCT department_id\nFROM employees\nORDER BY department_id;",
        explanation="DISTINCT removes duplicate department ids.",
    ),
    q(
        id=10,
        order=10,
        title="Customers Count",
        difficulty="easy",
        description="Return the number of customers in `customers` as `customer_count`.",
        schema=merge_schema(CUSTOMERS_SCHEMA),
        dataset_files=["customers.csv"],
        expected_query="SELECT COUNT(*) AS customer_count FROM customers",
        solution_query="SELECT COUNT(*) AS customer_count\nFROM customers;",
        explanation="COUNT(*) counts all customers.",
    ),
    q(
        id=11,
        order=11,
        title="Total Order Amount",
        difficulty="easy",
        description="Return the total sum of all order amounts as `total_amount`.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query="SELECT SUM(amount) AS total_amount FROM orders",
        solution_query="SELECT SUM(amount) AS total_amount\nFROM orders;",
        explanation="SUM(amount) totals all order amounts.",
    ),
    q(
        id=12,
        order=12,
        title="Orders In March 2024",
        difficulty="easy",
        description=(
            "List order id and amount for orders placed in March 2024. Order by date then id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, amount "
            "FROM orders "
            "WHERE CAST(date AS DATE) >= DATE '2024-03-01' AND CAST(date AS DATE) < DATE '2024-04-01' "
            "ORDER BY CAST(date AS DATE), id"
        ),
        solution_query=(
            "SELECT id, amount\n"
            "FROM orders\n"
            "WHERE CAST(date AS DATE) >= DATE '2024-03-01'\n"
            "  AND CAST(date AS DATE) < DATE '2024-04-01'\n"
            "ORDER BY CAST(date AS DATE), id;"
        ),
        explanation="Filter using a half-open date range for March 2024.",
    ),
    q(
        id=13,
        order=13,
        title="Orders Above 3000",
        difficulty="easy",
        description="Return id, customer_id, amount for orders with amount > 3000, ordered by amount descending.",
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT id, customer_id, amount "
            "FROM orders "
            "WHERE amount > 3000 "
            "ORDER BY amount DESC, id"
        ),
        solution_query=(
            "SELECT id, customer_id, amount\n"
            "FROM orders\n"
            "WHERE amount > 3000\n"
            "ORDER BY amount DESC, id;"
        ),
        explanation="Simple filter and sort.",
    ),
    q(
        id=14,
        order=14,
        title="Customer Names For Orders",
        difficulty="easy",
        description=(
            "Return order id, customer name, and amount for all orders. Order by order id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT o.id, c.name, o.amount "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.id "
            "ORDER BY o.id"
        ),
        solution_query=(
            "SELECT o.id, c.name, o.amount\n"
            "FROM orders o\n"
            "JOIN customers c ON o.customer_id = c.id\n"
            "ORDER BY o.id;"
        ),
        explanation="Join orders to customers to get the customer name.",
    ),
    q(
        id=17,
        order=17,
        title="Customers With At Least One Order",
        difficulty="easy",
        description=(
            "Return distinct customer id and name for customers who have at least one order. Order by customer id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT DISTINCT c.id, c.name "
            "FROM customers c "
            "JOIN orders o ON o.customer_id = c.id "
            "ORDER BY c.id"
        ),
        solution_query=(
            "SELECT DISTINCT c.id, c.name\n"
            "FROM customers c\n"
            "JOIN orders o ON o.customer_id = c.id\n"
            "ORDER BY c.id;"
        ),
        explanation="An inner join returns only customers with matching orders; DISTINCT removes duplicates.",
    ),
    q(
        id=18,
        order=18,
        title="Customers Without Orders (NOT IN)",
        difficulty="easy",
        description=(
            "Return id and name of customers who have no orders using a subquery with NOT IN. Order by id."
        ),
        schema=merge_schema(CUSTOMERS_SCHEMA, ORDERS_SCHEMA),
        dataset_files=["customers.csv", "orders.csv"],
        expected_query=(
            "SELECT id, name "
            "FROM customers "
            "WHERE id NOT IN (SELECT DISTINCT customer_id FROM orders) "
            "ORDER BY id"
        ),
        solution_query=(
            "SELECT id, name\n"
            "FROM customers\n"
            "WHERE id NOT IN (SELECT DISTINCT customer_id FROM orders)\n"
            "ORDER BY id;"
        ),
        explanation="NOT IN filters customers whose id never appears in orders.customer_id.",
    ),
    q(
        id=8,
        order=8,
        title="Department Names",
        difficulty="easy",
        description="Return all department names as `name`, ordered alphabetically.",
        schema=merge_schema(DEPARTMENTS_SCHEMA),
        dataset_files=["departments.csv"],
        expected_query="SELECT name FROM departments ORDER BY name",
        solution_query="SELECT name\nFROM departments\nORDER BY name;",
        explanation="Select and order the department names.",
    ),
    q(
        id=9,
        order=9,
        title="Employees With Department Name",
        difficulty="easy",
        description=(
            "Return employee id, employee name, and department name. Order by employee id."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA, DEPARTMENTS_SCHEMA),
        dataset_files=["employees.csv", "departments.csv"],
        expected_query=(
            "SELECT e.id, e.name, d.name AS department "
            "FROM employees e "
            "JOIN departments d ON e.department_id = d.id "
            "ORDER BY e.id"
        ),
        solution_query=(
            "SELECT e.id, e.name, d.name AS department\n"
            "FROM employees e\n"
            "JOIN departments d ON e.department_id = d.id\n"
            "ORDER BY e.id;"
        ),
        explanation="Join employees to departments to enrich with department name.",
    ),
    q(
        id=15,
        order=15,
        title="Count Orders Per Customer",
        difficulty="easy",
        description=(
            "Return customer_id and the number of orders as `order_count`, ordered by customer_id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, COUNT(*) AS order_count "
            "FROM orders "
            "GROUP BY customer_id "
            "ORDER BY customer_id"
        ),
        solution_query=(
            "SELECT customer_id, COUNT(*) AS order_count\n"
            "FROM orders\n"
            "GROUP BY customer_id\n"
            "ORDER BY customer_id;"
        ),
        explanation="Group orders by customer_id and count rows.",
    ),
    q(
        id=16,
        order=16,
        title="Total Spend Per Customer",
        difficulty="easy",
        description=(
            "Return customer_id and total amount spent as `total_spend`, ordered by total_spend descending."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query=(
            "SELECT customer_id, SUM(amount) AS total_spend "
            "FROM orders "
            "GROUP BY customer_id "
            "ORDER BY total_spend DESC, customer_id"
        ),
        solution_query=(
            "SELECT customer_id, SUM(amount) AS total_spend\n"
            "FROM orders\n"
            "GROUP BY customer_id\n"
            "ORDER BY total_spend DESC, customer_id;"
        ),
        explanation="SUM(amount) per customer_id gives total spend.",
    ),
    q(
        id=20,
        order=20,
        title="Orders With Rounded Amount",
        difficulty="easy",
        description=(
            "Return order id and amount rounded to the nearest whole number as `amount_rounded`. Order by id."
        ),
        schema=merge_schema(ORDERS_SCHEMA),
        dataset_files=["orders.csv"],
        expected_query="SELECT id, ROUND(amount) AS amount_rounded FROM orders ORDER BY id",
        solution_query="SELECT id, ROUND(amount) AS amount_rounded\nFROM orders\nORDER BY id;",
        explanation="ROUND(amount) rounds the numeric amount.",
    ),
    q(
        id=7,
        order=7,
        title="Employees Name Starts With A",
        difficulty="easy",
        description=(
            "Return employee id and name for employees whose name starts with 'A'. Order by id."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT id, name FROM employees WHERE name LIKE 'A%' ORDER BY id",
        solution_query="SELECT id, name\nFROM employees\nWHERE name LIKE 'A%'\nORDER BY id;",
        explanation="LIKE 'A%' matches strings beginning with A.",
    ),
    q(
        id=24,
        order=24,
        title="Employees With NULL Email?",
        difficulty="easy",
        description=(
            "Return the number of employees with a NULL email as `null_email_count`."
        ),
        schema=merge_schema(EMPLOYEES_SCHEMA),
        dataset_files=["employees.csv"],
        expected_query="SELECT SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS null_email_count FROM employees",
        solution_query=(
            "SELECT SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS null_email_count\n"
            "FROM employees;"
        ),
        explanation="Use a CASE expression to count NULLs (this dataset happens to have none).",
    ),
    q(
        id=19,
        order=19,
        title="Customers Alphabetical",
        difficulty="easy",
        description="Return all customer names ordered alphabetically.",
        schema=merge_schema(CUSTOMERS_SCHEMA),
        dataset_files=["customers.csv"],
        expected_query="SELECT name FROM customers ORDER BY name",
        solution_query="SELECT name\nFROM customers\nORDER BY name;",
        explanation="Order customer names with ORDER BY name.",
    ),
]
