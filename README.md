# 📊 EquityIQ

A Python library for quantitative stock analysis. EquityIQ provides a clean, 
data-driven framework to evaluate stocks based purely on numbers — no noise, 
no opinions, just metrics.

## Features

- **Financial Health** — Liquidity, debt, profitability and growth ratios
- **Valuation** — Market multiples, dividend analysis and simplified DCF
- **Quantitative Signals** — Momentum, quality and valuation signals aggregated into a score
- **Report** — Full analysis report with BUY / HOLD / SELL recommendation

## Installation

```bash
pip install equityiq
```

## Quick Start

```python
from equityiq.report import Report

report = Report("AAPL")
report.summary()
```

Output:
============================================================
  EQUITYIQ REPORT — Apple Inc. (AAPL)
============================================================
  Sector:      Technology
  Industry:    Consumer Electronics
  Country:     United States
  Market Cap:  $4376.98B
  Generated:   2026-06-21 01:05:26
============================================================

--- FINANCIAL HEALTH ---
  Liquidity
    Current Ratio:       1.07
    Quick Ratio:         0.91
  Debt
    Debt to Equity:      79.55
    Interest Coverage:   N/A
  Profitability
    ROE:                 141.5%
    ROA:                 26.2%
    Gross Margin:        47.9%
    Net Margin:          27.2%
  Growth
    Revenue Growth:      16.6%
    Earnings Growth:     21.8%

--- VALUATION ---
  Market Multiples
    P/E (trailing):      36.12
    P/E (forward):       31.04
    P/B:                 41.05
    P/S:                 9.70
    PEG:                 2.41
    EV/EBITDA:           27.46
  DCF Valuation (simplified)
    Intrinsic Value:     $107.87
    Safety Price (25%):  $80.91
    Upside/Downside:     -63.8%
    Undervalued:         No

--- SIGNALS ---
  Momentum
    Price:               $298.01
    MA 50:               $288.63
    MA 200:              $267.79
    Above MA50:          Yes
    Above MA200:         Yes
    Golden Cross:        Yes
    RSI (14):            39.07 — neutral
    From 52w High:       -5.45%
    From 52w Low:        49.37%
  Quality
    FCF Quality:         high
    Revenue Growing:     Yes
    Earnings Growing:    Yes
    Healthy Margins:     Yes
  Valuation Signals
    P/E Signal:          expensive
    P/B Signal:          expensive
    PEG Signal:          overvalued

============================================================
  🟢  RECOMMENDATION: BUY  |  SCORE: 70/100
============================================================
  Momentum Score:   3/4
  Quality Score:    4/4
  Valuation Score:  0/2
============================================================

## Usage

### Financial Health

```python
from equityiq.health import HealthAnalyzer

health = HealthAnalyzer("AAPL")
health.liquidity_ratios()
health.profitability_ratios()
health.summary()
```

### Valuation

```python
from equityiq.valuation import ValuationAnalyzer

valuation = ValuationAnalyzer("AAPL")
valuation.market_ratios()
valuation.intrinsic_value(growth_rate=0.12, discount_rate=0.09)
valuation.summary()
```

### Signals & Score

```python
from equityiq.signals import SignalAnalyzer

signals = SignalAnalyzer("AAPL")
signals.momentum_signals()
signals.quality_signals()
signals.overall_score()
```

### Compare Multiple Stocks

```python
import pandas as pd
from equityiq.report import Report

tickers = ["AAPL", "MSFT", "GOOGL"]
dataframes = []

for t in tickers:
    r = Report(t)
    df = r.to_dataframe()
    df["ticker"] = t
    dataframes.append(df)

comparison = pd.concat(dataframes).pivot_table(
    index="metric", columns="ticker", values="value", aggfunc="first"
)
print(comparison)
```

## Data Sources

EquityIQ uses [yfinance](https://github.com/ranaroussi/yfinance) to retrieve 
financial data from Yahoo Finance. Data availability depends on the ticker 
and may vary.

## Disclaimer

This library is intended for educational and research purposes only. 
Nothing in EquityIQ constitutes financial advice. Always do your own 
research before making investment decisions.

## License

MIT License — see [LICENSE](LICENSE) for details.