# 📊 Enterprise Applied AI Analyst Portal

An end-to-end AI-powered business analytics workspace featuring automated database population, customer segmentation machine learning pipelines, LLM-powered narrative generation, an interactive executive React web dashboard, and full **Streamlit Cloud** support.

---

## 🌟 Key Features

1. **Streamlit App (`streamlit_app.py`)**:
   - Ready for **Streamlit Cloud Deployment** (`share.streamlit.io`).
   - Features Executive Overview, ML Customer Segmentation charts, live SQL Explorer, and an AI Business Analyst Copilot powered by Groq Llama 3.3.

2. **Synthetic Business Database Generator (`generate_db.py`)**:
   - Generates realistic transactional, customer demographic, and web activity data stored in a relational SQLite database (`analytics.db`).

3. **Machine Learning Analytics Engine (`analytics_engine.py`)**:
   - Performs feature engineering (RFM metrics + web engagement indicators).
   - Clusters customers into distinct behavioral segments using **Scikit-Learn K-Means Clustering**.

4. **AI Narrative & Executive Report Generator (`ai_narrator.py`)**:
   - Uses the **Groq Llama 3.3 70B** model to analyze statistical segment profiles and construct executive business reports.

5. **FastAPI & React Dashboard (`app.py` & `frontend/`)**:
   - Production FastAPI backend serving endpoints and compiled React static dashboard assets.

---

## 🚀 Streamlit Cloud Deployment (1-Click)

1. Push this repository to GitHub.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and click **"New app"**.
3. Select your repository: `Mahatvasingh/applied-ai-business-intelligence-hub`.
4. Set **Main file path** to: `streamlit_app.py`.
5. Under **Advanced settings** -> **Secrets**, add your Groq API key:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   ```
6. Click **Deploy!** 🎉

---

## 💻 Running Streamlit Locally

To run the Streamlit app on your computer:

```bash
streamlit run streamlit_app.py
```

---

## 🛠 Local Setup & Pipeline Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Run ML & Data Pipeline
python generate_db.py
python analytics_engine.py
python ai_narrator.py

# Run FastAPI + React Backend Server
python app.py
```
