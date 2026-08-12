import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_mock_data():
    db_name = "analytics.db"
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS web_logs;")
    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS customers;")

    # 1. Create tables
    print("Creating database schema...")
    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            signup_date TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            income INTEGER NOT NULL,
            region TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE web_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            session_duration INTEGER NOT NULL,
            pages_viewed INTEGER NOT NULL,
            channel TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """)

    # Parameters
    num_customers = 1000
    end_date = datetime(2026, 7, 20)  # Current project time relative
    start_date = end_date - timedelta(days=180)  # 6 months window

    # 2. Populate Customers
    print(f"Generating demographic data for {num_customers} customers...")
    regions = ["North", "South", "East", "West"]
    genders = ["Male", "Female", "Non-binary"]
    gender_weights = [0.48, 0.48, 0.04]

    customer_list = []
    for c_id in range(1, num_customers + 1):
        # Age distribution: skewed towards 25-45, range 18-75
        age = int(np.clip(np.random.normal(38, 12), 18, 75))
        
        # Income distribution: correlated with age to make it realistic
        base_income = 40000 + (age - 18) * 1200
        income = int(np.clip(np.random.normal(base_income, 18000), 20000, 160000))
        
        # Region and Gender
        region = np.random.choice(regions)
        gender = np.random.choice(genders, p=gender_weights)
        
        # Signup date: uniform across the last 18 months, ensuring they had time to buy
        signup_offset = random.randint(0, 540)
        c_signup_date = (end_date - timedelta(days=signup_offset)).strftime("%Y-%m-%d")

        customer_list.append((c_id, c_signup_date, age, gender, income, region))

    cursor.executemany("""
        INSERT INTO customers (customer_id, signup_date, age, gender, income, region)
        VALUES (?, ?, ?, ?, ?, ?);
    """, customer_list)

    # 3. Populate Transactions (6-month active window)
    print("Generating simulated purchases...")
    categories = ["Electronics", "Apparel", "Home", "Groceries", "Books"]
    cat_probs = [0.15, 0.30, 0.20, 0.25, 0.10]
    
    transaction_list = []
    
    # We create segments implicitly so K-Means can find something rich:
    # Segment A: High income, older age -> high spend, low frequency (Electronics/Home)
    # Segment B: Young, mid income -> high frequency, low spend (Books/Apparel)
    # Segment C: Average income, variable -> regular shopping (Groceries)
    
    for c_id, signup_d_str, age, gender, income, region in customer_list:
        signup_dt = datetime.strptime(signup_d_str, "%Y-%m-%d")
        # Activity window starts at max(start_date, signup_date)
        trans_start_dt = max(start_date, signup_dt)
        days_active = (end_date - trans_start_dt).days
        
        if days_active <= 0:
            continue
            
        # Determine behavior profile
        if income > 90000 and age > 35:
            # High spend, fewer transactions
            num_trans = np.random.poisson(3)
            spend_mean = 180.0
            spend_std = 70.0
        elif age < 30 and income < 50000:
            # High frequency, low spend
            num_trans = np.random.poisson(8)
            spend_mean = 35.0
            spend_std = 12.0
        else:
            # Average profile
            num_trans = np.random.poisson(5)
            spend_mean = 75.0
            spend_std = 25.0

        for _ in range(num_trans):
            offset = random.randint(0, days_active)
            t_date = (trans_start_dt + timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S")
            amount = round(float(np.clip(np.random.normal(spend_mean, spend_std), 5.0, 1500.0)), 2)
            category = np.random.choice(categories, p=cat_probs)
            
            transaction_list.append((c_id, t_date, amount, category))

    cursor.executemany("""
        INSERT INTO transactions (customer_id, transaction_date, amount, category)
        VALUES (?, ?, ?, ?);
    """, transaction_list)

    # 4. Populate Web Sessions
    print("Generating digital footprint (web sessions)...")
    channels = ["Direct", "Organic Search", "Paid Search", "Social Media", "Email"]
    chan_probs = [0.20, 0.35, 0.15, 0.20, 0.10]

    web_logs_list = []
    
    for c_id, signup_d_str, age, gender, income, region in customer_list:
        signup_dt = datetime.strptime(signup_d_str, "%Y-%m-%d")
        session_start_dt = max(start_date, signup_dt)
        days_active = (end_date - session_start_dt).days
        
        if days_active <= 0:
            continue

        # Session count depends on purchase affinity
        if age < 30:
            # Tech-savvy young browser
            num_sessions = np.random.poisson(15)
            dur_mean = 450.0  # seconds
            page_mean = 8.0
        elif income > 90000:
            # High income, focused browser
            num_sessions = np.random.poisson(10)
            dur_mean = 280.0
            page_mean = 4.5
        else:
            # Average frequency
            num_sessions = np.random.poisson(8)
            dur_mean = 320.0
            page_mean = 5.2

        for _ in range(num_sessions):
            offset = random.randint(0, days_active)
            s_date = (session_start_dt + timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Session duration correlates with pages viewed
            pages = int(np.clip(np.random.poisson(page_mean), 1, 35))
            duration = int(np.clip(np.random.normal(dur_mean + pages * 30, dur_mean * 0.4), 10, 7200))
            channel = np.random.choice(channels, p=chan_probs)

            web_logs_list.append((c_id, s_date, duration, pages, channel))

    cursor.executemany("""
        INSERT INTO web_logs (customer_id, session_date, session_duration, pages_viewed, channel)
        VALUES (?, ?, ?, ?, ?);
    """, web_logs_list)

    # Commit changes and close
    conn.commit()
    
    # Print row count verification
    cursor.execute("SELECT COUNT(*) FROM customers;")
    c_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions;")
    t_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM web_logs;")
    w_count = cursor.fetchone()[0]

    conn.close()

    print(f"Database generation complete! File: '{db_name}'.")
    print(f"Summary of entries created:")
    print(f" - Customers: {c_count}")
    print(f" - Transactions: {t_count}")
    print(f" - Web Logs: {w_count}")

if __name__ == "__main__":
    generate_mock_data()
