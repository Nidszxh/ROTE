from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

import numpy as np


class WalkResult(TypedDict):
    shares_filled: float
    cash_paid: float
    avg_price: float
    half_spread_cost: float
    walk_premium: float
    shortfall: float
    shortfall_bps: float
    unfilled_shares: float


def walk_book_buy(
    ask_prices: np.ndarray | Sequence[float],
    ask_volumes: np.ndarray | Sequence[float],
    shares_to_buy: float,
    mid_price: float | None = None,
    footprint: float = 0.0,
) -> WalkResult:
    prices = np.asarray(ask_prices, dtype=float)
    volumes = np.asarray(ask_volumes, dtype=float).copy()
    if prices.ndim != 1 or volumes.ndim != 1:
        raise ValueError("ask_prices/ask_volumes must be 1-D")
    if prices.shape != volumes.shape:
        raise ValueError(
            f"ask_prices and ask_volumes must align, got {prices.shape} vs {volumes.shape}"
        )
    if shares_to_buy < 0:
        raise ValueError(f"shares_to_buy must be >= 0, got {shares_to_buy}")
    if footprint < 0:
        raise ValueError(f"footprint must be >= 0, got {footprint}")
    if not np.isfinite(prices).all():
        raise ValueError("non-finite prices")
    if not np.isfinite(volumes).all():
        raise ValueError("non-finite volumes")
    if np.any(volumes < 0):
        raise ValueError("negative ask volume")
    if shares_to_buy == 0:
        return WalkResult(
            shares_filled=0.0,
            cash_paid=0.0,
            avg_price=0.0,
            half_spread_cost=0.0,
            walk_premium=0.0,
            shortfall=0.0,
            shortfall_bps=0.0,
            unfilled_shares=0.0,
        )
    if prices.size == 0:
        raise ValueError("cannot fill from an empty order book")
    if footprint > 0:
        rem_fp = footprint
        for i in range(len(volumes)):
            deduct = min(volumes[i], rem_fp)
            volumes[i] -= deduct
            rem_fp -= deduct
            if rem_fp <= 0:
                break
    p1 = prices[0]
    m0 = mid_price if mid_price is not None else p1
    if m0 < 0 or not np.isfinite(m0):
        m0 = p1
    half_spread_per_share = p1 - m0
    shares_left = float(shares_to_buy)
    cash_paid = 0.0
    shares_filled = 0.0
    for i in range(len(prices)):
        fill_level = min(volumes[i], shares_left)
        if fill_level > 0:
            cash_paid += fill_level * prices[i]
            shares_filled += fill_level
            shares_left -= fill_level
        if shares_left <= 1e-12:
            break
    if shares_filled <= 0:
        return WalkResult(
            shares_filled=0.0,
            cash_paid=0.0,
            avg_price=0.0,
            half_spread_cost=0.0,
            walk_premium=0.0,
            shortfall=0.0,
            shortfall_bps=0.0,
            unfilled_shares=float(shares_to_buy),
        )
    avg_price = cash_paid / shares_filled
    shortfall = cash_paid - shares_filled * m0
    half_spread_cost = shares_filled * half_spread_per_share
    walk_premium = cash_paid - shares_filled * p1
    denom_bps = shares_filled * m0 if shares_filled * m0 > 0 else 0.0
    shortfall_bps = (shortfall / denom_bps) * 10000.0 if denom_bps > 0 else 0.0
    return WalkResult(
        shares_filled=shares_filled,
        cash_paid=cash_paid,
        avg_price=avg_price,
        half_spread_cost=half_spread_cost,
        walk_premium=walk_premium,
        shortfall=shortfall,
        shortfall_bps=shortfall_bps,
        unfilled_shares=float(max(0.0, shares_to_buy - shares_filled)),
    )
