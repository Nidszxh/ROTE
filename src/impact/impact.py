import numpy as np

from src.cost.walk_book import walk_book_buy


def calibrate_eta0_for_stock(
    ask_prices: np.ndarray,
    ask_volumes: np.ndarray,
    rho: float = 0.25,
    num_probe_sizes: int = 10,
) -> dict:
    """Calibrate eta_0 (quadratic), c (linear), and gamma (square-root) for a single stock."""
    N = ask_prices.shape[0]
    total_depths = ask_volumes.sum(axis=1)

    premiums = []
    x_quad = []
    x_lin = []
    x_sqrt = []

    for i in range(N):
        D_t = total_depths[i]
        if D_t <= 0:
            continue

        max_x = rho * D_t
        probe_sizes = np.linspace(max_x / num_probe_sizes, max_x, num_probe_sizes)

        for x in probe_sizes:
            res = walk_book_buy(ask_prices[i], ask_volumes[i], x)
            y_val = res["walk_premium"]
            if y_val == 0:
                continue
            premiums.append(y_val)
            x_quad.append((x**2) / D_t)
            x_lin.append(x)
            x_sqrt.append(
                x * np.sqrt(x / D_t)
            )  # e.g. x * sqrt(x / D) for total cost, or just whatever formulation is used.

    if not premiums:
        return {"eta0": 0.0, "c": 0.0, "gamma": 0.0}

    y = np.array(premiums)
    xq = np.array(x_quad)
    xl = np.array(x_lin)
    xs = np.array(x_sqrt)

    eta_0 = float(np.dot(xq, y) / np.dot(xq, xq)) if np.dot(xq, xq) > 0 else 0.0
    c = float(np.dot(xl, y) / np.dot(xl, xl)) if np.dot(xl, xl) > 0 else 0.0
    gamma = float(np.dot(xs, y) / np.dot(xs, xs)) if np.dot(xs, xs) > 0 else 0.0

    # Calculate R2
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)

    y_pred_q = eta_0 * xq
    ss_res_q = np.sum((y - y_pred_q) ** 2)
    r2_q = 1 - (ss_res_q / ss_tot) if ss_tot > 0 else 0

    y_pred_l = c * xl
    ss_res_l = np.sum((y - y_pred_l) ** 2)
    r2_l = 1 - (ss_res_l / ss_tot) if ss_tot > 0 else 0

    y_pred_s = gamma * xs
    ss_res_s = np.sum((y - y_pred_s) ** 2)
    r2_s = 1 - (ss_res_s / ss_tot) if ss_tot > 0 else 0

    return {
        "eta0": eta_0,
        "c": c,
        "gamma": gamma,
        "r2_quad": r2_q,
        "r2_lin": r2_l,
        "r2_sqrt": r2_s,
        "rmse_quad": np.sqrt(np.mean((y - y_pred_q) ** 2)),
        "rmse_lin": np.sqrt(np.mean((y - y_pred_l) ** 2)),
        "rmse_sqrt": np.sqrt(np.mean((y - y_pred_s) ** 2)),
    }
