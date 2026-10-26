"""Star Schema Creation and ER Diagram Generation.

Executes sql/schema.sql on the configured database (SQLite or PostgreSQL)
and draws an architectural ER / Star Schema diagram saved to docs/star_schema_architecture.png.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_URL, SQL_DIR, DOCS_DIR

def get_engine(db_url: str = DB_URL):
    """Return SQLAlchemy engine with appropriate configuration."""
    if db_url.startswith("sqlite"):
        return create_engine(db_url, echo=False)
    return create_engine(db_url, pool_pre_ping=True)

def create_star_schema(drop_existing: bool = False, engine=None):
    """Execute DDL statements to set up dimension and fact tables."""
    if engine is None:
        engine = get_engine()

    schema_file = SQL_DIR / "schema.sql"
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema SQL not found at {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        ddl_script = f.read()

    # Split into individual SQL commands by semicolon
    commands = [cmd.strip() for cmd in ddl_script.split(";") if cmd.strip()]

    with engine.begin() as conn:
        if drop_existing:
            # Drop in reverse dependency order
            tables = ["fact_sales", "dim_customer", "dim_product", "dim_location", "dim_date"]
            for tbl in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {tbl};"))
            print("Dropped existing warehouse tables.")

        for cmd in commands:
            conn.execute(text(cmd))

    print(f"Star schema successfully created/verified using database: {engine.url}")
    return True

def generate_star_schema_diagram(output_path: Path = None):
    """Generate an ER/star-schema diagram image using Matplotlib and save to docs/."""
    if output_path is None:
        output_path = DOCS_DIR / "star_schema_architecture.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 9), dpi=300)
    fig.patch.set_facecolor("#0F172A") # Dark slate background
    ax.set_facecolor("#0F172A")
    ax.axis("off")

    # Helper function to draw a table box
    def draw_table(x, y, w, h, title, columns, header_color, border_color):
        # Header rect
        hh = 0.55
        hdr = patches.FancyBboxPatch((x, y + h - hh), w, hh, boxstyle="round,pad=0.03", 
                                     facecolor=header_color, edgecolor=border_color, linewidth=1.5)
        ax.add_patch(hdr)
        ax.text(x + w / 2, y + h - hh / 2, title, color="white", weight="bold", 
                fontsize=11, ha="center", va="center")

        # Body rect
        body = patches.FancyBboxPatch((x, y), w, h - hh, boxstyle="round,pad=0.03", 
                                      facecolor="#1E293B", edgecolor=border_color, linewidth=1.2)
        ax.add_patch(body)

        # Columns
        col_y = y + h - hh - 0.35
        for col, col_type in columns:
            is_pk = "(PK)" in col_type
            is_fk = "(FK)" in col_type
            col_color = "#38BDF8" if is_pk else ("#FBBF24" if is_fk else "#E2E8F0")
            ax.text(x + 0.2, col_y, col, color=col_color, fontsize=8.5, weight="semibold" if (is_pk or is_fk) else "normal")
            ax.text(x + w - 0.2, col_y, col_type, color="#94A3B8", fontsize=7.5, ha="right")
            col_y -= 0.32

    # Dimensions definition
    # 1. dim_date (Top-Left)
    draw_table(0.8, 6.0, 3.2, 3.2, "dim_date", [
        ("date_key", "INTEGER (PK)"),
        ("full_date", "DATE"),
        ("day", "INTEGER"),
        ("month", "INTEGER"),
        ("month_name", "VARCHAR"),
        ("quarter", "INTEGER"),
        ("year", "INTEGER"),
        ("weekday", "VARCHAR"),
        ("is_weekend", "BOOLEAN")
    ], "#2563EB", "#60A5FA")

    # 2. dim_customer (Top-Right)
    draw_table(8.6, 6.2, 3.2, 2.4, "dim_customer", [
        ("customer_key", "INTEGER (PK)"),
        ("customer_id", "VARCHAR (UK)"),
        ("country", "VARCHAR")
    ], "#7C3AED", "#A78BFA")

    # 3. dim_product (Bottom-Left)
    draw_table(0.8, 1.2, 3.2, 2.6, "dim_product", [
        ("product_key", "INTEGER (PK)"),
        ("stock_code", "VARCHAR (UK)"),
        ("description", "VARCHAR"),
        ("category", "VARCHAR")
    ], "#059669", "#34D399")

    # 4. dim_location (Bottom-Right)
    draw_table(8.6, 1.4, 3.2, 2.3, "dim_location", [
        ("location_key", "INTEGER (PK)"),
        ("country", "VARCHAR (UK)"),
        ("region", "VARCHAR")
    ], "#D97706", "#FBBF24")

    # Central fact table: fact_sales
    draw_table(4.7, 3.3, 3.4, 4.0, "fact_sales", [
        ("sales_key", "INTEGER (PK)"),
        ("date_key", "INTEGER (FK)"),
        ("customer_key", "INTEGER (FK)"),
        ("product_key", "INTEGER (FK)"),
        ("location_key", "INTEGER (FK)"),
        ("invoice_no", "VARCHAR"),
        ("quantity", "INTEGER"),
        ("unit_price", "NUMERIC"),
        ("total_amount", "NUMERIC")
    ], "#DC2626", "#F87171")

    # Draw connection lines (1-to-many relationship arrows)
    arrow_props = dict(arrowstyle="-|>", color="#94A3B8", lw=1.8, mutation_scale=12)
    # dim_date to fact_sales
    ax.annotate("", xy=(4.7, 6.2), xytext=(4.0, 7.2), arrowprops=arrow_props)
    ax.text(4.2, 6.8, "1 : N", color="#38BDF8", fontsize=8, weight="bold")

    # dim_customer to fact_sales
    ax.annotate("", xy=(8.1, 6.3), xytext=(8.6, 7.0), arrowprops=arrow_props)
    ax.text(8.25, 6.8, "1 : N", color="#A78BFA", fontsize=8, weight="bold")

    # dim_product to fact_sales
    ax.annotate("", xy=(4.7, 4.4), xytext=(4.0, 2.8), arrowprops=arrow_props)
    ax.text(4.2, 3.5, "1 : N", color="#34D399", fontsize=8, weight="bold")

    # dim_location to fact_sales
    ax.annotate("", xy=(8.1, 4.5), xytext=(8.6, 2.8), arrowprops=arrow_props)
    ax.text(8.25, 3.5, "1 : N", color="#FBBF24", fontsize=8, weight="bold")

    # Title & Subtitle
    ax.text(6.3, 9.6, "Retail Data Warehouse - Star Schema Architecture", 
            color="#F8FAFC", fontsize=15, weight="bold", ha="center")
    ax.text(6.3, 9.25, "Central Fact Table with Conformed Dimension Tables and Surrogate Keys", 
            color="#94A3B8", fontsize=9.5, ha="center")

    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 10.0)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Star schema architecture diagram saved to {output_path}")
    return output_path

if __name__ == "__main__":
    create_star_schema(drop_existing=False)
    generate_star_schema_diagram()
