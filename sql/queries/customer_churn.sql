-- queries/customer_churn.sql
-- Churn rate by segment and region

SELECT
    c.segment,
    c.region,
    COUNT(cf.customer_id)                                           AS total_customers,
    SUM(CASE WHEN cf.is_churned = TRUE  THEN 1 ELSE 0 END)         AS churned,
    SUM(CASE WHEN cf.is_churned = FALSE THEN 1 ELSE 0 END)         AS retained,
    ROUND(SUM(CASE WHEN cf.is_churned = TRUE THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(COUNT(cf.customer_id), 0), 2)           AS churn_rate_pct,
    AVG(cf.monetary)                                                AS avg_ltv,
    AVG(cf.frequency)                                               AS avg_orders
FROM agg_customer_features cf
JOIN dim_customer c USING (customer_id)
GROUP BY c.segment, c.region
ORDER BY churn_rate_pct DESC;
