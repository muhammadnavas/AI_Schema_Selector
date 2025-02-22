import json

def load_schema_metadata():
    with open("data/schema_metadata.json", "r") as file:
        return json.load(file)

if __name__ == "__main__":
    print(load_schema_metadata())
