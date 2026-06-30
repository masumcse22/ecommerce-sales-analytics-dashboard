-- Top product categories by revenue and average review score
SELECT
    p.category_en,
    COUNT(DISTINCT oi.product_id)       AS num_products,
    SUM(oi.price)                       AS gross_revenue,
    SUM(oi.freight_value)               AS total_freight,
    COUNT(oi.order_id)                  AS num_order_lines,
    ROUND(AVG(oi.price), 2)            AS avg_item_price,
    ROUND(AVG(r.review_score), 2)      AS avg_review_score
FROM fact_order_items oi
JOIN dim_product p ON oi.product_id = p.product_id
JOIN fact_orders o  ON oi.order_id  = o.order_id
LEFT JOIN fact_reviews r ON oi.order_id = r.order_id
WHERE o.is_delivered = 1
  AND p.category_en IS NOT NULL
GROUP BY p.category_en
ORDER BY gross_revenue DESC
LIMIT 30;
