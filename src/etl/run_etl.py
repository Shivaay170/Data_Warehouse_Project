"""ETL Pipeline Orchestrator.

Orchestrates raw data extraction, cleaning & transformation,
dimensional modeling, and idempotent loading into the Data Warehouse.

Can be executed standalone via:
    python -m src.etl.run_etl
"""

import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.etl.extract import extract_raw_data
from src.etl.transform import clean_and_transform
from src.etl.load import load_data_warehouse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_Pipeline")

def run_etl_pipeline() -> dict:
    """Run full ETL pipeline end-to-end and return execution metrics."""
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("STARTING RETAIL DATA WAREHOUSE ETL PIPELINE")
    logger.info("=" * 65)

    try:
        # Phase 1: Extract
        logger.info("[PHASE 1/3] Extracting raw retail transactions...")
        df_raw = extract_raw_data()
        raw_count = len(df_raw)

        # Phase 2: Transform
        logger.info("[PHASE 2/3] Cleaning, filtering, and building dimensions...")
        df_clean, dimensions, quality_report = clean_and_transform(df_raw)
        clean_count = len(df_clean)

        # Phase 3: Load
        logger.info("[PHASE 3/3] Loading dimensions and fact table with surrogate keys...")
        fact_count = load_data_warehouse(df_clean, dimensions)

        elapsed = round(time.time() - start_time, 2)
        logger.info("=" * 65)
        logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY IN %.2f SECONDS", elapsed)
        logger.info("Raw Records:      %10s", f"{raw_count:,}")
        logger.info("Cleaned Records:  %10s", f"{clean_count:,}")
        logger.info("Fact Sales Rows:  %10s", f"{fact_count:,}")
        logger.info("Dim Customers:    %10s", f"{len(dimensions['dim_customer']):,}")
        logger.info("Dim Products:     %10s", f"{len(dimensions['dim_product']):,}")
        logger.info("Dim Locations:    %10s", f"{len(dimensions['dim_location']):,}")
        logger.info("Dim Dates:        %10s", f"{len(dimensions['dim_date']):,}")
        logger.info("=" * 65)

        return {
            "status": "SUCCESS",
            "elapsed_seconds": elapsed,
            "raw_records": raw_count,
            "cleaned_records": clean_count,
            "fact_records": fact_count,
            "quality_report": quality_report
        }

    except Exception as e:
        logger.exception("ETL Pipeline encountered a fatal error: %s", str(e))
        raise

if __name__ == "__main__":
    run_etl_pipeline()
