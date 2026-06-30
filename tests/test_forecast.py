"""
tests/test_forecast.py – Tests for ARIMA forecasting on Olist-shaped data.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from forecasting.arima_forecast import aggregate_to_monthly, run_arima_forecast


@pytest.fixture
def daily_revenue():
    """24 months of synthetic daily revenue (min required for seasonal ARIMA)."""
    dates = pd.date_range("2016-10-01", "2018-09-30", freq="D")
    np.random.seed(42)
    base = np.random.normal(26_000, 4_000, len(dates))
    season = 8_000 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    trend  = np.arange(len(dates)) * 10
    revenue = np.clip(base + season + trend, 500, None).round(2)
    return pd.DataFrame({"ds": dates, "revenue": revenue})


class TestAggregateMonthly:
    def test_returns_series(self, daily_revenue):
        result = aggregate_to_monthly(daily_revenue)
        assert isinstance(result, pd.Series)

    def test_24_months(self, daily_revenue):
        result = aggregate_to_monthly(daily_revenue)
        assert len(result) == 24

    def test_no_nulls(self, daily_revenue):
        result = aggregate_to_monthly(daily_revenue)
        assert result.isna().sum() == 0

    def test_positive_values(self, daily_revenue):
        result = aggregate_to_monthly(daily_revenue)
        assert (result > 0).all()


class TestArimaForecast:
    def test_returns_dataframe(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=6)
        assert isinstance(result, pd.DataFrame)

    def test_correct_horizon(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=6)
        assert len(result) == 6

    def test_non_negative_forecast(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=6)
        assert (result["forecast"] >= 0).all()

    def test_required_columns(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=3)
        for col in ["year_month", "forecast", "forecast_lower", "forecast_upper", "method"]:
            assert col in result.columns

    def test_lower_leq_forecast_leq_upper(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=3)
        assert (result["forecast_lower"] <= result["forecast"]).all()
        assert (result["forecast"] <= result["forecast_upper"]).all()

    def test_year_month_format(self, daily_revenue, tmp_path, monkeypatch):
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        result = run_arima_forecast(daily_revenue, horizon=3)
        import re
        pattern = re.compile(r"^\d{4}-\d{2}$")
        assert all(pattern.match(ym) for ym in result["year_month"])

    def test_short_series_fallback(self, tmp_path, monkeypatch):
        """Less than 24 months should fall back to non-seasonal ARIMA without error."""
        import forecasting.arima_forecast as af
        monkeypatch.setattr(af, "DATA_PROCESSED", tmp_path)
        dates = pd.date_range("2017-01-01", "2017-12-31", freq="D")
        short = pd.DataFrame({"ds": dates, "revenue": np.random.uniform(10000, 30000, len(dates))})
        result = run_arima_forecast(short, horizon=3)
        assert len(result) == 3
