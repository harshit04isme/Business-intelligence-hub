import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def run_analytics():
    db_name = "analytics.db"
    conn = sqlite3.connect(db_name)
    
    print("Loading data from database...")
    # Load raw data
    customers_df = pd.read_sql_query("SELECT * FROM customers;", conn)
    transactions_df = pd.read_sql_query("SELECT * FROM transactions;", conn)
    web_logs_df = pd.read_sql_query("SELECT * FROM web_logs;", conn)

    # 1. Feature Engineering
    print("Engineering metrics...")
    
    # End date of the 6-month window is 2026-07-20
    end_date = pd.to_datetime("2026-07-20")
    transactions_df["transaction_date"] = pd.to_datetime(transactions_df["transaction_date"])
    web_logs_df["session_date"] = pd.to_datetime(web_logs_df["session_date"])
    
    # Calculate RFM per customer
    # Recency: days since last transaction relative to end_date
    recency_s = transactions_df.groupby("customer_id")["transaction_date"].max()
    recency_days = (end_date - recency_s).dt.days
    
    # Frequency: transaction count
    frequency_count = transactions_df.groupby("customer_id")["transaction_id"].count()
    
    # Monetary: sum of amounts
    monetary_sum = transactions_df.groupby("customer_id")["amount"].sum()
    
    # Web behavior
    web_metrics = web_logs_df.groupby("customer_id").agg(
        avg_session_duration=("session_duration", "mean"),
        avg_pages_viewed=("pages_viewed", "mean")
    )
    
    # Construct base customer profile for Power BI structure
    features_df = customers_df.copy()
    features_df = features_df.merge(recency_days.rename("recency"), on="customer_id", how="left")
    features_df = features_df.merge(frequency_count.rename("frequency"), on="customer_id", how="left")
    features_df = features_df.merge(monetary_sum.rename("monetary"), on="customer_id", how="left")
    features_df = features_df.merge(web_metrics, on="customer_id", how="left")
    
    # Handle missing values for customers with no transactions or web logs
    features_df["recency"] = features_df["recency"].fillna(180.0) # max window length
    features_df["frequency"] = features_df["frequency"].fillna(0).astype(int)
    features_df["monetary"] = features_df["monetary"].fillna(0.0)
    features_df["avg_session_duration"] = features_df["avg_session_duration"].fillna(0.0)
    features_df["avg_pages_viewed"] = features_df["avg_pages_viewed"].fillna(0.0)
    
    # 2. Preprocess & Scaling
    print("Normalizing features for clustering...")
    cluster_features = ["age", "income", "recency", "frequency", "monetary", "avg_session_duration", "avg_pages_viewed"]
    X = features_df[cluster_features].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 3. Determine Optimal K (Silhouette score check for k in [3, 4, 5])
    print("Determining optimal cluster size K...")
    k_candidates = [3, 4, 5]
    best_k = 3
    best_score = -1
    silhouette_scores = {}
    
    for k in k_candidates:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_scores[k] = score
        print(f" - K = {k}: Silhouette Score = {score:.4f}")
        if score > best_score:
            best_score = score
            best_k = k
            
    print(f"Optimal cluster count identified: K = {best_k} (Silhouette = {best_score:.4f})")
    
    # 4. Final KMeans fitting
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    features_df["cluster_id"] = kmeans.fit_predict(X_scaled)
    
    # Map cluster IDs to descriptive segment labels
    persona_map = {
        0: "Segment 0 - Lapsed Buyers",
        1: "Segment 1 - Digital Browsers",
        2: "Segment 2 - VIP Spenders",
        3: "Segment 3 - Steady Shoppers"
    }
    features_df["segment_label"] = features_df["cluster_id"].map(lambda cid: persona_map.get(cid, f"Segment {cid}"))
    
    # Profile clusters
    print("\n--- Profile of Segmented Customer Clusters ---")
    profiles = features_df.groupby("cluster_id").agg(
        customer_count=("customer_id", "count"),
        avg_age=("age", "mean"),
        avg_income=("income", "mean"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        avg_session_dur=("avg_session_duration", "mean"),
        avg_pages=("avg_pages_viewed", "mean")
    ).reset_index()
    
    for _, row in profiles.iterrows():
        print(f"\nCluster {int(row['cluster_id'])} (Count: {int(row['customer_count'])}):")
        print(f" - Avg Age: {row['avg_age']:.1f} years")
        print(f" - Avg Income: ${row['avg_income']:,.2f}")
        print(f" - Recency: {row['avg_recency']:.1f} days since last purchase")
        print(f" - Frequency: {row['avg_frequency']:.1f} purchases in 6mo")
        print(f" - Spend (monetary): ${row['avg_monetary']:,.2f} total")
        print(f" - Session Duration: {row['avg_session_dur']:.1f} seconds")
        print(f" - Pages Viewed: {row['avg_pages']:.1f} pages/session")
        
    # 5. Save back to SQL table `customer_segments`
    print("\nWriting segmented data to 'customer_segments' table in local DB...")
    
    # Drop existing segments table
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS customer_segments;")
    conn.commit()
    
    # Save the dataframe
    features_df.to_sql("customer_segments", conn, index=False, if_exists="replace")
    
    # Verify the table schema
    print("Table 'customer_segments' successfully created and populated.")
    
    conn.close()

if __name__ == "__main__":
    run_analytics()
