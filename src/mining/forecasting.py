"""Sales Forecasting Module for Monthly Revenue Projection.

Extracts historical monthly revenue from the warehouse, evaluates forecasting
models on a holdout test partition, calculates MAE and RMSE metrics, projects
monthly sales revenue for the next 6 months with prediction intervals, and
generates actual-vs-forecast comparison plots.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL, FIGURES_DIR
from src.warehouse.create_schema import get_engine

def extract_monthly_revenue(engine=None) -> pd.DataFrame:
    """Extract chronological monthly revenue series from the star schema."""
    if engine is None:
        engine = get_engine(DB_URL)

    query = """
    SELECT 
        d.year,
        d.month,
        printf('%d-%02d', d.year, d.month) AS period,
        ROUND(SUM(f.total_amount), 2) AS monthly_revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month
    ORDER BY d.year, d.month;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    df["time_idx"] = np.arange(len(df))
    return df

def run_sales_forecasting(
    holdout_months: int = 4, 
    forecast_horizon: int = 6, 
    engine=None
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Train trend + seasonal forecast model, evaluate on holdout, and project future revenue.

    Returns:
        (df_history, df_future, metrics_dict)
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = extract_monthly_revenue(engine)
    n = len(df)

    if n < 8:
        raise ValueError(f"Insufficient historical data ({n} months) for time series forecasting.")

    train_df = df.iloc[:-holdout_months].copy()
    test_df = df.iloc[-holdout_months:].copy()

    # Feature engineering for monthly trend and seasonality
    # Month dummy indicators for seasonality (months 1-12)
    def make_features(data: pd.DataFrame) -> pd.DataFrame:
        feats = pd.DataFrame()
        feats["time_idx"] = data["time_idx"]
        for m in range(1, 13):
            feats[f"month_{m}"] = (data["month"] == m).astype(int)
        return feats

    X_train = make_features(train_df)
    y_train = train_df["monthly_revenue"]

    X_test = make_features(test_df)
    y_test = test_df["monthly_revenue"]

    # Model: Ridge regression with time trend + seasonal indicators
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)

    # In-sample & holdout predictions
    train_df["fitted"] = model.predict(X_train).round(2)
    test_df["predicted"] = model.predict(X_test).round(2)

    # Evaluate holdout metrics
    mae = float(mean_absolute_error(y_test, test_df["predicted"]))
    rmse = float(np.sqrt(mean_squared_error(y_test, test_df["predicted"])))
    mape = float(np.mean(np.abs((y_test - test_df["predicted"]) / y_test)) * 100)

    # Benchmark: 3-Month Simple Moving Average on Holdout
    sma_predictions = []
    full_revenue = list(train_df["monthly_revenue"])
    for i in range(len(test_df)):
        sma_val = np.mean(full_revenue[-3:])
        sma_predictions.append(sma_val)
        full_revenue.append(test_df["monthly_revenue"].iloc[i])
    sma_mae = float(mean_absolute_error(y_test, sma_predictions))
    sma_rmse = float(np.sqrt(mean_squared_error(y_test, sma_predictions)))

    # Re-fit on ALL historical data for forward-looking 6 months projection
    X_full = make_features(df)
    y_full = df["monthly_revenue"]
    full_model = Ridge(alpha=1.0)
    full_model.fit(X_full, y_full)

    # Generate future periods
    last_year = df["year"].iloc[-1]
    last_month = df["month"].iloc[-1]
    future_rows = []

    curr_year = last_year
    curr_month = last_month
    for step in range(1, forecast_horizon + 1):
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
        period_str = f"{curr_year}-{curr_month:02d}"
        future_rows.append({
            "year": curr_year,
            "month": curr_month,
            "period": period_str,
            "time_idx": n + step - 1
        })

    future_df = pd.DataFrame(future_rows)
    X_future = make_features(future_df)
    future_pred = full_model.predict(X_future)

    future_df["forecasted_revenue"] = np.maximum(0.0, np.round(future_pred, 2))
    # 95% Confidence interval bounds using holdout RMSE
    future_df["lower_bound"] = np.maximum(0.0, np.round(future_df["forecasted_revenue"] - 1.96 * rmse, 2))
    future_df["upper_bound"] = np.round(future_df["forecasted_revenue"] + 1.96 * rmse, 2)

    # Generate Visualization: Actual vs Fitted vs Forecast
    plt.figure(figsize=(12, 6), dpi=200)
    plt.plot(df["period"], df["monthly_revenue"], "o-", color="#1E293B", label="Historical Actual", lw=2.2, markersize=6)
    plt.plot(test_df["period"], test_df["predicted"], "s--", color="#F59E0B", label=f"Holdout Backtest (MAE: ${mae:,.0f})", lw=2, markersize=6)
    plt.plot(future_df["period"], future_df["forecasted_revenue"], "^-", color="#10B981", label="Future Forecast (Next 6 Months)", lw=2.5, markersize=7)

    # Shaded confidence band for future forecast
    plt.fill_between(
        future_df["period"],
        future_df["lower_bound"],
        future_df["upper_bound"],
        color="#10B981",
        alpha=0.2,
        label="95% Prediction Interval"
    )

    plt.axvline(x=train_df["period"].iloc[-1], color="#94A3B8", linestyle=":", alpha=0.8)
    plt.axvline(x=df["period"].iloc[-1], color="#059669", linestyle="--", alpha=0.8)

    plt.title("Monthly Revenue Forecast with Trend & Seasonality Decomposition", fontsize=12, weight="bold")
    plt.xlabel("Timeline (Year-Month)")
    plt.ylabel("Revenue ($)")
    plt.xticks(rotation=45, ha="right", fontsize=8.5)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(loc="upper left")
    plt.tight_layout()

    forecast_fig = FIGURES_DIR / "sales_forecasting.png"
    plt.savefig(forecast_fig, bbox_inches="tight")
    plt.close()

    metrics = {
        "historical_months": n,
        "holdout_months": holdout_months,
        "forecast_horizon_months": forecast_horizon,
        "model_name": "Ridge Regression with Trend and Monthly Seasonality",
        "holdout_metrics": {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE_pct": round(mape, 2)
        },
        "benchmark_sma_metrics": {
            "MAE": round(sma_mae, 2),
            "RMSE": round(sma_rmse, 2)
        },
        "figures": {
            "sales_forecast": str(forecast_fig)
        }
    }

    return df, future_df, metrics

if __name__ == "__main__":
    hist, fut, met = run_sales_forecasting()
    print("Forecasting Metrics:")
    print(met)
    print("\nNext 6-Months Projection:")
    print(fut[["period", "forecasted_revenue", "lower_bound", "upper_bound"]])
