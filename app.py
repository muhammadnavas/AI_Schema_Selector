from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import ollama
import json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

MODEL_NAME = "llama3"

def get_database_info(db_path):
    if not os.path.exists(db_path):
        return "No database found."

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        database_info = {}

        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            column_info = [{"name": col[1], "type": col[2]} for col in columns]

            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
            rows = cursor.fetchall()
            sample_data = [dict(zip([col["name"] for col in column_info], row)) for row in rows]

            database_info[table_name] = {"columns": column_info, "sample_data": sample_data}

        conn.close()
        return json.dumps({"tables": table_names, "data": database_info}, indent=2)

    except sqlite3.Error as e:
        return f"Error retrieving schema: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and file.filename.endswith('.db'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
        file.save(file_path)
        return jsonify({'message': 'Database uploaded successfully', 'file_path': file_path})
    
    return jsonify({'error': 'Invalid file format'})

@app.route('/get-tables', methods=['GET'])
def get_tables():
    db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
    database_json = get_database_info(db_path)
    return jsonify(json.loads(database_json))

@app.route('/nl-to-sql', methods=['POST'])
def nl_to_sql():
    data = request.json
    nl_query = data.get("query", "").strip()
    table_name = data.get("table", "").strip()

    if not nl_query:
        return jsonify({"error": "No query provided"}), 400

    db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
    database_json = get_database_info(db_path)
    
    if not table_name:
        tables = json.loads(database_json).get("tables", [])
        return jsonify({"tables": tables, "error": "Multiple tables found. Please select one."})
    
    try:
        prompt = f"""
    Given the following database schema and sample data, generate a valid SQLite query.

    **Database Schema and Sample Data:**
    {database_json}

    **User Selected Table:** {table_name}

    **User Query:** "{nl_query}"

    ### Instructions:
    - Provide only the SQL query as output.
    - Ensure proper formatting and correct SQL syntax.
    - Use appropriate JOINs, WHERE conditions, and GROUP BY if necessary.
    - The query should be executable in SQLite without modifications.
    - Do not include explanations, comments, or additional text.

    ### Expected SQL Query:
    """

        response = ollama.generate(model=MODEL_NAME, prompt=prompt)
        sql_query = response['response'].strip().split("**Output SQL Query:**")[-1].strip()
        
        return jsonify({"sql_query": sql_query})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/execute', methods=['POST'])
def execute_query():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'No SQL query provided'}), 400
    
    db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
    if not os.path.exists(db_path):
        return jsonify({'error': 'Database file not found'})
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().lower().startswith("select"):
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []
            response_data = {'results': [dict(zip(column_names, row)) for row in results]}
        else:
            conn.commit()
            response_data = {'message': 'Query executed successfully'}

        conn.close()
        return jsonify(response_data)
    except sqlite3.Error as e:
        return jsonify({'error': f'SQL Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)