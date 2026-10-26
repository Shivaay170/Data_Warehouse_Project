# Viva Voce Examination Questions & Answers
## Subject: Data Warehousing & Data Mining (DWDM)
### Project: End-to-End Retail Data Warehouse with Data Mining and Analytics Dashboard

---

### Category 1: Data Warehouse Concepts & Dimensional Modeling

#### Q1. What is a Data Warehouse, and how does it differ from an Operational Database (OLTP)?
**Answer:**  
A **Data Warehouse (DW)** is a subject-oriented, integrated, time-variant, and non-volatile collection of data designed to support managerial decision-making (OLAP - Online Analytical Processing).  
- **OLTP (Online Transaction Processing):** Optimized for high-throughput, day-to-day atomic insert/update transactions, strictly normalized (3NF/BCNF) to prevent anomalies.
- **OLAP / Data Warehouse:** Optimized for complex analytical aggregations and read-heavy queries, de-normalized into star or snowflake dimensional schemas.

#### Q2. What is a Star Schema, and why did you choose it over a Snowflake Schema?
**Answer:**  
A **Star Schema** features a central Fact table directly connected to multiple de-normalized Dimension tables through foreign keys.  
- **Why chosen:**
  1. **Query Simplicity & Performance:** Analytical queries require fewer `JOIN` operations, executing significantly faster than deeply normalized snowflake hierarchies.
  2. **OLAP Cube Suitability:** Directly aligns with OLAP multidimensional indexing and slicing.
  3. **Industry Best Practice:** Standard dimensional modeling standard (Kimball methodology) for retail enterprise analytics.

#### Q3. What is the difference between Fact tables and Dimension tables?
**Answer:**  
- **Fact Table (`fact_sales`):** Contains quantitative, numerical, measurable metrics (e.g., `quantity`, `unit_price`, `total_amount`) and surrogate foreign keys referencing dimensions. Facts are additive across dimensions.
- **Dimension Tables (`dim_date`, `dim_customer`, `dim_product`, `dim_location`):** Contain qualitative, textual descriptive attributes providing context (the "who, what, when, where") for filtering, slicing, dicing, and grouping facts.

#### Q4. What is a Surrogate Key, and why is it preferred over Natural / Business Keys?
**Answer:**  
A **Surrogate Key** is an artificially generated, sequential integer primary key assigned during ETL that has no business meaning (e.g., `customer_key = 1, 2, 3...` instead of `customer_id = '12345'`).  
**Advantages:**
1. **Performance:** Integer joins are much faster and consume less memory and index space than alphanumeric string joins.
2. **Slowly Changing Dimensions (SCD):** Allows maintaining historical versions of customer or product attributes under the same natural key.
3. **Source System Decoupling:** Protects warehouse referential integrity if source systems change their natural key format.

#### Q5. What is a Conformed Dimension?
**Answer:**  
A dimension that has the exact same meaning, schema, and surrogate keys across multiple business processes or data marts (e.g., `dim_date` and `dim_customer` shared between sales, inventory, and marketing).

#### Q6. What is a Degenerate Dimension?
**Answer:**  
A dimension key stored directly inside the fact table without a separate dimension table because it has no additional descriptive attributes. In our project, `invoice_no` acts as a degenerate dimension linking all lines of a purchase transaction.

#### Q7. What are Additive, Semi-Additive, and Non-Additive Facts?
**Answer:**  
- **Additive:** Can be summed across all dimensions (e.g., `quantity`, `total_amount` in our `fact_sales`).
- **Semi-Additive:** Can be summed across some dimensions but not time (e.g., bank account balances, inventory stock levels).
- **Non-Additive:** Cannot be summed across any dimension (e.g., unit ratios, percentages, discounts).

---

### Category 2: ETL (Extract, Transform, Load) Pipeline

#### Q8. What is the role of the Staging Area in ETL?
**Answer:**  
The **Staging Area** is an intermediate storage buffer between the raw operational data sources and the production data warehouse. It prevents analytical ETL transformations from overloading operational source systems, enables schema validation, and allows restarting failed loads without re-extracting from raw sources.

#### Q9. Why did you remove records with missing Customer IDs in the Transform phase?
**Answer:**  
In our retail analytics warehouse, dimensions are customer-centric. Unregistered guest purchases without an identifiable customer cannot be attributed to customer lifetime value (CLV), RFM loyalty segmentation, cohort retention, or churn prediction. Removing them preserves strict referential integrity (`FOREIGN KEY`) with `dim_customer`. Furthermore, these excluded records are tracked in `reports/data_quality_report.json`.

#### Q10. What does ETL "Idempotency" mean, and how did you guarantee it?
**Answer:**  
An ETL pipeline is **idempotent** if executing it multiple times produces the exact same warehouse state as executing it once, without duplicating records or generating primary key collision errors.  
We achieved this by wrapping table truncation and dimension/fact re-population inside an atomic database transaction (`with engine.begin()`).

#### Q11. What is Surrogate Key Lookup during the Load phase?
**Answer:**  
During the transformation of sales facts, the raw transactional row only has natural keys (e.g., `CustomerID`, `StockCode`, `Country`). In the load phase, these natural keys are mapped to their respective surrogate keys (`customer_key`, `product_key`, `location_key`) previously inserted into the dimension tables before writing to `fact_sales`.

#### Q12. What is Data Reconciliation in Data Warehousing?
**Answer:**  
Reconciliation is an automated data auditing check verifying that no rows were dropped, duplicated, or corrupted between the staging area and the fact table:  
$$\text{Cleaned Staging Rows} == \text{Loaded Fact Rows}$$  
Our pipeline explicitly asserts this equality (`assert fact_count == len(df_cleaned)`).

---

### Category 3: OLAP Operations (Online Analytical Processing)

#### Q13. Explain the Roll-Up OLAP operation with an example from your project.
**Answer:**  
**Roll-up** performs aggregation along a dimension hierarchy, reducing granularity. In our system, time rolls up from **Daily $\rightarrow$ Monthly $\rightarrow$ Quarterly $\rightarrow$ Yearly** revenue totals.

#### Q14. Explain the Drill-Down OLAP operation with an example from your project.
**Answer:**  
**Drill-down** is the inverse of roll-up; it navigates from summary data to detailed data by stepping down a hierarchy. For instance, drilling down into **Year 2024 $\rightarrow$ Q1 $\rightarrow$ January, February, March** to analyze monthly variances.

#### Q15. Differentiate between Slice and Dice operations.
**Answer:**  
- **Slice:** Filters the data cube along **one** specific dimension coordinate (e.g., Sales where `Country = 'United Kingdom'`).
- **Dice:** Filters the data cube along **multiple** dimensions simultaneously, forming a sub-cube (e.g., Sales where `Country IN ('UK', 'Germany')` **AND** `Category IN ('Kitchen & Dining', 'Home Decor')` **AND** `Quarter IN (3, 4)`).

#### Q16. What is the Pivot (Rotate) operation in OLAP?
**Answer:**  
**Pivot** rotates the coordinate axes in multidimensional space to view cross-tabulated data. In our project, rows represent `Product Category` while columns represent `Calendar Months (Jan-Dec)`, providing a monthly category revenue matrix.

#### Q17. What are MOLAP, ROLAP, and HOLAP?
**Answer:**  
- **MOLAP (Multidimensional OLAP):** Stores data in pre-aggregated, proprietary multidimensional arrays/cubes (fastest query response, higher storage).
- **ROLAP (Relational OLAP):** Executes multidimensional queries directly against relational tables (Star/Snowflake schema) via SQL aggregations (our project's architecture).
- **HOLAP (Hybrid OLAP):** Combines ROLAP for detailed transactional rows and MOLAP for pre-aggregated summaries.

---

### Category 4: Customer Segmentation (K-Means Clustering)

#### Q18. What is RFM Analysis, and why is it used?
**Answer:**  
RFM is a behavioral customer segmentation framework:
- **Recency (R):** Days since the customer's last purchase (lower is better).
- **Frequency (F):** Total number of distinct orders placed (higher is better).
- **Monetary (M):** Total cumulative spending ($) (higher is better).  
It provides empirical numerical representations of customer loyalty without requiring subjective surveys.

#### Q19. How does the K-Means clustering algorithm work?
**Answer:**  
1. Choose $k$ initial centroids randomly or via K-Means++.
2. Assign each data point to its nearest centroid using Euclidean distance.
3. Recompute centroids as the mean of all points assigned to that cluster.
4. Repeat steps 2 and 3 until centroids converge (within-cluster sum of squares is minimized).

#### Q20. How did you determine the optimal number of clusters $k$?
**Answer:**  
We evaluated $k \in [2, 7]$ using two complementary methods:
1. **Elbow Method:** Plots Inertia (Within-Cluster Sum of Squares) against $k$; optimal $k$ lies at the point where the rate of decrease abruptly slows.
2. **Silhouette Coefficient:** Measures how close each point is to its own cluster versus the nearest neighboring cluster (values range from -1 to +1; higher indicates denser, well-separated clusters).

#### Q21. Why is feature scaling essential before running K-Means?
**Answer:**  
K-Means calculates Euclidean distance:  
$$d(p, q) = \sqrt{\sum (p_i - q_i)^2}$$  
If Monetary spend ($50 - $5,000) is unscaled, its large variance will dominate Recency (1 - 365 days) and Frequency (1 - 30 orders), making the algorithm ignore frequency and recency. Log transformation and `StandardScaler` ensure all features contribute equally.

#### Q22. Why did you use PCA (Principal Component Analysis) in segmentation?
**Answer:**  
RFM exists in 3-dimensional space. PCA projects these correlated dimensions onto 2 orthogonal principal components capturing >90% of the total variance, allowing clear 2D scatter visualization of customer clusters.

---

### Category 5: Market Basket Analysis (Association Rule Mining)

#### Q23. Define Support, Confidence, and Lift.
**Answer:**  
For an association rule $A \Rightarrow B$:
- **Support:** Probability that a transaction contains both itemsets $A$ and $B$:  
  $$\text{Support}(A \Rightarrow B) = \frac{\text{Count}(A \cup B)}{\text{Total Transactions}}$$
- **Confidence:** Conditional probability that itemset $B$ is purchased given that itemset $A$ is purchased:  
  $$\text{Confidence}(A \Rightarrow B) = \frac{\text{Support}(A \cup B)}{\text{Support}(A)}$$
- **Lift:** Ratio of observed joint probability to expected probability under statistical independence:  
  $$\text{Lift}(A \Rightarrow B) = \frac{\text{Confidence}(A \Rightarrow B)}{\text{Support}(B)} = \frac{P(A \cap B)}{P(A) \cdot P(B)}$$

#### Q24. What does a Lift value greater than 1 signify?
**Answer:**  
- **Lift > 1:** Positive association; purchase of item $A$ significantly increases the likelihood of purchasing item $B$.
- **Lift = 1:** Statistical independence; items $A$ and $B$ occur together purely by random chance.
- **Lift < 1:** Negative association; purchase of item $A$ decreases the likelihood of purchasing item $B$ (substitutes).

#### Q25. Compare the Apriori and FP-Growth algorithms.
**Answer:**  
- **Apriori:** Uses the downward-closure (anti-monotonic) property to generate candidate itemsets level-by-level ($L_1 \rightarrow C_2 \rightarrow L_2 \dots$). Requires multiple full passes over the database, incurring high I/O cost.
- **FP-Growth (Frequent Pattern Growth):** Builds a compressed in-memory FP-Tree using only 2 passes over the database. Mines frequent patterns recursively by conditional pattern bases without generating candidate itemsets. It is substantially faster on dense transactional data.

#### Q26. What is the Apriori Property (Downward Closure)?
**Answer:**  
"All non-empty subsets of a frequent itemset must also be frequent." Conversely, if an itemset is infrequent, all of its supersets will also be infrequent and can be pruned immediately without candidate testing.

---

### Category 6: Churn Prediction & Machine Learning

#### Q27. How was Customer Churn defined in this project?
**Answer:**  
A customer is classified as **Churned (`churn = 1`)** if they have placed no orders within the last **90 days** relative to the warehouse's reference date; otherwise, they are classified as **Retained (`churn = 0`)**.

#### Q28. What features were engineered for the churn prediction models?
**Answer:**  
1. `order_count`: Total transaction frequency
2. `total_spend`: Cumulative lifetime monetary spend ($)
3. `avg_order_value`: Average spend per invoice ($)
4. `total_units`: Total volume of items purchased
5. `avg_units_per_order`: Average basket size
6. `unique_products`: Variety of distinct catalog items purchased
7. `tenure_days`: Lifespan from first order to reference date
8. `purchase_interval`: Average days between repeat transactions

#### Q29. Why is Accuracy alone an inadequate evaluation metric for churn?
**Answer:**  
In highly imbalanced datasets (e.g., 95% retained, 5% churned), a naive model predicting "Retained" for all customers achieves 95% accuracy while identifying zero churners. Therefore, **Precision, Recall, F1-Score, and ROC-AUC** are necessary to assess true positive capture and false alarm trade-offs.

#### Q30. What is the difference between Precision and Recall?
**Answer:**  
- **Precision:** Of all customers predicted as churners, what fraction actually churned?  
  $$\text{Precision} = \frac{TP}{TP + FP}$$
- **Recall:** Of all actual churners, what fraction did the model successfully detect?  
  $$\text{Recall} = \frac{TP}{TP + FN}$$

#### Q31. What is an ROC Curve and what does ROC-AUC measure?
**Answer:**  
- **ROC Curve (Receiver Operating Characteristic):** Plots True Positive Rate (Recall) against False Positive Rate ($1 - \text{Specificity}$) across all classification thresholds.
- **ROC-AUC (Area Under the Curve):** Measures the probability that the classifier ranks a randomly chosen churned customer higher than a randomly chosen retained customer. AUC = 1.0 represents a perfect classifier; AUC = 0.5 is random guessing.

#### Q32. What is Class Imbalance, and how did you mitigate it?
**Answer:**  
Class imbalance occurs when one target class significantly outnumbers the other. We mitigated it by setting `class_weight='balanced'` in scikit-learn models (which automatically adjusts weights inversely proportional to class frequencies) and employing stratified train-test splits.

#### Q33. What is Overfitting, and how can it be prevented in Random Forests and Decision Trees?
**Answer:**  
**Overfitting** occurs when a model memorizes noise and specifics of training data, failing to generalize to unseen data.  
**Prevention techniques:**
1. Constraining tree depth (`max_depth=5` or `6`).
2. Setting minimum samples per leaf (`min_samples_leaf`).
3. Using ensemble averaging (Random Forest aggregating 100 decorrelated trees with bootstrap sampling).
4. Evaluating performance on a distinct test holdout set.

---

### Category 7: Sales Forecasting & System Architecture

#### Q34. How did you validate your monthly sales forecasting model?
**Answer:**  
We employed **Out-of-Time Holdout Backtesting**: the model was trained on the first 20 historical months and evaluated against the remaining 4 holdout months using **Mean Absolute Error (MAE)** and **Root Mean Squared Error (RMSE)** before re-fitting on the full historical series to forecast the next 6 future months.

#### Q35. How can this warehouse scale from local SQLite to enterprise cloud scale?
**Answer:**  
Because database interactions are abstracted via SQLAlchemy ORM / Core connection engines, the entire pipeline is database-agnostic. Switching to an enterprise database like **PostgreSQL, Snowflake, or AWS Redshift** requires solely modifying the `DB_URL` environment variable in `.env` without modifying any ETL, OLAP, or machine learning application code.
