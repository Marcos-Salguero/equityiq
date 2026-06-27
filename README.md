# 📊 EquityIQ

**EquityIQ** is a Python library for quantitative stock analysis. It provides a clean, 
data-driven framework to evaluate stocks based purely on numbers — no noise, no opinions, 
just metrics.

Built for data scientists and quantitative investors who want to replicate professional 
financial analysis (Income Statement, FCF, ROIC, Valuation) directly in Python, with 
the same rigor as an institutional Excel model.

---

## Features

- **Fundamental Analysis** — Income statement metrics, margins, Y/Y growth, CAGR, 
  working capital, free cash flow, ROIC and red flags detection
- **Projections** — 5-year forward projections with flexible per-year assumptions 
  for revenue growth, EBIT margin and tax rate
- **Multiples Valuation** — Historical and projected PER, EV/FCF, EV/EBITDA and EV/EBIT, 
  target prices per year, implied CAGR and buy price for a target return
- **Quantitative Signals** — Momentum (MA, RSI, 52w high/low), quality and valuation 
  signals aggregated into a BUY / HOLD / SELL score
- **Financial Health** — Liquidity, debt, profitability and growth ratios
- **Reports** — Full console report combining all modules

---

## Installation

```bash
pip install equityiq
```

---

## Quick Start

```python
from equityiq.fundamental import FundamentalAnalyzer
from equityiq.projection import Projector
from equityiq.multiples_valuation import MultiplesValuation

# Step 1 — Historical analysis
fa = FundamentalAnalyzer("META")
fa.summary()

# Step 2 — Project the next 5 years
p = Projector("META", revenue_growth=0.20, ebit_margin=0.40, tax_rate=0.15)
p.summary()

# Step 3 — Valuation
mv = MultiplesValuation("META", projector=p,
                         per_target=25, ev_fcf_target=25,
                         ev_ebitda_target=17, ev_ebit_target=20)
mv.summary()
```

---

## Usage

### Fundamental Analysis

```python
from equityiq.fundamental import FundamentalAnalyzer

fa = FundamentalAnalyzer("AAPL")

fa.income_statement()       # Revenue, EBITDA, EBIT, Net Income, EPS + margins and Y/Y growth
fa.is_cagr()                # CAGR for key metrics across full available history
fa.free_cash_flow()         # FCF built from scratch: EBITDA - CapEx - Taxes - ΔWC
fa.fcf_efficiency()         # CapEx/Revenue, WC/Revenue, FCF margin, cash conversion
fa.capital_allocation()     # CapEx expansion, acquisitions, repurchases, dividends as % of FCF
fa.invested_capital()       # Invested capital components, ROIC and ROE
fa.red_flags()              # SBC/Revenue, years with FCF < 0, poor ROIC, high leverage
fa.summary()                # Full analysis in one call
```

### Projections

```python
from equityiq.projection import Projector

# Single assumption for all years
p = Projector("AAPL", revenue_growth=0.10, ebit_margin=0.30, tax_rate=0.16)

# Different assumption for year 1, same for the rest
p = Projector("AAPL", revenue_growth=[0.15, 0.10], ebit_margin=0.30, tax_rate=0.16)

# One assumption per year
p = Projector("AAPL",
              revenue_growth=[0.15, 0.12, 0.10, 0.09, 0.08],
              ebit_margin=[0.28, 0.29, 0.30, 0.30, 0.31],
              tax_rate=0.16)

p.assumptions()         # Shows assumptions used per year
p.income_statement()    # Projected IS for next 5 years
p.free_cash_flow()      # Projected FCF for next 5 years
p.combined_view()       # Historical + projected side by side
p.summary()             # Full projection in one call
```

### Multiples Valuation

```python
from equityiq.multiples_valuation import MultiplesValuation

mv = MultiplesValuation(
    "AAPL",
    projector=p,              # Optional: pass a custom Projector
    per_target=22,            # Optional: if None, uses historical median
    ev_fcf_target=25,
    ev_ebitda_target=15,
    ev_ebit_target=18,
)

mv.historical_multiples()       # PER, EV/FCF, EV/EBITDA, EV/EBIT with median
mv.valuation_summary()          # Multiples across historical and projected years
mv.target_prices()              # Target price per year per multiple + CAGR
mv.buy_price_for_return(0.15)   # Max buy price to achieve 15% annual return
mv.summary()                    # Full valuation in one call
```

### Quantitative Signals

```python
from equityiq.signals import SignalAnalyzer

signals = SignalAnalyzer("AAPL")
signals.momentum_signals()   # Price vs MA50/MA200, RSI, 52w high/low
signals.quality_signals()    # FCF quality, revenue/earnings growth, margins
signals.valuation_signals()  # P/E, P/B, PEG signals
signals.overall_score()      # Score 0-100 + BUY / HOLD / SELL recommendation
```

### Financial Health

```python
from equityiq.health import HealthAnalyzer

health = HealthAnalyzer("AAPL")
health.liquidity_ratios()       # Current ratio, quick ratio
health.debt_ratios()            # Debt/equity, interest coverage
health.profitability_ratios()   # ROE, ROA, gross/operating/net margin
health.growth_ratios()          # Revenue and earnings growth
health.summary()                # All metrics in one DataFrame
```

### Full Report

```python
from equityiq.report import Report

report = Report("AAPL")
report.summary()        # Console report with health, valuation and signals
report.to_dict()        # All metrics as a dictionary
report.to_dataframe()   # Flat DataFrame for multi-stock comparison
```

### Compare Multiple Stocks

```python
import pandas as pd
from equityiq.report import Report

tickers = ["AAPL", "MSFT", "GOOGL"]
frames = []

for t in tickers:
    df = Report(t).to_dataframe()
    df["ticker"] = t
    frames.append(df)

comparison = pd.concat(frames).pivot_table(
    index="metric", columns="ticker", values="value", aggfunc="first"
)
print(comparison)
```

---

## Data Sources

EquityIQ uses [yfinance](https://github.com/ranaroussi/yfinance) to retrieve financial 
data from Yahoo Finance. Data availability depends on the ticker and may vary. 
Free tier provides up to 4 years of annual financial statements.

---

## Project Structure

- `src/equityiq/`
  - `__init__.py`
  - `data/`
    - `__init__.py`
    - `fetcher.py` — Data retrieval and cleaning
  - `fundamental.py` — IS, FCF, ROIC, red flags
  - `projection.py` — 5-year forward projections
  - `multiples_valuation.py` — Target prices and implied returns
  - `health.py` — Financial health ratios
  - `valuation.py` — DCF and market multiples
  - `signals.py` — Quantitative signals and score
  - `report.py` — Full console report
- `tests/`
- `notebooks/`
  - `demo.ipynb`

---

## Disclaimer

EquityIQ is intended for **educational and research purposes only**. Nothing in this 
library constitutes financial advice. All projections and valuations are based on 
simplified models and historical data. Always do your own research before making 
any investment decision.

---

## License

MIT License — see [LICENSE](LICENSE) for details.