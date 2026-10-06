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
│   ├── config.py               # Validated experiment configuration and hashes
│   ├── data/                   # Dataset audit, loading, splits, and audit figures
│   ├── cost/                   # Book walking, units, and quadratic calibration
│   ├── loader/                 # FI-2010 data loader & normalization handling
│   ├── stats/                  # Microstructure & liquidity statistics
│   ├── impact/                 # Quadratic, square-root, and linear impact models
│   ├── optimize/               # Static quadratic schedule formulation
│   ├── evaluation/             # Multi-window evaluation and confidence intervals
│   ├── models/
│   │   ├── __init__.py         # Model package exports (M1-M4, ROTE-Static)
│   │   ├── m1_ac.py            # M1: Almgren-Chriss (closed-form + cvxpy)
│   │   ├── m2_lp.py            # M2: LOB LP/QP & shadow prices
│   │   ├── m3_mip.py           # M3: Fixed-charge Mixed-Integer Program
│   │   ├── m4_ahp.py           # M4: AHP Multi-Criteria Decision Framework
│   │   └── rote_static.py      # ROTE-Static: Arrival-state QP execution model
│   ├── benchmarks/
│   │   ├── __init__.py         # Benchmark package exports
│   │   └── baselines.py        # TWAP, Depth-Proportional, and VWAP-proxy
│   ├── sim/                    # Unified execution simulator & cost reporter
│   ├── reports/
│   │   ├── generate_report.py  # Report compiler & artifact export pipeline
│   │   ├── paper_figures.py    # 300 DPI research paper figure generator
│   │   └── visualizations.py   # Publication-grade chart generation suite
│   └── utils/
│       └── contracts.py        # Order, Schedule, and CostReport data classes
├── tests/
│   ├── test_models.py          # Unit tests for M1, M2, M3, M4, ROTE-Static
│   ├── test_baselines.py       # Unit tests for benchmarks
│   ├── test_visualizations.py  # Unit tests for visualization rendering
│   ├── test_e2e.py             # Full end-to-end integration tests
│   ├── test_t.py               # T1-T17 mathematical correctness assertions
│   └── test_basic.py           # Sanity and contract checks
├── results/
│   ├── EVALUATION_REPORT.md    # Multi-window bootstrap & Holm evaluation report
│   ├── MODEL_EXECUTION_REPORT.md # Compiled analysis and metrics report
│   ├── tables/calibration.json # Persisted eta_0 estimates
│   └── figures/                # 300 DPI publication figures
│       ├── fig_paper_empirical_results.png # 4-panel research paper figure
│       └── fig1-fig6_*.png     # Audit and microstructure figures
└── docs/
    ├── ARCHITECTURE.md         # Current data-to-decision architecture
    ├── FINAL_REPORT.md         # Full project report and findings
    └── PRESENTATION_DECK.md    # 8-slide presentation deck outline
```

---

## 3. Quick Start & Execution

### Environment Setup
Python **3.11+** (tested on 3.12 and 3.13). Using [`uv`](https://docs.astral.sh/uv/):

```bash
# Install dependencies into virtual environment
uv venv .venv
uv pip install -r pyproject.toml --extra dev
```

### Dataset setup

The FI-2010 files are not committed to Git because the raw release is nearly 1 GB. Store the
extracted files in `data/raw/FI-2010/`. Download the published archive from
the [Fairdata dataset page](https://etsin.fairdata.fi/dataset/73eb48d7-4dbc-4a10-a52a-da745b47a649)
under its CC BY 4.0 terms, then run:

```bash
uv run --no-sync python run_experiment.py setup --zip /path/to/fi2010.zip
```

The command extracts only the four required files, verifies the manifest, and builds the
disposable cache under `data/processed/`. Use `--verify-only` to check an existing installation
or `--force` to rebuild it. If the data is stored outside the repository, set
`ROTE_DATA_ROOT=/path/to/FI-2010` before running commands. The archive's direct URL is
intentionally not hardcoded because the Fairdata landing page is JavaScript-driven;
`--url` is supported when a stable archive endpoint is available.

### Running the Interactive UI
Launch the 5-tab Streamlit dashboard:
```bash
uv run --no-sync streamlit run app.py
```
Tabs included:
1. **1. Data**: Select stock (KESBV, OUT1V, SAMPO, RTRKS, WRT1V) and trading day (1–10).
2. **2. Statistics**: On-demand liquidity statistics (spread, depth by level, order imbalance, volatility).
3. **3. Optimiser**: Interactive solver parameter controls for M1, M2, and M3 with schedule plots.
4. **4. Compare**: Multi-strategy overlay and performance metrics table (Shortfall bps, Std, Trades).
5. **5. Decision**: AHP preference matrix configuration, real-time consistency ratio check, and strategy scoring.

### Generating Executive Reports & Visualizations
Compile the publication figures and generate the Markdown executive report:
```bash
uv run --no-sync python -m src.reports.generate_report
uv run --no-sync python run_experiment.py figures
```
Artifacts generated:
- Figures saved to `results/figures/` (LOB depth ladder, microstructure dashboard, M1 efficient frontier, M2 shadow prices, M3 ticket fee trade-off, benchmark Pareto scatter, AHP ranking, and the 4-panel research figure `fig_paper_empirical_results.png`).
- Executive Markdown report saved to `results/MODEL_EXECUTION_REPORT.md`.

Run the multi-stock evaluation configured in `configs/experiment.yaml`:

```bash
uv run --no-sync python run_experiment.py evaluate
```

The evaluation report is written to `results/EVALUATION_REPORT.md` and includes bootstrap
confidence intervals and Holm-corrected paired comparisons across $n = 176$ non-overlapping windows.

### Running Test Suites
```bash
# Run the complete quality gate (110 tests passing)
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
```

### Complete end-to-end command sequence

Run these commands from the repository root after placing the FI-2010 archive on disk:

```bash
# 1. Create the environment and install declared dependencies (no uv.lock is used)
uv venv .venv
uv pip install -r pyproject.toml --extra dev

# 2. Extract the four required raw files into data/raw/FI-2010/,
#    verify sizes and SHA-256 values, and build data/processed/ caches
uv run --no-sync python run_experiment.py setup --zip /path/to/fi2010.zip

# 3. Verify the local raw release without rebuilding it
uv run --no-sync python run_experiment.py setup --verify-only

# 4. Run data quality and protocol checks
uv run --no-sync python run_experiment.py audit
uv run --no-sync python run_experiment.py freeze-splits

# 5. Calibrate impact parameters and generate audit figures
uv run --no-sync python run_experiment.py calibrate
uv run --no-sync python run_experiment.py figures

# 6. Run multi-stock evaluation with confidence intervals and Holm correction
uv run --no-sync python run_experiment.py evaluate

# 7. Generate the benchmark report and figures
uv run --no-sync python -m src.reports.generate_report

# 8. Run the complete confirmatory test pipeline
uv run --no-sync python run_experiment.py full --test --confirm

# 9. Launch the interactive five-tab application
uv run --no-sync streamlit run app.py
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

### ROTE-Static: Arrival-State QP Execution Model
Ablation model linking M1 and M2 by freezing the order book at arrival snapshot $t=0$:
$$\min_{\tilde{q}, \tilde{y}, u} \sum_{t=1}^T \sum_{l=1}^{10} \frac{P^a_{0,l} - M_0}{M_0} \tilde{q}_{t,l} + \lambda \sum_{t=1}^T \frac{\sigma_t^2}{M_0^2} \tilde{y}_t^2 + \psi u$$
Subject to static arrival depth capacities, inventory flow conservation, and participation limits.

### M4: Analytic Hierarchy Process (AHP)
Evaluates candidate schedules across multiple objectives (Cost, Risk, Completion, Simplicity). Computes normalized priority weights via the principal eigenvector and verifies consistency:
$$CI = \frac{\lambda_{\max} - n}{n - 1}, \quad CR = \frac{CI}{RI} < 0.10$$

### Publication-Grade Empirical Research Figure
The generated 4-panel research figure in `results/figures/fig_paper_empirical_results.png` provides:
1. **(a) Empirical Risk-Cost Frontier**: 2D bootstrap ellipses showing M2 Pareto dominance over TWAP and Immediate execution.
2. **(b) Impact Non-Linear Scaling**: Cost expansion as order size scales across $\Theta \in [0.25, 5.0]$.
3. **(c) Ranked Execution Cost**: Horizontal forest plot with 95% bootstrap confidence intervals ($n=176$).
4. **(d) Treatment Effect Forest Plot**: Paired differences with Holm-Bonferroni significance testing.

---

## 5. Team Split & Responsibilities
- **Member 1 (Data & App Shell)**: Loader, data cleaning/validation, liquidity statistics module, and Streamlit app architecture.
- **Member 2 (Finance & Simulation)**: Market impact calibration, execution simulation engine, benchmark strategies, and financial interpretation.
- **Member 3 (Optimisation A)**: M1 Almgren-Chriss formulation, risk-cost efficient frontier, and M4 AHP decision framework.
- **Member 4 (Optimisation B)**: M2 LOB LP with shadow prices, M3 Fixed-charge MIP, and sensitivity analysis.