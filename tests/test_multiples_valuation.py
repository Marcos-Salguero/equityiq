import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from equityiq.multiples_valuation import MultiplesValuation
from equityiq.projection import Projector
from tests.test_fundamental import (
    MOCK_INFO, MOCK_IS, MOCK_BS, MOCK_CF
)

MOCK_INFO_MV = {
    **MOCK_INFO,
    "marketCap": 150_000_000_000,
    "currentPrice": 150.0,
}


@pytest.fixture
def mv():
    with patch("equityiq.fundamental.get_stock_info", return_value=MOCK_INFO_MV), \
         patch("equityiq.fundamental.get_income_statement", return_value=MOCK_IS), \
         patch("equityiq.fundamental.get_balance_sheet", return_value=MOCK_BS), \
         patch("equityiq.fundamental.get_cash_flow", return_value=MOCK_CF), \
         patch("equityiq.projection.get_stock_info", return_value=MOCK_INFO_MV), \
         patch("equityiq.multiples_valuation.get_stock_info", return_value=MOCK_INFO_MV):
        p = Projector("TEST", revenue_growth=0.20, ebit_margin=0.40, tax_rate=0.15)
        return MultiplesValuation(
            "TEST", projector=p,
            per_target=25, ev_fcf_target=25,
            ev_ebitda_target=17, ev_ebit_target=20
        )


def test_target_multiples(mv):
    s = mv.target_multiples()
    assert "PER Target" in s.index
    assert "EV/FCF Target" in s.index
    assert s["PER Target"] == "25.00x"


def test_historical_multiples_shape(mv):
    df = mv.historical_multiples()
    assert "PER" in df.index
    assert "EV/FCF" in df.index
    assert "Median" in df.columns


def test_valuation_summary_shape(mv):
    df = mv.valuation_summary()
    assert "PER" in df.index
    assert "EV/FCF" in df.index
    assert df.shape[1] > 0


def test_target_prices_shape(mv):
    df = mv.target_prices()
    assert "PER ex Cash" in df.index
    assert "EV/FCF" in df.index
    assert "Average" in df.index
    assert df.shape[1] == 5


def test_target_prices_cagr(mv):
    df = mv.target_prices()
    assert "CAGR EV/FCF" in df.index
    assert "CAGR Average" in df.index


def test_target_prices_margin_of_safety(mv):
    df = mv.target_prices()
    assert "Margin of Safety (EV/FCF)" in df.index
    assert "Upside Potential (EV/FCF)" in df.index


def test_buy_price_structure(mv):
    bp = mv.buy_price_for_return(target_return=0.15)
    assert "Max Buy Price" in bp
    assert "Current Price" in bp
    assert "Verdict" in bp
    assert bp["Verdict"] in [
        "BELOW target price — attractive entry",
        "ABOVE target price — wait for better entry"
    ]


def test_buy_price_logic(mv):
    bp = mv.buy_price_for_return(target_return=0.0)
    # With 0% target return, buy price should equal target price
    target = mv.target_prices(formatted=False).loc["EV/FCF"].iloc[0]
    buy = float(bp["Max Buy Price"].replace("$", "").replace(",", ""))
    assert abs(buy - target) < 1.0