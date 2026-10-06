# ROTE presentation outline

## 1. Motivation

Large orders trade off visible-book impact against timing risk. ROTE studies that trade-off on
FI-2010 using event-time limit-order-book snapshots.

## 2. Data and safeguards

- 10 levels per side, five stocks, ten trading days.
- Labels are excluded from the execution path.
- DecPre scale recovery and book integrity are verified by the A0-A8 audit.
- Calibration, validation, test, and reserve periods are frozen in configuration.

## 3. Shared execution contract

```text
load_day -> Order -> solve -> Schedule -> simulate -> CostReport
```

The simulator walks the visible book, applies configured footprint/resilience, enforces the
participation cap, and uses only snapshots inside the selected horizon.

## 4. Optimisation menu

1. M1: Almgren-Chriss mean-variance liquidation.
2. M2: book-aware allocation with depth constraints and risk.
3. M3: fixed-charge mixed-integer child-order scheduling.
4. M4: AHP strategy selection with a consistency ratio.

## 5. Benchmarks and evaluation

TWAP, depth-proportional, and imbalance-weighted VWAP-proxy schedules are evaluated through the
same simulator. Cost, timing-risk standard deviation, and active trades are reported together.

## 6. Interactive tool

The Streamlit UI provides Data, Statistics, Optimiser, Compare, and Decision panels. The
optimiser uses urgency `omega` for the default M1 frontier and exposes participation and lot
controls.

## 7. Current evidence

The reproducible audit and benchmark outputs are:

- [`data/README.md`](../data/README.md)
- [`results/MODEL_EXECUTION_REPORT.md`](../results/MODEL_EXECUTION_REPORT.md)
- [`results/figures/`](../results/figures/)

## 8. Limitations and conclusion

This is conditional historical replay, not a market-impact forecast. Queue position, hidden
liquidity, and endogenous response are unobserved. Conclusions therefore apply to the FI-2010
event-time sample and should not be generalized to other venues without new validation.
