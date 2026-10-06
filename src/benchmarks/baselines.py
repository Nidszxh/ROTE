from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from src.utils.contracts import Order, Schedule


def _validate_order(order: Order) -> tuple[float, int]:
    """Validate order inputs and return (size, horizon)."""
    if order.size <= 0:
        raise ValueError(f"Order size must be strictly positive, got {order.size}")
    if order.horizon <= 0:
        raise ValueError(f"Order horizon must be strictly positive, got {order.horizon}")
    return float(order.size), int(order.horizon)


def _normalize_shares(weights: np.ndarray, total_size: float, horizon: int) -> np.ndarray:
    """
    Scale positive weights to match total order size.
    Falls back to uniform TWAP allocation if total weight is non-positive or non-finite.
    """
    total_weight = float(np.sum(weights))
    if np.isfinite(total_weight) and total_weight > 0:
        return (weights / total_weight) * total_size
    return np.full(horizon, total_size / horizon, dtype=float)


def immediate_plan(order: Order) -> Schedule:
    """Execute entire parent order in the first period."""
    size, horizon = _validate_order(order)
    shares = np.zeros(horizon, dtype=float)
    shares[0] = size
    return Schedule(shares=shares)


def twap_plan(order: Order) -> Schedule:
    """
    Generate a Time-Weighted Average Price (TWAP) execution schedule.

    Evenly splits the total order size across the horizon steps.
    """
    size, horizon = _validate_order(order)
    shares = np.full(horizon, size / horizon, dtype=float)
    return Schedule(shares=shares)


def twap_prime_plan(order: Order, factor: float = 0.5) -> Schedule:
    """TWAP over shortened horizon T' = ceil(factor * T) (PROPOSAL.md section 7.1)."""
    size, horizon = _validate_order(order)
    t_prime = max(1, min(horizon, int(np.ceil(horizon * factor))))
    shares = np.zeros(horizon, dtype=float)
    shares[:t_prime] = size / t_prime
    return Schedule(shares=shares)


def depth_proportional_plan(
    order: Order,
    book: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """
    Generate an execution schedule proportional to available ask depth.

    Parameters
    ----------
    order : Order
        Target order containing size and horizon.
    book : Mapping[str, Any]
        Market data dictionary containing key 'Da' (ask depth array).
    params : Mapping[str, Any] | None
        Optional execution settings (rho, trailing_median_depth).
    """
    size, horizon = _validate_order(order)
    if "Da" not in book:
        raise KeyError("Market book missing required depth key 'Da'")

    da_arr = np.asarray(book["Da"][:horizon], dtype=float)
    if len(da_arr) < horizon:
        raise ValueError(
            f"Available ask depth length ({len(da_arr)}) is shorter than horizon ({horizon})"
        )

    da_clean = np.maximum(da_arr, 0.0)
    shares = _normalize_shares(da_clean, size, horizon)
    return Schedule(shares=shares)


def vwap_proxy_plan(order: Order, book: Mapping[str, Any]) -> Schedule:
    """
    Generate an execution schedule proportional to order-book imbalance.

    Because high-frequency event-time LOB datasets lack a continuous volume clock,
    this serves as an imbalance-weighted proxy for VWAP execution.

    Parameters
    ----------
    order : Order
        Target order containing size and horizon.
    book : Mapping[str, Any]
        Market data dictionary containing keys 'Da' (ask depth) and 'Db' (bid depth).
    """
    size, horizon = _validate_order(order)
    if "Da" not in book or "Db" not in book:
        raise KeyError("Market book missing required keys 'Da' and 'Db'")

    da = np.asarray(book["Da"][:horizon], dtype=float)
    db = np.asarray(book["Db"][:horizon], dtype=float)

    if len(da) < horizon or len(db) < horizon:
        raise ValueError("Market depth arrays are shorter than the order horizon")

    denom = np.maximum(da, 0.0) + np.maximum(db, 0.0)
    weights = np.zeros(horizon, dtype=float)
    valid_mask = denom > 0
    weights[valid_mask] = np.maximum(da[valid_mask], 0.0) / denom[valid_mask]

    shares = _normalize_shares(weights, size, horizon)
    return Schedule(shares=shares)
