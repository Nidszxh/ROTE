def test_contracts_import():
    from src.utils.contracts import CostReport, Order, Schedule
    s = Schedule(shares=[1, 2, 3])
    assert len(s.shares) == 3
    o = Order(side='buy', size=1000, horizon=20, params={})
    assert o.size == 1000
    r = CostReport(shortfall_bps=1.0, std=0.5, trades=5)
    assert r.trades == 5


def test_models_import():
    from src.models import m1_ac, m2_lp, m3_mip, m4_ahp
    assert hasattr(m1_ac, 'solve_m1')
    assert hasattr(m2_lp, 'solve_m2')
