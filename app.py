from flask import Flask, render_template_string, request, jsonify
import sqlite3
import os
import json
import google.generativeai as genai
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure Gemini API using environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

def get_database_info(db_path):
    """Extract database schema and sample data"""
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

            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            rows = cursor.fetchall()
            sample_data = [dict(zip([col["name"] for col in column_info], row)) for row in rows]

            database_info[table_name] = {"columns": column_info, "sample_data": sample_data}

        conn.close()
        return {"tables": table_names, "data": database_info}

    except sqlite3.Error as e:
        return {"error": f"Error retrieving schema: {str(e)}"}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NL to SQL Converter</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        .code-block {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.75rem;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .spinner-border-sm {
            width: 1rem;
            height: 1rem;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row">
            <div class="col-md-12">
                <h2 class="text-center mb-4">Natural Language to SQL Converter</h2>
                <p class="text-center text-muted">Upload your SQLite database and convert natural language queries to SQL</p>
            </div>
        </div>

        <!-- Upload Database -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">1. Upload SQLite Database</h5>
            </div>
            <div class="card-body">
                <div class="input-group">
                    <input type="file" id="dbFile" class="form-control" accept=".db,.sqlite,.sqlite3">
                    <button class="btn btn-primary" type="button" onclick="uploadDatabase()">
                        <span id="uploadSpinner" class="spinner-border spinner-border-sm d-none" role="status"></span>
                        Upload
                    </button>
                </div>
                <div id="uploadMessage" class="mt-2"></div>
            </div>
        </div>

        <!-- Select Table -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">2. Select Table</h5>
            </div>
            <div class="card-body">
                <div class="input-group">
                    <select id="tableSelect" class="form-select">
                        <option value="">Select a table</option>
                    </select>
                    <button class="btn btn-info" type="button" onclick="fetchTables()">Refresh</button>
                </div>
                <div id="tableInfo" class="mt-3"></div>
            </div>
        </div>

        <!-- Convert NL to SQL -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">3. Convert Natural Language to SQL</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <textarea id="nlQuery" class="form-control" rows="3" placeholder="Enter your query in natural language...&#10;Example: 'Show me all customers from New York'"></textarea>
                </div>
                <button class="btn btn-success" onclick="convertNLtoSQL()">
                    <span id="convertSpinner" class="spinner-border spinner-border-sm d-none" role="status"></span>
                    Convert to SQL
                </button>
                <div id="sqlResult" class="mt-3"></div>
            </div>
        </div>

        <!-- Execute SQL -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">4. Execute SQL Query</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <textarea id="queryInput" class="form-control" rows="4" placeholder="Enter or modify SQL query..."></textarea>
                </div>
                <button class="btn btn-danger" onclick="executeSQL()">
                    <span id="executeSpinner" class="spinner-border spinner-border-sm d-none" role="status"></span>
                    Execute Query
                </button>
                <div id="queryMessage" class="mt-2"></div>
            </div>
        </div>

        <!-- Results -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">5. Query Results</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-bordered" id="resultsTable" style="display: none;">
                        <thead id="resultHead"></thead>
                        <tbody id="resultBody"></tbody>
                    </table>
                </div>
                <div id="noResults" class="text-muted text-center py-3" style="display: none;">
                    No results to display
                </div>
            </div>
        </div>
    </div>

    <script>
        function showSpinner(spinnerId) {
            document.getElementById(spinnerId).classList.remove('d-none');
        }

        function hideSpinner(spinnerId) {
            document.getElementById(spinnerId).classList.add('d-none');
        }

        function showMessage(elementId, message, type = 'success') {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`;
        }

        function uploadDatabase() {
            const fileInput = document.getElementById('dbFile');
            const file = fileInput.files[0];
            
            if (!file) {
                showMessage('uploadMessage', 'Please select a database file.', 'warning');
                return;
            }

            if (!file.name.match(/\.(db|sqlite|sqlite3)$/i)) {
                showMessage('uploadMessage', 'Please select a valid SQLite database file (.db, .sqlite, .sqlite3).', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            showSpinner('uploadSpinner');

            fetch("/upload", { method: "POST", body: formData })
            .then(response => response.json())
            .then(data => {
                hideSpinner('uploadSpinner');
                if (data.error) {
                    showMessage('uploadMessage', data.error, 'danger');
                } else {
                    showMessage('uploadMessage', data.message, 'success');
                    fetchTables();
                }
            })
            .catch(error => {
                hideSpinner('uploadSpinner');
                showMessage('uploadMessage', 'Upload failed: ' + error.message, 'danger');
            });
        }

        function fetchTables() {
            fetch("/get-tables")
            .then(response => response.json())
            .then(data => {
                const tableSelect = document.getElementById("tableSelect");
                tableSelect.innerHTML = "<option value=''>Select a table</option>";
                
                if (data.tables && data.tables.length > 0) {
                    data.tables.forEach(table => {
                        const option = document.createElement("option");
                        option.value = table;
                        option.textContent = table;
                        tableSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching tables:', error);
            });
        }

        function showTableInfo() {
            const tableName = document.getElementById("tableSelect").value;
            if (!tableName) {
                document.getElementById("tableInfo").innerHTML = '';
                return;
            }

            fetch("/get-tables")
            .then(response => response.json())
            .then(data => {
                const tableData = data.data[tableName];
                if (tableData) {
                    let infoHTML = `<div class="mt-2"><strong>Table: ${tableName}</strong><br>`;
                    infoHTML += `<strong>Columns:</strong> ${tableData.columns.map(col => col.name + ' (' + col.type + ')').join(', ')}`;
                    infoHTML += '</div>';
                    document.getElementById("tableInfo").innerHTML = infoHTML;
                }
            });
        }

        document.getElementById("tableSelect").addEventListener('change', showTableInfo);

        function convertNLtoSQL() {
            const nlQuery = document.getElementById("nlQuery").value.trim();
            const tableName = document.getElementById("tableSelect").value;
            
            if (!nlQuery || !tableName) {
                showMessage('sqlResult', 'Please enter a query and select a table.', 'warning');
                return;
            }

            showSpinner('convertSpinner');

            fetch("/nl-to-sql", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: nlQuery, table: tableName })
            })
            .then(response => response.json())
            .then(data => {
                hideSpinner('convertSpinner');
                if (data.error) {
                    showMessage('sqlResult', data.error, 'danger');
                } else if (data.sql_query) {
                    document.getElementById("sqlResult").innerHTML = 
                        `<div class="alert alert-info"><strong>Generated SQL:</strong></div>
                         <div class="code-block">${data.sql_query}</div>`;
                    document.getElementById("queryInput").value = data.sql_query;
                } else {
                    showMessage('sqlResult', 'No SQL query generated.', 'warning');
                }
            })
            .catch(error => {
                hideSpinner('convertSpinner');
                showMessage('sqlResult', 'Conversion failed: ' + error.message, 'danger');
            });
        }

        function executeSQL() {
            const query = document.getElementById("queryInput").value.trim();
            
            if (!query) {
                showMessage('queryMessage', 'Please enter an SQL query.', 'warning');
                return;
            }

            showSpinner('executeSpinner');

            fetch("/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                hideSpinner('executeSpinner');
                
                if (data.error) {
                    showMessage('queryMessage', data.error, 'danger');
                    hideResults();
                } else if (data.results) {
                    displayResults(data.results);
                    showMessage('queryMessage', `Query executed successfully. ${data.results.length} rows returned.`, 'success');
                } else if (data.message) {
                    showMessage('queryMessage', data.message, 'success');
                    hideResults();
                }
            })
            .catch(error => {
                hideSpinner('executeSpinner');
                showMessage('queryMessage', 'Query execution failed: ' + error.message, 'danger');
                hideResults();
            });
        }

        function displayResults(results) {
            if (!results || results.length === 0) {
                hideResults();
                return;
            }

            const table = document.getElementById('resultsTable');
            const head = document.getElementById('resultHead');
            const body = document.getElementById('resultBody');
            const noResults = document.getElementById('noResults');

            // Show table, hide no results message
            table.style.display = 'table';
            noResults.style.display = 'none';

            // Build header
            const headers = Object.keys(results[0]);
            head.innerHTML = '<tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';

            // Build body
            body.innerHTML = results.map(row => 
                '<tr>' + headers.map(h => `<td>${row[h] !== null ? row[h] : '<em>NULL</em>'}</td>`).join('') + '</tr>'
            ).join('');
        }

        function hideResults() {
            document.getElementById('resultsTable').style.display = 'none';
            document.getElementById('noResults').style.display = 'block';
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and file.filename.lower().endswith(('.db', '.sqlite', '.sqlite3')):
            filename = secure_filename('database.db')
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Verify it's a valid SQLite database
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                
                if not tables:
                    os.remove(file_path)
                    return jsonify({'error': 'The uploaded file appears to be empty or contains no tables.'}), 400
                
                return jsonify({'message': f'Database uploaded successfully with {len(tables)} tables.'})
                
            except sqlite3.Error:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'error': 'Invalid SQLite database file.'}), 400
        
        return jsonify({'error': 'Please upload a valid SQLite database file (.db, .sqlite, .sqlite3).'}), 400
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/get-tables', methods=['GET'])
def get_tables():
    try:
        db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
        database_info = get_database_info(db_path)
        
        if isinstance(database_info, dict) and 'error' in database_info:
            return jsonify(database_info), 400
            
        return jsonify(database_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nl-to-sql', methods=['POST'])
def nl_to_sql():
    try:
        data = request.json
        nl_query = data.get("query", "").strip()
        table_name = data.get("table", "").strip()

        if not nl_query:
            return jsonify({"error": "No query provided"}), 400

        if not table_name:
            return jsonify({"error": "Please select a table"}), 400

        db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
        database_info = get_database_info(db_path)
        
        if isinstance(database_info, dict) and 'error' in database_info:
            return jsonify(database_info), 400
        
        # Get specific table information
        table_data = database_info['data'].get(table_name)
        if not table_data:
            return jsonify({"error": f"Table '{table_name}' not found"}), 400
        
        # Build a focused prompt for the selected table
        columns_info = ", ".join([f"{col['name']} ({col['type']})" for col in table_data['columns']])
        
        # Format sample data for context
        sample_data_str = ""
        if table_data['sample_data']:
            sample_data_str = "Sample data:\n"
            for i, row in enumerate(table_data['sample_data'][:3]):
                sample_data_str += f"Row {i+1}: {row}\n"

        prompt = f"""
Convert the following natural language query to a valid SQLite SQL query.

Table: {table_name}
Columns: {columns_info}

{sample_data_str}

Natural language query: "{nl_query}"

Instructions:
- Generate ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Use the exact table name: {table_name}
- Use the exact column names as provided
- Include appropriate WHERE, ORDER BY, GROUP BY clauses as needed
- For aggregations, use proper GROUP BY
- Limit results to reasonable numbers (e.g., LIMIT 100) for large result sets

SQL Query:
"""

        try:
            response = model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up the response - remove any markdown formatting
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            # Basic validation
            if not sql_query.lower().startswith(('select', 'insert', 'update', 'delete')):
                return jsonify({"error": "Generated query doesn't appear to be valid SQL"}), 400
            
            return jsonify({"sql_query": sql_query})
            
        except Exception as e:
            return jsonify({"error": f"Failed to generate SQL query: {str(e)}"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Request processing failed: {str(e)}"}), 500

@app.route('/execute', methods=['POST'])
def execute_query():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No SQL query provided'}), 400
        
        db_path = os.path.join(app.config['UPLOAD_FOLDER'], 'database.db')
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database file not found. Please upload a database first.'}), 400
        
        # Basic SQL injection prevention - block dangerous keywords
        dangerous_keywords = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate']
        query_lower = query.lower()
        
        # Allow only SELECT statements for safety
        if not query_lower.strip().startswith('select'):
            return jsonify({'error': 'Only SELECT queries are allowed for security reasons.'}), 400
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convert to list of dictionaries
        results_list = [dict(row) for row in results]
        
        conn.close()
        return jsonify({'results': results_list})
        
    except sqlite3.Error as e:
        return jsonify({'error': f'SQL Error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Query execution failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("=== NL to SQL Converter ===")
    print("Make sure your .env file contains GEMINI_API_KEY=your_actual_api_key")
    print("Starting server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)