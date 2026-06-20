import pandas as pd
from equityiq.data import get_stock_info, get_financials


class ValuationAnalyzer:
    """
    Analyzes the valuation of a company using market and
    fundamental-based metrics.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.info = get_stock_info(ticker)
        self.financials = get_financials(ticker)

    def market_ratios(self) -> dict:
        """
        Standard market valuation multiples.
        """
        info = self.info
        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "peg_ratio": info.get("pegRatio"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            "ev_to_revenue": info.get("enterpriseToRevenue"),
        }

    def intrinsic_value(self, growth_rate: float = 0.10,
                        discount_rate: float = 0.10,
                        terminal_growth: float = 0.03,
                        years: int = 10,
                        margin_of_safety: float = 0.25) -> dict:
        """
        Simplified DCF (Discounted Cash Flow) valuation.

        Args:
            growth_rate: Expected annual FCF growth rate (default 10%)
            discount_rate: Required rate of return / WACC (default 10%)
            terminal_growth: Perpetual growth rate after projection (default 3%)
            years: Number of years to project (default 10)
            margin_of_safety: Discount applied to intrinsic value to get the
                      target buy price (default 25%)

        Returns:
            Dictionary with DCF result and upside/downside vs current price
        """
        info = self.info
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")
        current_price = info.get("currentPrice")

        if not all([fcf, shares, current_price]):
            return {"error": "Insufficient data to compute DCF valuation."}

        # Project free cash flows
        projected_fcfs = []
        for year in range(1, years + 1):
            projected_fcf = fcf * ((1 + growth_rate) ** year)
            discounted = projected_fcf / ((1 + discount_rate) ** year)
            projected_fcfs.append(discounted)

        # Terminal value
        terminal_value = (projected_fcfs[-1] * (1 + terminal_growth) /
                          (discount_rate - terminal_growth))
        terminal_value_discounted = terminal_value / ((1 + discount_rate) ** years)

        # Intrinsic value per share
        total_value = sum(projected_fcfs) + terminal_value_discounted
        intrinsic_per_share = total_value / shares
        upside = ((intrinsic_per_share - current_price) / current_price) * 100

        margin_of_safety_price = intrinsic_per_share * (1 - margin_of_safety)

        return {
            "intrinsic_value_per_share": round(intrinsic_per_share, 2),
            "margin_of_safety_price": round(margin_of_safety_price, 2),
            "current_price": round(current_price, 2),
            "upside_downside_pct": round(upside, 2),
            "is_undervalued": intrinsic_per_share > current_price,
        }

    def dividend_analysis(self) -> dict:
        """
        Dividend-related metrics for income investors.
        """
        info = self.info
        return {
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "five_year_avg_dividend_yield": info.get("fiveYearAvgDividendYield"),
        }

    def summary(self) -> pd.DataFrame:
        """
        Returns a single DataFrame with all valuation metrics.
        Excludes DCF as it has its own method with configurable parameters.
        """
        all_metrics = {
            **self.market_ratios(),
            **self.dividend_analysis(),
        }
        df = pd.DataFrame.from_dict(
            all_metrics, orient="index", columns=["value"]
        )
        df.index.name = "metric"
        return df