import pytest
from unittest.mock import patch, MagicMock
from equityiq.valuation import ValuationAnalyzer


MOCK_INFO = {
    "symbol": "TEST",
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
    "freeCashflow": 100_000_000,
    "sharesOutstanding": 1_000_000,
    "currentPrice": 150.0,
}

MOCK_FINANCIALS = {
    "income_statement": MagicMock(),
    "balance_sheet": MagicMock(),
    "cash_flow": MagicMock(),
}


@pytest.fixture
def valuation():
    with patch("equityiq.valuation.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.valuation.get_financials", return_value=MOCK_FINANCIALS):
        return ValuationAnalyzer("TEST")


def test_market_ratios(valuation):
    ratios = valuation.market_ratios()
    assert ratios["pe_ratio"] == 25.0
    assert ratios["pb_ratio"] == 3.5
    assert ratios["peg_ratio"] == 1.5


def test_dividend_analysis(valuation):
    ratios = valuation.dividend_analysis()
    assert ratios["dividend_yield"] == 0.02
    assert ratios["payout_ratio"] == 0.25


def test_intrinsic_value_returns_expected_keys(valuation):
    dcf = valuation.intrinsic_value()
    assert "intrinsic_value_per_share" in dcf
    assert "margin_of_safety_price" in dcf
    assert "current_price" in dcf
    assert "upside_downside_pct" in dcf
    assert "is_undervalued" in dcf


def test_intrinsic_value_current_price(valuation):
    dcf = valuation.intrinsic_value()
    assert dcf["current_price"] == 150.0


def test_intrinsic_value_margin_of_safety(valuation):
    dcf = valuation.intrinsic_value(margin_of_safety=0.25)
    expected = round(dcf["intrinsic_value_per_share"] * 0.75, 2)
    assert dcf["margin_of_safety_price"] == expected


def test_intrinsic_value_missing_data():
    incomplete_info = {"symbol": "TEST", "currentPrice": 100.0}
    with patch("equityiq.valuation.get_stock_info", return_value=incomplete_info), \
         patch("equityiq.valuation.get_financials", return_value={}):
        v = ValuationAnalyzer("TEST")
        result = v.intrinsic_value()
        assert "error" in result


def test_summary_returns_dataframe(valuation):
    import pandas as pd
    df = valuation.summary()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0