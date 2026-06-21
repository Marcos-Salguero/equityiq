import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from equityiq.report import Report


MOCK_INFO = {
    "symbol": "TEST",
    "longName": "Test Company Inc.",
    "sector": "Technology",
    "industry": "Software",
    "country": "United States",
    "marketCap": 1_000_000_000,
    "currentPrice": 150.0,
    "freeCashflow": 100_000_000,
    "netIncomeToCommon": 80_000_000,
    "sharesOutstanding": 1_000_000,
    "currentRatio": 1.5,
    "quickRatio": 1.2,
    "debtToEquity": 50.0,
    "interestCoverage": 10.0,
    "totalDebt": 1_000_000,
    "returnOnEquity": 0.30,
    "returnOnAssets": 0.15,
    "grossMargins": 0.45,
    "operatingMargins": 0.25,
    "profitMargins": 0.20,
    "revenueGrowth": 0.10,
    "earningsGrowth": 0.15,
    "earningsQuarterlyGrowth": 0.12,
    "trailingPE": 25.0,
    "forwardPE": 20.0,
    "priceToBook": 3.5,
    "priceToSalesTrailing12Months": 5.0,
    "pegRatio": 1.5,
    "enterpriseToEbitda": 15.0,
    "enterpriseToRevenue": 4.0,
    "dividendYield": 0.02,
    "dividendRate": 1.0,
    "payoutRatio": 0.25,
    "fiveYearAvgDividendYield": 0.018,
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
def report():
    with patch("equityiq.health.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.health.get_financials", return_value=MOCK_FINANCIALS), \
         patch("equityiq.valuation.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.valuation.get_financials", return_value=MOCK_FINANCIALS), \
         patch("equityiq.signals.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.signals.get_price_history", return_value=MOCK_PRICE_HISTORY), \
         patch("equityiq.signals.get_financials", return_value=MOCK_FINANCIALS):
        return Report("TEST")


def test_summary_returns_string(report):
    result = report.summary()
    assert isinstance(result, str)
    assert "EQUITYIQ REPORT" in result
    assert "TEST" in result


def test_summary_contains_sections(report):
    result = report.summary()
    assert "FINANCIAL HEALTH" in result
    assert "VALUATION" in result
    assert "SIGNALS" in result
    assert "RECOMMENDATION" in result


def test_to_dict_keys(report):
    d = report.to_dict()
    assert "ticker" in d
    assert "health" in d
    assert "valuation" in d
    assert "signals" in d
    assert "dcf" in d


def test_to_dict_ticker(report):
    d = report.to_dict()
    assert d["ticker"] == "TEST"


def test_to_dataframe_returns_dataframe(report):
    df = report.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert "section" in df.columns
    assert "metric" in df.columns
    assert "value" in df.columns


def test_to_dataframe_sections(report):
    df = report.to_dataframe()
    sections = df["section"].unique().tolist()
    assert "health" in sections
    assert "valuation" in sections
    assert "signals" in sections