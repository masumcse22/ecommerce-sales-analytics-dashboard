"""
etl/load.py
Load all processed Olist DataFrames into the SQL warehouse (SQLite or PostgreSQL).
Also builds the dim_date table automatically from the orders date range.
"""
import pandas as pd
from sqlalchemy import create_engine
from loguru import logger
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_db_url


def build_dim_date(start: str = "2016-01-01", end: str = "2019-12-31") -> pd.DataFrame:
    """Date dimension covering the full Olist period (2016-2018) with a buffer."""
    dates = pd.date_range(start=start, end=end, freq="D")
    df = pd.DataFrame({"date_key": dates.date})
    df["year"]       = dates.year
    df["quarter"]    = dates.quarter
    df["month"]      = dates.month
    df["month_name"] = dates.strftime("%B")
    df["week"]       = dates.isocalendar().week.values
    df["day"]        = dates.day
    df["day_name"]   = dates.strftime("%A")
    df["is_weekend"] = dates.dayofweek >= 5
    df["yyyymm"]     = dates.strftime("%Y%m").astype(int)
    return df


def load_to_warehouse(processed: dict[str, pd.DataFrame]) -> None:
    url    = get_db_url()
    engine = create_engine(url)
    logger.info(f"Warehouse: {url[:45]}…")

    dim_date = build_dim_date()

    # Map processed dict keys → warehouse table names
    table_map = {
        "dim_date":             dim_date,
        "dim_customer":         processed["dim_customer"],
        "dim_product":          processed["dim_product"],
        "dim_seller":           processed["dim_seller"],
        "fact_orders":          processed["fact_orders"],
        "fact_order_items":     processed["fact_order_items"],
        "fact_reviews":         processed["fact_reviews"],
        "agg_daily_revenue":    processed["daily_revenue"],
        "agg_customer_rfm":     processed["customer_features"],
        "agg_product_perf":     processed["product_performance"],
        "agg_state_revenue":    processed["state_revenue"],
    }

    with engine.connect() as conn:
        for tbl, df in table_map.items():
            logger.info(f"  Loading {tbl:<25} ({len(df):>7,} rows) …")
            # Stringify all columns for SQLite compatibility
            df_out = df.copy()
            for col in df_out.columns:
                if df_out[col].dtype == "object":
                    df_out[col] = df_out[col].astype(str).replace("nan", "")
                elif str(df_out[col].dtype).startswith("datetime"):
                    df_out[col] = df_out[col].astype(str)
            df_out.to_sql(tbl, con=conn, if_exists="replace", index=False, chunksize=5_000)
            conn.commit()
            logger.success(f"  ✓ {tbl}")

    logger.success("Warehouse load complete!")


if __name__ == "__main__":
    from etl.extract import load_olist_csvs
    from etl.transform import run_transforms
    processed = run_transforms(load_olist_csvs())
    load_to_warehouse(processed)
