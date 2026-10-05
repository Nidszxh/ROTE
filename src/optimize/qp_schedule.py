import cvxpy as cp
import numpy as np


def build_qp(
    Q: float,
    T: int,
    S: np.ndarray,
    eta: np.ndarray,
    alpha_bar: np.ndarray,
    sigma2: np.ndarray,
    psi: float,
    alpha_bar_T: float,
    lambda_imp: float,
    rho_D_net: np.ndarray,
) -> tuple[cp.Problem, cp.Variable, cp.Variable, cp.Variable]:
    """
    Build the risk-aware optimal execution QP (section 5.4).

    Args:
        Q: Parent order size
        T: Horizon length (periods)
        S: Half-spread or spread array of length T
        eta: Impact coefficient array of length T
        alpha_bar: Cumulative drift array of length T
        sigma2: Variance array of length T (sigma2[0] is unused as there is no risk in period 1)
        psi: Sweep price (excluding drift)
        alpha_bar_T: Cumulative drift at T
        lambda_imp: Risk aversion coefficient
        rho_D_net: Capacity cap array of length T

    Returns:
        problem, x, y, u
    """
    # Variables
    x = cp.Variable(T, nonneg=True)
    y = cp.Variable(T + 1)

    constraints = [y[0] == Q, y[1 : T + 1] == y[0:T] - x, x <= rho_D_net, y[T] >= 0]
    u = y[T]

    # Cost
    cost = 0
    cost += cp.sum(0.5 * cp.multiply(S, x))
    cost += cp.sum(cp.multiply(eta, cp.square(x)))
    cost += cp.sum(cp.multiply(alpha_bar, x))

    if lambda_imp > 0:
        cost += lambda_imp * cp.sum(cp.multiply(sigma2[1:T], cp.square(y[1:T])))

    cost += (psi + alpha_bar_T) * u

    problem = cp.Problem(cp.Minimize(cost), constraints)
    return problem, x, y, u
