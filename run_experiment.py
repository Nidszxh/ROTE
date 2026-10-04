#!/usr/bin/env python
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

USAGE = "ROTE: use audit|freeze-splits|calibrate|frontier|check-formulation|figures|full"


def _cmd_audit(cfg: dict) -> int:
    from data.audit import run_audit

    res = run_audit(cfg)
    if res.get("report_written"):
        print(f"Audit completed: {res['status']}. Report written to {res['report']}")
    else:
        print(
            f"Audit completed: {res['status']}. {res['report']} left unchanged "
            "(the last good report is preserved until the audit completes)."
        )
    for chk, status in res.get("checks", {}).items():
        print(f"  [{chk}] {status}: {res.get('findings', {}).get(chk, '')}")
    if res.get("error"):
        print(f"  error: {res['error']}")
    return 0 if res.get("status") == "complete" else 1


def _cmd_freeze_splits(cfg: dict) -> int:
    from data.splits import freeze_splits

    res = freeze_splits(cfg)
    print(res)
    return 0 if res.get("status") == "written" else 1


def _cmd_figures(cfg: dict) -> int:
    from data import figures, loader

    _, lob, boundaries = loader.load_train_lob(cfg)
    paths = figures.generate_all_audit_figures(lob, boundaries, cfg)
    print(f"Generated {len(paths)} audit and microstructure figures in results/figures/:")
    for p in paths:
        print(f"  - {p}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE)
        return 0
    cmd = args[0]
    if cmd == "audit":
        from config import load

        return _cmd_audit(load())
    if cmd == "freeze-splits":
        from config import load

        return _cmd_freeze_splits(load())
    if cmd == "figures":
        from config import load

        return _cmd_figures(load())
    if cmd == "calibrate":
        print("calibrate: (stub)")
        return 0
    if cmd == "frontier":
        print("frontier: (stub)")
        return 0
    if cmd == "check-formulation":
        print("check-formulation: (stub) Section 5.4 vs qp_schedule.py")
        return 0
    if cmd in {"-h", "--help", "help"}:
        print(USAGE)
        return 0
    print(f"run_experiment: unknown command {cmd!r}")
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
