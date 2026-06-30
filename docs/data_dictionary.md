# Data Dictionary — Olist E-Commerce Warehouse

Currency: **Brazilian Real (R$)**  
Date range: **September 2016 – September 2018**

---

## Raw Source Files (data/raw/)

| Olist CSV file | Rows (approx) | Description |
|---|---|---|
| `olist_orders_dataset.csv` | 99,441 | Core order metadata |
| `olist_customers_dataset.csv` | 99,441 | Customer IDs and location |
| `olist_order_items_dataset.csv` | 112,650 | Line items per order |
| `olist_order_payments_dataset.csv` | 103,886 | Payment details |
| `olist_order_reviews_dataset.csv` | 99,224 | Customer review scores and text |
| `olist_products_dataset.csv` | 32,951 | Product metadata |
| `olist_sellers_dataset.csv` | 3,095 | Seller location |
| `olist_geolocation_dataset.csv` | 1,000,163 | Zip code → lat/lng |
| `product_category_name_translation.csv` | 71 | Portuguese → English |

---

## Processed Tables (data/processed/)

### dim_customer.csv

| Column | Type | Description |
|---|---|---|
| customer_id | string | PK — unique per order (changes per purchase!) |
| customer_unique_id | string | True customer identifier (use for repeat analysis) |
| customer_zip_code_prefix | string | First 5 digits of zip code |
| customer_city | string | Customer city (title-cased) |
| customer_state | string | 2-letter Brazilian state code (upper-case) |

> **Note:** The same real person appears with different `customer_id` values for each order. Use `customer_unique_id` for retention and repeat-purchase analysis.

---

### dim_product.csv

| Column | Type | Description |
|---|---|---|
| product_id | string | PK |
| category_pt | string | Category name in Portuguese |
| category_en | string | Category name in English (translated) |
| product_name_length | int | Number of chars in product name |
| product_description_length | int | Description length |
| product_photos_qty | int | Number of product images |
| product_weight_g | float | Weight in grams |
| product_length_cm | float | Length (cm) |
| product_height_cm | float | Height (cm) |
| product_width_cm | float | Width (cm) |

---

### dim_seller.csv

| Column | Type | Description |
|---|---|---|
| seller_id | string | PK |
| seller_zip_code_prefix | string | First 5 digits of zip |
| seller_city | string | Seller city |
| seller_state | string | 2-letter state code |

---

### fact_orders.csv

| Column | Type | Description |
|---|---|---|
| order_id | string | PK |
| customer_id | string | FK → dim_customer |
| customer_state | string | Denormalised customer state |
| customer_city | string | Denormalised customer city |
| order_status | string | delivered / shipped / canceled / etc. |
| order_purchase_timestamp | datetime | When the order was placed |
| order_approved_at | datetime | When payment was approved |
| order_delivered_carrier_date | datetime | When handed to carrier |
| order_delivered_customer_date | datetime | When received by customer |
| order_estimated_delivery_date | datetime | Estimated delivery |
| order_date | date | Date portion of purchase timestamp |
| order_year | int | Year |
| order_month | int | Month (1–12) |
| order_quarter | int | Quarter (1–4) |
| order_dow | string | Day of week |
| order_week | int | ISO week number |
| total_payment | float | Sum of all payment values for this order (R$) |
| num_installments | int | Maximum installment count across payments |
| payment_types | string | Pipe-separated payment methods (e.g. "boleto\|credit_card") |
| days_to_carrier | int | Days from purchase → carrier pickup |
| days_to_customer | int | Days from purchase → customer delivery |
| delivery_delay_days | float | Actual − estimated delivery (positive = late) |
| is_delivered | bool | order_status == "delivered" |
| is_cancelled | bool | order_status == "canceled" |
| is_completed | bool | Same as is_delivered |

---

### fact_order_items.csv

| Column | Type | Description |
|---|---|---|
| order_id | string | FK → fact_orders |
| order_item_id | int | Item sequence within order (1-based) |
| product_id | string | FK → dim_product |
| seller_id | string | FK → dim_seller |
| shipping_limit_date | datetime | Seller's deadline to ship |
| price | float | Item price (R$) — excludes freight |
| freight_value | float | Freight cost for this item (R$) |
| line_total | float | price + freight_value |

---

### fact_reviews.csv

| Column | Type | Description |
|---|---|---|
| review_id | string | PK (deduplicated to one per order) |
| order_id | string | FK → fact_orders |
| review_score | int | 1–5 stars |
| review_creation_date | datetime | When review was submitted |
| has_comment | bool | Whether review_comment_message is non-null |
| is_positive_review | bool | review_score >= 4 |
| is_negative_review | bool | review_score <= 2 |

---

### daily_revenue.csv  (for forecasting)

| Column | Type | Description |
|---|---|---|
| ds | date | Calendar date (Prophet convention) |
| revenue | float | Total completed-order revenue (R$) |
| num_orders | int | Count of completed orders |
| unique_customers | int | Distinct customers |
| aov | float | Average order value (R$) |

---

### customer_features.csv  (RFM)

| Column | Type | Description |
|---|---|---|
| customer_unique_id | string | PK — true repeat-customer key |
| first_order_date | datetime | Date of first order |
| last_order_date | datetime | Date of most recent order |
| frequency | int | Total completed orders |
| monetary | float | Total lifetime spend (R$) |
| recency_days | int | Days since last order |
| tenure_days | int | Days from first order to snapshot |
| aov | float | Average order value (R$) |
| is_churned | bool | recency_days > 180 |
| r_score | int | Recency quintile (1=worst, 5=best) |
| f_score | int | Frequency quintile |
| m_score | int | Monetary quintile |
| rfm_score | int | r + f + m (range 3–15) |
| rfm_segment | string | Champions / Loyal Customers / At Risk / Hibernating / Lost |
| state | string | Customer's state |

---

### product_performance.csv

| Column | Type | Description |
|---|---|---|
| product_id | string | PK |
| category_en | string | English category |
| total_units_sold | int | Count of order line items |
| total_revenue | float | Sum of item prices (R$) |
| total_freight | float | Sum of freight values (R$) |
| num_orders | int | Distinct orders containing this product |
| avg_price | float | Average item price (R$) |
| aov_product | float | Revenue ÷ num_orders |
| revenue_rank | int | 1 = highest revenue |
| avg_review_score | float | Average review score (1–5) |

---

### state_revenue.csv

| Column | Type | Description |
|---|---|---|
| customer_state | string | PK — 2-letter state code |
| state_name | string | Full state name in Portuguese |
| revenue | float | Total delivered revenue (R$) |
| num_orders | int | Delivered order count |
| unique_customers | int | Distinct customer_ids |
| avg_delay_days | float | Average delivery delay (positive = late) |
| aov | float | Average order value (R$) |
| revenue_rank | int | 1 = highest revenue |

---

### forecast_arima.csv

| Column | Type | Description |
|---|---|---|
| year_month | string | Format YYYY-MM |
| forecast | float | Predicted monthly revenue (R$) |
| forecast_lower | float | Lower bound — 90% confidence interval |
| forecast_upper | float | Upper bound — 90% confidence interval |
| method | string | SARIMA or Prophet |

---

### churn_predictions.csv

| Column | Type | Description |
|---|---|---|
| customer_unique_id | string | PK |
| churn_probability | float | GBM model score (0–1) |
| churn_risk | string | Low / Medium / High |
| is_churned | string | Actual observed label ("True"/"False") |
| recency_days | int | Days since last order |
| frequency | int | Total orders |
| monetary | float | Total spend (R$) |
| aov | float | Average order value (R$) |
| rfm_score | int | Combined RFM score |
| rfm_segment | string | RFM segment label |
| state | string | Customer state |
