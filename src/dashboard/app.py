"""Streamlit Executive Analytics and Data Mining Dashboard.

Provides an interactive enterprise portal for the Retail Data Warehouse:
1. Executive Overview & KPIs
2. Multi-Dimensional OLAP Cube Explorer (Roll-up, Drill-down, Slice, Dice, Pivot)
3. Customer Segmentation (RFM, K-Means, PCA, CSV Export)
4. Market Basket Analysis (Apriori vs FP-Growth, Rule Filtering)
5. Customer Churn Prediction (Model Benchmarks, ROC Curves, Real-time Customer Inference)
6. Sales Forecasting (Horizon Slider, 95% Confidence Intervals, Error Metrics)
7. Star Schema Architecture & ETL Data Quality Report
"""

import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure project path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.config import (
    DB_URL, DEFAULT_SQLITE_PATH, METRICS_FILE, DATA_QUALITY_REPORT_FILE,
    DOCS_DIR, FIGURES_DIR
)
from src.warehouse.create_schema import get_engine
from src.warehouse.olap import (
    get_kpis, olap_rollup, olap_drilldown, olap_slice, olap_dice, olap_pivot,
    get_top_products, get_top_customers, get_revenue_by_country
)
from src.mining.segmentation import run_customer_segmentation
from src.mining.association_rules import run_market_basket_analysis
from src.mining.churn import run_churn_pipeline, predict_customer_churn
from src.mining.forecasting import run_sales_forecasting

# Cached Data Loaders
@st.cache_data(ttl=600)
def load_kpis():
    return get_kpis()

@st.cache_data(ttl=600)
def load_rollup(level):
    return olap_rollup(level)

@st.cache_data(ttl=600)
def load_country_data():
    return get_revenue_by_country()

@st.cache_data(ttl=600)
def load_segmentation():
    return run_customer_segmentation()

@st.cache_data(ttl=600)
def load_market_basket(min_supp, min_lft, min_conf):
    return run_market_basket_analysis(min_support=min_supp, min_lift=min_lft, min_confidence=min_conf)

@st.cache_data(ttl=600)
def load_churn():
    return run_churn_pipeline()

@st.cache_data(ttl=600)
def load_forecast(horizon):
    return run_sales_forecasting(forecast_horizon=horizon)

def render_dashboard():
    """Render all Streamlit UI components."""
    # Custom Styling for polished enterprise dashboard
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            padding: 1.2rem;
            border-radius: 10px;
            color: #F8FAFC;
            border-left: 4px solid #3B82F6;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #38BDF8;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 18px;
            font-weight: 600;
            border-radius: 6px 6px 0 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header Section
    st.markdown('<div class="main-header">🛒 Retail Data Warehouse & Data Mining Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">B.Tech Final Year Capstone Project | Star Schema DW, OLAP Engine & Predictive Machine Learning</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        schema_img_path = DOCS_DIR / "star_schema_architecture.png"
        if schema_img_path.exists():
            st.image(str(schema_img_path), use_container_width=True)
        st.markdown("### System Controls & Architecture")
        st.info(f"**Database:** `{DB_URL.split('///')[-1] if '///' in DB_URL else DB_URL}`")
        
        if st.button("🔄 Refresh Cached Metrics", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown("**Core Modules:**")
        st.markdown("- 📊 Star Schema & ETL Engine\n- 🧊 Multi-Dimensional OLAP\n- 👥 K-Means RFM Segmentation\n- 🧺 Apriori / FP-Growth MBA\n- ⚠️ Churn Risk Predictor\n- 📈 Ridge Sales Forecasting")
        st.caption("Engineered with Python, SQLAlchemy, scikit-learn, mlxtend, & Streamlit.")

    # Main Navigation Tabs
    tabs = st.tabs([
        "📊 Executive Overview",
        "🧊 OLAP Explorer",
        "👥 Customer Segments",
        "🧺 Market Basket Analysis",
        "⚠️ Churn Prediction",
        "📈 Sales Forecasting",
        "📋 Data Quality & Architecture"
    ])

    # -------------------------------------------------------------
    # TAB 1: EXECUTIVE OVERVIEW
    # -------------------------------------------------------------
    with tabs[0]:
        st.subheader("Key Performance Indicators (KPIs)")
        kpis = load_kpis()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Revenue</div>
                <div class="metric-value">${kpis.get('total_revenue', 0):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Orders</div>
                <div class="metric-value">{kpis.get('total_orders', 0):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Customers</div>
                <div class="metric-value">{kpis.get('total_customers', 0):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Units Sold</div>
                <div class="metric-value">{kpis.get('total_units_sold', 0):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Order Value</div>
                <div class="metric-value">${kpis.get('avg_order_value', 0):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Monthly Trend & Country Distribution
        c_left, c_right = st.columns([1.6, 1.2])

        with c_left:
            st.markdown("#### Monthly Revenue Trajectory")
            monthly_df = load_rollup("monthly")
            fig_trend = px.line(
                monthly_df, x="year_month", y="total_revenue", markers=True,
                title="Monthly Revenue Trend (24-Month Historical)",
                labels={"year_month": "Year-Month", "total_revenue": "Revenue ($)"},
                color_discrete_sequence=["#2563EB"]
            )
            fig_trend.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_trend, use_container_width=True)

        with c_right:
            st.markdown("#### Revenue by Geographic Market")
            country_df = load_country_data()
            fig_pie = px.pie(
                country_df, names="country", values="total_revenue",
                title="Revenue Distribution by Country",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_pie.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

        # Top 10 Leaderboards
        col_p, col_c = st.columns(2)
        with col_p:
            st.markdown("#### Top 10 Best-Selling Products")
            top_prods = get_top_products(10)
            st.dataframe(
                top_prods[["stock_code", "description", "category", "units_sold", "total_revenue"]].rename(
                    columns={"stock_code": "Code", "description": "Product Description", "category": "Category", "units_sold": "Units", "total_revenue": "Revenue ($)"}
                ),
                use_container_width=True, hide_index=True
            )

        with col_c:
            st.markdown("#### Top 10 Highest-Value Customers")
            top_custs = get_top_customers(10)
            st.dataframe(
                top_custs[["customer_id", "country", "total_orders", "total_spent"]].rename(
                    columns={"customer_id": "Customer ID", "country": "Country", "total_orders": "Orders", "total_spent": "Total Spent ($)"}
                ),
                use_container_width=True, hide_index=True
            )

    # -------------------------------------------------------------
    # TAB 2: OLAP EXPLORER
    # -------------------------------------------------------------
    with tabs[1]:
        st.subheader("🧊 Multi-Dimensional OLAP Operations")
        st.markdown("Interactive slice-and-dice, hierarchy roll-up/drill-down, and category pivot cross-tabulations.")

        op_mode = st.radio("Select OLAP Operation:", ["Roll-up & Drill-down", "Slice & Dice", "Pivot Table (Cross-Tabulation)"], horizontal=True)

        if op_mode == "Roll-up & Drill-down":
            col_ctrl1, col_ctrl2 = st.columns([1, 2])
            with col_ctrl1:
                st.markdown("##### Roll-Up Aggregation Level")
                roll_level = st.selectbox("Ascend Time Hierarchy:", ["Yearly", "Quarterly", "Monthly", "Daily"])
                rollup_res = olap_rollup(roll_level.lower())
                st.dataframe(rollup_res, use_container_width=True)

            with col_ctrl2:
                st.markdown("##### Drill-Down into Year & Quarter")
                dd_year = st.selectbox("Select Year to Drill Down:", [2024, 2025])
                drill_q = st.radio("Quarter Granularity:", ["All Quarters", "Q1", "Q2", "Q3", "Q4"], horizontal=True)
                q_val = None if drill_q == "All Quarters" else int(drill_q[-1])
                drill_res = olap_drilldown(year=dd_year, quarter=q_val)
                
                fig_dd = px.bar(
                    drill_res, x="month_name", y="revenue", color="quarter",
                    title=f"Drill-down: {dd_year} Revenue by Month",
                    labels={"revenue": "Revenue ($)", "month_name": "Month", "quarter": "Quarter"},
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig_dd, use_container_width=True)

        elif op_mode == "Slice & Dice":
            c_filter1, c_filter2, c_filter3 = st.columns(3)
            with c_filter1:
                sel_countries = st.multiselect("Select Countries (Dice):", ["United Kingdom", "Germany", "France", "Spain", "Australia", "Netherlands"], default=["United Kingdom", "Germany", "France"])
            with c_filter2:
                sel_cats = st.multiselect("Select Categories (Dice):", ["Kitchen & Dining", "Home Decor", "Gifts & Accessories", "Stationery & Office", "Clothing & Apparel"], default=["Kitchen & Dining", "Home Decor"])
            with c_filter3:
                year_range = st.slider("Select Year Span:", 2024, 2025, (2024, 2025))

            dice_df = olap_dice(countries=sel_countries, categories=sel_cats, start_year=year_range[0], end_year=year_range[1])
            st.markdown(f"**Dice Result:** {len(dice_df)} multi-dimensional cells matched")

            if not dice_df.empty:
                fig_dice = px.bar(
                    dice_df, x="country", y="dice_revenue", color="category", barmode="group",
                    title="Diced Multi-Dimensional Revenue Sub-Cube",
                    labels={"dice_revenue": "Revenue ($)", "country": "Country", "category": "Product Category"}
                )
                st.plotly_chart(fig_dice, use_container_width=True)
                st.dataframe(dice_df, use_container_width=True)
            else:
                st.warning("No data matched the selected slice/dice criteria.")

        else: # Pivot Table
            st.markdown("##### Category x Month Revenue Cross-Tabulation (Pivot)")
            pivot_year = st.selectbox("Select Year for Pivot:", ["All Years (Aggregated)", 2024, 2025])
            pyear = None if pivot_year == "All Years (Aggregated)" else int(pivot_year)
            pivot_df = olap_pivot(year=pyear)
            
            st.dataframe(pivot_df, use_container_width=True)
            
            # Heatmap of Category vs Months
            months_cols = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            heat_data = pivot_df.set_index("category")[months_cols]
            fig_heat = px.imshow(
                heat_data, text_auto=True, aspect="auto", color_continuous_scale="Blues",
                title="Category Revenue Heatmap Across Calendar Months"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 3: CUSTOMER SEGMENTS
    # -------------------------------------------------------------
    with tabs[2]:
        st.subheader("👥 Customer RFM Segmentation & K-Means Clustering")
        st.markdown("Segmentation models built directly from the warehouse using Recency, Frequency, and Monetary features.")

        rfm_df, profile_df, seg_metrics = load_segmentation()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Customers Clustered", f"{seg_metrics['total_customers']:,}")
        with m2:
            st.metric("Number of Clusters (k)", seg_metrics["chosen_k"])
        with m3:
            st.metric("Silhouette Score", f"{seg_metrics['silhouette_score']:.3f}")
        with m4:
            st.metric("PCA Variance Explained", f"{sum(seg_metrics['pca_variance_explained'])*100:.1f}%")

        st.markdown("---")
        c_pca, c_prof = st.columns([1.3, 1.1])

        with c_pca:
            st.markdown("#### 2D PCA Cluster Scatter Visualization")
            fig_pca = px.scatter(
                rfm_df, x="pca_1", y="pca_2", color="segment",
                hover_data=["customer_id", "recency", "frequency", "monetary", "country"],
                title="Customer Clusters in 2D PCA Space",
                color_discrete_map={"Champions": "#10B981", "Loyal Customers": "#3B82F6", "At-Risk Customers": "#F59E0B", "Lost Customers": "#EF4444"}
            )
            fig_pca.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_pca, use_container_width=True)

        with c_prof:
            st.markdown("#### Segment Size & Revenue Contribution")
            fig_seg_bar = px.bar(
                profile_df, x="segment", y=["customer_pct", "revenue_pct"],
                barmode="group", title="Customer Count % vs Revenue Contribution %",
                labels={"value": "Percentage (%)", "variable": "Metric", "segment": "Segment"},
                color_discrete_sequence=["#3B82F6", "#10B981"]
            )
            st.plotly_chart(fig_seg_bar, use_container_width=True)

        st.markdown("#### Segment Behavioral Profiles")
        st.dataframe(profile_df, use_container_width=True, hide_index=True)

        csv_bytes = rfm_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Customer Segmentation CSV",
            data=csv_bytes,
            file_name="retail_customer_segments.csv",
            mime="text/csv",
            use_container_width=True
        )

    # -------------------------------------------------------------
    # TAB 4: MARKET BASKET ANALYSIS
    # -------------------------------------------------------------
    with tabs[3]:
        st.subheader("🧺 Market Basket Analysis (Apriori vs FP-Growth)")
        st.markdown("Mining frequent itemsets and high-lift association rules to drive product recommendations and cross-selling.")

        c_b1, c_b2, c_b3 = st.columns(3)
        with c_b1:
            min_supp = st.slider("Min Support Threshold:", 0.005, 0.05, 0.015, step=0.005)
        with c_b2:
            min_lft = st.slider("Min Lift Threshold:", 1.0, 5.0, 1.2, step=0.1)
        with c_b3:
            min_conf = st.slider("Min Confidence:", 0.1, 0.9, 0.2, step=0.05)

        rules_df, mb_metrics = load_market_basket(min_supp, min_lft, min_conf)

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.metric("Rules Discovered", mb_metrics["rules_discovered"])
        with b2:
            st.metric("Apriori Runtime", f"{mb_metrics['runtime_apriori_seconds']:.4f}s")
        with b3:
            st.metric("FP-Growth Runtime", f"{mb_metrics['runtime_fpgrowth_seconds']:.4f}s")
        with b4:
            st.metric("Transactions Tested", f"{mb_metrics['transactions_analyzed']:,}")

        st.markdown("---")

        if not rules_df.empty:
            c_r1, c_r2 = st.columns([1.4, 1.0])
            with c_r1:
                st.markdown("#### Association Rules Scatter (Support vs Confidence)")
                fig_rules = px.scatter(
                    rules_df, x="support", y="confidence", size="lift", color="lift",
                    hover_data=["rule_str"], color_continuous_scale="Viridis",
                    title="Support vs Confidence (Bubble Size = Lift Ratio)"
                )
                st.plotly_chart(fig_rules, use_container_width=True)

            with c_r2:
                st.markdown("#### Top Association Rules by Lift")
                top10_rules = rules_df.head(8).sort_values("lift", ascending=True)
                fig_lift_bar = px.bar(
                    top10_rules, y="rule_str", x="lift", orientation="h",
                    color="lift", color_continuous_scale="Blues",
                    title="Top Rules Ranked by Lift (Affinity)"
                )
                st.plotly_chart(fig_lift_bar, use_container_width=True)

            st.markdown("#### Discovered Rules Explorer")
            disp_cols = ["rule_str", "support", "confidence", "lift", "leverage"]
            st.dataframe(
                rules_df[disp_cols].rename(columns={
                    "rule_str": "Association Rule (Antecedent ==> Consequent)",
                    "support": "Support", "confidence": "Confidence", "lift": "Lift", "leverage": "Leverage"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("No rules discovered under current thresholds. Try reducing minimum support or lift.")

    # -------------------------------------------------------------
    # TAB 5: CHURN PREDICTION
    # -------------------------------------------------------------
    with tabs[4]:
        st.subheader("⚠️ Customer Churn Prediction & Early Warning System")
        st.markdown("Supervised classification models predicting customer churn probability based on historical ordering dynamics.")

        df_churn, churn_summary = load_churn()

        st.markdown("#### Supervised Classifier Performance Benchmark")
        m_cols = st.columns(3)
        for i, (mname, mstats) in enumerate(churn_summary["models"].items()):
            with m_cols[i]:
                is_best = (mname == churn_summary["best_model"])
                border_col = "#10B981" if is_best else "#3B82F6"
                badge = " ⭐ (Best Model)" if is_best else ""
                st.markdown(f"""
                <div style="border: 2px solid {border_col}; padding: 1rem; border-radius: 8px; background-color: #F8FAFC;">
                    <h4 style="margin: 0; color: #1E293B;">{mname}{badge}</h4>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                        <b>Accuracy:</b> {mstats['accuracy'] * 100:.1f}%<br>
                        <b>Precision:</b> {mstats['precision'] * 100:.1f}%<br>
                        <b>Recall:</b> {mstats['recall'] * 100:.1f}%<br>
                        <b>F1-Score:</b> {mstats['f1_score']:.3f}<br>
                        <b>ROC-AUC:</b> {mstats['roc_auc']:.3f}
                    </p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            st.markdown("#### ROC Curves Comparison")
            roc_path = FIGURES_DIR / "churn_roc_curves.png"
            if roc_path.exists():
                st.image(str(roc_path), use_container_width=True)
        with c_img2:
            st.markdown("#### Feature Importances")
            feat_path = FIGURES_DIR / "churn_feature_importance.png"
            if feat_path.exists():
                st.image(str(feat_path), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔍 Real-Time Customer Churn Risk Inference")
        st.markdown("Select an existing customer or input synthetic parameters to predict churn risk immediately.")

        pred_c1, pred_c2 = st.columns([1, 1])
        with pred_c1:
            cust_options = ["Select an existing customer..."] + list(df_churn["customer_id"].head(200))
            sel_c = st.selectbox("Choose Customer from Warehouse:", cust_options)

            if sel_c != "Select an existing customer...":
                row = df_churn[df_churn["customer_id"] == sel_c].iloc[0]
                in_order_count = int(row["order_count"])
                in_spend = float(row["total_spend"])
                in_aov = float(row["avg_order_value"])
                in_units = int(row["total_units"])
                in_prods = int(row["unique_products"])
                in_tenure = int(row["tenure_days"])
                in_interval = float(row["purchase_interval"])
            else:
                in_order_count = 3
                in_spend = 150.0
                in_aov = 50.0
                in_units = 25
                in_prods = 4
                in_tenure = 200
                in_interval = 45.0

            p1, p2 = st.columns(2)
            with p1:
                u_orders = st.number_input("Total Orders:", value=in_order_count, min_value=1)
                u_spend = st.number_input("Total Spend ($):", value=in_spend, min_value=0.0)
                u_aov = st.number_input("Average Order Value ($):", value=in_aov, min_value=0.0)
                u_units = st.number_input("Total Units Purchased:", value=in_units, min_value=1)
            with p2:
                u_prods = st.number_input("Unique Products:", value=in_prods, min_value=1)
                u_tenure = st.number_input("Customer Tenure (Days):", value=in_tenure, min_value=1)
                u_interval = st.number_input("Avg Purchase Interval (Days):", value=in_interval, min_value=0.0)

        with pred_c2:
            st.markdown("#### Inference Result")
            features_dict = {
                "order_count": u_orders,
                "total_spend": u_spend,
                "avg_order_value": u_aov,
                "total_units": u_units,
                "avg_units_per_order": u_units / u_orders if u_orders > 0 else 0,
                "unique_products": u_prods,
                "tenure_days": u_tenure,
                "purchase_interval": u_interval
            }

            if st.button("🔮 Run Churn Prediction Model", use_container_width=True):
                pred_res = predict_customer_churn(features_dict)
                prob_pct = pred_res["churn_probability"] * 100
                if pred_res["churn_prediction"] == 1:
                    st.error(f"⚠️ **High Churn Risk!** ({prob_pct:.1f}% estimated probability)")
                    st.markdown("Recommended action: Trigger win-back discount email and personalized retention campaign.")
                else:
                    st.success(f"✅ **Customer Retained!** (Only {prob_pct:.1f}% churn risk)")
                    st.markdown("Customer exhibits healthy repeat purchase rhythm.")

    # -------------------------------------------------------------
    # TAB 6: SALES FORECASTING
    # -------------------------------------------------------------
    with tabs[5]:
        st.subheader("📈 Monthly Sales Revenue Forecasting")
        st.markdown("Trend and seasonality decomposition forecasting model evaluating future revenue bounds.")

        horizon = st.slider("Select Forecast Horizon (Months):", 1, 12, 6)
        hist_df, future_df, f_metrics = load_forecast(horizon)

        f1, f2, f3 = st.columns(3)
        with f1:
            st.metric("Holdout Backtest MAE", f"${f_metrics['holdout_metrics']['MAE']:,.2f}")
        with f2:
            st.metric("Holdout Backtest RMSE", f"${f_metrics['holdout_metrics']['RMSE']:,.2f}")
        with f3:
            st.metric("Holdout MAPE", f"{f_metrics['holdout_metrics']['MAPE_pct']:.1f}%")

        st.markdown("---")

        fig_f = go.Figure()
        fig_f.add_trace(go.Scatter(
            x=hist_df["period"], y=hist_df["monthly_revenue"],
            mode="lines+markers", name="Historical Actual Revenue",
            line=dict(color="#1E293B", width=2.5)
        ))
        fig_f.add_trace(go.Scatter(
            x=future_df["period"], y=future_df["forecasted_revenue"],
            mode="lines+markers", name="Forecasted Revenue",
            line=dict(color="#10B981", width=3, dash="solid")
        ))
        fig_f.add_trace(go.Scatter(
            x=future_df["period"], y=future_df["upper_bound"],
            mode="lines", line=dict(color="rgba(16, 185, 129, 0)"),
            showlegend=False
        ))
        fig_f.add_trace(go.Scatter(
            x=future_df["period"], y=future_df["lower_bound"],
            mode="lines", line=dict(color="rgba(16, 185, 129, 0)"),
            fill="tonexty", fillcolor="rgba(16, 185, 129, 0.2)",
            name="95% Prediction Interval"
        ))

        fig_f.update_layout(
            title=f"Sales Forecast for Next {horizon} Months with 95% Confidence Bounds",
            xaxis_title="Timeline (Year-Month)",
            yaxis_title="Monthly Revenue ($)",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_f, use_container_width=True)

        st.markdown("#### Projected Monthly Revenue Table")
        st.dataframe(
            future_df[["period", "forecasted_revenue", "lower_bound", "upper_bound"]].rename(columns={
                "period": "Period",
                "forecasted_revenue": "Forecast Revenue ($)",
                "lower_bound": "95% Lower Bound ($)",
                "upper_bound": "95% Upper Bound ($)"
            }),
            use_container_width=True, hide_index=True
        )

    # -------------------------------------------------------------
    # TAB 7: DATA QUALITY & ARCHITECTURE
    # -------------------------------------------------------------
    with tabs[6]:
        st.subheader("📋 Star Schema Architecture & ETL Data Quality Audit")

        c_arch, c_qa = st.columns([1.2, 1.0])
        with c_arch:
            st.markdown("#### Warehouse Star Schema ER Diagram")
            schema_img = DOCS_DIR / "star_schema_architecture.png"
            if schema_img.exists():
                st.image(str(schema_img), use_container_width=True)

        with c_qa:
            st.markdown("#### ETL Data Quality Audit Report")
            if DATA_QUALITY_REPORT_FILE.exists():
                with open(DATA_QUALITY_REPORT_FILE, "r", encoding="utf-8") as f:
                    dq = json.load(f)
                st.json(dq)
            else:
                st.info("Run ETL pipeline to generate data quality report.")

# Set page config at top if script runs in Streamlit
try:
    st.set_page_config(
        page_title="Retail Data Warehouse & Analytics",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    pass

# Execute UI if running under streamlit runtime
if st.runtime.exists():
    render_dashboard()
