"""Transform module for Retail Data Warehouse ETL pipeline.

Cleans dirty raw retail data, enforces business rules, derives metrics,
classifies product categories, constructs dimension models, and generates
a comprehensive Data Quality Audit Report saved to reports/data_quality_report.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DATA_QUALITY_REPORT_FILE, STAGING_DATA_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Category mapping based on product keywords
CATEGORY_KEYWORDS = {
    "Kitchen & Dining": ["TEA", "CAKE", "BREAD", "COFFEE", "CUP", "MUG", "DISH", "BOWL", "PLATE", "KITCHEN", "APRON", "SPATULA", "BAKING", "JUG", "POT", "SPOON", "FORK", "PANTRY", "SPICE", "JAR"],
    "Home Decor": ["HEART", "LIGHT", "T-LIGHT", "ORNAMENT", "LANTERN", "CHRISTMAS", "BOTTLE", "CLOCK", "FRAME", "CANDLE", "MIRROR", "TIN", "HANGING"],
    "Gifts & Accessories": ["BAG", "CASE", "BOX", "GIFT", "LUNCH", "PURSE", "WALLET", "JEWELLERY", "RETROSPOT", "DOILEY"],
    "Stationery & Office": ["STICKER", "PEN", "PENCIL", "NOTEPAD", "PAPER", "BUNTING", "POPCORN", "TAPE", "BOOK", "CARD", "ENVELOPE", "LABEL"],
    "Clothing & Apparel": ["SLIPPER", "SHIRT", "DRESS", "SCARF", "GLOVE", "SOCK", "HAT", "FLEECE", "COAT", "SHOES"]
}

import re

def derive_product_category(description: str) -> str:
    """Categorize a product by inspecting keywords in its description with word boundary matching."""
    if not isinstance(description, str) or not description.strip():
        return "General Merchandise"
    desc_upper = description.upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", desc_upper):
                return category
    return "General Merchandise"

def map_country_region(country: str) -> str:
    """Map country to high-level geographic region for dim_location."""
    if not isinstance(country, str):
        return "Unknown"
    c = country.strip().title()
    if c in ["United Kingdom", "Uk"]:
        return "UK"
    elif c in ["Germany", "France", "Spain", "Netherlands", "Switzerland", "Portugal", "Belgium", "Italy", "Austria", "Eire", "Norway", "Poland"]:
        return "Europe"
    elif c in ["Australia", "Japan", "Singapore"]:
        return "APAC"
    elif c in ["Usa", "Canada"]:
        return "North America"
    return "Other"

def clean_and_transform(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], dict]:
    """Execute all data cleaning rules, derivations, and build dimension tables.

    Returns:
        (df_cleaned, dimensions_dict, data_quality_report)
    """
    initial_rows = len(df_raw)
    report = {
        "initial_raw_records": initial_rows,
        "cleaning_steps": {}
    }
    logger.info(f"Starting data transformation. Initial raw records: {initial_rows:,}")

    df = df_raw.copy()

    # Step 1: Remove exact duplicates
    before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = before - len(df)
    report["cleaning_steps"]["exact_duplicates_removed"] = duplicates_removed
    logger.info(f"Step 1 - Exact duplicates removed: {duplicates_removed:,} (Remaining: {len(df):,})")

    # Step 2: Remove missing/null Customer IDs
    # Documented Decision: In a customer-centric retail warehouse, transactions without identifiable
    # customer IDs cannot be attributed to customer segments, retention cohorts, or churn models.
    # To maintain strict referential integrity with dim_customer, anonymous guest transactions are logged
    # and segregated from the star schema.
    before = len(df)
    df["CustomerID"] = df["CustomerID"].astype(str).str.strip()
    df = df[~df["CustomerID"].isna() & (df["CustomerID"] != "") & (df["CustomerID"] != "nan") & (df["CustomerID"] != "None")]
    # Clean customer ID to integer string format if numeric
    df["CustomerID"] = df["CustomerID"].apply(lambda x: str(int(float(x))) if x.replace(".", "", 1).isdigit() else str(x))
    null_customers_removed = before - len(df)
    report["cleaning_steps"]["null_customer_ids_removed"] = null_customers_removed
    report["customer_id_handling_policy"] = (
        "Anonymous transactions without valid CustomerID removed to preserve referential integrity "
        "and enable accurate RFM segmentation and churn modeling."
    )
    logger.info(f"Step 2 - Missing CustomerID records removed: {null_customers_removed:,} (Remaining: {len(df):,})")

    # Step 3: Remove cancelled invoices (InvoiceNo starting with 'C')
    before = len(df)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df = df[~df["InvoiceNo"].str.startswith("C", na=False)]
    cancellations_removed = before - len(df)
    report["cleaning_steps"]["cancelled_invoices_removed"] = cancellations_removed
    logger.info(f"Step 3 - Cancelled invoices removed: {cancellations_removed:,} (Remaining: {len(df):,})")

    # Step 4: Remove negative or zero Quantity and UnitPrice
    before = len(df)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce").fillna(0.0)
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0.0)]
    invalid_qty_price_removed = before - len(df)
    report["cleaning_steps"]["non_positive_qty_price_removed"] = invalid_qty_price_removed
    logger.info(f"Step 4 - Non-positive quantity/price removed: {invalid_qty_price_removed:,} (Remaining: {len(df):,})")

    # Step 5: Trim text and standardize formats
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Description"] = df["Description"].astype(str).str.strip().str.upper()
    df["Country"] = df["Country"].astype(str).str.strip().str.title()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["InvoiceDate"])

    # Step 6: Derive Total Amount
    df["total_amount"] = (df["Quantity"] * df["UnitPrice"]).round(2)

    # Step 7: Derive Product Category
    df["Category"] = df["Description"].apply(derive_product_category)

    final_clean_rows = len(df)
    report["final_cleaned_records"] = final_clean_rows
    report["retention_rate_pct"] = round(100.0 * final_clean_rows / initial_rows, 2)
    logger.info(f"Data cleaning finished. Cleaned records: {final_clean_rows:,} ({report['retention_rate_pct']}% retention)")

    # Save cleaned data to staging
    STAGING_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(STAGING_DATA_FILE, index=False)
    logger.info(f"Staged cleaned data at {STAGING_DATA_FILE}")

    # Build Dimension DataFrames
    # 1. dim_date
    dates = pd.DataFrame({"full_date": df["InvoiceDate"].dt.date.unique()})
    dates["full_date"] = pd.to_datetime(dates["full_date"])
    dates = dates.sort_values("full_date").reset_index(drop=True)
    dates["date_key"] = dates["full_date"].dt.strftime("%Y%m%d").astype(int)
    dates["day"] = dates["full_date"].dt.day
    dates["month"] = dates["full_date"].dt.month
    dates["month_name"] = dates["full_date"].dt.strftime("%B")
    dates["quarter"] = dates["full_date"].dt.quarter
    dates["year"] = dates["full_date"].dt.year
    dates["weekday"] = dates["full_date"].dt.strftime("%A")
    dates["is_weekend"] = dates["full_date"].dt.day_of_week.isin([5, 6]).astype(int)
    dim_date = dates[["date_key", "full_date", "day", "month", "month_name", "quarter", "year", "weekday", "is_weekend"]]

    # 2. dim_customer
    # Deduplicate customers by taking their primary country
    customers = df.groupby("CustomerID").agg({"Country": "last"}).reset_index()
    customers = customers.rename(columns={"CustomerID": "customer_id", "Country": "country"})
    customers["customer_key"] = range(1, len(customers) + 1)
    dim_customer = customers[["customer_key", "customer_id", "country"]]

    # 3. dim_product
    # Deduplicate products by taking most frequent description & category
    products = df.groupby("StockCode").agg({
        "Description": "first",
        "Category": "first"
    }).reset_index()
    products = products.rename(columns={"StockCode": "stock_code", "Description": "description", "Category": "category"})
    products["product_key"] = range(1, len(products) + 1)
    dim_product = products[["product_key", "stock_code", "description", "category"]]

    # 4. dim_location
    countries = df["Country"].dropna().unique()
    locations = pd.DataFrame({"country": sorted(countries)})
    locations["region"] = locations["country"].apply(map_country_region)
    locations["location_key"] = range(1, len(locations) + 1)
    dim_location = locations[["location_key", "country", "region"]]

    dimensions = {
        "dim_date": dim_date,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_location": dim_location
    }

    # Save Data Quality Report
    DATA_QUALITY_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_QUALITY_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    logger.info(f"Data quality audit report saved to {DATA_QUALITY_REPORT_FILE}")

    return df, dimensions, report

if __name__ == "__main__":
    from src.etl.extract import extract_raw_data
    df_raw = extract_raw_data()
    df_clean, dims, rep = clean_and_transform(df_raw)
    print(f"Cleaned records: {len(df_clean)}, Dimensions: {list(dims.keys())}")
