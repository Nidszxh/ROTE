import numpy as np
import pytest

from data import audit, loader
from data.audit import detect_scale_exponent


@pytest.mark.A1
def test_scale_recovery_detects_k6():
    x_synth = np.zeros((10, 149))
    x_synth[:, 0] = 0.2554
    x_synth[:, 2] = 0.2550
    res = detect_scale_exponent(x_synth)
    assert res["k_decpre"] == 6


@pytest.mark.A4
def test_book_integrity_reconstruction():
    x_synth = np.zeros((5, 149))
    for level in range(10):
        base = level * 4
        x_synth[:, base] = 0.2500 + level * 0.0001
        x_synth[:, base + 1] = 0.0500
        x_synth[:, base + 2] = 0.2490 - level * 0.0001
        x_synth[:, base + 3] = 0.0500
    lob = loader.reconstruct_lob(x_synth, k_decpre=6)
    assert np.all(lob["Pa1"] > lob["Pb1"])
    assert np.all(lob["S"] > 0)
    assert np.all(lob["Da"] > 0)
    assert np.all(lob["Db"] > 0)
    assert np.all(np.abs(lob["OBI"]) <= 1.0)


def test_stock_boundaries_detection():
    m = np.array([25.0, 25.1, 25.0, 12.5, 12.6, 17.0, 17.1])
    jumps = loader.find_stock_boundaries(m, threshold=1.0)
    assert len(jumps) == 2
    assert jumps == [2, 4]


def test_detect_scale_exponent_none():
    x = np.array([[0.1, 0.2]] * 5)
    res = detect_scale_exponent(x)
    assert res["k_decpre"] is None


def test_audit_boundaries_returns_segment_edges():
    m = np.array([25.0, 25.1, 25.0, 12.5, 12.6, 17.0, 17.1])
    results = {"checks": {}, "findings": {}}
    edges = audit._audit_boundaries({"M": m}, results)
    assert edges == [0, 3, 5, 7]
    assert "3 blocks" in results["findings"]["A2"]
    assert results["checks"]["A2"] == "warn"


def test_audit_windows_reports_shortfall():
    results = {"checks": {}, "findings": {}, "splits": {}}
    audit._audit_windows(
        {"audit": {"min_effective_windows": 100}},
        [],
        [0, 10],
        6,
        20,
        100,
        400,
        0,
        0,
        results,
    )
    assert results["checks"]["A6"] == "warn"
    assert "INSUFFICIENT" in results["findings"]["A6"]
    assert "0 < required 100" in results["findings"]["A6"]


def test_failed_audit_preserves_existing_report(tmp_path, monkeypatch):
    monkeypatch.delenv("ROTE_DATA_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "README.md"
    report.write_text("last good report")
    cfg = {
        "dataset": {"root": str(tmp_path / "missing")},
        "audit": {"report": str(report), "decision_log": str(tmp_path / "dl.md")},
        "period": {"horizon": 20, "rows_per_period": 20},
        "splits": {"file": str(tmp_path / "splits.yaml")},
    }
    res = audit.run_audit(cfg)
    assert res["status"] == "error"
    assert res["report_written"] is False
    assert report.read_text() == "last good report"
