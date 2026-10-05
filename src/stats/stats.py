from typing import Any

import numpy as np


def compute_statistics(
    lob_slice: dict[str, np.ndarray], rows_per_period: int = 20
) -> dict[str, Any]:
    """Compute on-demand statistics for a given LOB slice."""
    S = lob_slice["S"]
    Da = lob_slice["Da"]
    Db = lob_slice["Db"]
    OBI = lob_slice["OBI"]
    M = lob_slice["M"]

    # Spread
    avg_half_spread_bps = (S / M / 2).mean() * 10000

    # Depth
    avg_depth_ask = Da.mean()
    avg_depth_bid = Db.mean()

    # Imbalance
    avg_imbalance = OBI.mean()

    # Volatility (causal_sigma2)
    # Using the standard estimator: 10th percentile of non-zero absolute returns as floor
    # plus variance
    # First compute period returns
    n = len(M)
    n_periods = n // rows_per_period
    if n_periods < 2:
        vol_bps = 0.0
    else:
        end = n_periods * rows_per_period
        period_mids = M[:end].reshape(n_periods, rows_per_period)[:, -1]
        returns = np.diff(np.log(period_mids))
        vol_bps = 0.0 if len(returns) == 0 else returns.std() * 10000

    return {
        "avg_half_spread_bps": avg_half_spread_bps,
        "avg_depth_ask": avg_depth_ask,
        "avg_depth_bid": avg_depth_bid,
        "avg_imbalance": avg_imbalance,
        "volatility_bps_per_period": vol_bps,
    }
