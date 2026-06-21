import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from equityiq.signals import SignalAnalyzer


MOCK_INFO = {
    "symbol": "TEST",
    "currentPrice": 150.0,
    "freeCashflow": 100_000_000,
    "netIncomeToCommon": 80_000_000,
    "revenueGrowth": 0.10,
    "earningsGrowth": 0.12,
    "profitMargins": 0.20,
    "returnOnEquity": 0.30,
    "returnOnAssets": 0.15,
    "grossMargins": 0.45,
    "operatingMargins": 0.25,
    "trailingPE": 20.0,
    "priceToBook": 2.5,
    "pegRatio": 1.2,
}

dates = pd.date_range(end="2026-06-21", periods=252, freq="B")
prices = pd.Series(np.linspace(100, 150, 252), index=dates)
MOCK_PRICE_HISTORY = pd.DataFrame({
    "Close": prices,
    "Open": prices * 0.99,
    "High": prices * 1.01,
    "Low": prices * 0.98,
    "Volume": np.random.randint(1_000_000, 10_000_000, 252),
})

MOCK_FINANCIALS = {
    "income_statement": MagicMock(),
    "balance_sheet": MagicMock(),
    "cash_flow": MagicMock(),
}


@pytest.fixture
def signals():
    with patch("equityiq.signals.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.signals.get_price_history", return_value=MOCK_PRICE_HISTORY), \
         patch("equityiq.signals.get_financials", return_value=MOCK_FINANCIALS), \
         patch("equityiq.health.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.health.get_financials", return_value=MOCK_FINANCIALS), \
         patch("equityiq.valuation.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.valuation.get_financials", return_value=MOCK_FINANCIALS):
        return SignalAnalyzer("TEST")


def test_momentum_signals_keys(signals):
    momentum = signals.momentum_signals()
    assert "current_price" in momentum
    assert "ma_50" in momentum
    assert "ma_200" in momentum
    assert "rsi_14" in momentum
    assert "rsi_signal" in momentum


def test_rsi_signal_values(signals):
    momentum = signals.momentum_signals()
    assert momentum["rsi_signal"] in ["overbought", "oversold", "neutral"]


def test_quality_signals(signals):
    quality = signals.quality_signals()
    assert "fcf_quality_ratio" in quality
    assert quality["fcf_quality_signal"] in ["high", "medium", "low"]
    assert isinstance(quality["revenue_growing"], bool)
    assert isinstance(quality["earnings_growing"], bool)


def test_overall_score_range(signals):
    score = signals.overall_score()
    assert 0 <= score["score"] <= 100


def test_overall_score_recommendation(signals):
    score = signals.overall_score()
    assert score["recommendation"] in ["BUY", "HOLD", "SELL"]


def test_overall_score_subscores(signals):
    score = signals.overall_score()
    assert 0 <= score["momentum_score"] <= 4
    assert 0 <= score["quality_score"] <= 4
    assert 0 <= score["valuation_score"] <= 2