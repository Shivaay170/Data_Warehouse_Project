-- ====================================================================
-- OLAP QUERIES FOR RETAIL DATA WAREHOUSE (STAR SCHEMA)
-- Demonstrating Core OLAP Operations: Roll-up, Drill-down, Slice, Dice, Pivot
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. ROLL-UP OPERATION
-- Aggregates data by ascending through dimension hierarchies:
-- Daily -> Monthly -> Quarterly -> Yearly
-- --------------------------------------------------------------------

-- 1a. Yearly Revenue Roll-Up
SELECT 
    d.year,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    SUM(f.quantity) AS total_items_sold,
    ROUND(SUM(f.total_amount), 2) AS total_revenue,
    ROUND(AVG(f.total_amount), 2) AS avg_item_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year
ORDER BY d.year;

-- 1b. Quarterly Revenue Roll-Up
SELECT 
    d.year,
    d.quarter,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    SUM(f.quantity) AS total_items_sold,
    ROUND(SUM(f.total_amount), 2) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.quarter
ORDER BY d.year, d.quarter;

-- 1c. Monthly Revenue Roll-Up
SELECT 
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    ROUND(SUM(f.total_amount), 2) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- --------------------------------------------------------------------
-- 2. DRILL-DOWN OPERATION
-- De-aggregates data by stepping down a hierarchy into finer granularity
-- Example: Drill down into Year 2024 to inspect Quarter and Month breakdown
-- --------------------------------------------------------------------
SELECT 
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    SUM(f.quantity) AS total_units,
    ROUND(SUM(f.total_amount), 2) AS monthly_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2024
GROUP BY d.year, d.quarter, d.month, d.month_name
ORDER BY d.quarter, d.month;


-- --------------------------------------------------------------------
-- 3. SLICE OPERATION
-- Filters the data cube along ONE specific dimension value
-- Example: Sales sliced for Country = 'United Kingdom' AND Year = 2024
-- --------------------------------------------------------------------
SELECT 
    l.country,
    d.year,
    p.category,
    COUNT(DISTINCT f.invoice_no) AS total_invoices,
    SUM(f.quantity) AS total_units,
    ROUND(SUM(f.total_amount), 2) AS total_revenue
FROM fact_sales f
JOIN dim_location l ON f.location_key = l.location_key
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_product p ON f.product_key = p.product_key
WHERE l.country = 'United Kingdom' AND d.year = 2024
GROUP BY l.country, d.year, p.category
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------------
-- 4. DICE OPERATION
-- Filters the data cube along MULTIPLE dimensions simultaneously
-- Example: Countries IN ('United Kingdom', 'Germany', 'France')
--          AND Categories IN ('Kitchen & Dining', 'Home Decor')
--          AND Year = 2024 AND Quarter IN (3, 4)
-- --------------------------------------------------------------------
SELECT 
    l.country,
    p.category,
    d.year,
    d.quarter,
    COUNT(DISTINCT f.invoice_no) AS order_count,
    ROUND(SUM(f.total_amount), 2) AS dice_revenue
FROM fact_sales f
JOIN dim_location l ON f.location_key = l.location_key
JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_date d ON f.date_key = d.date_key
WHERE l.country IN ('United Kingdom', 'Germany', 'France')
  AND p.category IN ('Kitchen & Dining', 'Home Decor')
  AND d.year = 2024
  AND d.quarter IN (3, 4)
GROUP BY l.country, p.category, d.year, d.quarter
ORDER BY dice_revenue DESC;


-- --------------------------------------------------------------------
-- 5. PIVOT OPERATION (CROSSTAB)
-- Rotates the data axis to view Category revenue across Months
-- --------------------------------------------------------------------
SELECT 
    p.category,
    ROUND(SUM(CASE WHEN d.month = 1 THEN f.total_amount ELSE 0 END), 2) AS Jan,
    ROUND(SUM(CASE WHEN d.month = 2 THEN f.total_amount ELSE 0 END), 2) AS Feb,
    ROUND(SUM(CASE WHEN d.month = 3 THEN f.total_amount ELSE 0 END), 2) AS Mar,
    ROUND(SUM(CASE WHEN d.month = 4 THEN f.total_amount ELSE 0 END), 2) AS Apr,
    ROUND(SUM(CASE WHEN d.month = 5 THEN f.total_amount ELSE 0 END), 2) AS May,
    ROUND(SUM(CASE WHEN d.month = 6 THEN f.total_amount ELSE 0 END), 2) AS Jun,
    ROUND(SUM(CASE WHEN d.month = 7 THEN f.total_amount ELSE 0 END), 2) AS Jul,
    ROUND(SUM(CASE WHEN d.month = 8 THEN f.total_amount ELSE 0 END), 2) AS Aug,
    ROUND(SUM(CASE WHEN d.month = 9 THEN f.total_amount ELSE 0 END), 2) AS Sep,
    ROUND(SUM(CASE WHEN d.month = 10 THEN f.total_amount ELSE 0 END), 2) AS Oct,
    ROUND(SUM(CASE WHEN d.month = 11 THEN f.total_amount ELSE 0 END), 2) AS Nov,
    ROUND(SUM(CASE WHEN d.month = 12 THEN f.total_amount ELSE 0 END), 2) AS "Dec",
    ROUND(SUM(f.total_amount), 2) AS Total_Revenue
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY p.category
ORDER BY Total_Revenue DESC;


-- --------------------------------------------------------------------
-- 6. TOP 10 BEST-SELLING PRODUCTS BY REVENUE
-- --------------------------------------------------------------------
SELECT 
    p.stock_code,
    p.description,
    p.category,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.total_amount), 2) AS total_revenue
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.stock_code, p.description, p.category
ORDER BY total_revenue DESC
LIMIT 10;


-- --------------------------------------------------------------------
-- 7. TOP 10 VALUABLE CUSTOMERS BY REVENUE
-- --------------------------------------------------------------------
SELECT 
    c.customer_id,
    c.country,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    SUM(f.quantity) AS total_items,
    ROUND(SUM(f.total_amount), 2) AS total_spent
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_id, c.country
ORDER BY total_spent DESC
LIMIT 10;


-- --------------------------------------------------------------------
-- 8. REVENUE & ORDER DISTRIBUTION BY COUNTRY
-- --------------------------------------------------------------------
SELECT 
    l.country,
    l.region,
    COUNT(DISTINCT f.invoice_no) AS total_orders,
    COUNT(DISTINCT f.customer_key) AS unique_customers,
    ROUND(SUM(f.total_amount), 2) AS total_revenue,
    ROUND(100.0 * SUM(f.total_amount) / (SELECT SUM(total_amount) FROM fact_sales), 2) AS revenue_pct
FROM fact_sales f
JOIN dim_location l ON f.location_key = l.location_key
GROUP BY l.country, l.region
ORDER BY total_revenue DESC;
