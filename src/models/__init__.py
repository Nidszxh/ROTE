"""
ROTE Optimization Models (M1-M4).
Provides unified access to:
- M1 (Almgren-Chriss NLP/QP)
- M2 (LOB LP with shadow prices)
- M3 (Fixed-charge Mixed-Integer Program)
- M4 (Analytic Hierarchy Process Strategy Selection)
"""

from src.models.m1_ac import (
    ac_classical_closed_form,
    ac_classical_cvxpy,
    solve_m1,
)
from src.models.m2_lp import (
    build_m2,
    solve_m2,
)
from src.models.m3_mip import (
    build_m3,
    solve_m3,
)
from src.models.m4_ahp import (
    ahp_consistency_ratio,
    ahp_weights,
    solve_m4,
)

__all__ = [
    "ac_classical_closed_form",
    "ac_classical_cvxpy",
    "ahp_consistency_ratio",
    "ahp_weights",
    "build_m2",
    "build_m3",
    "solve_m1",
    "solve_m2",
    "solve_m3",
    "solve_m4",
]
