# ROTE: Risk-Aware Optimal Trade Execution
## 8-Slide Executive & Viva Presentation Deck

---

### Slide 1: Motivation & The Execution Problem
- **The Core Trade-off:**
  - Fast execution walks deeper into the limit order book $\implies$ massive temporary market impact.
  - Slow execution minimizes book-walk impact $\implies$ unexecuted inventory suffers adverse price volatility drift.
- **The ROTE Mission:**
  - Build an end-to-end quantitative execution pipeline bridging **Financial Engineering** (mean-variance frontiers, utility theory, microstructure impact modeling) and **Operations Research** (convex quadratic programming, multi-level queue LP, fixed-charge MIP, analytic hierarchy process).
- **Target Dataset:** FI-2010 benchmark (5 Finnish stocks, NASDAQ OMX Helsinki, normalized DecPre).

---

### Slide 2: Data Realities & Cryptographic Protocol Safeguards
- **Microstructure Specifications:**
  - 10 levels of bid/ask prices and volumes ($40$ raw LOB features).
  - All $5$ forecast labels strictly forbidden to preserve unsupervised execution realism.
  - Event-time clock ($200$ events per period $t$; $T = 20$ periods per parent order).
- **Audit Standards (A0–A8):**
  - Cryptographic verification against SHA-256 manifest (`data/manifest.json`).
  - Scale recovery ($k=6$): $\text{Price} = \text{stored} \times 10^2$ EUR, $\text{Volume} = \text{stored} \times 10^6$ shares.
  - Strict frozen splits: Calibration (Days 1–5), Validation (Days 6–7), Test (Days 8–9, gated with `--confirm`), Reserve (Day 10).
  - Guaranteed effective sample size: $N_{\mathrm{eff}} = 176 \ge 100$ independent non-overlapping windows.

---

### Slide 3: Unified Architecture & Execution Contract
- **Immutable Pipeline Hierarchy:**
  ```text
  Raw FI-2010 -> Loader -> Calibration (eta_0) -> Order -> Solver -> Schedule -> Simulator -> CostReport -> Streamlit UI
  ```
- **Unified Simulator (`src/sim/simulate.py`):**
  - Walks empirical visible depth up to participation cap ($\rho = 0.25$).
  - Dynamic catch-up execution rule: $\min(y_t, \text{cum\_plan}[t] - \text{cum\_fill})$.
  - Transient price impact footprint recursion: $F_t = (1 - \phi)(F_{t-1} + \text{fill}_t)$ with resilience $\phi = 0.5$.
  - Exact realized cost decomposition identity:
    $$\text{IS}_{\text{bps}} = \text{Half-Spread} + \text{Book-Walk Impact} + \text{Timing Risk} + \text{Sweep Execution} + \text{Sweep Timing}$$

---

### Slide 4: Optimization Model Menu
1. **M1 (Almgren-Chriss Mean-Variance):**
   - Closed-form hyperbolic schedule verified against CVXPY convex QP.
   - Traces Pareto efficient frontier parameterized by urgency $\omega$ and risk aversion $\lambda$.
2. **M2 (Multi-Level Queue-Aware LP):**
   - Direct allocation across 10 visible depth levels ($q_{t,l} \le V^a_{t,l}$) with participation cap $\rho D^a_t$.
   - Dimensionless variables ($q/Q, y/Q, x/Q$) and terminal sweep penalty slack $u$.
   - Dual variables yield shadow prices identifying liquidity bottleneck periods.
3. **M3 (Fixed-Charge MIP):**
   - Integer binaries $z_t \in \{0, 1\}$ incorporating discrete ticket fees $c_f$, minimum lot sizes $L_{\min}$, and order caps $K$.
4. **ROTE-Static (QP):**
   - Static arrival-state ablation baseline modeling single-snapshot liquidity replenishment.
5. **M4 (Analytic Hierarchy Process):**
   - Dynamic multi-criteria scoring across Cost, Risk, Completion Rate, and Ticket Simplicity with Saaty consistency ratio $CR < 0.10$.

---

### Slide 5: Empirical Benchmark Findings
- **Validation Dataset Results ($n = 176$ Independent Windows, $\Theta = 1.0$):**
  - **M2 (LOB LP):** **$12.34$ bps** shortfall (95% CI: [$7.17$, $17.42$]) · Risk: **$4.42$**
  - **TWAP / AC / ROTE-Static:** **$14.20$ bps** shortfall (95% CI: [$9.74$, $18.83$]) · Risk: **$4.96$**
  - **Depth-Proportional:** **$15.19$ bps** shortfall (95% CI: [$10.29$, $20.16$]) · Risk: **$4.97$**
  - **TWAP' (Accelerated):** **$19.06$ bps** shortfall (95% CI: [$14.63$, $23.48$]) · Risk: **$5.51$**
  - **Immediate (Market Sweep):** **$25.08$ bps** shortfall (95% CI: [$21.18$, $29.00$]) · Risk: **$5.99$**
- **Statistical Significance:**
  - $M_2$ beats TWAP by **$1.81$ bps** ($p = 0.0005$, Holm-adjusted $p = 0.014$, Statistically Significant).
  - $M_2$ beats Immediate by **$9.08$ bps** ($p < 0.001$).
  - TWAP beats Accelerated TWAP' by **$3.44$ bps** ($p < 0.001$).

---

### Slide 6: Microstructural Cost Decomposition — Why M2 Wins
- **Decomposition at Confirmatory Order Size $\Theta = 1.0$:**
  - **Half-Spread Cost:** Constant across all strategies ($7.10$ bps) — market entry fee.
  - **Timing Price Risk:** Identical across full-horizon strategies ($3.42$ bps).
  - **Book-Walk Impact Cost:**
    - Immediate: **$14.56$ bps** (walks through multiple price tiers)
    - Accelerated TWAP': **$8.54$ bps** (higher rate per slice)
    - Depth-Proportional: **$4.67$ bps** (overshoots during temporary depth spikes)
    - TWAP: **$3.68$ bps** (even pacing)
    - **M2 (Queue-Aware LP):** **$1.82$ bps** (routes around thin books and exploits deep queues)
- **Key Insight:** Mathematical programming achieves outperformance not by taking excess timing risk, but by optimizing order book level consumption.

---

### Slide 7: Interactive Streamlit Platform (`app.py`)
- **5-Tab Integrated Quantitative Workflow:**
  1. **Data:** Stock selector (5 stocks), trading day (1–10), interactive 10-level LOB ladder, and cumulative depth charts.
  2. **Statistics:** Microstructure analytics, spread distributions (bps), depth-by-level profiles, and log-return volatility.
  3. **Optimiser:** Parameter sliders ($\Theta, \omega, \rho, c_f, L_{\min}$); interactive schedule plots and inventory burn-down curves.
  4. **Compare:** Multi-strategy benchmark overlay, liquidation trajectories, and risk-cost Pareto scatter.
  5. **Decision:** Interactive pairwise preference sliders, Saaty consistency indicator, and multi-attribute utility ranking.
- **Server:** Runs locally at `http://localhost:8501`.

---

### Slide 8: Limitations, Conclusions & Viva Defense
- **Methodological Limitations:**
  - Backtesting is a conditional historical replay; endogenous adversary market reactions are unobserved.
  - Event-time indexing reflects volume pacing rather than continuous calendar clock.
  - First-come-first-served queue priority within price levels is approximated by participation cap $\rho$.
- **Core Viva Takeaways:**
  - Dimensionless optimization eliminates ill-conditioning in numerical quadratic programming.
  - Strict out-of-sample data hygiene (calibrating $\eta_0$ on days 1–5, validating on 6–7) prevents look-ahead bias.
  - Multi-level LOB linear programming provides measurable, statistically valid alpha over classical closed-form benchmarks.
