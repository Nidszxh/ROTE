# ROTE final report

## Scope

ROTE is a research implementation for risk-aware execution on FI-2010 limit-order-book data.
The project uses event time because the source files do not provide a reliable calendar-time
clock. Production loaders read the first 144 feature rows and never use the five labels.

The data audit confirms the DecPre representation, global `k_decpre=6` scale recovery, five
stock blocks, positive and monotone books, and the frozen calibration/validation/test split in
[`configs/splits.yaml`](../configs/splits.yaml). The current audit results are generated in
[`data/README.md`](../data/README.md).

## Execution model

The shared contract is:

```text
Order -> model.solve(...) -> Schedule -> simulate(...) -> CostReport
```

The simulator walks visible ask-side depth, applies the configured footprint/resilience
recursion, enforces the participation cap, and prices any residual inventory at the final
snapshot inside the horizon (`T-1`). It does not read a post-horizon snapshot and does not
pretend that the recorded book reacts to the simulated order.

## Models and benchmarks

- **M1**: Almgren-Chriss mean-variance liquidation, with a closed form and CVXPY cross-check.
- **M2**: Multi-level book allocation with participation constraints and a quadratic risk term.
- **M3**: Fixed-charge mixed-integer scheduling with minimum lots and an optional trade-count cap.
- **M4**: AHP consistency checking for strategy selection.
- **Benchmarks**: TWAP, depth-proportional, and imbalance-weighted VWAP proxy.

The Streamlit application exposes Data, Statistics, Optimiser, Compare, and Decision panels.
The report generator produces the current benchmark table and figures in
[`results/MODEL_EXECUTION_REPORT.md`](../results/MODEL_EXECUTION_REPORT.md).

## Reproducibility

```bash
export ROTE_DATA_ROOT="$HOME/data/FI-2010"
uv pip install -r pyproject.toml --extra dev
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
uv run --no-sync python run_experiment.py full --test --confirm
```

The calibration command writes one `eta_0` estimate per stock to
[`results/tables/calibration.json`](../results/tables/calibration.json). Test-split results
should be treated as a single confirmatory run and regenerated only when the run is intentionally
repeated.

## Limitations

The replay is conditional on the recorded book: queue position, hidden liquidity, and endogenous
market reaction are not observed. The VWAP implementation is a clearly labelled proxy because
FI-2010 has no continuous market-volume clock. Numerical results are evidence for this dataset
and event-time replay, not a claim about other venues or market regimes.
