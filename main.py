"""
main.py – Single-command runner for the Olist e-commerce analytics pipeline.

Usage
─────
  python main.py                        # ETL + ARIMA forecast + churn
  python main.py --mode etl             # ETL only
  python main.py --mode forecast        # Prophet forecast (needs processed data)
  python main.py --mode forecast --method arima
  python main.py --mode churn           # Churn model only
"""
import argparse
import sys
from loguru import logger
from pathlib import Path

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    level="INFO",
    colorize=True,
)
logger.add("pipeline.log", rotation="10 MB", retention="14 days", level="DEBUG")


def parse_args():
    p = argparse.ArgumentParser(description="Olist Analytics Pipeline")
    p.add_argument("--mode",   choices=["full","etl","forecast","churn"], default="full")
    p.add_argument("--method", choices=["prophet","arima"],               default="arima",
                   help="Forecasting method (default: arima — Prophet needs extra install)")
    return p.parse_args()


def run_etl():
    from etl.pipeline import run_pipeline
    return run_pipeline()


def run_forecast(method: str):
    import pandas as pd
    from config import DATA_PROCESSED

    path = DATA_PROCESSED / "daily_revenue.csv"
    if not path.exists():
        logger.error("daily_revenue.csv not found — run --mode etl first")
        sys.exit(1)

    daily = pd.read_csv(path)

    if method == "prophet":
        try:
            from forecasting.prophet_forecast import run_prophet_forecast, plot_forecast
            result, monthly = run_prophet_forecast(daily)
            plot_forecast(result, save_path=DATA_PROCESSED / "forecast_plot.png")
            logger.success("Prophet forecast complete")
        except ImportError:
            logger.warning("Prophet not installed — falling back to ARIMA")
            logger.warning("To use Prophet:  pip install prophet")
            from forecasting.arima_forecast import run_arima_forecast
            run_arima_forecast(daily)
    else:
        from forecasting.arima_forecast import run_arima_forecast
        run_arima_forecast(daily)


def run_churn():
    from forecasting.churn_model import run_churn_pipeline
    run_churn_pipeline()


def main():
    args = parse_args()

    if args.mode in ("full", "etl"):
        run_etl()

    if args.mode in ("full", "forecast"):
        run_forecast(args.method)

    if args.mode in ("full", "churn"):
        run_churn()

    logger.success("=" * 55)
    logger.success("  Pipeline finished!  Power BI-ready files:")
    logger.success("  data/processed/")
    logger.success("  → fact_orders.csv, dim_customer.csv, dim_product.csv")
    logger.success("  → daily_revenue.csv, forecast_arima.csv")
    logger.success("  → customer_features.csv, churn_predictions.csv")
    logger.success("  → product_performance.csv, state_revenue.csv")
    logger.success("=" * 55)
    logger.info("Next step: see powerbi/dashboard_guide.md")


if __name__ == "__main__":
    main()
