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
        raise ValueError(f"Could not retrieve data for ticker '{ticker}'. "
                         f"Please check the symbol is correct.")
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


def get_financials(ticker: str) -> dict:
    """
    Returns the main financial statements of a company.

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
        Dictionary with info, price history and financial statements
    """
    return {
        "info": get_stock_info(ticker),
        "price_history": get_price_history(ticker),
        "financials": get_financials(ticker),
    }