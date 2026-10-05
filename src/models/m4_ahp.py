import numpy as np


def solve_m4(order, book, params):
    """Solve M4: Strategy selection."""
    T = order.horizon if order.horizon > 0 else 20
    from src.utils.contracts import Schedule
    return Schedule(shares=np.ones(T) * order.size / T)
