"""Customer Churn Prediction Module.

Defines customer churn (no transaction in > 90 days), engineers behavioral
features from the warehouse, trains Logistic Regression, Decision Tree, and
Random Forest classifiers with class imbalance handling, computes comprehensive
classification metrics, generates ROC curves and confusion matrices, and persists
the best performing model using joblib.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score, roc_curve
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    CHURN_DAYS_THRESHOLD, DB_URL, FIGURES_DIR, PROCESSED_DATA_DIR, RANDOM_STATE
)
from src.warehouse.create_schema import get_engine

CHURN_MODEL_FILE = PROCESSED_DATA_DIR / "best_churn_model.joblib"

def extract_churn_dataset(engine=None, churn_threshold_days: int = CHURN_DAYS_THRESHOLD) -> pd.DataFrame:
    """Extract customer transactional history from the warehouse and compute feature vectors."""
    if engine is None:
        engine = get_engine(DB_URL)

    with engine.connect() as conn:
        max_date_str = conn.execute(text("SELECT MAX(full_date) FROM dim_date WHERE date_key IN (SELECT date_key FROM fact_sales);")).scalar()
    
    ref_date = pd.to_datetime(max_date_str)

    query = """
    SELECT 
        c.customer_id,
        d.full_date,
        f.invoice_no,
        f.product_key,
        f.quantity,
        f.total_amount
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.date_key = d.date_key;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    df["full_date"] = pd.to_datetime(df["full_date"])

    # Aggregate customer behavioral metrics
    grouped = df.groupby("customer_id")
    features = []

    for cid, g in grouped:
        first_date = g["full_date"].min()
        last_date = g["full_date"].max()
        recency = (ref_date - last_date).days
        tenure = (ref_date - first_date).days
        order_count = g["invoice_no"].nunique()
        total_spend = g["total_amount"].sum()
        total_units = g["quantity"].sum()
        unique_prods = g["product_key"].nunique()
        
        avg_order_value = total_spend / order_count if order_count > 0 else 0
        avg_units_per_order = total_units / order_count if order_count > 0 else 0
        purchase_interval = (last_date - first_date).days / (order_count - 1) if order_count > 1 else 0

        churn_label = 1 if recency > churn_threshold_days else 0

        features.append({
            "customer_id": cid,
            "order_count": order_count,
            "total_spend": round(total_spend, 2),
            "avg_order_value": round(avg_order_value, 2),
            "total_units": total_units,
            "avg_units_per_order": round(avg_units_per_order, 2),
            "unique_products": unique_prods,
            "tenure_days": tenure,
            "purchase_interval": round(purchase_interval, 2),
            "churn": churn_label
        })

    return pd.DataFrame(features)

def train_churn_models(
    df: pd.DataFrame, 
    random_state: int = RANDOM_STATE
) -> Tuple[Dict[str, dict], str, Path]:
    """Train multiple classifiers, evaluate performance, and save the best model."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    feature_cols = [
        "order_count", "total_spend", "avg_order_value",
        "total_units", "avg_units_per_order", "unique_products",
        "tenure_days", "purchase_interval"
    ]

    X = df[feature_cols].copy()
    y = df["churn"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    # Standard Scaler for distance/linear models
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Models dictionary
    models = {
        "Logistic Regression": {
            "model": LogisticRegression(class_weight="balanced", random_state=random_state, max_iter=1000),
            "use_scaled": True
        },
        "Decision Tree": {
            "model": DecisionTreeClassifier(class_weight="balanced", max_depth=5, random_state=random_state),
            "use_scaled": False
        },
        "Random Forest": {
            "model": RandomForestClassifier(n_estimators=100, class_weight="balanced", max_depth=6, random_state=random_state),
            "use_scaled": False
        }
    }

    results = {}
    best_f1 = -1.0
    best_name = None
    best_model_obj = None

    plt.figure(figsize=(8, 6), dpi=200)

    for name, config in models.items():
        clf = config["model"]
        x_tr = X_train_scaled if config["use_scaled"] else X_train
        x_te = X_test_scaled if config["use_scaled"] else X_test

        clf.fit(x_tr, y_train)
        y_pred = clf.predict(x_te)
        y_prob = clf.predict_proba(x_te)[:, 1] if hasattr(clf, "predict_proba") else y_pred

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        roc = float(roc_auc_score(y_test, y_prob))
        cm = confusion_matrix(y_test, y_pred).tolist()

        fpr, tpr, _ = roc_curve(y_test, y_prob)
        plt.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {roc:.3f})")

        results[name] = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc, 4),
            "confusion_matrix": cm,
            "model_instance": clf
        }

        if f1 > best_f1:
            best_f1 = f1
            best_name = name
            best_model_obj = clf

    # Finalize ROC curves plot
    plt.plot([0, 1], [0, 1], "k--", lw=1.5, alpha=0.7)
    plt.title("ROC Curves Comparison for Customer Churn Classifiers", fontsize=12, weight="bold")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle="--", alpha=0.4)
    roc_fig_path = FIGURES_DIR / "churn_roc_curves.png"
    plt.savefig(roc_fig_path, bbox_inches="tight")
    plt.close()

    # Plot Confusion Matrix of best model
    best_cm = np.array(results[best_name]["confusion_matrix"])
    plt.figure(figsize=(6, 5), dpi=200)
    sns.heatmap(best_cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Retained", "Churned"], yticklabels=["Retained", "Churned"])
    plt.title(f"Confusion Matrix: {best_name}", fontsize=11, weight="bold")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.tight_layout()
    cm_fig_path = FIGURES_DIR / "churn_confusion_matrix.png"
    plt.savefig(cm_fig_path, bbox_inches="tight")
    plt.close()

    # Feature Importance for Best Model (if Tree-based)
    feat_imp = {}
    if hasattr(best_model_obj, "feature_importances_"):
        importances = best_model_obj.feature_importances_
        indices = np.argsort(importances)[::-1]
        sorted_feats = [feature_cols[i] for i in indices]
        sorted_vals = [importances[i] for i in indices]
        feat_imp = {f: round(float(v), 4) for f, v in zip(sorted_feats, sorted_vals)}

        plt.figure(figsize=(9, 5), dpi=200)
        plt.barh(sorted_feats[::-1], sorted_vals[::-1], color="#3B82F6", edgecolor="#1D4ED8")
        plt.title(f"Feature Importances ({best_name})", fontsize=11, weight="bold")
        plt.xlabel("Relative Importance")
        plt.grid(axis="x", linestyle="--", alpha=0.4)
        plt.tight_layout()
        feat_fig_path = FIGURES_DIR / "churn_feature_importance.png"
        plt.savefig(feat_fig_path, bbox_inches="tight")
        plt.close()
    else:
        feat_fig_path = None

    # Save best model bundle
    bundle = {
        "model_name": best_name,
        "model": best_model_obj,
        "scaler": scaler,
        "feature_cols": feature_cols,
        "is_scaled": models[best_name]["use_scaled"],
        "metrics": {k: v for k, v in results[best_name].items() if k != "model_instance"}
    }
    CHURN_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, CHURN_MODEL_FILE)

    summary = {
        "total_samples": len(df),
        "churn_rate_pct": round(100.0 * df["churn"].mean(), 2),
        "best_model": best_name,
        "feature_importances": feat_imp,
        "models": {k: {mk: mv for mk, mv in v.items() if mk != "model_instance"} for k, v in results.items()},
        "figures": {
            "roc_curves": str(roc_fig_path),
            "confusion_matrix": str(cm_fig_path),
            "feature_importance": str(feat_fig_path) if feat_fig_path else None
        }
    }
    return summary, best_name, CHURN_MODEL_FILE

def run_churn_pipeline(engine=None) -> Tuple[pd.DataFrame, dict]:
    """Execute end-to-end churn analysis pipeline."""
    df_churn = extract_churn_dataset(engine)
    summary, best_model, model_path = train_churn_models(df_churn)
    return df_churn, summary

def predict_customer_churn(customer_features: dict, model_path: Path = CHURN_MODEL_FILE) -> dict:
    """Inference helper to predict churn probability for an individual customer."""
    if not model_path.exists():
        raise FileNotFoundError(f"Trained churn model not found at {model_path}. Train model first.")
    
    bundle = joblib.load(model_path)
    model = bundle["model"]
    scaler = bundle["scaler"]
    feature_cols = bundle["feature_cols"]
    use_scaled = bundle["is_scaled"]

    # Assemble vector
    vec = pd.DataFrame([{col: customer_features.get(col, 0.0) for col in feature_cols}])
    if use_scaled:
        vec_processed = scaler.transform(vec)
    else:
        vec_processed = vec

    pred = int(model.predict(vec_processed)[0])
    prob = float(model.predict_proba(vec_processed)[0][1]) if hasattr(model, "predict_proba") else float(pred)

    return {
        "churn_prediction": pred,
        "churn_label": "High Risk of Churn" if pred == 1 else "Likely to Retain",
        "churn_probability": round(prob, 4)
    }

if __name__ == "__main__":
    df_churn, summary = run_churn_pipeline()
    print("Churn Pipeline Summary:")
    print(f"Total customers: {summary['total_samples']}, Churn rate: {summary['churn_rate_pct']}%")
    print(f"Best Model: {summary['best_model']}")
    for mname, mres in summary["models"].items():
        print(f" - {mname}: Accuracy={mres['accuracy']}, F1={mres['f1_score']}, AUC={mres['roc_auc']}")
