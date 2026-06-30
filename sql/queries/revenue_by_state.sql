-- Revenue by Brazilian state with MoM growth
WITH monthly AS (
    SELECT
        o.customer_state,
        d.yyyymm,
        d.year,
        d.month,
        SUM(o.total_payment)  AS revenue,
        COUNT(o.order_id)     AS num_orders
    FROM fact_orders o
    JOIN dim_date d ON o.order_date = d.date_key
    WHERE o.is_completed = 1
    GROUP BY o.customer_state, d.yyyymm, d.year, d.month
),
with_prev AS (
    SELECT *,
        LAG(revenue) OVER (PARTITION BY customer_state ORDER BY yyyymm) AS prev_revenue
    FROM monthly
)
SELECT
    customer_state,
    yyyymm,
    year,
    month,
    ROUND(revenue, 2) AS revenue,
    num_orders,
    ROUND((revenue - prev_revenue) / NULLIF(prev_revenue, 0) * 100, 2) AS mom_growth_pct
FROM with_prev
ORDER BY yyyymm DESC, revenue DESC;
