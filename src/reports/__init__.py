"""
ROTE Visualization and Model Reporting Package.
Provides publication-grade visualizations for limit order book microstructure,
optimization models (M1-M4), benchmark frontiers, and executive reports.
"""

from src.reports.generate_report import generate_all_reports_and_figures
from src.reports.visualizations import (
    plot_ahp_ranking,
    plot_benchmark_frontier,
    plot_lob_ladder,
    plot_m1_frontier,
    plot_m2_diagnostics,
    plot_m3_tradeoff,
    plot_microstructure_analytics,
)

__all__ = [
    "generate_all_reports_and_figures",
    "plot_ahp_ranking",
    "plot_benchmark_frontier",
    "plot_lob_ladder",
    "plot_m1_frontier",
    "plot_m2_diagnostics",
    "plot_m3_tradeoff",
    "plot_microstructure_analytics",
]
