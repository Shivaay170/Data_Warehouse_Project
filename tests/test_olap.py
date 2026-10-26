"""Tests for multi-dimensional OLAP queries and mathematical reconciliation."""

import pytest
from sqlalchemy import text
from src.config import DB_URL
from src.warehouse.create_schema import get_engine
from src.warehouse.olap import (
    get_kpis, olap_rollup, olap_drilldown, olap_slice, olap_dice, olap_pivot,
    get_top_products, get_top_customers, get_revenue_by_country
)

@pytest.fixture(scope="module")
def db_engine():
    return get_engine(DB_URL)

def test_kpi_summary(db_engine):
    """Verify KPI figures match fact table aggregations."""
    kpis = get_kpis(db_engine)
    assert kpis["total_revenue"] > 0
    assert kpis["total_orders"] > 0
    assert kpis["total_customers"] > 0
    assert kpis["avg_order_value"] > 0

    with db_engine.connect() as conn:
        fact_rev = conn.execute(text("SELECT ROUND(SUM(total_amount), 2) FROM fact_sales;")).scalar()
        fact_orders = conn.execute(text("SELECT COUNT(DISTINCT invoice_no) FROM fact_sales;")).scalar()
    
    assert abs(kpis["total_revenue"] - fact_rev) < 0.05
    assert kpis["total_orders"] == fact_orders

def test_rollup_totals_reconciliation(db_engine):
    """Verify that totals at every roll-up hierarchy (daily, monthly, quarterly, yearly) match the fact table total."""
    with db_engine.connect() as conn:
        fact_total = conn.execute(text("SELECT ROUND(SUM(total_amount), 2) FROM fact_sales;")).scalar()

    # Yearly Roll-up
    df_year = olap_rollup("yearly", db_engine)
    year_sum = round(df_year["total_revenue"].sum(), 2)
    assert abs(year_sum - fact_total) < 0.05, f"Yearly rollup sum {year_sum} != Fact total {fact_total}"

    # Quarterly Roll-up
    df_quarter = olap_rollup("quarterly", db_engine)
    quarter_sum = round(df_quarter["total_revenue"].sum(), 2)
    assert abs(quarter_sum - fact_total) < 0.05, f"Quarterly rollup sum {quarter_sum} != Fact total {fact_total}"

    # Monthly Roll-up
    df_month = olap_rollup("monthly", db_engine)
    month_sum = round(df_month["total_revenue"].sum(), 2)
    assert abs(month_sum - fact_total) < 0.05, f"Monthly rollup sum {month_sum} != Fact total {fact_total}"

    # Daily Roll-up
    df_daily = olap_rollup("daily", db_engine)
    daily_sum = round(df_daily["total_revenue"].sum(), 2)
    assert abs(daily_sum - fact_total) < 0.05, f"Daily rollup sum {daily_sum} != Fact total {fact_total}"

def test_drilldown_results(db_engine):
    """Verify drill-down query returns granular data for selected year."""
    df_dd = olap_drilldown(year=2024, quarter=1, engine=db_engine)
    assert not df_dd.empty
    assert set(df_dd["quarter"]) == {1}
    assert set(df_dd["month"]).issubset({1, 2, 3})

def test_slice_and_dice(db_engine):
    """Verify slice and multi-dimensional dice queries."""
    # Slice on single country
    df_slice = olap_slice(country="United Kingdom", year=2024, engine=db_engine)
    assert not df_slice.empty
    assert (df_slice["country"] == "United Kingdom").all()

    # Dice on countries + categories
    countries = ["United Kingdom", "Germany"]
    categories = ["Kitchen & Dining", "Home Decor"]
    df_dice = olap_dice(countries=countries, categories=categories, start_year=2024, end_year=2025, engine=db_engine)
    assert not df_dice.empty
    assert set(df_dice["country"]).issubset(set(countries))
    assert set(df_dice["category"]).issubset(set(categories))

def test_pivot_table(db_engine):
    """Verify category x month cross-tabulation table."""
    df_pivot = olap_pivot(engine=db_engine)
    assert not df_pivot.empty
    expected_cols = ["category", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total_Revenue"]
    for c in expected_cols:
        assert c in df_pivot.columns
    # Check that sum of Total_Revenue in pivot matches fact total
    with db_engine.connect() as conn:
        fact_total = conn.execute(text("SELECT ROUND(SUM(total_amount), 2) FROM fact_sales;")).scalar()
    assert abs(df_pivot["Total_Revenue"].sum() - fact_total) < 0.5
