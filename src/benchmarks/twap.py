import numpy as np


def twap_schedule(size, horizon):
    T = horizon if horizon > 0 else 20
    return np.ones(T) * size / T
