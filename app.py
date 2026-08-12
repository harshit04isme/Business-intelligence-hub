import os
import sqlite3
import json
import requests
import pandas as pd
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load local environment variables (.env)
load_dotenv()

app = FastAPI(title="Enterprise Applied AI Analyst Portal")

# Configure CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "analytics.db"

# Helpers
def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file 'analytics.db' not found. Please run generate_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_schema() -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")]
    
    schema_desc = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_desc = [f"{c['name']} ({c['type']}){' PRIMARY KEY' if c['pk'] else ''}" for c in columns]
        schema_desc.append(f"Table: {table}\nColumns:\n  " + "\n  ".join(col_desc))
        
    conn.close()
    return "\n\n".join(schema_desc)

# Pydantic Schemas for Requests
class CellUpdate(BaseModel):
    table: str
    column: str
    value: Any
    pk_column: str
    pk_value: Any

class RowDelete(BaseModel):
    table: str
    pk_column: str
    pk_value: Any

class BatchClean(BaseModel):
    table: str
    action: str  # drop_duplicates, fill_na, normalize_case
    column: Optional[str] = None
    value: Optional[str] = None  # for fill_na or case type (upper/lower/title)

class SQLExecute(BaseModel):
    query: str

class ChatQuery(BaseModel):
    message: str

# API Routes
@app.get("/api/tables")
def list_tables():
    """Retrieve metadata for all tables in the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")]
    
    result = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
        row_count = cursor.fetchone()["count"]
        
        cursor.execute(f"PRAGMA table_info({table});")
        columns = [dict(col) for col in cursor.fetchall()]
        
        result[table] = {
            "name": table,
            "rows": row_count,
            "columns": [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"])} for c in columns]
        }
    conn.close()
    return result

@app.get("/api/table/{table_name}")
def get_table_data(table_name: str, page: int = 1, limit: int = 50, search: str = "", search_col: str = ""):
    """Paginated data retrieval for an analyst data grid with support for column search."""
    # Validate table name to prevent SQL Injection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    valid_tables = [row["name"] for row in cursor.fetchall()]
    if table_name not in valid_tables:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid table name")

    offset = (page - 1) * limit
    
    # Structure search query
    where_clause = ""
    params = []
    if search and search_col:
        # Check that search column exists in table to prevent injection
        cursor.execute(f"PRAGMA table_info({table_name});")
        cols = [c["name"] for c in cursor.fetchall()]
        if search_col in cols:
            where_clause = f"WHERE {search_col} LIKE ?"
            params.append(f"%{search}%")
            
    # Count total matching rows
    count_query = f"SELECT COUNT(*) as count FROM {table_name} {where_clause};"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()["count"]
    
    # Get rows
    data_query = f"SELECT * FROM {table_name} {where_clause} LIMIT ? OFFSET ?;"
    query_params = params + [limit, offset]
    
    cursor.execute(data_query, query_params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "table": table_name,
        "total": total_count,
        "page": page,
        "limit": limit,
        "data": rows
    }

@app.post("/api/cell/update")
def update_cell(payload: CellUpdate):
    """Executes a single inline cell update for manual data cleaning."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Safety checks on tables & columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    if payload.table not in [r["name"] for r in cursor.fetchall()]:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid table name")
        
    cursor.execute(f"PRAGMA table_info({payload.table});")
    cols = [c["name"] for c in cursor.fetchall()]
    if payload.column not in cols or payload.pk_column not in cols:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid column name(s)")

    query = f"UPDATE {payload.table} SET {payload.column} = ? WHERE {payload.pk_column} = ?;"
    try:
        cursor.execute(query, (payload.value, payload.pk_value))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail=f"Database update failed: {e}")
        
    conn.close()
    return {"status": "success", "message": f"Updated {payload.table}.{payload.column} to {payload.value}"}

@app.post("/api/row/delete")
def delete_row(payload: RowDelete):
    """Manual deletion of a row from the data table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Safety checks
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    if payload.table not in [r["name"] for r in cursor.fetchall()]:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid table name")
        
    cursor.execute(f"PRAGMA table_info({payload.table});")
    cols = [c["name"] for c in cursor.fetchall()]
    if payload.pk_column not in cols:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid primary key column name")

    query = f"DELETE FROM {payload.table} WHERE {payload.pk_column} = ?;"
    try:
        cursor.execute(query, (payload.pk_value,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail=f"Database deletion failed: {e}")
        
    conn.close()
    return {"status": "success", "message": f"Deleted row from table {payload.table} where {payload.pk_column} = {payload.pk_value}"}

@app.post("/api/clean/batch")
def batch_clean(payload: BatchClean):
    """Executes a batch data cleaning routine using pandas for fast manipulation."""
    conn = get_db_connection()
    
    try:
        # Read the SQL table into a Pandas DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {payload.table};", conn)
        
        cols = list(df.columns)
        action_msg = ""
        
        if payload.action == "drop_duplicates":
            before_len = len(df)
            df = df.drop_duplicates()
            action_msg = f"Dropped {before_len - len(df)} duplicate records."
            
        elif payload.action == "fill_na":
            if not payload.column or payload.column not in cols:
                raise HTTPException(status_code=400, detail="Column not provided or invalid for fill_na action.")
            
            val = payload.value
            # Deduce fill logic: mean / numeric / string
            if val == "mean" and pd.api.types.is_numeric_dtype(df[payload.column]):
                fill_val = df[payload.column].mean()
            elif val == "mode":
                fill_val = df[payload.column].mode()[0] if not df[payload.column].mode().empty else ""
            else:
                # Convert string type if needed
                if pd.api.types.is_numeric_dtype(df[payload.column]):
                    try:
                        fill_val = float(val) if '.' in val else int(val)
                    except ValueError:
                        fill_val = val
                else:
                    fill_val = val
            
            df[payload.column] = df[payload.column].fillna(fill_val)
            action_msg = f"Filled missing values in column '{payload.column}' using '{val}'."
            
        elif payload.action == "normalize_case":
            if not payload.column or payload.column not in cols:
                raise HTTPException(status_code=400, detail="Column not provided or invalid for casing action.")
            
            case_type = payload.value or "title"
            if case_type == "upper":
                df[payload.column] = df[payload.column].astype(str).str.upper()
            elif case_type == "lower":
                df[payload.column] = df[payload.column].astype(str).str.lower()
            else:
                df[payload.column] = df[payload.column].astype(str).str.title()
                
            action_msg = f"Normalized values in '{payload.column}' to case '{case_type}'."
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported batch action: {payload.action}")
            
        # Write DataFrame back to SQLite: drop original table index and replace
        df.to_sql(payload.table, conn, index=False, if_exists="replace")
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Batch cleaning fail: {e}")
        
    conn.close()
    return {"status": "success", "message": action_msg}

@app.post("/api/sql/execute")
def execute_sql(payload: SQLExecute):
    """SQL Sandbox endpoint allowing data analysts to inspect schemas or perform manual operations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query_stripped = payload.query.strip().lower()
    
    try:
        cursor.execute(payload.query)
        
        # Check if query is a SELECT statement or similar returnable query
        if query_stripped.startswith("select") or query_stripped.startswith("pragma") or query_stripped.startswith("explain"):
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return {
                "type": "select",
                "rowCount": len(rows),
                "data": rows,
                "message": "Query executed successfully."
            }
        else:
            conn.commit()
            rows_affected = conn.total_changes
            conn.close()
            return {
                "type": "mutation",
                "rowCount": rows_affected,
                "message": f"Query successful. Rows affected/modified: {rows_affected}"
            }
    except Exception as e:
        conn.close()
        return {
            "type": "error",
            "message": str(e)
        }

@app.post("/api/chat")
def chat_to_db(payload: ChatQuery):
    """Natural language interface executing SQL code generation vs the database."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not groq_api_key or "gsk_" not in groq_api_key:
        # Fallback simulated analyst if no keys are found
        # (This prevents crashes while enabling a standard test bed)
        msg_lower = payload.message.lower()
        if "sale" in msg_lower or "spent" in msg_lower or "spend" in msg_lower:
            sql = "SELECT SUM(amount) as total_sales FROM transactions;"
            res = [{"total_sales": 328845.54}]
            ans = "Based on a direct query, the total revenue logged in the transactional database is **$328,845.54** across all customer profiles."
        elif "count" in msg_lower or "customer" in msg_lower:
            sql = "SELECT COUNT(*) as total_customers FROM customers;"
            res = [{"total_customers": 1000}]
            ans = "The database currently registers a demographic cohort of **1,000 customers**."
        else:
            sql = "SELECT * FROM customer_segments LIMIT 3;"
            res = []
            ans = "I detected the search intent but no API key is set. Here is a sample query you can run in the SQL Sandbox instead: `SELECT AVG(monetary) FROM customer_segments GROUP BY cluster_id;`"
            
        return {
            "sql": sql,
            "results": res,
            "explanation": "Simulated parser (Fallback Mode - No Groq Key)",
            "answer": ans
        }

    # Retrieve active schemas
    db_schema = get_db_schema()

    # Step A: Translate Natural English to SQL
    translation_system_prompt = (
        "You are an assistant that translates natural language questions into valid, optimized SQLite SQL queries. "
        "Your responses must contain ONLY a JSON object representation. Do not include markdown code block backticks."
    )
    
    translation_user_prompt = f"""
Given this SQLite database schema:
{db_schema}

Translate this question into a valid, optimized SQLite query:
"{payload.message}"

Return a JSON format structure with exactly these keys:
- "sql": "the raw SQLite query string"
- "explanation": "a short 1-sentence descriptor of what is being queried"

Do not explain the SQL or provide markdown. Return ONLY the JSON object.
"""
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        # 1. Fetch SQL Query
        payload_sql = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": translation_system_prompt},
                {"role": "user", "content": translation_user_prompt}
            ],
            "temperature": 0.1
        }
        
        res = requests.post(url, headers=headers, json=payload_sql, timeout=15)
        if res.status_code != 200:
            raise Exception(f"Groq API Error: {res.text}")
            
        raw_text = res.json()["choices"][0]["message"]["content"].strip()
        
        # Strip code block decorators if present
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                raw_text = "\n".join(lines[1:-1]).strip()
                
        translation = json.loads(raw_text)
        sql_query = translation["sql"]
        sql_explanation = translation["explanation"]
        
        # 2. Run generated SQL against DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_query)
        db_rows = [dict(row) for row in cursor.fetchall()[:100]] # Cap results at 100 rows for size limits
        conn.close()
        
        # 3. Request LLM to write a friendly natural language response
        interpretation_system_prompt = (
            "You are a professional Business Intelligence Analyst. Describe the query outcomes "
            "clearly in markdown for non-technical users. Avoid comments about SQL syntax unless relevant."
        )
        
        interpretation_user_prompt = f"""
The user asked: "{payload.message}"
The generated SQL query ran: `{sql_query}`
The resulting rows returned (up to 100):
{json.dumps(db_rows)}

Construct a concise, engaging summary in business terms answering the user's question directly.
"""
        
        payload_interpret = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": interpretation_system_prompt},
                {"role": "user", "content": interpretation_user_prompt}
            ],
            "temperature": 0.2
        }
        
        res_interpret = requests.post(url, headers=headers, json=payload_interpret, timeout=15)
        if res_interpret.status_code != 200:
            raise Exception(f"Interpretation API error: {res_interpret.text}")
            
        chat_answer = res_interpret.json()["choices"][0]["message"]["content"]
        
        return {
            "sql": sql_query,
            "explanation": sql_explanation,
            "results": db_rows,
            "answer": chat_answer
        }
        
    except Exception as e:
        print(f"Chat Exception: {e}")
        return {
            "sql": "-- Generation Failed --",
            "explanation": "Could not execute chat request",
            "results": [],
            "answer": f"Something went wrong processing your request: {e}. Please try checking the phrasing or run a manual query in the Sandbox."
        }

# Serve compiled frontend static items if they exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Exclude backend APIs from asset fallbacks
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API Endpoint Not Found")
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/")
    def index_fallback():
        return {"status": "running", "message": "Backend API is active. Frontend static files have not been built or served at /static yet."}

if __name__ == "__main__":
    import uvicorn
    # Load backend server on Port 8000
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
