"""
etl/pipeline.py
Orchestrates the Olist ETL pipeline: Extract → Transform → Load.

Usage:
    from etl.pipeline import run_pipeline
    processed = run_pipeline()
"""
import time
from loguru import logger
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_RAW, DATA_PROCESSED


def run_pipeline() -> dict:
    start = time.time()
    logger.info("=" * 60)
    logger.info("  OLIST E-COMMERCE ETL PIPELINE")
    logger.info("=" * 60)

    # ── Step 1: Extract ───────────────────────────────────────────────────
    logger.info("Step 1/3 → Extracting Olist CSVs from data/raw/ …")
    from etl.extract import load_olist_csvs
    raw = load_olist_csvs()

    # ── Step 2: Transform ─────────────────────────────────────────────────
    logger.info("Step 2/3 → Transforming & feature engineering …")
    from etl.transform import run_transforms
    processed = run_transforms(raw)

    # ── Step 3: Load ──────────────────────────────────────────────────────
    logger.info("Step 3/3 → Loading to SQL warehouse …")
    from etl.load import load_to_warehouse
    load_to_warehouse(processed)

    elapsed = time.time() - start
    logger.success(f"Pipeline complete in {elapsed:.1f}s")
    logger.info(f"Power BI-ready CSVs → {DATA_PROCESSED}/")
    return processed


if __name__ == "__main__":
    run_pipeline()
