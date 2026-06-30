"""
etl/extract.py  –  Load all 9 Olist CSV files from data/raw/
"""
import pandas as pd
from pathlib import Path
from loguru import logger
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_RAW

# Exact Kaggle filenames → friendly table name
OLIST_FILES = {
    "olist_orders_dataset.csv":              "orders",
    "olist_customers_dataset.csv":           "customers",
    "olist_order_items_dataset.csv":         "order_items",
    "olist_order_payments_dataset.csv":      "payments",
    "olist_order_reviews_dataset.csv":       "reviews",
    "olist_products_dataset.csv":            "products",
    "olist_sellers_dataset.csv":             "sellers",
    "olist_geolocation_dataset.csv":         "geolocation",
    "product_category_name_translation.csv": "category_translation",
}

def load_olist_csvs(data_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load all Olist CSVs. Raises FileNotFoundError with helpful message if missing."""
    base = data_dir or DATA_RAW
    result = {}
    missing = []

    for filename, table in OLIST_FILES.items():
        path = base / filename
        if not path.exists():
            missing.append(filename)
            continue
        df = pd.read_csv(path, low_memory=False)
        logger.info(f"  ✓ {filename:<50} {len(df):>7,} rows")
        result[table] = df

    if missing:
        raise FileNotFoundError(
            f"\n\nMissing {len(missing)} Olist file(s) in {base}/:\n"
            + "\n".join(f"  • {f}" for f in missing)
            + "\n\nDownload from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
            + "\nThen place all 9 CSV files in:  data/raw/"
        )

    logger.success(f"Loaded {len(result)} Olist tables from {base}")
    return result
