"""
forecasting/arima_forecast.py
SARIMA revenue forecasting for Olist daily_revenue data.
Aggregates daily → monthly, fits SARIMA, forecasts 12 months.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import warnings
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_PROCESSED, FORECAST_HORIZON_MONTHS

warnings.filterwarnings("ignore")


def aggregate_to_monthly(daily_revenue: pd.DataFrame) -> pd.Series:
    """
    Convert daily revenue data into monthly revenue series
    """

    df = daily_revenue.copy()

    df["ds"] = pd.to_datetime(df["ds"])

    monthly = (
        df.groupby(df["ds"].dt.to_period("M"))["revenue"]
        .sum()
        .sort_index()
    )

    monthly.index = monthly.index.to_timestamp()

    return monthly



def run_arima_forecast(
    daily_revenue: pd.DataFrame,
    horizon: int = FORECAST_HORIZON_MONTHS,
    order: tuple = (1, 1, 1),
    seasonal_order: tuple = (1, 1, 0, 12),
) -> pd.DataFrame:

    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

    except ImportError:
        raise ImportError("Install statsmodels: pip install statsmodels")


    # Aggregate daily -> monthly
    monthly = aggregate_to_monthly(daily_revenue)


    logger.info(
        f"SARIMA{order}x{seasonal_order} | "
        f"{len(monthly)} months history | "
        f"horizon={horizon} months"
    )


    # Need enough data for seasonal SARIMA
    if len(monthly) < 24:

        logger.warning(
            f"Only {len(monthly)} months available. "
            "Using non-seasonal ARIMA."
        )

        seasonal_order = (0, 0, 0, 0)



    # Train SARIMA model

    model = SARIMAX(
        monthly,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )


    fit = model.fit(disp=False)


    logger.info(
        f"AIC={fit.aic:.1f} BIC={fit.bic:.1f}"
    )



    # Forecast

    forecast_obj = fit.get_forecast(
        steps=horizon
    )


    fc_mean = forecast_obj.predicted_mean

    fc_ci = forecast_obj.conf_int(
        alpha=0.10
    )



    # Forecast dataframe

    result = pd.DataFrame({

        "year_month": pd.date_range(
            start=monthly.index.max()
            + pd.offsets.MonthBegin(),

            periods=len(fc_mean),

            freq="MS"

        ).strftime("%Y-%m"),


        "forecast":
            np.clip(
                fc_mean.values,
                0,
                None
            ).round(2),


        "forecast_lower":
            np.clip(
                fc_ci.iloc[:, 0].values,
                0,
                None
            ).round(2),


        "forecast_upper":
            fc_ci.iloc[:, 1].values.round(2),


        "method":
            "SARIMA"

    })



    # Historical data

    hist = pd.DataFrame({

        "year_month":
            monthly.index.strftime("%Y-%m"),


        "revenue":
            monthly.values.round(2),


        "forecast":
            np.nan,


        "forecast_lower":
            np.nan,


        "forecast_upper":
            np.nan,


        "method":
            "actual"

    })



    # Combine actual + forecast

    forecast_for_chart = result.rename(
        columns={
            "forecast": "revenue"
        }
    )


    combined = pd.concat(
        [
            hist,
            forecast_for_chart
        ],

        ignore_index=True
    )



    # Save files

    DATA_PROCESSED.mkdir(
        parents=True,
        exist_ok=True
    )


    result.to_csv(
        DATA_PROCESSED / "forecast_arima.csv",
        index=False
    )


    combined.to_csv(
        DATA_PROCESSED / "forecast_combined.csv",
        index=False
    )



    logger.success(
        f"SARIMA forecast saved | "
        f"Average forecast: {result['forecast'].mean():,.0f}"
    )


    return result





if __name__ == "__main__":


    daily = pd.read_csv(
        DATA_PROCESSED / "daily_revenue.csv"
    )


    output = run_arima_forecast(
        daily
    )


    print(output)