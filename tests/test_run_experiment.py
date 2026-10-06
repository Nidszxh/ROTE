import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_experiment as rx


def test_usage_no_args(capsys):
    code = rx.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "use" in out


def test_unknown_command(capsys):
    code = rx.main(["nope"])
    out = capsys.readouterr().out
    assert code == 2
    assert "unknown command" in out
    assert "use" in out


def test_frontier_command(capsys, monkeypatch):
    import src.reports.generate_report as report

    monkeypatch.setattr(report, "generate_all_reports_and_figures", lambda: None)
    assert rx.main(["frontier"]) == 0
    assert "frontier" in capsys.readouterr().out


def test_calibrate_command(capsys, require_dataset):
    assert rx.main(["calibrate"]) == 0
    assert "Calibrating" in capsys.readouterr().out


def test_check_formulation_command(capsys):
    assert rx.main(["check-formulation"]) == 0
    assert "Checking" in capsys.readouterr().out
