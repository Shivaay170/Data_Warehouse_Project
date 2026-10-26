"""Customer Segmentation Module using RFM Analysis and K-Means Clustering.

Extracts customer purchasing behavior directly from the warehouse, calculates
Recency, Frequency, and Monetary (RFM) metrics, evaluates optimal clusters k
using Elbow (Inertia) and Silhouette scores, applies K-Means, maps clusters to
business personas (Champions, Loyal, At-Risk, Lost), and generates 2D PCA visualizations.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL, FIGURES_DIR, RANDOM_STATE
from src.warehouse.create_schema import get_engine

def extract_rfm_data(engine=None) -> pd.DataFrame:
    """Query transactional sales from warehouse to compute RFM metrics per customer."""
    if engine is None:
        engine = get_engine(DB_URL)

    # Calculate max date in warehouse as reference point
    with engine.connect() as conn:
        max_date_str = conn.execute(text("SELECT MAX(full_date) FROM dim_date WHERE date_key IN (SELECT date_key FROM fact_sales);")).scalar()
    
    if not max_date_str:
        raise ValueError("Warehouse fact_sales table is empty! Run ETL before data mining.")

    ref_date = pd.to_datetime(max_date_str)

    # Query customer transactions with invoice dates
    query = """
    SELECT 
        c.customer_id,
        c.country,
        d.full_date,
        f.invoice_no,
        f.total_amount
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.date_key = d.date_key;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    df["full_date"] = pd.to_datetime(df["full_date"])

    # Aggregate by customer
    rfm = df.groupby(["customer_id", "country"]).agg(
        last_purchase=("full_date", "max"),
        frequency=("invoice_no", "nunique"),
        monetary=("total_amount", "sum")
    ).reset_index()

    rfm["recency"] = (ref_date - rfm["last_purchase"]).dt.days
    rfm["monetary"] = rfm["monetary"].round(2)
    return rfm[["customer_id", "country", "recency", "frequency", "monetary"]]

def find_optimal_k(X_scaled: np.ndarray, k_range=range(2, 8)) -> Tuple[int, Dict[int, float], Dict[int, float]]:
    """Compute inertia and silhouette scores across cluster counts to determine best k."""
    inertias = {}
    silhouettes = {}

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias[k] = float(km.inertia_)
        silhouettes[k] = float(silhouette_score(X_scaled, labels))

    # Pick k with highest silhouette score
    best_k = max(silhouettes, key=silhouettes.get)
    return best_k, inertias, silhouettes

def run_customer_segmentation(engine=None, n_clusters: int = 4) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Execute complete RFM segmentation, clustering, profiling, and plotting.

    Returns:
        (df_rfm_clustered, df_profiles, metrics_dict)
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rfm = extract_rfm_data(engine)

    # Feature scaling: log1p to reduce skewness, then standard scaling
    rfm_features = rfm[["recency", "frequency", "monetary"]].copy()
    rfm_log = np.log1p(rfm_features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(rfm_log)

    # Evaluate k
    optimal_k, inertias, silhouettes = find_optimal_k(X_scaled)
    # Target 4 clusters for business interpretability (Champions, Loyal, At-Risk, Lost)
    k = n_clusters or 4

    kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=15)
    rfm["cluster"] = kmeans.fit_predict(X_scaled)

    # Profile clusters by mean R, F, M
    cluster_means = rfm.groupby("cluster").agg(
        recency_mean=("recency", "mean"),
        frequency_mean=("frequency", "mean"),
        monetary_mean=("monetary", "mean")
    )

    # Rank clusters:
    # Champions: Low recency, high frequency, high monetary
    # Loyal: Moderate-low recency, moderate frequency, moderate-high monetary
    # At-Risk: Higher recency, moderate frequency
    # Lost: High recency, low frequency, low monetary
    def get_span(s: pd.Series) -> float:
        return float(s.max() - s.min())

    f_span = get_span(cluster_means["frequency_mean"]) + 1e-5
    m_span = get_span(cluster_means["monetary_mean"]) + 1e-5
    r_span = get_span(cluster_means["recency_mean"]) + 1e-5

    score = (
        (cluster_means["frequency_mean"] - cluster_means["frequency_mean"].min()) / f_span +
        (cluster_means["monetary_mean"] - cluster_means["monetary_mean"].min()) / m_span -
        (cluster_means["recency_mean"] - cluster_means["recency_mean"].min()) / r_span
    )
    ranked_clusters = score.sort_values(ascending=False).index.tolist()

    label_names = ["Champions", "Loyal Customers", "At-Risk Customers", "Lost Customers"]
    # In case k != 4, adapt
    label_map = {}
    for i, c_idx in enumerate(ranked_clusters):
        if i < len(label_names):
            label_map[c_idx] = label_names[i]
        else:
            label_map[c_idx] = f"Segment {i+1}"

    rfm["segment"] = rfm["cluster"].map(label_map)

    # PCA 2D Projection
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    coords = pca.fit_transform(X_scaled)
    rfm["pca_1"] = coords[:, 0]
    rfm["pca_2"] = coords[:, 1]
    explained_var = [round(float(v), 4) for v in pca.explained_variance_ratio_]

    # Generate Plot 1: Elbow and Silhouette curve
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=200)
    fig.patch.set_facecolor("#F8FAFC")
    ax1.set_facecolor("#FFFFFF")
    ax2.set_facecolor("#FFFFFF")

    ks = list(inertias.keys())
    ax1.plot(ks, list(inertias.values()), "o-", color="#2563EB", lw=2, markersize=7)
    ax1.set_title("Elbow Method (Inertia)", fontsize=11, weight="bold")
    ax1.set_xlabel("Number of Clusters (k)")
    ax1.set_ylabel("Inertia (Within-Cluster Sum of Squares)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2.plot(ks, list(silhouettes.values()), "s-", color="#059669", lw=2, markersize=7)
    ax2.set_title("Silhouette Score by Cluster Count", fontsize=11, weight="bold")
    ax2.set_xlabel("Number of Clusters (k)")
    ax2.set_ylabel("Silhouette Coefficient")
    ax2.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    elbow_file = FIGURES_DIR / "rfm_elbow_silhouette.png"
    plt.savefig(elbow_file, bbox_inches="tight")
    plt.close()

    # Generate Plot 2: 2D PCA Cluster Scatter
    plt.figure(figsize=(9, 6), dpi=200)
    palette = {"Champions": "#10B981", "Loyal Customers": "#3B82F6", "At-Risk Customers": "#F59E0B", "Lost Customers": "#EF4444"}
    sns.scatterplot(
        data=rfm,
        x="pca_1",
        y="pca_2",
        hue="segment",
        palette=palette,
        alpha=0.85,
        s=60,
        edgecolor="w",
        linewidth=0.5
    )
    plt.title(f"Customer Segments in 2D PCA Space (Variance Explained: {round(sum(explained_var)*100, 1)}%)", fontsize=12, weight="bold")
    plt.xlabel(f"Principal Component 1 ({round(explained_var[0]*100, 1)}%)")
    plt.ylabel(f"Principal Component 2 ({round(explained_var[1]*100, 1)}%)")
    plt.legend(title="Customer Segment", loc="best")
    plt.grid(True, linestyle="--", alpha=0.4)
    pca_file = FIGURES_DIR / "rfm_clusters_pca.png"
    plt.savefig(pca_file, bbox_inches="tight")
    plt.close()

    # Segment Profile Table
    total_revenue = rfm["monetary"].sum()
    profile = rfm.groupby("segment").agg(
        customer_count=("customer_id", "count"),
        recency_avg=("recency", lambda x: round(x.mean(), 1)),
        frequency_avg=("frequency", lambda x: round(x.mean(), 1)),
        monetary_avg=("monetary", lambda x: round(x.mean(), 2)),
        total_revenue=("monetary", "sum")
    ).reset_index()

    profile["revenue_pct"] = (profile["total_revenue"] / total_revenue * 100).round(2)
    profile["customer_pct"] = (profile["customer_count"] / len(rfm) * 100).round(2)

    metrics = {
        "total_customers": len(rfm),
        "chosen_k": k,
        "silhouette_score": round(silhouettes[k], 4),
        "inertias": inertias,
        "silhouettes": silhouettes,
        "pca_variance_explained": explained_var,
        "figures": {
            "elbow_silhouette": str(elbow_file),
            "pca_clusters": str(pca_file)
        }
    }

    return rfm, profile, metrics

if __name__ == "__main__":
    rfm_df, prof_df, metrics = run_customer_segmentation()
    print("Metrics:", metrics)
    print("\nSegment Profiles:")
    print(prof_df)
