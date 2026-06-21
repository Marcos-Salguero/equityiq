import pandas as pd
import numpy as np
from equityiq.data import get_stock_info
from equityiq.fundamental import (
    FundamentalAnalyzer,
    _fmt_currency,
    _fmt_pct,
    _fmt_eps,
    _fmt_shares,
    _apply_format,
    _get_currency_symbol,
)


class Projector:
    """
    Projects income statement, FCF and valuation metrics
    for the next N years based on analyst assumptions or
    historical medians/averages as defaults.

    Mirrors the projection logic of the Excel model:
    - Revenue grows at a user-defined or historically-derived rate
    - EBIT margin is user-defined or historical median
    - Tax rate is user-defined or historical median
    - CapEx maintenance scales with revenue (historical % median)
    - Working capital scales with revenue (historical % median)
    """

    def __init__(
        self,
        ticker: str,
        years: int = 5,
        revenue_growth: float | list | None = None,
        ebit_margin: float | list | None = None,
        tax_rate: float | list | None = None,
    ):
        """
        Args:
            ticker: Stock ticker symbol
            years: Number of years to project (default 5)
            revenue_growth: Annual revenue growth rate.
                            If None, uses historical median Y/Y growth.
            ebit_margin: EBIT margin assumption for projected years.
                         If None, uses historical median EBIT margin.
            tax_rate: Effective tax rate for projected years.
                      If None, uses historical median tax rate.
        """
        self.ticker = ticker.upper()
        self.years = years
        self.info = get_stock_info(ticker)
        self.currency = _get_currency_symbol(self.info)
        self.fa = FundamentalAnalyzer(ticker)

        self.is_df = self.fa.is_df
        self.cf_df = self.fa.cf_df

        # Resolve assumptions: use provided value or derive from history
        is_raw = self.fa.income_statement(formatted=False)
        fcf_eff = self.fa.fcf_efficiency(formatted=False)

        hist_growth = self._historical_median(self.is_df.loc["revenue"].pct_change())
        hist_ebit = self._historical_median(is_raw.loc["EBIT Margin %"])
        hist_tax = self._historical_median(is_raw.loc["Tax Rate %"])

        self.revenue_growth = self._resolve_assumption(revenue_growth, self.years, hist_growth)
        self.ebit_margin = self._resolve_assumption(ebit_margin, self.years, hist_ebit)
        self.tax_rate = self._resolve_assumption(tax_rate, self.years, hist_tax)

        self._capex_pct = self._historical_median(fcf_eff.loc["CapEx Maintenance / Revenue"])
        self._wc_pct = self._historical_median(fcf_eff.loc["Working Capital / Revenue"])
        self._da_pct = self._historical_median(self.is_df.loc["da"] / self.is_df.loc["revenue"])
        self._shares = self.is_df.loc["shares_diluted"].iloc[-1]

        # Last historical year as base
        self._base_year = int(self.is_df.columns[-1])
        self._base_revenue = self.is_df.loc["revenue"].iloc[-1]
        self._base_wc = self.fa.working_capital().loc["Working Capital"].iloc[-1]

    @staticmethod
    def _historical_median(series: pd.Series) -> float:
        return float(series.replace([np.inf, -np.inf], np.nan).dropna().median())

    @staticmethod
    def _resolve_assumption(value, years: int, historical_median: float) -> list[float]:
        """
        Resolves an assumption input into a list of length `years`.

        Rules:
        - None → use historical median for all years
        - float → use that value for all years
        - list of 1 → use that value for all years
        - list of 2 → first for year 1, last for remaining years
        - list of N (N <= years) → fill remaining years with last value
        - list of N (N > years) → truncate to `years`
        """
        if value is None:
            return [historical_median] * years
        if isinstance(value, (int, float)):
            return [float(value)] * years
        if isinstance(value, list):
            if len(value) == 0:
                return [historical_median] * years
            if len(value) >= years:
                return [float(v) for v in value[:years]]
            # Pad remaining years with last value
            padded = [float(v) for v in value]
            padded += [padded[-1]] * (years - len(padded))
            return padded
        return [historical_median] * years

    def assumptions(self) -> pd.DataFrame:
        """Returns the assumptions being used for the projection."""
        proj_years = self._project_years()
        data = {
            year: {
                "Revenue Growth": _fmt_pct(self.revenue_growth[i]),
                "EBIT Margin": _fmt_pct(self.ebit_margin[i]),
                "Tax Rate": _fmt_pct(self.tax_rate[i]),
                "CapEx Maint. / Revenue": _fmt_pct(self._capex_pct),
                "Working Capital / Revenue": _fmt_pct(self._wc_pct),
                "D&A / Revenue": _fmt_pct(self._da_pct),
            }
            for i, year in enumerate(proj_years)
        }
        return pd.DataFrame(data)

    def _project_years(self) -> list[str]:
        return [f"{self._base_year + i + 1}e" for i in range(self.years)]

    def income_statement(self, formatted: bool = True) -> pd.DataFrame:
        """
        Projects the income statement for the next N years.

        Returns:
            DataFrame with projected IS metrics.
        """
        sym = self.currency
        proj_years = self._project_years()
        results = {}

        base_revenue = self._base_revenue
        for i, year in enumerate(proj_years):
            revenue = base_revenue * ((1 + self.revenue_growth[i]) ** (i + 1))
            ebit_m = self.ebit_margin[i]
            tax_r = self.tax_rate[i]
            ebitda = revenue * (ebit_m + self._da_pct)
            da = revenue * self._da_pct
            ebit = revenue * ebit_m
            tax = ebit * tax_r
            net_income = ebit - tax
            eps = net_income / self._shares if self._shares > 0 else np.nan

            results[year] = {
                "Revenue": revenue,
                "Revenue Y/Y %": self.revenue_growth[i],
                "EBITDA": ebitda,
                "EBITDA Margin %": ebitda / revenue,
                "D&A": da,
                "EBIT": ebit,
                "EBIT Margin %": ebit_m,
                "Tax Expense": tax,
                "Tax Rate %": tax_r,
                "Net Income": net_income,
                "Net Margin %": net_income / revenue,
                "EPS Diluted": eps * 1e6,
                "Shares Diluted (M)": self._shares / 1e6,
            }

        df = pd.DataFrame(results)

        if not formatted:
            return df

        fmt_map = {
            "Revenue": lambda v: _fmt_currency(v, sym),
            "Revenue Y/Y %": _fmt_pct,
            "EBITDA": lambda v: _fmt_currency(v, sym),
            "EBITDA Margin %": _fmt_pct,
            "D&A": lambda v: _fmt_currency(v, sym),
            "EBIT": lambda v: _fmt_currency(v, sym),
            "EBIT Margin %": _fmt_pct,
            "Tax Expense": lambda v: _fmt_currency(v, sym),
            "Tax Rate %": _fmt_pct,
            "Net Income": lambda v: _fmt_currency(v, sym),
            "Net Margin %": _fmt_pct,
            "EPS Diluted": lambda v: _fmt_eps(v, sym),
            "Shares Diluted (M)": _fmt_shares,
        }
        return _apply_format(df, fmt_map)

    def free_cash_flow(self, formatted: bool = True) -> pd.DataFrame:
        """
        Projects FCF for the next N years.
        """
        sym = self.currency
        proj_years = self._project_years()
        is_proj = self.income_statement(formatted=False)
        results = {}

        prev_wc = self._base_wc
        for year in proj_years:
            revenue = is_proj.loc["Revenue", year]
            ebitda = is_proj.loc["EBITDA", year]
            capex_maint = -revenue * self._capex_pct
            tax = -is_proj.loc["Tax Expense", year]
            wc = revenue * self._wc_pct
            cwc = wc - prev_wc
            fcf = ebitda + capex_maint + tax - cwc
            prev_wc = wc

            results[year] = {
                "EBITDA": ebitda,
                "(-) CapEx Maintenance": capex_maint,
                "(-) Taxes Paid": tax,
                "(-) Change in WC": -cwc,
                "Free Cash Flow": fcf,
                "FCF Margin %": fcf / revenue,
                "FCF Y/Y %": np.nan,
                "FCF per Share": fcf / (self._shares / 1e6) if self._shares > 0 else np.nan,
                "Cash Conversion (FCF/EBITDA)": fcf / ebitda,
            }

        df = pd.DataFrame(results)

        # Compute Y/Y growth vs last historical FCF
        last_hist_fcf = self.fa._fcf_raw().loc["Free Cash Flow"].iloc[-1]
        fcf_values = [last_hist_fcf] + [
            df.loc["Free Cash Flow", y] for y in proj_years
        ]
        for i, year in enumerate(proj_years):
            if fcf_values[i] != 0:
                df.loc["FCF Y/Y %", year] = (
                    fcf_values[i + 1] / fcf_values[i]
                ) - 1

        if not formatted:
            return df

        fmt_map = {
            "EBITDA": lambda v: _fmt_currency(v, sym),
            "(-) CapEx Maintenance": lambda v: _fmt_currency(v, sym),
            "(-) Taxes Paid": lambda v: _fmt_currency(v, sym),
            "(-) Change in WC": lambda v: _fmt_currency(v, sym),
            "Free Cash Flow": lambda v: _fmt_currency(v, sym),
            "FCF Margin %": _fmt_pct,
            "FCF Y/Y %": _fmt_pct,
            "FCF per Share": lambda v: _fmt_eps(v, sym),
            "Cash Conversion (FCF/EBITDA)": _fmt_pct,
        }
        return _apply_format(df, fmt_map)

    def combined_view(self, formatted: bool = True) -> pd.DataFrame:
        """
        Returns historical + projected IS and FCF side by side,
        exactly like the Excel model.
        """
        hist_is = self.fa.income_statement(formatted=formatted)
        proj_is = self.income_statement(formatted=formatted)
        hist_fcf = self.fa.free_cash_flow(formatted=formatted)
        proj_fcf = self.free_cash_flow(formatted=formatted)

        # Valid historical years: only those present in IS data
        valid_hist_years = self.fa._years
        proj_years = self._project_years()

        # Filter historical columns to only valid years
        hist_is = hist_is[[c for c in hist_is.columns if c in valid_hist_years]]
        hist_fcf = hist_fcf[[c for c in hist_fcf.columns if c in valid_hist_years]]

        # Keep only rows common to both historical and projected
        is_common_rows = [r for r in hist_is.index if r in proj_is.index]
        fcf_common_rows = [r for r in hist_fcf.index if r in proj_fcf.index]

        is_combined = pd.concat(
            [hist_is.loc[is_common_rows], proj_is.loc[is_common_rows]], axis=1
        )
        fcf_combined = pd.concat(
            [hist_fcf.loc[fcf_common_rows], proj_fcf.loc[fcf_common_rows]], axis=1
        )

        # Sort columns chronologically
        all_years = valid_hist_years + proj_years
        is_combined = is_combined[[c for c in all_years if c in is_combined.columns]]
        fcf_combined = fcf_combined[[c for c in all_years if c in fcf_combined.columns]]

        separator = pd.DataFrame("", index=[""], columns=is_combined.columns)

        return pd.concat([is_combined, separator, fcf_combined]).fillna("-")

    def summary(self) -> None:
        """Prints the full projection to the console."""
        name = self.info.get("longName", self.ticker)
        currency = self.info.get("currency", "USD")

        print(f"\n{'=' * 65}")
        print(f"  PROJECTION — {name} ({self.ticker})")
        print(f"  Currency: {currency} | Values in millions")
        print(f"{'=' * 65}")

        print("\n--- ASSUMPTIONS ---")
        print(self.assumptions().to_string())

        print("\n--- PROJECTED INCOME STATEMENT ---")
        print(self.income_statement().to_string())

        print("\n--- PROJECTED FREE CASH FLOW ---")
        print(self.free_cash_flow().to_string())

        print("\n--- COMBINED VIEW (Historical + Projected) ---")
        combined = self.combined_view()

        # Replace any remaining NaN with "-"
        combined = combined.fillna("-")
        print(combined.to_string())