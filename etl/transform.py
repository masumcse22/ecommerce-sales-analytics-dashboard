"""
etl/transform.py  –  Clean & transform the 9 Olist tables into
warehouse-ready DataFrames (fact tables, dimensions, aggregates).

Olist schema recap
──────────────────
orders          order_id → customer_id, timestamps, status
customers       customer_id, customer_unique_id, zip, city, state
order_items     order_id, product_id, seller_id, price, freight_value
payments        order_id, payment_type, installments, payment_value
reviews         order_id, review_score, review_comment_*
products        product_id, category_name (PT), dimensions/weight
sellers         seller_id, zip, city, state
geolocation     zip_prefix, lat, lng, city, state
category_translation  category_name_portuguese → category_name_english
"""
import pandas as pd
import numpy as np
from loguru import logger
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED, CHURN_DAYS


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ts(df: pd.DataFrame, *cols) -> pd.DataFrame:
    """Convert columns to datetime, coercing errors."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dimension: Customers
# ─────────────────────────────────────────────────────────────────────────────

def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    """
    Olist has TWO customer id types:
      customer_id         – unique per ORDER (changes each order)
      customer_unique_id  – true repeat-customer identifier
    We keep both and use customer_unique_id for RFM/churn.
    """
    logger.info("Building dim_customer …")
    df = customers.copy()
    df.columns = df.columns.str.strip()
    df["customer_city"]  = df["customer_city"].str.title().str.strip()
    df["customer_state"] = df["customer_state"].str.upper().str.strip()
    df.drop_duplicates(subset=["customer_id"], inplace=True)
    logger.success(f"dim_customer: {len(df):,} rows")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dimension: Products  (with English category names)
# ─────────────────────────────────────────────────────────────────────────────

def build_dim_product(
    products: pd.DataFrame,
    category_translation: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building dim_product …")
    df = products.copy()
    df.columns = df.columns.str.strip()

    # Translate category names to English
    trans = category_translation.copy()
    trans.columns = trans.columns.str.strip()
    df = df.merge(trans, on="product_category_name", how="left")

    # Fill missing English name with Portuguese name
    df["category_en"] = (
        df["product_category_name_english"]
        .fillna(df["product_category_name"])
        .str.replace("_", " ", regex=False)
        .str.title()
        .str.strip()
    )

    # Clean numeric dimensions
    for col in ["product_weight_g", "product_length_cm",
                "product_height_cm", "product_width_cm",
                "product_photos_qty", "product_name_length",
                "product_description_length"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop the Portuguese translation column (redundant)
    df.drop(columns=["product_category_name_english"], errors="ignore", inplace=True)
    df.rename(columns={"product_category_name": "category_pt"}, inplace=True)

    logger.success(f"dim_product: {len(df):,} rows  |  {df['category_en'].nunique()} categories")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dimension: Sellers
# ─────────────────────────────────────────────────────────────────────────────

def build_dim_seller(sellers: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building dim_seller …")
    df = sellers.copy()
    df.columns = df.columns.str.strip()
    df["seller_city"]  = df["seller_city"].str.title().str.strip()
    df["seller_state"] = df["seller_state"].str.upper().str.strip()
    df.drop_duplicates(subset=["seller_id"], inplace=True)
    logger.success(f"dim_seller: {len(df):,} rows")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fact: Orders  (core metrics from orders + payments joined)
# ─────────────────────────────────────────────────────────────────────────────

def build_fact_orders(
    orders: pd.DataFrame,
    payments: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building fact_orders …")

    o = orders.copy()
    o.columns = o.columns.str.strip()
    o = _ts(o,
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    )

    # Aggregate payments per order
    pay = payments.copy()
    pay.columns = pay.columns.str.strip()
    pay_agg = (
        pay.groupby("order_id")
        .agg(
            total_payment   = ("payment_value",        "sum"),
            num_installments= ("payment_installments", "max"),
            payment_types   = ("payment_type",         lambda x: "|".join(sorted(x.unique()))),
        )
        .reset_index()
    )

    # Pull customer state for region analysis
    cust_state = customers[["customer_id","customer_state","customer_city"]].drop_duplicates("customer_id")

    df = (
        o.merge(pay_agg,    on="order_id",    how="left")
         .merge(cust_state, on="customer_id", how="left")
    )

    # ── Derived columns ─────────────────────────────────────────────────────
    df["order_date"]       = df["order_purchase_timestamp"].dt.date
    df["order_year"]       = df["order_purchase_timestamp"].dt.year
    df["order_month"]      = df["order_purchase_timestamp"].dt.month
    df["order_quarter"]    = df["order_purchase_timestamp"].dt.quarter
    df["order_dow"]        = df["order_purchase_timestamp"].dt.day_name()
    df["order_week"]       = df["order_purchase_timestamp"].dt.isocalendar().week.astype("Int64")

    df["days_to_carrier"]  = (
        df["order_delivered_carrier_date"] - df["order_purchase_timestamp"]
    ).dt.days.clip(lower=0)

    df["days_to_customer"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days.clip(lower=0)

    df["delivery_delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.days   # positive = late, negative = early

    # Status flags
    df["is_delivered"]  = df["order_status"] == "delivered"
    df["is_cancelled"]  = df["order_status"] == "canceled"
    df["is_completed"]  = df["is_delivered"]

    # Remove rows with no payment info (cancelled before payment)
    df = df[df["total_payment"].notna()]

    logger.success(
        f"fact_orders: {len(df):,} rows  |  "
        f"delivered={df['is_delivered'].sum():,}  cancelled={df['is_cancelled'].sum():,}"
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fact: Order Items  (with price / freight per line)
# ─────────────────────────────────────────────────────────────────────────────

def build_fact_order_items(
    order_items: pd.DataFrame,
    orders:      pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building fact_order_items …")

    oi = order_items.copy()
    oi.columns = oi.columns.str.strip()
    oi = _ts(oi, "shipping_limit_date")

    # Numeric guard
    for col in ["price", "freight_value"]:
        oi[col] = pd.to_numeric(oi[col], errors="coerce").fillna(0)

    oi["line_total"] = oi["price"] + oi["freight_value"]

    # Only keep items for orders that exist in fact_orders
    valid_orders = set(orders["order_id"])
    oi = oi[oi["order_id"].isin(valid_orders)]

    logger.success(f"fact_order_items: {len(oi):,} rows")
    return oi


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fact: Reviews
# ─────────────────────────────────────────────────────────────────────────────

def build_fact_reviews(reviews: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building fact_reviews …")

    r = reviews.copy()
    r.columns = r.columns.str.strip()
    r = _ts(r, "review_creation_date", "review_answer_timestamp")

    # Keep latest review per order
    r.sort_values("review_creation_date", ascending=False, inplace=True)
    r.drop_duplicates(subset=["order_id"], keep="first", inplace=True)

    r["review_score"]        = pd.to_numeric(r["review_score"], errors="coerce")
    r["has_comment"]         = r["review_comment_message"].notna()
    r["is_positive_review"]  = r["review_score"] >= 4
    r["is_negative_review"]  = r["review_score"] <= 2

    valid_orders = set(orders["order_id"])
    r = r[r["order_id"].isin(valid_orders)]

    cols = ["review_id","order_id","review_score","review_creation_date",
            "has_comment","is_positive_review","is_negative_review"]
    cols = [c for c in cols if c in r.columns]

    logger.success(
        f"fact_reviews: {len(r):,} rows  |  "
        f"avg score={r['review_score'].mean():.2f}"
    )
    return r[cols]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Aggregate: Daily Revenue
# ─────────────────────────────────────────────────────────────────────────────

def build_daily_revenue(fact_orders: pd.DataFrame) -> pd.DataFrame:
    logger.info("Building daily_revenue …")
    completed = fact_orders[fact_orders["is_completed"]].copy()
    completed["order_date"] = pd.to_datetime(completed["order_purchase_timestamp"]).dt.date

    daily = (
        completed.groupby("order_date")
        .agg(
            revenue             = ("total_payment",    "sum"),
            num_orders          = ("order_id",         "count"),
            unique_customers    = ("customer_id",      "nunique"),
        )
        .reset_index()
        .rename(columns={"order_date": "ds"})
        .sort_values("ds")
    )
    daily["ds"]  = pd.to_datetime(daily["ds"])
    daily["aov"] = (daily["revenue"] / daily["num_orders"]).round(2)
    logger.success(f"daily_revenue: {len(daily):,} days  |  total R$ {daily['revenue'].sum():,.0f}")
    return daily


# ─────────────────────────────────────────────────────────────────────────────
# 8. Aggregate: Customer RFM Features
# ─────────────────────────────────────────────────────────────────────────────

def build_customer_features(
    fact_orders: pd.DataFrame,
    customers:   pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building customer RFM features …")

    snapshot = pd.to_datetime(fact_orders["order_purchase_timestamp"]).max()
    completed = fact_orders[fact_orders["is_completed"]].copy()
    completed["order_purchase_timestamp"] = pd.to_datetime(completed["order_purchase_timestamp"])

    # Join unique_id (Olist's real repeat-customer key)
    cust_map = customers[["customer_id","customer_unique_id",
                           "customer_state","customer_city"]].drop_duplicates("customer_id")
    completed = completed.merge(cust_map, on="customer_id", how="left")

    agg_cols = {
        "first_order_date": ("order_purchase_timestamp", "min"),
        "last_order_date":  ("order_purchase_timestamp", "max"),
        "frequency":        ("order_id",                 "nunique"),
        "monetary":         ("total_payment",            "sum"),
    }
    if "customer_state" in completed.columns:
        agg_cols["state"] = ("customer_state", "first")

    rfm = completed.groupby("customer_unique_id").agg(**agg_cols).reset_index()

    rfm["recency_days"] = (snapshot - rfm["last_order_date"]).dt.days
    rfm["tenure_days"]  = (snapshot - rfm["first_order_date"]).dt.days
    rfm["aov"]          = (rfm["monetary"] / rfm["frequency"]).round(2)
    rfm["is_churned"]   = rfm["recency_days"] > CHURN_DAYS

    # RFM scores (quintiles)
    for col, label, asc in [
        ("recency_days", "r_score", False),   # lower recency = better
        ("frequency",    "f_score", True),
        ("monetary",     "m_score", True),
    ]:
        try:
            rfm[label] = pd.qcut(
                rfm[col] if asc else -rfm[col],
                q=5, labels=[1,2,3,4,5], duplicates="drop"
            ).astype(int)
        except Exception:
            rfm[label] = 3   # fallback if too few unique values

    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]
    rfm["rfm_segment"] = rfm["rfm_score"].map(lambda s:
        "Champions"       if s >= 13 else
        "Loyal Customers" if s >= 10 else
        "At Risk"         if s >= 7  else
        "Hibernating"     if s >= 4  else
        "Lost"
    )

    logger.success(
        f"customer_features: {len(rfm):,} unique customers  |  "
        f"churned={rfm['is_churned'].sum():,} ({rfm['is_churned'].mean()*100:.1f}%)"
    )
    return rfm


# ─────────────────────────────────────────────────────────────────────────────
# 9. Aggregate: Product Performance
# ─────────────────────────────────────────────────────────────────────────────

def build_product_performance(
    fact_order_items: pd.DataFrame,
    fact_orders:      pd.DataFrame,
    dim_product:      pd.DataFrame,
    fact_reviews:     pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building product_performance …")

    # Only delivered orders
    delivered_ids = set(fact_orders[fact_orders["is_delivered"]]["order_id"])
    items = fact_order_items[fact_order_items["order_id"].isin(delivered_ids)].copy()

    perf = (
        items.groupby("product_id")
        .agg(
            total_units_sold  = ("order_item_id",  "count"),
            total_revenue     = ("price",          "sum"),
            total_freight     = ("freight_value",  "sum"),
            num_orders        = ("order_id",       "nunique"),
            avg_price         = ("price",          "mean"),
        )
        .reset_index()
    )
    perf["aov_product"]    = (perf["total_revenue"] / perf["num_orders"]).round(2)
    perf["revenue_rank"]   = perf["total_revenue"].rank(ascending=False).astype(int)

    # Join English category names
    prod_slim = dim_product[["product_id","category_en","category_pt",
                              "product_weight_g"]].copy()
    perf = perf.merge(prod_slim, on="product_id", how="left")

    # Add average review score per product
    order_review = fact_reviews[["order_id","review_score"]].copy()
    item_review  = fact_order_items[["order_id","product_id"]].merge(order_review, on="order_id")
    avg_review   = item_review.groupby("product_id")["review_score"].mean().round(2).reset_index()
    avg_review.columns = ["product_id","avg_review_score"]
    perf = perf.merge(avg_review, on="product_id", how="left")

    logger.success(f"product_performance: {len(perf):,} products")
    return perf


# ─────────────────────────────────────────────────────────────────────────────
# 10. Aggregate: State Revenue (for map chart in Power BI)
# ─────────────────────────────────────────────────────────────────────────────

def build_state_revenue(
    fact_orders: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building state_revenue …")
    completed = fact_orders[fact_orders["is_delivered"]].copy()

    state = (
        completed.groupby("customer_state")
        .agg(
            revenue         = ("total_payment", "sum"),
            num_orders      = ("order_id",      "count"),
            unique_customers= ("customer_id",   "nunique"),
            avg_delay_days  = ("delivery_delay_days", "mean"),
        )
        .reset_index()
    )
    state["aov"] = (state["revenue"] / state["num_orders"]).round(2)
    state["revenue_rank"] = state["revenue"].rank(ascending=False).astype(int)

    # Map state codes to full names
    BR_STATES = {
        "AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia",
        "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
        "MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais",
        "PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí",
        "RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul",
        "RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SP":"São Paulo",
        "SE":"Sergipe","TO":"Tocantins"
    }
    state["state_name"] = state["customer_state"].map(BR_STATES).fillna(state["customer_state"])
    logger.success(f"state_revenue: {len(state):,} states")
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

def run_transforms(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    dim_customer  = build_dim_customer(raw["customers"])
    dim_product   = build_dim_product(raw["products"], raw["category_translation"])
    dim_seller    = build_dim_seller(raw["sellers"])
    fact_orders   = build_fact_orders(raw["orders"], raw["payments"], raw["customers"])
    fact_items    = build_fact_order_items(raw["order_items"], fact_orders)
    fact_reviews  = build_fact_reviews(raw["reviews"], fact_orders)
    daily_revenue = build_daily_revenue(fact_orders)
    cust_features = build_customer_features(fact_orders, raw["customers"])
    product_perf  = build_product_performance(fact_items, fact_orders, dim_product, fact_reviews)
    state_revenue = build_state_revenue(fact_orders)

    processed = {
        "dim_customer":        dim_customer,
        "dim_product":         dim_product,
        "dim_seller":          dim_seller,
        "fact_orders":         fact_orders,
        "fact_order_items":    fact_items,
        "fact_reviews":        fact_reviews,
        "daily_revenue":       daily_revenue,
        "customer_features":   cust_features,
        "product_performance": product_perf,
        "state_revenue":       state_revenue,
    }

    for name, df in processed.items():
        path = DATA_PROCESSED / f"{name}.csv"
        df.to_csv(path, index=False)
        logger.info(f"  → {name}.csv  ({len(df):,} rows)")

    logger.success("All processed CSVs written to data/processed/")
    return processed


if __name__ == "__main__":
    from etl.extract import load_olist_csvs
    raw = load_olist_csvs()
    run_transforms(raw)
