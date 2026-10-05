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
) -> tuple[cp.Problem, cp.Variable, cp.Variable, cp.Expression, list[cp.Constraint]]:
    """
    Build M2 model (Limit Order Book LP when lam=0, or QP when lam>0).
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
    q = cp.Variable((T, L), nonneg=True, name="fill_by_level")
    y = cp.Variable(T + 1, nonneg=True, name="inventory")

    # Execution per step across all book levels
    x = cp.sum(q, axis=1)

    constraints: list[cp.Constraint] = [
        y[0] == Q,
        y[T] == 0,
        q <= Va[:T, :],
        y[1:] == y[:-1] - x,
        x <= rho * Da_net[:T],
    ]

    # Spread cost relative to mid-price: (Pa - mid) * q
    cost_per_share = Pa[:T, :] - mid[:T, np.newaxis]
    spread_cost = cp.sum(cp.multiply(cost_per_share, q))

    # Variance risk penalty on remaining inventory
    if lam > 0:
        variance_cost = lam * cp.sum(cp.multiply(sigma2[1:T], cp.square(y[1:T])))
        total_cost = spread_cost + variance_cost
    else:
        total_cost = spread_cost

    prob = cp.Problem(cp.Minimize(total_cost), constraints)
    return prob, q, y, x, constraints


def solve_m2(
    order: Order,
    book: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """
    Solve M2 LOB optimization model and return execution Schedule.
    Uses multi-solver fallback (HIGHS -> CLARABEL -> OSQP) to prevent user_limit errors.
    """
    if order.size <= 0 or order.horizon < 1:
        raise ValueError(
            f"Invalid order specifications: size={order.size}, horizon={order.horizon}"
        )

    for req_key in ("Pa", "Va", "M", "Da"):
        if req_key not in book:
            raise KeyError(f"Market book missing required key '{req_key}'")

    p = params or {}
    Q = float(order.size)
    T = int(order.horizon)
    lam = float(p.get("lambda_imp", 0.0))
    rho = float(p.get("rho", 1.0))

    Pa = np.asarray(book["Pa"], dtype=float)
    Va = np.asarray(book["Va"], dtype=float)
    mid = np.asarray(book["M"], dtype=float)
    Da = np.asarray(book["Da"], dtype=float)

    if Pa.shape[0] < T or Va.shape[0] < T or len(mid) < T or len(Da) < T:
        raise ValueError(f"Market book arrays must have at least {T} rows")

    sigma2 = np.asarray(p.get("sigma2", np.zeros(T)), dtype=float)
    if len(sigma2) < T:
        sigma2 = np.zeros(T, dtype=float)

    prob, q, y, x, constraints = build_m2(
        Q=Q,
        T=T,
        Pa=Pa,
        Va=Va,
        mid=mid,
        sigma2=sigma2,
        lam=lam,
        rho=rho,
        Da_net=Da,
    )

    # Multi-solver cascade: HiGHS (exact for LP/QP) -> CLARABEL -> OSQP
    solved = False
    for s in (cp.HIGHS, cp.CLARABEL):
        try:
            prob.solve(solver=s)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and x.value is not None:
                solved = True
                break
        except Exception:
            continue

    if not solved:
        try:
            prob.solve(solver=cp.OSQP, max_iter=20000, eps_abs=1e-3, eps_rel=1e-3)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and x.value is not None:
                solved = True
        except Exception:
            pass

    if not solved or x.value is None:
        if "infeasible" in str(prob.status).lower():
            raise RuntimeError(
                f"M2 optimization is infeasible (status={prob.status}). "
                f"Order size ({Q:.0f}) exceeds available depth capacity with participation "
                f"cap rho={rho:.2f} over horizon T={T}."
            )
        raise RuntimeError(f"M2 optimization failed: status={prob.status}")

    trades = np.asarray(x.value, dtype=float)
    trades = np.maximum(trades, 0.0)

    # Clean slight numerical residual to match exact order size
    sum_trades = np.sum(trades)
    trades = trades * (Q / sum_trades) if sum_trades > 0 else np.full(T, Q / T, dtype=float)

    return Schedule(shares=trades)
