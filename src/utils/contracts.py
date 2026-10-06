from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Order:
    side: str
    size: float
    horizon: int
    params: dict


@dataclass(frozen=True)
class Schedule:
    shares: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "shares", np.asarray(self.shares, dtype=float))


@dataclass(frozen=True)
class CostReport:
    shortfall_bps: float
    std: float
    trades: int
    half_spread_bps: float = 0.0
    book_walk_bps: float = 0.0
    timing_bps: float = 0.0
    sweep_exec_bps: float = 0.0
    sweep_timing_bps: float = 0.0
    penalty_bps: float = 0.0
    inventory_risk: float = 0.0
    unfilled_shares: float = 0.0
    cash_paid: float = 0.0
    spend: float = 0.0

    def to_dict(self) -> dict:
        return {
            "shortfall_bps": self.shortfall_bps,
            "std": self.std,
            "trades": self.trades,
            "half_spread_bps": self.half_spread_bps,
            "book_walk_bps": self.book_walk_bps,
            "timing_bps": self.timing_bps,
            "sweep_exec_bps": self.sweep_exec_bps,
            "sweep_timing_bps": self.sweep_timing_bps,
            "penalty_bps": self.penalty_bps,
            "inventory_risk": self.inventory_risk,
            "unfilled_shares": self.unfilled_shares,
            "cash_paid": self.cash_paid,
            "spend": self.spend,
        }
