from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.models.m1_ac import ac_classical_closed_form
from src.models.m2_lp import build_m2
from src.models.m3_mip import build_m3
from src.sim.simulate import simulate
from src.utils.contracts import Order, Schedule

# Professional financial styling palette
COLORS = {
    "ask": "#E53935",  # Vibrant Red
    "bid": "#1E88E5",  # Vibrant Blue
    "mid": "#43A047",  # Green
    "accent": "#FB8C00",  # Amber/Orange
    "purple": "#8E24AA",  # Purple
    "teal": "#00897B",  # Teal
    "dark": "#263238",  # Slate
    "gray": "#90A4AE",  # Cool gray
    "grid": "#ECEFF1",  # Light grid
}


def _apply_theme(ax: plt.Axes) -> None:
    """Apply clean minimalist styling to an axis."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CFD8DC")
    ax.spines["bottom"].set_color("#CFD8DC")
    ax.grid(True, linestyle="--", alpha=0.5, color=COLORS["grid"])
    ax.tick_params(colors="#37474F", labelsize=9)


def _validate_book_keys(book: Mapping[str, Any], required_keys: Sequence[str]) -> None:
    """Validate presence and non-emptiness of required keys in market book."""
    for key in required_keys:
        if key not in book:
            raise KeyError(f"Market book missing required key '{key}'")
        if len(book[key]) == 0:
            raise ValueError(f"Market book array '{key}' cannot be empty")


def plot_lob_ladder(book: Mapping[str, Any], snapshot_idx: int = 0) -> plt.Figure:
    """
    Generate an interactive 10-level Limit Order Book Price and Depth Ladder.

    Parameters
    ----------
    book : Mapping[str, Any]
        Market data containing 'Pa', 'Va', 'Pb', 'Vb', 'M', 'S'.
    snapshot_idx : int, optional
        Time index to snapshot, default 0.

    Returns
    -------
    plt.Figure
    """
    _validate_book_keys(book, ("Pa", "Va", "Pb", "Vb", "M", "S"))

    n_rows = len(book["M"])
    if snapshot_idx < 0 or snapshot_idx >= n_rows:
        raise IndexError(f"snapshot_idx {snapshot_idx} is out of bounds for book length {n_rows}")

    pa = np.asarray(book["Pa"], dtype=float)[snapshot_idx]
    va = np.asarray(book["Va"], dtype=float)[snapshot_idx]
    pb = np.asarray(book["Pb"], dtype=float)[snapshot_idx]
    vb = np.asarray(book["Vb"], dtype=float)[snapshot_idx]
    mid = float(book["M"][snapshot_idx])
    spread_bps = float(book["S"][snapshot_idx]) * 10000

    levels = np.arange(1, len(pa) + 1)
    cum_va = np.cumsum(va)
    cum_vb = np.cumsum(vb)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)

    # 1. Price Ladder
    _apply_theme(ax1)
    ax1.plot(levels, pa, marker="o", color=COLORS["ask"], lw=2.0, label="Ask Levels ($P^a_i$)")
    ax1.plot(levels, pb, marker="s", color=COLORS["bid"], lw=2.0, label="Bid Levels ($P^b_i$)")
    ax1.axhline(mid, color=COLORS["mid"], linestyle="--", lw=1.5, label=f"Mid Price ({mid:.2f})")
    ax1.fill_between(
        levels, pb, pa, color=COLORS["accent"], alpha=0.15, label=f"Spread: {spread_bps:.1f} bps"
    )
    ax1.set_xlabel("Order Book Level (1 to 10)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Price", fontsize=10, fontweight="bold")
    ax1.set_title("LOB Price Ladder & Spread Zone", fontsize=11, fontweight="bold", pad=8)
    ax1.set_xticks(levels)
    ax1.legend(loc="best", frameon=True, facecolor="white", edgecolor="#CFD8DC", fontsize=8.5)

    # 2. Volume & Cumulative Depth
    _apply_theme(ax2)
    ax2.bar(
        levels - 0.2, va, width=0.38, color=COLORS["ask"], alpha=0.75, label="Ask Depth ($V^a_i$)"
    )
    ax2.bar(
        levels + 0.2, vb, width=0.38, color=COLORS["bid"], alpha=0.75, label="Bid Depth ($V^b_i$)"
    )
    ax2.set_xlabel("Order Book Level (1 to 10)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Level Volume (Shares)", fontsize=10, fontweight="bold")
    ax2.set_title(
        "Liquidity Distribution & Cumulative Depth", fontsize=11, fontweight="bold", pad=8
    )
    ax2.set_xticks(levels)

    ax2_twin = ax2.twinx()
    ax2_twin.plot(levels, cum_va, color="#B71C1C", marker="^", ls=":", lw=1.8, label="Cumul. Ask")
    ax2_twin.plot(levels, cum_vb, color="#0D47A1", marker="v", ls=":", lw=1.8, label="Cumul. Bid")
    ax2_twin.set_ylabel("Cumulative Liquidity", fontsize=10, fontweight="bold")
    ax2_twin.spines["top"].set_visible(False)
    ax2_twin.spines["left"].set_visible(False)
    ax2_twin.grid(False)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="#CFD8DC",
        fontsize=8,
    )

    fig.tight_layout()
    return fig


def plot_microstructure_analytics(book: Mapping[str, Any], max_points: int = 400) -> plt.Figure:
    """
    Generate a 3-panel Microstructure Analytics Dashboard:
    1. Order Book Imbalance (OBI) rolling series.
    2. Half-spread distribution.
    3. Aggregate book depth evolution.
    """
    _validate_book_keys(book, ("M", "OBI", "S", "Da", "Db"))
    if max_points < 1:
        raise ValueError("max_points must be at least 1")

    n = min(len(book["M"]), max_points)
    mids = np.asarray(book["M"][:n], dtype=float)
    obi = np.asarray(book["OBI"][:n], dtype=float)
    spread_bps = np.asarray(book["S"][:n], dtype=float) * 5000  # half spread in bps
    da = np.asarray(book["Da"][:n], dtype=float)
    db = np.asarray(book["Db"][:n], dtype=float)
    t = np.arange(n)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 7.5), dpi=150, sharex=True)

    # 1. Mid-Price & OBI
    _apply_theme(ax1)
    ax1.plot(t, mids, color=COLORS["dark"], lw=1.5, label="Mid Price")
    ax1.set_ylabel("Mid Price", fontsize=9, fontweight="bold")
    ax1.set_title(
        "Microstructure Price & Imbalance Dynamics", fontsize=11, fontweight="bold", pad=8
    )

    ax1_twin = ax1.twinx()
    ax1_twin.plot(t, obi, color=COLORS["purple"], lw=1.0, alpha=0.7, label="Order Book Imbalance")
    ax1_twin.axhline(0, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax1_twin.set_ylabel("OBI [-1, 1]", fontsize=9, fontweight="bold", color=COLORS["purple"])
    ax1_twin.set_ylim(-1.1, 1.1)
    ax1_twin.grid(False)

    # 2. Half-Spread Dynamics
    _apply_theme(ax2)
    ax2.plot(t, spread_bps, color=COLORS["accent"], lw=1.2, label="Half-Spread (bps)")
    mean_spr = float(np.mean(spread_bps)) if len(spread_bps) > 0 else 0.0
    ax2.axhline(mean_spr, color="#E65100", ls="--", lw=1.2, label=f"Mean: {mean_spr:.1f} bps")
    ax2.set_ylabel("Half-Spread (bps)", fontsize=9, fontweight="bold")
    ax2.legend(loc="upper right", frameon=True, facecolor="white", fontsize=8)

    # 3. Depth Evolution
    _apply_theme(ax3)
    ax3.fill_between(t, 0, da, color=COLORS["ask"], alpha=0.35, label="Ask Depth ($D^a$)")
    ax3.fill_between(t, 0, -db, color=COLORS["bid"], alpha=0.35, label="Bid Depth ($D^b$)")
    ax3.axhline(0, color="black", lw=0.8)
    ax3.set_xlabel("Event Step Index (Discrete LOB Updates)", fontsize=10, fontweight="bold")
    ax3.set_ylabel("Net Depth", fontsize=9, fontweight="bold")
    ax3.legend(loc="lower right", frameon=True, facecolor="white", fontsize=8)

    fig.tight_layout()
    return fig


def plot_m1_frontier(
    order: Order,
    book: Mapping[str, Any],
    lambda_grid: list[float] | None = None,
) -> tuple[plt.Figure, pd.DataFrame]:
    """
    Compute and plot the Almgren-Chriss (M1) Risk-Cost Efficient Frontier.
    Left: Expected Shortfall (Cost) vs Volatility Risk (Std).
    Right: Execution schedule trajectories across varying risk aversions.
    """
    if order.size <= 0 or order.horizon < 1:
        raise ValueError("Invalid order size or horizon")
    _validate_book_keys(book, ("M", "Pa", "Va", "Da"))

    Q = float(order.size)
    T = int(order.horizon)
    eta = 0.1
    sigma = 0.015
    parameter_name = "lambda"
    if lambda_grid is None:
        omega_grid = [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
        lambda_grid = [2.0 * eta * (np.cosh(omega) - 1.0) / (sigma**2) for omega in omega_grid]
        parameter_name = "omega"

    records = []
    schedules = {}

    for lam in lambda_grid:
        trades = ac_classical_closed_form(X=Q, T=T, lam=lam, sigma=sigma, eta=eta)
        sched = Schedule(shares=trades)
        rep = simulate(sched, book)
        records.append(
            {
                "lambda": lam,
                "omega": np.arccosh(1.0 + lam * sigma**2 / (2.0 * eta)),
                "Shortfall (bps)": rep.shortfall_bps,
                "Risk (std)": rep.std,
                "Trades": rep.trades,
                "First Slice (%)": (trades[0] / Q) * 100,
            }
        )
        schedules[lam] = trades

    df = pd.DataFrame(records)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)

    # 1. Efficient Frontier Curve
    _apply_theme(ax1)
    ax1.plot(
        df["Risk (std)"],
        df["Shortfall (bps)"],
        marker="o",
        color=COLORS["purple"],
        lw=2.0,
        markersize=6,
    )
    # Highlight TWAP limit (lambda = 0)
    ax1.scatter(
        [df.iloc[0]["Risk (std)"]],
        [df.iloc[0]["Shortfall (bps)"]],
        color=COLORS["bid"],
        s=120,
        zorder=5,
        label=r"TWAP Limit ($\lambda=0$)",
    )
    # Highlight aggressive limit
    ax1.scatter(
        [df.iloc[-1]["Risk (std)"]],
        [df.iloc[-1]["Shortfall (bps)"]],
        color=COLORS["ask"],
        s=120,
        zorder=5,
        label=r"Max Risk-Averse",
    )

    ax1.set_xlabel("Timing Risk (Standard Deviation)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Implementation Shortfall (bps)", fontsize=10, fontweight="bold")
    ax1.set_title("M1 Efficient Frontier (Cost vs. Risk)", fontsize=11, fontweight="bold", pad=8)
    ax1.legend(loc="upper right", frameon=True, facecolor="white", fontsize=8.5)

    # 2. Schedule Trajectories
    _apply_theme(ax2)
    t_steps = np.arange(1, T + 1)
    colors_traj = plt.cm.viridis(np.linspace(0.1, 0.9, len(lambda_grid)))

    for i, lam in enumerate(lambda_grid):
        ax2.plot(
            t_steps,
            schedules[lam],
            label=(
                rf"$\lambda$={lam:.1e}"
                if parameter_name == "lambda" and lam > 0
                else (
                    rf"$\omega$={np.arccosh(1.0 + lam * sigma**2 / (2.0 * eta)):.2g}"
                    if lam > 0
                    else "TWAP"
                )
            ),
            color=colors_traj[i],
            lw=1.8,
        )

    ax2.set_xlabel("Execution Horizon Step ($t$)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Trade Quantity ($n_t$)", fontsize=10, fontweight="bold")
    ax2.set_title("Optimal Liquidation Trajectories", fontsize=11, fontweight="bold", pad=8)
    ax2.legend(loc="upper right", frameon=True, facecolor="white", fontsize=7.5, ncol=2)

    fig.tight_layout()
    return fig, df


def plot_m2_diagnostics(order: Order, book: Mapping[str, Any], rho: float = 0.25) -> plt.Figure:
    """
    Generate M2 LOB LP Liquidity & Shadow Price Diagnostics.
    Upper: Trade allocations vs. depth capacity limits.
    Lower: Shadow prices indicating liquidity bottleneck constraints.
    """
    if order.size <= 0 or order.horizon < 1:
        raise ValueError("Invalid order size or horizon")
    _validate_book_keys(book, ("Pa", "Va", "M", "Da"))

    Q = float(order.size)
    T = int(order.horizon)
    Pa = np.asarray(book["Pa"][:T], dtype=float)
    Va = np.asarray(book["Va"][:T], dtype=float)
    mid = np.asarray(book["M"][:T], dtype=float)
    Da = np.asarray(book["Da"][:T], dtype=float)
    sigma2 = np.zeros(T)

    prob, q, y, x, constraints = build_m2(
        Q=Q, T=T, Pa=Pa, Va=Va, mid=mid, sigma2=sigma2, lam=0.0, rho=rho, Da_net=Da
    )
    prob.solve()

    trades = np.asarray(x.value, dtype=float) if x.value is not None else np.zeros(T)
    # Extract dual shadow prices for participation constraint
    dual_val = constraints[4].dual_value
    shadow_prices = np.asarray(dual_val, dtype=float) if dual_val is not None else np.zeros(T)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5.0), dpi=150, sharex=True)

    # 1. Trade vs Capacity
    _apply_theme(ax1)
    steps = np.arange(1, T + 1)
    ax1.bar(steps - 0.15, trades, width=0.4, color=COLORS["teal"], label="Executed Shares ($x_t$)")
    ax1.plot(
        steps,
        rho * Da[:T],
        color=COLORS["ask"],
        lw=1.8,
        ls="--",
        label=r"Participation Cap ($\rho D^a_t$)",
    )
    ax1.set_ylabel("Quantity", fontsize=9, fontweight="bold")
    ax1.set_title(
        "M2 LOB Depth Allocations & Capacity Utilization", fontsize=11, fontweight="bold", pad=8
    )
    ax1.legend(loc="upper right", frameon=True, facecolor="white", fontsize=8.5)

    # 2. Shadow Price Spikes
    _apply_theme(ax2)
    ax2.plot(
        steps,
        shadow_prices,
        marker="d",
        color=COLORS["purple"],
        lw=1.8,
        label=r"Shadow Price ($\mu_t$)",
    )
    ax2.fill_between(steps, 0, shadow_prices, color=COLORS["purple"], alpha=0.15)
    ax2.set_xlabel("Execution Horizon Step ($t$)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Shadow Price", fontsize=9, fontweight="bold")
    ax2.set_title(
        "Marginal Cost of Liquidity Constraints (Dual Multipliers)",
        fontsize=10,
        fontweight="bold",
        pad=6,
    )
    ax2.legend(loc="upper right", frameon=True, facecolor="white", fontsize=8.5)

    fig.tight_layout()
    return fig


def plot_m3_tradeoff(order: Order, book: Mapping[str, Any]) -> plt.Figure:
    """
    Generate M3 Fixed-Charge Trade-off: Trade count and impact vs. fixed ticket charge c_f.
    """
    if order.size <= 0 or order.horizon < 1:
        raise ValueError("Invalid order size or horizon")
    _validate_book_keys(book, ("Pa", "Va", "M", "Da"))

    cf_values = [0.0, 2.0, 5.0, 10.0, 20.0, 40.0]
    Q = float(order.size)
    T = int(order.horizon)
    Pa = np.asarray(book["Pa"][:T], dtype=float)
    Va = np.asarray(book["Va"][:T], dtype=float)
    mid = np.asarray(book["M"][:T], dtype=float)
    Da = np.asarray(book["Da"][:T], dtype=float)

    active_trades = []
    total_costs = []

    for cf in cf_values:
        prob, q, y, x, z = build_m3(
            Q=Q, T=T, Pa=Pa, Va=Va, mid=mid, rho=1.0, Da_net=Da, L_min=50.0, c_f=cf
        )
        prob.solve()
        if x.value is not None:
            n_active = int(np.sum(x.value > 1.0))
            active_trades.append(n_active)
            total_costs.append(float(prob.value))
        else:
            active_trades.append(0)
            total_costs.append(0.0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.0), dpi=150)

    # 1. Sparsity / Active trades
    _apply_theme(ax1)
    ax1.plot(cf_values, active_trades, marker="s", color=COLORS["ask"], lw=2.0, markersize=7)
    ax1.set_xlabel("Fixed Ticket Fee ($c_f$)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Active Child Orders ($K$)", fontsize=10, fontweight="bold")
    ax1.set_title("Child Order Sparsity vs. Fixed Fee", fontsize=11, fontweight="bold", pad=8)

    # 2. Total Execution Cost
    _apply_theme(ax2)
    ax2.plot(cf_values, total_costs, marker="o", color=COLORS["bid"], lw=2.0, markersize=7)
    ax2.set_xlabel("Fixed Ticket Fee ($c_f$)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Total Objective Cost", fontsize=10, fontweight="bold")
    ax2.set_title(
        "Total Cost Impact of Discrete Ticket Fees", fontsize=11, fontweight="bold", pad=8
    )

    fig.tight_layout()
    return fig


def plot_benchmark_frontier(
    compare_df: pd.DataFrame,
    schedules: Mapping[str, np.ndarray],
) -> plt.Figure:
    """
    Generate Multi-Model Benchmark Comparison:
    Left: Overlay of execution trajectories across all strategies.
    Right: Risk-Cost Scatter plot (Pareto Frontier) mapping cost vs timing risk.
    """
    if compare_df.empty or not schedules:
        raise ValueError("compare_df and schedules cannot be empty")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3), dpi=150)

    # 1. Trajectory Overlay
    _apply_theme(ax1)
    color_map = {
        "M1": COLORS["purple"],
        "M2": COLORS["teal"],
        "M3": COLORS["accent"],
        "TWAP": COLORS["bid"],
        "Depth-Prop": COLORS["dark"],
        "VWAP Proxy": COLORS["mid"],
    }

    for name, shares in schedules.items():
        steps = np.arange(1, len(shares) + 1)
        c = color_map.get(name, "#78909C")
        ax1.plot(steps, shares, label=name, color=c, lw=1.8, marker="o", markersize=4)

    ax1.set_xlabel("Execution Horizon Step ($t$)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Trade Quantity ($n_t$)", fontsize=10, fontweight="bold")
    ax1.set_title("Strategy Liquidation Profiles", fontsize=11, fontweight="bold", pad=8)
    ax1.legend(loc="upper right", frameon=True, facecolor="white", fontsize=8, ncol=2)

    # 2. Risk vs Cost Scatter
    _apply_theme(ax2)
    for _, row in compare_df.iterrows():
        name = str(row["Model"])
        c = color_map.get(name, "#78909C")
        ax2.scatter(
            row["Risk (std)"],
            row["Shortfall (bps)"],
            color=c,
            s=130,
            edgecolor="black",
            linewidth=0.8,
            zorder=4,
        )
        ax2.annotate(
            name,
            (row["Risk (std)"], row["Shortfall (bps)"]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8.5,
            fontweight="bold",
        )

    ax2.set_xlabel("Timing Risk (Std Dev)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Implementation Shortfall (bps)", fontsize=10, fontweight="bold")
    ax2.set_title("Risk-Cost Empirical Execution Frontier", fontsize=11, fontweight="bold", pad=8)

    fig.tight_layout()
    return fig


def plot_ahp_ranking(
    weights: np.ndarray,
    scores_df: pd.DataFrame,
) -> plt.Figure:
    """
    Generate AHP Decision Analysis visualization:
    Left: Normalized weights assigned to decision criteria.
    Right: Final composite scores across candidate execution models.
    """
    if len(weights) == 2:
        raise ValueError(f"weights must have length 3, got {len(weights)}")
    if len(weights) not in (3, 4):
        raise ValueError(f"weights must have length 3 or 4, got {len(weights)}")
    if scores_df.empty or "Model" not in scores_df or "Score" not in scores_df:
        raise ValueError("scores_df must contain 'Model' and 'Score' columns")

    criteria = (
        ["Cost", "Risk", "Completion", "Simplicity"]
        if len(weights) == 4
        else [
            "Cost",
            "Risk",
            "Simplicity",
        ]
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.8), dpi=150)

    # 1. Criteria Weights
    _apply_theme(ax1)
    bar_colors = [COLORS["ask"], COLORS["bid"], COLORS["accent"], COLORS["purple"]][: len(weights)]
    ax1.bar(criteria, weights * 100, color=bar_colors, width=0.55, edgecolor="#37474F", alpha=0.85)
    for i, w in enumerate(weights):
        ax1.text(i, w * 100 + 1.5, f"{w * 100:.1f}%", ha="center", fontsize=9, fontweight="bold")
    ax1.set_ylabel("Priority Weight (%)", fontsize=10, fontweight="bold")
    ax1.set_ylim(0, max(weights * 100) + 15)
    ax1.set_title("AHP Criteria Preference Weights", fontsize=11, fontweight="bold", pad=8)

    # 2. Strategy Composite Scores
    _apply_theme(ax2)
    sorted_df = scores_df.sort_values("Score", ascending=True)
    models = sorted_df["Model"]
    scores = sorted_df["Score"] * 100

    bars = ax2.barh(
        models, scores, color=COLORS["teal"], height=0.55, edgecolor="#004D40", alpha=0.85
    )
    # Highlight winner
    bars[-1].set_color(COLORS["purple"])

    for i, s in enumerate(scores):
        ax2.text(s + 1.0, i, f"{s:.1f}", va="center", fontsize=8.5, fontweight="bold")

    ax2.set_xlabel("Composite Score (Higher is Better)", fontsize=10, fontweight="bold")
    ax2.set_xlim(0, max(scores) + 15)
    ax2.set_title("Ranked Strategy Performance Score", fontsize=11, fontweight="bold", pad=8)

    fig.tight_layout()
    return fig
