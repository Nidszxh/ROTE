from __future__ import annotations

import numpy as np

from src.benchmarks.baselines import depth_proportional_plan, twap_plan, vwap_proxy_plan
from src.loader.loader import STOCK_NAMES, load_day
from src.models.m1_ac import solve_m1
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio, ahp_weights, solve_m4
from src.sim.simulate import simulate
from src.stats.stats import compute_statistics
from src.utils.contracts import Order


def test_end_to_end_pipeline():
    """Verify entire pipeline: loader -> stats -> all models -> simulate -> AHP."""
    # 1. Load data
    stock = STOCK_NAMES[0]
    book, day, is_measured = load_day(stock, 1)
    assert len(book["M"]) > 0
    assert "Pa" in book and "Va" in book and "Da" in book and "Db" in book

    # 2. Statistics
    stats = compute_statistics(book)
    assert "avg_half_spread_bps" in stats
    assert "avg_depth_ask" in stats
    assert "volatility_bps_per_period" in stats
    assert stats["avg_half_spread_bps"] > 0

    # 3. Order setup
    order = Order(side="buy", size=500.0, horizon=10, params={})

    # 4. Solvers & Baselines
    schedules = {
        "M1": solve_m1(order, book, {"lambda_imp": 1e-4}),
        "M2": solve_m2(order, book, {"rho": 1.0, "lambda_imp": 0.0}),
        "M3": solve_m3(order, book, {"rho": 1.0, "c_f": 5.0, "L_min": 20.0}),
        "M4": solve_m4(order, book, {}),
        "TWAP": twap_plan(order),
        "Depth": depth_proportional_plan(order, book),
        "VWAP": vwap_proxy_plan(order, book),
    }

    # Verify each schedule
    for name, sched in schedules.items():
        assert len(sched.shares) == 10, f"{name} length mismatch"
        assert np.all(sched.shares >= -1e-6), f"{name} contains negative shares"
        np.testing.assert_allclose(
            np.sum(sched.shares), 500.0, atol=1e-3, err_msg=f"{name} sum mismatch"
        )

        # 5. Simulate
        report = simulate(sched, book, {"rho": 1.0, "phi": 0.5, "pi": 1.0})
        assert np.isfinite(report.shortfall_bps), f"{name} shortfall is not finite"
        assert np.isfinite(report.std), f"{name} std is not finite"
        assert report.trades >= 1, f"{name} trades < 1"

    # 6. AHP Decision
    matrix = np.array(
        [
            [1.0, 2.0, 0.5],
            [0.5, 1.0, 0.25],
            [2.0, 4.0, 1.0],
        ]
    )
    cr, is_consistent = ahp_consistency_ratio(matrix)
    assert is_consistent
    assert cr < 0.05
    weights = ahp_weights(matrix)
    assert len(weights) == 3
    np.testing.assert_allclose(np.sum(weights), 1.0)
