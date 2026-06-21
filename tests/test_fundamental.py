import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from equityiq.fundamental import FundamentalAnalyzer


MOCK_INFO = {
    "symbol": "TEST",
    "longName": "Test Company Inc.",
    "currency": "USD",
    "currentPrice": 150.0,
}

MOCK_IS = pd.DataFrame({
    "2022": [100000, 80000, 40000, 48000, 8000, 30000, 5000, 2000, 1000, 6000, 10.0, 3000e6],
    "2023": [120000, 96000, 50000, 59000, 9000, 36000, 6000, 2500, 1200, 7000, 12.0, 2900e6],
    "2024": [150000, 120000, 65000, 76000, 11000, 45000, 7000, 3000, 1500, 8000, 15.0, 2800e6],
}, index=[
    "revenue", "gross_profit", "ebit", "ebitda", "da",
    "net_income", "tax_expense", "interest_income",
    "interest_expense", "gross_profit", "eps_diluted", "shares_diluted"
])

# Rebuild cleanly to avoid duplicate index
MOCK_IS = pd.DataFrame({
    "2022": {
        "revenue": 100000, "gross_profit": 80000, "ebit": 40000,
        "ebitda": 48000, "da": 8000, "net_income": 30000,
        "tax_expense": 6000, "interest_income": 2000,
        "interest_expense": 1000, "eps_diluted": 10.0,
        "shares_diluted": 3000e6,
    },
    "2023": {
        "revenue": 120000, "gross_profit": 96000, "ebit": 50000,
        "ebitda": 59000, "da": 9000, "net_income": 36000,
        "tax_expense": 7000, "interest_income": 2500,
        "interest_expense": 1200, "eps_diluted": 12.0,
        "shares_diluted": 2900e6,
    },
    "2024": {
        "revenue": 150000, "gross_profit": 120000, "ebit": 65000,
        "ebitda": 76000, "da": 11000, "net_income": 45000,
        "tax_expense": 8000, "interest_income": 3000,
        "interest_expense": 1500, "eps_diluted": 15.0,
        "shares_diluted": 2800e6,
    },
})

MOCK_BS = pd.DataFrame({
    "2022": {
        "cash": 10000, "marketable_securities": 5000,
        "accounts_receivable": 8000, "inventories": 0,
        "total_current_assets": 30000, "total_assets": 100000,
        "accounts_payable": 3000, "unearned_revenue": 0,
        "short_term_debt": 0, "long_term_debt": 5000,
        "operating_lease_current": 500, "operating_lease_non_current": 2000,
        "total_equity": 60000,
    },
    "2023": {
        "cash": 15000, "marketable_securities": 6000,
        "accounts_receivable": 10000, "inventories": 0,
        "total_current_assets": 40000, "total_assets": 130000,
        "accounts_payable": 4000, "unearned_revenue": 0,
        "short_term_debt": 0, "long_term_debt": 8000,
        "operating_lease_current": 600, "operating_lease_non_current": 2500,
        "total_equity": 75000,
    },
    "2024": {
        "cash": 20000, "marketable_securities": 7000,
        "accounts_receivable": 12000, "inventories": 0,
        "total_current_assets": 50000, "total_assets": 160000,
        "accounts_payable": 5000, "unearned_revenue": 0,
        "short_term_debt": 0, "long_term_debt": 10000,
        "operating_lease_current": 700, "operating_lease_non_current": 3000,
        "total_equity": 90000,
    },
})

MOCK_CF = pd.DataFrame({
    "2022": {
        "cfo": 35000, "capex": -10000, "capex_maintenance": -8000,
        "capex_expansion": -2000, "da": 8000, "acquisitions": 0,
        "repurchases": -5000, "dividends": 0,
        "stock_based_compensation": 3000, "net_change_in_cash": 2000,
    },
    "2023": {
        "cfo": 45000, "capex": -12000, "capex_maintenance": -9000,
        "capex_expansion": -3000, "da": 9000, "acquisitions": 0,
        "repurchases": -6000, "dividends": 0,
        "stock_based_compensation": 3500, "net_change_in_cash": 3000,
    },
    "2024": {
        "cfo": 58000, "capex": -15000, "capex_maintenance": -11000,
        "capex_expansion": -4000, "da": 11000, "acquisitions": 0,
        "repurchases": -8000, "dividends": -1000,
        "stock_based_compensation": 4000, "net_change_in_cash": 4000,
    },
})


@pytest.fixture
def fa():
    with patch("equityiq.fundamental.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.fundamental.get_income_statement", return_value=MOCK_IS), \
         patch("equityiq.fundamental.get_balance_sheet", return_value=MOCK_BS), \
         patch("equityiq.fundamental.get_cash_flow", return_value=MOCK_CF):
        return FundamentalAnalyzer("TEST")


def test_income_statement_returns_dataframe(fa):
    df = fa.income_statement()
    assert isinstance(df, pd.DataFrame)
    assert "Revenue" in df.index
    assert "EBIT" in df.index
    assert "Net Income" in df.index


def test_income_statement_raw_values(fa):
    df = fa.income_statement(formatted=False)
    assert df.loc["Revenue", "2024"] == 150000
    assert df.loc["EBIT", "2024"] == 65000


def test_income_statement_margins(fa):
    df = fa.income_statement(formatted=False)
    margin = df.loc["EBIT Margin %", "2024"]
    assert abs(margin - 65000 / 150000) < 1e-6


def test_is_cagr_returns_series(fa):
    cagr = fa.is_cagr()
    assert isinstance(cagr, pd.Series)
    assert "Revenue CAGR" in cagr.index


def test_working_capital(fa):
    wc = fa.working_capital()
    assert "Working Capital" in wc.index
    assert "Change in WC (CWC)" in wc.index


def test_free_cash_flow_returns_dataframe(fa):
    df = fa.free_cash_flow()
    assert isinstance(df, pd.DataFrame)
    assert "Free Cash Flow" in df.index
    assert "FCF Margin %" in df.index


def test_free_cash_flow_raw(fa):
    df = fa.free_cash_flow(formatted=False)
    assert df.loc["Free Cash Flow"].notna().any()


def test_fcf_efficiency(fa):
    df = fa.fcf_efficiency()
    assert "FCF Margin (FCF / Revenue)" in df.index
    assert "Median" in df.columns


def test_capital_allocation(fa):
    df = fa.capital_allocation()
    assert "Repurchases" in df.index
    assert "Median" in df.columns


def test_invested_capital(fa):
    df = fa.invested_capital()
    assert "ROIC" in df.index
    assert "ROE" in df.index
    assert "Invested Capital" in df.index


def test_roic_positive(fa):
    df = fa.invested_capital(formatted=False)
    roic = df.loc["ROIC"].dropna()
    assert (roic > 0).all()


def test_red_flags_structure(fa):
    flags = fa.red_flags()
    assert "as_pct_revenue" in flags
    assert "counters" in flags
    assert "Years with FCF < 0" in flags["counters"].index
    assert "Years with poor ROIC (<10%)" in flags["counters"].index


def test_no_empty_years(fa):
    """Ensures years with all-zero data are dropped."""
    assert "2021" not in fa.is_df.columns