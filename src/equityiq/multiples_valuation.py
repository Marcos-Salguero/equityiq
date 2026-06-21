import pandas as pd
import numpy as np
from equityiq.data import get_stock_info
from equityiq.fundamental import (
    FundamentalAnalyzer,
    _fmt_currency,
    _fmt_pct,
    _fmt_ratio,
    _get_currency_symbol,
    _apply_format,
)
from equityiq.projection import Projector


class MultiplesValuation:
    """
    Replicates the valuation sheet of the Excel model.

    Computes:
    - Historical and projected market multiples (PER, EV/FCF, EV/EBITDA, EV/EBIT)
    - Target price per year per multiple
    - Implied CAGR from current price to target
    - Margin of safety and upside potential
    - Buy price for a target annual return
    """

    def __init__(
        self,
        ticker: str,
        projector: Projector | None = None,
        per_target: float | None = None,
        ev_fcf_target: float | None = None,
        ev_ebitda_target: float | None = None,
        ev_ebit_target: float | None = None,
    ):
        """
        Args:
            ticker: Stock ticker symbol
            projector: Optional Projector instance. If None, uses defaults.
            per_target: Target P/E multiple. If None, uses historical median.
            ev_fcf_target: Target EV/FCF multiple. If None, uses historical median.
            ev_ebitda_target: Target EV/EBITDA multiple. If None, uses historical median.
            ev_ebit_target: Target EV/EBIT multiple. If None, uses historical median.
        """
        self.ticker = ticker.upper()
        self.info = get_stock_info(ticker)
        self.currency = _get_currency_symbol(self.info)
        self.fa = FundamentalAnalyzer(ticker)
        self.projector = projector or Projector(ticker)

        self._current_price = self.info.get("currentPrice", np.nan)
        self._shares = self.fa.is_df.loc["shares_diluted"].iloc[-1] / 1e6
        self._base_year = int(self.fa.is_df.columns[-1])

        # Compute historical multiples to derive medians
        self._hist_multiples = self._compute_historical_multiples()

        # Resolve target multiples
        self.per_target = per_target or self._median("PER")
        self.ev_fcf_target = ev_fcf_target or self._median("EV/FCF")
        self.ev_ebitda_target = ev_ebitda_target or self._median("EV/EBITDA")
        self.ev_ebit_target = ev_ebit_target or self._median("EV/EBIT")

    def _median(self, metric: str) -> float:
        series = self._hist_multiples.loc[metric].replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        return float(series.median())

    def _net_debt(self, year: str | None = None) -> float:
        """Returns net debt. If year is None uses latest historical."""
        bs_ = self.fa.bs_df
        if year is None:
            return float(
                bs_.loc["long_term_debt"].iloc[-1]
                + bs_.loc["short_term_debt"].iloc[-1]
                - bs_.loc["cash"].iloc[-1]
                - bs_.loc["marketable_securities"].iloc[-1]
            )
        # For projected years use last known net debt as approximation
        return self._net_debt()

    def _compute_historical_multiples(self) -> pd.DataFrame:
        """
        Computes PER, EV/FCF, EV/EBITDA, EV/EBIT for historical years.
        """
        is_ = self.fa.is_df
        fcf = self.fa._fcf_raw().loc["Free Cash Flow"]
        info = self.info

        market_cap = info.get("marketCap", np.nan) / 1e6
        net_debt = self._net_debt()
        ev = market_cap + net_debt

        # Historical EV approximation: use current EV as reference
        # (yfinance doesn't provide historical market cap easily)
        years = is_.columns.tolist()
        results = {}

        for year in years:
            ni = is_.loc["net_income", year]
            ebitda = is_.loc["ebitda", year]
            ebit = is_.loc["ebit", year]
            fcf_val = fcf.get(year, np.nan)

            results[year] = {
                "PER": market_cap / ni if ni > 0 else np.nan,
                "EV/FCF": ev / fcf_val if fcf_val and fcf_val > 0 else np.nan,
                "EV/EBITDA": ev / ebitda if ebitda > 0 else np.nan,
                "EV/EBIT": ev / ebit if ebit > 0 else np.nan,
            }

        return pd.DataFrame(results).T.T

    def historical_multiples(self, formatted: bool = True) -> pd.DataFrame:
        """
        Returns historical valuation multiples with median.
        """
        df = self._hist_multiples.copy()
        df["Median"] = df.replace(
            [np.inf, -np.inf], np.nan
        ).median(axis=1)

        if not formatted:
            return df

        return df.map(
            lambda v: _fmt_ratio(v) if not pd.isna(v) else "-"
        )

    def valuation_summary(self, formatted: bool = True) -> pd.DataFrame:
        """
        Returns market cap, net debt, EV and multiples for
        historical and projected years, like the Excel valuation sheet.
        """
        is_ = self.fa.is_df
        fcf_hist = self.fa._fcf_raw()
        proj_is = self.projector.income_statement(formatted=False)
        proj_fcf = self.projector.free_cash_flow(formatted=False)

        info = self.info
        market_cap = info.get("marketCap", np.nan) / 1e6
        net_debt_val = self._net_debt()
        ev = market_cap + net_debt_val
        latest_year = is_.columns[-1]

        hist_years = is_.columns.tolist()
        proj_years = self.projector._project_years()
        all_years = hist_years + proj_years

        results = {}
        for year in all_years:
            is_hist = year in hist_years
            is_latest = year == latest_year

            ni = (
                is_.loc["net_income", year] if is_hist
                else proj_is.loc["Net Income", year]
            )
            ebitda = (
                is_.loc["ebitda", year] if is_hist
                else proj_is.loc["EBITDA", year]
            )
            ebit = (
                is_.loc["ebit", year] if is_hist
                else proj_is.loc["EBIT", year]
            )
            fcf_val = (
                fcf_hist.loc["Free Cash Flow", year] if is_hist
                else proj_fcf.loc["Free Cash Flow", year]
            )

            results[year] = {
                "Net Debt / EBITDA": net_debt_val / ebitda if ebitda else np.nan,
                "PER": market_cap / ni if ni > 0 else np.nan,
                "EV/FCF": ev / fcf_val if fcf_val and fcf_val > 0 else np.nan,
                "EV/EBITDA": ev / ebitda if ebitda > 0 else np.nan,
                "EV/EBIT": ev / ebit if ebit > 0 else np.nan,
            }
        df = pd.DataFrame(results).T.T

        if not formatted:
            return df

        sym = self.currency
        fmt_map = {
            "Net Debt / EBITDA": _fmt_ratio,
            "PER": _fmt_ratio,
            "EV/FCF": _fmt_ratio,
            "EV/EBITDA": _fmt_ratio,
            "EV/EBIT": _fmt_ratio,
        }
        return _apply_format(df, fmt_map).fillna("-")

    def target_prices(self, formatted: bool = True) -> pd.DataFrame:
        """
        Computes target price per year per multiple, implied CAGR,
        margin of safety and upside potential.

        Logic mirrors the Excel valuation sheet exactly:
        - PER ex Cash: (Net Income * PER_target + Cash) / Shares
        - EV/FCF: (FCF * EV_FCF_target - Net Debt) / Shares
        - EV/EBITDA: (EBITDA * EV_EBITDA_target - Net Debt) / Shares
        - EV/EBIT: (EBIT * EV_EBIT_target - Net Debt) / Shares
        """
        sym = self.currency
        proj_is = self.projector.income_statement(formatted=False)
        proj_fcf = self.projector.free_cash_flow(formatted=False)
        proj_years = self.projector._project_years()

        net_debt = self._net_debt()
        cash = float(self.fa.bs_df.loc["cash"].iloc[-1]
                     + self.fa.bs_df.loc["marketable_securities"].iloc[-1])
        shares = self._shares
        current = self._current_price
        n_years = len(proj_years)

        results = {}
        for i, year in enumerate(proj_years):
            ni = proj_is.loc["Net Income", year]
            ebitda = proj_is.loc["EBITDA", year]
            ebit = proj_is.loc["EBIT", year]
            fcf = proj_fcf.loc["Free Cash Flow", year]
            yrs_ahead = i + 1

            per_price = (ni * self.per_target + cash) / shares
            ev_fcf_price = (fcf * self.ev_fcf_target - net_debt) / shares
            ev_ebitda_price = (ebitda * self.ev_ebitda_target - net_debt) / shares
            ev_ebit_price = (ebit * self.ev_ebit_target - net_debt) / shares
            avg_price = np.mean([per_price, ev_fcf_price, ev_ebitda_price, ev_ebit_price])

            def cagr(target):
                if current > 0 and target > 0:
                    return (target / current) ** (1 / yrs_ahead) - 1
                return np.nan

            results[year] = {
                "PER ex Cash": per_price,
                "EV/FCF": ev_fcf_price,
                "EV/EBITDA": ev_ebitda_price,
                "EV/EBIT": ev_ebit_price,
                "Average": avg_price,
                "---": "---",
                "CAGR PER ex Cash": cagr(per_price),
                "CAGR EV/FCF": cagr(ev_fcf_price),
                "CAGR EV/EBITDA": cagr(ev_ebitda_price),
                "CAGR EV/EBIT": cagr(ev_ebit_price),
                "CAGR Average": cagr(avg_price),
                "----": "----",
                "Margin of Safety (EV/FCF)": (
                    (ev_fcf_price - current) / ev_fcf_price
                    if ev_fcf_price > 0 else np.nan
                ),
                "Upside Potential (EV/FCF)": (
                    (ev_fcf_price - current) / current
                    if current > 0 else np.nan
                ),
            }

        df = pd.DataFrame(results).T.T

        if not formatted:
            return df

        price_rows = ["PER ex Cash", "EV/FCF", "EV/EBITDA", "EV/EBIT", "Average"]
        cagr_rows = [
            "CAGR PER ex Cash", "CAGR EV/FCF", "CAGR EV/EBITDA",
            "CAGR EV/EBIT", "CAGR Average",
        ]
        pct_rows = ["Margin of Safety (EV/FCF)", "Upside Potential (EV/FCF)"]

        fmt_map = {
            **{r: lambda v, s=sym: (
                f"{s}{v:,.0f}" if not pd.isna(v) and isinstance(v, float) else "-"
            ) for r in price_rows},
            **{r: _fmt_pct for r in cagr_rows},
            **{r: _fmt_pct for r in pct_rows},
        }
        return _apply_format(df, fmt_map).fillna("-")

    def buy_price_for_return(
        self, target_return: float = 0.15, reference_year: int = 1
    ) -> dict:
        """
        Computes the maximum price to pay today to achieve
        a target annualized return, based on EV/FCF target price.

        Args:
            target_return: Desired annual return (default 15%)
            reference_year: Which projected year to use as target (default 1)

        Returns:
            Dictionary with buy price, current price and difference
        """
        sym = self.currency
        proj_years = self.projector._project_years()
        target_prices_raw = self.target_prices(formatted=False)

        year = proj_years[reference_year - 1]
        target = float(target_prices_raw.loc["EV/FCF", year])
        years_ahead = reference_year
        buy_price = target / ((1 + target_return) ** years_ahead)
        diff_pct = (self._current_price - buy_price) / buy_price

        return {
            "Target Return": _fmt_pct(target_return),
            "Reference Year": year,
            "EV/FCF Target Price": f"{sym}{target:,.0f}",
            "Max Buy Price": f"{sym}{buy_price:,.2f}",
            "Current Price": f"{sym}{self._current_price:,.2f}",
            "Difference vs Current": _fmt_pct(diff_pct),
            "Verdict": (
                "BELOW target price — attractive entry"
                if self._current_price <= buy_price
                else "ABOVE target price — wait for better entry"
            ),
        }

    def target_multiples(self) -> pd.Series:
        """Returns the target multiples being used."""
        return pd.Series({
            "PER Target": _fmt_ratio(self.per_target),
            "EV/FCF Target": _fmt_ratio(self.ev_fcf_target),
            "EV/EBITDA Target": _fmt_ratio(self.ev_ebitda_target),
            "EV/EBIT Target": _fmt_ratio(self.ev_ebit_target),
        }, name="Target")

    def summary(self) -> None:
        """Prints the full valuation analysis to the console."""
        name = self.info.get("longName", self.ticker)
        currency = self.info.get("currency", "USD")
        sym = self.currency
        market_cap = self.info.get("marketCap", 0) / 1e6
        net_debt = self._net_debt()
        ev = market_cap + net_debt

        print(f"\n{'=' * 65}")
        print(f"  VALUATION — {name} ({self.ticker})")
        print(f"  Current Price:    {sym}{self._current_price:,.2f}")
        print(f"  Market Cap:       {_fmt_currency(market_cap, sym)}")
        print(f"  Net Debt:         {_fmt_currency(net_debt, sym)}")
        print(f"  Enterprise Value: {_fmt_currency(ev, sym)}")
        print(f"  Currency: {currency}")
        print(f"{'=' * 65}")

        print("\n--- TARGET MULTIPLES ---")
        print(self.target_multiples().to_string())

        print("\n--- HISTORICAL MULTIPLES ---")
        print(self.historical_multiples().to_string())

        print("\n--- VALUATION SUMMARY (Historical + Projected) ---")
        print(self.valuation_summary().to_string())

        print("\n--- TARGET PRICES BY MULTIPLE ---")
        print(self.target_prices().to_string())

        print("\n--- BUY PRICE FOR 15% ANNUAL RETURN ---")
        bp = self.buy_price_for_return(target_return=0.15, reference_year=1)
        for k, v in bp.items():
            print(f"  {k:<35} {v}")