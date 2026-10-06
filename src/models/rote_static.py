from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cvxpy as cp
import numpy as np

from src.cost.units import eta0_tilde, sigma_tilde
from src.utils.contracts import Order, Schedule


def solve_rote_static(
    order: Order,
    book: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """Solve ROTE-Static arrival-state convex QP (PROPOSAL.md section 6.2/6.3).

    All parameters are frozen at arrival state (t=0).
    Uses dimensionless formulation (PROPOSAL.md section 5.3) for numerical stability.
    """
    if order.size <= 0:
        raise ValueError(f"Order size must be positive, got {order.size}")
    if order.horizon < 1:
        raise ValueError(f"Order horizon must be >= 1, got {order.horizon}")

    for req in ("Pa", "Va", "M", "Da"):
        if req not in book:
            raise KeyError(f"Market book missing required key '{req}'")

    p = dict(params or {})
    Q = float(order.size)
    T = int(order.horizon)

    Pa = np.asarray(book["Pa"], dtype=float)
    mid = np.asarray(book["M"], dtype=float)
    Da = np.asarray(book["Da"], dtype=float)

    if Pa.shape[0] < T or len(mid) < T or len(Da) < T:
        raise ValueError(f"Market book arrays must have at least {T} rows")

    M0 = float(mid[0])
    if M0 <= 0:
        raise ValueError("Arrival mid-price must be positive")

    # Arrival state (frozen)
    P_max_arr = float(Pa[0, -1])
    pi = float(p.get("pi", 0.005))
    psi = max(P_max_arr * (1.0 + pi) - M0, 1e-4)

    D_arr = float(Da[0]) if Da[0] > 0 else 1.0
    D_bar = float(p.get("D_bar", p.get("median_depth", D_arr)))
    if D_bar <= 0:
        D_bar = D_arr
    theta = Q / D_bar if D_bar > 0 else 1.0

    rho = float(p.get("rho", 0.25))
    eta0 = float(p.get("eta0", p.get("eta", 0.1)))
    sigma = float(p.get("sigma", 0.015))
    if sigma <= 0:
        sigma = 1e-4

    # Dimensionless conversions
    eta0_t = eta0_tilde(eta0, M0)
    sigma_t = sigma_tilde(sigma, M0)

    # Risk parameter: omega priority over lambda_imp
    if "omega" in p:
        omega = float(p["omega"])
        # cosh(omega) = 1 + lambda_imp * sigma_t^2 / (2 * eta0_t * theta)
        cosh_om = float(np.cosh(omega))
        denom = sigma_t**2 if sigma_t > 0 else 1e-8
        lam_imp = 2.0 * (cosh_om - 1.0) * (eta0_t * theta) / denom
    else:
        lam_imp = float(p.get("lambda_imp", 0.0))

    # Spread term (half-spread relative to M0)
    S_arr = float(Pa[0, 0] - mid[0]) * 2.0
    if "S" in book and len(book["S"]) > 0:
        S_arr = float(book["S"][0])
    half_spread_norm = 0.5 * (S_arr / M0)

    # Impact term: eta_t = eta0 / D_arr in raw, eta0_t * (Q / D_arr) in xi
    eta_xi = eta0_t * (Q / D_arr)
    psi_norm = psi / M0

    # Decision variables in dimensionless space: xi_t = x_t / Q, y_norm = y / Q
    xi = cp.Variable(T, nonneg=True, name="fractional_shares")
    y_norm = cp.Variable(T + 1, nonneg=True, name="fractional_inventory")
    u_norm = y_norm[T]

    cap_xi = rho * (D_arr / Q)
    constraints = [
        y_norm[0] == 1.0,
        y_norm[1:] == y_norm[:-1] - xi,
        xi <= cap_xi,
    ]

    # Objective
    cost = cp.sum(half_spread_norm * xi) + eta_xi * cp.sum_squares(xi)
    if lam_imp > 0 and sigma_t > 0:
        cost += lam_imp * (sigma_t**2) * cp.sum_squares(y_norm[1:T])
    cost += psi_norm * u_norm

    problem = cp.Problem(cp.Minimize(cost), constraints)

    # Solve with fast convex solver
    solved = False
    for s in (cp.OSQP, cp.CLARABEL, cp.HIGHS):
        try:
            problem.solve(solver=s)
            if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and xi.value is not None:
                solved = True
                break
        except Exception:
            continue

    if not solved or xi.value is None:
        return Schedule(np.full(T, Q / T, dtype=float))

    shares = np.asarray(xi.value, dtype=float) * Q
    shares = np.maximum(shares, 0.0)

    # Invariant: sum(Schedule.shares) == Q
    residual = Q - float(np.sum(shares))
    if abs(residual) > 1e-4:
        shares[-1] += residual

    return Schedule(shares=np.maximum(shares, 0.0))
