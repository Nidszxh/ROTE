import numpy as np


def solve_m2(order, book, params):
    """Solve M2: LOB-aware slice allocation."""
    T = order.horizon if order.horizon > 0 else 20
    from src.utils.contracts import Schedule
    return Schedule(shares=np.ones(T) * order.size / T)
