import pandas as pd
from equityiq.data import get_stock_info, get_financials


class HealthAnalyzer:
    """
    Analyzes the financial health of a company using key ratios
    derived from its financial statements.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.info = get_stock_info(ticker)
        self.financials = get_financials(ticker)

    def liquidity_ratios(self) -> dict:
        """
        Liquidity ratios: ability to meet short-term obligations.
        """
        info = self.info
        return {
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
        }

    def debt_ratios(self) -> dict:
        """
        Debt and solvency ratios: financial leverage and risk.
        """
        info = self.info
        return {
            "debt_to_equity": info.get("debtToEquity"),
            "interest_coverage": info.get("interestCoverage"),
            "total_debt": info.get("totalDebt"),
        }

    def profitability_ratios(self) -> dict:
        """
        Profitability ratios: how efficiently the company generates profit.
        """
        info = self.info
        return {
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "net_margin": info.get("profitMargins"),
        }

    def growth_ratios(self) -> dict:
        """
        Growth metrics: revenue and earnings trends.
        """
        info = self.info
        return {
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
        }

    def summary(self) -> pd.DataFrame:
        """
        Returns a single DataFrame with all health metrics.
        """
        all_metrics = {
            **self.liquidity_ratios(),
            **self.debt_ratios(),
            **self.profitability_ratios(),
            **self.growth_ratios(),
        }
        df = pd.DataFrame.from_dict(
            all_metrics, orient="index", columns=["value"]
        )
        df.index.name = "metric"
        return df