def process_query(query):
    return query.lower().strip()

if __name__ == "__main__":
    query = "Show me all employees with their departments"
    print(process_query(query))
