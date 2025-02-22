from flask import Flask, render_template, request, jsonify
import sqlite3
from src.schema_selector import get_relevant_schema

app = Flask(__name__)

# Home route to serve the frontend
@app.route('/')
def home():
    return render_template("index.html")

# API endpoint to process queries
@app.route('/query', methods=['POST'])
def process_query():
    user_query = request.json.get("query", "")
    if not user_query:
        return jsonify({"error": "Query is empty"}), 400

    # Get SQL Query from schema selector
    sql_query = get_relevant_schema(user_query)

    try:
        conn = sqlite3.connect("data/database.db")
        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"sql_query": sql_query, "result": result})

if __name__ == '__main__':
    app.run(debug=True)
