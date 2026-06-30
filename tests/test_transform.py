"""
tests/test_transform.py – Unit tests for Olist ETL transforms.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from etl.transform import (
    build_dim_customer,
    build_dim_product,
    build_dim_seller,
    build_fact_orders,
    build_fact_order_items,
    build_fact_reviews,
    build_daily_revenue,
    build_customer_features,
    build_state_revenue,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def raw_customers():
    return pd.DataFrame({
        "customer_id":          ["C1","C2","C3","C1"],     # C1 duplicate
        "customer_unique_id":   ["U1","U2","U3","U1"],
        "customer_zip_code_prefix": ["01310","20040","30112","01310"],
        "customer_city":        ["são paulo","rio de janeiro","belo horizonte","são paulo"],
        "customer_state":       ["sp","rj","mg","sp"],
    })

@pytest.fixture
def raw_products():
    return pd.DataFrame({
        "product_id":          ["P1","P2","P3"],
        "product_category_name":["cama_mesa_banho","esporte_lazer","beleza_saude"],
        "product_name_length": [40,35,50],
        "product_description_length": [800,600,700],
        "product_photos_qty":  [3,2,4],
        "product_weight_g":    [500,200,300],
        "product_length_cm":   [30,20,15],
        "product_height_cm":   [10,5,8],
        "product_width_cm":    [20,15,12],
    })

@pytest.fixture
def raw_category_translation():
    return pd.DataFrame({
        "product_category_name":         ["cama_mesa_banho","esporte_lazer","beleza_saude"],
        "product_category_name_english":  ["Bed Bath Table","Sports Leisure","Health Beauty"],
    })

@pytest.fixture
def raw_sellers():
    return pd.DataFrame({
        "seller_id":             ["S1","S2","S1"],   # S1 duplicate
        "seller_zip_code_prefix":["01310","20040","01310"],
        "seller_city":           ["são paulo","rio de janeiro","são paulo"],
        "seller_state":          ["SP","RJ","SP"],
    })

@pytest.fixture
def raw_orders():
    return pd.DataFrame({
        "order_id":                    ["O1","O2","O3","O4"],
        "customer_id":                 ["C1","C2","C1","C3"],
        "order_status":                ["delivered","delivered","canceled","delivered"],
        "order_purchase_timestamp":    [
            "2017-01-10 10:00:00","2017-02-15 14:00:00",
            "2017-03-01 09:00:00","2017-04-05 12:00:00"
        ],
        "order_approved_at":           [
            "2017-01-10 11:00:00","2017-02-15 15:00:00",None,"2017-04-05 13:00:00"
        ],
        "order_delivered_carrier_date":[
            "2017-01-12 08:00:00","2017-02-17 10:00:00",None,"2017-04-08 09:00:00"
        ],
        "order_delivered_customer_date":[
            "2017-01-18 14:00:00","2017-02-22 16:00:00",None,"2017-04-15 11:00:00"
        ],
        "order_estimated_delivery_date":[
            "2017-01-20 00:00:00","2017-02-20 00:00:00",None,"2017-04-10 00:00:00"
        ],
    })

@pytest.fixture
def raw_payments():
    return pd.DataFrame({
        "order_id":             ["O1","O1","O2","O3","O4"],
        "payment_sequential":   [1,   2,   1,   1,   1],
        "payment_type":         ["credit_card","voucher","boleto","credit_card","credit_card"],
        "payment_installments": [3,   1,   1,   1,   6],
        "payment_value":        [150.0, 10.0, 200.0, 80.0, 350.0],
    })

@pytest.fixture
def raw_reviews():
    return pd.DataFrame({
        "review_id":              ["R1","R2","R3","R1"],   # R1 duplicate
        "order_id":               ["O1","O2","O4","O1"],
        "review_score":           [5,   3,   4,   5],
        "review_creation_date":   ["2017-01-20","2017-02-25","2017-04-18","2017-01-21"],
        "review_answer_timestamp":["2017-01-21","2017-02-26","2017-04-19","2017-01-22"],
        "review_comment_message": ["Great!",None,"Good",None],
    })

@pytest.fixture
def fact_orders_df(raw_orders, raw_payments, raw_customers):
    return build_fact_orders(raw_orders, raw_payments, raw_customers)

@pytest.fixture
def fact_order_items_df(fact_orders_df):
    items = pd.DataFrame({
        "order_id":     ["O1","O1","O2","O4"],
        "order_item_id":[1,   2,   1,   1],
        "product_id":   ["P1","P2","P2","P3"],
        "seller_id":    ["S1","S2","S1","S2"],
        "shipping_limit_date":["2017-01-12","2017-01-12","2017-02-17","2017-04-08"],
        "price":        [140.0, 10.0, 190.0, 340.0],
        "freight_value":[10.0,  0.0,  10.0,  10.0],
    })
    return build_fact_order_items(items, fact_orders_df)


# ── dim_customer ───────────────────────────────────────────────────────────

class TestDimCustomer:
    def test_deduplicates_customer_id(self, raw_customers):
        result = build_dim_customer(raw_customers)
        assert result["customer_id"].duplicated().sum() == 0

    def test_title_cases_city(self, raw_customers):
        result = build_dim_customer(raw_customers)
        assert "São Paulo" in result["customer_city"].values

    def test_uppercases_state(self, raw_customers):
        result = build_dim_customer(raw_customers)
        assert result["customer_state"].str.isupper().all()


# ── dim_product ────────────────────────────────────────────────────────────

class TestDimProduct:
    def test_translates_category(self, raw_products, raw_category_translation):
        result = build_dim_product(raw_products, raw_category_translation)
        assert "Bed Bath Table" in result["category_en"].values

    def test_no_raw_english_col(self, raw_products, raw_category_translation):
        result = build_dim_product(raw_products, raw_category_translation)
        assert "product_category_name_english" not in result.columns

    def test_numeric_dimensions(self, raw_products, raw_category_translation):
        result = build_dim_product(raw_products, raw_category_translation)
        assert pd.api.types.is_numeric_dtype(result["product_weight_g"])


# ── dim_seller ─────────────────────────────────────────────────────────────

class TestDimSeller:
    def test_deduplicates(self, raw_sellers):
        result = build_dim_seller(raw_sellers)
        assert result["seller_id"].duplicated().sum() == 0


# ── fact_orders ────────────────────────────────────────────────────────────

class TestFactOrders:
    def test_payments_aggregated(self, fact_orders_df):
        # O1 has two payments: 150 + 10 = 160
        o1 = fact_orders_df[fact_orders_df["order_id"] == "O1"]
        assert abs(float(o1["total_payment"].iloc[0]) - 160.0) < 0.01

    def test_status_flags(self, fact_orders_df):
        assert "is_delivered" in fact_orders_df.columns
        assert "is_cancelled" in fact_orders_df.columns
        assert "is_completed" in fact_orders_df.columns

    def test_derived_date_cols(self, fact_orders_df):
        for col in ["order_year","order_month","order_quarter","order_dow"]:
            assert col in fact_orders_df.columns

    def test_days_to_carrier_nonneg(self, fact_orders_df):
        delivered = fact_orders_df[fact_orders_df["is_delivered"]]
        assert (delivered["days_to_carrier"].dropna() >= 0).all()

    def test_cancelled_not_completed(self, fact_orders_df):
        cancelled = fact_orders_df[fact_orders_df["is_cancelled"]]
        assert (cancelled["is_completed"] == False).all()


# ── fact_order_items ───────────────────────────────────────────────────────

class TestFactOrderItems:
    def test_line_total_computed(self, fact_order_items_df):
        assert "line_total" in fact_order_items_df.columns
        row = fact_order_items_df[fact_order_items_df["order_id"] == "O1"].iloc[0]
        expected = row["price"] + row["freight_value"]
        assert abs(row["line_total"] - expected) < 0.01

    def test_only_valid_orders(self, fact_order_items_df, fact_orders_df):
        valid = set(fact_orders_df["order_id"])
        assert set(fact_order_items_df["order_id"]).issubset(valid)


# ── fact_reviews ───────────────────────────────────────────────────────────

class TestFactReviews:
    def test_deduplicates_per_order(self, raw_reviews, fact_orders_df):
        result = build_fact_reviews(raw_reviews, fact_orders_df)
        assert result["order_id"].duplicated().sum() == 0

    def test_review_flags(self, raw_reviews, fact_orders_df):
        result = build_fact_reviews(raw_reviews, fact_orders_df)
        assert "is_positive_review" in result.columns
        assert "is_negative_review" in result.columns
        # score=5 should be positive
        pos = result[result["review_score"] == 5]
        assert pos["is_positive_review"].all()

    def test_has_comment_flag(self, raw_reviews, fact_orders_df):
        result = build_fact_reviews(raw_reviews, fact_orders_df)
        assert "has_comment" in result.columns


# ── daily revenue ──────────────────────────────────────────────────────────

class TestDailyRevenue:
    def test_only_completed_orders(self, fact_orders_df):
        daily = build_daily_revenue(fact_orders_df)
        completed_revenue = fact_orders_df[fact_orders_df["is_completed"]]["total_payment"].sum()
        assert abs(daily["revenue"].sum() - completed_revenue) < 0.01

    def test_required_columns(self, fact_orders_df):
        daily = build_daily_revenue(fact_orders_df)
        for col in ["ds","revenue","num_orders","unique_customers","aov"]:
            assert col in daily.columns

    def test_sorted_ascending(self, fact_orders_df):
        daily = build_daily_revenue(fact_orders_df)
        assert daily["ds"].is_monotonic_increasing


# ── customer features (RFM) ────────────────────────────────────────────────

class TestCustomerFeatures:
    def test_rfm_score_range(self, fact_orders_df, raw_customers):
        result = build_customer_features(fact_orders_df, raw_customers)
        assert result["rfm_score"].between(3, 15).all()

    def test_churn_flag_exists(self, fact_orders_df, raw_customers):
        result = build_customer_features(fact_orders_df, raw_customers)
        assert "is_churned" in result.columns

    def test_rfm_segment_labels(self, fact_orders_df, raw_customers):
        result = build_customer_features(fact_orders_df, raw_customers)
        valid = {"Champions","Loyal Customers","At Risk","Hibernating","Lost"}
        assert set(result["rfm_segment"].unique()).issubset(valid)


# ── state revenue ──────────────────────────────────────────────────────────

class TestStateRevenue:
    def test_only_delivered(self, fact_orders_df):
        result = build_state_revenue(fact_orders_df)
        delivered_revenue = fact_orders_df[fact_orders_df["is_delivered"]]["total_payment"].sum()
        assert abs(result["revenue"].sum() - delivered_revenue) < 0.01

    def test_state_names_mapped(self, fact_orders_df):
        result = build_state_revenue(fact_orders_df)
        assert "state_name" in result.columns
