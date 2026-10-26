"""Load module for Retail Data Warehouse ETL pipeline.

Loads transformed data and dimension entities into the Star Schema database.
Enforces surrogate key lookups, referential integrity, idempotency,
and reconciles row counts between staging and warehouse.
"""

import logging
from pathlib import Path
from typing import Dict
import pandas as pd
from sqlalchemy import text
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL
from src.warehouse.create_schema import get_engine, create_star_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def load_data_warehouse(
    df_cleaned: pd.DataFrame, 
    dimensions: Dict[str, pd.DataFrame], 
    engine=None
) -> int:
    """Load dimensions and fact table into data warehouse idempotently.

    Returns:
        int: Number of fact table rows loaded.
    """
    if engine is None:
        engine = get_engine(DB_URL)

    # Ensure schema exists
    create_star_schema(drop_existing=False, engine=engine)

    logger.info("Starting idempotent warehouse load transaction...")
    with engine.begin() as conn:
        # Idempotency: Clean out existing rows before loading fresh data
        tables_in_order = ["fact_sales", "dim_customer", "dim_product", "dim_location", "dim_date"]
        for tbl in tables_in_order:
            conn.execute(text(f"DELETE FROM {tbl};"))
        logger.info("Cleared existing records to guarantee idempotency.")

        # 1. Load Dimensions
        for dim_name in ["dim_date", "dim_customer", "dim_product", "dim_location"]:
            dim_df = dimensions[dim_name].copy()
            if dim_name == "dim_date":
                # Ensure date format is string for sqlite or proper date
                dim_df["full_date"] = dim_df["full_date"].dt.strftime("%Y-%m-%d")
            dim_df.to_sql(dim_name, conn, if_exists="append", index=False)
            logger.info(f"Loaded {len(dim_df):,} records into {dim_name}")

        # 2. Build Fact Table by joining surrogate keys
        logger.info("Performing surrogate key lookups for fact table construction...")
        df_fact = df_cleaned.copy()
        df_fact["date_key"] = df_fact["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)

        # Lookup customer_key
        cust_map = dimensions["dim_customer"].set_index("customer_id")["customer_key"].to_dict()
        df_fact["customer_key"] = df_fact["CustomerID"].map(cust_map)

        # Lookup product_key
        prod_map = dimensions["dim_product"].set_index("stock_code")["product_key"].to_dict()
        df_fact["product_key"] = df_fact["StockCode"].map(prod_map)

        # Lookup location_key
        loc_map = dimensions["dim_location"].set_index("country")["location_key"].to_dict()
        df_fact["location_key"] = df_fact["Country"].map(loc_map)

        # Check for any unmapped surrogate keys (Referential Integrity Check)
        unmapped_cust = df_fact["customer_key"].isna().sum()
        unmapped_prod = df_fact["product_key"].isna().sum()
        unmapped_loc = df_fact["location_key"].isna().sum()

        if unmapped_cust > 0 or unmapped_prod > 0 or unmapped_loc > 0:
            raise ValueError(
                f"Referential integrity failure: unmapped keys detected! "
                f"Cust: {unmapped_cust}, Prod: {unmapped_prod}, Loc: {unmapped_loc}"
            )

        # Select and format fact columns
        fact_sales = pd.DataFrame({
            "sales_key": range(1, len(df_fact) + 1),
            "date_key": df_fact["date_key"].astype(int),
            "customer_key": df_fact["customer_key"].astype(int),
            "product_key": df_fact["product_key"].astype(int),
            "location_key": df_fact["location_key"].astype(int),
            "invoice_no": df_fact["InvoiceNo"].astype(str),
            "quantity": df_fact["Quantity"].astype(int),
            "unit_price": df_fact["UnitPrice"].astype(float),
            "total_amount": df_fact["total_amount"].astype(float)
        })

        # 3. Load Fact Table
        fact_sales.to_sql("fact_sales", conn, if_exists="append", index=False, chunksize=10000)
        logger.info(f"Loaded {len(fact_sales):,} records into fact_sales")

    # Reconciliation check
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_sales;")).scalar()
        if fact_count != len(df_cleaned):
            raise AssertionError(f"Reconciliation error! Cleaned rows ({len(df_cleaned)}) != Fact rows ({fact_count})")
        logger.info(f"Reconciliation successful: fact_sales row count ({fact_count:,}) exactly matches cleaned rows!")

    return fact_count

if __name__ == "__main__":
    from src.etl.extract import extract_raw_data
    from src.etl.transform import clean_and_transform
    df_raw = extract_raw_data()
    df_clean, dims, _ = clean_and_transform(df_raw)
    load_data_warehouse(df_clean, dims)
