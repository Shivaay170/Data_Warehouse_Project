"""Extract module for Retail Data Warehouse ETL pipeline.

Extracts raw retail transaction data from CSV or Excel files in data/raw/
into a pandas DataFrame, verifying schema requirements.
"""

import logging
from pathlib import Path
import pandas as pd
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import RAW_DATA_FILE
from scripts.generate_synthetic_data import generate_retail_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity", 
    "InvoiceDate", "UnitPrice", "CustomerID", "Country"
]

def extract_raw_data(file_path: Path = RAW_DATA_FILE) -> pd.DataFrame:
    """Extract raw transaction data from CSV/Excel into a DataFrame."""
    if not file_path.exists():
        logger.warning(f"Raw data file not found at {file_path}. Generating synthetic data...")
        generate_retail_dataset(output_path=file_path)

    logger.info(f"Extracting raw data from: {file_path}")
    if str(file_path).endswith(".csv"):
        df = pd.read_csv(file_path, dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str})
    elif str(file_path).endswith((".xls", ".xlsx")):
        df = pd.read_excel(file_path, dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str})
    else:
        raise ValueError(f"Unsupported file format for {file_path}. Expected CSV or Excel.")

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Raw dataset is missing required columns: {missing_cols}")

    logger.info(f"Raw data extraction complete. Total records extracted: {len(df):,}")
    return df

if __name__ == "__main__":
    df_raw = extract_raw_data()
    print(df_raw.head())
