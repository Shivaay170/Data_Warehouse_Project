"""Market Basket Analysis using Apriori and FP-Growth Algorithms.

Extracts transaction itemsets from the warehouse, prepares one-hot encoded
baskets, runs and benchmarks both Apriori and FP-Growth via mlxtend,
extracts association rules (Support, Confidence, Lift), and produces
analytical rule charts and runtime performance comparisons.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL, FIGURES_DIR
from src.warehouse.create_schema import get_engine

def extract_baskets_from_dw(engine=None, sample_invoices: int = 5000) -> pd.DataFrame:
    """Extract transaction baskets from the warehouse and create one-hot encoded matrix."""
    if engine is None:
        engine = get_engine(DB_URL)

    # Query invoice lines with product descriptions
    query = """
    SELECT 
        f.invoice_no,
        p.description
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    ORDER BY f.invoice_no;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    # Limit to sample of invoices if very large for fast association mining
    unique_invoices = df["invoice_no"].unique()
    if len(unique_invoices) > sample_invoices:
        selected_invoices = set(unique_invoices[:sample_invoices])
        df = df[df["invoice_no"].isin(selected_invoices)]

    # Crosstab / pivot into Boolean matrix
    basket = pd.crosstab(df["invoice_no"], df["description"]).astype(bool)
    return basket

def run_market_basket_analysis(
    min_support: float = 0.015,
    min_lift: float = 1.2,
    min_confidence: float = 0.20,
    engine=None
) -> Tuple[pd.DataFrame, dict]:
    """Execute both Apriori and FP-Growth, benchmark runtimes, extract rules, and plot.

    Returns:
        (df_rules, metrics_dict)
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    basket = extract_baskets_from_dw(engine)
    num_transactions = len(basket)
    num_products = basket.shape[1]

    # Benchmark 1: Apriori
    start_apriori = time.perf_counter()
    freq_items_apriori = apriori(basket, min_support=min_support, use_colnames=True)
    time_apriori = round(time.perf_counter() - start_apriori, 4)

    # Benchmark 2: FP-Growth
    start_fpgrowth = time.perf_counter()
    freq_items_fpgrowth = fpgrowth(basket, min_support=min_support, use_colnames=True)
    time_fpgrowth = round(time.perf_counter() - start_fpgrowth, 4)

    # Derive association rules from the frequent itemsets
    if not freq_items_fpgrowth.empty:
        rules = association_rules(freq_items_fpgrowth, metric="lift", min_threshold=min_lift)
        # Filter by minimum confidence
        rules = rules[rules["confidence"] >= min_confidence].copy()
    else:
        rules = pd.DataFrame()

    if not rules.empty:
        # Format antecedents and consequents into readable strings
        rules["antecedents_str"] = rules["antecedents"].apply(lambda s: ", ".join(list(s)))
        rules["consequents_str"] = rules["consequents"].apply(lambda s: ", ".join(list(s)))
        rules["rule_str"] = rules["antecedents_str"] + "  ==>  " + rules["consequents_str"]
        rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)

        # Plot 1: Top 10 Association Rules by Lift
        top10 = rules.head(10).copy()
        plt.figure(figsize=(11, 6), dpi=200)
        top10_sorted = top10.sort_values("lift", ascending=True)
        bars = plt.barh(top10_sorted["rule_str"], top10_sorted["lift"], color="#3B82F6", edgecolor="#1D4ED8")
        plt.title("Top Association Rules by Lift (Basket Affinity)", fontsize=12, weight="bold")
        plt.xlabel("Lift Ratio (Values > 1.0 indicate strong positive co-occurrence)")
        plt.grid(axis="x", linestyle="--", alpha=0.5)
        # Add value labels on bars
        for bar in bars:
            w = bar.get_width()
            plt.text(w + 0.05, bar.get_y() + bar.get_height() / 2, f"{w:.2f}", va="center", fontsize=8.5, weight="bold")
        plt.tight_layout()
        rules_fig = FIGURES_DIR / "market_basket_rules.png"
        plt.savefig(rules_fig, bbox_inches="tight")
        plt.close()
    else:
        rules_fig = None

    # Plot 2: Algorithm Runtime Benchmark Comparison
    plt.figure(figsize=(7, 4.5), dpi=200)
    algorithms = ["Apriori", "FP-Growth"]
    runtimes = [time_apriori, time_fpgrowth]
    colors = ["#EF4444", "#10B981"]
    bars = plt.bar(algorithms, runtimes, color=colors, width=0.45, edgecolor="#334155")
    plt.title("Algorithm Runtime Comparison: Apriori vs FP-Growth", fontsize=11, weight="bold")
    plt.ylabel("Execution Time (Seconds)")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, h + 0.001, f"{h:.4f}s", ha="center", va="bottom", fontsize=9.5, weight="bold")
    plt.tight_layout()
    runtime_fig = FIGURES_DIR / "apriori_vs_fpgrowth_runtime.png"
    plt.savefig(runtime_fig, bbox_inches="tight")
    plt.close()

    metrics = {
        "transactions_analyzed": num_transactions,
        "distinct_items": num_products,
        "min_support": min_support,
        "min_lift": min_lift,
        "min_confidence": min_confidence,
        "rules_discovered": len(rules),
        "runtime_apriori_seconds": time_apriori,
        "runtime_fpgrowth_seconds": time_fpgrowth,
        "speedup_factor": round(time_apriori / (time_fpgrowth + 1e-6), 2),
        "figures": {
            "top_rules": str(rules_fig) if rules_fig else None,
            "runtime_comparison": str(runtime_fig)
        }
    }

    return rules, metrics

if __name__ == "__main__":
    rules, metrics = run_market_basket_analysis()
    print("Market Basket Metrics:", metrics)
    if not rules.empty:
        print("\nTop 5 Discovered Rules:")
        print(rules[["rule_str", "support", "confidence", "lift"]].head())
