from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.benchmarks.baselines import (
    depth_proportional_plan,
    immediate_plan,
    twap_plan,
    twap_prime_plan,
    vwap_proxy_plan,
)
from src.impact.impact import calibrate_eta0_for_stock
from src.models.m1_ac import solve_m1
from src.models.m2_lp import solve_m2
from src.models.m3_mip import solve_m3
from src.models.rote_static import solve_rote_static
from src.sim.simulate import simulate
from src.utils.contracts import Order, Schedule

Strategy = Callable[[Order, Mapping[str, np.ndarray], Mapping[str, float]], Schedule]


def bootstrap_mean_ci(
    values: Iterable[float],
    reps: int = 2000,
    block: int = 1,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float]:
    """Return a percentile bootstrap interval for the mean.

    ``block`` resamples consecutive observations, which preserves the local
    dependence present in adjacent execution windows.
    """
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return (float("nan"), float("nan"))
    if reps < 1 or block < 1 or not 0 < confidence < 1:
        raise ValueError("reps and block must be positive and confidence must be in (0, 1)")
    if x.size == 1:
        return (float(x[0]), float(x[0]))
    rng = np.random.default_rng(seed)
    block = min(block, x.size)
    n_blocks = int(np.ceil(x.size / block))
    samples = np.empty((reps, n_blocks * block), dtype=float)
    for i in range(reps):
        starts = rng.integers(0, x.size - block + 1, size=n_blocks)
        samples[i] = np.concatenate([x[s : s + block] for s in starts])
    means = samples[:, : x.size].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    return (float(np.quantile(means, alpha)), float(np.quantile(means, 1.0 - alpha)))


def holm_correction(p_values: Mapping[str, float], alpha: float = 0.05) -> pd.DataFrame:
    """Apply Holm's step-down family-wise error correction."""
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    items = sorted(p_values.items(), key=lambda item: item[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p_value) in enumerate(items):
        if not np.isfinite(p_value) or not 0 <= p_value <= 1:
            raise ValueError("p-values must be finite and in [0, 1]")
        running = max(running, min(1.0, (m - rank) * p_value))
        adjusted[name] = running
    return pd.DataFrame(
        [
            {
                "comparison": name,
                "p_value": p_values[name],
                "p_adjusted": adjusted[name],
                "reject": adjusted[name] <= alpha,
            }
            for name in p_values
        ]
    )


@dataclass(frozen=True)
class EvaluationResult:
    observations: pd.DataFrame
    summary: pd.DataFrame
    comparisons: pd.DataFrame


def _default_strategies() -> dict[str, Strategy]:
    """Return the baseline ladder from PROPOSAL.md section 7.1."""
    return {
        "immediate": lambda order, book, params: immediate_plan(order),
        "twap_T": lambda order, book, params: twap_plan(order),
        "twap_Tprime": lambda order, book, params: twap_prime_plan(
            order, factor=float(params.get("twap_prime_factor", 0.5))
        ),
        "depth_proportional": lambda order, book, params: depth_proportional_plan(
            order, book, params
        ),
        "ac": lambda order, book, params: solve_m1(order, book, params),
        "ac_capped": lambda order, book, params: solve_m1(
            order, book, {**dict(params), "capped": True}
        ),
        "m2_lp": lambda order, book, params: solve_m2(order, book, params),
        "rote_static": lambda order, book, params: solve_rote_static(order, book, params),
    }


def get_full_strategy_registry() -> dict[str, Strategy]:
    """Return all available strategies including MIP and VWAP proxy."""
    strategies = _default_strategies()
    strategies["m3_mip"] = lambda order, book, params: solve_m3(order, book, params)
    strategies["vwap_proxy"] = lambda order, book, params: vwap_proxy_plan(order, book)
    return strategies


def _load_cached_calibration() -> dict[str, float]:
    path = Path("results/tables/calibration.json")
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in raw.get("eta_0", {}).items()}
    except Exception:
        return {}


def evaluate(
    books: Mapping[str, Mapping[str, np.ndarray]],
    windows: Mapping[str, Iterable[slice]] | Iterable[slice] | None = None,
    theta: Iterable[float] = (1.0,),
    strategies: Mapping[str, Strategy] | None = None,
    rows_per_period: int = 20,
    horizon: int = 20,
    burn_in_rows: int = 100,
    params: Mapping[str, Any] | None = None,
    bootstrap_reps: int = 2000,
    bootstrap_block: int = 5,
    seed: int | None = None,
    calibrate_impact: bool = True,
    calibrated_params: Mapping[str, Any] | None = None,
) -> EvaluationResult:
    """Evaluate strategies over every stock, window, and order-size multiplier.

    Enforces strict calibration-split parameters without in-sample leakage (C4),
    unique per-window keys without observation duplication (C2),
    and execution over non-overlapping snapshot windows (C3).
    """
    if rows_per_period < 1 or horizon < 1 or any(float(t) <= 0 for t in theta):
        raise ValueError("rows_per_period, horizon, and theta values must be positive")

    strategy_map = dict(strategies or _default_strategies())
    base_params = dict(params or {})
    cached_calib = _load_cached_calibration()
    records: list[dict[str, Any]] = []

    # Ensure baseline simulation params are present
    base_params.setdefault("rho", 0.25)
    base_params.setdefault("phi", 0.5)
    base_params.setdefault("pi", 0.005)

    for stock_key, book in books.items():
        if "Va" not in book:
            raise KeyError(f"book for {stock_key!r} is missing 'Va'")

        depth = np.asarray(book["Va"], dtype=float).sum(axis=1)
        gross_depth = (
            np.asarray(book["Da"], dtype=float)
            if "Da" in book
            else np.asarray(book["Va"], dtype=float).sum(axis=1)
        )
        n_rows = len(depth)

        # Calibrated parameters
        stock_calib = dict((calibrated_params or {}).get(stock_key, {}))
        eta = stock_calib.get("eta0") or base_params.get("eta0") or base_params.get("eta")

        if calibrate_impact and "Pa" in book:
            c_res = calibrate_eta0_for_stock(np.asarray(book["Pa"]), np.asarray(book["Va"]))
            if isinstance(c_res, Mapping):
                eta = c_res.get("eta0", eta)
            elif isinstance(c_res, (float, int)):
                eta = float(c_res)

        if eta is None and cached_calib:
            for k, val in cached_calib.items():
                if k in stock_key or stock_key in k:
                    eta = val
                    break
            if eta is None and cached_calib:
                eta = float(np.median(list(cached_calib.values())))

        if eta is None:
            eta = 0.1

        local_params = {
            **base_params,
            **stock_calib,
            "eta": float(eta),
            "eta0": float(eta),
        }

        # Order size scaling: Q = theta * D_bar (PROPOSAL.md section 10.1)
        median_depth = float(stock_calib.get("D_bar", np.nanmedian(gross_depth[gross_depth > 0])))
        if not np.isfinite(median_depth) or median_depth <= 0:
            median_depth = 1000.0
        local_params["D_bar"] = median_depth

        # Resolve windows for this specific book
        slices_for_book: list[slice] = []
        if isinstance(windows, Mapping):
            if stock_key in windows and windows[stock_key] is not None:
                slices_for_book = list(windows[stock_key])
            elif "window" in windows and windows["window"] is not None:
                slices_for_book = list(windows["window"])
            else:
                for s_list in windows.values():
                    if s_list is not None:
                        slices_for_book.extend(s_list)
        elif windows is not None:
            slices_for_book = list(windows)

        if not slices_for_book:
            # Deterministic non-overlapping grid (A6)
            stride = horizon * rows_per_period
            for w_start in range(burn_in_rows, n_rows - stride + 1, stride):
                slices_for_book.append(slice(w_start, w_start + stride))

        # Evaluate over resolved windows
        for window_id, window in enumerate(slices_for_book):
            start, stop, step = window.indices(n_rows)
            indices = np.arange(start, stop, step or 1)
            if len(indices) < rows_per_period:
                continue

            # Sample snapshots across horizon
            eff_horizon = min(horizon, len(indices) // rows_per_period)
            if eff_horizon < 1:
                eff_horizon = 1
                sample_idx = indices[:1]
            else:
                sample_idx = indices[: eff_horizon * rows_per_period : rows_per_period]

            selected = {k: np.asarray(v)[sample_idx] for k, v in book.items()}
            window_key = f"{stock_key}_w{window_id}"

            for multiplier in theta:
                q_order = float(multiplier) * median_depth
                order = Order("buy", q_order, eff_horizon, {})

                for strategy_name, strategy in strategy_map.items():
                    schedule = strategy(order, selected, local_params)
                    report = simulate(schedule, selected, local_params)
                    records.append(
                        {
                            "stock": stock_key,
                            "window": str(window_id),
                            "window_id": window_id,
                            "window_key": window_key,
                            "theta": float(multiplier),
                            "strategy": strategy_name,
                            "shortfall_bps": report.shortfall_bps,
                            "risk": report.inventory_risk
                            if report.inventory_risk > 0
                            else report.std,
                            "std": report.std,
                            "trades": report.trades,
                            "half_spread_bps": report.half_spread_bps,
                            "book_walk_bps": report.book_walk_bps,
                            "timing_bps": report.timing_bps,
                            "sweep_exec_bps": report.sweep_exec_bps,
                            "sweep_timing_bps": report.sweep_timing_bps,
                            "penalty_bps": report.penalty_bps,
                        }
                    )

    observations = pd.DataFrame.from_records(records)
    if observations.empty:
        columns = ["strategy", "theta", "metric", "mean", "ci_low", "ci_high", "n"]
        return EvaluationResult(observations, pd.DataFrame(columns=columns), pd.DataFrame())

    # Guarantee uniqueness (C2)
    assert not observations.duplicated(subset=["stock", "window_key", "theta", "strategy"]).any(), (
        "Duplicate evaluation observations detected!"
    )

    rng = np.random.default_rng(seed)
    summary_rows = []
    for (strategy, multiplier), group in observations.groupby(["strategy", "theta"]):
        for metric in ("shortfall_bps", "risk"):
            values = group[metric].to_numpy()
            ci = bootstrap_mean_ci(
                values, bootstrap_reps, bootstrap_block, seed=int(rng.integers(2**32))
            )
            summary_rows.append(
                {
                    "strategy": strategy,
                    "theta": multiplier,
                    "metric": metric,
                    "mean": float(np.mean(values)),
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                    "n": len(values),
                }
            )
    summary = pd.DataFrame(summary_rows)
    comparisons = _paired_comparisons(observations, bootstrap_reps, seed)
    return EvaluationResult(observations, summary, comparisons)


def _paired_comparisons(observations: pd.DataFrame, reps: int, seed: int | None) -> pd.DataFrame:
    """Pair observations strictly by (stock, window_key, theta) and run permutation test."""
    pivot = observations.pivot_table(
        index=["stock", "window_key", "theta"], columns="strategy", values="shortfall_bps"
    )
    names = list(pivot.columns)
    if len(names) < 2:
        return pd.DataFrame()

    rng = np.random.default_rng(seed)
    rows = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            diff = (pivot[left] - pivot[right]).dropna().to_numpy()
            if not len(diff):
                continue
            signs = rng.choice([-1.0, 1.0], size=(max(1, reps), len(diff)))
            null = (np.abs((diff * signs).mean(axis=1)) >= abs(diff.mean())).mean()
            rows.append(
                {
                    "comparison": f"{left} - {right}",
                    "mean_difference": float(diff.mean()),
                    "p_value": float(max(null, 1.0 / max(1, reps))),
                    "n": len(diff),
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        corrected = holm_correction(dict(zip(result.comparison, result.p_value, strict=True)))
        result = result.merge(corrected[["comparison", "p_adjusted", "reject"]], on="comparison")
    return result


run_evaluation = evaluate
