import numpy as np
import pytest

from src.loader.loader import resolve_data_root


@pytest.fixture
def require_dataset():
    try:
        resolve_data_root({})
    except FileNotFoundError:
        pytest.skip("FI-2010 dataset is not available; run `setup` first")


@pytest.fixture
def synthetic_lob():
    n = 300
    Pa = np.zeros((n, 10), dtype=float)
    Va = np.zeros((n, 10), dtype=float)
    Pb = np.zeros((n, 10), dtype=float)
    Vb = np.zeros((n, 10), dtype=float)
    for t in range(n):
        for level in range(10):
            base = level * 0.0005
            Pa[t, level] = 25.00 + base + (t % 5) * 0.0001
            Va[t, level] = 5000.0 + level * 100
            Pb[t, level] = 24.98 - base - (t % 5) * 0.0001
            Vb[t, level] = 5000.0 + level * 100
    Pa1 = Pa[:, 0]
    Pb1 = Pb[:, 0]
    M = (Pa1 + Pb1) / 2.0
    S = Pa1 - Pb1
    Da = Va.sum(axis=1)
    Db = Vb.sum(axis=1)
    denom = Da + Db
    OBI = np.zeros(n)
    mask = denom > 0
    OBI[mask] = (Db[mask] - Da[mask]) / denom[mask]
    return {
        "Pa": Pa,
        "Va": Va,
        "Pb": Pb,
        "Vb": Vb,
        "Pa1": Pa1,
        "Pb1": Pb1,
        "M": M,
        "S": S,
        "Da": Da,
        "Db": Db,
        "OBI": OBI,
    }


@pytest.fixture
def tmp_config(tmp_path):
    cfg = {
        "run": {"name": "test"},
        "proposal": {"path": "PROPOSAL.md", "sha256": None},
        "dataset": {
            "name": "FI-2010",
            "root": str(tmp_path / "data"),
            "file": "Train.txt",
            "source": None,
            "scale_exponent": 6,
        },
        "audit": {
            "report": str(tmp_path / "report.md"),
            "decision_log": str(tmp_path / "dec.md"),
            "burn_in_rows": 10,
            "min_effective_windows": 1,
            "checks": ["A0"],
        },
        "period": {"horizon": 2, "rows_per_period": 10},
        "splits": {"file": str(tmp_path / "splits.yaml")},
    }
    return cfg
