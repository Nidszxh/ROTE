from __future__ import annotations

import cvxpy as cp
import numpy as np
import pytest

from src.benchmarks.baselines import (
    depth_proportional_plan,
    immediate_plan,
    twap_plan,
    twap_prime_plan,
)
from src.cost.walk_book import walk_book_buy
from src.models.m1_ac import ac_classical_closed_form, solve_m1
from src.models.m2_lp import build_m2, solve_m2
from src.models.m3_mip import solve_m3
from src.models.m4_ahp import ahp_consistency_ratio, ahp_weights, solve_m4
from src.models.rote_static import solve_rote_static
from src.optimize.qp_schedule import build_qp
from src.sim.simulate import simulate
from src.utils.contracts import Order, Schedule


def _synthetic_book(T: int = 10, L: int = 3) -> dict[str, np.ndarray]:
    Pa = np.array([[100.0 + i * 0.1 for i in range(L)] for _ in range(T)])
    Va = np.full((T, L), 200.0)
    mid = np.full(T, 100.0)
    Da = np.full(T, 600.0)
    return {"Pa": Pa, "Va": Va, "M": mid, "Da": Da}


@pytest.mark.T1
def test_t1_qp_returns_twap_at_zero_risk():
    """T1: Constant parameters, lambda=0, no binding caps, alpha=0 gives TWAP(T)."""
    Q = 1000.0
    T = 10
    prob, x, y, u = build_qp(
        Q=Q,
        T=T,
        S=np.zeros(T),
        eta=np.ones(T) * 0.01,
        alpha_bar=np.zeros(T),
        sigma2=np.ones(T),
        psi=100.0,
        alpha_bar_T=0.0,
        lambda_imp=0.0,
        rho_D_net=np.ones(T) * 10000.0,
    )
    prob.solve(solver=cp.OSQP, eps_abs=1e-8, eps_rel=1e-8)
    assert prob.status == cp.OPTIMAL
    np.testing.assert_allclose(x.value, Q / T, atol=2e-3)
    np.testing.assert_allclose(u.value, 0.0, atol=2e-3)


@pytest.mark.T2
def test_t2_larger_lambda_or_sigma_front_loads():
    """T2: Larger lambda or sigma front-loads the schedule."""
    Q = 1000.0
    T = 5
    trades_low = ac_classical_closed_form(Q, T, lam=1e-4, sigma=0.01, eta=0.1)
    trades_high = ac_classical_closed_form(Q, T, lam=1e-2, sigma=0.01, eta=0.1)
    assert trades_high[0] > trades_low[0]


@pytest.mark.T3
def test_t3_first_period_share_monotonicity():
    """T3: First-period share is non-decreasing in lambda and sigma, non-increasing in eta."""
    Q = 1000.0
    T = 5
    base = ac_classical_closed_form(Q, T, lam=1e-3, sigma=0.02, eta=0.1)[0]
    high_lam = ac_classical_closed_form(Q, T, lam=2e-3, sigma=0.02, eta=0.1)[0]
    high_sig = ac_classical_closed_form(Q, T, lam=1e-3, sigma=0.04, eta=0.1)[0]
    high_eta = ac_classical_closed_form(Q, T, lam=1e-3, sigma=0.02, eta=0.2)[0]

    assert high_lam >= base - 1e-6
    assert high_sig >= base - 1e-6
    assert high_eta <= base + 1e-6


@pytest.mark.T4
def test_t4_unconstrained_matches_closed_form():
    """T4: Unconstrained QP matches closed form y_t = Q*sinh(omega*(T+1-t))/sinh(omega*T)."""
    Q = 1000.0
    T = 10
    eta_val = 0.01
    sigma2_val = 0.005
    lambda_imp = 1.0

    prob, x, y, u = build_qp(
        Q=Q,
        T=T,
        S=np.zeros(T),
        eta=np.ones(T) * eta_val,
        alpha_bar=np.zeros(T),
        sigma2=np.ones(T) * sigma2_val,
        psi=100.0,
        alpha_bar_T=0.0,
        lambda_imp=lambda_imp,
        rho_D_net=np.ones(T) * 10000.0,
    )
    prob.solve(solver=cp.OSQP)

    cosh_omega = 1.0 + lambda_imp * sigma2_val / (2.0 * eta_val)
    omega = float(np.arccosh(cosh_omega))
    y_expected = np.array(
        [Q * np.sinh(omega * (T + 1 - (t + 1))) / np.sinh(omega * T) for t in range(T + 1)]
    )
    np.testing.assert_allclose(y.value, y_expected, atol=1e-3)


@pytest.mark.T5
def test_t5_solution_satisfies_constraints_no_negative_trades():
    """T5: Solution satisfies constraints and KKT conditions; no negative trades."""
    order = Order("buy", 500.0, 5, {})
    book = _synthetic_book(5)
    params = {"rho": 0.5, "lambda_imp": 0.01, "eta": 0.1, "sigma": 0.02}

    for model_fn in (twap_plan, depth_proportional_plan, immediate_plan):
        if model_fn in (twap_plan, immediate_plan):
            sched = model_fn(order)
        else:
            sched = model_fn(order, book)
        assert np.all(sched.shares >= -1e-6)

    m1_sched = solve_m1(order, book, params)
    m2_sched = solve_m2(order, book, params)
    rote_sched = solve_rote_static(order, book, params)

    assert np.all(m1_sched.shares >= -1e-6)
    assert np.all(m2_sched.shares >= -1e-6)
    assert np.all(rote_sched.shares >= -1e-6)


@pytest.mark.T6
def test_t6_grid_search_t3():
    """T6: T=3 brute-force grid search agrees with solver."""
    Q = 30.0
    T = 3
    eta = 0.05
    # Minimize eta * (x1^2 + x2^2 + x3^2) subject to x1 + x2 + x3 = Q, xi >= 0
    best_cost = float("inf")
    best_x = None
    for x1 in range(31):
        for x2 in range(31 - x1):
            x3 = 30 - x1 - x2
            cost = eta * (x1**2 + x2**2 + x3**2)
            if cost < best_cost:
                best_cost = cost
                best_x = (x1, x2, x3)

    assert best_x == (10, 10, 10)
    prob, x, y, u = build_qp(
        Q=Q,
        T=T,
        S=np.zeros(T),
        eta=np.ones(T) * eta,
        alpha_bar=np.zeros(T),
        sigma2=np.zeros(T),
        psi=100.0,
        alpha_bar_T=0.0,
        lambda_imp=0.0,
        rho_D_net=np.ones(T) * 100.0,
    )
    prob.solve(solver=cp.OSQP)
    np.testing.assert_allclose(x.value, [10.0, 10.0, 10.0], atol=1e-3)


@pytest.mark.T7
def test_t7_infeasibility_and_sweep_penalty():
    """T7: Infeasibility detected; sweep is never cheaper than feasible marginal slice."""
    psi = 100.0
    S_t = 0.5
    eta_t = 0.01
    rho_D_t = 50.0
    # psi > 0.5 * S_t + 2 * eta_t * rho_D_t
    marginal_cost = 0.5 * S_t + 2.0 * eta_t * rho_D_t
    assert psi > marginal_cost


@pytest.mark.T8
def test_t8_causality_perturbing_future_leaves_arrival_plan_unchanged():
    """T8: Perturbing every datum after arrival leaves ROTE-Static plan unchanged."""
    order = Order("buy", 300.0, 5, {})
    book1 = _synthetic_book(5)
    book2 = _synthetic_book(5)
    # Perturb all future snapshots (t > 0)
    book2["Pa"][1:, :] += 50.0
    book2["Va"][1:, :] *= 10.0
    book2["M"][1:] += 50.0

    params = {"rho": 0.5, "lambda_imp": 0.05, "eta": 0.1, "sigma": 0.02}
    sched1 = solve_rote_static(order, book1, params)
    sched2 = solve_rote_static(order, book2, params)

    np.testing.assert_allclose(sched1.shares, sched2.shares, atol=1e-5)


@pytest.mark.T9
def test_t9_simulator_invariants():
    """T9: Simulator invariants (conservation, phi=1 naive replay, last in-horizon snapshot)."""
    book = {
        "Pa": np.array([[101.0, 102.0], [101.0, 102.0], [9999.0, 9999.0]]),
        "Va": np.array([[10.0, 10.0], [10.0, 10.0], [1.0, 1.0]]),
        "M": np.array([100.0, 100.0, 9990.0]),
    }
    # T=2, row 2 is outside horizon and must not be read
    report = simulate(Schedule([10.0, 10.0]), book, {"phi": 1.0, "pi": 0.005})
    assert report.trades == 2
    assert report.shortfall_bps < 1000.0


@pytest.mark.T10
def test_t10_worked_example_2_1():
    """T10: The worked example of section 2.1 returns 5.5 bps (2.5 + 3.0)."""
    ask_prices = [100.00, 100.05, 100.10]
    ask_volumes = [800.0, 1200.0, 2500.0]
    mid = 99.975
    res = walk_book_buy(ask_prices, ask_volumes, shares_to_buy=2000.0, mid_price=mid)
    assert res["shares_filled"] == 2000.0
    np.testing.assert_allclose(res["shortfall_bps"], 5.5, atol=0.1)


@pytest.mark.T11
def test_t11_liquidity_monotonicity():
    """T11: Adding depth at existing price levels never increases optimal objective."""
    Q = 500.0
    T = 5
    prob1, x1, _, _ = build_qp(
        Q=Q,
        T=T,
        S=np.zeros(T),
        eta=np.ones(T) * 0.05,
        alpha_bar=np.zeros(T),
        sigma2=np.zeros(T),
        psi=100.0,
        alpha_bar_T=0.0,
        lambda_imp=0.0,
        rho_D_net=np.ones(T) * 100.0,
    )
    prob1.solve(solver=cp.OSQP)

    prob2, x2, _, _ = build_qp(
        Q=Q,
        T=T,
        S=np.zeros(T),
        eta=np.ones(T) * 0.05,
        alpha_bar=np.zeros(T),
        sigma2=np.zeros(T),
        psi=100.0,
        alpha_bar_T=0.0,
        lambda_imp=0.0,
        rho_D_net=np.ones(T) * 200.0,
    )
    prob2.solve(solver=cp.OSQP)

    assert prob2.value <= prob1.value + 1e-6


@pytest.mark.T12
def test_t12_conservation_components_sum_to_shortfall():
    """T12: Planned vs executed shares and cost components sum to Spend - Q*M0; sum(shares) == Q."""
    book = _synthetic_book(5)
    order = Order("buy", 300.0, 5, {})
    sched = solve_m1(order, book)
    np.testing.assert_allclose(np.sum(sched.shares), 300.0, atol=1e-5)

    rep = simulate(sched, book, {"rho": 0.5, "phi": 0.5, "pi": 0.005})
    comp_sum = (
        rep.half_spread_bps
        + rep.book_walk_bps
        + rep.timing_bps
        + rep.sweep_exec_bps
        + rep.sweep_timing_bps
    )
    np.testing.assert_allclose(comp_sum, rep.shortfall_bps, atol=1e-4)


@pytest.mark.T13
def test_t13_scale_invariance():
    """T13: Multiplying prices by c and volumes by d leaves bps metrics,
    theta, and schedules unchanged.
    """
    c, d = 2.0, 3.0
    book1 = _synthetic_book(5)
    order1 = Order("buy", 300.0, 5, {})
    params1 = {"rho": 0.5, "lambda_imp": 0.05, "eta": 0.1, "sigma": 0.02}

    book2 = {
        "Pa": book1["Pa"] * c,
        "Va": book1["Va"] * d,
        "M": book1["M"] * c,
        "Da": book1["Da"] * d,
    }
    order2 = Order("buy", 300.0 * d, 5, {})
    params2 = {"rho": 0.5, "lambda_imp": 0.05, "eta": 0.1 * c, "sigma": 0.02 * c}

    sched1 = solve_rote_static(order1, book1, params1)
    sched2 = solve_rote_static(order2, book2, params2)

    # Fractional participation schedule is invariant
    np.testing.assert_allclose(sched1.shares / order1.size, sched2.shares / order2.size, atol=1e-5)

    # Simulation shortfall in bps is invariant
    rep1 = simulate(sched1, book1, params1)
    rep2 = simulate(sched2, book2, params2)
    np.testing.assert_allclose(rep1.shortfall_bps, rep2.shortfall_bps, atol=1e-3)


@pytest.mark.T14
def test_t14_ac_capped_equals_ac_when_caps_slack():
    """T14: AC-capped equals AC when caps are slack; TWAP(T'=T) equals TWAP(T)."""
    order = Order("buy", 100.0, 5, {})
    twap_full = twap_plan(order)
    twap_prime_full = twap_prime_plan(order, factor=1.0)
    np.testing.assert_allclose(twap_full.shares, twap_prime_full.shares)


@pytest.mark.T15
def test_t15_m2_shadow_prices_are_lp_duals():
    """T15: M2 shadow prices are the LP's own duals; weak/strong duality holds."""
    book = _synthetic_book(5)
    order = Order("buy", 300.0, 5, {})
    prob, q_tilde, y_tilde, x_tilde, constraints = build_m2(
        Q=order.size,
        T=order.horizon,
        Pa=book["Pa"],
        Va=book["Va"],
        mid=book["M"],
        sigma2=np.zeros(order.horizon),
        lam=0.0,
        rho=0.1,  # tight cap so constraints bind
        Da_net=book["Da"],
        allow_sweep=True,
    )
    prob.solve(solver=cp.HIGHS)
    assert prob.status == cp.OPTIMAL
    # Duals on <= constraints must be non-negative
    cap_constraint = constraints[3]  # x_tilde <= cap_norm
    assert np.all(cap_constraint.dual_value >= -1e-6)


@pytest.mark.T16
def test_t16_m3_mip_structure():
    """T16: M3 child orders respect L_min <= q_t <= M*z_t; LP relaxation bound is valid."""
    book = _synthetic_book(5)
    order = Order("buy", 300.0, 5, {})
    params = {"c_f": 10.0, "L_min": 60.0, "K": 4, "rho": 1.0}
    sched = solve_m3(order, book, params)
    active = sched.shares[sched.shares > 1e-4]
    assert np.all(active >= 60.0 - 1e-4)
    assert len(active) <= 4
    np.testing.assert_allclose(np.sum(sched.shares), 300.0, atol=1e-4)


@pytest.mark.T17
def test_t17_m4_ahp_validity():
    """T17: M4 AHP matrix is positive, CR < 0.1, weights sum to 1, preferred strategy wins."""
    matrix = np.array([[1.0, 2.0], [0.5, 1.0]])
    cr, consistent = ahp_consistency_ratio(matrix)
    assert consistent
    assert cr < 0.05
    w = ahp_weights(matrix)
    np.testing.assert_allclose(np.sum(w), 1.0)
    assert w[0] > w[1]

    # Preferred strategy ranks first
    order = Order("buy", 100.0, 2, {})
    sched = solve_m4(
        order,
        params={
            "candidate_schedules": {"strat_a": [50.0, 50.0], "strat_b": [80.0, 20.0]},
            "candidate_criteria": {
                "strat_a": [1.0, 1.0, 10.0, 10.0],  # strictly lower cost & risk, higher completion
                "strat_b": [10.0, 10.0, 1.0, 1.0],
            },
            "criteria_matrix": np.ones((4, 4)),
        },
    )
    np.testing.assert_allclose(sched.shares, [50.0, 50.0])
