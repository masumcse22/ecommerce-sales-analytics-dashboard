"""
config.py – Central configuration for the Olist e-commerce analytics pipeline.
Reads from environment variables; falls back to sensible local-dev defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DATA_RAW       = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

# ── Database ───────────────────────────────────────────────────────────────
# Set DB_DRIVER=postgresql in .env to use Postgres instead of SQLite
DB_DRIVER   = os.getenv("DB_DRIVER",   "sqlite")
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "olist_dw")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
SQLITE_PATH = BASE_DIR / "data" / "olist_dw.db"

def get_db_url() -> str:
    if DB_DRIVER == "sqlite":
        return f"sqlite:///{SQLITE_PATH}"
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ── Olist dataset date range (actual data: Sep 2016 – Aug 2018) ────────────
OLIST_START_DATE = "2016-09-01"
OLIST_END_DATE   = "2018-09-03"

# ── Churn definition ───────────────────────────────────────────────────────
# Olist customers rarely repeat (real marketplace behaviour),
# so we use a longer window: churned = no order in last 180 days
CHURN_DAYS = 180

# ── Forecasting ────────────────────────────────────────────────────────────
FORECAST_HORIZON_MONTHS = 12   # months to forecast ahead
FORECAST_FREQ           = "MS" # month-start

# ── Brazilian state → region mapping ──────────────────────────────────────
BR_REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast", "ES": "Southeast",
    "RS": "South",     "PR": "South",     "SC": "South",
    "BA": "Northeast", "CE": "Northeast", "PE": "Northeast", "MA": "Northeast",
    "PB": "Northeast", "RN": "Northeast", "AL": "Northeast", "SE": "Northeast",
    "PI": "Northeast",
    "GO": "Center-West", "MT": "Center-West", "MS": "Center-West", "DF": "Center-West",
    "AM": "North", "PA": "North", "RO": "North", "AC": "North",
    "AP": "North", "RR": "North", "TO": "North",
}
