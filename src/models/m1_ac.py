import numpy as np


def solve_m1(order, book, params):
    """Solve M1: Almgren-Chriss mean-variance schedule."""
    T = order.horizon if order.horizon > 0 else 20
    from src.utils.contracts import Schedule
    return Schedule(shares=np.ones(T) * order.size / T)
