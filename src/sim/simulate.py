from collections.abc import Mapping

import numpy as np

from src.cost.walk_book import walk_book_buy
from src.utils.contracts import CostReport, Schedule


def flip_book_for_sell(book: dict) -> dict:
    """Mirrors the order book so a sell order can be executed as a buy order."""
    flipped = book.copy()
    flipped["Pa"] = -book["Pb"]
    flipped["Pb"] = -book["Pa"]
    flipped["Va"] = book["Vb"]
    flipped["Vb"] = book["Va"]
    flipped["Pa1"] = -book["Pb1"]
    flipped["Pb1"] = -book["Pa1"]
    flipped["M"] = -book["M"]
    flipped["Da"] = book["Db"]
    flipped["Db"] = book["Da"]
    flipped["OBI"] = -book["OBI"]
    return flipped


def simulate(
    schedule: Schedule,
    book: Mapping[str, np.ndarray],
    impact: Mapping[str, float] | None = None,
) -> CostReport:
    """Execute a schedule against recorded ask-side book snapshots."""
    shares = np.asarray(schedule.shares, dtype=float)
    if shares.ndim != 1 or np.any(~np.isfinite(shares)) or np.any(shares < 0):
        raise ValueError("schedule shares must be a finite, non-negative 1-D array")
    required = ("Pa", "Va", "M")
    missing = [key for key in required if key not in book]
    if missing:
        raise KeyError(f"market book missing required keys: {', '.join(missing)}")

    ask_prices = book["Pa"]
    ask_volumes = book["Va"]
    mid_prices = book["M"]
    if not (len(ask_prices) == len(ask_volumes) == len(mid_prices)):
        raise ValueError("book price, volume, and mid-price arrays must have equal length")
    if len(ask_prices) < len(shares):
        raise ValueError("book does not contain enough snapshots for the schedule horizon")

    T = len(shares)
    Q = np.sum(shares)
    y = Q
    F = 0.0
    fills = []
    cash_paid = 0.0
    shares_filled = 0.0

    settings = impact or {}
    phi = float(settings.get("phi", settings.get("resilience", 0.5)))
    pi = float(settings.get("pi", 0.005))
    rho = float(settings.get("rho", 1.0))
    if not 0.0 <= phi <= 1.0:
        raise ValueError(f"resilience phi must be in [0, 1], got {phi}")
    if pi < 0:
        raise ValueError(f"sweep penalty pi must be non-negative, got {pi}")
    if rho <= 0:
        raise ValueError(f"participation rho must be positive, got {rho}")

    shortfalls = []

    for t in range(T):
        if t >= len(ask_prices):
            break

        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        offered = min(shares[t], y, rho * max(float(np.sum(V_a)) - F, 0.0))

        res = walk_book_buy(P_a, V_a, offered, M, footprint=F)

        fill = res["shares_filled"]
        fills.append(fill)

        cash_paid += res["cash_paid"]
        shares_filled += fill
        y -= fill

        # Calculate shortfall for this slice
        if fill > 0:
            slice_shortfall_bps = (
                (res["cash_paid"] - fill * M) / (fill * M) * 10000.0 if M > 0 else 0
            )
            shortfalls.append(slice_shortfall_bps)

        F = (1 - phi) * (F + fill)

    # The terminal sweep uses the final snapshot already inside the horizon.
    if y > 1e-8:
        t = T - 1
        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        F_sweep = F / (1 - phi) if phi < 1 and fills else F + (fills[-1] if fills else 0.0)
        res = walk_book_buy(P_a, V_a, y, M, footprint=F_sweep)

        fill = res["shares_filled"]
        cash_paid += res["cash_paid"]
        shares_filled += fill

        if fill > 0:
            slice_shortfall_bps = (
                (res["cash_paid"] - fill * M) / (fill * M) * 10000.0 if M > 0 else 0
            )
            shortfalls.append(slice_shortfall_bps)

        unfilled = res["unfilled_shares"]
        if unfilled > 1e-8:
            P_max = P_a[-1]
            cash_paid += unfilled * P_max * (1 + pi)
            shares_filled += unfilled
            slice_shortfall_bps = (
                (unfilled * P_max * (1 + pi) - unfilled * M) / (unfilled * M) * 10000.0
                if M > 0
                else 0
            )
            shortfalls.append(slice_shortfall_bps)

    total_shortfall = cash_paid - Q * mid_prices[0]
    denom_bps = Q * mid_prices[0]
    total_shortfall_bps = (total_shortfall / denom_bps) * 10000.0 if denom_bps > 0 else 0.0

    std = np.std(shortfalls) if len(shortfalls) > 0 else 0.0
    trades = np.count_nonzero(np.array(fills) > 1e-8)

    return CostReport(shortfall_bps=total_shortfall_bps, std=std, trades=trades)
