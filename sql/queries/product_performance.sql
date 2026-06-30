-- queries/product_performance.sql
-- Top products by revenue with margin and return analysis

SELECT
    p.category,
    p.product_name,
    ap.revenue_rank,
    ap.total_units_sold,
    ap.total_revenue,
    ap.gross_profit,
    ROUND(ap.gross_profit / NULLIF(ap.total_revenue, 0) * 100, 2) AS margin_pct,
    ROUND(ap.avg_discount * 100, 2)                               AS avg_discount_pct,
    ap.num_orders
FROM agg_product_performance ap
JOIN dim_product p USING (product_id)
ORDER BY ap.total_revenue DESC
LIMIT 50;
