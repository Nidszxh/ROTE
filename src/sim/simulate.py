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

    ask_prices = np.asarray(book["Pa"], dtype=float)
    ask_volumes = np.asarray(book["Va"], dtype=float)
    mid_prices = np.asarray(book["M"], dtype=float)
    if not (len(ask_prices) == len(ask_volumes) == len(mid_prices)):
        raise ValueError("book price, volume, and mid-price arrays must have equal length")
    if len(ask_prices) < len(shares):
        raise ValueError("book does not contain enough snapshots for the schedule horizon")

    T = len(shares)
    Q = float(np.sum(shares))
    if Q <= 0:
        return CostReport(shortfall_bps=0.0, std=0.0, trades=0)

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

    M0 = mid_prices[0]
    denom_bps = Q * M0 if (M0 > 0 and Q > 0) else 1.0

    y = Q
    F = 0.0
    fills = []
    shortfalls = []
    inventories = [y]

    total_half_spread = 0.0
    total_book_walk = 0.0
    total_timing = 0.0
    in_horizon_cash = 0.0

    cum_plan = np.cumsum(shares)
    cum_fill = 0.0

    F_last_entering = 0.0
    fill_last = 0.0

    for t in range(T):
        P_a = ask_prices[t]
        V_a = ask_volumes[t]
        M_t = mid_prices[t]

        F_last_entering = F
        net_depth = max(float(np.sum(V_a)) - F, 0.0)

        # Catch-up rule (section 7.1): min(y_t, planned_cumulative - filled_cumulative)
        desired_t = max(0.0, min(y, cum_plan[t] - cum_fill))
        offered = min(desired_t, rho * net_depth)

        res = walk_book_buy(P_a, V_a, offered, M_t, footprint=F)
        fill = res["shares_filled"]
        cash = res["cash_paid"]
        fill_last = fill

        fills.append(fill)
        cum_fill += fill
        y -= fill
        inventories.append(y)
        in_horizon_cash += cash

        p1 = P_a[0]
        half_spread_t = fill * (p1 - M_t)
        walk_prem_t = cash - fill * p1
        timing_t = fill * (M_t - M0)

        total_half_spread += half_spread_t
        total_book_walk += walk_prem_t
        total_timing += timing_t

        if fill > 0:
            slice_shortfall = (cash - fill * M_t) / (fill * M_t) * 10000.0 if M_t > 0 else 0.0
            shortfalls.append(slice_shortfall)

        F = (1.0 - phi) * (F + fill)

    # Terminal sweep (section 8.1): priced against snapshot T-1 net of (F_T + fill_T)
    sweep_exec_cost = 0.0
    sweep_timing_cost = 0.0
    penalty_premium = 0.0
    sweep_cash = 0.0
    unfilled_shares = 0.0

    if y > 1e-8:
        t_term = T - 1
        P_a_term = ask_prices[t_term]
        V_a_term = ask_volumes[t_term]
        M_term = mid_prices[t_term]

        F_sweep = F_last_entering + fill_last
        res_sweep = walk_book_buy(P_a_term, V_a_term, y, M_term, footprint=F_sweep)

        cash_sw = res_sweep["cash_paid"]
        unfilled_shares = res_sweep["unfilled_shares"]

        pen_cash = 0.0
        if unfilled_shares > 1e-8:
            P_max = P_a_term[-1]
            pen_cash = unfilled_shares * P_max * (1.0 + pi)
            penalty_premium = unfilled_shares * (P_max * (1.0 + pi) - M_term)

        total_sw_cash = cash_sw + pen_cash
        sweep_cash = total_sw_cash

        sweep_exec_cost = total_sw_cash - y * M_term
        sweep_timing_cost = y * (M_term - M0)

        if y > 0 and M_term > 0:
            slice_sw_bps = (total_sw_cash - y * M_term) / (y * M_term) * 10000.0
            shortfalls.append(slice_sw_bps)

    total_spend = in_horizon_cash + sweep_cash
    total_shortfall = total_spend - Q * M0
    total_shortfall_bps = (total_shortfall / denom_bps) * 10000.0

    half_spread_bps = (total_half_spread / denom_bps) * 10000.0
    book_walk_bps = (total_book_walk / denom_bps) * 10000.0
    timing_bps = (total_timing / denom_bps) * 10000.0
    sweep_exec_bps = (sweep_exec_cost / denom_bps) * 10000.0
    sweep_timing_bps = (sweep_timing_cost / denom_bps) * 10000.0
    penalty_bps = (penalty_premium / denom_bps) * 10000.0

    sigma_val = float(settings.get("sigma", 0.0))
    sigma2_arr = settings.get("sigma2")
    if sigma2_arr is not None:
        s2 = np.asarray(sigma2_arr, dtype=float)
    elif sigma_val > 0:
        s2 = np.full(T, sigma_val**2)
    else:
        s2 = np.zeros(T)
    inv_arr = np.asarray(inventories[1:T], dtype=float)
    var_inv = float(np.sum(s2[1 : len(inv_arr) + 1] * (inv_arr**2))) if len(inv_arr) > 0 else 0.0

    std = float(np.std(shortfalls)) if len(shortfalls) > 0 else 0.0
    trades = int(np.count_nonzero(np.array(fills) > 1e-8))

    return CostReport(
        shortfall_bps=total_shortfall_bps,
        std=std,
        trades=trades,
        half_spread_bps=half_spread_bps,
        book_walk_bps=book_walk_bps,
        timing_bps=timing_bps,
        sweep_exec_bps=sweep_exec_bps,
        sweep_timing_bps=sweep_timing_bps,
        penalty_bps=penalty_bps,
        inventory_risk=var_inv,
        unfilled_shares=unfilled_shares,
        cash_paid=total_spend,
        spend=total_spend,
    )
