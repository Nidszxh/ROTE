import numpy as np
import pytest

from src.benchmarks.baselines import twap_plan
from src.models.m1_ac import ac_classical_closed_form
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio
from src.sim.simulate import simulate
from src.utils.contracts import Order, Schedule


@pytest.mark.T1
def test_t1_schedule_conserves_order():
    schedule = twap_plan(Order("buy", 1000.0, 5, {}))
    np.testing.assert_allclose(schedule.shares.sum(), 1000.0)


@pytest.mark.T2
def test_t2_schedule_is_non_negative():
    schedule = Schedule([1.0, 2.0, 3.0])
    assert np.all(schedule.shares >= 0)


@pytest.mark.T3
def test_t3_zero_risk_is_twap():
    np.testing.assert_allclose(ac_classical_closed_form(1000.0, 4, 0.0, 0.02, 0.1), 250.0)


@pytest.mark.T4
def test_t4_lob_model_conserves_order():
    book = {
        "Pa": np.full((2, 2), 101.0),
        "Va": np.full((2, 2), 100.0),
        "M": np.full(2, 100.0),
        "Da": np.full(2, 200.0),
    }
    schedule = solve_m2(Order("buy", 100.0, 2, {}), book)
    np.testing.assert_allclose(schedule.shares.sum(), 100.0, atol=1e-5)


@pytest.mark.T5
def test_t5_mip_respects_minimum_lot():
    book = {
        "Pa": np.full((2, 2), 101.0),
        "Va": np.full((2, 2), 100.0),
        "M": np.full(2, 100.0),
        "Da": np.full(2, 200.0),
    }
    schedule = solve_m3(Order("buy", 100.0, 2, {}), book, {"L_min": 50.0})
    active = schedule.shares[schedule.shares > 1e-6]
    assert np.all(active >= 50.0 - 1e-5)


@pytest.mark.T6
def test_t6_ahp_consistency_accepts_consistent_matrix():
    cr, consistent = ahp_consistency_ratio(np.array([[1.0, 2.0], [0.5, 1.0]]))
    assert consistent
    assert cr == 0.0


@pytest.mark.T7
def test_t7_simulator_reports_filled_order():
    book = {"Pa": np.full((2, 1), 101.0), "Va": np.full((2, 1), 100.0), "M": np.full(2, 100.0)}
    report = simulate(Schedule([50.0, 50.0]), book)
    assert report.trades == 2
    assert report.shortfall_bps > 0


@pytest.mark.T8
def test_t8_terminal_sweep_uses_last_in_horizon_snapshot():
    book = {
        "Pa": np.array([[101.0], [102.0], [10_000.0]]),
        "Va": np.array([[5.0], [5.0], [5.0]]),
        "M": np.array([100.0, 101.0, 9_999.0]),
    }
    report = simulate(Schedule([10.0, 0.0]), book, {"phi": 1.0})
    assert report.shortfall_bps < 1_000.0


@pytest.mark.T9
def test_t9_snapshots_after_horizon_are_not_read():
    book = {
        "Pa": np.array([[101.0], [102.0], [np.nan]]),
        "Va": np.array([[5.0], [5.0], [5.0]]),
        "M": np.array([100.0, 101.0, np.nan]),
    }
    simulate(Schedule([10.0, 0.0]), book, {"phi": 1.0})
