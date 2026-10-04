from pathlib import Path

from data.splits import freeze_splits


def test_freeze_splits(tmp_path):
    cfg = {
        "splits": {"file": str(tmp_path / "splits.yaml")},
        "period": {"horizon": 20, "rows_per_period": 20},
    }
    res = freeze_splits(cfg)
    assert res["status"] == "written"
    assert Path(res["path"]).exists()
