from __future__ import annotations

import numpy as np
import pytest

from src.models.m1_ac import ac_classical_closed_form, ac_classical_cvxpy, solve_m1
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio, ahp_weights, solve_m4
from src.utils.contracts import Order


# ---------------------------------------------------------
# M1: Almgren-Chriss Tests
# ---------------------------------------------------------
def test_m1_zero_risk_is_twap():
    trades = ac_classical_closed_form(X=1000.0, T=5, lam=0.0, sigma=0.02, eta=0.1)
    np.testing.assert_allclose(trades, np.full(5, 200.0))


def test_m1_positive_risk_front_loaded():
    trades = ac_classical_closed_form(X=1000.0, T=5, lam=1e-3, sigma=0.02, eta=0.05)
    # Higher risk aversion means front-loading trades
    assert trades[0] > trades[-1]
    np.testing.assert_allclose(np.sum(trades), 1000.0, atol=1e-5)


def test_m1_closed_form_matches_cvxpy():
    X = 5000.0
    T = 10
    lam = 1e-4
    sigma = 0.015
    eta = 0.08

    closed = ac_classical_closed_form(X, T, lam, sigma, eta)
    solver = ac_classical_cvxpy(X, T, lam, sigma, eta)

    np.testing.assert_allclose(np.sum(closed), X, atol=1e-4)
    np.testing.assert_allclose(np.sum(solver), X, atol=1e-4)
    np.testing.assert_allclose(closed, solver, rtol=1e-2, atol=1e-2)


def test_m1_numerical_stability_large_kappa():
    # Extreme risk aversion / long horizon should not overflow to inf or nan
    trades = ac_classical_closed_form(X=1000.0, T=50, lam=10.0, sigma=1.0, eta=0.001)
    assert not np.any(np.isnan(trades))
    assert not np.any(np.isinf(trades))
    np.testing.assert_allclose(np.sum(trades), 1000.0, atol=1e-4)


def test_m1_invalid_parameters():
    with pytest.raises(ValueError, match="Order quantity X must be positive"):
        ac_classical_closed_form(X=-10.0, T=5, lam=0.1, sigma=0.1, eta=0.1)

    with pytest.raises(ValueError, match="Horizon T must be at least 1"):
        ac_classical_closed_form(X=100.0, T=0, lam=0.1, sigma=0.1, eta=0.1)

    with pytest.raises(ValueError, match="Temporary impact eta must be strictly positive"):
        ac_classical_closed_form(X=100.0, T=5, lam=0.1, sigma=0.1, eta=0.0)

    with pytest.raises(ValueError, match="Risk aversion lambda must be non-negative"):
        ac_classical_closed_form(X=100.0, T=5, lam=-0.1, sigma=0.1, eta=0.1)


def test_m1_solve_contract():
    order = Order(side="buy", size=2000.0, horizon=4, params={})
    schedule = solve_m1(order, params={"lambda_imp": 0.0})
    assert len(schedule.shares) == 4
    np.testing.assert_allclose(schedule.shares, np.full(4, 500.0))


# ---------------------------------------------------------
# M2: LOB LP/QP Tests
# ---------------------------------------------------------
@pytest.fixture
def mock_lob_data():
    T = 5
    L = 3
    Pa = np.array([[100.0 + level_idx * 0.1 for level_idx in range(L)] for _ in range(T)])
    Va = np.full((T, L), 200.0)
    mid = np.full(T, 99.95)
    Da = np.full(T, 600.0)
    return {"Pa": Pa, "Va": Va, "M": mid, "Da": Da, "T": T, "L": L}


def test_m2_lp_solve_and_conservation(mock_lob_data):
    order = Order(side="buy", size=300.0, horizon=5, params={})
    schedule = solve_m2(order, mock_lob_data, params={"rho": 1.0, "lambda_imp": 0.0})

    assert len(schedule.shares) == 5
    assert np.all(schedule.shares >= -1e-6)
    np.testing.assert_allclose(np.sum(schedule.shares), 300.0, atol=1e-4)


def test_m2_participation_limit(mock_lob_data):
    # If Da = 600, rho = 0.1, max per step is 60. Over 5 steps, max total is 300.
    order = Order(side="buy", size=250.0, horizon=5, params={})
    schedule = solve_m2(order, mock_lob_data, params={"rho": 0.1})
    assert np.all(schedule.shares <= 60.0 + 1e-4)


def test_m2_invalid_inputs(mock_lob_data):
    order = Order(side="buy", size=-100.0, horizon=5, params={})
    with pytest.raises(ValueError):
        solve_m2(order, mock_lob_data)

    valid_order = Order(side="buy", size=100.0, horizon=5, params={})
    with pytest.raises(KeyError):
        solve_m2(valid_order, {"Pa": mock_lob_data["Pa"]})


# ---------------------------------------------------------
# M3: MIP Tests
# ---------------------------------------------------------
def test_m3_mip_lot_and_fixed_costs(mock_lob_data):
    order = Order(side="buy", size=300.0, horizon=5, params={})
    # Set high fixed cost c_f to incentivize fewer trade steps, with min lot = 100
    params = {"c_f": 50.0, "L_min": 100.0, "K": 3, "rho": 1.0}
    schedule = solve_m3(order, mock_lob_data, params=params)

    assert len(schedule.shares) == 5
    np.testing.assert_allclose(np.sum(schedule.shares), 300.0, atol=1e-4)
    # Active trades must be at least L_min
    active_trades = schedule.shares[schedule.shares > 1e-4]
    assert len(active_trades) <= 3
    assert np.all(active_trades >= 100.0 - 1e-4)


def test_m3_mip_infeasible_detected(mock_lob_data):
    # Cardinality K=1 with Q=500 and max execution per step limited by rho*Da = 50
    order = Order(side="buy", size=500.0, horizon=5, params={})
    params = {"rho": 0.05, "K": 1}  # max single step is 30, impossible to fill 500
    with pytest.raises(RuntimeError, match="infeasible"):
        solve_m3(order, mock_lob_data, params=params)


# ---------------------------------------------------------
# M4: AHP Tests
# ---------------------------------------------------------
def test_m4_ahp_consistent():
    # Perfectly consistent 3x3 matrix: criterion 1 is 2x criterion 2, 6x criterion 3
    matrix = np.array(
        [
            [1.0, 2.0, 6.0],
            [0.5, 1.0, 3.0],
            [1 / 6, 1 / 3, 1.0],
        ]
    )
    cr, is_consistent = ahp_consistency_ratio(matrix)
    assert is_consistent
    assert cr < 0.05

    weights = ahp_weights(matrix)
    assert len(weights) == 3
    np.testing.assert_allclose(np.sum(weights), 1.0)
    assert weights[0] > weights[1] > weights[2]


def test_m4_ahp_inconsistent():
    # Intentionally contradictory pairwise matrix
    matrix = np.array(
        [
            [1.0, 9.0, 1 / 9],
            [1 / 9, 1.0, 9.0],
            [9.0, 1 / 9, 1.0],
        ]
    )
    cr, is_consistent = ahp_consistency_ratio(matrix)
    assert not is_consistent
    assert cr > 0.10


def test_m4_ahp_invalid_inputs():
    with pytest.raises(ValueError, match="must be 2D square"):
        ahp_weights(np.array([1.0, 2.0, 3.0]))

    with pytest.raises(ValueError, match="must be strictly positive"):
        ahp_consistency_ratio(np.array([[1.0, -1.0], [-1.0, 1.0]]))


def test_m4_solve_contract():
    order = Order(side="buy", size=400.0, horizon=4, params={})
    sched = solve_m4(order)
    np.testing.assert_allclose(sched.shares, np.full(4, 100.0))
