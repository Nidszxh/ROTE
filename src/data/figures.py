from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from data import loader
from data.loader import Lob, stock_name, stock_short_name

SERIES_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
SNAPSHOT_INDEX = 1000
THETAS = [0.25, 0.5, 1.0, 2.0]
THETA_STYLES = [
    (":", "#333333"),
    ("--", "#e6550d"),
    ("-.", "#de2d26"),
    ("-", "#756bb1"),
]


def _setup_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.titlesize": 12,
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )


def _snapshot_index(n: int) -> int:
    if n <= 0:
        raise ValueError("LOB series is empty; cannot take a snapshot")
    return min(SNAPSHOT_INDEX, n - 1)


def _walk_cash(prices: np.ndarray, volumes: np.ndarray, shares: float) -> float:
    cash = 0.0
    remaining = shares
    for price, vol in zip(prices, volumes, strict=True):
        if remaining <= 0:
            break
        fill = min(vol, remaining)
        if fill > 0:
            cash += fill * price
            remaining -= fill
    return cash


def generate_fig1_lob_snapshot(lob: Lob, out_dir: Path) -> Path:
    _setup_style()
    idx = _snapshot_index(len(lob["M"]))
    pa = lob["Pa"][idx]
    va = lob["Va"][idx]
    pb = lob["Pb"][idx]
    vb = lob["Vb"][idx]
    m0 = lob["M"][idx]
    s0 = lob["S"][idx]
    cum_va = np.cumsum(va)
    cum_vb = np.cumsum(vb)
    levels = np.arange(1, 11)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(levels, pa, marker="o", color="#d62728", label="Ask Levels (P^a_i)", lw=1.8)
    ax1.plot(levels, pb, marker="s", color="#1f77b4", label="Bid Levels (P^b_i)", lw=1.8)
    ax1.axhline(m0, color="#2ca02c", linestyle="--", label=f"Arrival Mid M_0 = €{m0:.2f}")
    ax1.fill_between(
        [1, 10], pb[0], pa[0], color="#ff7f0e", alpha=0.15, label=f"Spread S_0 = €{s0:.2f}"
    )
    ax1.set_xlabel("Order Book Level (i = 1 .. 10)")
    ax1.set_ylabel("Price (EUR)")
    ax1.set_title("LOB Price Ladder Snapshot (Event Time)")
    ax1.set_xticks(levels)
    ax1.legend(frameon=True, facecolor="white", framealpha=0.9)
    ax2.bar(
        levels - 0.2, va / 1e3, width=0.4, color="#d62728", alpha=0.8, label="Ask Volume (v^a_i)"
    )
    ax2.bar(
        levels + 0.2, vb / 1e3, width=0.4, color="#1f77b4", alpha=0.8, label="Bid Volume (v^b_i)"
    )
    ax2_twin = ax2.twinx()
    ax2_twin.plot(levels, cum_va / 1e3, color="#8c564b", marker="^", label="Cumul Ask Depth")
    ax2_twin.plot(levels, cum_vb / 1e3, color="#17becf", marker="v", label="Cumul Bid Depth")
    ax2_twin.grid(False)
    ax2.set_xlabel("Order Book Level (i = 1 .. 10)")
    ax2.set_ylabel("Level Volume (1,000 shares)")
    ax2_twin.set_ylabel("Cumulative Depth (1,000 shares)")
    ax2.set_title("LOB Depth and Level Volume Profile (Event Time)")
    ax2.set_xticks(levels)
    lines_1, labels_1 = ax2.get_legend_handles_labels()
    lines_2, labels_2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="upper left",
        frameon=True,
        facecolor="white",
    )
    fig.suptitle("Figure 1: 10-level limit order book snapshot in event time on FI-2010 (DecPre)")
    fig.tight_layout()
    p = out_dir / "fig1_lob_snapshot.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_fig2_stock_boundaries(lob: Lob, boundaries: list[int], out_dir: Path) -> Path:
    _setup_style()
    m = lob["M"]
    n_samples = len(m)
    x = np.arange(n_samples)
    fig, ax = plt.subplots(figsize=(13, 5))
    n_seg = max(0, len(boundaries) - 1)
    for i in range(n_seg):
        s = boundaries[i]
        e = boundaries[i + 1]
        if e <= s:
            continue
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        ax.plot(x[s:e], m[s:e], color=color, lw=0.7, label=stock_name(i))
        if i > 0:
            ax.axvline(s, color="black", linestyle=":", lw=1.2, alpha=0.7)
    for i in range(n_seg):
        s = boundaries[i]
        e = boundaries[i + 1]
        if e <= s:
            continue
        mid_x = (s + e) // 2
        try:
            y_pos = float(np.median(m[s:e]))
        except Exception:
            y_pos = float(np.median(m))
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        ax.text(
            mid_x,
            y_pos,
            stock_short_name(i),
            horizontalalignment="center",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color, alpha=0.9),
        )
    ax.set_xlabel("Observation Index in Event Time (10-event blocks)")
    ax.set_ylabel("Mid-Price M_t (EUR)")
    ax.set_title("Figure 2: Mid-price series and stock boundary identification in event time")
    ax.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    fig.tight_layout()
    p = out_dir / "fig2_stock_boundaries_price_series.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_fig3_depth_distribution(lob: Lob, boundaries: list[int], out_dir: Path) -> Path:
    _setup_style()
    n_seg = max(0, len(boundaries) - 1)
    fig, axes = (
        plt.subplots(1, n_seg, figsize=(15 if n_seg > 1 else 5, 4.5), sharey=True)
        if n_seg > 0
        else plt.subplots(1, 1)
    )
    axes_list = np.atleast_1d(axes)
    for i in range(n_seg):
        ax = axes_list[i] if i < len(axes_list) else axes_list[0]
        s = boundaries[i]
        e = boundaries[i + 1]
        if e <= s:
            continue
        da = lob["Da"][s:e] / 1e3
        d_med = float(np.median(da)) if len(da) > 0 else 0.0
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        ax.hist(da, bins=35, density=True, alpha=0.6, color=color, edgecolor="black", lw=0.5)
        ax.axvline(d_med, color="black", linestyle="-", lw=1.8, label=f"Median D̄={d_med:.0f}k")
        for th, (ls, col) in zip(THETAS, THETA_STYLES, strict=True):
            q_val = th * d_med
            ax.axvline(q_val, color=col, linestyle=ls, lw=1.3, label=f"θ={th} ({q_val:.0f}k)")
        ax.set_title(stock_short_name(i))
        ax.set_xlabel("Gross Ask Depth (10^3 shares)")
        if i == 0:
            ax.set_ylabel("Probability Density")
            ax.legend(loc="upper right", fontsize=7.5, frameon=True, facecolor="white")
    fig.suptitle("Figure 3: Ask depth distribution and parent order sizes in event time (A8)")
    fig.tight_layout()
    p = out_dir / "fig3_depth_distribution_order_realism.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_fig4_spread_imbalance(lob: Lob, boundaries: list[int], out_dir: Path) -> Path:
    _setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    n_seg = max(0, len(boundaries) - 1)
    for i in range(n_seg):
        s = boundaries[i]
        e = boundaries[i + 1]
        if e <= s:
            continue
        m_seg = lob["M"][s:e]
        s_seg = lob["S"][s:e]
        obi_seg = lob["OBI"][s:e]
        with np.errstate(divide="ignore", invalid="ignore"):
            s_bps = (s_seg / m_seg) * 10000.0
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        med_bps = float(np.median(s_bps)) if len(s_bps) > 0 else 0.0
        ax1.hist(
            s_bps,
            bins=np.linspace(0, 50, 40),
            density=True,
            histtype="step",
            lw=1.6,
            color=color,
            label=f"{stock_short_name(i)} (med={med_bps:.1f} bps)",
        )
        ax2.hist(
            obi_seg,
            bins=np.linspace(-1, 1, 40),
            density=True,
            histtype="step",
            lw=1.6,
            color=color,
            label=f"{stock_short_name(i)}",
        )
    ax1.set_xlabel("Bid-Ask Spread S_t / M_t (basis points)")
    ax1.set_ylabel("Empirical Density")
    ax1.set_title("Bid-Ask Spread Distribution in Event Time")
    ax1.legend(frameon=True, facecolor="white", framealpha=0.9)
    ax2.set_xlabel("Order Book Imbalance OBI_t = (D^b - D^a)/(D^b + D^a)")
    ax2.set_ylabel("Empirical Density")
    ax2.set_title("Order Book Imbalance Distribution in Event Time")
    ax2.axvline(0, color="grey", linestyle="--", lw=1)
    ax2.legend(frameon=True, facecolor="white", framealpha=0.9)
    fig.suptitle("Figure 4: Bid-ask spread (bps) and depth imbalance distributions in event time")
    fig.tight_layout()
    p = out_dir / "fig4_spread_and_imbalance.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_fig5_volatility_sigma_floor(
    lob: Lob, boundaries: list[int], m_rows: int, out_dir: Path
) -> Path:
    _setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    n_seg = max(0, len(boundaries) - 1)
    for i in range(n_seg):
        s = boundaries[i]
        e = boundaries[i + 1]
        if e <= s:
            continue
        m_stock = lob["M"][s:e]
        ret_period = loader.period_log_returns(m_stock, m_rows)
        sigma_min = loader.sigma_min_floor(ret_period)
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        vol_period_bps = np.abs(ret_period) * 10000.0
        ax1.hist(
            vol_period_bps,
            bins=np.linspace(0, 30, 40),
            density=True,
            histtype="step",
            lw=1.6,
            color=color,
            label=f"{stock_short_name(i)} (σ_min={sigma_min * 10000:.1f} bps)",
        )
        if i == 2:
            m_sample = m_stock[:10000]
            ret_row = np.diff(np.log(m_sample)) if len(m_sample) >= 2 else np.array([], dtype=float)
            ax2.hist(
                ret_row * 10000.0,
                bins=np.linspace(-15, 15, 61),
                density=True,
                color="#1f77b4",
                alpha=0.6,
                edgecolor="black",
                lw=0.5,
                label=f"Row-level (10 events) for {stock_short_name(i)}",
            )
            ax2.hist(
                vol_period_bps,
                bins=np.linspace(-30, 30, 61),
                density=True,
                color="#d62728",
                histtype="step",
                lw=1.8,
                label=f"Period-level (m={m_rows} rows = 200 events)",
            )
    ax1.set_xlabel("Period Return Volatility |r_t| (basis points)")
    ax1.set_ylabel("Empirical Density")
    ax1.set_title("Period-Level Volatility & σ_min Floor (Event Time)")
    ax1.legend(frameon=True, facecolor="white", framealpha=0.9)
    ax2.set_xlabel("Return (basis points)")
    ax2.set_ylabel("Empirical Density")
    ax2.set_title("Tick Discretization: Zero-Return Spike at 10-Event Scale (A5)")
    ax2.legend(frameon=True, facecolor="white", framealpha=0.9)
    fig.suptitle(
        "Figure 5: Period return volatility, tick discretization, and sigma_min floor in event time"
    )
    fig.tight_layout()
    p = out_dir / "fig5_volatility_and_sigma_floor.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_fig6_book_walk_convexity(
    lob: Lob, out_dir: Path, rho: float = 0.25, pi: float = 0.005
) -> Path:
    _setup_style()
    idx = _snapshot_index(len(lob["M"]))
    pa = lob["Pa"][idx]
    va = lob["Va"][idx]
    m0 = lob["M"][idx]
    s0 = lob["S"][idx]
    da = lob["Da"][idx]
    x_grid = np.linspace(0.0, float(da), 500)
    cost_actual = np.zeros_like(x_grid)
    for i, x_val in enumerate(x_grid):
        cash_paid = _walk_cash(pa, va, float(x_val))
        cost_actual[i] = cash_paid - float(x_val) * m0
    x_probe = rho * da
    cash_paid_probe = _walk_cash(pa, va, float(x_probe))
    premium_probe = cash_paid_probe - float(x_probe) * pa[0] if x_probe > 0 else 0.0
    eta0 = premium_probe / (x_probe**2 / da) if x_probe > 0 and da > 0 else 1.0
    eta_t = eta0 / da if da > 0 else 1.0
    cost_model = 0.5 * s0 * x_grid + eta_t * (x_grid**2)
    half_spread_line = 0.5 * s0 * x_grid
    x_beyond = np.linspace(float(da), float(da) * 1.5, 200)
    p_max = pa[-1]
    sweep_price = p_max * (1 + pi)
    cash_at_da = cost_actual[-1] + float(da) * m0 if len(cost_actual) > 0 else float(da) * m0
    cost_beyond = (cash_at_da + (x_beyond - float(da)) * sweep_price) - x_beyond * m0
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        x_grid / 1e3,
        cost_actual,
        color="#1f77b4",
        lw=2.2,
        label="Actual Book-Walk Cost C_t(x) - x·M_0",
    )
    ax.plot(
        x_grid / 1e3,
        cost_model,
        color="#d62728",
        linestyle="--",
        lw=2.0,
        label=r"QP Approximation: $\frac{1}{2}S_t x + \frac{\eta_0}{D^a_t} x^2$",
    )
    ax.plot(
        x_grid / 1e3,
        half_spread_line,
        color="#7f7f7f",
        linestyle=":",
        lw=1.5,
        label=r"Half-Spread Baseline: $\frac{1}{2}S_t x$",
    )
    ax.plot(
        x_beyond / 1e3,
        cost_beyond,
        color="#e377c2",
        linestyle="-.",
        lw=2.0,
        label=r"Terminal Sweep Penalty: $P^{\max}_a(1+\pi) - M_0$",
    )
    ax.axvline(
        va[0] / 1e3,
        color="#2ca02c",
        linestyle=":",
        lw=1.5,
        label=f"Level 1 Depth v^a_1 ({va[0] / 1e3:.1f}k sh, zero premium)",
    )
    ax.axvline(
        rho * da / 1e3,
        color="#ff7f0e",
        linestyle="--",
        lw=1.5,
        label=f"Participation Cap ρ·D^a ({rho * da / 1e3:.1f}k sh)",
    )
    ax.axvline(
        da / 1e3,
        color="black",
        linestyle="-",
        lw=1.5,
        label=f"Total 10-level Visible Depth D^a ({da / 1e3:.1f}k sh)",
    )
    ax.set_xlabel("Order Size x (1,000 shares)")
    ax.set_ylabel("Execution Cost vs. Arrival Mid (EUR)")
    ax.set_title(
        "Figure 6: Book-walk execution cost, quadratic approximation, and terminal sweep penalty"
    )
    ax.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    fig.tight_layout()
    p = out_dir / "fig6_book_walk_cost_convexity.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def generate_all_audit_figures(
    lob: Lob,
    boundaries: list[int],
    config: Mapping[str, Any],
    output_dir: str | Path = "results/figures",
) -> list[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    period_cfg = config.get("period") or {}
    m_rows = int(period_cfg.get("rows_per_period", 20))
    exec_cfg = config.get("execution") or {}
    rho = float(exec_cfg.get("rho", 0.25))
    pi = float(exec_cfg.get("pi", 0.005))
    p1 = generate_fig1_lob_snapshot(lob, out_dir)
    p2 = generate_fig2_stock_boundaries(lob, boundaries, out_dir)
    p3 = generate_fig3_depth_distribution(lob, boundaries, out_dir)
    p4 = generate_fig4_spread_imbalance(lob, boundaries, out_dir)
    p5 = generate_fig5_volatility_sigma_floor(lob, boundaries, m_rows, out_dir)
    p6 = generate_fig6_book_walk_convexity(lob, out_dir, rho=rho, pi=pi)
    return [p1, p2, p3, p4, p5, p6]
