"""
etl/generate_data.py
Generate realistic synthetic e-commerce transactional data.
Produces: customers.csv, products.csv, orders.csv, order_items.csv
"""
import random
import numpy as np
import pandas as pd
from faker import Faker
from pathlib import Path
from loguru import logger
from tqdm import tqdm

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS,
    START_DATE, END_DATE, RANDOM_SEED,
    REGIONS, CATEGORIES, DATA_RAW
)
from datetime import date as _date

_START = _date.fromisoformat(START_DATE)
_END   = _date.fromisoformat(END_DATE)

fake = Faker()
Faker.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


# ── Helpers ────────────────────────────────────────────────────────────────

def _weighted_country() -> tuple[str, str]:
    """Return (country, region) with realistic weights."""
    region = random.choices(
        list(REGIONS.keys()),
        weights=[40, 30, 20, 6, 4],
        k=1
    )[0]
    country = random.choice(REGIONS[region])
    return country, region


def _seasonal_weight(date: pd.Timestamp) -> float:
    """More orders in Q4 (holiday season) and around mid-year sales."""
    month = date.month
    if month in (11, 12): return 2.2
    if month in (6, 7):   return 1.4
    if month in (1, 2):   return 0.7
    return 1.0


# ── Generators ─────────────────────────────────────────────────────────────

def generate_customers(n: int = NUM_CUSTOMERS) -> pd.DataFrame:
    logger.info(f"Generating {n:,} customers …")
    rows = []
    for i in tqdm(range(n), desc="customers"):
        country, region = _weighted_country()
        segment = random.choices(
            ["Bronze", "Silver", "Gold", "Platinum"],
            weights=[50, 30, 15, 5]
        )[0]
        rows.append({
            "customer_id":    f"C{i+1:05d}",
            "first_name":     fake.first_name(),
            "last_name":      fake.last_name(),
            "email":          fake.unique.email(),
            "phone":          fake.phone_number()[:20],
            "country":        country,
            "region":         region,
            "city":           fake.city(),
            "segment":        segment,
            "signup_date":    fake.date_between(start_date=_START, end_date=_END),
            "gender":         random.choice(["M", "F", "Other"]),
            "age":            random.randint(18, 70),
        })
    df = pd.DataFrame(rows)
    logger.success(f"Customers: {len(df):,} rows")
    return df


def generate_products(n: int = NUM_PRODUCTS) -> pd.DataFrame:
    logger.info(f"Generating {n:,} products …")
    rows = []
    for i in range(n):
        cat   = random.choice(list(CATEGORIES.keys()))
        cfg   = CATEGORIES[cat]
        price = max(1, np.random.normal(cfg["avg_price"], cfg["std"]))
        rows.append({
            "product_id":   f"P{i+1:04d}",
            "product_name": f"{fake.word().capitalize()} {cat} {fake.word().capitalize()}",
            "category":     cat,
            "sub_category": fake.bs().split()[0].capitalize(),
            "brand":        fake.company().split()[0],
            "unit_price":   round(price, 2),
            "unit_cost":    round(price * (1 - cfg["margin"]), 2),
            "stock_qty":    random.randint(0, 500),
            "is_active":    random.choices([True, False], weights=[92, 8])[0],
            "launch_date":  fake.date_between(start_date=_START, end_date=_END),
        })
    df = pd.DataFrame(rows)
    logger.success(f"Products: {len(df):,} rows")
    return df


def generate_orders(
    customers: pd.DataFrame,
    products:  pd.DataFrame,
    n: int = NUM_ORDERS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info(f"Generating {n:,} orders …")

    date_range = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    # Build date pool with seasonal weights
    weights = [_seasonal_weight(d) for d in date_range]
    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    active_products = products[products["is_active"]].copy()

    orders, items = [], []
    item_id = 1
    for i in tqdm(range(n), desc="orders"):
        cust = customers.sample(1).iloc[0]
        order_date = pd.Timestamp(
            np.random.choice(date_range, p=weights)
        )
        num_items = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 12, 8, 5])[0]
        prods = active_products.sample(min(num_items, len(active_products)))

        subtotal = 0.0
        for _, prod in prods.iterrows():
            qty      = random.randint(1, 4)
            discount = random.choices([0, 0.05, 0.10, 0.15, 0.20],
                                      weights=[60, 15, 12, 8, 5])[0]
            line_total = round(prod["unit_price"] * qty * (1 - discount), 2)
            subtotal  += line_total
            items.append({
                "item_id":       f"I{item_id:07d}",
                "order_id":      f"O{i+1:06d}",
                "product_id":    prod["product_id"],
                "quantity":      qty,
                "unit_price":    prod["unit_price"],
                "discount_pct":  discount,
                "line_total":    line_total,
            })
            item_id += 1

        shipping = round(random.uniform(0, 15), 2) if subtotal < 50 else 0.0
        tax_rate  = 0.08
        tax       = round(subtotal * tax_rate, 2)
        total     = round(subtotal + shipping + tax, 2)

        status = random.choices(
            ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"],
            weights=[65, 15, 10, 6, 4]
        )[0]

        orders.append({
            "order_id":       f"O{i+1:06d}",
            "customer_id":    cust["customer_id"],
            "order_date":     order_date.date(),
            "ship_date":      (order_date + pd.Timedelta(days=random.randint(1, 7))).date(),
            "status":         status,
            "channel":        random.choices(
                                  ["Web", "Mobile", "Marketplace", "In-store"],
                                  weights=[45, 30, 15, 10])[0],
            "payment_method": random.choices(
                                  ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Crypto"],
                                  weights=[45, 25, 20, 8, 2])[0],
            "country":        cust["country"],
            "region":         cust["region"],
            "subtotal":       round(subtotal, 2),
            "shipping_cost":  shipping,
            "tax":            tax,
            "total_amount":   total,
            "currency":       "USD",
        })

    orders_df = pd.DataFrame(orders)
    items_df  = pd.DataFrame(items)
    logger.success(f"Orders: {len(orders_df):,} | Items: {len(items_df):,}")
    return orders_df, items_df


# ── Entry point ────────────────────────────────────────────────────────────

def generate_all(save: bool = True) -> dict[str, pd.DataFrame]:
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    customers      = generate_customers()
    products       = generate_products()
    orders, items  = generate_orders(customers, products)

    datasets = {
        "customers":   customers,
        "products":    products,
        "orders":      orders,
        "order_items": items,
    }

    if save:
        for name, df in datasets.items():
            path = DATA_RAW / f"{name}.csv"
            df.to_csv(path, index=False)
            logger.info(f"Saved → {path}  ({len(df):,} rows)")

    return datasets


if __name__ == "__main__":
    generate_all()
