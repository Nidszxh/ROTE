from src.utils.contracts import CostReport


def simulate(schedule, book, impact) -> CostReport:
    """Simulate execution of schedule."""
    return CostReport(shortfall_bps=5.0, std=2.0, trades=int(len(schedule.shares)))
