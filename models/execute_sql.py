import sqlite3
import mysql.connector
import psycopg2

# Execute SQL Query in Different Databases
def execute_sql(sql_query, db_type="sqlite", db_config=None):
    result = None

    try:
        if db_type == "sqlite":
            conn = sqlite3.connect(db_config["database"])  # SQLite
        elif db_type == "mysql":
            conn = mysql.connector.connect(**db_config)  # MySQL
        elif db_type == "postgres":
            conn = psycopg2.connect(**db_config)  # PostgreSQL
        else:
            raise ValueError("Unsupported database type!")

        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()

    except Exception as e:
        print(f"Database Error: {e}")
    
    finally:
        if conn:
            conn.close()

    return result
