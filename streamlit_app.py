import os
import sqlite3
import json
import requests
import pandas as pd
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Applied AI & Business Intelligence Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #6B7280;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre;
        border-radius: 8px;
        padding: 10px 16px;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "analytics.db"

def ensure_database():
    if not os.path.exists(DB_PATH):
        st.warning("⚠️ Database 'analytics.db' not found. Generating initial data & clustering pipeline...")
        try:
            from generate_db import generate_mock_data
            from analytics_engine import run_analytics
            generate_mock_data()
            run_analytics()
            st.success("✅ Database initialized successfully!")
        except Exception as e:
            st.error(f"Failed to initialize database: {e}")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Ensure database exists
ensure_database()

# Sidebar Navigation
st.sidebar.title("📊 BI Analyst Hub")
st.sidebar.markdown("---")

api_key = os.getenv("GROQ_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("🔑 Groq API Key", type="password", help="Enter Groq API Key for AI Narrative & Chatbot features.")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key

st.sidebar.markdown("""
### 🛠 Pipeline Control
""")
if st.sidebar.button("🔄 Regenerate Data & Clusters"):
    with st.spinner("Re-running ML clustering pipeline..."):
        try:
            from generate_db import generate_mock_data
            from analytics_engine import run_analytics
            generate_mock_data()
            run_analytics()
            st.sidebar.success("Database & clusters refreshed!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Deployed on Streamlit Cloud**\nPowered by FastAPI backend architecture, Scikit-Learn KMeans, and Groq Llama 3.3.")

# Header
st.markdown('<div class="main-title">Applied AI & Business Intelligence Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Enterprise Customer Analytics, Machine Learning Segmentation & AI Copilot</div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_overview, tab_clustering, tab_explorer, tab_ai_chat = st.tabs([
    "🏠 Executive Overview",
    "🎯 Customer Segmentation (ML)",
    "🔍 SQL Data Explorer",
    "🤖 AI Analyst Copilot"
])

# ---------------------------------------------------------
# TAB 1: EXECUTIVE OVERVIEW
# ---------------------------------------------------------
with tab_overview:
    conn = get_connection()
    
    # Key Performance Indicators
    c1, c2, c3, c4 = st.columns(4)
    
    total_customers = pd.read_sql_query("SELECT COUNT(*) FROM customers;", conn).iloc[0, 0]
    total_revenue = pd.read_sql_query("SELECT SUM(amount) FROM transactions;", conn).iloc[0, 0]
    avg_order = pd.read_sql_query("SELECT AVG(amount) FROM transactions;", conn).iloc[0, 0]
    total_clusters = pd.read_sql_query("SELECT COUNT(DISTINCT cluster_id) FROM customer_segments;", conn).iloc[0, 0] if os.path.exists(DB_PATH) else 0
    
    c1.metric("Total Customers", f"{total_customers:,}")
    c2.metric("Total Revenue", f"${total_revenue:,.2f}")
    c3.metric("Avg Order Value", f"${avg_order:,.2f}")
    c4.metric("Identified Segments", f"{total_clusters} Clusters")
    
    st.markdown("---")
    
    st.subheader("📄 Executive Business Report")
    
    if st.button("✨ Generate / Refresh AI Narrative Report"):
        if not os.getenv("GROQ_API_KEY"):
            st.error("Please set GROQ_API_KEY in environment or sidebar to generate AI reports.")
        else:
            with st.spinner("Analyzing cluster statistics with Groq Llama-3.3..."):
                try:
                    from ai_narrator import generate_report
                    generate_report()
                    st.success("Executive report generated!")
                except Exception as e:
                    st.error(f"Error generating report: {e}")
                    
    if os.path.exists("business_report.md"):
        with open("business_report.md", "r", encoding="utf-8") as f:
            report_text = f.read()
        st.markdown(report_text)
    else:
        st.info("Run `ai_narrator.py` or click the button above to generate the Executive Narrative Report.")
        
    conn.close()

# ---------------------------------------------------------
# TAB 2: CUSTOMER SEGMENTATION (ML)
# ---------------------------------------------------------
with tab_clustering:
    st.subheader("🎯 Customer Segmentation (K-Means Clustering)")
    
    conn = get_connection()
    segments_df = pd.read_sql_query("SELECT * FROM customer_segments;", conn)
    conn.close()
    
    if not segments_df.empty:
        if "segment_label" not in segments_df.columns:
            segments_df["segment_label"] = segments_df["cluster_id"].apply(lambda c: f"Segment {c}")
            
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("### Segment Summary")
            cluster_counts = segments_df.groupby(["cluster_id", "segment_label"]).size().reset_index(name="count")
            st.dataframe(cluster_counts, use_container_width=True)
            
            cluster_filter = st.selectbox("Filter by Segment", ["All"] + list(segments_df["segment_label"].unique()))
            
        with col_right:
            st.markdown("### Demographic Distribution (Age vs Income)")
            filtered_df = segments_df if cluster_filter == "All" else segments_df[segments_df["segment_label"] == cluster_filter]
            st.scatter_chart(filtered_df, x="age", y="income", color="segment_label")
            
        st.markdown("---")
        st.markdown("### Segment Profiles Detail")
        
        profile_cols = ["customer_id", "segment_label", "cluster_id", "age", "income", "recency", "frequency", "monetary", "avg_session_duration", "avg_pages_viewed"]
        display_df = filtered_df[[c for c in profile_cols if c in filtered_df.columns]]
        st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.warning("No segmentation data found. Please run the analytics pipeline.")

# ---------------------------------------------------------
# TAB 3: SQL DATA EXPLORER
# ---------------------------------------------------------
with tab_explorer:
    st.subheader("🔍 Interactive SQL Explorer")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
    
    selected_table = st.selectbox("Select Table to View", tables)
    if selected_table:
        table_df = pd.read_sql_query(f"SELECT * FROM {selected_table} LIMIT 100;", conn)
        st.markdown(f"**Showing top 100 rows from `{selected_table}`** (Total columns: {len(table_df.columns)})")
        st.dataframe(table_df, use_container_width=True)
        
    st.markdown("---")
    st.markdown("### ⚡ Custom SQL Query Runner")
    custom_sql = st.text_area("Write SQL Query", f"SELECT region, COUNT(*) as customer_count, AVG(income) as avg_income FROM customers GROUP BY region;", height=100)
    
    if st.button("Run SQL Query"):
        try:
            query_res = pd.read_sql_query(custom_sql, conn)
            st.success(f"Query executed successfully! Returned {len(query_res)} rows.")
            st.dataframe(query_res, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Error: {e}")
            
    conn.close()

# ---------------------------------------------------------
# TAB 4: AI ANALYST COPILOT
# ---------------------------------------------------------
with tab_ai_chat:
    st.subheader("🤖 AI Business Analyst Copilot")
    st.markdown("Ask natural language questions about your revenue, customer demographics, web engagement, or clusters.")
    
    user_query = st.text_input("Ask a business question:", placeholder="e.g. Which region has the highest average income and purchase frequency?")
    
    if st.button("Ask Analyst") and user_query:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            st.error("Please provide a valid GROQ_API_KEY in .env or the sidebar to use the AI Copilot.")
        else:
            with st.spinner("Analyzing schema and generating SQL query via Groq..."):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
                    
                    schema_desc = []
                    for t in tables:
                        cursor.execute(f"PRAGMA table_info({t});")
                        cols = [f"{c[1]} ({c[2]})" for c in cursor.fetchall()]
                        schema_desc.append(f"Table: {t}\nColumns: {', '.join(cols)}")
                    db_schema_str = "\n\n".join(schema_desc)
                    
                    # 1. SQL Generation Prompt
                    sql_sys = (
                        "You are an expert SQLite Data Analyst. Given the database schema, generate ONLY "
                        "valid SQLite SQL code answering the user request. Do not include markdown code block syntax or explanations."
                    )
                    sql_user = f"Schema:\n{db_schema_str}\n\nUser Question: {user_query}\nSQL Query:"
                    
                    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                    payload_sql = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "system", "content": sql_sys}, {"role": "user", "content": sql_user}],
                        "temperature": 0.1
                    }
                    
                    res_sql = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload_sql, timeout=15)
                    if res_sql.status_code != 200:
                        st.error(f"Groq API Error: {res_sql.text}")
                    else:
                        generated_sql = res_sql.json()["choices"][0]["message"]["content"].strip()
                        if generated_sql.startswith("```"):
                            generated_sql = generated_sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                            
                        st.markdown(f"**Generated SQL Query:**")
                        st.code(generated_sql, language="sql")
                        
                        # Execute query
                        query_df = pd.read_sql_query(generated_sql, conn)
                        st.markdown("**Query Results:**")
                        st.dataframe(query_df, use_container_width=True)
                        
                        # 2. Interpretation Prompt
                        interp_sys = "You are a senior Business Intelligence executive. Synthesize query results into concise, clear executive insights."
                        interp_user = f"User Question: '{user_query}'\nSQL Ran: {generated_sql}\nData Returned: {query_df.head(20).to_json(orient='records')}\nSummary:"
                        
                        payload_interp = {
                            "model": "llama-3.3-70b-versatile",
                            "messages": [{"role": "system", "content": interp_sys}, {"role": "user", "content": interp_user}],
                            "temperature": 0.2
                        }
                        
                        res_interp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload_interp, timeout=15)
                        if res_interp.status_code == 200:
                            ai_answer = res_interp.json()["choices"][0]["message"]["content"].strip()
                            st.markdown("### 💡 Executive Insights")
                            st.info(ai_answer)
                            
                    conn.close()
                except Exception as e:
                    st.error(f"Error processing AI query: {e}")
