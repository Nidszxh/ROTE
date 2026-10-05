from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from src.reports.visualizations import (
    plot_ahp_ranking,
    plot_benchmark_frontier,
    plot_lob_ladder,
    plot_m1_frontier,
    plot_m2_diagnostics,
    plot_m3_tradeoff,
    plot_microstructure_analytics,
)
from src.utils.contracts import Order


@pytest.fixture
def mock_book():
    T = 25
    L = 10
    Pa = np.array([[100.0 + l_idx * 0.1 for l_idx in range(L)] for _ in range(T)])
    Pb = np.array([[99.9 - l_idx * 0.1 for l_idx in range(L)] for _ in range(T)])
    Va = np.full((T, L), 500.0)
    Vb = np.full((T, L), 500.0)
    mid = np.full(T, 99.95)
    spread = np.full(T, 0.002)
    obi = np.full(T, 0.05)
    da = np.full(T, 5000.0)
    db = np.full(T, 5000.0)
    return {
        "Pa": Pa,
        "Pb": Pb,
        "Va": Va,
        "Vb": Vb,
        "M": mid,
        "S": spread,
        "OBI": obi,
        "Da": da,
        "Db": db,
    }


def test_plot_lob_ladder_valid(mock_book):
    fig = plot_lob_ladder(mock_book, snapshot_idx=0)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 2
    plt.close(fig)


def test_plot_lob_ladder_invalid_index(mock_book):
    with pytest.raises(IndexError, match="out of bounds"):
        plot_lob_ladder(mock_book, snapshot_idx=100)

    with pytest.raises(IndexError, match="out of bounds"):
        plot_lob_ladder(mock_book, snapshot_idx=-1)


def test_plot_lob_ladder_missing_key():
    with pytest.raises(KeyError, match="missing required key"):
        plot_lob_ladder({"Pa": np.ones((5, 10))})


def test_plot_microstructure_analytics_valid(mock_book):
    fig = plot_microstructure_analytics(mock_book, max_points=20)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 3
    plt.close(fig)


def test_plot_microstructure_analytics_invalid(mock_book):
    with pytest.raises(ValueError, match="max_points must be at least 1"):
        plot_microstructure_analytics(mock_book, max_points=0)


def test_plot_m1_frontier(mock_book):
    order = Order(side="buy", size=1000.0, horizon=5, params={})
    fig, df = plot_m1_frontier(order, mock_book, lambda_grid=[0.0, 1e-4, 1e-2])
    assert isinstance(fig, plt.Figure)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Shortfall (bps)" in df.columns
    assert "Risk (std)" in df.columns
    plt.close(fig)


def test_plot_m2_diagnostics(mock_book):
    order = Order(side="buy", size=500.0, horizon=5, params={})
    fig = plot_m2_diagnostics(order, mock_book, rho=0.25)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 2
    plt.close(fig)


def test_plot_m3_tradeoff(mock_book):
    order = Order(side="buy", size=500.0, horizon=5, params={})
    fig = plot_m3_tradeoff(order, mock_book)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 2
    plt.close(fig)


def test_plot_benchmark_frontier():
    df = pd.DataFrame(
        [
            {"Model": "TWAP", "Shortfall (bps)": 10.0, "Risk (std)": 15.0},
            {"Model": "M1", "Shortfall (bps)": 8.0, "Risk (std)": 10.0},
        ]
    )
    schedules = {
        "TWAP": np.array([50.0, 50.0]),
        "M1": np.array([60.0, 40.0]),
    }
    fig = plot_benchmark_frontier(df, schedules)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 2
    plt.close(fig)

    with pytest.raises(ValueError, match="cannot be empty"):
        plot_benchmark_frontier(pd.DataFrame(), {})


def test_plot_ahp_ranking():
    weights = np.array([0.5, 0.3, 0.2])
    scores_df = pd.DataFrame(
        [
            {"Model": "TWAP", "Score": 0.4},
            {"Model": "M1", "Score": 0.6},
        ]
    )
    fig = plot_ahp_ranking(weights, scores_df)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) >= 2
    plt.close(fig)

    with pytest.raises(ValueError, match="weights must have length 3"):
        plot_ahp_ranking(np.array([0.5, 0.5]), scores_df)
