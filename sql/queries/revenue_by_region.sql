-- queries/revenue_by_region.sql
-- Top 20 country revenue breakdown with YoY growth

WITH base AS (
    SELECT
        o.region,
        o.country,
        d.year,
        SUM(o.total_amount) AS revenue
    FROM fact_orders o
    JOIN dim_date d ON o.order_date = d.date_key
    WHERE o.is_completed = TRUE
    GROUP BY o.region, o.country, d.year
),
yoy AS (
    SELECT
        curr.region,
        curr.country,
        curr.year,
        curr.revenue,
        prev.revenue AS prev_year_revenue,
        ROUND(
            (curr.revenue - prev.revenue) / NULLIF(prev.revenue, 0) * 100, 2
        ) AS yoy_growth_pct
    FROM base curr
    LEFT JOIN base prev
        ON curr.country = prev.country
       AND curr.year    = prev.year + 1
)
SELECT *
FROM yoy
ORDER BY revenue DESC
LIMIT 20;
