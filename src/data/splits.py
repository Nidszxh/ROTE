"""Splits (section 4.3)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

import yaml

from config import require


class FreezeResult(TypedDict):
    status: str
    path: str


def freeze_splits(config: Mapping[str, Any]) -> FreezeResult:
    out_path = Path(require(config, "splits", "file"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    horizon = int(require(config, "period", "horizon"))
    rows_per_period = int(require(config, "period", "rows_per_period"))
    purge_gap_rows = horizon * rows_per_period
    data = {
        "split_version": 1,
        "construction": "day_blocks",
        "purge_gap_rows": purge_gap_rows,
        "apply_within": "stock_segment",
        "generalisation": "none",
        "splits": {
            "calibration": {"days": [1, 2, 3, 4, 5], "share": 0.56},
            "validation": {"days": [6, 7], "share": 0.22},
            "test": {"days": [8, 9], "share": 0.22},
        },
        "reserve": {"days": [10]},
    }
    out_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return FreezeResult(status="written", path=str(out_path))
