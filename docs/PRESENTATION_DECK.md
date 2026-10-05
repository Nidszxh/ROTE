# ROTE Presentation Deck Outline
**Risk-Aware Optimal Trade Execution on the FI-2010 Limit Order Book**
*Combined Final Presentation: Financial Engineering & Operations Research*

---

## Slide 1: The Problem & What Changed Since Review 1
- **The Execution Dilemma**: Liquidating a parent order faces a fundamental trade-off:
  - Trade fast $\to$ severe market impact & walking the book.
  - Trade slowly $\to$ adverse price volatility & inventory risk.
- **Review 1 Feedback Incorporated**:
  - *Data Normalization*: Acknowledged relative units (bps, ticks, normalized volume) openly.
  - *Event Time Clock*: Execution indexed by LOB updates ($T$ event slices).
  - *No Exogenous Market Reaction*: Stated replay assumptions with calibrated impact ($\eta_0, \phi$).
  - *VWAP Adaptation*: Replaced infeasible continuous volume clock with an Imbalance-Weighted Volume Proxy.
  - *5-Tab Interactive Platform*: Fully operationalized Streamlit decision application.

---

## Slide 2: Data Realities, Cleaning & Structural Assumptions
- **Dataset**: FI-2010 benchmark (Nasdaq Nordic ITCH, 5 Finnish equities, 10 trading days).
- **Audit & Validation (G1 Exit)**:
  - Checked monotonicity: $P^a_{t,1} < P^a_{t,2} < \dots < P^a_{t,10}$ and $P^b_{t,1} > P^b_{t,2} > \dots > P^b_{t,10}$.
  - Verified no cross-book violations: $P^b_{t,1} < P^a_{t,1}$ for all $t$.
  - Split protocol: Days 1–7 for calibration/training; Days 8–10 held out for out-of-sample testing.
- **Microstructure Features**:
  - 10 levels of bid/ask prices and volumes ($40$ raw features).
  - Top-of-book depth represents $< 18\%$ of total 10-level liquidity.

---

## Slide 3: Liquidity Statistics as Actionable Findings
- **Spread Dynamics**:
  - Mean half-spread: $3.2$ to $8.9\text{ bps}$ across assets.
  - Intraday U-shape: Spreads widen significantly at market open and close.
- **Depth Asymmetry & Order Book Imbalance (OBI)**:
  $$OBI_t = \frac{V^a_{t,1} - V^b_{t,1}}{V^a_{t,1} + V^b_{t,1}}$$
  - Persistent order book imbalance is predictive of directional short-term mid-price drift.
- **Takeaway**: Liquidity is highly non-uniform in time; static flat slicing (TWAP) leaves significant money on the table.

---

## Slide 4: Market Impact Calibration & Out-of-Sample Validation
- **Three Competing Impact Models**:
  1. *Quadratic*: $\Delta P(x) = \eta_0 \frac{x^2}{D^a_t}$ (analytically tractable, convex).
  2. *Square-Root*: $\Delta P(x) = \eta_{\text{sqrt}} \sqrt{\frac{x}{D^a_t}}$ (institutional standard).
  3. *Linear*: $\Delta P(x) = c \cdot x$ (simple baseline).
- **Validation Results (Days 8–10)**:
  - Square-root impact achieves lowest RMSE ($0.42\text{ bps}$) for large order blocks.
  - Quadratic formulation retained for mathematical programming guarantees (global convexity).
  - Out-of-sample stability confirmed via 95% bootstrap confidence intervals.

---

## Slide 5: Optimization Models M1 to M4 (Formulations & Mechanics)
- **M1 (Almgren-Chriss QP/NLP)**:
  - Objective: $\min \sum_k \frac{\eta}{\tau} n_k^2 + \lambda \sigma^2 \tau \sum_k x_k^2$.
  - Dual implementation: Sinh closed form (numerically stable exponential ratio) + CVXPY solver.
  - Produces the continuous Risk–Cost Efficient Frontier over $\lambda$.
- **M2 (LOB LP with Shadow Prices)**:
  - Direct discrete clearing over book levels with participation cap $\rho$.
  - Dual values ($\mu_t$) reveal the shadow price of market liquidity bottlenecks.
- **M3 (Fixed-Charge Child-Order MIP)**:
  - Binary trade indicators $z_t \in \{0, 1\}$, fixed fee $c_f$, and minimum lot $L_{\min}$.
  - Solved via HiGHS branch-and-cut; proves optimal trade clustering.
- **M4 (AHP Multi-Criteria Strategy Selection)**:
  - Criteria: Cost, Risk, Completion, Simplicity.
  - Principal eigenvector weights verified by Saaty Consistency Ratio ($CR < 0.10$).

---

## Slide 6: Benchmark Comparison & Strategy Performance Matrix
*Sample Execution: 1,000 shares across 20 event intervals ($T=20$)*

| Strategy | Shortfall (bps) | Volatility / Risk (bps) | Trade Count | Best Suited For |
| :--- | :---: | :---: | :---: | :--- |
| **Immediate** | 24.8 | **0.0** | 1 | Extreme risk-aversion, illiquid volatility |
| **TWAP** | 9.4 | 14.2 | 20 | Uninformed execution, simple routing |
| **Depth-Proportional** | 8.1 | 12.8 | 20 | High-depth regimes |
| **M1 ($\lambda = 10^{-3}$)** | 8.7 | 7.9 | 20 | Risk-aware quantitative liquidation |
| **M2 (LOB LP)** | **6.9** | 13.5 | 16 | Minimizing walk-the-book spread cost |
| **M3 (Fixed-Charge MIP)** | 7.8 | 11.2 | **6** | Exchange ticket fees & minimum lots |

---

## Slide 7: Live UI Walkthrough (The 5-Tab Experience)
- **Tab 1: Data**: Seamless stock and day selection; visual validation of raw LOB queues.
- **Tab 2: Statistics**: On-demand spread distribution, cumulative depth profile, and OBI.
- **Tab 3: Optimiser**: Real-time parameter sliders ($\lambda, \rho, c_f, L_{\min}$) with instant trajectory plotting and shadow price reporting.
- **Tab 4: Compare**: Multi-strategy overlay and comprehensive metrics comparison.
- **Tab 5: Decision**: Interactive AHP pairwise preference matrix with live consistency check and recommended model selection.

---

## Slide 8: Financial Conclusions, Viva Readiness & Limitations
- **Key Financial Conclusions**:
  1. *Front-loading pays only when volatility risk outweighs spread concessions*.
  2. *LOB-aware execution cuts implementation shortfall by up to 28% over TWAP*.
  3. *Fixed fees enforce schedule sparsity with negligible impact degradation*.
- **Acknowledged Limitations**:
  - Replay without market reaction; event time clock; 5 Finnish equities sample size.
- **Viva Readiness**:
  - Every team member is prepared to write formulations from memory, interpret shadow prices, explain Saaty consistency ratios, and defend empirical limitations.
