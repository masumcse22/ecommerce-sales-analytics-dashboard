-- ============================================================
-- views.sql  –  Analytical Views for Olist (Power BI / reporting)
-- ============================================================

-- ── V1: Monthly Revenue ───────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_monthly_revenue AS
SELECT
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    d.yyyymm,
    COUNT(DISTINCT o.order_id)      AS num_orders,
    COUNT(DISTINCT o.customer_id)   AS unique_customers,
    ROUND(SUM(o.total_payment), 2)  AS revenue,
    ROUND(AVG(o.total_payment), 2)  AS aov
FROM fact_orders o
JOIN dim_date d ON o.order_date = d.date_key
WHERE o.is_completed = 1
GROUP BY d.year, d.quarter, d.month, d.month_name, d.yyyymm
ORDER BY d.yyyymm;


-- ── V2: Revenue by State ──────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_revenue_by_state AS
SELECT
    s.customer_state,
    s.state_name,
    s.revenue,
    s.num_orders,
    s.unique_customers,
    s.aov,
    s.avg_delay_days,
    s.revenue_rank
FROM agg_state_revenue s
ORDER BY s.revenue DESC;


-- ── V3: Product Performance ───────────────────────────────────
CREATE VIEW IF NOT EXISTS v_product_performance AS
SELECT
    p.product_id,
    p.category_en,
    ap.total_units_sold,
    ROUND(ap.total_revenue, 2)   AS total_revenue,
    ROUND(ap.total_freight, 2)   AS total_freight,
    ap.num_orders,
    ROUND(ap.avg_price, 2)       AS avg_price,
    ROUND(ap.aov_product, 2)     AS aov_product,
    ap.revenue_rank,
    ROUND(ap.avg_review_score,2) AS avg_review_score
FROM agg_product_perf ap
JOIN dim_product p USING (product_id)
ORDER BY ap.revenue_rank;


-- ── V4: Category Summary ──────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_category_summary AS
SELECT
    p.category_en,
    COUNT(DISTINCT ap.product_id)  AS num_products,
    SUM(ap.total_units_sold)       AS total_units_sold,
    ROUND(SUM(ap.total_revenue),2) AS total_revenue,
    ROUND(AVG(ap.avg_review_score),2) AS avg_review_score,
    ROUND(AVG(ap.avg_price),2)     AS avg_price
FROM agg_product_perf ap
JOIN dim_product p USING (product_id)
WHERE p.category_en IS NOT NULL
GROUP BY p.category_en
ORDER BY total_revenue DESC;


-- ── V5: Customer RFM Segments ─────────────────────────────────
CREATE VIEW IF NOT EXISTS v_customer_rfm AS
SELECT
    rfm_segment,
    customer_state  AS state,
    COUNT(*)                            AS num_customers,
    ROUND(AVG(monetary), 2)            AS avg_ltv,
    ROUND(AVG(frequency), 2)           AS avg_orders,
    ROUND(AVG(recency_days), 0)        AS avg_recency_days,
    SUM(CASE WHEN is_churned = 'True' OR is_churned = 1 THEN 1 ELSE 0 END) AS churned_count
FROM agg_customer_rfm
GROUP BY rfm_segment, customer_state;


-- ── V6: Churn Rate by State ───────────────────────────────────
CREATE VIEW IF NOT EXISTS v_churn_by_state AS
SELECT
    state,
    COUNT(*)                                                          AS total_customers,
    SUM(CASE WHEN is_churned IN ('True','1',1) THEN 1 ELSE 0 END)   AS churned,
    ROUND(
        SUM(CASE WHEN is_churned IN ('True','1',1) THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2
    )                                                                 AS churn_rate_pct,
    ROUND(AVG(CAST(monetary AS REAL)), 2)                            AS avg_ltv
FROM agg_customer_rfm
GROUP BY state
ORDER BY churn_rate_pct DESC;


-- ── V7: Delivery Performance ──────────────────────────────────
CREATE VIEW IF NOT EXISTS v_delivery_performance AS
SELECT
    d.year,
    d.month,
    d.month_name,
    o.customer_state,
    ROUND(AVG(o.days_to_customer), 2)    AS avg_delivery_days,
    ROUND(AVG(o.delivery_delay_days), 2) AS avg_delay_days,
    SUM(CASE WHEN o.delivery_delay_days > 0 THEN 1 ELSE 0 END) AS late_orders,
    COUNT(*)                              AS total_orders,
    ROUND(
        SUM(CASE WHEN o.delivery_delay_days > 0 THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2
    )                                     AS late_rate_pct
FROM fact_orders o
JOIN dim_date d ON o.order_date = d.date_key
WHERE o.is_delivered = 1
GROUP BY d.year, d.month, d.month_name, o.customer_state;


-- ── V8: Payment Method Mix ────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_payment_mix AS
SELECT
    payment_types,
    COUNT(*)                           AS num_orders,
    ROUND(SUM(total_payment), 2)       AS total_revenue,
    ROUND(AVG(total_payment), 2)       AS avg_order_value,
    ROUND(AVG(num_installments), 2)    AS avg_installments
FROM fact_orders
WHERE is_completed = 1
GROUP BY payment_types
ORDER BY num_orders DESC;


-- ── V9: Review Score Distribution ────────────────────────────
CREATE VIEW IF NOT EXISTS v_review_distribution AS
SELECT
    review_score,
    COUNT(*)                                    AS num_reviews,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM fact_reviews
GROUP BY review_score
ORDER BY review_score;
