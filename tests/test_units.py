import math

import pytest

from cost.units import eta0_tilde, lambda_imp, sigma_tilde

pytestmark = pytest.mark.T13


def test_eta0_tilde_basic():
    assert eta0_tilde(10.0, 2.0) == 5.0


def test_sigma_tilde_basic():
    assert sigma_tilde(4.0, 2.0) == 2.0


def test_lambda_imp_basic():
    assert lambda_imp(2.0, 5.0, 3.0) == 30.0


def test_m0_zero_raises():
    with pytest.raises(ValueError):
        eta0_tilde(1.0, 0.0)
    with pytest.raises(ValueError):
        sigma_tilde(1.0, 0.0)


def test_identity_section52():
    lam_raw = 0.5
    sigma = 0.02
    eta0 = 0.001
    Q = 10.0
    M0 = 1.5
    D_bar = 100.0
    theta = Q / D_bar if D_bar > 0 else 1.0
    eta = eta0 * theta / Q
    lam_impv = lambda_imp(lam_raw, Q, M0)
    sig_t = sigma_tilde(sigma, M0)
    eta_t0 = eta0_tilde(eta0, M0)
    lhs = lam_impv * sig_t * sig_t / (eta_t0 * theta)
    rhs = lam_raw * sigma * sigma / eta
    assert math.isclose(lhs, rhs, rel_tol=1e-12)
