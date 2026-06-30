-- Top sellers: revenue, order count, avg review
SELECT
    oi.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)         AS num_orders,
    SUM(oi.price)                       AS total_revenue,
    ROUND(AVG(oi.price), 2)            AS avg_item_price,
    ROUND(AVG(r.review_score), 2)      AS avg_review_score,
    ROUND(AVG(o.delivery_delay_days),2) AS avg_delay_days
FROM fact_order_items oi
JOIN fact_orders o ON oi.order_id = o.order_id
JOIN dim_seller  s ON oi.seller_id = s.seller_id
LEFT JOIN fact_reviews r ON oi.order_id = r.order_id
WHERE o.is_delivered = 1
GROUP BY oi.seller_id, s.seller_city, s.seller_state
ORDER BY total_revenue DESC
LIMIT 50;
