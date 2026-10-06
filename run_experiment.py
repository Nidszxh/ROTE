#!/usr/bin/env python
from __future__ import annotations

import json
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

USAGE = (
    "ROTE: use setup|audit|freeze-splits|calibrate|evaluate|frontier|"
    "check-formulation|figures|full "
    "[setup options] [--test --confirm]"
)


def _cmd_setup(args: list[str]) -> int:
    from src.data.setup import setup_dataset

    archive = None
    url = None
    verify_only = False
    force = False
    i = 0
    while i < len(args):
        option = args[i]
        if option == "--verify-only":
            verify_only = True
        elif option == "--force":
            force = True
        elif option in {"--url", "--zip"}:
            if i + 1 >= len(args):
                print(f"{option} requires a value")
                return 2
            if option == "--url":
                url = args[i + 1]
            else:
                archive = Path(args[i + 1])
            i += 1
        else:
            print(f"setup: unknown option {option!r}")
            return 2
        i += 1
    try:
        errors = setup_dataset(archive=archive, url=url, verify_only=verify_only, force=force)
    except (OSError, ValueError) as exc:
        print(f"setup failed: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Dataset files verified.")
    if not verify_only:
        print("Processed cache is ready under data/processed/.")
    return 0


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
    from pathlib import Path

    from data import figures, loader

    _, lob, boundaries = loader.load_train_lob(cfg)
    paths = figures.generate_all_audit_figures(lob, boundaries, cfg)
    print(f"Generated {len(paths)} audit and microstructure figures in results/figures/:")
    for p in paths:
        print(f"  - {p}")

    eval_md = Path("results/EVALUATION_REPORT.md")
    if eval_md.is_file():
        from src.reports.paper_figures import (
            generate_research_paper_figure,
            parse_evaluation_markdown,
        )

        s_df, c_df = parse_evaluation_markdown(eval_md)
        paper_fig = generate_research_paper_figure(s_df, c_df)
        print(f"Generated publication research paper figure:\n  - {paper_fig}")

    return 0


def _cmd_calibrate(cfg: dict) -> int:
    from pathlib import Path

    from cost.quadratic import calibrate_eta0_for_stock
    from data import loader

    print("Calibrating cost model (section 5.2)...")
    _, lob, boundaries = loader.load_train_lob(cfg)

    estimates = {}
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        n_rows = end - start
        # Use first 60% of the stock's data for calibration
        calib_end = start + int(0.6 * n_rows)

        ask_prices = lob["Pa"][start:calib_end]
        ask_volumes = lob["Va"][start:calib_end]

        eta0 = calibrate_eta0_for_stock(ask_prices, ask_volumes)
        estimates[str(i + 1)] = eta0
        print(f"Stock {i + 1} eta_0: {eta0:.6e}")

    output = Path("results/tables/calibration.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"eta_0": estimates}, indent=2) + "\n", encoding="utf-8")
    print(f"Calibration saved to {output}")
    print("Calibration complete.")
    return 0


def _cmd_evaluate(cfg: dict, args: list[str]) -> int:
    from src.loader.loader import STOCK_NAMES
    from src.reports.evaluation_report import generate_evaluation_report

    evaluation = cfg.get("execution", {}).get("evaluation", {})
    theta = cfg.get("execution", {}).get("theta", [1.0])
    validation_days = int(evaluation.get("day_blocks", {}).get("validation_days", 2))
    if "--test" in args:
        if "--confirm" not in args:
            print("evaluate: --test requires --confirm to access frozen test days 8–9")
            return 2
        days = list(range(8, 8 + validation_days))
        allow_test = True
    else:
        # Default to validation split (days 6–7)
        days = list(range(6, 6 + validation_days))
        allow_test = False
    path = generate_evaluation_report(STOCK_NAMES, days, theta, allow_test=allow_test)
    print(f"Evaluation report written to {path}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE)
        return 0
    cmd = args[0]
    if cmd == "setup":
        return _cmd_setup(args[1:])
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
        from config import load

        return _cmd_calibrate(load())
    if cmd == "evaluate":
        from config import load

        return _cmd_evaluate(load(), args[1:])
    if cmd == "frontier":
        if "--test" in args and "--confirm" not in args:
            print("frontier: --test requires --confirm flag")
            return 2
        from src.reports.generate_report import generate_all_reports_and_figures

        if "--test" in args:
            generate_all_reports_and_figures(day=8, allow_test=True)
        else:
            generate_all_reports_and_figures()
        print("frontier: generated results/figures and results/MODEL_EXECUTION_REPORT.md")
        return 0
    if cmd == "check-formulation":
        import subprocess

        print("Checking formulation against section 5.4...")
        res = subprocess.run([sys.executable, "-m", "pytest", "tests/test_optimizer.py", "-v"])
        if res.returncode == 0:
            print("check-formulation: SUCCESS. Section 5.4 vs qp_schedule.py validated.")
        else:
            print("check-formulation: FAILED.")
        return res.returncode
    if cmd in {"-h", "--help", "help"}:
        print(USAGE)
        return 0
    if cmd == "full":
        if len(args) > 1 and args[1:] != ["--test", "--confirm"]:
            print("full accepts only --test --confirm")
            return 2
        if "--test" in args and "--confirm" not in args:
            print("full --test requires --confirm")
            return 2
        from config import load

        cfg = load()
        for handler in (_cmd_audit, _cmd_calibrate, _cmd_figures):
            if handler(cfg) != 0:
                return 1
        from src.reports.generate_report import generate_all_reports_and_figures

        if "--test" in args:
            generate_all_reports_and_figures(day=8, allow_test=True)
        else:
            generate_all_reports_and_figures()
        return 0
    print(f"run_experiment: unknown command {cmd!r}")
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
