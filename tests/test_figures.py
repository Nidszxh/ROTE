import matplotlib

matplotlib.use("Agg")

from data import figures


def test_generate_all_figures(synthetic_lob, tmp_path):
    lob = synthetic_lob
    boundaries = [0, 60, 120, 180, 240, 300]
    cfg = {"period": {"rows_per_period": 20}, "execution": {"rho": 0.25, "pi": 0.005}}
    paths = figures.generate_all_audit_figures(lob, boundaries, cfg, output_dir=tmp_path)
    assert len(paths) == 6
    for p in paths:
        assert p.exists()
        assert p.stat().st_size > 0
