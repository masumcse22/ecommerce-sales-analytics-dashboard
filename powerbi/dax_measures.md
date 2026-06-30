# DAX Measures — Olist Dashboard

Paste these into Power BI via **Home → New Measure**.
All monetary values are in **Brazilian Real (R$)**.

---

## Revenue

```dax
Total Revenue =
CALCULATE(
    SUM(FactOrders[total_payment]),
    FactOrders[is_completed] = TRUE()
)

Revenue MoM % =
VAR curr = [Total Revenue]
VAR prev = CALCULATE([Total Revenue], DATEADD(DimDate[Date], -1, MONTH))
RETURN DIVIDE(curr - prev, prev)

Revenue YoY % =
VAR curr = [Total Revenue]
VAR prev = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(DimDate[Date]))
RETURN DIVIDE(curr - prev, prev)

Revenue YTD =
TOTALYTD([Total Revenue], DimDate[Date])

Avg Daily Revenue =
AVERAGEX(
    VALUES(DimDate[Date]),
    CALCULATE(SUM(FactOrders[total_payment]))
)
```

---

## Orders

```dax
Total Orders =
CALCULATE(
    COUNTROWS(FactOrders),
    FactOrders[is_completed] = TRUE()
)

AOV =
DIVIDE([Total Revenue], [Total Orders])

Cancellation Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(FactOrders), FactOrders[is_cancelled] = TRUE()),
    COUNTROWS(FactOrders)
) * 100

Late Order Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactOrders),
        FactOrders[is_delivered] = TRUE(),
        FactOrders[delivery_delay_days] > 0
    ),
    CALCULATE(COUNTROWS(FactOrders), FactOrders[is_delivered] = TRUE())
) * 100

Avg Delivery Days =
CALCULATE(
    AVERAGE(FactOrders[days_to_customer]),
    FactOrders[is_delivered] = TRUE()
)

Avg Delay Days =
CALCULATE(
    AVERAGE(FactOrders[delivery_delay_days]),
    FactOrders[is_delivered] = TRUE()
)
```

---

## Products & Reviews

```dax
Total Units Sold = SUM(FactOrderItems[order_item_id])

Total Freight Revenue = SUM(FactOrderItems[freight_value])

Avg Review Score =
AVERAGE(FactReviews[review_score])

Positive Review Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(FactReviews), FactReviews[is_positive_review] = TRUE()),
    COUNTROWS(FactReviews)
) * 100

Negative Review Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(FactReviews), FactReviews[is_negative_review] = TRUE()),
    COUNTROWS(FactReviews)
) * 100
```

---

## Customer & Churn

```dax
Unique Customers =
CALCULATE(
    DISTINCTCOUNT(FactOrders[customer_id]),
    FactOrders[is_completed] = TRUE()
)

Unique Repeat Customers =
CALCULATE(
    DISTINCTCOUNT(CustomerRFM[customer_unique_id]),
    CustomerRFM[frequency] > 1
)

Repeat Purchase Rate % =
DIVIDE([Unique Repeat Customers], COUNTROWS(CustomerRFM)) * 100

Avg Customer LTV =
AVERAGE(CustomerRFM[monetary])

Churn Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(CustomerRFM), CustomerRFM[is_churned] = "True"),
    COUNTROWS(CustomerRFM)
) * 100

High Risk Customers =
CALCULATE(
    COUNTROWS(ChurnPredictions),
    ChurnPredictions[churn_risk] = "High"
)

Avg Churn Probability =
AVERAGE(ChurnPredictions[churn_probability])
```

---

## Forecast

```dax
Forecast Revenue =
SUM(Forecast[forecast])

Forecast Upper Bound =
SUM(Forecast[forecast_upper])

Forecast Lower Bound =
SUM(Forecast[forecast_lower])

Next Quarter Forecast =
CALCULATE(
    SUM(Forecast[forecast]),
    DATESINPERIOD(
        DimDate[Date],
        TODAY(),
        3,
        MONTH
    )
)

Forecast vs Actual =
[Total Revenue] - [Forecast Revenue]
```

---

## Conditional Formatting Helpers

```dax
-- Traffic light for MoM growth
Revenue Colour =
SWITCH(
    TRUE(),
    [Revenue MoM %] >= 0.05, "Green",
    [Revenue MoM %] >= 0,    "Yellow",
    "Red"
)

-- Traffic light for late orders
Delay Colour =
SWITCH(
    TRUE(),
    [Late Order Rate %] <= 5,  "Green",
    [Late Order Rate %] <= 15, "Yellow",
    "Red"
)

-- Review score label
Review Label =
SWITCH(
    TRUE(),
    [Avg Review Score] >= 4.5, "Excellent",
    [Avg Review Score] >= 4.0, "Good",
    [Avg Review Score] >= 3.0, "Average",
    "Poor"
)
```
