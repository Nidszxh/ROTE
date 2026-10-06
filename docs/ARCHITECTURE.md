# ROTE System Architecture & Data Pipeline

ROTE is organized as an end-to-end, reproducible quantitative data-to-decision pipeline designed for limit-order-book execution research:

```text
+-----------------------------------------------------------------------------------+
|                               1. INGESTION & AUDIT                                |
|  Raw FI-2010 (DecPre) -> Cryptographic Audit (A0-A8, SHA-256) -> Clean LOB Arrays |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         2. CALIBRATION & MICROSTRUCTURE                           |
|  Calibration Split (Days 1-5): eta_0 Impact Parameter per Stock | Volatility Floor|
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                           3. OPTIMIZATION MODEL LAYER                             |
|  Immutable Order Spec -> Model Solver (Dimensionless Formulation) -> Schedule     |
|  - M1: Almgren-Chriss (Closed-Form & CVXPY QP)                                    |
|  - M2: Multi-Level LOB LP / Shadow Prices (CVXPY)                                 |
|  - M3: Fixed-Charge Mixed-Integer Program (CVXPY / HiGHS / SCIPY)                 |
|  - ROTE-Static: Arrival-State QP Ablation                                         |
|  - Baselines: TWAP, Accelerated TWAP', Immediate, Depth-Proportional, VWAP Proxy  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                           4. SIMULATION & DECOMPOSITION                           |
|  Schedule -> Book Walking Simulator (Catch-Up Rule + Resilience Recursion)        |
|  Output: CostReport (IS = Spread + Book Walk + Timing + Sweep Exec + Sweep Timing)|
+-----------------------------------------------------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
+---------------------------------------+ +-----------------------------------------+
|     5. AUTOMATED RESEARCH REPORTS     | |     6. INTERACTIVE STREAMLIT UI         |
| - Multi-Window Evaluation (Core)      | | app.py (Port 8501, 5 Tabs):             |
|   (176 Windows, Bootstrap CIs, Holm)  | | 1. Data Loader & LOB Ladder             |
| - Publication Figures (300 DPI)       | | 2. Descriptive Statistics & Analytics   |
|   (results/figures/*.png)             | | 3. Mathematical Optimization Solvers    |
| - EVALUATION_REPORT.md                | | 4. Multi-Model Benchmark Comparison     |
| - MODEL_EXECUTION_REPORT.md           | | 5. Decision Support (M4 AHP Scoring)    |
+---------------------------------------+ +-----------------------------------------+
```

---

## 1. Data Layer (`src/data/`, `src/loader/`)
- **Exclusion of Labels:** FI-2010 contains 144 microstructure features and 5 forward labels. The loader slices strictly `rows[:144]`, guaranteeing unsupervised execution conditions.
- **Scale Recovery ($k=6$):** Converts normalized DecPre features to euros and shares:
  $$\text{Price}_{\text{EUR}} = \text{stored} \times 100, \quad \text{Volume}_{\text{shares}} = \text{stored} \times 1,000,000$$
- **Stock Boundaries:** Segments the continuous file into the 5 Nordic equity blocks by identifying inter-stock price jumps ($> 1.00$ EUR).
- **Split Governance:** Calibration (Days 1–5), Validation (Days 6–7), Test (Days 8–9, gated with `--confirm`), Reserve (Day 10).

---

## 2. Microstructure & Calibration Layer (`src/cost/`, `src/impact/`, `src/stats/`)
- **Impact Calibration ($\eta_0$):** Calibrated on Days 1–5 by walking the visible depth ladder of each stock; saved to `results/tables/calibration.json`.
- **Volatility Floor ($\sigma_{\min}$):** Computed as the 10th percentile of period log-return magnitudes to prevent negative or zero-risk collapse on quiet books.
- **Liquidity Statistics:** Calculates mean spread (bps), gross depth, depth-by-level, and order book imbalance (OBI).

---

## 3. Mathematical Programming Layer (`src/models/`, `src/benchmarks/`)
- **Dimensionless Variables:** Normalized by parent order size $Q$ and arrival mid-price $M_0$ to guarantee numerical conditioning ($q/Q, y/Q, x/Q, P/M_0$).
- **Solver Waterfall:** Solves LPs/MIPs with HiGHS and CLARABEL, backed by OSQP fallback with explicit timeouts.
- **Unified Strategy Interface:**
  ```python
  model.solve(order: Order, book: Mapping[str, np.ndarray], params: Mapping[str, Any]) -> Schedule
  ```
- **Invariants:** $\sum_{t=1}^T \text{Schedule.shares}[t] == Q$ and $\text{Schedule.shares}[t] \ge 0$.

---

## 4. Execution Simulation Layer (`src/sim/simulate.py`)
- **Catch-Up Execution:** Slices execute $\min(y_t, \text{cum\_plan}[t] - \text{cum\_fill})$, rolling unfilled shares forward under temporary depth deficits.
- **Transient Footprint:** Tracks book depletion and resilience recovery:
  $$F_t = (1 - \phi)(F_{t-1} + \text{fill}_t)$$
- **Terminal Sweep:** Evaluated at snapshot $T-1$ net of final fill footprint without resilience recovery; excess unfilled shares pay penalty premium $\pi$.
- **Cost Decomposition:** Decomposes implementation shortfall into:
  $$\text{IS}_{\text{bps}} = \text{half\_spread} + \text{book\_walk} + \text{timing} + \text{sweep\_exec} + \text{sweep\_timing}$$

---

## 5. Decision & Visualization Layer (`app.py`, `src/reports/`)
- **Streamlit Platform:** 5 interactive research tabs exposing data inspection, microstructure analytics, parameter sweeps, benchmark frontiers, and AHP decision support.
- **Publication Figures:** 300 DPI high-resolution figures saved to `results/figures/` for academic publication.
