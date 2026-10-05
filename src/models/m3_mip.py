import numpy as np


def solve_m3(order, book, params):
    """Solve M3: Fixed-charge child-order scheduling."""
    T = order.horizon if order.horizon > 0 else 20
    from src.utils.contracts import Schedule
    return Schedule(shares=np.ones(T) * order.size / T)
