# ROTE — Risk-Aware Optimal Trade Execution
**On the FI-2010 Limit Order Book**

ROTE is a quantitative trade execution suite and interactive decision tool built on the high-frequency FI-2010 Limit Order Book (LOB) dataset. It provides an end-to-end pipeline: data loading and integrity auditing, microstructure liquidity analytics, market impact calibration, and four mathematical optimization models (M1–M4) evaluated against benchmark execution strategies.

---

## 1. Overview & Architecture

ROTE bridges **Financial Engineering (FE)** and **Operations Research (OR)**:

- **Financial Engineering**: Models the fundamental mean-variance trade-off between market impact (cost of trading fast) and price volatility risk (cost of trading slowly). Evaluates implementation shortfall (IS) in basis points across risk-aversion frontiers.
- **Operations Research**: Formulates execution problems across mathematical programming classes:
  - **M1 (NLP / Convex QP)**: Classical Almgren–Chriss (2000) optimal liquidation schedule (closed-form + CVXPY).
  - **M2 (LP / QP)**: Limit order book depth allocation with participation caps and shadow prices.
  - **M3 (MIP)**: Fixed-charge child order scheduling with minimum lot sizes and cardinality limits.
  - **M4 (MCDA / AHP)**: Analytic Hierarchy Process for multi-criteria strategy selection with Saaty consistency ratio checks.

### Unified Interface Contract
Every optimization model adheres to the unified architectural contract:
```python
load_day(stock: str, day: int) -> tuple[dict, int, bool]     # Clean, validated LOB data
Order(side: str, size: float, horizon: int, params: dict)    # Immutable order contract
model.solve(order: Order, book: dict, params: dict) -> Schedule # Execution schedule
simulate(schedule: Schedule, book: dict, params: dict) -> CostReport # Standardized evaluation
```

---

## 2. Directory Structure

```text
ROTE/
├── ROADMAP.md                  # Master roadmap and milestone schedule
├── app.py                      # 5-Tab Streamlit interactive research platform
├── pyproject.toml              # Tool configs, pytest markers, and dependencies
├── src/
│   ├── loader/                 # FI-2010 data loader & normalization handling
│   ├── stats/                  # Microstructure & liquidity statistics
│   ├── impact/                 # Quadratic, square-root, and linear impact models
│   ├── models/
│   │   ├── __init__.py         # Model package exports (M1-M4)
│   │   ├── m1_ac.py            # M1: Almgren-Chriss (closed-form + cvxpy)
│   │   ├── m2_lp.py            # M2: LOB LP/QP & shadow prices
│   │   ├── m3_mip.py           # M3: Fixed-charge Mixed-Integer Program
│   │   └── m4_ahp.py           # M4: AHP Multi-Criteria Decision Framework
│   ├── benchmarks/
│   │   ├── __init__.py         # Benchmark package exports
│   │   └── baselines.py        # TWAP, Depth-Proportional, and VWAP-proxy
│   ├── sim/                    # Unified execution simulator & cost reporter
│   ├── reports/
│   │   ├── visualizations.py   # Publication-grade chart generation suite
│   │   └── generate_report.py  # Report compiler & artifact export pipeline
│   └── utils/
│       └── contracts.py        # Order, Schedule, and CostReport data classes
├── tests/
│   ├── test_models.py          # Unit tests for M1, M2, M3, M4
│   ├── test_baselines.py       # Unit tests for benchmarks
│   ├── test_visualizations.py  # Unit tests for visualization rendering
│   ├── test_e2e.py             # Full end-to-end integration tests
│   └── test_basic.py           # Sanity and contract checks
├── results/
│   ├── MODEL_EXECUTION_REPORT.md  # Compiled analysis and metrics report
│   └── figures/*.png              # High-resolution publication figures
└── docs/
    ├── feedback_log.md         # Review-1 feedback tracker
    ├── decision_log.md         # Architecture decision records
    ├── REUSE_ANALYSIS.md       # Component classification and reuse audit
    ├── FINAL_REPORT.md         # Full project report and findings
    └── PRESENTATION_DECK.md    # 8-slide presentation deck outline
```

---

## 3. Quick Start & Execution

### Environment Setup
Python **3.11+** (tested on 3.12). Using [`uv`](https://docs.astral.sh/uv/):

```bash
# Set dataset path (if using local FI-2010 files)
export ROTE_DATA_ROOT="$HOME/data/FI-2010"

# Install dependencies into virtual environment
uv venv .venv
uv pip install -r pyproject.toml --extra dev
```

### Running the Interactive UI
Launch the 5-tab Streamlit dashboard:
```bash
uv run --no-sync streamlit run app.py
```
Tabs included:
1. **1. Data**: Select stock (KESK1, OUT1V, SAMPO, RVI1V, WRT1V) and trading day (1–10).
2. **2. Statistics**: On-demand liquidity statistics (spread, depth by level, order imbalance, volatility).
3. **3. Optimiser**: Interactive solver parameter controls for M1, M2, and M3 with schedule plots.
4. **4. Compare**: Multi-strategy overlay and performance metrics table (Shortfall bps, Std, Trades).
5. **5. Decision**: AHP preference matrix configuration, real-time consistency ratio check, and strategy scoring.

### Generating Executive Reports & Visualizations
Compile all 7 publication-grade figures and generate the Markdown executive report:
```bash
uv run --no-sync python -m src.reports.generate_report
```
Artifacts generated:
- Figures saved to `results/figures/` (LOB depth ladder, microstructure dashboard, M1 efficient frontier, M2 shadow prices, M3 ticket fee trade-off, benchmark Pareto scatter, AHP ranking).
- Executive Markdown report saved to `results/MODEL_EXECUTION_REPORT.md`.

### Running Test Suites
```bash
# Run all model, baseline, visualization, and integration tests
uv run --no-sync pytest tests/test_e2e.py tests/test_models.py tests/test_baselines.py tests/test_visualizations.py tests/test_basic.py

# Run linter and formatting checks
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
```

---

## 4. Key Models & Formulations

### M1: Almgren–Chriss Optimal Liquidation
Minimizes total expected execution cost plus risk penalty:
$$\min_{x} \sum_{k=1}^T \left[ \frac{\eta}{\tau} n_k^2 \right] + \lambda \sigma^2 \tau \sum_{k=1}^T x_k^2$$
Subject to $x_0 = X$, $x_T = 0$, $n_k = x_{k-1} - x_k \ge 0$.
- Implemented both in **closed form** using hyperbolic functions (with numerically stable exponential scaling) and verified via **CVXPY** quadratic programming.

### M2: Limit Order Book LP with Shadow Prices
Allocates executions across order book depth levels:
$$\min_{q} \sum_{t=1}^T \sum_{l=1}^L (P^a_{t,l} - M_t) q_{t,l}$$
Subject to level volume capacities $q_{t,l} \le V^a_{t,l}$, order completion $\sum_{t,l} q_{t,l} = Q$, and participation limits $\sum_l q_{t,l} \le \rho D^a_t$.
- Shadow prices on depth constraints reveal marginal liquidity costs across time slices.

### M3: Fixed-Charge Mixed-Integer Program
Optimizes trade timing under discrete fixed order fees $c_f$ and lot constraints:
$$\min_{q, z} \sum_{t=1}^T \sum_{l=1}^L (P^a_{t,l} - M_t) q_{t,l} + c_f \sum_{t=1}^T z_t$$
Subject to:
$$L_{\min} z_t \le \sum_{l=1}^L q_{t,l} \le Q z_t, \quad z_t \in \{0, 1\}, \quad \sum_{t=1}^T z_t \le K$$

### M4: Analytic Hierarchy Process (AHP)
Evaluates candidate schedules across multiple objectives (Cost, Risk, Completion, Simplicity). Computes normalized priority weights via the principal eigenvector and verifies consistency:
$$CI = \frac{\lambda_{\max} - n}{n - 1}, \quad CR = \frac{CI}{RI} < 0.10$$

---

## 5. Team Split & Responsibilities
- **Member 1 (Data & App Shell)**: Loader, data cleaning/validation, liquidity statistics module, and Streamlit app architecture.
- **Member 2 (Finance & Simulation)**: Market impact calibration, execution simulation engine, benchmark strategies, and financial interpretation.
- **Member 3 (Optimisation A)**: M1 Almgren-Chriss formulation, risk-cost efficient frontier, and M4 AHP decision framework.
- **Member 4 (Optimisation B)**: M2 LOB LP with shadow prices, M3 Fixed-charge MIP, and sensitivity analysis.