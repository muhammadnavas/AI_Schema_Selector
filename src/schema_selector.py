from models.retrieval_model import select_schema

def get_relevant_schema(query):
    return select_schema(query)

if __name__ == "__main__":
    query = "List all customers who made purchases"
    print(get_relevant_schema(query))
