-- ============================================================
-- schema.sql  –  Olist E-Commerce Data Warehouse
-- Star schema compatible with PostgreSQL 14+ and SQLite 3
-- ============================================================

-- ── Dimension: Date ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    DATE        PRIMARY KEY,
    year        INTEGER     NOT NULL,
    quarter     INTEGER     NOT NULL,
    month       INTEGER     NOT NULL,
    month_name  VARCHAR(12) NOT NULL,
    week        INTEGER     NOT NULL,
    day         INTEGER     NOT NULL,
    day_name    VARCHAR(12) NOT NULL,
    is_weekend  BOOLEAN     NOT NULL,
    yyyymm      INTEGER     NOT NULL
);

-- ── Dimension: Customer ──────────────────────────────────────
-- Note: Olist has two IDs.
--   customer_id        = unique per order (changes per purchase)
--   customer_unique_id = true repeat-customer identifier
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id         VARCHAR(50) PRIMARY KEY,
    customer_unique_id  VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city       VARCHAR(80),
    customer_state      VARCHAR(5)
);

-- ── Dimension: Product ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_product (
    product_id              VARCHAR(50) PRIMARY KEY,
    category_pt             VARCHAR(100),
    category_en             VARCHAR(100),
    product_name_length     INTEGER,
    product_description_length INTEGER,
    product_photos_qty      INTEGER,
    product_weight_g        NUMERIC(10,2),
    product_length_cm       NUMERIC(8,2),
    product_height_cm       NUMERIC(8,2),
    product_width_cm        NUMERIC(8,2)
);

-- ── Dimension: Seller ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_seller (
    seller_id               VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix  VARCHAR(10),
    seller_city             VARCHAR(80),
    seller_state            VARCHAR(5)
);

-- ── Fact: Orders ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id                    VARCHAR(50) PRIMARY KEY,
    customer_id                 VARCHAR(50),
    customer_state              VARCHAR(5),
    customer_city               VARCHAR(80),
    order_status                VARCHAR(20),
    order_purchase_timestamp    TIMESTAMP,
    order_approved_at           TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    order_date                  DATE,
    order_year                  INTEGER,
    order_month                 INTEGER,
    order_quarter               INTEGER,
    order_dow                   VARCHAR(12),
    order_week                  INTEGER,
    total_payment               NUMERIC(12,2),
    num_installments            INTEGER,
    payment_types               VARCHAR(100),
    days_to_carrier             INTEGER,
    days_to_customer            INTEGER,
    delivery_delay_days         NUMERIC(8,2),
    is_delivered                BOOLEAN,
    is_cancelled                BOOLEAN,
    is_completed                BOOLEAN
);

-- ── Fact: Order Items ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_order_items (
    order_id            VARCHAR(50),
    order_item_id       INTEGER,
    product_id          VARCHAR(50),
    seller_id           VARCHAR(50),
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10,2),
    freight_value       NUMERIC(10,2),
    line_total          NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- ── Fact: Reviews ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_reviews (
    review_id           VARCHAR(50) PRIMARY KEY,
    order_id            VARCHAR(50),
    review_score        INTEGER,
    review_creation_date TIMESTAMP,
    has_comment         BOOLEAN,
    is_positive_review  BOOLEAN,
    is_negative_review  BOOLEAN
);

-- ── Aggregates ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agg_daily_revenue (
    ds                  DATE PRIMARY KEY,
    revenue             NUMERIC(14,2),
    num_orders          INTEGER,
    unique_customers    INTEGER,
    aov                 NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS agg_customer_rfm (
    customer_unique_id  VARCHAR(50) PRIMARY KEY,
    first_order_date    TIMESTAMP,
    last_order_date     TIMESTAMP,
    frequency           INTEGER,
    monetary            NUMERIC(14,2),
    recency_days        INTEGER,
    tenure_days         INTEGER,
    aov                 NUMERIC(10,2),
    is_churned          BOOLEAN,
    r_score             INTEGER,
    f_score             INTEGER,
    m_score             INTEGER,
    rfm_score           INTEGER,
    rfm_segment         VARCHAR(30),
    state               VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS agg_product_perf (
    product_id          VARCHAR(50) PRIMARY KEY,
    category_en         VARCHAR(100),
    total_units_sold    INTEGER,
    total_revenue       NUMERIC(14,2),
    total_freight       NUMERIC(12,2),
    num_orders          INTEGER,
    avg_price           NUMERIC(10,2),
    aov_product         NUMERIC(10,2),
    revenue_rank        INTEGER,
    avg_review_score    NUMERIC(4,2)
);

CREATE TABLE IF NOT EXISTS agg_state_revenue (
    customer_state      VARCHAR(5) PRIMARY KEY,
    state_name          VARCHAR(60),
    revenue             NUMERIC(14,2),
    num_orders          INTEGER,
    unique_customers    INTEGER,
    avg_delay_days      NUMERIC(8,2),
    aov                 NUMERIC(10,2),
    revenue_rank        INTEGER
);

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_orders_date       ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer   ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_state      ON fact_orders(customer_state);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON fact_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_items_order       ON fact_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product     ON fact_order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller      ON fact_order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order     ON fact_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_score     ON fact_reviews(review_score);
