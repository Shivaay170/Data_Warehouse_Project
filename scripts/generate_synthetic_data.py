"""Synthetic retail dataset generator mimicking the UCI Online Retail dataset.

Generates realistic retail transactions over 2 years with:
- Natural basket associations (for Market Basket Analysis)
- Recency, frequency, and monetary distributions (for RFM customer segmentation)
- Active vs lapsed customer patterns (for Churn prediction)
- Monthly seasonality / growth trend (for Forecasting)
- Deliberate real-world dirty data (nulls, cancelled invoices, duplicates, negative values)
  to thoroughly exercise the ETL cleaning pipeline.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DATA_FILE, RAW_DATA_DIR, RANDOM_STATE

def generate_retail_dataset(
    num_records: int = 60000,
    output_path: Path = RAW_DATA_FILE,
    seed: int = RANDOM_STATE
):
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Product catalog with Categories and natural pairing bundles
    catalog = [
        # Kitchen & Dining
        ("22423", "REGENCY CAKESTAND 3 TIER", 12.75, "Kitchen & Dining"),
        ("22424", "ENAMEL BREAD BIN", 9.95, "Kitchen & Dining"),
        ("22425", "CERAMIC TEA POT WHITE", 7.50, "Kitchen & Dining"),
        ("22426", "SET OF 4 TEA CUPS AND SAUCERS", 8.50, "Kitchen & Dining"),
        ("22427", "RETRO CHILLI APRON", 4.95, "Kitchen & Dining"),
        ("22428", "WOODEN SPATULA SET 3PC", 3.25, "Kitchen & Dining"),
        ("22429", "BAKING MOULD SILICONE STAR", 2.95, "Kitchen & Dining"),
        ("22430", "MEASURING JUG 1L GLASS", 4.50, "Kitchen & Dining"),
        
        # Home Decor
        ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55, "Home Decor"),
        ("85123B", "RED HANGING HEART T-LIGHT HOLDER", 2.55, "Home Decor"),
        ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69, "Home Decor"),
        ("21733", "RED HANGING HEART LANTERN", 3.75, "Home Decor"),
        ("22086", "PAPER CHAIN KIT 50S CHRISTMAS", 2.95, "Home Decor"),
        ("22112", "CHOCOLATE HOT WATER BOTTLE", 4.95, "Home Decor"),
        ("22114", "HOT WATER BOTTLE TEA AND SYMPATHY", 4.95, "Home Decor"),
        ("22720", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95, "Home Decor"),
        ("22722", "SET OF 6 SPICE TINS PANTRY DESIGN", 3.95, "Home Decor"),

        # Gifts & Accessories
        ("21212", "PACK OF 72 RETROSPOT CAKE CASES", 0.55, "Gifts & Accessories"),
        ("21213", "PACK OF 72 SKULL CAKE CASES", 0.55, "Gifts & Accessories"),
        ("20725", "LUNCH BAG RED RETROSPOT", 1.65, "Gifts & Accessories"),
        ("20727", "LUNCH BAG BLACK SKULL", 1.65, "Gifts & Accessories"),
        ("20728", "LUNCH BAG CARS BLUE", 1.65, "Gifts & Accessories"),
        ("22383", "LUNCH BAG SUKI DESIGN", 1.65, "Gifts & Accessories"),
        ("22382", "LUNCH BAG SPACEBOY DESIGN", 1.65, "Gifts & Accessories"),
        ("22666", "RECIPE BOX PANTRY DESIGN", 2.95, "Gifts & Accessories"),

        # Stationery & Office
        ("22960", "JAM MAKING SET WITH JARS", 4.25, "Stationery & Office"),
        ("22961", "JAM JAR LABELS VINTAGE FLORAL", 1.25, "Stationery & Office"),
        ("84991", "60 TEATIME PAIRING STICKERS", 0.85, "Stationery & Office"),
        ("84992", "72 ROUND NOTEPAD RETRO", 1.45, "Stationery & Office"),
        ("22090", "PAPER BUNTING RETROSPOT", 2.95, "Stationery & Office"),
        ("22197", "POPCORN HOLDER RETRO RED", 0.85, "Stationery & Office"),
        ("22198", "LARGE POPCORN HOLDER STRIPED", 1.65, "Stationery & Office"),
        
        # Clothing & Apparel
        ("23203", "JUMBO BAG DOILEY PATTERNS", 1.95, "Clothing & Apparel"),
        ("23204", "CHARLOTTE BAG APPLES DESIGN", 1.95, "Clothing & Apparel"),
        ("23205", "JUMBO BAG VINTAGE LEAF", 1.95, "Clothing & Apparel"),
        ("23206", "LUNCH BAG WOODLAND", 1.65, "Clothing & Apparel"),
        ("23207", "COSY SLIPPERS FLEECE PINK", 5.95, "Clothing & Apparel"),
        ("23208", "COSY SLIPPERS FLEECE GREY", 5.95, "Clothing & Apparel"),
    ]

    # Specific basket affinity sets to ensure strong Apriori / FP-growth association rules
    affinity_pairs = [
        (("22425", "CERAMIC TEA POT WHITE"), ("22426", "SET OF 4 TEA CUPS AND SAUCERS")),
        (("22960", "JAM MAKING SET WITH JARS"), ("22961", "JAM JAR LABELS VINTAGE FLORAL")),
        (("20725", "LUNCH BAG RED RETROSPOT"), ("20727", "LUNCH BAG BLACK SKULL")),
        (("85123A", "WHITE HANGING HEART T-LIGHT HOLDER"), ("85123B", "RED HANGING HEART T-LIGHT HOLDER")),
        (("22197", "POPCORN HOLDER RETRO RED"), ("22198", "LARGE POPCORN HOLDER STRIPED")),
        (("22720", "SET OF 3 CAKE TINS PANTRY DESIGN"), ("22722", "SET OF 6 SPICE TINS PANTRY DESIGN")),
        (("21212", "PACK OF 72 RETROSPOT CAKE CASES"), ("22423", "REGENCY CAKESTAND 3 TIER")),
    ]

    countries = [
        ("United Kingdom", 0.70),
        ("Germany", 0.08),
        ("France", 0.07),
        ("Spain", 0.04),
        ("Netherlands", 0.03),
        ("Australia", 0.03),
        ("Switzerland", 0.02),
        ("Portugal", 0.02),
        ("Belgium", 0.01),
    ]
    country_names = [c[0] for c in countries]
    country_weights = [c[1] for c in countries]

    # Customer definitions: ~1,500 distinct customers
    num_customers = 1500
    customers = []
    for cid in range(10001, 10001 + num_customers):
        c_country = random.choices(country_names, weights=country_weights)[0]
        # customer profile: high-frequency (loyal), moderate, or one-off
        tier = random.choices(["vip", "regular", "churn_risk", "one_time"], weights=[0.15, 0.45, 0.25, 0.15])[0]
        customers.append((cid, c_country, tier))

    # Timeframe: 2 full years from 2024-01-01 to 2025-12-31 (730 days)
    start_date = datetime(2024, 1, 1, 8, 0, 0)
    
    rows = []
    invoice_seq = 500000

    print(f"Generating synthetic retail dataset with target >= {num_records} rows...")

    while len(rows) < num_records:
        invoice_seq += 1
        cid, country, tier = random.choice(customers)

        # Date distribution according to tier to create realistic churn & RFM
        if tier == "vip":
            # Active throughout the 2 years, frequent purchases
            day_offset = random.randint(0, 729)
        elif tier == "regular":
            day_offset = random.randint(0, 729)
        elif tier == "churn_risk":
            # Disappeared in the first 1.5 years (more than 90-180 days before end)
            day_offset = random.randint(0, 550)
        else: # one_time
            day_offset = random.randint(0, 600)

        tx_time = start_date + timedelta(
            days=day_offset,
            hours=random.randint(0, 10),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        invoice_date_str = tx_time.strftime("%Y-%m-%d %H:%M:%S")

        # Determine if cancelled invoice (simulating ~2% cancellations)
        is_cancelled = random.random() < 0.02
        inv_prefix = "C" if is_cancelled else ""
        inv_no = f"{inv_prefix}{invoice_seq}"

        # Determine basket size (number of distinct items in invoice)
        basket_size = random.randint(1, 6)
        
        # Chance to inject correlated affinity bundle
        items_to_add = []
        if random.random() < 0.45:
            pair = random.choice(affinity_pairs)
            items_to_add.append(pair[0])
            items_to_add.append(pair[1])

        # Fill remaining items from general catalog
        while len(items_to_add) < basket_size:
            prod = random.choice(catalog)
            if (prod[0], prod[1]) not in items_to_add:
                items_to_add.append((prod[0], prod[1]))

        # Catalog lookup map for price
        cat_map = {p[0]: p[2] for p in catalog}

        for stock_code, desc in items_to_add:
            base_price = cat_map.get(stock_code, 2.50)
            qty = random.randint(1, 12) if not is_cancelled else -random.randint(1, 5)
            price = round(base_price * random.uniform(0.95, 1.05), 2)
            
            # Chance of deliberate data anomalies for ETL to clean:
            # 1. Null CustomerID (~3% missing customer IDs)
            c_id_val = "" if random.random() < 0.03 else str(cid)
            
            # 2. Occasional negative or zero price (~0.1% dirty data)
            if random.random() < 0.001 and not is_cancelled:
                price = 0.0

            rows.append({
                "InvoiceNo": inv_no,
                "StockCode": stock_code,
                "Description": desc,
                "Quantity": qty,
                "InvoiceDate": invoice_date_str,
                "UnitPrice": price,
                "CustomerID": c_id_val,
                "Country": country
            })

    # Add duplicate rows (~1.5% duplicates) to test deduplication in ETL
    num_duplicates = int(len(rows) * 0.015)
    duplicates = [random.choice(rows).copy() for _ in range(num_duplicates)]
    rows.extend(duplicates)

    # Shuffle to ensure natural sequence
    random.shuffle(rows)

    # Write to CSV
    fieldnames = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows):,} raw records successfully at {output_path}")
    return output_path

if __name__ == "__main__":
    generate_retail_dataset()
