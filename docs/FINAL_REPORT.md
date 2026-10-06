# ROTE: Risk-Aware Optimal Trade Execution on FI-2010
## Final Research Report & Technical Evaluation

**Course Context:** Combined Financial Engineering (FE) & Operations Research (OR)  
**Dataset:** FI-2010 High-Frequency Limit Order Book Benchmark (DecPre, CC BY 4.0)  
**Repository:** `Nidszxh/ROTE`  
**Evaluation Split:** Validation Days 6–7 ($N_{\mathrm{eff}} = 176$ Independent Non-Overlapping Windows)  

---

## 1. Executive Summary

Large institutional orders face a fundamental dilemma in financial market microstructure:
1. **Trading rapidly** depletes available order book liquidity, walking deeper into the book and incurring severe temporary market impact.
2. **Trading slowly** minimizes instantaneous book-walk impact but exposes unexecuted inventory to adverse price drift and volatility risk.

The **ROTE** (Risk-Aware Optimal Trade Execution) project develops, implements, and benchmarks a complete quantitative execution suite on the high-frequency NASDAQ Nordic **FI-2010** limit order book dataset. ROTE formulates trade execution across multiple mathematical optimization paradigms—from classical continuous mean-variance liquidation ($M_1$) to discrete multi-level queue-aware linear/quadratic programming ($M_2$), fixed-charge mixed-integer programming ($M_3$), multi-criteria decision analysis ($M_4$), and static arrival-state quadratic programming (ROTE-Static).

### Key Empirical Findings
- **Statistical Superiority of Queue-Aware Programming:** Over $176$ non-overlapping test windows at confirmatory order size $\Theta = 1.0$, the multi-level LOB linear program ($M_2$) achieves an average implementation shortfall of **$12.34$ bps** (95% CI: [$7.17$, $17.42$]), significantly outperforming TWAP ($14.20$ bps), Almgren-Chriss ($14.20$ bps), Depth-Proportional ($15.19$ bps), and Immediate Market Sweeps ($25.08$ bps).
- **Hypothesis Testing:** Holm-Bonferroni step-down paired comparisons confirm that $M_2$ achieves statistically significant cost reductions relative to TWAP ($p = 0.0005$, Holm-adjusted $p = 0.014$, rejecting the null hypothesis of equal execution performance).
- **Convex Impact Scaling:** Execution cost scales convexly with order size $\Theta \in [0.25, 5.0]$. For small parent orders ($\Theta \le 0.5$), orders execute within visible 10-level liquidity with minimal impact (6.70–11.50 bps). Once parent order sizes exceed the visible order book ($\Theta \ge 1.0$), non-linear market impact accelerates rapidly, reaching $36.16$–$37.93$ bps at $\Theta = 5.0$.

---

## 2. Dataset Architecture & Audit Provenance

### 2.1 The FI-2010 Benchmark
The FI-2010 dataset provides normalized high-frequency limit order book events for 5 liquid Finnish equities traded on NASDAQ OMX Helsinki over 10 trading days:
1. **Kesko Oyj (KESBV)**
2. **Outokumpu Oyj (OUT1V)**
3. **Sampo Oyj (SAMPO)**
4. **Rautaruukki Oyj (RTRKS)**
5. **Wärtsilä Oyj (WRT1V)**

Each event records 10 levels of bid/ask prices and volumes (40 microstructure features). Across the entire pipeline, all five feature labels are strictly excluded to preserve unsupervised, realistic execution conditions.

### 2.2 Cryptographic & Protocol Audit (A0–A8)
The automated data audit verifies nine protocol invariants:
- **[A0] Provenance & Checksums:** All raw data files (`Train_Dst_NoAuction_DecPre_CF_7.txt` and `Test_Dst_..._CF_7/8/9.txt`) verify against SHA-256 hashes registered in `data/manifest.json`.
- **[A1] Decimal Precision Scale Recovery:** The DecPre format is confirmed with global scaling exponent $k = 6$:
  $$\text{Price}_{\text{EUR}} = \text{stored} \times 10^2, \quad \text{Volume}_{\text{shares}} = \text{stored} \times 10^6$$
- **[A2] Boundary Identification:** Event-time price discontinuities correctly delineate the 5 stock blocks across days 1–7.
- **[A3] Event-Time Representation:** $10$ events per row; one execution period $t$ comprises $m = 20$ rows ($200$ events); parent execution horizon $T = 20$ periods ($4,000$ book events).
- **[A4] Book Monotonicity & Integrity:** Strict positive bid-ask spread ($P^a_1 > P^b_1$), ascending asks, descending bids, positive depth, and finite mid-prices verified across all files.
- **[A5] Tick Discretization & Volatility Floor:** Prices lie on the 0.01 EUR tick grid. Volatility floor $\sigma_{\min}$ is set to the 10th percentile of period log-return magnitudes (ranging from 1.4 to 3.9 bps across stocks).
- **[A6] Frozen Split Sample Sizes:** Calibration (Days 1–5): $451$ windows; Validation (Days 6–7): $178$ windows; Test (Days 8–9): $261$ windows; Reserve (Day 10). Effective sample sizes exceed the required threshold ($N_{\mathrm{eff}} \ge 100$).
- **[A7] Fallback Independence:** No synthetic inversion or LOBSTER fallbacks required; upstream raw DecPre data passes all checks.
- **[A8] Order Size Realism:** Protocol sizing $Q = \theta \bar{D}$ where $\bar{D}$ is median gross ask depth. Orders with $\theta \le 0.5$ clear within visible depth; orders with $\theta \ge 1.0$ bind depth capacity.

---

## 3. Microstructure Calibration & Impact Modeling

Parameters are calibrated strictly on the frozen **Calibration Split** (Days 1–5) to prevent in-sample look-ahead bias.

### 3.1 Empirical Market Impact Parameter ($\eta_0$)
The empirical temporary market impact coefficient $\eta_0$ is estimated by walking the cumulative depth profile of each stock and regressing marginal cost against normalized trade size:
$$\Delta P_t(x) = \frac{1}{2} S_t + \eta_t x_t, \quad \eta_t = \frac{\eta_0}{D_t^a}$$

The calibrated values persisted in `results/tables/calibration.json` are:

| Stock Name | Ticker | Calibrated $\eta_0$ | Mean Spread (bps) | Volatility $\sigma_{\min}$ (bps) |
| :--- | :--- | :---: | :---: | :---: |
| Kesko | KESBV | $0.143467$ | $14.2$ | $1.82$ |
| Outokumpu | OUT1V | $0.058827$ | $18.6$ | $3.89$ |
| Sampo | SAMPO | $0.061597$ | $10.8$ | $1.41$ |
| Rautaruukki | RTRKS | $0.102412$ | $19.4$ | $2.65$ |
| Wärtsilä | WRT1V | $0.093776$ | $15.5$ | $2.10$ |

---

## 4. Mathematical Optimization Formulations

### 4.1 M1: Almgren–Chriss Mean-Variance Liquidation (Convex QP)
Minimizes total expected execution cost plus risk penalty on remaining inventory:
$$\min_{x} \sum_{t=1}^T \left[ \frac{1}{2} S_t n_t + \frac{\eta_0}{\bar{D}} n_t^2 \right] + \lambda \sum_{t=1}^T \sigma_t^2 x_t^2$$
Subject to:
$$x_0 = Q, \quad x_T = 0, \quad n_t = x_{t-1} - x_t \ge 0$$
- Implemented in **closed form** via hyperbolic functions with stable asymptotic scaling:
  $$\kappa = \operatorname{arcosh}\left(1 + \frac{\lambda \sigma^2 \bar{D}}{2 \eta_0}\right), \quad x_j = \frac{\sinh(\kappa (T - j))}{\sinh(\kappa T)} Q$$
- Cross-validated against numerical quadratic programming using CVXPY to within $3 \times 10^{-3}$ shares.

### 4.2 M2: Multi-Level LOB Linear/Quadratic Program
Optimizes order allocation directly across the 10 discrete visible depth levels $l \in \{1, \dots, 10\}$:
$$\min_{\tilde{q}, \tilde{y}, u} \sum_{t=1}^T \sum_{l=1}^{10} \frac{P^a_{t,l} - M_t}{M_0} \tilde{q}_{t,l} + \lambda \sum_{t=1}^T \frac{\sigma_t^2}{M_0^2} \tilde{y}_t^2 + \psi u$$
Subject to:
$$\tilde{y}_0 = 1.0$$
$$\tilde{y}_t = \tilde{y}_{t-1} - \sum_{l=1}^{10} \tilde{q}_{t,l}, \quad \forall t \in \{1, \dots, T\}$$
$$\tilde{q}_{t,l} \le \frac{V^a_{t,l}}{Q}, \quad \forall t, l$$
$$\sum_{l=1}^{10} \tilde{q}_{t,l} \le \frac{\rho D^a_t}{Q}, \quad \forall t$$
$$\tilde{y}_T = u, \quad u \ge 0, \quad \tilde{q} \ge 0, \quad \tilde{y} \ge 0$$
- Dimensionless formulation ensures numerical conditioning and eliminates solver timeouts.
- Shadow prices (dual multipliers on the participation constraint) identify periods of acute liquidity scarcity.

### 4.3 M3: Fixed-Charge Mixed-Integer Program (MIP)
Models transaction cost structures with discrete ticket fees $c_f$ and minimum fill sizes $L_{\min}$:
$$\min_{\tilde{q}, \tilde{y}, z, u} \text{Objective}(M_2) + \frac{c_f}{M_0 Q} \sum_{t=1}^T z_t$$
Subject to:
$$\frac{L_{\min}}{Q} z_t \le \sum_{l=1}^{10} \tilde{q}_{t,l} \le \frac{\rho D^a_t}{Q} z_t, \quad z_t \in \{0, 1\}$$
$$\sum_{t=1}^T z_t \le K$$

### 4.4 ROTE-Static: Arrival-State QP
Ablation model freezing the order book at arrival snapshot $t=0$, assuming static liquidity replenishment across all $T$ periods.

### 4.5 M4: Analytic Hierarchy Process (AHP)
Multi-criteria decision support framework evaluating candidate schedules across Cost, Risk, Completion Rate, and Simplicity. Dynamic normalization derives utilities from actual simulation outputs:
$$CR = \frac{\lambda_{\max} - 4}{3 \times 0.90} < 0.10 \implies \text{Saaty Consistent}$$

---

## 5. Empirical Benchmark Results & Statistical Validation

Evaluated across $n = 176$ non-overlapping stride-$400$ windows on Validation Days 6–7.

### 5.1 Strategy Performance Across Order Sizes ($\Theta$)

| Strategy | $\Theta$ | Implementation Shortfall (bps) | 95% Bootstrap CI | Timing Risk ($\sigma_{\mathrm{IS}}$) | Active Trades |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M2 (LOB LP)** | 0.25 | **6.70** | [1.52, 11.48] | 2.70 | 20.0 |
| TWAP (Full) | 0.25 | 9.99 | [5.24, 14.88] | 3.78 | 20.0 |
| AC | 0.25 | 9.99 | [5.28, 14.60] | 3.78 | 20.0 |
| ROTE-Static | 0.25 | 9.99 | [5.43, 14.67] | 3.78 | 20.0 |
| Depth-Prop | 0.25 | 11.09 | [6.27, 15.85] | 3.80 | 20.0 |
| TWAP' (Half) | 0.25 | 12.14 | [7.89, 16.63] | 4.08 | 10.0 |
| Immediate | 0.25 | 17.01 | [15.69, 18.46] | 1.42 | 1.0 |
| **M2 (LOB LP)** | 0.50 | **8.64** | [3.53, 13.66] | 3.67 | 20.0 |
| TWAP (Full) | 0.50 | 11.50 | [6.59, 16.38] | 4.31 | 20.0 |
| Immediate | 0.50 | 21.05 | [18.92, 23.30] | 4.20 | 1.0 |
| **M2 (LOB LP)** | **1.00** | **12.34** | [7.17, 17.42] | **4.42** | 20.0 |
| TWAP (Full) | 1.00 | 14.20 | [9.74, 18.83] | 4.96 | 20.0 |
| AC | 1.00 | 14.20 | [9.54, 19.13] | 4.96 | 20.0 |
| ROTE-Static | 1.00 | 14.20 | [9.64, 18.84] | 4.96 | 20.0 |
| Depth-Prop | 1.00 | 15.19 | [10.29, 20.16] | 4.97 | 20.0 |
| TWAP' (Half) | 1.00 | 19.06 | [14.63, 23.48] | 5.51 | 10.0 |
| Immediate | 1.00 | 25.08 | [21.18, 29.00] | 5.99 | 1.0 |
| **M2 (LOB LP)** | 2.00 | **17.88** | [12.98, 23.14] | 4.90 | 20.0 |
| TWAP (Full) | 2.00 | 18.64 | [13.87, 23.52] | 5.63 | 20.0 |
| Immediate | 2.00 | 27.23 | [22.10, 32.12] | 7.02 | 1.0 |
| **M2 (LOB LP)** | 5.00 | **36.16** | [30.67, 42.07] | 11.90 | 20.0 |
| TWAP (Full) | 5.00 | 36.42 | [30.37, 41.98] | 12.18 | 20.0 |
| Immediate | 5.00 | 36.75 | [30.84, 42.57] | 11.93 | 1.0 |

### 5.2 Statistical Significance (Holm-Bonferroni Paired Comparisons)
Pairwise differences are tested using block bootstrap hypothesis tests with Holm step-down correction for family-wise error rate ($\alpha = 0.05$):

| Pairwise Comparison | Mean Difference ($\Delta \text{IS}$) | Raw $p$-value | Holm Adjusted $p$ | Null Hypothesis ($H_0$) |
| :--- | :---: | :---: | :---: | :---: |
| **M2 vs. TWAP** | **-1.8078 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **M2 vs. Immediate** | **-9.0821 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **M2 vs. Depth-Prop** | **-2.6224 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **M2 vs. TWAP'** | **-5.2476 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **TWAP vs. Immediate** | **-7.2744 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **TWAP vs. TWAP'** | **-3.4398 bps** | $0.0005$ | **$0.0140$** | **Rejected (Significant Outperformance)** |
| **AC vs. TWAP** | $-0.0000\text{ bps}$ | $0.3295$ | $0.9885$ | Retained (Equivalent at $\lambda=0$) |

---

## 6. Realized Cost Decomposition

The unified simulator decomposes total implementation shortfall into its microstructural constituents:
$$\text{IS}_{\text{bps}} = \text{Half-Spread} + \text{Book-Walk Impact} + \text{Timing Risk} + \text{Sweep Execution} + \text{Sweep Timing}$$

```text
At theta = 1.0 (Confirmatory Parent Order Size):
========================================================================================
Strategy       | Half-Spread | Book Walk   | Timing Risk | Sweep Impact | Total Shortfall
----------------------------------------------------------------------------------------
M2 (LOB LP)    |  7.10 bps   |  1.82 bps   |  3.42 bps   |  0.00 bps    |   12.34 bps
TWAP           |  7.10 bps   |  3.68 bps   |  3.42 bps   |  0.00 bps    |   14.20 bps
Depth-Prop     |  7.10 bps   |  4.67 bps   |  3.42 bps   |  0.00 bps    |   15.19 bps
TWAP' (Half)   |  7.10 bps   |  8.54 bps   |  3.42 bps   |  0.00 bps    |   19.06 bps
Immediate      |  7.10 bps   | 14.56 bps   |  3.42 bps   |  0.00 bps    |   25.08 bps
========================================================================================
```
**Key Analytical Takeaway:** The entire outperformance of $M_2$ over TWAP ($1.86$ bps) stems from minimizing **Book-Walk Impact** ($1.82$ bps vs $3.68$ bps). Because $M_2$ explicitly observes visible depth levels, it routes child orders to periods with deeper queues, eliminating unnecessary penetrations into deeper price tiers.

---

## 7. Publication-Grade Research Figures

The figures generated in `results/figures/` synthesize these empirical results at 300 DPI for journal dissemination:

1. **`fig_paper_empirical_results.png`**:
   - **(a) Empirical Risk-Cost Frontier:** 2D bootstrap error ellipses demonstrating $M_2$'s Pareto dominance.
   - **(b) Impact Non-Linear Scaling:** Implementation shortfall as a function of $\Theta \in [0.25, 5.0]$.
   - **(c) Ranked Execution Cost:** Horizontal forest ranking with exact 95% bootstrap intervals.
   - **(d) Treatment Effect Forest Plot:** Holm-Bonferroni paired differences relative to TWAP.
2. **`fig1_lob_snapshot.png`**: Multi-level price ladder snapshot and cumulative depth profiles.
3. **`fig2_stock_boundaries_price_series.png`**: Event-time continuity and boundary detection across the five Nordic stocks.
4. **`fig3_depth_distribution_order_realism.png`**: Visible depth distributions vs parent order size thresholds.
5. **`fig4_spread_and_imbalance.png`**: Empirical density of bid-ask spreads (bps) and order book imbalances (OBI).
6. **`fig5_volatility_and_sigma_floor.png`**: Period return volatility, tick discretization spikes, and $\sigma_{\min}$ floor.
7. **`fig6_book_walk_cost_convexity.png`**: Empirical cost convexity resulting from multi-level book walks.

---

## 8. Limitations & Methodological Constraints

1. **Conditional Replay Assumption:** Backtesting uses recorded event-time order books. Endogenous market reaction (adversaries reacting to simulated fills) is not modeled.
2. **Event-Time Clock:** FI-2010 records discrete order book events, not millisecond physical timestamps. Execution periods are therefore scaled by event counts ($m = 20$ rows = $200$ events) rather than calendar seconds.
3. **Queue Position Dynamics:** Order fills assume immediate visible liquidity access up to participation cap $\rho$; internal queue priority within a price level is unobserved.
4. **VWAP Proxy:** Because continuous market trade volumes are not provided in the normalized feature release, VWAP is evaluated via an imbalance-weighted proxy.

---

## 9. Conclusion

The ROTE project demonstrates that mathematical optimization yields statistically robust, economically meaningful execution cost reductions on high-frequency limit order book data. By moving from naive time-slicing (TWAP) or closed-form equilibrium approximations (Almgren-Chriss) to multi-level queue-aware mathematical programming ($M_2$), institutional trading desks can systematically exploit transient book liquidity, reducing implementation shortfall by over **$1.8$ basis points** without increasing timing risk exposure.
