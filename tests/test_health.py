import pytest
from unittest.mock import patch, MagicMock
from equityiq.health import HealthAnalyzer


MOCK_INFO = {
    "currentRatio": 1.5,
    "quickRatio": 1.2,
    "debtToEquity": 50.0,
    "interestCoverage": 10.0,
    "totalDebt": 1000000,
    "returnOnEquity": 0.30,
    "returnOnAssets": 0.15,
    "grossMargins": 0.45,
    "operatingMargins": 0.25,
    "profitMargins": 0.20,
    "revenueGrowth": 0.10,
    "earningsGrowth": 0.15,
    "earningsQuarterlyGrowth": 0.12,
    "symbol": "TEST",
}

MOCK_FINANCIALS = {
    "income_statement": MagicMock(),
    "balance_sheet": MagicMock(),
    "cash_flow": MagicMock(),
}


@pytest.fixture
def health():
    with patch("equityiq.health.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.health.get_financials", return_value=MOCK_FINANCIALS):
        return HealthAnalyzer("TEST")


def test_liquidity_ratios(health):
    ratios = health.liquidity_ratios()
    assert ratios["current_ratio"] == 1.5
    assert ratios["quick_ratio"] == 1.2


def test_debt_ratios(health):
    ratios = health.debt_ratios()
    assert ratios["debt_to_equity"] == 50.0
    assert ratios["total_debt"] == 1000000


def test_profitability_ratios(health):
    ratios = health.profitability_ratios()
    assert ratios["roe"] == 0.30
    assert ratios["net_margin"] == 0.20


def test_growth_ratios(health):
    ratios = health.growth_ratios()
    assert ratios["revenue_growth"] == 0.10
    assert ratios["earnings_growth"] == 0.15


def test_summary_returns_dataframe(health):
    import pandas as pd
    df = health.summary()
    assert isinstance(df, pd.DataFrame)
    assert "value" in df.columns
    assert len(df) > 0


def test_summary_contains_all_metrics(health):
    df = health.summary()
    assert "current_ratio" in df.index
    assert "roe" in df.index
    assert "net_margin" in df.index
    assert "revenue_growth" in df.index