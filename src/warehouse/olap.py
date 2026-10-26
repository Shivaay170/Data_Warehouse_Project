"""OLAP Engine and Analytical Query Interface.

Provides programmatic execution of core OLAP operations against the Star Schema:
- Roll-up (Aggregation across date hierarchies: Day -> Month -> Quarter -> Year)
- Drill-down (De-aggregation into granular time slices)
- Slice (Filtering on a specific dimension coordinate)
- Dice (Multi-dimensional sub-cube extraction)
- Pivot (Matrix cross-tabulation across Category and Months)
- Top-N Leaderboards and Executive KPI summaries
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL
from src.warehouse.create_schema import get_engine

def get_kpis(engine=None) -> Dict[str, float]:
    """Retrieve executive high-level retail KPIs."""
    if engine is None:
        engine = get_engine(DB_URL)

    query = """
    SELECT 
        ROUND(SUM(total_amount), 2) AS total_revenue,
        COUNT(DISTINCT invoice_no) AS total_orders,
        COUNT(DISTINCT customer_key) AS total_customers,
        SUM(quantity) AS total_units_sold,
        ROUND(SUM(total_amount) / COUNT(DISTINCT invoice_no), 2) AS avg_order_value
    FROM fact_sales;
    """
    with engine.connect() as conn:
        res = conn.execute(text(query)).mappings().first()
        return dict(res) if res else {}

def olap_rollup(level: str = "monthly", engine=None) -> pd.DataFrame:
    """Execute Roll-up aggregation across date hierarchies: 'yearly', 'quarterly', 'monthly', or 'daily'."""
    if engine is None:
        engine = get_engine(DB_URL)

    level = level.lower().strip()
    if level == "yearly":
        query = """
        SELECT 
            d.year,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.quantity) AS total_items,
            ROUND(SUM(f.total_amount), 2) AS total_revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year
        ORDER BY d.year;
        """
    elif level == "quarterly":
        query = """
        SELECT 
            d.year,
            d.quarter,
            printf('%d-Q%d', d.year, d.quarter) AS period,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.quantity) AS total_items,
            ROUND(SUM(f.total_amount), 2) AS total_revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.quarter
        ORDER BY d.year, d.quarter;
        """
    elif level == "daily":
        query = """
        SELECT 
            d.full_date,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.quantity) AS total_items,
            ROUND(SUM(f.total_amount), 2) AS total_revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.full_date
        ORDER BY d.full_date;
        """
    else:  # default monthly
        query = """
        SELECT 
            d.year,
            d.month,
            d.month_name,
            printf('%d-%02d', d.year, d.month) AS year_month,
            COUNT(DISTINCT f.invoice_no) AS total_orders,
            SUM(f.quantity) AS total_items,
            ROUND(SUM(f.total_amount), 2) AS total_revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month;
        """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def olap_drilldown(year: int = 2024, quarter: Optional[int] = None, engine=None) -> pd.DataFrame:
    """Execute Drill-down into finer temporal granularity for a selected year / quarter."""
    if engine is None:
        engine = get_engine(DB_URL)

    where_clauses = ["d.year = :year"]
    params = {"year": year}

    if quarter is not None:
        where_clauses.append("d.quarter = :quarter")
        params["quarter"] = quarter

    where_sql = " AND ".join(where_clauses)
    query = f"""
    SELECT 
        d.year,
        d.quarter,
        d.month,
        d.month_name,
        COUNT(DISTINCT f.invoice_no) AS total_orders,
        SUM(f.quantity) AS total_units,
        ROUND(SUM(f.total_amount), 2) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE {where_sql}
    GROUP BY d.year, d.quarter, d.month, d.month_name
    ORDER BY d.quarter, d.month;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def olap_slice(country: Optional[str] = None, year: Optional[int] = None, engine=None) -> pd.DataFrame:
    """Execute Slice operation filtering along a specific country and/or year."""
    if engine is None:
        engine = get_engine(DB_URL)

    where_parts = []
    params = {}
    if country:
        where_parts.append("l.country = :country")
        params["country"] = country
    if year:
        where_parts.append("d.year = :year")
        params["year"] = year

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    query = f"""
    SELECT 
        l.country,
        p.category,
        COUNT(DISTINCT f.invoice_no) AS order_count,
        SUM(f.quantity) AS units_sold,
        ROUND(SUM(f.total_amount), 2) AS slice_revenue
    FROM fact_sales f
    JOIN dim_location l ON f.location_key = l.location_key
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d ON f.date_key = d.date_key
    {where_sql}
    GROUP BY l.country, p.category
    ORDER BY slice_revenue DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def olap_dice(
    countries: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    engine=None
) -> pd.DataFrame:
    """Execute Dice operation filtering across multiple dimension subsets simultaneously."""
    if engine is None:
        engine = get_engine(DB_URL)

    clauses = ["1=1"]
    params = {}

    if countries:
        c_placeholders = [f":c_{i}" for i in range(len(countries))]
        clauses.append(f"l.country IN ({', '.join(c_placeholders)})")
        for i, c in enumerate(countries):
            params[f"c_{i}"] = c

    if categories:
        cat_placeholders = [f":cat_{i}" for i in range(len(categories))]
        clauses.append(f"p.category IN ({', '.join(cat_placeholders)})")
        for i, cat in enumerate(categories):
            params[f"cat_{i}"] = cat

    if start_year is not None:
        clauses.append("d.year >= :start_year")
        params["start_year"] = start_year

    if end_year is not None:
        clauses.append("d.year <= :end_year")
        params["end_year"] = end_year

    where_sql = " AND ".join(clauses)

    query = f"""
    SELECT 
        l.country,
        p.category,
        d.year,
        COUNT(DISTINCT f.invoice_no) AS total_orders,
        SUM(f.quantity) AS units_sold,
        ROUND(SUM(f.total_amount), 2) AS dice_revenue
    FROM fact_sales f
    JOIN dim_location l ON f.location_key = l.location_key
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE {where_sql}
    GROUP BY l.country, p.category, d.year
    ORDER BY dice_revenue DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def olap_pivot(year: Optional[int] = None, engine=None) -> pd.DataFrame:
    """Execute Pivot crosstab of Category revenue across Month columns."""
    if engine is None:
        engine = get_engine(DB_URL)

    year_filter = f"WHERE d.year = {year}" if year else ""
    query = f"""
    SELECT 
        p.category,
        ROUND(SUM(CASE WHEN d.month = 1 THEN f.total_amount ELSE 0 END), 2) AS Jan,
        ROUND(SUM(CASE WHEN d.month = 2 THEN f.total_amount ELSE 0 END), 2) AS Feb,
        ROUND(SUM(CASE WHEN d.month = 3 THEN f.total_amount ELSE 0 END), 2) AS Mar,
        ROUND(SUM(CASE WHEN d.month = 4 THEN f.total_amount ELSE 0 END), 2) AS Apr,
        ROUND(SUM(CASE WHEN d.month = 5 THEN f.total_amount ELSE 0 END), 2) AS May,
        ROUND(SUM(CASE WHEN d.month = 6 THEN f.total_amount ELSE 0 END), 2) AS Jun,
        ROUND(SUM(CASE WHEN d.month = 7 THEN f.total_amount ELSE 0 END), 2) AS Jul,
        ROUND(SUM(CASE WHEN d.month = 8 THEN f.total_amount ELSE 0 END), 2) AS Aug,
        ROUND(SUM(CASE WHEN d.month = 9 THEN f.total_amount ELSE 0 END), 2) AS Sep,
        ROUND(SUM(CASE WHEN d.month = 10 THEN f.total_amount ELSE 0 END), 2) AS Oct,
        ROUND(SUM(CASE WHEN d.month = 11 THEN f.total_amount ELSE 0 END), 2) AS Nov,
        ROUND(SUM(CASE WHEN d.month = 12 THEN f.total_amount ELSE 0 END), 2) AS "Dec",
        ROUND(SUM(f.total_amount), 2) AS Total_Revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d ON f.date_key = d.date_key
    {year_filter}
    GROUP BY p.category
    ORDER BY Total_Revenue DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def get_top_products(n: int = 10, engine=None) -> pd.DataFrame:
    """Top N best-selling products by revenue."""
    if engine is None:
        engine = get_engine(DB_URL)

    query = f"""
    SELECT 
        p.stock_code,
        p.description,
        p.category,
        SUM(f.quantity) AS units_sold,
        ROUND(SUM(f.total_amount), 2) AS total_revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.stock_code, p.description, p.category
    ORDER BY total_revenue DESC
    LIMIT {int(n)};
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def get_top_customers(n: int = 10, engine=None) -> pd.DataFrame:
    """Top N most valuable customers by spending."""
    if engine is None:
        engine = get_engine(DB_URL)

    query = f"""
    SELECT 
        c.customer_id,
        c.country,
        COUNT(DISTINCT f.invoice_no) AS total_orders,
        SUM(f.quantity) AS total_units,
        ROUND(SUM(f.total_amount), 2) AS total_spent
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    GROUP BY c.customer_id, c.country
    ORDER BY total_spent DESC
    LIMIT {int(n)};
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def get_revenue_by_country(engine=None) -> pd.DataFrame:
    """Revenue and order distribution by country."""
    if engine is None:
        engine = get_engine(DB_URL)

    query = """
    SELECT 
        l.country,
        l.region,
        COUNT(DISTINCT f.invoice_no) AS total_orders,
        COUNT(DISTINCT f.customer_key) AS unique_customers,
        ROUND(SUM(f.total_amount), 2) AS total_revenue
    FROM fact_sales f
    JOIN dim_location l ON f.location_key = l.location_key
    GROUP BY l.country, l.region
    ORDER BY total_revenue DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

if __name__ == "__main__":
    kpis = get_kpis()
    print("KPIs:", kpis)
    print("\nRollup Monthly:")
    print(olap_rollup("monthly").head())
