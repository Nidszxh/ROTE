from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np


@dataclass(frozen=True)
class Order:
    side: str
    size: float
    horizon: int
    params: dict


@dataclass(frozen=True)
class Schedule:
    shares: np.ndarray  # shares per period/slice

    def __post_init__(self):
        object.__setattr__(self, 'shares', np.asarray(self.shares, dtype=float))


@dataclass(frozen=True)
class CostReport:
    shortfall_bps: float
    std: float
    trades: int

    def to_dict(self) -> dict:
        return {
            'shortfall_bps': self.shortfall_bps,
            'std': self.std,
            'trades': self.trades,
        }
