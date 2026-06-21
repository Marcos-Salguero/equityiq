import yfinance as yf
import pandas as pd
from typing import Optional


def get_stock_info(ticker: str) -> dict:
    """
    Returns general information and fundamentals of a stock.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'MSFT')

    Returns:
        Dictionary with company info and key metrics
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info or "symbol" not in info:
        raise ValueError(
            f"Could not retrieve data for ticker '{ticker}'. "
            f"Please check the symbol is correct."
        )
    return info


def get_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d"
) -> pd.DataFrame:
    """
    Returns historical price data for a stock.

    Args:
        ticker: Stock ticker symbol
        period: Time period ('1mo', '3mo', '6mo', '1y', '2y', '5y')
        interval: Data interval ('1d', '1wk', '1mo')

    Returns:
        DataFrame with OHLCV data
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No price history found for ticker '{ticker}'.")

    df.index = pd.to_datetime(df.index)
    return df


def get_income_statement(ticker: str, annual: bool = True) -> pd.DataFrame:
    """
    Returns a cleaned annual income statement with standardized field names.

    Fields returned (in millions):
        - revenue, gross_profit, ebit, ebitda, net_income,
          interest_expense, interest_income, tax_expense,
          da (depreciation & amortization), eps_diluted, shares_diluted

    Args:
        ticker: Stock ticker symbol
        annual: If True returns annual data, else quarterly

    Returns:
        DataFrame with years as columns and metrics as rows
    """
    stock = yf.Ticker(ticker)
    is_raw = stock.financials if annual else stock.quarterly_financials
    cf_raw = stock.cashflow if annual else stock.quarterly_cashflow

    if is_raw is None or is_raw.empty:
        raise ValueError(f"No income statement data available for '{ticker}'.")

    def safe_row(df, *keys):
        for k in keys:
            if k in df.index:
                return df.loc[k]
        return pd.Series(dtype=float)

    revenue = safe_row(is_raw, "Total Revenue")
    gross_profit = safe_row(is_raw, "Gross Profit")
    ebit = safe_row(is_raw, "EBIT", "Operating Income")
    net_income = safe_row(is_raw, "Net Income")
    interest_expense = safe_row(is_raw, "Interest Expense")
    interest_income = safe_row(
        is_raw, "Interest Income", "Interest And Investment Income"
    )
    tax_expense = safe_row(is_raw, "Tax Provision", "Income Tax Expense")
    da = safe_row(
        cf_raw,
        "Depreciation And Amortization",
        "Depreciation Amortization Depletion",
    )
    eps_diluted = safe_row(is_raw, "Diluted EPS")
    shares_diluted = safe_row(is_raw, "Diluted Average Shares")

    ebitda = ebit + da.reindex(ebit.index, fill_value=0)

    result = pd.DataFrame({
        "revenue": revenue,
        "gross_profit": gross_profit,
        "ebit": ebit,
        "ebitda": ebitda,
        "da": da,
        "net_income": net_income,
        "interest_expense": interest_expense,
        "interest_income": interest_income,
        "tax_expense": tax_expense,
        "eps_diluted": eps_diluted,
        "shares_diluted": shares_diluted,
    }).T

    result.columns = [str(c.year) for c in result.columns]
    result = result.sort_index(axis=1)
    result = result / 1e6  # Convert to millions
    result.loc["eps_diluted"] = result.loc["eps_diluted"] * 1e6  # EPS stays as-is
    result.loc["shares_diluted"] = (
        result.loc["shares_diluted"] * 1e6
    )  # shares back to units

    return result


def get_balance_sheet(ticker: str, annual: bool = True) -> pd.DataFrame:
    """
    Returns a cleaned annual balance sheet with standardized field names.

    Fields returned (in millions):
        - cash, marketable_securities, accounts_receivable, inventories,
          total_current_assets, total_assets, accounts_payable,
          short_term_debt, long_term_debt, operating_lease_current,
          operating_lease_non_current, total_equity, unearned_revenue

    Args:
        ticker: Stock ticker symbol
        annual: If True returns annual data, else quarterly

    Returns:
        DataFrame with years as columns and metrics as rows
    """
    stock = yf.Ticker(ticker)
    bs_raw = stock.balance_sheet if annual else stock.quarterly_balance_sheet

    if bs_raw is None or bs_raw.empty:
        raise ValueError(f"No balance sheet data available for '{ticker}'.")

    def safe_row(df, *keys):
        for k in keys:
            if k in df.index:
                return df.loc[k]
        return pd.Series(dtype=float)

    result = pd.DataFrame({
        "cash": safe_row(bs_raw, "Cash And Cash Equivalents"),
        "marketable_securities": safe_row(
            bs_raw, "Available For Sale Securities",
            "Other Short Term Investments"
        ),
        "accounts_receivable": safe_row(
            bs_raw, "Accounts Receivable", "Net Receivables"
        ),
        "inventories": safe_row(bs_raw, "Inventory"),
        "total_current_assets": safe_row(bs_raw, "Current Assets"),
        "total_assets": safe_row(bs_raw, "Total Assets"),
        "accounts_payable": safe_row(bs_raw, "Accounts Payable"),
        "unearned_revenue": safe_row(
            bs_raw, "Deferred Revenue", "Contract Liabilities"
        ),
        "short_term_debt": safe_row(
            bs_raw, "Current Debt", "Short Term Debt And Current Portion Of Long Term Debt"
        ),
        "long_term_debt": safe_row(bs_raw, "Long Term Debt"),
        "operating_lease_current": safe_row(
            bs_raw, "Current Deferred Liabilities", "Finance Lease Liability Current"
        ),
        "operating_lease_non_current": safe_row(
            bs_raw, "Non Current Deferred Liabilities",
            "Finance Lease Liability Non Current"
        ),
        "total_equity": safe_row(
            bs_raw, "Stockholders Equity", "Common Stock Equity"
        ),
    }).T

    result.columns = [str(c.year) for c in result.columns]
    result = result.sort_index(axis=1)
    result = result / 1e6
    return result


def get_cash_flow(ticker: str, annual: bool = True) -> pd.DataFrame:
    """
    Returns a cleaned annual cash flow statement with standardized field names.

    Fields returned (in millions):
        - cfo (cash from operations), capex, capex_maintenance,
          capex_expansion, acquisitions, repurchases, dividends,
          net_change_in_cash, stock_based_compensation

    Args:
        ticker: Stock ticker symbol
        annual: If True returns annual data, else quarterly

    Returns:
        DataFrame with years as columns and metrics as rows
    """
    stock = yf.Ticker(ticker)
    cf_raw = stock.cashflow if annual else stock.quarterly_cashflow

    if cf_raw is None or cf_raw.empty:
        raise ValueError(f"No cash flow data available for '{ticker}'.")

    def safe_row(df, *keys):
        for k in keys:
            if k in df.index:
                return df.loc[k]
        return pd.Series(dtype=float)

    da = safe_row(
        cf_raw,
        "Depreciation And Amortization",
        "Depreciation Amortization Depletion",
    )
    capex = safe_row(cf_raw, "Capital Expenditure")
    capex_maintenance = -da.abs()  # Use D&A as proxy for maintenance capex
    capex_expansion = capex - capex_maintenance

    result = pd.DataFrame({
        "cfo": safe_row(cf_raw, "Operating Cash Flow"),
        "capex": capex,
        "capex_maintenance": capex_maintenance,
        "capex_expansion": capex_expansion,
        "da": da,
        "acquisitions": safe_row(cf_raw, "Acquisitions Net"),
        "repurchases": safe_row(
            cf_raw, "Repurchase Of Capital Stock", "Common Stock Repurchased"
        ),
        "dividends": safe_row(
            cf_raw, "Common Stock Dividend Paid", "Payment Of Dividends"
        ),
        "stock_based_compensation": safe_row(cf_raw, "Stock Based Compensation"),
        "net_change_in_cash": safe_row(cf_raw, "Changes In Cash"),
    }).T

    result.columns = [str(c.year) for c in result.columns]
    result = result.sort_index(axis=1)
    result = result / 1e6
    return result


def get_financials(ticker: str) -> dict:
    """
    Returns the main financial statements of a company (legacy format).

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with income statement, balance sheet and cash flow
    """
    stock = yf.Ticker(ticker)
    return {
        "income_statement": stock.financials,
        "balance_sheet": stock.balance_sheet,
        "cash_flow": stock.cashflow,
    }


def get_full_data(ticker: str) -> dict:
    """
    Returns all available data for a stock in a single call.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with info, price history and all financial statements
    """
    return {
        "info": get_stock_info(ticker),
        "price_history": get_price_history(ticker),
        "income_statement": get_income_statement(ticker),
        "balance_sheet": get_balance_sheet(ticker),
        "cash_flow": get_cash_flow(ticker),
    }