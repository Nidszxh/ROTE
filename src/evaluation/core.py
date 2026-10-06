from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.benchmarks.baselines import (
    depth_proportional_plan,
    twap_plan,
)
from src.impact.impact import calibrate_eta0_for_stock
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
    return {
        "twap_T": lambda order, book, params: twap_plan(order),
        "depth_proportional": lambda order, book, params: depth_proportional_plan(order, book),
    }


def evaluate(
    books: Mapping[str, Mapping[str, np.ndarray]],
    windows: Mapping[str, Iterable[slice]] | Iterable[slice],
    theta: Iterable[float] = (1.0,),
    strategies: Mapping[str, Strategy] | None = None,
    rows_per_period: int = 20,
    params: Mapping[str, float] | None = None,
    bootstrap_reps: int = 2000,
    bootstrap_block: int = 5,
    seed: int | None = None,
    calibrate_impact: bool = True,
) -> EvaluationResult:
    """Evaluate strategies over every stock, window, and order-size multiplier.

    ``theta`` scales the median first-level ask depth, avoiding a hard-coded
    order size while keeping comparisons comparable across stocks.
    """
    if rows_per_period < 1 or any(float(t) <= 0 for t in theta):
        raise ValueError("rows_per_period and theta values must be positive")
    strategy_map = dict(strategies or _default_strategies())
    window_map = windows if isinstance(windows, Mapping) else {"window": windows}
    base_params = dict(params or {})
    records: list[dict[str, float | str]] = []
    for stock, book in books.items():
        if "Va" not in book:
            raise KeyError(f"book for {stock!r} is missing 'Va'")
        depth = np.asarray(book["Va"], dtype=float).sum(axis=1)
        eta = base_params.get("eta")
        if calibrate_impact and "Pa" in book:
            eta = calibrate_eta0_for_stock(np.asarray(book["Pa"]), np.asarray(book["Va"]))
            if isinstance(eta, Mapping):
                eta = eta.get("eta0")
        local_params = {**base_params, **({"eta": float(eta), "eta0": float(eta)} if eta else {})}
        median_depth = float(np.nanmedian(depth[depth > 0])) if np.any(depth > 0) else 1.0
        for window_name, slices in window_map.items():
            for window_id, window in enumerate(slices):
                start, stop, step = window.indices(len(depth))
                indices = np.arange(start, stop, step or 1)
                if len(indices) < rows_per_period:
                    continue
                for multiplier in theta:
                    order = Order("buy", float(multiplier) * median_depth, rows_per_period, {})
                    selected = {
                        k: np.asarray(v)[indices[:rows_per_period]] for k, v in book.items()
                    }
                    for strategy_name, strategy in strategy_map.items():
                        schedule = strategy(order, selected, local_params)
                        report = simulate(schedule, selected, local_params)
                        records.append(
                            {
                                "stock": stock,
                                "window": str(window_name),
                                "window_id": window_id,
                                "theta": float(multiplier),
                                "strategy": strategy_name,
                                "shortfall_bps": report.shortfall_bps,
                                "risk": report.std,
                                "trades": report.trades,
                            }
                        )
    observations = pd.DataFrame.from_records(records)
    if observations.empty:
        columns = ["strategy", "theta", "metric", "mean", "ci_low", "ci_high", "n"]
        return EvaluationResult(observations, pd.DataFrame(columns=columns), pd.DataFrame())
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
    pivot = observations.pivot_table(
        index=["stock", "window_id", "theta"], columns="strategy", values="shortfall_bps"
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
                    "mean_difference": diff.mean(),
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
