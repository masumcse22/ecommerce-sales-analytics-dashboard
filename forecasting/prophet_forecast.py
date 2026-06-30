"""
forecasting/prophet_forecast.py
Revenue forecasting with Facebook Prophet for Olist data.
Adds Brazilian public holidays automatically.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED, FORECAST_HORIZON_MONTHS

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def prepare_prophet_df(daily_revenue: pd.DataFrame) -> pd.DataFrame:
    """Prepare daily_revenue for Prophet (needs ds + y columns)."""
    df = daily_revenue[["ds", "revenue"]].copy()
    df.columns = ["ds", "y"]
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.sort_values("ds").dropna()

    # Remove statistical outliers (>3 std from 30d rolling mean)
    roll_mean = df["y"].rolling(30, min_periods=1).mean()
    roll_std  = df["y"].rolling(30, min_periods=1).std().fillna(df["y"].std())
    df = df[(df["y"] - roll_mean).abs() <= 3 * roll_std]
    return df


def run_prophet_forecast(
    daily_revenue:    pd.DataFrame,
    horizon_months:   int  = FORECAST_HORIZON_MONTHS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PROPHET_AVAILABLE:
        raise ImportError("Install Prophet:  pip install prophet")

    horizon_days = horizon_months * 30
    logger.info(f"Prophet forecast | horizon={horizon_months} months …")

    df = prepare_prophet_df(daily_revenue)

    model = Prophet(
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.90,
    )
    # Brazilian national holidays
    model.add_country_holidays(country_name="BR")
    model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

    model.fit(df)

    future   = model.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = model.predict(future)

    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper",
                        "trend", "weekly", "yearly"]].copy()
    result.columns = ["date", "forecast", "forecast_lower", "forecast_upper",
                      "trend", "weekly_effect", "yearly_effect"]

    # Monthly rollup for Power BI
    result["year_month"] = pd.to_datetime(result["date"]).dt.to_period("M").astype(str)
    monthly = (
        result.groupby("year_month")
        .agg(
            forecast       = ("forecast",       "sum"),
            forecast_lower = ("forecast_lower", "sum"),
            forecast_upper = ("forecast_upper", "sum"),
            trend          = ("trend",          "mean"),
        )
        .reset_index()
        .assign(method="Prophet")
    )

    result.to_csv(DATA_PROCESSED / "forecast_daily.csv",   index=False)
    monthly.to_csv(DATA_PROCESSED / "forecast_arima.csv",  index=False)  # same name for Power BI
    logger.success(
        f"Prophet forecast → data/processed/forecast_arima.csv  "
        f"(mean R$ {monthly['forecast'].mean():,.0f}/mo)"
    )
    return result, monthly


def plot_forecast(result: pd.DataFrame, save_path: Path | None = None) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    result = result.copy()
    result["date"] = pd.to_datetime(result["date"])

    cutoff = result["date"].max() - pd.Timedelta(days=FORECAST_HORIZON_MONTHS * 30)
    hist   = result[result["date"] <= cutoff]
    fut    = result[result["date"] >  cutoff]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(hist["date"], hist["forecast"], color="#1565C0", lw=1.5, label="Historical fit")
    ax.plot(fut["date"],  fut["forecast"],  color="#F57C00", lw=2,   label="Forecast")
    ax.fill_between(fut["date"], fut["forecast_lower"], fut["forecast_upper"],
                    alpha=0.2, color="#F57C00", label="90% CI")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    ax.set_title("Olist Revenue Forecast (Prophet) — BRL", fontsize=14)
    ax.set_xlabel("Date"); ax.set_ylabel("Revenue (R$)")
    ax.legend(); ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        logger.info(f"Plot → {save_path}")
    else:
        plt.show()
    plt.close()


if __name__ == "__main__":
    daily = pd.read_csv(DATA_PROCESSED / "daily_revenue.csv")
    result, monthly = run_prophet_forecast(daily)
    plot_forecast(result, save_path=DATA_PROCESSED / "forecast_plot.png")
