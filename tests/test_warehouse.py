"""Warehouse star schema, idempotency, and referential integrity tests."""

import pytest
from sqlalchemy import inspect, text
from src.config import DB_URL
from src.warehouse.create_schema import get_engine, create_star_schema
from src.etl.extract import extract_raw_data
from src.etl.transform import clean_and_transform
from src.etl.load import load_data_warehouse

@pytest.fixture(scope="module")
def db_engine():
    """Shared database engine for testing."""
    engine = get_engine(DB_URL)
    create_star_schema(drop_existing=False, engine=engine)
    return engine

def test_schema_tables_exist(db_engine):
    """Verify all Star Schema dimension and fact tables exist."""
    inspector = inspect(db_engine)
    tables = inspector.get_table_names()
    
    expected_tables = ["dim_date", "dim_customer", "dim_product", "dim_location", "fact_sales"]
    for tbl in expected_tables:
        assert tbl in tables, f"Expected table {tbl} not found in database!"

def test_table_columns_and_keys(db_engine):
    """Verify required primary keys and attribute columns."""
    inspector = inspect(db_engine)

    # dim_date
    date_cols = [c["name"] for c in inspector.get_columns("dim_date")]
    for col in ["date_key", "full_date", "day", "month", "month_name", "quarter", "year", "weekday", "is_weekend"]:
        assert col in date_cols

    # dim_customer
    cust_cols = [c["name"] for c in inspector.get_columns("dim_customer")]
    for col in ["customer_key", "customer_id", "country"]:
        assert col in cust_cols

    # dim_product
    prod_cols = [c["name"] for c in inspector.get_columns("dim_product")]
    for col in ["product_key", "stock_code", "description", "category"]:
        assert col in prod_cols

    # fact_sales
    fact_cols = [c["name"] for c in inspector.get_columns("fact_sales")]
    for col in ["sales_key", "date_key", "customer_key", "product_key", "location_key", "invoice_no", "quantity", "unit_price", "total_amount"]:
        assert col in fact_cols

def test_referential_integrity(db_engine):
    """Verify that there are no orphan foreign keys in fact_sales."""
    with db_engine.connect() as conn:
        # Check orphan dates
        orphan_dates = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f 
            LEFT JOIN dim_date d ON f.date_key = d.date_key 
            WHERE d.date_key IS NULL;
        """)).scalar()
        assert orphan_dates == 0, f"Found {orphan_dates} orphan date_keys in fact_sales!"

        # Check orphan customers
        orphan_custs = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f 
            LEFT JOIN dim_customer c ON f.customer_key = c.customer_key 
            WHERE c.customer_key IS NULL;
        """)).scalar()
        assert orphan_custs == 0, f"Found {orphan_custs} orphan customer_keys in fact_sales!"

        # Check orphan products
        orphan_prods = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f 
            LEFT JOIN dim_product p ON f.product_key = p.product_key 
            WHERE p.product_key IS NULL;
        """)).scalar()
        assert orphan_prods == 0, f"Found {orphan_prods} orphan product_keys in fact_sales!"

        # Check orphan locations
        orphan_locs = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f 
            LEFT JOIN dim_location l ON f.location_key = l.location_key 
            WHERE l.location_key IS NULL;
        """)).scalar()
        assert orphan_locs == 0, f"Found {orphan_locs} orphan location_keys in fact_sales!"

def test_etl_idempotency_and_reconciliation(db_engine):
    """Verify that re-running load_data_warehouse produces exact same row count without duplication."""
    df_raw = extract_raw_data()
    df_clean, dims, _ = clean_and_transform(df_raw)

    count_1 = load_data_warehouse(df_clean, dims, engine=db_engine)
    assert count_1 == len(df_clean)

    # Re-run load
    count_2 = load_data_warehouse(df_clean, dims, engine=db_engine)
    assert count_2 == count_1, "ETL load is not idempotent! Row count changed on re-run."
    assert count_2 == len(df_clean), "Reconciliation failure: fact count != cleaned rows count."
