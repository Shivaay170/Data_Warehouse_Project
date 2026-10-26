"""Unified Data Mining Pipeline Runner.

Executes all 4 data mining and machine learning modules against the warehouse:
1. Customer Segmentation (RFM + K-Means + PCA)
2. Market Basket Analysis (Apriori & FP-Growth benchmarks + Association Rules)
3. Churn Prediction (Classifiers, Evaluations, ROC Curves, Model Persistence)
4. Sales Forecasting (Holdout backtesting & 6-month revenue projection)

Saves all analytical figures to reports/figures/ and metrics to reports/results.json.
"""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import METRICS_FILE, REPORTS_DIR, FIGURES_DIR
from src.mining.segmentation import run_customer_segmentation
from src.mining.association_rules import run_market_basket_analysis
from src.mining.churn import run_churn_pipeline
from src.mining.forecasting import run_sales_forecasting

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Data_Mining_Pipeline")

def run_all_mining_modules() -> dict:
    """Run all data mining tasks and compile results.json."""
    start_time = time.time()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 65)
    logger.info("STARTING DATA MINING & PREDICTIVE ANALYTICS SUITE")
    logger.info("=" * 65)

    all_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modules": {}
    }

    # 1. Customer Segmentation
    logger.info("[MODULE 1/4] Running RFM Customer Segmentation...")
    _, profile_df, seg_metrics = run_customer_segmentation()
    all_results["modules"]["customer_segmentation"] = {
        "metrics": seg_metrics,
        "segment_profiles": profile_df.to_dict(orient="records")
    }

    # 2. Market Basket Analysis
    logger.info("[MODULE 2/4] Running Market Basket Analysis (Apriori vs FP-Growth)...")
    rules_df, basket_metrics = run_market_basket_analysis()
    # Format rules for JSON serialization (convert frozensets)
    clean_rules = []
    if not rules_df.empty:
        for r in rules_df.head(10).to_dict(orient="records"):
            item = {k: list(v) if isinstance(v, (set, frozenset)) else v for k, v in r.items()}
            clean_rules.append(item)

    all_results["modules"]["market_basket_analysis"] = {
        "metrics": basket_metrics,
        "top_rules": clean_rules
    }

    # 3. Customer Churn Prediction
    logger.info("[MODULE 3/4] Training Churn Prediction Classifiers...")
    _, churn_metrics = run_churn_pipeline()
    all_results["modules"]["churn_prediction"] = churn_metrics

    # 4. Sales Forecasting
    logger.info("[MODULE 4/4] Generating Monthly Sales Forecasting...")
    _, future_df, forecast_metrics = run_sales_forecasting()
    all_results["modules"]["sales_forecasting"] = {
        "metrics": forecast_metrics,
        "future_projections": future_df.to_dict(orient="records")
    }

    all_results["total_elapsed_seconds"] = round(time.time() - start_time, 2)

    # Save to reports/results.json
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

    logger.info("=" * 65)
    logger.info("ALL MINING MODULES COMPLETED IN %.2f SECONDS", all_results["total_elapsed_seconds"])
    logger.info("Compiled metrics saved to: %s", METRICS_FILE)
    logger.info("=" * 65)

    return all_results

if __name__ == "__main__":
    run_all_mining_modules()
