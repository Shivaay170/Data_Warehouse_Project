"""Tests for data mining and predictive machine learning modules."""

import pytest
from src.config import DB_URL
from src.warehouse.create_schema import get_engine
from src.mining.segmentation import run_customer_segmentation
from src.mining.association_rules import run_market_basket_analysis
from src.mining.churn import run_churn_pipeline, predict_customer_churn
from src.mining.forecasting import run_sales_forecasting

@pytest.fixture(scope="module")
def db_engine():
    return get_engine(DB_URL)

def test_customer_segmentation(db_engine):
    """Verify RFM customer segmentation outputs and silhouette scores."""
    rfm_df, profile_df, metrics = run_customer_segmentation(engine=db_engine, n_clusters=4)
    
    assert len(rfm_df) > 0
    assert set(["customer_id", "recency", "frequency", "monetary", "cluster", "segment", "pca_1", "pca_2"]).issubset(rfm_df.columns)
    assert len(profile_df) == 4
    assert -1.0 <= metrics["silhouette_score"] <= 1.0
    assert len(metrics["pca_variance_explained"]) == 2
    assert sum(metrics["pca_variance_explained"]) > 0.5  # Explains majority of variance

def test_market_basket_analysis(db_engine):
    """Verify Apriori and FP-Growth rule mining and benchmarking."""
    rules_df, metrics = run_market_basket_analysis(min_support=0.015, min_lift=1.2, min_confidence=0.20, engine=db_engine)
    
    assert metrics["transactions_analyzed"] > 0
    assert metrics["runtime_apriori_seconds"] >= 0
    assert metrics["runtime_fpgrowth_seconds"] >= 0
    
    if not rules_df.empty:
        assert set(["rule_str", "support", "confidence", "lift"]).issubset(rules_df.columns)
        assert (rules_df["lift"] >= 1.2).all()
        assert (rules_df["confidence"] >= 0.20).all()
        assert (rules_df["support"] >= 0.015).all()

def test_churn_prediction_pipeline(db_engine):
    """Verify supervised classification models, metric ranges, and real-time inference."""
    df_churn, summary = run_churn_pipeline(engine=db_engine)
    
    assert len(df_churn) > 0
    assert "churn" in df_churn.columns
    assert summary["best_model"] in ["Logistic Regression", "Decision Tree", "Random Forest"]
    
    for mname, mstats in summary["models"].items():
        assert 0.0 <= mstats["accuracy"] <= 1.0
        assert 0.0 <= mstats["f1_score"] <= 1.0
        assert 0.5 <= mstats["roc_auc"] <= 1.0  # Better than random guessing

    # Test single customer prediction helper
    sample_features = {
        "order_count": 2,
        "total_spend": 80.0,
        "avg_order_value": 40.0,
        "total_units": 10,
        "avg_units_per_order": 5.0,
        "unique_products": 3,
        "tenure_days": 180,
        "purchase_interval": 30.0
    }
    pred_res = predict_customer_churn(sample_features)
    assert pred_res["churn_prediction"] in [0, 1]
    assert 0.0 <= pred_res["churn_probability"] <= 1.0
    assert "churn_label" in pred_res

def test_sales_forecasting(db_engine):
    """Verify time series forecasting, holdout evaluation, and future projections."""
    horizon = 6
    hist_df, future_df, metrics = run_sales_forecasting(holdout_months=4, forecast_horizon=horizon, engine=db_engine)
    
    assert len(hist_df) > 0
    assert len(future_df) == horizon
    assert metrics["holdout_metrics"]["MAE"] > 0
    assert metrics["holdout_metrics"]["RMSE"] > 0
    
    for col in ["period", "forecasted_revenue", "lower_bound", "upper_bound"]:
        assert col in future_df.columns
    # Ensure lower bound is non-negative and <= upper bound
    assert (future_df["lower_bound"] >= 0).all()
    assert (future_df["lower_bound"] <= future_df["upper_bound"]).all()
