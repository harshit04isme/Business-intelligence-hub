# Executive Customer Insights & Segmentation Report

## Executive Summary
This report analyzes a customer base of **1000** active customers over a 6-month historical window. By integrating demographic variables (Age, Income) with web log metrics (Session Duration, Pages Viewed) and purchase metrics (Recency, Frequency, Monetary Value), an unsupervised K-Means clustering algorithm identified **four (4) distinct customer segments**. 

These segments reveal clear customer behavioral archetypes, ranging from highly engaged digital browsers to high-value VIP shoppers and churning customers. Establishing target campaigns for these behaviors yields substantial opportunities to lift customer lifetime value, optimize marketing return on investment, and proactively prevent churn.

---

## Segment Analysis

### Segment 0: Churn Risk / Lapsed Customers
* **Descriptive Persona**: *Lapsed Casual Buyers*
* **Segment Size**: 92 customers (9.2% of customer base)
* **Demographic Profile**: Avg Age 39.5 years | Avg Income $67,945.60
* **Behavioral & Web Profile**: 
  * **Recency**: 107.3 days (Inactive for over 3 months)
  * **Frequency**: 2.4 purchases in 6 months
  * **Spend**: $202.73 total spent
  * **Digital Engagement**: 468.0 seconds duration | 5.2 pages/session
* **Analysis**: This segment contains mature, middle-income customers who have become disengaged. Their purchase frequency is extremely low, and they have not made a purchase index of over 100 days. While their browsing sessions are moderate, they are not converting.

---

### Segment 1: Digitally Enthusiastic Core (Gen Z / Millennial Browsers)
* **Descriptive Persona**: *Digital-First Impulse Buyers*
* **Segment Size**: 259 customers (25.9% of customer base)
* **Demographic Profile**: Avg Age 23.7 years | Avg Income $46,758.16
* **Behavioral & Web Profile**: 
  * **Recency**: 20.1 days (Highly active recently)
  * **Frequency**: 6.9 purchases in 6 months
  * **Spend**: $344.49 total spent
  * **Digital Engagement**: 685.2 seconds duration | 8.0 pages/session
* **Analysis**: Representing young, tech-savvy buyers with lower incomes, this cluster features the highest digital session length and pages viewed (8.0 pages/session). They buy frequently, but their average transaction size is small.

---

### Segment 2: VIP Premium Spenders
* **Descriptive Persona**: *High-Value Brand Advocates*
* **Segment Size**: 260 customers (26.0% of customer base)
* **Demographic Profile**: Avg Age 42.7 years | Avg Income $70,264.52
* **Behavioral & Web Profile**: 
  * **Recency**: 17.4 days (Recent transactions)
  * **Frequency**: 7.2 purchases in 6 months
  * **Spend**: $627.55 total spent (Highest group spend)
  * **Digital Engagement**: 457.3 seconds duration | 4.9 pages/session
* **Analysis**: The most valuable customer segment. These are high-earning, mature customers who spend heavily ($627.55 average total spend) and buy frequently, despite spending less time page-browsing. They are highly transactional, high-intent brand champions.

---

### Segment 3: Steady Standard Shoppers
* **Descriptive Persona**: *Consistent Household Buyers*
* **Segment Size**: 389 customers (38.9% of customer base)
* **Demographic Profile**: Avg Age 43.5 years | Avg Income $70,335.72
* **Behavioral & Web Profile**: 
  * **Recency**: 23.3 days (Moderate activity)
  * **Frequency**: 3.9 purchases in 6 months
  * **Spend**: $312.52 total spent
  * **Digital Engagement**: 467.1 seconds duration | 5.0 pages/session
* **Analysis**: This is the largest segment of the customer base. They represent the standard customer with average incomes, moderate frequency, and steady spend, forming the stable baseline revenue of the business.

---

## Actionable Business Recommendations

### Recommendations for Segment 0 (Lapsed Casual Buyers)
1. **Re-engagement Email Campaigns**: Deploy direct Win-Back email promotions with high-discount incentives (e.g., 'We Miss You: Get 25% Off Your Next Order') targeted at their historic purchase categories.
2. **Web Session Exit Polls**: Set up triggered surveys when these users return to detect price sensitivity or friction points.
3. **Tailored Remarketing**: Run paid retargeting ads on social channels displaying low-price entry items to lower the hurdle for a second trial.

### Recommendations for Segment 1 (Digital-First Impulse Buyers)
1. **Flash Sales & In-App Gamification**: Since they browse frequently, introduce loyalty points or app-exclusive time-bound sales to increase conversion rates.
2. **Product Bundling**: Offer 'Buy More, Save More' bundles (e.g., combining Apparel and Books) to increase their low average order value.
3. **Social Commerce Targeting**: Focus marketing efforts on channels like Instagram or TikTok, displaying curated lifestyle collections.

### Recommendations for Segment 2 (High-Value Brand Advocates)
1. **VIP Loyalty Tier**: Grant exclusive access to early product launches, free express shipping, and a dedicated VIP support helpline.
2. **Subscription/Premium Tier Upsell**: Pitch subscription-based loyalty models to lock in recurring revenue from high-spending patterns.
3. **Referral Reward Program**: Incentivize these loyal advocates to refer peers by offering premium tier bonuses.

### Recommendations for Segment 3 (Consistent Household Buyers)
1. **Tiered Spend Promotions**: Encourage higher purchase order sizes by offering thresholds (e.g., 'Free shipping on orders over $75' or '$10 off $100').
2. **Cross-Category Recommendations**: Use transaction history to cross-sell recommendations (e.g., Groceries buyers recommended with kitchen/Home products).
3. **Quarterly Loyalty Reviews**: Send points updates and loyalty check-ins to build stronger retention bonds.

---

## Power BI Visualization Guide

### Relational Schema Blueprint
To build interactive tracking dashboards in Power BI, developers can connect directly to the SQLite `analytics.db` database. The `customer_segments` table acts as the unified analytics view. 

#### Schema Setup:
* **Table Relations (1-to-Many)**:
  * Connect `customers.customer_id` (1) to `customer_segments.customer_id` (1) - *1:1 Relationship (or Join logically)*.
  * Connect `customer_segments.customer_id` (1) to `transactions.customer_id` (Many) - *Active Cross-Filtering*.
  * Connect `customer_segments.customer_id` (1) to `web_logs.customer_id` (Many) - *Active Cross-Filtering*.

#### Recommended Visualizations:
* **Cluster Overview Card**: Cluster Segment Selector as a Slicing filter.
* **Demographic Scatter Plot**: Age (X-axis) vs. Income (Y-axis) colored by `cluster_id`.
* **Value Bubble Chart**: Average Recency (X-axis) vs. Average Frequency (Y-axis), with size represented by Average Monetary Spent, showing the distinct positions of VIP Spenders (high-frequency, low-recency, large size) vs. Lapsed Buyers (high-recency, low-frequency, small size).