-- ====================================================================
-- Retail Data Warehouse - Star Schema DDL Script
-- Supports SQLite and PostgreSQL (via standard ANSI SQL DDL)
-- ====================================================================

-- 1. Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,           -- Format: YYYYMMDD (e.g. 20240115)
    full_date DATE NOT NULL,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    weekday VARCHAR(20) NOT NULL,
    is_weekend INTEGER NOT NULL             -- 0 = Weekday, 1 = Weekend
);

-- 2. Customer Dimension
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key INTEGER PRIMARY KEY,       -- Surrogate Key
    customer_id VARCHAR(50) NOT NULL UNIQUE,-- Natural/Business Key
    country VARCHAR(100) NOT NULL
);

-- 3. Product Dimension
CREATE TABLE IF NOT EXISTS dim_product (
    product_key INTEGER PRIMARY KEY,        -- Surrogate Key
    stock_code VARCHAR(50) NOT NULL UNIQUE, -- Natural/Business Key
    description VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL
);

-- 4. Location Dimension
CREATE TABLE IF NOT EXISTS dim_location (
    location_key INTEGER PRIMARY KEY,       -- Surrogate Key
    country VARCHAR(100) NOT NULL UNIQUE,   -- Country Name
    region VARCHAR(100) NOT NULL            -- Geographic Region (e.g. UK, Europe, APAC)
);

-- 5. Sales Fact Table
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key INTEGER PRIMARY KEY,          -- Fact Surrogate Key
    date_key INTEGER NOT NULL,              -- FK to dim_date
    customer_key INTEGER NOT NULL,          -- FK to dim_customer
    product_key INTEGER NOT NULL,           -- FK to dim_product
    location_key INTEGER NOT NULL,          -- FK to dim_location
    invoice_no VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
    FOREIGN KEY (location_key) REFERENCES dim_location(location_key)
);

-- Performance Indexes for OLAP query acceleration
CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_location ON fact_sales(location_key);
CREATE INDEX IF NOT EXISTS idx_fact_invoice ON fact_sales(invoice_no);
CREATE INDEX IF NOT EXISTS idx_dim_date_ym ON dim_date(year, month);
CREATE INDEX IF NOT EXISTS idx_dim_product_cat ON dim_product(category);
CREATE INDEX IF NOT EXISTS idx_dim_loc_country ON dim_location(country);
