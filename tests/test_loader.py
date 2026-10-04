import numpy as np
import pytest

from data import loader


def test_load_fi2010_file(tmp_path):
    p = tmp_path / "test.txt"
    lines = []
    for i in range(149):
        tokens = []
        for j in range(5):
            tokens.append(f"{i * 0.001 + j * 0.0001}")
        lines.append(" ".join(tokens))
    p.write_text("\n".join(lines))
    X, meta = loader.load_fi2010_file(p)
    assert X.shape[0] == 5
    assert meta["n_samples"] == 5


def test_load_fi2010_file_wrong_rows(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("0 1 2\n")
    with pytest.raises(ValueError):
        loader.load_fi2010_file(p)


def test_load_fi2010_file_ragged(tmp_path):
    p = tmp_path / "test.txt"
    lines = []
    for i in range(149):
        if i == 1:
            lines.append("0 1")
        else:
            lines.append("0 1 2")
    p.write_text("\n".join(lines))
    with pytest.raises(ValueError):
        loader.load_fi2010_file(p)


def test_recover_scale():
    s = loader.recover_scale(k_decpre=6)
    assert s["scale_factor_price"] == 100.0
    assert s["scale_factor_vol"] == 1_000_000.0


def test_reconstruct_lob():
    n = 2
    X = np.zeros((n, 149), dtype=float)
    for t in range(n):
        for level in range(10):
            base = level * 4
            X[t, base] = 0.2500 + level * 0.0001
            X[t, base + 1] = 0.0500
            X[t, base + 2] = 0.2490 - level * 0.0001
            X[t, base + 3] = 0.0500
    lob = loader.reconstruct_lob(X, k_decpre=6)
    assert np.all(lob["Pa1"] > lob["Pb1"])
    assert np.all(lob["S"] > 0)


def test_find_stock_boundaries():
    m = np.array([25.0, 25.1, 25.0, 12.5, 12.6, 17.0, 17.1])
    jumps = loader.find_stock_boundaries(m, threshold=1.0)
    assert jumps == [2, 4]


def test_segment_boundaries_are_edges_not_jumps():
    edges = loader.segment_boundaries([2, 4], 7)
    assert edges == [0, 3, 5, 7]
    assert len(edges) - 1 == 3


def test_segment_boundaries_drops_out_of_range():
    assert loader.segment_boundaries([], 10) == [0, 10]
    assert loader.segment_boundaries([0, 9, 20], 10) == [0, 1, 10]


def test_sigma_min_floor_is_non_negative():
    returns = np.array([-0.01, -0.002, 0.0, 0.003, 0.02])
    floor = loader.sigma_min_floor(returns)
    assert floor > 0.0
    assert np.isclose(floor, np.percentile(np.abs(returns[[0, 1, 3, 4]]), 10.0))


def test_sigma_min_floor_empty_and_flat():
    assert loader.sigma_min_floor(np.array([])) == 0.0
    assert loader.sigma_min_floor(np.zeros(5)) == 0.0


def test_period_log_returns():
    m = np.exp(np.linspace(0.0, 0.02, 40))
    r = loader.period_log_returns(m, 20)
    assert r.shape == (1,)
    assert loader.period_log_returns(m, 1).size == 0
    assert loader.period_log_returns(m[:5], 20).size == 0


def test_resolve_data_root(tmp_path, monkeypatch):
    d = tmp_path / "data_dir"
    d.mkdir()
    cfg = {"dataset": {"root": str(d)}}
    assert loader.resolve_data_root(cfg) == d
