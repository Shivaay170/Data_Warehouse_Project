"""Retail Data Warehouse and Analytics System Configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
STAGING_DATA_DIR = DATA_DIR / "staging"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_DATA_FILE = RAW_DATA_DIR / "online_retail.csv"
STAGING_DATA_FILE = STAGING_DATA_DIR / "cleaned_retail.parquet"

# Reports and docs
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_FILE = REPORTS_DIR / "results.json"
DATA_QUALITY_REPORT_FILE = REPORTS_DIR / "data_quality_report.json"
DOCS_DIR = BASE_DIR / "docs"
SQL_DIR = BASE_DIR / "sql"

# Ensure all directories exist
for folder in [RAW_DATA_DIR, STAGING_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, FIGURES_DIR, DOCS_DIR, SQL_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Default database SQLite URL; can be overridden by setting DB_URL in .env
DEFAULT_SQLITE_PATH = PROCESSED_DATA_DIR / "retail_dw.db"
DB_URL = os.getenv("DB_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}")

# Mining parameters & random state
RANDOM_STATE = 42
CHURN_DAYS_THRESHOLD = 90
