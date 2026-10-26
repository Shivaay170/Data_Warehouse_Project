"""End-to-End Master Execution Pipeline.

Executes the complete project workflow sequentially:
1. Generates / verifies raw retail transaction dataset (>= 50,000 rows)
2. Sets up Star Schema database & generates ER architecture diagram
3. Executes complete ETL pipeline (Extract -> Clean & Transform -> Load)
4. Executes all 4 Data Mining & Machine Learning modules
5. Executes the automated pytest test suite
6. Displays instructions to launch the Streamlit dashboard

Run simply via:
    python run_all.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.config import RAW_DATA_FILE, DEFAULT_SQLITE_PATH
from scripts.generate_synthetic_data import generate_retail_dataset
from src.warehouse.create_schema import create_star_schema, generate_star_schema_diagram
from src.etl.run_etl import run_etl_pipeline
from src.mining.run_all_mining import run_all_mining_modules

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def main():
    total_start = time.time()
    print_banner("RETAIL DATA WAREHOUSE & DATA MINING - MASTER PIPELINE")
    print(f"Project Root: {BASE_DIR}")
    print(f"Python Executable: {sys.executable}")

    # Step 1: Dataset Generation / Verification
    print_banner("[STEP 1/5] Verifying Raw Transaction Dataset")
    if not RAW_DATA_FILE.exists():
        print(f"Raw data file not found at {RAW_DATA_FILE}. Generating synthetic dataset...")
        generate_retail_dataset(num_records=60000, output_path=RAW_DATA_FILE)
    else:
        print(f"Found existing raw dataset: {RAW_DATA_FILE}")

    # Step 2: Star Schema Setup & Architecture Diagram
    print_banner("[STEP 2/5] Creating Star Schema & ER Diagram")
    create_star_schema(drop_existing=False)
    generate_star_schema_diagram()

    # Step 3: Run ETL Pipeline
    print_banner("[STEP 3/5] Executing Idempotent ETL Pipeline")
    etl_results = run_etl_pipeline()
    print(f"ETL Complete: {etl_results['fact_records']:,} fact rows loaded.")

    # Step 4: Run Data Mining Modules
    print_banner("[STEP 4/5] Executing Data Mining & ML Models")
    mining_results = run_all_mining_modules()
    print("Data Mining Complete: All models, figures, and metrics compiled.")

    # Step 5: Automated Testing
    print_banner("[STEP 5/5] Running Automated Pytest Test Suite")
    test_cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
    test_proc = subprocess.run(test_cmd, cwd=str(BASE_DIR))
    if test_proc.returncode != 0:
        print("\n❌ Pytest encountered test failures! Please inspect the logs above.")
        sys.exit(test_proc.returncode)

    total_elapsed = round(time.time() - total_start, 2)
    print_banner("PIPELINE EXECUTION COMPLETE (SUCCESS)")
    print(f"Total Elapsed Time: {total_elapsed} seconds")
    print("\nTo launch the interactive Streamlit analytics dashboard, run:")
    print("    streamlit run src/dashboard/app.py\n")

if __name__ == "__main__":
    main()
