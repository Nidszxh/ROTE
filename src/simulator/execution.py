from collections.abc import Callable

import numpy as np

from cost.walk_book import walk_book_buy


def run_simulation(
    Q: float,
    T: int,
    ask_prices: np.ndarray,
    ask_volumes: np.ndarray,
    mid_prices: np.ndarray,
    schedule_fn: Callable,  # function that takes state and returns shares to offer
    rho: float = 0.25,
    phi: float = 0.5,
    pi: float = 0.005,
) -> dict[str, float]:
    """
    Run execution simulator (Section 7).
    """
    y = Q
    F = 0.0
    fills = []

    cash_paid = 0.0
    shares_filled = 0.0

    for t in range(T):
        if t >= len(ask_prices):
            break

        # Current state
        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        # Calculate net depth
        D_a = V_a.sum()
        D_net = max(0.0, D_a - F)

        # Get target from strategy
        offered = schedule_fn(t, y, fills, D_net)

        # Apply cap if strategy is capped
        offered = min(offered, rho * D_net)

        # Walk the book
        res = walk_book_buy(P_a, V_a, offered, M, footprint=F)

        fill = res["shares_filled"]
        fills.append(fill)

        cash_paid += res["cash_paid"]
        shares_filled += fill
        y -= fill

        # Update footprint
        F = (1 - phi) * (F + fill)

    # Sweep remaining inventory
    if y > 1e-8 and len(ask_prices) > T:
        t = T
        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        # Note: no resilience recovery on period T's own fill
        # F is already (1-phi)*(F_{T-1} + fill_{T-1}) if t was T-1
        # wait, the sweep is priced against depth net of F_T + fill_T
        F_sweep = (F / (1 - phi) if phi != 1 else F + fills[-1]) if len(fills) > 0 else F

        res = walk_book_buy(P_a, V_a, y, M, footprint=F_sweep)

        fill = res["shares_filled"]
        cash_paid += res["cash_paid"]
        shares_filled += fill

        # Penalty for remaining unexecuted
        unfilled = res["unfilled_shares"]
        if unfilled > 1e-8:
            P_max = P_a[-1]
            cash_paid += unfilled * P_max * (1 + pi)
            shares_filled += unfilled

    return {
        "shares_filled": shares_filled,
        "cash_paid": cash_paid,
        "avg_price": cash_paid / shares_filled if shares_filled > 0 else 0.0,
    }
