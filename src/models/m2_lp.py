from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cvxpy as cp
import numpy as np

from src.utils.contracts import Order, Schedule


def build_m2(
    Q: float,
    T: int,
    Pa: np.ndarray,
    Va: np.ndarray,
    mid: np.ndarray,
    sigma2: np.ndarray,
    lam: float,
    rho: float,
    Da_net: np.ndarray,
    psi: float | None = None,
    allow_sweep: bool = True,
) -> tuple[cp.Problem, cp.Variable, cp.Variable, cp.Expression, list[cp.Constraint]]:
    """Build M2 model (Limit Order Book LP when lam=0, or QP when lam>0).

    Uses dimensionless formulation (PROPOSAL.md section 5.3) for numerical conditioning.
    q_tilde = q / Q, y_tilde = y / Q, x_tilde = x / Q.
    """
    if Q <= 0:
        raise ValueError(f"Order size Q must be positive, got {Q}")
    if T < 1:
        raise ValueError(f"Horizon T must be >= 1, got {T}")
    if rho <= 0:
        raise ValueError(f"Participation rate rho must be positive, got {rho}")
    if lam < 0:
        raise ValueError(f"Risk parameter lambda must be non-negative, got {lam}")

    L = Pa.shape[1]
    M0 = float(mid[0]) if (len(mid) > 0 and mid[0] > 0) else 100.0

    q_tilde = cp.Variable((T, L), nonneg=True, name="fill_by_level")
    y_tilde = cp.Variable(T + 1, nonneg=True, name="inventory")
    x_tilde = cp.sum(q_tilde, axis=1)

    Va_norm = Va[:T, :] / Q
    cap_norm = (rho * Da_net[:T]) / Q

    constraints: list[cp.Constraint] = [
        y_tilde[0] == 1.0,
        q_tilde <= Va_norm,
        y_tilde[1:] == y_tilde[:-1] - x_tilde,
        x_tilde <= cap_norm,
    ]

    if not allow_sweep:
        constraints.append(y_tilde[T] == 0.0)

    # Normalized spread cost relative to arrival mid
    cost_per_share_norm = (Pa[:T, :] - mid[:T, np.newaxis]) / M0
    spread_cost = cp.sum(cp.multiply(cost_per_share_norm, q_tilde))

    # Variance risk penalty on remaining inventory (dimensionless)
    sigma2_norm = sigma2[:T] / (M0**2)
    if lam > 0 and np.any(sigma2_norm > 0):
        variance_cost = lam * cp.sum(cp.multiply(sigma2_norm[1:T], cp.square(y_tilde[1:T])))
    else:
        variance_cost = 0.0

    # Terminal sweep cost
    if allow_sweep:
        if psi is None:
            P_max = float(Pa[0, -1]) if Pa.shape[1] > 0 else M0 * 1.01
            psi = max(P_max * 1.005 - M0, 0.01 * M0)
        psi_norm = psi / M0
        sweep_cost = psi_norm * y_tilde[T]
    else:
        sweep_cost = 0.0

    total_cost = spread_cost + variance_cost + sweep_cost
    prob = cp.Problem(cp.Minimize(total_cost), constraints)
    return prob, q_tilde, y_tilde, x_tilde, constraints


def solve_m2(
    order: Order,
    book: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """Solve M2 LOB optimization model and return execution Schedule."""
    if order.size <= 0 or order.horizon < 1:
        raise ValueError(
            f"Invalid order specifications: size={order.size}, horizon={order.horizon}"
        )

    for req_key in ("Pa", "Va", "M", "Da"):
        if req_key not in book:
            raise KeyError(f"Market book missing required key '{req_key}'")

    p = dict(params or {})
    Q = float(order.size)
    T = int(order.horizon)
    lam = float(p.get("lambda_imp", 0.0))
    rho = float(p.get("rho", 1.0))
    allow_sweep = bool(p.get("allow_sweep", True))

    Pa = np.asarray(book["Pa"], dtype=float)
    Va = np.asarray(book["Va"], dtype=float)
    mid = np.asarray(book["M"], dtype=float)
    Da = np.asarray(book["Da"], dtype=float)

    if Pa.shape[0] < T or Va.shape[0] < T or len(mid) < T or len(Da) < T:
        raise ValueError(f"Market book arrays must have at least {T} rows")

    sigma2 = np.asarray(p.get("sigma2", np.zeros(T)), dtype=float)
    if len(sigma2) < T:
        sigma = float(p.get("sigma", 0.0))
        sigma2 = np.full(T, sigma**2, dtype=float)

    psi = p.get("psi")
    if psi is not None:
        psi = float(psi)

    prob, q_tilde, y_tilde, x_tilde, constraints = build_m2(
        Q=Q,
        T=T,
        Pa=Pa,
        Va=Va,
        mid=mid,
        sigma2=sigma2,
        lam=lam,
        rho=rho,
        Da_net=Da,
        psi=psi,
        allow_sweep=allow_sweep,
    )

    # Multi-solver with fast timeouts
    solved = False
    for s in (cp.HIGHS, cp.CLARABEL):
        try:
            prob.solve(solver=s)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and x_tilde.value is not None:
                solved = True
                break
        except Exception:
            continue

    if not solved:
        try:
            prob.solve(solver=cp.OSQP, max_iter=10000, eps_abs=1e-4, eps_rel=1e-4)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and x_tilde.value is not None:
                solved = True
        except Exception:
            pass

    if not solved or x_tilde.value is None:
        if "infeasible" in str(prob.status).lower():
            raise RuntimeError(
                f"M2 optimization is infeasible (status={prob.status}). "
                f"Order size ({Q:.0f}) exceeds available depth capacity with participation "
                f"cap rho={rho:.2f} over horizon T={T}."
            )
        raise RuntimeError(f"M2 optimization failed: status={prob.status}")

    trades = np.asarray(x_tilde.value, dtype=float) * Q
    trades = np.maximum(trades, 0.0)

    # Invariant: sum(Schedule.shares) == Q
    residual = Q - float(np.sum(trades))
    if abs(residual) > 1e-4:
        trades[-1] += residual

    schedule = Schedule(shares=np.maximum(trades, 0.0))

    # Attach duals for diagnostic inspection (T15, shadow prices)
    try:
        cap_duals = [float(c.dual_value) for c in constraints if c.shape == (T,)]
        schedule.capacity_duals = cap_duals
    except Exception:
        pass

    return schedule
