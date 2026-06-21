import pandas as pd
import numpy as np
from equityiq.data import (
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_stock_info,
)


# ------------------------------------------------------------------
# FORMATTING UTILITIES
# ------------------------------------------------------------------

def _get_currency_symbol(info: dict) -> str:
    currency = info.get("currency", "USD")
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    return symbols.get(currency, currency + " ")


def _fmt_currency(val, symbol="$") -> str:
    if pd.isna(val) or val == 0:
        return "-"
    if abs(val) >= 1_000:
        return f"{symbol}{val:,.0f}M"
    return f"{symbol}{val:.1f}M"


def _fmt_pct(val) -> str:
    if pd.isna(val):
        return "-"
    return f"{val * 100:.1f}%"


def _fmt_ratio(val) -> str:
    if pd.isna(val):
        return "-"
    return f"{val:.2f}x"


def _fmt_eps(val, symbol="$") -> str:
    if pd.isna(val) or val == 0:
        return "-"
    return f"{symbol}{val:.2f}"


def _fmt_shares(val) -> str:
    if pd.isna(val) or val == 0:
        return "-"
    return f"{val:,.0f}M"


def _apply_format(df: pd.DataFrame, fmt_map: dict) -> pd.DataFrame:
    """
    Applies formatting functions to each row of a DataFrame.
    fmt_map: {row_name: format_function}
    """
    result = df.copy().astype(object)
    for row, fn in fmt_map.items():
        if row in result.index:
            result.loc[row] = result.loc[row].apply(
                lambda v: fn(v) if not isinstance(v, str) else v
            )
    return result


class FundamentalAnalyzer:
    """
    Replicates the IS, FCF and ROIC analysis sheets.
    Computes historical metrics, margins, Y/Y growth rates,
    working capital, free cash flow and return on invested capital.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.info = get_stock_info(ticker)
        self.currency = _get_currency_symbol(self.info)
        self.is_df = get_income_statement(ticker).fillna(0)
        self.bs_df = get_balance_sheet(ticker).fillna(0)
        self.cf_df = get_cash_flow(ticker).fillna(0)

        # Drop columns where all values are 0 or NaN
        self.is_df = self._drop_empty_years(self.is_df)
        self.bs_df = self._drop_empty_years(self.bs_df)
        self.cf_df = self._drop_empty_years(self.cf_df)
        self._years = self.is_df.columns.tolist()

    def _drop_empty_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes columns (years) where all values are 0 or NaN."""
        return df.loc[:, ~(df.fillna(0) == 0).all(axis=0)]

    # ------------------------------------------------------------------
    # INCOME STATEMENT
    # ------------------------------------------------------------------

    def income_statement(self, formatted: bool = True) -> pd.DataFrame:
        """
        Returns a summary income statement with margins and Y/Y growth.
        All monetary values in millions.

        Args:
            formatted: If True returns human-readable strings.
                       If False returns raw floats for further processing.
        """
        is_ = self.is_df
        sym = self.currency

        rows = {}
        rows["Revenue"] = is_.loc["revenue"]
        rows["Revenue Y/Y %"] = is_.loc["revenue"].pct_change()
        rows["Gross Profit"] = is_.loc["gross_profit"]
        rows["Gross Margin %"] = is_.loc["gross_profit"] / is_.loc["revenue"]
        rows["EBITDA"] = is_.loc["ebitda"]
        rows["EBITDA Margin %"] = is_.loc["ebitda"] / is_.loc["revenue"]
        rows["EBITDA Y/Y %"] = is_.loc["ebitda"].pct_change()
        rows["D&A"] = is_.loc["da"]
        rows["EBIT"] = is_.loc["ebit"]
        rows["EBIT Margin %"] = is_.loc["ebit"] / is_.loc["revenue"]
        rows["EBIT Y/Y %"] = is_.loc["ebit"].pct_change()
        rows["Interest Expense"] = is_.loc["interest_expense"]
        rows["Interest Income"] = is_.loc["interest_income"]
        rows["Total Net Interest"] = (
            is_.loc["interest_income"] - is_.loc["interest_expense"]
        )
        rows["Tax Expense"] = is_.loc["tax_expense"]
        rows["Tax Rate %"] = (
            is_.loc["tax_expense"].abs() /
            (is_.loc["ebit"] + rows["Total Net Interest"])
        )
        rows["Net Income"] = is_.loc["net_income"]
        rows["Net Margin %"] = is_.loc["net_income"] / is_.loc["revenue"]
        rows["Net Income Y/Y %"] = is_.loc["net_income"].pct_change()
        rows["EPS Diluted"] = is_.loc["eps_diluted"]
        rows["EPS Y/Y %"] = is_.loc["eps_diluted"].pct_change()
        rows["Shares Diluted (M)"] = is_.loc["shares_diluted"] / 1e6
        rows["Shares Y/Y %"] = is_.loc["shares_diluted"].pct_change()

        df = pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)

        if not formatted:
            return df

        fmt_map = {
            "Revenue": lambda v: _fmt_currency(v, sym),
            "Revenue Y/Y %": _fmt_pct,
            "Gross Profit": lambda v: _fmt_currency(v, sym),
            "Gross Margin %": _fmt_pct,
            "EBITDA": lambda v: _fmt_currency(v, sym),
            "EBITDA Margin %": _fmt_pct,
            "EBITDA Y/Y %": _fmt_pct,
            "D&A": lambda v: _fmt_currency(v, sym),
            "EBIT": lambda v: _fmt_currency(v, sym),
            "EBIT Margin %": _fmt_pct,
            "EBIT Y/Y %": _fmt_pct,
            "Interest Expense": lambda v: _fmt_currency(v, sym),
            "Interest Income": lambda v: _fmt_currency(v, sym),
            "Total Net Interest": lambda v: _fmt_currency(v, sym),
            "Tax Expense": lambda v: _fmt_currency(v, sym),
            "Tax Rate %": _fmt_pct,
            "Net Income": lambda v: _fmt_currency(v, sym),
            "Net Margin %": _fmt_pct,
            "Net Income Y/Y %": _fmt_pct,
            "EPS Diluted": lambda v: _fmt_eps(v, sym),
            "EPS Y/Y %": _fmt_pct,
            "Shares Diluted (M)": _fmt_shares,
            "Shares Y/Y %": _fmt_pct,
        }
        return _apply_format(df, fmt_map)

    def is_cagr(self) -> pd.Series:
        """
        Returns CAGR for key IS metrics across available history.
        """
        is_ = self.is_df
        years = len(self._years) - 1
        if years <= 0:
            return pd.Series(dtype=float)

        def cagr(series):
            try:
                start = series.iloc[0]
                end = series.iloc[-1]
                if start <= 0 or end <= 0:
                    return np.nan
                return (end / start) ** (1 / years) - 1
            except Exception:
                return np.nan

        return pd.Series({
            "Revenue CAGR": _fmt_pct(cagr(is_.loc["revenue"])),
            "EBITDA CAGR": _fmt_pct(cagr(is_.loc["ebitda"])),
            "EBIT CAGR": _fmt_pct(cagr(is_.loc["ebit"])),
            "Net Income CAGR": _fmt_pct(cagr(is_.loc["net_income"])),
            "EPS CAGR": _fmt_pct(cagr(is_.loc["eps_diluted"])),
        })

    # ------------------------------------------------------------------
    # FREE CASH FLOW
    # ------------------------------------------------------------------

    def working_capital(self) -> pd.DataFrame:
        """Returns working capital components and variation (CWC)."""
        bs_ = self.bs_df

        wc = (
            bs_.loc["accounts_receivable"]
            + bs_.loc["inventories"]
            - bs_.loc["accounts_payable"]
            - bs_.loc["unearned_revenue"]
        )
        cwc = wc.diff()

        rows = {
            "Accounts Receivable": bs_.loc["accounts_receivable"],
            "Inventories": bs_.loc["inventories"],
            "Accounts Payable": bs_.loc["accounts_payable"],
            "Unearned Revenue": bs_.loc["unearned_revenue"],
            "Working Capital": wc,
            "Change in WC (CWC)": cwc,
        }
        return pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)

    def _fcf_raw(self) -> pd.DataFrame:
        """Internal method returning raw FCF data for further calculations."""
        is_ = self.is_df
        cf_ = self.cf_df
        wc_df = self.working_capital()

        ebitda = is_.loc["ebitda"]
        capex_maint = cf_.loc["capex_maintenance"]
        net_interest = (
            is_.loc["interest_income"] - is_.loc["interest_expense"]
        )
        taxes = -is_.loc["tax_expense"].abs()
        cwc = wc_df.loc["Change in WC (CWC)"].fillna(0)
        shares = is_.loc["shares_diluted"] / 1e6

        fcf = ebitda + capex_maint + net_interest + taxes - cwc

        rows = {
            "EBITDA": ebitda,
            "(-) CapEx Maintenance": capex_maint,
            "(-) Net Interest": net_interest,
            "(-) Taxes Paid": taxes,
            "(-) Change in WC": -cwc,
            "Free Cash Flow": fcf,
            "FCF Margin %": fcf / is_.loc["revenue"],
            "FCF Y/Y %": fcf.pct_change(),
            "FCF per Share": fcf / shares,
            "Cash Conversion (FCF/EBITDA)": fcf / ebitda,
        }
        return pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)

    def free_cash_flow(self, formatted: bool = True) -> pd.DataFrame:
        """
        Computes FCF following the Excel model logic.

        Args:
            formatted: If True returns human-readable strings.
        """
        sym = self.currency
        df = self._fcf_raw()

        if not formatted:
            return df

        fmt_map = {
            "EBITDA": lambda v: _fmt_currency(v, sym),
            "(-) CapEx Maintenance": lambda v: _fmt_currency(v, sym),
            "(-) Net Interest": lambda v: _fmt_currency(v, sym),
            "(-) Taxes Paid": lambda v: _fmt_currency(v, sym),
            "(-) Change in WC": lambda v: _fmt_currency(v, sym),
            "Free Cash Flow": lambda v: _fmt_currency(v, sym),
            "FCF Margin %": _fmt_pct,
            "FCF Y/Y %": _fmt_pct,
            "FCF per Share": lambda v: _fmt_eps(v, sym),
            "Cash Conversion (FCF/EBITDA)": _fmt_pct,
        }
        return _apply_format(df, fmt_map)

    def fcf_efficiency(self, formatted: bool = True) -> pd.DataFrame:
        """Returns FCF efficiency ratios as % of revenue."""
        is_ = self.is_df
        cf_ = self.cf_df
        fcf = self._fcf_raw().loc["Free Cash Flow"]
        wc = self.working_capital().loc["Working Capital"]

        rows = {
            "CapEx Maintenance / Revenue": cf_.loc["capex_maintenance"].abs() / is_.loc["revenue"],
            "Working Capital / Revenue": wc / is_.loc["revenue"],
            "FCF Margin (FCF / Revenue)": fcf / is_.loc["revenue"],
            "Cash Conversion (FCF / EBITDA)": fcf / is_.loc["ebitda"],
        }
        df = pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)
        df["Median"] = df.median(axis=1)

        if not formatted:
            return df

        return df.map(_fmt_pct)

    def capital_allocation(self, formatted: bool = True) -> pd.DataFrame:
        """Returns capital allocation as % of FCF."""
        cf_ = self.cf_df
        fcf = self._fcf_raw().loc["Free Cash Flow"]

        rows = {
            "CapEx Expansion": cf_.loc["capex_expansion"].abs() / fcf,
            "Acquisitions": cf_.loc["acquisitions"].abs() / fcf,
            "Repurchases": cf_.loc["repurchases"].abs() / fcf,
            "Dividends": cf_.loc["dividends"].abs() / fcf,
        }
        df = pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)
        df["Median"] = df.median(axis=1)

        if not formatted:
            return df

        return df.map(_fmt_pct)

    # ------------------------------------------------------------------
    # ROIC
    # ------------------------------------------------------------------

    def _roic_raw(self) -> pd.DataFrame:
        """Internal method returning raw ROIC data."""
        bs_ = self.bs_df
        is_ = self.is_df

        tax_rate = (
            is_.loc["tax_expense"].abs() /
            (is_.loc["ebit"] + is_.loc["interest_income"] -
             is_.loc["interest_expense"])
        ).replace([np.inf, -np.inf], np.nan).fillna(0.20)

        nopat = is_.loc["ebit"] * (1 - tax_rate)
        ic = (
            bs_.loc["total_equity"]
            + bs_.loc["short_term_debt"]
            + bs_.loc["long_term_debt"]
            + bs_.loc["operating_lease_current"]
            + bs_.loc["operating_lease_non_current"]
            - bs_.loc["cash"]
            - bs_.loc["marketable_securities"]
        )

        rows = {
            "NOPAT (EBIT x (1-t))": nopat,
            "Cash": bs_.loc["cash"],
            "(-) Marketable Securities": bs_.loc["marketable_securities"],
            "(+) Short-Term Debt": bs_.loc["short_term_debt"],
            "(+) Long-Term Debt": bs_.loc["long_term_debt"],
            "(+) Operating Lease Current": bs_.loc["operating_lease_current"],
            "(+) Operating Lease Non-Current": bs_.loc["operating_lease_non_current"],
            "(+) Equity": bs_.loc["total_equity"],
            "Invested Capital": ic,
            "ROIC": nopat / ic,
            "ROE": is_.loc["net_income"] / bs_.loc["total_equity"],
        }
        return pd.DataFrame(rows).T.replace([np.inf, -np.inf], np.nan)

    def invested_capital(self, formatted: bool = True) -> pd.DataFrame:
        """
        Returns invested capital components, ROIC and ROE.

        Args:
            formatted: If True returns human-readable strings.
        """
        sym = self.currency
        df = self._roic_raw()
        df["Median"] = df.median(axis=1)

        if not formatted:
            return df

        currency_rows = [
            "NOPAT (EBIT x (1-t))", "Cash", "(-) Marketable Securities",
            "(+) Short-Term Debt", "(+) Long-Term Debt",
            "(+) Operating Lease Current", "(+) Operating Lease Non-Current",
            "(+) Equity", "Invested Capital",
        ]
        pct_rows = ["ROIC", "ROE"]

        fmt_map = {
            **{r: lambda v, s=sym: _fmt_currency(v, s) for r in currency_rows},
            **{r: _fmt_pct for r in pct_rows},
        }
        return _apply_format(df, fmt_map)

    # ------------------------------------------------------------------
    # RED FLAGS
    # ------------------------------------------------------------------

    def red_flags(self) -> dict:
        """
        Scans historical data and returns potential red flags.
        """
        is_ = self.is_df
        bs_ = self.bs_df
        cf_ = self.cf_df
        sym = self.currency
        roic = self._roic_raw().loc["ROIC"]
        fcf = self._fcf_raw().loc["Free Cash Flow"]

        sbc = cf_.loc["stock_based_compensation"]
        revenue = is_.loc["revenue"]

        net_debt_ebitda = (
            bs_.loc["long_term_debt"]
            + bs_.loc["short_term_debt"]
            - bs_.loc["cash"]
            - bs_.loc["marketable_securities"]
        ) / is_.loc["ebitda"]

        as_pct_revenue = pd.DataFrame({
            "SBC / Revenue": sbc / revenue,
        }).T.map(_fmt_pct)

        counters = pd.Series({
            "Years with revenue decline": int((is_.loc["revenue"].diff() < 0).sum()),
            "Years with FCF < 0": int((fcf < 0).sum()),
            "Years with poor ROIC (<10%)": int((roic < 0.10).sum()),
            "Years with Net Debt/EBITDA > 2.5x": int((net_debt_ebitda > 2.5).sum()),
        })

        return {
            "as_pct_revenue": as_pct_revenue,
            "counters": counters,
        }

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------

    def summary(self) -> None:
        """Prints a full fundamental analysis to the console."""
        name = self.info.get("longName", self.ticker)
        currency = self.info.get("currency", "USD")

        print(f"\n{'=' * 65}")
        print(f"  FUNDAMENTAL ANALYSIS — {name} ({self.ticker})")
        print(f"  Currency: {currency} | Values in millions")
        print(f"{'=' * 65}")

        print("\n--- INCOME STATEMENT ---")
        print(self.income_statement().fillna("-").to_string())

        print("\n--- CAGR (full available history) ---")
        print(self.is_cagr().to_string())

        print("\n--- FREE CASH FLOW ---")
        print(self.free_cash_flow().fillna("-").to_string())

        print("\n--- FCF EFFICIENCY ---")
        print(self.fcf_efficiency().fillna("-").to_string())

        print("\n--- CAPITAL ALLOCATION (% of FCF) ---")
        print(self.capital_allocation().fillna("-").to_string())

        print("\n--- ROIC & INVESTED CAPITAL ---")
        print(self.invested_capital().fillna("-").to_string())

        print("\n--- RED FLAGS ---")
        flags = self.red_flags()
        print(flags["as_pct_revenue"].fillna("-").to_string())
        print()
        print(flags["counters"].to_string())