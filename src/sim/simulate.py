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


def simulate(schedule: Schedule, book: dict, impact: dict = None) -> CostReport:
    """
    Simulate schedule execution on the book.
    impact parameters are ignored because recorded data doesn't react to orders.
    """
    shares = schedule.shares
    T = len(shares)

    ask_prices = book["Pa"]
    ask_volumes = book["Va"]
    mid_prices = book["M"]

    Q = np.sum(shares)
    y = Q
    F = 0.0
    fills = []
    cash_paid = 0.0
    shares_filled = 0.0

    phi = 0.5  # default footprint resilience decay
    pi = 0.005  # sweep penalty

    shortfalls = []

    for t in range(T):
        if t >= len(ask_prices):
            break

        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        offered = shares[t]

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

    # Sweep remaining inventory at snapshot T
    if y > 1e-8 and len(ask_prices) > T:
        t = T
        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M = mid_prices[t]

        F_sweep = (F / (1 - phi) if phi != 1 else F + fills[-1]) if len(fills) > 0 else F
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
