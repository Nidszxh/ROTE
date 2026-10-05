import numpy as np

from cost.walk_book import walk_book_buy


def calibrate_eta0_for_stock(
    ask_prices: np.ndarray,  # shape (N, L)
    ask_volumes: np.ndarray,  # shape (N, L)
    rho: float = 0.25,
    num_probe_sizes: int = 10,
) -> float:
    """
    Calibrate eta_0 for a single stock using the calibration split.
    Regresses walk_premium on x^2 / D^a_t through the origin.
    """
    N = ask_prices.shape[0]
    total_depths = ask_volumes.sum(axis=1)

    premiums = []
    regressors = []

    for i in range(N):
        D_t = total_depths[i]
        if D_t <= 0:
            continue

        # Probe sizes up to rho * D_t
        max_x = rho * D_t
        probe_sizes = np.linspace(max_x / num_probe_sizes, max_x, num_probe_sizes)

        for x in probe_sizes:
            res = walk_book_buy(ask_prices[i], ask_volumes[i], x)
            # walk premium is exactly res['walk_premium']
            premiums.append(res["walk_premium"])
            # regressor is x^2 / D_t
            regressors.append((x**2) / D_t)

    if not regressors:
        return 0.0

    y = np.array(premiums)
    x_reg = np.array(regressors)

    # Regress y on x through origin: argmin_w ||y - w x_reg||^2 -> w = (x^T y) / (x^T x)
    eta_0 = np.dot(x_reg, y) / np.dot(x_reg, x_reg)
    return float(eta_0)
