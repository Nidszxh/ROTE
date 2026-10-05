from __future__ import annotations

import numpy as np


def ewma_volatility(returns: np.ndarray, span: int = 20, min_vol: float = 0.0) -> np.ndarray:
    """Calculate EWMA volatility of period returns."""
    if len(returns) == 0:
        return np.array([])

    alpha = 2 / (span + 1)
    vols = np.zeros(len(returns))

    # Initialize with the first squared return or variance
    var = returns[0] ** 2
    vols[0] = np.sqrt(var)

    for i in range(1, len(returns)):
        var = alpha * (returns[i] ** 2) + (1 - alpha) * var
        vols[i] = np.sqrt(var)

    return np.maximum(vols, min_vol)


def compute_regime_thresholds(
    metric: np.ndarray,
) -> tuple[float, float]:
    """Compute tercile thresholds (33rd and 67th percentiles) for a metric."""
    if len(metric) == 0:
        return 0.0, 0.0
    return float(np.percentile(metric, 33.33)), float(np.percentile(metric, 66.67))


def assign_regimes(metric: np.ndarray, thresholds: tuple[float, float]) -> np.ndarray:
    """Assign regime labels (0=low, 1=med, 2=high) based on thresholds."""
    if len(metric) == 0:
        return np.array([], dtype=int)

    regimes = np.zeros(len(metric), dtype=int)
    regimes[metric >= thresholds[0]] = 1
    regimes[metric >= thresholds[1]] = 2
    return regimes
