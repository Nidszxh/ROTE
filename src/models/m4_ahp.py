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
    """Select a candidate schedule with a four-criterion AHP.

    ``params`` may provide ``candidate_schedules`` and ``candidate_criteria``.
    Criteria are ordered cost, risk, completion, simplicity; lower is better
    for the first two and higher is better for the latter two.  A 4x4
    reciprocal ``criteria_matrix`` controls the criterion weights.
    """
    if order.size <= 0:
        raise ValueError(f"Order size must be positive, got {order.size}")
    if order.horizon < 1:
        raise ValueError(f"Order horizon must be >= 1, got {order.horizon}")

    settings = dict(params or {})
    candidates = settings.get("candidate_schedules")
    if candidates is None:
        # Preserve the useful baseline contract when no decision inputs exist.
        return Schedule(np.full(order.horizon, order.size / order.horizon, dtype=float))
    if not isinstance(candidates, Mapping) or not candidates:
        raise ValueError("candidate_schedules must be a non-empty mapping")

    names = list(candidates)
    arrays = {}
    for name in names:
        value = candidates[name]
        values = value.shares if isinstance(value, Schedule) else np.asarray(value, dtype=float)
        if values.shape != (order.horizon,) or np.any(~np.isfinite(values)) or np.any(values < 0):
            raise ValueError(
                f"candidate {name!r} must contain {order.horizon} finite non-negative shares"
            )
        if not np.isclose(values.sum(), order.size, rtol=1e-6, atol=1e-6):
            raise ValueError(f"candidate {name!r} must conserve the order size")
        arrays[name] = values

    criteria = settings.get("candidate_criteria")
    if criteria is None:
        raise ValueError("candidate_criteria is required with candidate_schedules")
    if not isinstance(criteria, Mapping) or set(criteria) != set(names):
        raise ValueError("candidate_criteria must contain exactly the candidate names")
    matrix = settings.get("criteria_matrix", np.ones((4, 4), dtype=float))
    matrix, n = _validate_ahp_matrix(matrix)
    if n != 4 or not np.allclose(matrix * matrix.T, 1.0, atol=1e-8):
        raise ValueError("criteria_matrix must be a 4x4 reciprocal positive matrix")
    criterion_weights = ahp_weights(matrix)
    values = np.asarray([criteria[name] for name in names], dtype=float)
    if values.shape != (len(names), 4) or np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("each candidate must have four positive finite criterion values")
    priorities = np.empty_like(values)
    priorities[:, :2] = 1.0 / values[:, :2]
    priorities[:, 2:] = values[:, 2:]
    priorities /= priorities.sum(axis=0, keepdims=True)
    scores = priorities @ criterion_weights
    winner = int(np.argmax(scores))
    return Schedule(arrays[names[winner]])


def ahp_sensitivity(
    candidate_criteria: np.ndarray,
    criteria_matrix: np.ndarray,
    weight_grid: np.ndarray | None = None,
) -> np.ndarray:
    """Return winners for a grid of criterion-weight perturbations."""
    values = np.asarray(candidate_criteria, dtype=float)
    matrix, n = _validate_ahp_matrix(criteria_matrix)
    if n != 4 or values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("sensitivity inputs must contain four criteria")
    default_grid = ahp_weights(matrix)[None, :]
    grid = np.asarray(weight_grid if weight_grid is not None else default_grid, dtype=float)
    if grid.ndim != 2 or grid.shape[1] != 4 or np.any(grid <= 0):
        raise ValueError("weight_grid must be a positive (n, 4) array")
    priorities = np.column_stack((1.0 / values[:, :2], values[:, 2:]))
    priorities /= priorities.sum(axis=0, keepdims=True)
    return np.argmax(priorities @ (grid / grid.sum(axis=1, keepdims=True)).T, axis=0)
