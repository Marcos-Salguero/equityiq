import pandas as pd
from datetime import datetime
from equityiq.health import HealthAnalyzer
from equityiq.valuation import ValuationAnalyzer
from equityiq.signals import SignalAnalyzer


class Report:
    """
    Generates a comprehensive quantitative analysis report for a stock,
    aggregating health, valuation and signal metrics into a single output.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.health = HealthAnalyzer(ticker)
        self.valuation = ValuationAnalyzer(ticker)
        self.signals = SignalAnalyzer(ticker)
        self.info = self.health.info

    def _header(self) -> str:
        name = self.info.get("longName", self.ticker)
        sector = self.info.get("sector", "N/A")
        industry = self.info.get("industry", "N/A")
        country = self.info.get("country", "N/A")
        market_cap = self.info.get("marketCap", 0)
        market_cap_str = f"${market_cap / 1e9:.2f}B" if market_cap else "N/A"

        return (
            f"\n{'=' * 60}\n"
            f"  EQUITYIQ REPORT — {name} ({self.ticker})\n"
            f"{'=' * 60}\n"
            f"  Sector:      {sector}\n"
            f"  Industry:    {industry}\n"
            f"  Country:     {country}\n"
            f"  Market Cap:  {market_cap_str}\n"
            f"  Generated:   {self.generated_at}\n"
            f"{'=' * 60}\n"
        )

    def _health_section(self) -> str:
        liquidity = self.health.liquidity_ratios()
        debt = self.health.debt_ratios()
        profitability = self.health.profitability_ratios()
        growth = self.health.growth_ratios()

        def fmt(value, pct=False) -> str:
            if value is None:
                return "N/A"
            if pct:
                return f"{value * 100:.1f}%"
            return f"{value:.2f}"

        return (
            f"\n--- FINANCIAL HEALTH ---\n"
            f"  Liquidity\n"
            f"    Current Ratio:       {fmt(liquidity.get('current_ratio'))}\n"
            f"    Quick Ratio:         {fmt(liquidity.get('quick_ratio'))}\n"
            f"  Debt\n"
            f"    Debt to Equity:      {fmt(debt.get('debt_to_equity'))}\n"
            f"    Interest Coverage:   {fmt(debt.get('interest_coverage'))}\n"
            f"  Profitability\n"
            f"    ROE:                 {fmt(profitability.get('roe'), pct=True)}\n"
            f"    ROA:                 {fmt(profitability.get('roa'), pct=True)}\n"
            f"    Gross Margin:        {fmt(profitability.get('gross_margin'), pct=True)}\n"
            f"    Net Margin:          {fmt(profitability.get('net_margin'), pct=True)}\n"
            f"  Growth\n"
            f"    Revenue Growth:      {fmt(growth.get('revenue_growth'), pct=True)}\n"
            f"    Earnings Growth:     {fmt(growth.get('earnings_growth'), pct=True)}\n"
        )

    def _valuation_section(self) -> str:
        ratios = self.valuation.market_ratios()
        dcf = self.valuation.intrinsic_value()

        def fmt(value) -> str:
            if value is None:
                return "N/A"
            return f"{value:.2f}"

        dcf_value = dcf.get("intrinsic_value_per_share", "N/A")
        dcf_price = dcf.get("margin_of_safety_price", "N/A")
        upside = dcf.get("upside_downside_pct", "N/A")
        undervalued = dcf.get("is_undervalued", None)

        return (
            f"\n--- VALUATION ---\n"
            f"  Market Multiples\n"
            f"    P/E (trailing):      {fmt(ratios.get('pe_ratio'))}\n"
            f"    P/E (forward):       {fmt(ratios.get('forward_pe'))}\n"
            f"    P/B:                 {fmt(ratios.get('pb_ratio'))}\n"
            f"    P/S:                 {fmt(ratios.get('ps_ratio'))}\n"
            f"    PEG:                 {fmt(ratios.get('peg_ratio'))}\n"
            f"    EV/EBITDA:           {fmt(ratios.get('ev_to_ebitda'))}\n"
            f"  DCF Valuation (simplified)\n"
            f"    Intrinsic Value:     ${dcf_value}\n"
            f"    Safety Price (25%):  ${dcf_price}\n"
            f"    Upside/Downside:     {upside}%\n"
            f"    Undervalued:         {'Yes' if undervalued else 'No'}\n"
        )

    def _signals_section(self) -> str:
        momentum = self.signals.momentum_signals()
        quality = self.signals.quality_signals()
        valuation = self.signals.valuation_signals()

        return (
            f"\n--- SIGNALS ---\n"
            f"  Momentum\n"
            f"    Price:               ${momentum.get('current_price')}\n"
            f"    MA 50:               ${momentum.get('ma_50')}\n"
            f"    MA 200:              ${momentum.get('ma_200')}\n"
            f"    Above MA50:          {'Yes' if momentum.get('above_ma_50') else 'No'}\n"
            f"    Above MA200:         {'Yes' if momentum.get('above_ma_200') else 'No'}\n"
            f"    Golden Cross:        {'Yes' if momentum.get('golden_cross') else 'No'}\n"
            f"    RSI (14):            {momentum.get('rsi_14')} — {momentum.get('rsi_signal')}\n"
            f"    From 52w High:       {momentum.get('pct_from_52w_high')}%\n"
            f"    From 52w Low:        {momentum.get('pct_from_52w_low')}%\n"
            f"  Quality\n"
            f"    FCF Quality:         {quality.get('fcf_quality_signal')}\n"
            f"    Revenue Growing:     {'Yes' if quality.get('revenue_growing') else 'No'}\n"
            f"    Earnings Growing:    {'Yes' if quality.get('earnings_growing') else 'No'}\n"
            f"    Healthy Margins:     {'Yes' if quality.get('healthy_margins') else 'No'}\n"
            f"  Valuation Signals\n"
            f"    P/E Signal:          {valuation.get('pe_signal')}\n"
            f"    P/B Signal:          {valuation.get('pb_signal')}\n"
            f"    PEG Signal:          {valuation.get('peg_signal')}\n"
        )

    def _recommendation_section(self) -> str:
        score = self.signals.overall_score()
        normalized = score.get("score")
        recommendation = score.get("recommendation")
        emoji = "🟢" if recommendation == "BUY" else "🟡" if recommendation == "HOLD" else "🔴"

        return (
            f"\n{'=' * 60}\n"
            f"  {emoji}  RECOMMENDATION: {recommendation}  |  SCORE: {normalized}/100\n"
            f"{'=' * 60}\n"
            f"  Momentum Score:   {score.get('momentum_score')}/4\n"
            f"  Quality Score:    {score.get('quality_score')}/4\n"
            f"  Valuation Score:  {score.get('valuation_score')}/2\n"
            f"{'=' * 60}\n"
        )

    def summary(self) -> str:
        """
        Prints the full analysis report to the console.
        """
        report = (
            self._header()
            + self._health_section()
            + self._valuation_section()
            + self._signals_section()
            + self._recommendation_section()
        )
        return report

    def to_dict(self) -> dict:
        """
        Returns the full report as a dictionary for programmatic use.
        """
        return {
            "ticker": self.ticker,
            "generated_at": self.generated_at,
            "health": self.health.summary().to_dict()["value"],
            "valuation": self.valuation.summary().to_dict()["value"],
            "signals": self.signals.overall_score(),
            "dcf": self.valuation.intrinsic_value(),
        }

    def to_dataframe(self) -> pd.DataFrame:
        """
        Returns a flat DataFrame with all metrics for easy comparison
        across multiple stocks.
        """
        data = self.to_dict()
        rows = []

        for key, value in data["health"].items():
            rows.append({"section": "health", "metric": key, "value": value})
        for key, value in data["valuation"].items():
            rows.append({"section": "valuation", "metric": key, "value": value})
        for key, value in data["signals"].items():
            if key != "ticker":
                rows.append({"section": "signals", "metric": key, "value": value})

        return pd.DataFrame(rows)