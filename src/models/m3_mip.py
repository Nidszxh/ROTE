from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cvxpy as cp
import numpy as np

from src.utils.contracts import Order, Schedule


def build_m3(
    Q: float,
    T: int,
    Pa: np.ndarray,
    Va: np.ndarray,
    mid: np.ndarray,
    rho: float,
    Da_net: np.ndarray,
    L_min: float,
    c_f: float,
    K: int | None = None,
) -> tuple[cp.Problem, cp.Variable, cp.Variable, cp.Expression, cp.Variable]:
    """
    Build M3 Mixed-Integer Programming (MIP) execution model with fixed costs and lot constraints.

    Parameters
    ----------
    Q : float
        Total order quantity to liquidate.
    T : int
        Horizon steps.
    Pa : np.ndarray
        Ask prices, shape (>=T, L).
    Va : np.ndarray
        Ask depths, shape (>=T, L).
    mid : np.ndarray
        Mid-prices, shape (>=T,).
    rho : float
        Participation factor constraint (0 < rho <= 1.0).
    Da_net : np.ndarray
        Net ask depth, shape (>=T,).
    L_min : float
        Minimum trade size if step is active (L_min >= 0).
    c_f : float
        Fixed charge per executed trade (c_f >= 0).
    K : int | None, optional
        Maximum allowed number of trades (cardinality constraint).

    Returns
    -------
    tuple
        (problem, q_var, y_var, x_expr, z_var)
    """
    if Q <= 0:
        raise ValueError(f"Order quantity Q must be positive, got {Q}")
    if T < 1:
        raise ValueError(f"Horizon T must be >= 1, got {T}")
    if rho <= 0:
        raise ValueError(f"Participation rate rho must be positive, got {rho}")
    if L_min < 0:
        raise ValueError(f"Minimum lot L_min must be non-negative, got {L_min}")
    if c_f < 0:
        raise ValueError(f"Fixed charge c_f must be non-negative, got {c_f}")
    if K is not None and K < 1:
        raise ValueError(f"Cardinality limit K must be at least 1, got {K}")

    L = Pa.shape[1]
    q = cp.Variable((T, L), nonneg=True, name="fill_by_level")
    y = cp.Variable(T + 1, nonneg=True, name="inventory")
    z = cp.Variable(T, boolean=True, name="trade_indicator")

    x = cp.sum(q, axis=1)

    constraints: list[cp.Constraint] = [
        y[0] == Q,
        y[T] == 0,
        q <= Va[:T, :],
        y[1:] == y[:-1] - x,
        x <= rho * Da_net[:T],
        x <= Q * z,  # Big-M upper bound
    ]

    if L_min > 0:
        constraints.append(x >= L_min * z)

    if K is not None:
        constraints.append(cp.sum(z) <= K)

    # Cost: spread cost + fixed transaction fee per active step
    cost_per_share = Pa[:T, :] - mid[:T, np.newaxis]
    total_cost = cp.sum(cp.multiply(cost_per_share, q)) + c_f * cp.sum(z)

    prob = cp.Problem(cp.Minimize(total_cost), constraints)
    return prob, q, y, x, z


def solve_m3(
    order: Order,
    book: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """
    Solve M3 MIP execution problem and return Schedule.
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
    rho = float(p.get("rho", 1.0))
    L_min = float(p.get("L_min", 0.0))
    c_f = float(p.get("c_f", 0.0))
    K = int(p["K"]) if p.get("K") is not None else None

    Pa = np.asarray(book["Pa"], dtype=float)
    Va = np.asarray(book["Va"], dtype=float)
    mid = np.asarray(book["M"], dtype=float)
    Da = np.asarray(book["Da"], dtype=float)

    if Pa.shape[0] < T or Va.shape[0] < T or len(mid) < T or len(Da) < T:
        raise ValueError(f"Market book arrays must have at least {T} rows")

    prob, q, y, x, z = build_m3(
        Q=Q,
        T=T,
        Pa=Pa,
        Va=Va,
        mid=mid,
        rho=rho,
        Da_net=Da,
        L_min=L_min,
        c_f=c_f,
        K=K,
    )

    prob.solve(solver=cp.HIGHS)

    if prob.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) or x.value is None:
        raise RuntimeError(
            f"M3 MIP optimization failed with status '{prob.status}'. "
            f"Parameters (Q={Q}, L_min={L_min}, K={K}) may be infeasible for available depth."
        )

    trades = np.asarray(x.value, dtype=float)
    trades = np.maximum(trades, 0.0)

    # Re-normalize slight numerical tolerance to match exact order size
    sum_trades = np.sum(trades)
    trades = trades * (Q / sum_trades) if sum_trades > 0 else np.full(T, Q / T, dtype=float)

    return Schedule(shares=trades)
