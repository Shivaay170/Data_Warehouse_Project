"""Unit tests for ETL transformation and data cleaning logic."""

import pandas as pd
import pytest
from src.etl.transform import clean_and_transform, derive_product_category, map_country_region

def test_derive_product_category():
    """Verify keyword-based category derivations."""
    assert derive_product_category("CERAMIC TEA POT WHITE") == "Kitchen & Dining"
    assert derive_product_category("WHITE HANGING HEART T-LIGHT HOLDER") == "Home Decor"
    assert derive_product_category("LUNCH BAG RED RETROSPOT") == "Gifts & Accessories"
    assert derive_product_category("POPCORN HOLDER RETRO RED") == "Stationery & Office"
    assert derive_product_category("COSY SLIPPERS FLEECE PINK") == "Clothing & Apparel"
    assert derive_product_category("UNKNOWN MYSTERY WIDGET") == "General Merchandise"

def test_map_country_region():
    """Verify geographic region mappings."""
    assert map_country_region("United Kingdom") == "UK"
    assert map_country_region("Germany") == "Europe"
    assert map_country_region("France") == "Europe"
    assert map_country_region("Australia") == "APAC"
    assert map_country_region("USA") == "North America"
    assert map_country_region("Brazil") == "Other"

def test_cleaning_rules():
    """Verify filtering of dirty data: duplicates, null customers, cancellations, invalid qty/price."""
    dirty_data = pd.DataFrame([
        # Valid row 1
        {"InvoiceNo": "1001", "StockCode": "TEA01", "Description": "TEA CUP", "Quantity": 2, "InvoiceDate": "2024-01-15 10:00:00", "UnitPrice": 5.0, "CustomerID": "12345", "Country": "United Kingdom"},
        # Exact duplicate of row 1
        {"InvoiceNo": "1001", "StockCode": "TEA01", "Description": "TEA CUP", "Quantity": 2, "InvoiceDate": "2024-01-15 10:00:00", "UnitPrice": 5.0, "CustomerID": "12345", "Country": "United Kingdom"},
        # Cancelled invoice (starts with C)
        {"InvoiceNo": "C1002", "StockCode": "TEA01", "Description": "TEA CUP", "Quantity": -2, "InvoiceDate": "2024-01-15 11:00:00", "UnitPrice": 5.0, "CustomerID": "12345", "Country": "United Kingdom"},
        # Null Customer ID (blank, None, nan)
        {"InvoiceNo": "1003", "StockCode": "CAKE01", "Description": "CAKE STAND", "Quantity": 1, "InvoiceDate": "2024-01-16 12:00:00", "UnitPrice": 15.0, "CustomerID": "", "Country": "Germany"},
        {"InvoiceNo": "1004", "StockCode": "CAKE01", "Description": "CAKE STAND", "Quantity": 1, "InvoiceDate": "2024-01-16 12:30:00", "UnitPrice": 15.0, "CustomerID": "nan", "Country": "Germany"},
        # Non-positive quantity
        {"InvoiceNo": "1005", "StockCode": "CAKE01", "Description": "CAKE STAND", "Quantity": 0, "InvoiceDate": "2024-01-17 14:00:00", "UnitPrice": 15.0, "CustomerID": "12346", "Country": "France"},
        # Non-positive price
        {"InvoiceNo": "1006", "StockCode": "CAKE01", "Description": "CAKE STAND", "Quantity": 3, "InvoiceDate": "2024-01-17 14:30:00", "UnitPrice": 0.0, "CustomerID": "12346", "Country": "France"},
        # Valid row 2
        {"InvoiceNo": "1007", "StockCode": "LAMP01", "Description": "HEART LIGHT", "Quantity": 4, "InvoiceDate": "2024-01-18 15:00:00", "UnitPrice": 2.50, "CustomerID": "12347", "Country": "France"}
    ])

    df_clean, dims, report = clean_and_transform(dirty_data)

    # Exactly 2 valid rows should survive
    assert len(df_clean) == 2
    assert set(df_clean["InvoiceNo"]) == {"1001", "1007"}
    assert report["cleaning_steps"]["exact_duplicates_removed"] == 1
    assert report["cleaning_steps"]["cancelled_invoices_removed"] == 1
    assert report["cleaning_steps"]["null_customer_ids_removed"] == 2
    assert report["cleaning_steps"]["non_positive_qty_price_removed"] == 2

    # Verify derived total_amount
    row_1001 = df_clean[df_clean["InvoiceNo"] == "1001"].iloc[0]
    assert row_1001["total_amount"] == 10.0  # 2 * 5.0

    row_1007 = df_clean[df_clean["InvoiceNo"] == "1007"].iloc[0]
    assert row_1007["total_amount"] == 10.0  # 4 * 2.50

    # Verify dimension generation
    assert "dim_date" in dims
    assert "dim_customer" in dims
    assert "dim_product" in dims
    assert "dim_location" in dims
    assert len(dims["dim_customer"]) == 2
    assert len(dims["dim_product"]) == 2
