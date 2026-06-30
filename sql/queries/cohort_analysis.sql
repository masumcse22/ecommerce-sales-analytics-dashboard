-- Monthly cohort retention based on customer_unique_id
WITH first_orders AS (
    SELECT
        c.customer_unique_id,
        MIN(strftime('%Y-%m', o.order_purchase_timestamp)) AS cohort_month
    FROM fact_orders o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.is_completed = 1
    GROUP BY c.customer_unique_id
),
all_orders AS (
    SELECT
        c.customer_unique_id,
        strftime('%Y-%m', o.order_purchase_timestamp) AS order_month
    FROM fact_orders o
    JOIN dim_customer c ON o.customer_id = c.customer_id
    WHERE o.is_completed = 1
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_n
    FROM first_orders GROUP BY cohort_month
),
retention AS (
    SELECT
        f.cohort_month,
        a.order_month,
        COUNT(DISTINCT a.customer_unique_id) AS active_n
    FROM first_orders f
    JOIN all_orders a ON f.customer_unique_id = a.customer_unique_id
    GROUP BY f.cohort_month, a.order_month
)
SELECT
    r.cohort_month,
    r.order_month,
    cs.cohort_n,
    r.active_n,
    ROUND(r.active_n * 100.0 / cs.cohort_n, 2) AS retention_pct
FROM retention r
JOIN cohort_size cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.order_month;
