from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from src.utils.contracts import Order, Schedule

# Saaty Random Index (RI) table for matrix dimensions 1 through 10
_SAATY_RI_TABLE: dict[int, float] = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


def _validate_ahp_matrix(matrix: np.ndarray) -> tuple[np.ndarray, int]:
    """Validate pairwise comparison matrix dimensions and positivity."""
    arr = np.asarray(matrix, dtype=float)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError(f"AHP comparison matrix must be 2D square, got shape {arr.shape}")
    n = arr.shape[0]
    if n < 1:
        raise ValueError("AHP matrix dimension must be at least 1")
    if not np.all(np.isfinite(arr)):
        raise ValueError("AHP matrix contains non-finite values (NaN/Inf)")
    if np.any(arr <= 0):
        raise ValueError(
            "All elements in an AHP pairwise comparison matrix must be strictly positive"
        )
    return arr, n


def _principal_eigen(matrix: np.ndarray) -> tuple[float, np.ndarray, int]:
    """
    Extract principal eigenvalue and corresponding eigenvector for an AHP matrix.
    Eliminates duplicated eigensolver calls across weights and consistency ratio.
    """
    arr, n = _validate_ahp_matrix(matrix)
    if n == 1:
        return 1.0, np.array([1.0], dtype=float), 1

    eigenvalues, eigenvectors = np.linalg.eig(arr)
    max_idx = int(np.argmax(np.real(eigenvalues)))
    lambda_max = float(np.real(eigenvalues[max_idx]))

    # Perron-Frobenius theorem guarantees a positive eigenvector for positive matrices;
    # solvers may return it with arbitrary overall negative sign, so take abs.
    raw_weights = np.abs(np.real(eigenvectors[:, max_idx]))
    weight_sum = np.sum(raw_weights)
    weights = raw_weights / weight_sum if weight_sum > 0 else np.full(n, 1.0 / n)

    return lambda_max, weights, n


def ahp_consistency_ratio(matrix: np.ndarray) -> tuple[float, bool]:
    """
    Calculate the Analytic Hierarchy Process (AHP) Consistency Ratio (CR).

    Parameters
    ----------
    matrix : np.ndarray
        Pairwise positive reciprocal comparison matrix (n x n).

    Returns
    -------
    tuple[float, bool]
        (Consistency Ratio, is_consistent) where is_consistent is True if CR < 0.10.
    """
    lambda_max, _, n = _principal_eigen(matrix)

    if n <= 2:
        return 0.0, True

    ci = (lambda_max - n) / (n - 1)
    # Numerical tolerance safeguard
    ci = max(0.0, ci)

    ri = _SAATY_RI_TABLE.get(n, 1.49)
    cr = float(ci / ri) if ri > 0 else 0.0

    return cr, cr < 0.10


def ahp_weights(matrix: np.ndarray) -> np.ndarray:
    """
    Compute normalized priority weights using the principal eigenvector of an AHP matrix.

    Parameters
    ----------
    matrix : np.ndarray
        Pairwise comparison matrix (n x n).

    Returns
    -------
    np.ndarray
        Normalized priority weight vector summing to 1.0.
    """
    _, weights, _ = _principal_eigen(matrix)
    return weights


def solve_m4(
    order: Order,
    book: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
) -> Schedule:
    """
    AHP Multi-Criteria Decision Framework (M4).

    Produces a valid baseline execution schedule while the pairwise
    preference evaluation is driven interactively in the Decision interface.
    """
    if order.size <= 0:
        raise ValueError(f"Order size must be positive, got {order.size}")
    if order.horizon < 1:
        raise ValueError(f"Order horizon must be >= 1, got {order.horizon}")

    # Default uniform schedule for M4 wrapper
    shares = np.full(order.horizon, order.size / order.horizon, dtype=float)
    return Schedule(shares=shares)
