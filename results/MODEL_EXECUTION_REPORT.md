# ROTE: Comprehensive Model Execution & Microstructure Report
**Asset**: Kesko (KESBV) | **Test Period**: Day 6 | **Size**: 5000 shares ($T=20$)

---

## 1. Microstructure Environment
- **Average Half-Spread**: 13.81 bps
- **Average Ask Depth**: 50006 shares
- **Average Bid Depth**: 53725 shares
- **Order Book Imbalance (Mean)**: 0.0373
- **Short-Term Volatility**: 19.87 bps/period

![LOB Depth Ladder](figures/lob_depth_ladder.png)
![Microstructure Dashboard](figures/microstructure_dashboard.png)

---

## 2. Multi-Model Benchmark Comparison Table

| Model | Implementation Shortfall (bps) | Timing Risk (Std Dev) | Active Trades |
| :--- | :---: | :---: | :---: |
| **M1** | 26.14 | 6.55 | 20 |
| **M2** | 59.15 | 0.00 | 1 |
| **M3** | 59.15 | 0.00 | 1 |
| **ROTE-Static** | 26.21 | 6.55 | 20 |
| **TWAP** | 26.25 | 6.55 | 20 |
| **Depth-Prop** | 31.58 | 6.55 | 20 |
| **VWAP Proxy** | 27.45 | 6.55 | 20 |

![Benchmark Frontier Comparison](figures/benchmark_frontier_comparison.png)

---

## 3. Mathematical Optimization Deep Dive

### M1: Almgren-Chriss Mean-Variance Efficient Frontier
![M1 Efficient Frontier](figures/m1_efficient_frontier.png)
- As risk aversion lambda increases, execution front-loads to curb volatility risk.

### M2: Limit Order Book LP with Shadow Prices
![M2 Liquidity Diagnostics](figures/m2_liquidity_diagnostics.png)
- Shadow prices identify binding depth constraints where liquidity bottlenecks occur.

### M3: Fixed-Charge Mixed-Integer Program
![M3 Tradeoff](figures/m3_fixed_charge_tradeoff.png)
- Fixed fees enforce child order sparsity, reducing ticket fee overhead.

---

## 4. Multi-Criteria Strategy Selection (AHP)
- **Consistency Ratio (CR)**: 0.0079 (Valid: $CR < 0.10$)
- **Weights**: Cost=54.0%, Risk=16.3%, Simplicity=29.7%
- **Recommended Strategy**: **M2**

![AHP Decision Ranking](figures/ahp_decision_ranking.png)