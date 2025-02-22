function sendQuery() {
    let query = document.getElementById("queryInput").value;
    let resultDiv = document.getElementById("result");

    if (!query.trim()) {
        resultDiv.innerHTML = "<p style='color:red;'>Please enter a query.</p>";
        return;
    }

    fetch("/query", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
        } else {
            resultDiv.innerHTML = `<p><b>SQL Query:</b> ${data.sql_query}</p><p><b>Result:</b> ${JSON.stringify(data.result)}</p>`;
        }
    })
    .catch(error => {
        resultDiv.innerHTML = `<p style='color:red;'>Error: ${error}</p>`;
    });
}
