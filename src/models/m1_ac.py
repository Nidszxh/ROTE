from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cvxpy as cp
import numpy as np

from src.utils.contracts import Order, Schedule


def ac_classical_closed_form(
    X: float,
    T: int,
    lam: float,
    sigma: float,
    eta: float,
    tau: float = 1.0,
) -> np.ndarray:
    """
    Compute closed-form Almgren-Chriss (2000) execution schedule.

    Parameters
    ----------
    X : float
        Total order quantity to liquidate. Must be positive.
    T : int
        Number of discrete execution intervals. Must be >= 1.
    lam : float
        Risk aversion coefficient (lambda >= 0).
    sigma : float
        Volatility parameter (sigma >= 0).
    eta : float
        Temporary price impact parameter (eta > 0).
    tau : float, optional
        Time step length (tau > 0), default 1.0.

    Returns
    -------
    np.ndarray
        Array of trade sizes [n_1, ..., n_T] summing to X.
    """
    if X <= 0:
        raise ValueError(f"Order quantity X must be positive, got {X}")
    if T < 1:
        raise ValueError(f"Horizon T must be at least 1, got {T}")
    if lam < 0:
        raise ValueError(f"Risk aversion lambda must be non-negative, got {lam}")
    if sigma < 0:
        raise ValueError(f"Volatility sigma must be non-negative, got {sigma}")
    if eta <= 0:
        raise ValueError(f"Temporary impact eta must be strictly positive, got {eta}")
    if tau <= 0:
        raise ValueError(f"Time step tau must be strictly positive, got {tau}")

    if lam == 0 or sigma == 0:
        return np.full(T, X / T, dtype=float)

    # cosh(kappa * tau) = 1 + 0.5 * lambda * sigma^2 * tau^2 / eta
    arg = 1.0 + 0.5 * lam * (sigma**2) * (tau**2) / eta
    # Safeguard against precision rounding below 1.0
    kappa = float(np.arccosh(max(1.0, arg))) / tau

    # Numerically stable evaluation of sinh(kappa * (T - t)) / sinh(kappa * T)
    # Using exp representation to avoid sinh overflow for large kappa * T
    t_vals = np.arange(1, T + 1, dtype=float) * tau
    total_time = T * tau

    # Ratio: sinh(kappa * (T - t)) / sinh(kappa * T)
    # = exp(-kappa * t) * (1 - exp(-2 * kappa * (T - t))) / (1 - exp(-2 * kappa * T))
    exp_neg_kt = np.exp(-kappa * t_vals)
    num = 1.0 - np.exp(-2.0 * kappa * (total_time - t_vals))
    denom = 1.0 - np.exp(-2.0 * kappa * total_time)

    # Handle boundary where denom is tiny or numerical limits
    x_t = np.zeros(T, dtype=float) if denom <= 0 else X * exp_neg_kt * (num / denom)

    # Ensure final inventory reaches exactly zero
    x_t[-1] = 0.0

    x_prev = np.concatenate(([X], x_t[:-1]))
    n_k = np.maximum(x_prev - x_t, 0.0)

    # Re-normalize to guarantee exact sum to X
    sum_n = np.sum(n_k)
    n_k = n_k * (X / sum_n) if sum_n > 0 else np.full(T, X / T, dtype=float)

    return n_k


def ac_classical_cvxpy(
    X: float,
    T: int,
    lam: float,
    sigma: float,
    eta: float,
    tau: float = 1.0,
    gamma: float = 0.0,
    eps: float = 0.0,
) -> np.ndarray:
    """
    Compute Almgren-Chriss schedule using CVXPY quadratic programming.

    Minimizes:
        sum_k [ gamma * n_k * x_k + eps * n_k + (eta / tau) * n_k^2 ]
        + lambda * sigma^2 * tau * sum_k x_k^2

    Subject to:
        x_0 = X, x_T = 0, n_k = x_{k-1} - x_k, n_k >= 0.
    """
    if X <= 0 or T < 1 or lam < 0 or sigma < 0 or eta <= 0 or tau <= 0:
        raise ValueError("Invalid parameters for Almgren-Chriss CVXPY optimization")

    x = cp.Variable(T + 1, nonneg=True, name="inventory")
    n = cp.Variable(T, nonneg=True, name="trades")

    constraints = [
        x[0] == X,
        x[T] == 0,
        n == x[:-1] - x[1:],
    ]

    # Objective formulation
    cost_terms = []

    if gamma > 0:
        cost_terms.append(gamma * cp.sum(cp.multiply(n, x[1:])))

    if eps > 0:
        cost_terms.append(eps * cp.sum(n))

    # Quadratic temporary impact
    cost_terms.append((eta / tau) * cp.sum_squares(n))

    # Variance risk penalty
    if lam > 0 and sigma > 0:
        cost_terms.append(lam * (sigma**2) * tau * cp.sum_squares(x[1:]))

    objective = cp.Minimize(cp.sum(cost_terms) if cost_terms else 0.0)
    prob = cp.Problem(objective, constraints)

    solved = False
    for s in (cp.HIGHS, cp.CLARABEL):
        try:
            prob.solve(solver=s)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and n.value is not None:
                solved = True
                break
        except Exception:
            continue

    if not solved:
        try:
            prob.solve(solver=cp.OSQP, max_iter=20000)
            if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and n.value is not None:
                solved = True
        except Exception:
            pass

    if not solved or n.value is None:
        raise RuntimeError(
            f"Almgren-Chriss CVXPY failed to find optimal solution: status={prob.status}"
        )

    trades = np.asarray(n.value, dtype=float)
    trades = np.maximum(trades, 0.0)
    sum_t = np.sum(trades)
    if sum_t > 0:
        trades = trades * (X / sum_t)

    return trades


def solve_m1(
    order: Order,
    book: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """
    Execute Almgren-Chriss model (M1) returning a Schedule contract.
    """
    if order.size <= 0:
        raise ValueError(f"Order size must be positive, got {order.size}")
    if order.horizon < 1:
        raise ValueError(f"Order horizon must be >= 1, got {order.horizon}")

    p = params or {}
    lam = float(p.get("lambda_imp", 1e-4))
    sigma = float(p.get("sigma", 0.01))
    eta = float(p.get("eta", 0.1))
    tau = float(p.get("tau", 1.0))

    trades = ac_classical_closed_form(
        X=float(order.size),
        T=int(order.horizon),
        lam=lam,
        sigma=sigma,
        eta=eta,
        tau=tau,
    )
    return Schedule(shares=trades)
