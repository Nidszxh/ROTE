import numpy as np

from src.evaluation import bootstrap_mean_ci, evaluate, holm_correction
from src.models.m4_ahp import solve_m4
from src.utils.contracts import Order


def _book(n=40):
    return {
        "Pa": np.full((n, 2), 101.0),
        "Va": np.full((n, 2), 100.0),
        "M": np.full(n, 100.0),
        "Da": np.full(n, 200.0),
    }


def test_evaluation_covers_stocks_windows_theta_and_ci(monkeypatch):
    calls = []

    def calibrated(pa, va):
        calls.append((pa.shape, va.shape))
        return {"eta0": 0.25}

    monkeypatch.setattr("src.evaluation.core.calibrate_eta0_for_stock", calibrated)
    result = evaluate(
        {"A": _book(), "B": _book()},
        {"validation": [slice(0, 20), slice(10, 30)]},
        theta=[0.5, 1.0],
        bootstrap_reps=20,
        bootstrap_block=2,
    )
    assert set(result.observations.stock) == {"A", "B"}
    assert set(result.observations.theta) == {0.5, 1.0}
    assert result.summary[["ci_low", "ci_high"]].notna().all().all()
    assert "p_adjusted" in result.comparisons
    assert len(calls) == 2


def test_bootstrap_and_holm_are_deterministic():
    assert bootstrap_mean_ci([1, 2, 3], reps=100, seed=7) == bootstrap_mean_ci(
        [1, 2, 3], reps=100, seed=7
    )
    corrected = holm_correction({"a": 0.01, "b": 0.04})
    assert corrected.loc[corrected.comparison == "a", "p_adjusted"].item() == 0.02


def test_m4_selects_four_criterion_candidates():
    order = Order("buy", 100.0, 2, {})
    schedule = solve_m4(
        order,
        params={
            "candidate_schedules": {"early": [80, 20], "late": [20, 80]},
            "candidate_criteria": {
                "early": [1.0, 2.0, 3.0, 4.0],
                "late": [2.0, 1.0, 2.0, 3.0],
            },
            "criteria_matrix": np.ones((4, 4)),
        },
    )
    np.testing.assert_allclose(schedule.shares, [80.0, 20.0])
