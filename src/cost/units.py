"""Unit conversion (section 5.2). One home for 10^4."""


def eta0_tilde(eta0: float, M0: float) -> float:
    if M0 == 0:
        raise ValueError("M0 must be non-zero")
    return eta0 / M0


def sigma_tilde(sigma: float, M0: float) -> float:
    if M0 == 0:
        raise ValueError("M0 must be non-zero")
    return sigma / M0


def lambda_imp(lambda_raw: float, Q: float, M0: float) -> float:
    return lambda_raw * Q * M0
