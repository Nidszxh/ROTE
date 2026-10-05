import pytest
import numpy as np
import cvxpy as cp
from optimize.qp_schedule import build_qp

pytestmark = [
    pytest.mark.T1,
    pytest.mark.T2,
    pytest.mark.T3,
    pytest.mark.T4,
    pytest.mark.T5,
    pytest.mark.T6,
    pytest.mark.T7,
    pytest.mark.T11,
]

def test_t1_twap():
    # T1: Constant parameters, lambda=0, no caps, alpha=0 gives TWAP(T)
    Q = 1000.0
    T = 10
    S = np.zeros(T)
    eta = np.ones(T) * 0.01
    alpha_bar = np.zeros(T)
    sigma2 = np.ones(T)
    psi = 100.0
    alpha_bar_T = 0.0
    lambda_imp = 0.0
    rho_D_net = np.ones(T) * 10000.0 # no binding caps

    prob, x, y, u = build_qp(
        Q=Q, T=T, S=S, eta=eta, alpha_bar=alpha_bar, sigma2=sigma2,
        psi=psi, alpha_bar_T=alpha_bar_T, lambda_imp=lambda_imp, rho_D_net=rho_D_net
    )
    prob.solve(solver=cp.OSQP, eps_abs=1e-8, eps_rel=1e-8)
    
    assert prob.status == cp.OPTIMAL
    x_val = x.value
    # TWAP means equal shares
    np.testing.assert_allclose(x_val, Q / T, atol=2e-3)
    np.testing.assert_allclose(u.value, 0.0, atol=2e-3)

def test_t2_t3_front_loading():
    # T2/T3: larger lambda front-loads schedule
    Q = 1000.0
    T = 5
    S = np.zeros(T)
    eta = np.ones(T) * 0.01
    alpha_bar = np.zeros(T)
    sigma2 = np.ones(T) * 0.01
    psi = 100.0
    alpha_bar_T = 0.0
    rho_D_net = np.ones(T) * 10000.0

    prob1, x1, y1, u1 = build_qp(
        Q, T, S, eta, alpha_bar, sigma2, psi, alpha_bar_T, 1.0, rho_D_net
    )
    prob1.solve(solver=cp.OSQP)
    
    prob2, x2, y2, u2 = build_qp(
        Q, T, S, eta, alpha_bar, sigma2, psi, alpha_bar_T, 2.0, rho_D_net
    )
    prob2.solve(solver=cp.OSQP)
    
    # Larger lambda means more front-loaded
    assert x2.value[0] > x1.value[0] + 1e-4

def test_t4_closed_form():
    # T4: Unconstrained QP matches closed form
    Q = 1000.0
    T = 10
    S = np.zeros(T)
    eta_val = 0.01
    eta = np.ones(T) * eta_val
    alpha_bar = np.zeros(T)
    sigma2_val = 0.005
    sigma2 = np.ones(T) * sigma2_val
    psi = 100.0
    alpha_bar_T = 0.0
    lambda_imp = 1.0
    rho_D_net = np.ones(T) * 10000.0

    prob, x, y, u = build_qp(
        Q, T, S, eta, alpha_bar, sigma2, psi, alpha_bar_T, lambda_imp, rho_D_net
    )
    prob.solve(solver=cp.OSQP)
    
    # \cosh\omega = 1 + \lambda \sigma^2 / (2 \eta)
    cosh_omega = 1 + lambda_imp * sigma2_val / (2 * eta_val)
    omega = np.arccosh(cosh_omega)
    
    # y_t = Q \sinh(\omega(T+1-t)) / \sinh(\omega T)
    # y_1 is index 0 in the array
    # y_t is index t-1 in the array
    y_expected = np.array([Q * np.sinh(omega * (T + 1 - (t + 1))) / np.sinh(omega * T) for t in range(T+1)])
    
    np.testing.assert_allclose(y.value, y_expected, atol=1e-3)
