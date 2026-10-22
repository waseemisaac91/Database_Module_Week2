
##Database_Module_Week2
#Assigment-2
#PostgreSQL using Python
#Waseem Isaac


import psycopg2
from psycopg2 import Error

# Update your password here
DB_CONFIG = {
    "host": "localhost",
    "database": "emp_db",
    "user": "postgres",
    "password": "W@isaac1091",
    "port": "5432"
}

def setup_tables():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Connected to PostgreSQL.\n")

        # Drop tables if they exist
        cur.execute("DROP TABLE IF EXISTS departments CASCADE;")
        cur.execute("DROP TABLE IF EXISTS employees CASCADE;")
        conn.commit()

        # 1. Create Tables
        cur.execute("""
            CREATE TABLE employees (
                emp_id INTEGER PRIMARY KEY,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                salary NUMERIC(10, 2),
                job_title VARCHAR(100),
                gender VARCHAR(10),
                hire_date DATE
            );
        """)
        
        cur.execute("""
            CREATE TABLE departments (
                emp_id INTEGER PRIMARY KEY,
                dept_name VARCHAR(100),
                dept_id INTEGER,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        print("Tables created.")

        # 2. Insert Employees 
        employees_data = [
            (17679, 'Robert', 'Gilmore', 110000, 'Operations Director', 'Male', '2018-09-04'),
            (26650, 'Elvis', 'Ritter', 86000, 'Sales Manager', 'Male', '2017-11-24'),
            (30840, 'David', 'Barrow', 85000, 'Data Scientist', 'Male', '2019-12-02'),
            (49714, 'Hugo', 'Forester', 55000, 'IT Support Specialist', 'Male', '2019-11-22'),
            (51821, 'Linda', 'Foster', 95000, 'Data Scientist', 'Female', '2019-04-29'),
            (67323, 'Lisa', 'Wiener', 75000, 'Business Analyst', 'Female', '2018-08-09'),
            (70950, 'Rodney', 'Weaver', 87000, 'Project Manager', 'Male', '2018-12-20'),
            (71329, 'Gayle', 'Meyer', 77000, 'HR Manager', 'Female', '2019-06-28'),
            (76589, 'Jason', 'Christian', 99000, 'Project Manager', 'Male', '2019-01-21'),
            (97927, 'Billie', 'Lanning', 67000, 'Web Developer', 'Female', '2018-06-25')
        ]
        
        cur.executemany("""
            INSERT INTO employees VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, employees_data)
        print(f"Inserted {len(employees_data)} rows into employees.")
        
        # 4. Insert Departments 
        departments_data = [
            (17679, 'Operations', 13),
            (26650, 'Marketing', 14),
            (30840, 'Operations', 13),
            (49714, 'Technology', 12), #    
            (51821, 'Operations', 13),
            (67323, 'Marketing', 14),
            (70950, 'Administrative', 11), # 
            (71329, 'Administrative', 11), # 
            (76589, 'Operations', 13),
            (97927, 'Technology', 12)
        ]
        
        cur.executemany("""
            INSERT INTO departments VALUES (%s, %s, %s);
        """, departments_data)
        conn.commit()
        print(f"Inserted {len(departments_data)} rows into departments.\n")

        # 5. Output Data 
        print("--- 1 Employees who get paid more than Rodney Weaver. ---")
        cur.execute("""
            SELECT first_name, last_name, salary FROM employees 
            WHERE salary > ( SELECT salary FROM employees 
                 WHERE first_name = 'Rodney' AND last_name = 'Weaver')
         """)
        
        for row in cur.fetchall():
            print(f"Name: {row[0]}  {row[1]} -> {row[2]}")

        print("\n--- 2 average, min and max salaries of all employees. ---")
        cur.execute("""
            SELECT AVG(salary), MIN(salary), MAX(salary)
            FROM employees;
        """)
        
        for row in cur.fetchall():
            print(f"Average: {row[0]}, Min: {row[1]}, Max: {row[2]}")

        print("\n--- 3 employees whose salary is more than 8700. Our query should return first name, last name, and salary info of the employees.. ---")
        cur.execute("""
            SELECT e.first_name, e.last_name, e.salary
            FROM employees e
            WHERE e.salary > 8700;
        """)
        
        for row in cur.fetchall():
            print(f"Name: {row[0]}  {row[1]} -> {row[2]}")

        print("\n--- 4 Find the employees (first name, last name from employees table) " \
        "who work under the Operations department (departments table)---")
        cur.execute("""   
        SELECT e.first_name, e.last_name
        FROM employees e
        JOIN departments d ON e.emp_id = d.emp_id
        WHERE d.dept_name = 'Operations'
        """)
        
        for row in cur.fetchall():
            print(f"Name: {row[0]}  {row[1]}")

        print("\n--- 5 Find the employees (first name, last name from employees table) " \
        "who work under the Technology  department (departments table) ")
        cur.execute("""   
        SELECT e.first_name, e.last_name, e.salary
        FROM employees e
        JOIN departments d ON e.emp_id = d.emp_id
        WHERE d.dept_name = 'Technology'
        """)
        
        for row in cur.fetchall():
            print(f"Name: {row[0]}  {row[1]}")

        print("\n--- 6 Find the average salary of female employees ---")
        cur.execute("""             
        SELECT avg(salary) FROM employees WHERE gender = 'Female'
        """)
        for row in cur.fetchall():
            print(f"Average Salary of Female Employees: {row[0]}")   

        print("\n--- 7 Find the average salary of each department ---")
        cur.execute("""             
        SELECT d.dept_name, avg(e.salary) AS average_salary
        FROM employees e
        JOIN departments d ON e.emp_id = d.emp_id
        GROUP BY d.dept_name
        """)
        for row in cur.fetchall():
            print(f"Department: {row[0]}, Average Salary: {row[1]}")

        print("\n--- 8 Find the oldest and newest employees ---")
        cur.execute(""" SELECT first_name, last_name, hire_date
        FROM employees              
        ORDER BY hire_date ASC
        LIMIT 1
        """)
        oldest_employee = cur.fetchone()
        newest_employee = cur.execute("""
        SELECT first_name, last_name, hire_date         
FROM employees
        ORDER BY hire_date DESC lIMIT 1
        """)
        newest_employee = cur.fetchone()

        print(f"Oldest Employee: {oldest_employee[0]} ")
        print(f"Newest Employee: {newest_employee[0]} ")

        print("\n--- 9 Find the hiring date and department of the highest paid employee-")
        cur.execute("""
                SELECT e.first_name, e.last_name, e.hire_date, d.dept_name
                FROM employees e
                JOIN departments d ON e.emp_id = d.emp_id
                WHERE e.salary = (SELECT MAX(salary) FROM employees);
                """)
        highest_paid_employee = cur.fetchone()
        
        print(f"Highest Paid Employee: {highest_paid_employee[0]} {highest_paid_employee[1]}")
        print(f"Hiring Date: {highest_paid_employee[2]}")
        print(f"Department: {highest_paid_employee[3]}")
        
        print("\n--- 10 Find the hiring date and department of the lowest paid employee ---")
        cur.execute("""
               SELECT e.first_name, e.last_name, e.hire_date, 
               COALESCE(d.dept_name, 'Unassigned') AS dept_name
               FROM employees e
               JOIN departments d ON e.emp_id = d.emp_id
               WHERE e.salary = (SELECT MIN(salary) FROM employees);
                """)
        lowest_paid_employee = cur.fetchone()
        
        print(f"Lowest Paid Employee: {lowest_paid_employee[0]} {lowest_paid_employee[1]}")
        print(f"Hiring Date: {lowest_paid_employee[2]}")
        print(f"Department: {lowest_paid_employee[3]}")
        
    except (Exception, Error) as error: 
        print(f"Error: {error}")
    finally:
        if conn is not None:

            cur.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    setup_tables()