import sqlite3
import os

# Ensure the 'data' directory exists
os.makedirs("data", exist_ok=True)

# Connect to the database (creates 'database.db' if not exists)
conn = sqlite3.connect("data/database.db")
cursor = conn.cursor()

# Create Employees Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        position TEXT NOT NULL,
        salary INTEGER NOT NULL
    );
""")

# Insert Sample Data
employees_data = [
    ("Alice Johnson", "Software Engineer", 80000),
    ("Bob Smith", "Data Scientist", 95000),
    ("Charlie Brown", "HR Manager", 70000),
    ("David Wilson", "Product Manager", 120000),
    ("Emma Davis", "Marketing Lead", 65000)
]

cursor.executemany("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?);", employees_data)

# Commit and close connection
conn.commit()
conn.close()

print("✅ Database 'data/database.db' initialized with employee data!")
