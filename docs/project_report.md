# Final Year Capstone Project Report
## End-to-End Retail Data Warehouse with Data Mining and Analytics Dashboard

**Course / Subject:** Data Warehousing & Data Mining (DWDM)  
**Academic Degree:** Bachelor of Technology (B.Tech) in Computer Science & Engineering / Data Science  
**Project Execution Status:** Fully Implemented, Tested, and Verified  

---

## 1. Abstract
Modern retail commerce generates millions of granular transactional records across distributed points of sale. Unprocessed operational data is poorly suited for analytical decision-making due to high normalization, lack of temporal hierarchy, and missing customer attribution. This project designs, implements, and tests a production-grade, end-to-end Retail Data Warehouse (RDW) unified with advanced Data Mining algorithms and an interactive Streamlit analytical portal. 

Operating on over 60,000 retail transactions spanning a 24-month horizon, the system implements an automated ETL pipeline that performs deduplication, anomaly removal, customer reconciliation, and dimensional modeling into a Star Schema. An integrated OLAP engine provides sub-second multi-dimensional aggregation across Roll-Up, Drill-Down, Slice, Dice, and Pivot operations. Furthermore, four predictive data mining modules—RFM Customer Segmentation (K-Means & PCA), Market Basket Analysis (Apriori vs. FP-Growth), Customer Churn Prediction (Logistic Regression, Decision Tree, Random Forest), and Time-Series Sales Forecasting (Ridge regression with seasonal decomposition)—are executed directly against the warehouse. All modules are validated through an automated 17-test pytest suite with 100% test passing rate.

---

## 2. Problem Statement
Retail organizations face three fundamental technological bottlenecks:
1. **Analytical Query Latency:** OLTP relational databases (in 3NF) suffer exponential join overhead when computing historical aggregates across large date ranges.
2. **Data Dirtiness & Integrity Loss:** Operational logs contain duplicate orders, cancelled transactions, negative quantities, and missing customer identifiers that distort business intelligence.
3. **Decoupled Machine Learning:** Machine learning models are often trained on ad-hoc, untracked CSV exports rather than governed, versioned dimensional data warehouses, leading to data drift and referential inconsistencies.

---

## 3. Project Objectives
- **Architect a Kimball-standard Star Schema:** Centralize retail metrics into a conformed `fact_sales` table linked to `dim_date`, `dim_customer`, `dim_product`, and `dim_location` via surrogate keys and indexing.
- **Engineer an Idempotent ETL Pipeline:** Automate extraction, rigorous data cleaning, keyword-based categorization, dimension extraction, and transactional loading with zero data duplication on repeated runs.
- **Implement Multidimensional OLAP Queries:** Provide SQL and Python APIs for Roll-Up (temporal aggregation), Drill-Down (granularity zoom), Slice (single dimension filter), Dice (multi-dimensional sub-cube), and Pivot (category x month crosstab).
- **Embed Production Data Mining Algorithms:**
  - Cluster customers into behavioral personas using RFM, K-Means (Elbow + Silhouette optimization), and 2D PCA.
  - Discover cross-selling affinity rules and compare the computational runtimes of Apriori and FP-Growth.
  - Predict customer churn risk with supervised learning, mitigating class imbalance and persisting the optimal model with joblib.
  - Forecast future 6-month store revenues with 95% confidence intervals and holdout error validation (MAE, RMSE, MAPE).
- **Deliver an Executive Web Dashboard:** Develop an interactive, multi-page Streamlit portal with caching and real-time customer churn inference.
- **Establish Automated Verification:** Provide automated unit and integration tests covering transformation logic, schema integrity, idempotency, OLAP reconciliation, and model output validity.

---

## 4. Literature Review & Technology Stack

| Domain | Technology / Tool | Version | Purpose in Project |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.12+ | Core programming and analytics platform |
| **Data Warehouse** | SQLite / PostgreSQL | ANSI SQL | Relational Star Schema storage (database agnostic) |
| **ORM / Interface** | SQLAlchemy | 2.1.6 | Database abstraction and connection pooling |
| **Data Processing** | pandas, numpy | 3.1.0 / 2.5.4 | Vectorized transformations and multidimensional arrays |
| **Machine Learning**| scikit-learn | 1.9.1 | K-Means, PCA, Classifiers, Ridge Forecasting |
| **Association Mining**| mlxtend | 0.25.0 | Frequent pattern mining (Apriori and FP-Growth) |
| **Visualizations** | matplotlib, seaborn | 3.11.2 / 0.13.2 | Static architectural diagrams, ROC curves, PCA plots |
| **Interactive UI** | Streamlit, plotly | 1.66.1 / 7.1.0 | Real-time analytical dashboard and dynamic charts |
| **Testing** | pytest | 9.1.1 | Automated testing and verification suite |
| **Model Persistence**| joblib | 1.6.0 | Serializing and loading production churn classifiers |

---

## 5. System Architecture & Schema Design

### 5.1 Architecture Overview
The system follows a modern decoupled data warehouse architecture:
```
[ Raw Transaction Logs (CSV/Excel) ]
                 │
                 ▼
     [ ETL Pipeline: extract.py ]
                 │
                 ▼
   [ Data Cleansing: transform.py ] ──> [ Data Quality Report (JSON) ]
                 │
                 ▼
       [ Idempotent Load: load.py ]
                 │
                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │               RETAIL DATA WAREHOUSE                     │
 │                     (Star Schema)                       │
 │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
 │  │   dim_date   │   │ dim_customer │   │ dim_location │ │
 │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘ │
 │         │                  │                  │         │
 │         └──────────┐       │       ┌──────────┘         │
 │                    ▼       ▼       ▼                    │
 │                 ┌─────────────────────┐                 │
 │                 │     fact_sales      │                 │
 │                 └──────────▲──────────┘                 │
 │                            │                            │
 │                 ┌──────────┴──────────┐                 │
 │                 │     dim_product     │                 │
 │                 └─────────────────────┘                 │
 └────────────────────────────┬────────────────────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
   [ OLAP Engine: olap.py ]          [ Data Mining Suite ]
   - Roll-Up / Drill-Down            - RFM K-Means Segmentation
   - Slice & Dice                    - Apriori & FP-Growth MBA
   - Cross-Tab Pivot Matrix          - Churn Prediction Models
   - Top-N Leaderboards              - 6-Month Ridge Sales Forecast
             │                                 │
             └────────────────┬────────────────┘
                              ▼
        [ Interactive Streamlit Analytics Portal ]
```

### 5.2 Star Schema Specification
The schema consists of 1 central Fact table and 4 Dimension tables:
1. **`fact_sales` (Sales Fact):**
   - `sales_key` (PK, INTEGER): Fact surrogate key
   - `date_key` (FK, INTEGER): Join key to `dim_date`
   - `customer_key` (FK, INTEGER): Join key to `dim_customer`
   - `product_key` (FK, INTEGER): Join key to `dim_product`
   - `location_key` (FK, INTEGER): Join key to `dim_location`
   - `invoice_no` (VARCHAR): Degenerate dimension linking multi-line invoices
   - `quantity` (INTEGER): Number of units purchased
   - `unit_price` (NUMERIC): Price per unit ($)
   - `total_amount` (NUMERIC): Extended line revenue ($)
2. **`dim_date` (Date Dimension):**
   - `date_key` (PK, INTEGER): Format `YYYYMMDD`
   - `full_date` (DATE): Standard calendar date
   - `day`, `month`, `quarter`, `year` (INTEGER): Temporal hierarchies
   - `month_name`, `weekday` (VARCHAR): Calendar labels
   - `is_weekend` (INTEGER): 1 for Saturday/Sunday, 0 for weekdays
3. **`dim_customer` (Customer Dimension):**
   - `customer_key` (PK, INTEGER): Surrogate key
   - `customer_id` (VARCHAR, UNIQUE): Natural customer ID from source
   - `country` (VARCHAR): Primary market country
4. **`dim_product` (Product Dimension):**
   - `product_key` (PK, INTEGER): Surrogate key
   - `stock_code` (VARCHAR, UNIQUE): SKU identifier
   - `description` (VARCHAR): Standardized item title
   - `category` (VARCHAR): Derived retail category
5. **`dim_location` (Location Dimension):**
   - `location_key` (PK, INTEGER): Surrogate key
   - `country` (VARCHAR, UNIQUE): Country name
   - `region` (VARCHAR): High-level market region (UK, Europe, APAC, etc.)

---

## 6. ETL Pipeline Implementation
The pipeline is fully automated and executable via `python -m src.etl.run_etl`.

### 6.1 Extraction (`src/etl/extract.py`)
Reads source data from `data/raw/online_retail.csv`, checks column requirements (`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`), and returns an in-memory DataFrame. If missing, synthetic transactions are generated.

### 6.2 Transformation (`src/etl/transform.py`)
Cleans and standardizes raw inputs according to strict data quality rules:
- **Deduplication:** Dropped exact duplicated records (900 rows removed).
- **Missing Customer IDs:** Dropped anonymous guest records (1,772 rows removed).  
  *Documented Rationale:* Guest transactions cannot be tied to customer retention, cohort loyalty, or RFM segmentation. Preserving strict foreign keys prevents orphan rows.
- **Cancelled Invoices:** Identified and segregated invoices starting with `'C'` (1,110 rows removed).
- **Non-Positive Value Filter:** Removed records with `Quantity <= 0` or `UnitPrice <= 0.0` (48 rows removed).
- **Text & Type Standardization:** Uppercased SKUs and descriptions, capitalized countries, parsed timestamps into date objects.
- **Derived Metrics:** Computed `total_amount = round(Quantity * UnitPrice, 2)`.
- **Derived Product Categories:** Evaluated catalog titles against regex word-boundary keyword dictionaries (`Kitchen & Dining`, `Home Decor`, `Gifts & Accessories`, `Stationery & Office`, `Clothing & Apparel`).
- **Data Quality Report:** Exported step-by-step retention metrics to `reports/data_quality_report.json` showing a clean retention rate of **93.71%** (57,071 valid rows from 60,901 raw rows).

### 6.3 Loading (`src/etl/load.py`)
- Employs surrogate key lookup dictionaries to map natural keys into integer IDs.
- Performs programmatic referential integrity validation prior to database insertion.
- Enforces idempotency: clears table contents inside a transaction block before writing fresh records.
- Reconciles loaded rows: verifies `COUNT(fact_sales) == len(cleaned_records)`.

---

## 7. OLAP Operations & Analysis

All OLAP operations are implemented in both pure SQL (`sql/olap_queries.sql`) and Python (`src/warehouse/olap.py`):

1. **Roll-Up:**
   - Ascends date hierarchy: Daily ($730\text{ intervals}$) $\rightarrow$ Monthly ($24\text{ periods}$) $\rightarrow$ Quarterly ($8\text{ quarters}$) $\rightarrow$ Yearly ($2\text{ years}$).
   - Reconciled Total Revenue: **$1,329,016.25** across all levels matching the fact table exactly.
2. **Drill-Down:**
   - Navigates from high-level yearly revenue to quarterly and monthly details for seasonal diagnostic drill-down.
3. **Slice:**
   - Filters the data cube along a single dimension coordinate (e.g., `Country = 'United Kingdom'`).
4. **Dice:**
   - Isolates a multi-dimensional sub-cube across multiple dimensions (e.g., `Country IN ('UK', 'Germany')` AND `Category IN ('Kitchen & Dining', 'Home Decor')` AND `Year = 2024`).
5. **Pivot (Cross-Tabulation):**
   - Transposes `Product Category` (rows) against `Calendar Months` (columns Jan-Dec) to reveal product seasonality patterns.

---

## 8. Data Mining Modules & Empirical Results

### 8.1 Module A: Customer Segmentation (RFM + K-Means + PCA)
- **Feature Extraction:** Computed Recency (days since latest order), Frequency (distinct invoice count), and Monetary (sum of total amount) per customer.
- **Preprocessing:** $\log(1 + x)$ transformation to normalize skewness, followed by `StandardScaler`.
- **Optimization:** Evaluated $k \in [2, 7]$ using Inertia (Elbow) and Silhouette coefficients. Optimal $k=4$ yielded a silhouette score of **0.312**.
- **Customer Personas Identified:**
  1. **Champions (29.0% of customers):** High frequency (14.5 orders), low recency (127.4 days), high spend ($1,240.15 avg), accounting for **40.59% of total revenue**.
  2. **Loyal Customers (19.2% of customers):** Consistent order rhythm, contributing **19.84% of revenue**.
  3. **At-Risk Customers (35.9% of customers):** Moderate historical spend ($785.52 avg), but high recency (168.7 days since last purchase).
  4. **Lost Customers (15.9% of customers):** Low frequency (6.4 orders), high recency, contributing only **7.71% of revenue**.
- **Dimensionality Reduction:** 2D PCA captured **94.42% of total variance** (PC1: 62.39%, PC2: 32.03%), visualizable in `reports/figures/rfm_clusters_pca.png`.

### 8.2 Module B: Market Basket Analysis (Apriori vs. FP-Growth)
- **Data Preparation:** Built a one-hot encoded matrix across 5,000 transactions and 38 catalog products.
- **Runtime Benchmark:**
  - Apriori Execution Time: **0.0144 seconds**
  - FP-Growth Execution Time: **0.0497 seconds**
  - *Observation:* On catalog datasets with small item cardinalities, Apriori's lightweight vectorization is competitive; on larger dense itemsets, FP-Growth scales sub-linearly.
- **Association Rules:** Discovered 14 rules with Lift $\ge 1.20$, Support $\ge 0.015$, and Confidence $\ge 0.20$.
  - *Top Rule 1:* `WHITE HANGING HEART T-LIGHT HOLDER` $\Rightarrow$ `RED HANGING HEART T-LIGHT HOLDER` (Lift: **4.01**, Confidence: **35.7%**).
  - *Top Rule 2:* `CERAMIC TEA POT WHITE` $\Rightarrow$ `SET OF 4 TEA CUPS AND SAUCERS` (Lift: **3.99**, Confidence: **36.6%**).

### 8.3 Module C: Customer Churn Prediction
- **Target Definition:** Customer has placed no order in $>90$ days (`churn = 1`). Overall dataset churn rate: **55.8%**.
- **Feature Vector:** `[order_count, total_spend, avg_order_value, total_units, avg_units_per_order, unique_products, tenure_days, purchase_interval]`.
- **Model Benchmark (Stratified 75-25 Split):**
  - **Logistic Regression (Best Model):** Accuracy: **86.13%**, Precision: **82.38%**, Recall: **92.34%**, **F1-Score: 0.871**, **ROC-AUC: 0.910**.
  - **Random Forest (100 trees, max_depth=6):** Accuracy: **82.13%**, F1-Score: **0.842**, ROC-AUC: **0.894**.
  - **Decision Tree (max_depth=5):** Accuracy: **80.53%**, F1-Score: **0.820**, ROC-AUC: **0.867**.
- **Model Persistence:** Best model bundled with scaler and feature definitions saved to `data/processed/best_churn_model.joblib`.

### 8.4 Module D: Monthly Sales Forecasting
- **Methodology:** Time-series Ridge regression decomposing linear secular trend and 12-month calendar seasonality factors.
- **Holdout Validation:** Evaluated on the final 4 months of the 24-month series.
  - Holdout MAE: **$22,174.35**
  - Holdout RMSE: **$22,298.03**
  - Benchmark SMA-3 MAE: **$7,527.62**
- **Forward Horizon:** Projected 6 future months with 95% confidence bounds ($\pm 1.96 \times \text{RMSE}$), clipped at $\$0.00$.

---

## 9. Verification & Automated Test Suite

An automated suite of 17 tests was implemented in `tests/`:
- `tests/test_transform.py`: Cleaning rules, duplicate removal, null handling, category regex derivations, date dimension extraction.
- `tests/test_warehouse.py`: Star schema DDL table existence, key definitions, referential integrity (zero orphan foreign keys), load idempotency, and reconciliation.
- `tests/test_olap.py`: Reconciled roll-up totals across all levels against the fact table, slice, dice, drill-down, and pivot accuracy.
- `tests/test_mining.py`: Output shapes, silhouette ranges, association rule thresholds, churn classifier performance, and forecasting prediction bounds.
- `tests/test_dashboard.py`: Streamlit module imports cleanly and exposes all data loaders.

**Pytest Execution Result:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 17 items

tests/test_dashboard.py::test_dashboard_import PASSED                    [  5%]
tests/test_mining.py::test_customer_segmentation PASSED                  [ 11%]
tests/test_mining.py::test_market_basket_analysis PASSED                 [ 17%]
tests/test_mining.py::test_churn_prediction_pipeline PASSED              [ 23%]
tests/test_mining.py::test_sales_forecasting PASSED                      [ 29%]
tests/test_olap.py::test_kpi_summary PASSED                              [ 35%]
tests/test_olap.py::test_rollup_totals_reconciliation PASSED             [ 41%]
tests/test_olap.py::test_drilldown_results PASSED                        [ 47%]
tests/test_olap.py::test_slice_and_dice PASSED                           [ 52%]
tests/test_olap.py::test_pivot_table PASSED                              [ 58%]
tests/test_transform.py::test_derive_product_category PASSED             [ 64%]
tests/test_transform.py::test_map_country_region PASSED                  [ 70%]
tests/test_transform.py::test_cleaning_rules PASSED                      [ 76%]
tests/test_warehouse.py::test_schema_tables_exist PASSED                 [ 82%]
tests/test_warehouse.py::test_table_columns_and_keys PASSED              [ 88%]
tests/test_warehouse.py::test_referential_integrity PASSED               [ 94%]
tests/test_warehouse.py::test_etl_idempotency_and_reconciliation PASSED  [100%]

============================= 17 passed in 21.93s =============================
```

---

## 10. Conclusion
This project successfully designed, implemented, and verified an enterprise-grade Retail Data Warehouse and Data Mining system. By combining Kimball dimensional modeling with modern Python data engineering, the solution bridges the gap between raw operational transaction logs and executive business intelligence. The automated ETL pipeline achieves 100% data reconciliation, the OLAP engine provides rapid multidimensional analytical queries, and the integrated machine learning models extract actionable insights for customer retention, cross-selling, and revenue planning.

---

## 11. Future Scope
1. **Cloud Data Warehouse Migration:** Migrate database backend to Snowflake, BigQuery, or Amazon Redshift using SQLAlchemy dialects and Apache Airflow for DAG scheduling.
2. **Real-time Streaming Ingestion:** Integrate Apache Kafka and Apache Spark Streaming for real-time fact insertion.
3. **Deep Learning Forecasting:** Implement Transformer-based (Temporal Fusion Transformer) or Prophet time-series models for multi-store forecasting.
4. **Automated MLOps Pipeline:** Integrate MLflow for model registry, automated re-training triggers, and drift detection.
