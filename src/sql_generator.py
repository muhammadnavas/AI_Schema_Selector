def generate_sql(query, schema):
    if "employees" in query:
        return "SELECT name, salary FROM employees;"
    if "sales" in query:
        return "SELECT product, amount, date FROM sales;"
    return "SELECT * FROM unknown_table;"

if __name__ == "__main__":
    query = "Retrieve all employee names and salaries"
    schema = {"name": "EmployeeDB"}
    print(generate_sql(query, schema))
