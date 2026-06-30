# Power BI Dashboard – Olist Setup Guide

## What you'll build: 6-page interactive dashboard

| Page | Content |
|---|---|
| 1. Executive Summary | Revenue KPIs, monthly trend, order status |
| 2. Regional Analysis | Brazil state heatmap, state ranking table |
| 3. Product & Category | Category treemap, top products, review scores |
| 4. Customer RFM | Segment donuts, churn risk table |
| 5. Delivery & Reviews | Delay heatmap, review score distribution |
| 6. Forecast | 12-month revenue forecast with confidence band |

---

## Step 1 — Download & place the data

1. Download the Olist dataset from Kaggle:
   https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Place all 9 CSV files in `data/raw/`
3. Run the pipeline: `python main.py`
4. Your Power BI files will be in `data/processed/`

---

## Step 2 — Connect to Power BI Desktop

**Home → Get Data → Folder** → select `data/processed/`

Import each file as its own table:

| File | Table name in Power BI |
|---|---|
| `fact_orders.csv` | `FactOrders` |
| `fact_order_items.csv` | `FactOrderItems` |
| `fact_reviews.csv` | `FactReviews` |
| `dim_customer.csv` | `DimCustomer` |
| `dim_product.csv` | `DimProduct` |
| `dim_seller.csv` | `DimSeller` |
| `daily_revenue.csv` | `DailyRevenue` |
| `customer_features.csv` | `CustomerRFM` |
| `product_performance.csv` | `ProductPerf` |
| `state_revenue.csv` | `StateRevenue` |
| `forecast_arima.csv` | `Forecast` |
| `churn_predictions.csv` | `ChurnPredictions` |

---

## Step 3 — Set column types

In **Power Query Editor**, set these types:

**FactOrders:**
- `order_purchase_timestamp` → Date/Time
- `order_date` → Date
- `total_payment` → Decimal Number
- `is_delivered`, `is_cancelled`, `is_completed` → True/False
- `delivery_delay_days` → Decimal Number

**DailyRevenue:**
- `ds` → Date
- `revenue`, `aov` → Decimal Number

**CustomerRFM:**
- `monetary`, `aov` → Decimal Number
- `is_churned` → Text (keep as "True"/"False" for DAX)

**Forecast:**
- `forecast`, `forecast_lower`, `forecast_upper` → Decimal Number

---

## Step 4 — Build Relationships (Model view)

```
FactOrders[customer_id]    → DimCustomer[customer_id]    (Many-to-One)
FactOrderItems[order_id]   → FactOrders[order_id]         (Many-to-One)
FactOrderItems[product_id] → DimProduct[product_id]       (Many-to-One)
FactOrderItems[seller_id]  → DimSeller[seller_id]         (Many-to-One)
FactReviews[order_id]      → FactOrders[order_id]         (Many-to-One)
CustomerRFM[customer_unique_id] → DimCustomer[customer_unique_id] (Many-to-One)
ProductPerf[product_id]    → DimProduct[product_id]       (One-to-One)
StateRevenue[customer_state] → FactOrders[customer_state] (One-to-Many)
```

---

## Step 5 — Add a Date Table

In **Home → New Table** paste:

```dax
DimDate = CALENDAR(DATE(2016,9,1), DATE(2018,9,30))
```

Then add columns:
```dax
Year    = YEAR(DimDate[Date])
Month   = MONTH(DimDate[Date])
Quarter = QUARTER(DimDate[Date])
MonthName = FORMAT(DimDate[Date], "MMMM")
YearMonth = FORMAT(DimDate[Date], "YYYY-MM")
```

Mark it as a **Date Table** (Table Tools → Mark as date table → Date).

Connect: `FactOrders[order_date] → DimDate[Date]`

---

## Step 6 — Slicers panel (add to all pages)

- `DimDate[Year]`
- `DimDate[Quarter]`
- `FactOrders[customer_state]`
- `DimProduct[category_en]`
- `FactOrders[order_status]`
- `CustomerRFM[rfm_segment]`

---

## Step 7 — Page-by-page build

### Page 1: Executive Summary
- **4 KPI Cards**: Total Revenue, Total Orders, AOV, Avg Review Score
- **Line Chart**: `DimDate[YearMonth]` vs `[Total Revenue]` + `[Forecast Revenue]` (dual line)
- **Donut Chart**: `FactOrders[order_status]` by count
- **Bar Chart**: Top 5 states by revenue (from `StateRevenue`)

### Page 2: Regional Analysis
- **Filled Map**: `StateRevenue[customer_state]` coloured by `[revenue]`
  - Use "Brazil" as map scope
- **Bar Chart**: Top 10 states — revenue, num_orders, avg_delay_days
- **Matrix**: State × Month revenue

### Page 3: Product & Category
- **Treemap**: `DimProduct[category_en]` → `[Total Revenue]`
- **Scatter Plot**: `[avg_price]` (X) vs `[avg_review_score]` (Y), size = `[total_units_sold]`, colour = category
- **Table**: Top 20 products (product_id, category_en, total_revenue, avg_review_score, revenue_rank)

### Page 4: Customer RFM
- **Donut**: RFM segments (Champions / Loyal / At Risk / Hibernating / Lost)
- **Bar**: `CustomerRFM[rfm_segment]` vs avg monetary
- **Table**: At-Risk customers — churn_probability, recency_days, monetary (from `ChurnPredictions`)
- **Scatter**: recency_days (X) vs frequency (Y), size=monetary, colour=rfm_segment

### Page 5: Delivery & Reviews
- **Clustered Bar**: `[avg_delay_days]` by state
- **Bar Chart**: `FactReviews[review_score]` count distribution (1–5 stars)
- **Line Chart**: monthly `[avg_delivery_days]` trend
- **KPI Card**: Late Order Rate %

### Page 6: Forecast
- **Line Chart**: Actual revenue (from `DailyRevenue` or monthly rollup) + `Forecast[forecast]`
  - Add `forecast_lower` and `forecast_upper` as shaded area using Line + Clustered Column combo
- **Table**: `Forecast` table with year_month, forecast, lower, upper
- **KPI**: Next-quarter forecast total

---

## Step 8 — Publish to Power BI Service (optional)

1. **File → Publish → To Power BI**
2. Set up a **Personal Gateway** pointing to your `data/processed/` folder
3. Configure **Scheduled Refresh** (daily)
4. Automate ETL via GitHub Actions (`.github/workflows/ci.yml`) or a cron job
