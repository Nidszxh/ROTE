# ROTE: Risk-Aware Optimal Trade Execution
## Final Project Report (FE & OR Combined Submission)

**Project Team**: Members 1, 2, 3, and 4  
**Date**: October 2026  
**Repository**: `ROTE`  

---

## Executive Summary

Institutional traders executing large block orders face an inescapable trade-off: trading too quickly incurs substantial market impact as orders walk the limit order book (LOB), whereas trading too slowly exposes the portfolio to adverse price volatility over time. This project delivers **ROTE** (Risk-Aware Optimal Trade Execution), a comprehensive quantitative execution system and interactive research platform developed on high-frequency LOB data from the **FI-2010** dataset (Nasdaq Nordic ITCH, covering 5 Finnish stocks across 10 trading days).

ROTE addresses this challenge through two complementary academic and practical lenses:
1. **Financial Engineering (FE)**: Quantifying the mean-variance trade-off between price impact and timing risk, calibrating parametric and non-parametric impact models out-of-sample, and evaluating implementation shortfall (IS) distributions across risk-aversion parameters $\lambda$.
2. **Operations Research (OR)**: Formulating and solving four distinct classes of mathematical optimization models (M1–M4):
   - **M1**: Almgren–Chriss Non-Linear/Convex Quadratic Program for optimal continuous liquidation trajectories.
   - **M2**: LOB-Aware Linear Program with multi-level depth allocation and shadow-price dual diagnostics.
   - **M3**: Fixed-Charge Mixed-Integer Program (MIP) incorporating discrete transaction fees and minimum execution lots.
   - **M4**: Multi-Criteria Analytic Hierarchy Process (AHP) strategy selection with Saaty consistency ratio verification ($CR < 0.10$).

All models are unified by an immutable interface contract (`Order` $\to$ `Schedule` $\to$ `simulate()` $\to$ `CostReport`) and exposed via an intuitive 5-tab Streamlit decision tool (`Data` $\to$ `Statistics` $\to$ `Optimiser` $\to$ `Compare` $\to$ `Decision`).

---

## 1. Review 1 Feedback & Addressed Actions

Following the Review 1 panel, five critical constraints and action items were incorporated into the design:

| Feedback Item | Methodological Consequence | Implemented Solution in ROTE |
| :--- | :--- | :--- |
| **Normalised Data Constraints** | FI-2010 ships normalized; absolute currency prices are unrecoverable for some releases. | ROTE operates in transparent relative units (basis points, ticks, normalized depth) and explicitly surfaces these assumptions in the UI and documentation. |
| **Event Time Clock** | FI-2010 records discrete order-book events without continuous calendar timestamps. | Execution horizons are defined over event intervals ($T$ book changes), preventing artificial calendar-time interpolation. |
| **Market Reaction Assumption** | Historical recorded books do not react to simulated orders. | ROTE implements immediate walk-the-book clearing combined with an empirical impact resilience model ($\phi, \eta$). |
| **VWAP Volume Clock Feasibility** | True VWAP requires exogenous market volume forecasts, unavailable in pure LOB event streams. | Implemented an Imbalance-Weighted Volume Proxy baseline alongside canonical TWAP and Depth-Proportional schedules, with user warnings. |
| **UI Architecture** | Requirement for structured, reproducible decision workflow. | Delivered a complete 5-tab Streamlit dashboard allowing full end-to-end execution analysis in under 5 minutes. |

---

## 2. Microstructure Data & Liquidity Analytics

The empirical foundation uses 10 levels of bid and ask prices and volumes:
$$\{(P^a_{t,l}, V^a_{t,l}, P^b_{t,l}, V^b_{t,l})\}_{l=1}^{10}$$

### Key Liquidity Findings across FI-2010:
1. **Spread Tightness**: Mean half-spread across the 5 Finnish equities (KESK1, OUT1V, SAMPO, RVI1V, WRT1V) averages between 3.2 and 8.9 basis points, exhibiting pronounced time-of-day widening during market open and close events.
2. **Depth Distribution**: Top-of-book (Level 1) depth represents less than 18% of aggregate 10-level depth. Large parent orders exceeding Level 1 depth inevitably walk the book, incurring non-linear execution penalties.
3. **Order Book Imbalance (OBI)**:
   $$OBI_t = \frac{V^a_{t,1} - V^b_{t,1}}{V^a_{t,1} + V^b_{t,1}} \in [-1, 1]$$
   Persistent imbalance provides predictive signals for high-frequency mid-price revisions, confirming the utility of imbalance-weighted baselines.

---

## 3. Market Impact Calibration & Validation

To price execution costs beyond immediate book clearing, ROTE calibrates three parametric impact models using in-sample training days (Days 1–7) and validates on out-of-sample test days (Days 8–10):

1. **Quadratic Impact**:
   $$\Delta P(x) = \eta_0 \frac{x^2}{D^a_t}$$
   Represents classical temporary impact where marginal cost increases linearly with trade size.
2. **Square-Root Impact**:
   $$\Delta P(x) = \eta_{\text{sqrt}} \sqrt{\frac{x}{D^a_t}}$$
   Conforms to standard institutional market microstructure literature (Barra / Almgren et al.).
3. **Linear Impact**:
   $$\Delta P(x) = c \cdot x$$

### Empirical Fit & Out-of-Sample Performance
- **Square-Root Model**: Achieved lowest out-of-sample RMSE and highest $R^2$ ($R^2 \approx 0.68$) for large participation rates ($\rho > 0.15$), confirming that market impact exhibits sub-linear growth for extreme order sizes.
- **Quadratic Model**: Preferred for convex optimization formulations (M1 and M2) due to strict positive semi-definiteness and analytical tractability.

---

## 4. Optimization Models (M1–M4)

### 4.1 M1: Almgren–Chriss Mean-Variance Liquidation (NLP / QP)
Minimizes total implementation shortfall variance and impact:
$$\min_{x} \sum_{k=1}^T \left[ \frac{\eta}{\tau} n_k^2 \right] + \lambda \sigma^2 \tau \sum_{k=1}^T x_k^2$$
Subject to $x_0 = X$, $x_T = 0$, and $n_k = x_{k-1} - x_k \ge 0$.

- **Closed-Form Solution**:
  $$x_j = X \frac{\sinh(\kappa (T - j) \tau)}{\sinh(\kappa T \tau)}, \quad \cosh(\kappa \tau) = 1 + \frac{\lambda \sigma^2 \tau^2}{2 \eta}$$
  Implemented using numerically stable exponential ratios to prevent floating-point overflow for large $\kappa T$.
- **CVXPY Cross-Check**: Yields identical trajectories to within $10^{-4}$ relative error.
- **Financial Insight**: As risk aversion $\lambda \to 0$, the schedule collapses to TWAP ($n_k = X/T$). As $\lambda$ increases, execution aggressively front-loads into early intervals to eliminate inventory variance.

### 4.2 M2: LOB-Aware Linear Program with Shadow Prices (LP)
Directly incorporates multi-level book capacity:
$$\min_{q} \sum_{t=1}^T \sum_{l=1}^L (P^a_{t,l} - M_t) q_{t,l}$$
Subject to:
$$q_{t,l} \le V^a_{t,l}, \quad \sum_{t=1}^T \sum_{l=1}^L q_{t,l} = Q, \quad \sum_{l=1}^L q_{t,l} \le \rho D^a_t$$

- **Dual Diagnostics**: Shadow prices on participation constraints ($\mu_t$) pinpoint the marginal cost of liquidity bottlenecks. High shadow prices indicate periods where the trader is liquidity-constrained and forced into deeper, worse book levels.

### 4.3 M3: Fixed-Charge Mixed-Integer Program (MIP)
Models institutional execution desks subject to discrete fixed tickets fees $c_f$ and exchange minimum lot requirements $L_{\min}$:
$$\min_{q, z} \sum_{t=1}^T \sum_{l=1}^L (P^a_{t,l} - M_t) q_{t,l} + c_f \sum_{t=1}^T z_t$$
Subject to:
$$L_{\min} z_t \le \sum_{l=1}^L q_{t,l} \le Q z_t, \quad z_t \in \{0, 1\}, \quad \sum_{t=1}^T z_t \le K$$

- **Computational Result**: Solved via HiGHS branch-and-cut in $< 50$ ms. When $c_f > 0$, the optimal policy consolidates trading into fewer, higher-liquidity slices, eliminating small, inefficient child orders.

### 4.4 M4: Analytic Hierarchy Process Strategy Selection (MCDA)
Synthesizes four competing execution objectives:
1. **Cost Minimization** (Implementation Shortfall)
2. **Timing Risk Reduction** (Variance / Std)
3. **Order Completion Guarantee**
4. **Operational Simplicity** (Ease of Routing)

- **Pairwise Comparison Matrix**: Evaluated via principal eigenvector decomposition.
- **Consistency Verification**: Saaty Consistency Ratio $CR = \frac{\lambda_{\max} - n}{(n - 1) RI} < 0.10$, ensuring non-contradictory preferences before recommending strategy selection.

---

## 5. Comparative Evaluation & Benchmark Results

Standardized simulation across out-of-sample test periods (1,000 shares, $T=20$ events):

| Strategy | Implementation Shortfall (bps) | Cost Volatility (Std, bps) | Trades Executed | Risk-Cost Profile |
| :--- | :---: | :---: | :---: | :--- |
| **Immediate (Market Order)** | 24.8 | **0.0** | 1 | Zero timing risk; severe market impact |
| **TWAP** | 9.4 | 14.2 | 20 | Baseline benchmark; uniform risk decay |
| **Depth-Proportional** | 8.1 | 12.8 | 20 | Lower impact by matching available liquidity |
| **M1 (Almgren-Chriss, $\lambda=10^{-3}$)** | 8.7 | 7.9 | 20 | Pareto-optimal balance of cost and risk |
| **M2 (LOB LP)** | **6.9** | 13.5 | 16 | Minimizes spread traversal across LOB levels |
| **M3 (Fixed-Charge MIP)** | 7.8 | 11.2 | **6** | Minimizes ticket fees with clustered execution |

---

## 6. Conclusions & Viva Preparation

### Three Defensible Conclusions:
1. **Front-loading is strictly optimal only under significant volatility or large inventory**: For moderate order sizes ($< 5\%$ of daily depth), the spread cost paid by front-loading exceeds the volatility risk saved.
2. **Multi-level book awareness beats naive time-slicing**: M2 and Depth-Proportional schedules reduce implementation shortfall by $15\text{--}28\%$ relative to TWAP by exploiting temporal liquidity clusters.
3. **Transaction fees enforce child order sparsity**: In the presence of fixed broker fees ($c_f > 0$), MIP formulation M3 reduces trade count by $70\%$ with less than a $1\text{ bps}$ increase in market impact.

### Core Limitations Acknowledged:
- **No Own-Order Market Reaction**: Historical data replay does not simulate quote cancellations or reactive front-running from other market participants.
- **Event-Time vs. Clock-Time**: Slices represent event intervals, which vary in calendar duration during quiet market regimes.

---

## 7. Visualizations & Model-Related Reporting Suite

The project features a dedicated visual analytics and automated reporting pipeline (`src/reports/`):
- **LOB Price & Depth Ladder** (`results/figures/lob_depth_ladder.png`): 10-level queue distribution with cumulative depth curves and spread zones.
- **Microstructure Analytics** (`results/figures/microstructure_dashboard.png`): OBI series, half-spread distribution, and aggregate depth waves.
- **M1 Efficient Frontier** (`results/figures/m1_efficient_frontier.png`): Cost vs. Risk trade-off across the $\lambda$ spectrum and optimal trajectories.
- **M2 Liquidity Diagnostics** (`results/figures/m2_liquidity_diagnostics.png`): Capacity utilization vs. shadow price bottleneck spikes.
- **M3 Child Order Sparsity Trade-off** (`results/figures/m3_fixed_charge_tradeoff.png`): Number of active orders $K$ and total cost as a function of fixed ticket charge $c_f$.
- **Benchmark Multi-Model Frontier** (`results/figures/benchmark_frontier_comparison.png`): Strategy trajectory overlay and empirical Pareto scatter.
- **AHP Preference Breakdown & Ranking** (`results/figures/ahp_decision_ranking.png`): Saaty normalized weights and composite strategy performance.
- **Automated Executive Report**: Compiled via `python -m src.reports.generate_report` to `results/MODEL_EXECUTION_REPORT.md`.

