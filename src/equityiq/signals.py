import pandas as pd
import numpy as np
from equityiq.data import get_stock_info, get_price_history, get_financials
from equityiq.health import HealthAnalyzer
from equityiq.valuation import ValuationAnalyzer


class SignalAnalyzer:
    """
    Generates quantitative buy/hold/sell signals based on financial
    health, valuation metrics and price momentum.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.info = get_stock_info(ticker)
        self.price_history = get_price_history(ticker, period="1y")
        self.health = HealthAnalyzer(ticker)
        self.valuation = ValuationAnalyzer(ticker)

    def momentum_signals(self) -> dict:
        """
        Price-based momentum indicators.
        """
        df = self.price_history
        close = df["Close"]

        ma_50 = close.rolling(window=50).mean().iloc[-1]
        ma_200 = close.rolling(window=200).mean().iloc[-1]
        current_price = close.iloc[-1]

        # RSI calculation
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # 52-week high/low
        high_52w = close.max()
        low_52w = close.min()
        pct_from_high = ((current_price - high_52w) / high_52w) * 100
        pct_from_low = ((current_price - low_52w) / low_52w) * 100

        return {
            "current_price": round(float(current_price), 2),
            "ma_50": round(float(ma_50), 2),
            "ma_200": round(float(ma_200), 2),
            "above_ma_50": bool(current_price > ma_50),
            "above_ma_200": bool(current_price > ma_200),
            "golden_cross": bool(ma_50 > ma_200),
            "rsi_14": round(float(rsi), 2),
            "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            "pct_from_52w_high": round(float(pct_from_high), 2),
            "pct_from_52w_low": round(float(pct_from_low), 2),
        }

    def quality_signals(self) -> dict:
        """
        Signals based on financial quality and consistency.
        """
        info = self.info
        profitability = self.health.profitability_ratios()
        growth = self.health.growth_ratios()

        fcf = info.get("freeCashflow", 0)
        net_income = info.get("netIncomeToCommon", 1)
        fcf_quality = fcf / net_income if net_income else None

        return {
            "fcf_quality_ratio": round(fcf_quality, 2) if fcf_quality else None,
            "fcf_quality_signal": (
                "high" if fcf_quality and fcf_quality > 0.8
                else "medium" if fcf_quality and fcf_quality > 0.5
                else "low"
            ),
            "revenue_growing": (
                growth.get("revenue_growth") is not None
                and growth.get("revenue_growth") > 0
            ),
            "earnings_growing": (
                growth.get("earnings_growth") is not None
                and growth.get("earnings_growth") > 0
            ),
            "healthy_margins": (
                profitability.get("net_margin") is not None
                and profitability.get("net_margin") > 0.10
            ),
        }

    def valuation_signals(self) -> dict:
        """
        Signals based on whether the stock looks cheap or expensive.
        """
        ratios = self.valuation.market_ratios()
        pe = ratios.get("pe_ratio")
        pb = ratios.get("pb_ratio")
        peg = ratios.get("peg_ratio")

        return {
            "pe_ratio": pe,
            "pe_signal": (
                "cheap" if pe and pe < 15
                else "fair" if pe and pe < 25
                else "expensive" if pe
                else "unavailable"
            ),
            "pb_signal": (
                "cheap" if pb and pb < 1.5
                else "fair" if pb and pb < 3
                else "expensive" if pb
                else "unavailable"
            ),
            "peg_signal": (
                "undervalued" if peg and peg < 1
                else "fair" if peg and peg < 2
                else "overvalued" if peg
                else "unavailable"
            ),
        }

    def overall_score(self) -> dict:
        """
        Aggregates all signals into a final score and recommendation.

        Scoring:
            - Each positive signal adds 1 point
            - Score is normalized to 0-100
            - 0-40: Sell | 40-60: Hold | 60-100: Buy
        """
        momentum = self.momentum_signals()
        quality = self.quality_signals()
        valuation = self.valuation_signals()

        score = 0
        max_score = 10

        # Momentum signals (4 points)
        if momentum.get("above_ma_50"): score += 1
        if momentum.get("above_ma_200"): score += 1
        if momentum.get("golden_cross"): score += 1
        rsi = momentum.get("rsi_14", 50)
        if 40 < rsi < 70: score += 1

        # Quality signals (4 points)
        if quality.get("fcf_quality_signal") == "high": score += 1
        if quality.get("revenue_growing"): score += 1
        if quality.get("earnings_growing"): score += 1
        if quality.get("healthy_margins"): score += 1

        # Valuation signals (2 points)
        if valuation.get("pe_signal") in ["cheap", "fair"]: score += 1
        if valuation.get("peg_signal") in ["undervalued", "fair"]: score += 1

        normalized = round((score / max_score) * 100)

        recommendation = (
            "BUY" if normalized >= 60
            else "HOLD" if normalized >= 40
            else "SELL"
        )

        return {
            "ticker": self.ticker,
            "score": normalized,
            "recommendation": recommendation,
            "momentum_score": sum([
                momentum.get("above_ma_50", False),
                momentum.get("above_ma_200", False),
                momentum.get("golden_cross", False),
                40 < rsi < 70,
            ]),
            "quality_score": sum([
                quality.get("fcf_quality_signal") == "high",
                quality.get("revenue_growing", False),
                quality.get("earnings_growing", False),
                quality.get("healthy_margins", False),
            ]),
            "valuation_score": sum([
                valuation.get("pe_signal") in ["cheap", "fair"],
                valuation.get("peg_signal") in ["undervalued", "fair"],
            ]),
        }