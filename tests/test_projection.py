import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from equityiq.projection import Projector
from tests.test_fundamental import (
    MOCK_INFO, MOCK_IS, MOCK_BS, MOCK_CF
)


@pytest.fixture
def projector():
    with patch("equityiq.fundamental.get_stock_info", return_value=MOCK_INFO), \
         patch("equityiq.fundamental.get_income_statement", return_value=MOCK_IS), \
         patch("equityiq.fundamental.get_balance_sheet", return_value=MOCK_BS), \
         patch("equityiq.fundamental.get_cash_flow", return_value=MOCK_CF), \
         patch("equityiq.projection.get_stock_info", return_value=MOCK_INFO):
        return Projector("TEST", revenue_growth=0.20, ebit_margin=0.40, tax_rate=0.15)


def test_resolve_assumption_scalar():
    result = Projector._resolve_assumption(0.20, 5, 0.10)
    assert result == [0.20] * 5


def test_resolve_assumption_none():
    result = Projector._resolve_assumption(None, 5, 0.15)
    assert result == [0.15] * 5


def test_resolve_assumption_list_single():
    result = Projector._resolve_assumption([0.25], 5, 0.10)
    assert result == [0.25] * 5


def test_resolve_assumption_list_two():
    result = Projector._resolve_assumption([0.25, 0.20], 5, 0.10)
    assert result == [0.25, 0.20, 0.20, 0.20, 0.20]


def test_resolve_assumption_list_full():
    vals = [0.25, 0.22, 0.20, 0.18, 0.16]
    result = Projector._resolve_assumption(vals, 5, 0.10)
    assert result == vals


def test_resolve_assumption_list_truncate():
    vals = [0.25, 0.22, 0.20, 0.18, 0.16, 0.14]
    result = Projector._resolve_assumption(vals, 5, 0.10)
    assert result == vals[:5]


def test_assumptions_returns_dataframe(projector):
    df = projector.assumptions()
    assert isinstance(df, pd.DataFrame)
    assert "Revenue Growth" in df.index
    assert "EBIT Margin" in df.index
    assert "Tax Rate" in df.index


def test_projected_years(projector):
    years = projector._project_years()
    assert len(years) == 5
    assert years[0] == "2025e"
    assert years[-1] == "2029e"


def test_income_statement_shape(projector):
    df = projector.income_statement()
    assert df.shape[1] == 5
    assert "Revenue" in df.index


def test_income_statement_growth(projector):
    df = projector.income_statement(formatted=False)
    rev = df.loc["Revenue"]
    for i in range(1, len(rev)):
        ratio = rev.iloc[i] / rev.iloc[i - 1]
        assert abs(ratio - 1.20) < 1e-6


def test_income_statement_margins(projector):
    df = projector.income_statement(formatted=False)
    for col in df.columns:
        assert abs(df.loc["EBIT Margin %", col] - 0.40) < 1e-6
        assert abs(df.loc["Tax Rate %", col] - 0.15) < 1e-6


def test_free_cash_flow_shape(projector):
    df = projector.free_cash_flow()
    assert df.shape[1] == 5
    assert "Free Cash Flow" in df.index


def test_free_cash_flow_positive(projector):
    df = projector.free_cash_flow(formatted=False)
    assert (df.loc["Free Cash Flow"] > 0).all()


def test_combined_view_no_stray_columns(projector):
    df = projector.combined_view()
    for col in df.columns:
        assert "2021" not in col


def test_combined_view_no_nan(projector):
    df = projector.combined_view()
    assert not df.isin([float("nan")]).any().any()