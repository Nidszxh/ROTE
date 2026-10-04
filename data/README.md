# FI-2010 Dataset Audit Report (A0–A8)

Authoritative audit report generated in accordance with PROPOSAL.md section 4.1.

## Summary of Audit Checks

| Check | Name | Status | Finding |
|---|---|---|---|
| **A0** | Provenance | `PASS` | Found 4 files (1 train, 3 test), all DecPre NoAuction format with 149 features/labels per event. |
| **A1** | Scale Recovery | `PASS` | DecPre variant confirmed. Global exponent k=6. Scale recovery: price_euros = stored * 100, vol_shares = stored * 10^6. |
| **A2** | Stock/Day Boundaries | `PASS` | Detected 4 discontinuities separating 5 blocks. Identified Nordic equities: Kesko (KESBV), Outokumpu (OUT1V), Sampo (SAMPO), Rautaruukki (RTRKS), Wärtsilä (WRT1V). Blocks are stock-major over days 1-7. |
| **A3** | Time Axis & Periodicity | `PASS` | Event-based representations: 10 events per row. One period = 20 rows = 200 events. Execution horizon T = 20 periods. |
| **A4** | Book Integrity | `PASS` | Book integrity verified: positive spread (P^a > P^b), price monotonicity, non-negative volumes, finite mid-prices, and tick-grid conformance. |
| **A5** | Tick Discretization & Volatility Floor | `PASS` | Tick discretization: prices on the 0.01 EUR grid (half-tick 0.0050 EUR); σ_min floor, the 10th percentile of non-zero 20-row block return magnitudes per stock, is 1.4–3.9 bps. |
| **A6** | Effective Sample Size (N_eff) | `PASS` | Effective non-overlapping sample sizes (B0=100, stride=400): Calibration=451 windows, Validation=178 windows, Test=261 windows (pooled N_eff=261 >= required 100; sufficient). |
| **A7** | Fallback Dataset | `N/A` | Fallback (LOBSTER) not required: A1 scale recovery and A4 book integrity hold on every file read (train days 1-7, test days 8-9). Day 10 is the reserve split and was not read. |
| **A8** | Order-Size Realism | `PASS` | Order size realism: Q = θ·D̄ with θ ∈ {0.25, 0.5, 1, 2}. For θ ∈ {0.25, 0.5}, orders execute within visible 10-level liquidity. For θ ∈ {1, 2}, parent orders meet or exceed the entire visible book and are penalty-dominated by construction. |

## A0: Dataset Files & Provenance

| Filename | Trading Days | Size (bytes) | SHA-256 Checksum |
|---|---|---|---|
| `Test_Dst_NoAuction_DecPre_CF_7.txt` | Day 8 | 132,259,850 | `1acd92e13df8f499...` |
| `Test_Dst_NoAuction_DecPre_CF_8.txt` | Day 9 | 124,378,346 | `950559383a3cf823...` |
| `Test_Dst_NoAuction_DecPre_CF_9.txt` | Day 10 | 76,138,106 | `c09785b0aed0825a...` |
| `Train_Dst_NoAuction_DecPre_CF_7.txt` | Days 1–7 | 607,324,298 | `11af4bbcf26f08a4...` |

## A2 & A8: Stock Characteristics and Order-Size Realism

| Stock | Ticker | Median Mid | Spread (bps) | Depth Dā (sh) | Depth (€) | σ_min |
|---|---|---|---|---|---|---|
| Kesko | `KESBV` | €26.92 | 22.3 bps | 46,110 | €1,241,512 | 1.87 bps |
| Outokumpu | `OUT1V` | €12.80 | 15.6 bps | 293,375 | €3,755,200 | 3.87 bps |
| Sampo | `SAMPO` | €17.35 | 11.5 bps | 304,460 | €5,282,381 | 2.88 bps |
| Rautaruukki | `RTRKS` | €12.70 | 15.8 bps | 255,300 | €3,241,034 | 3.89 bps |
| Wärtsilä | `WRT1V` | €34.83 | 14.4 bps | 58,350 | €2,032,039 | 1.43 bps |

### Parent Order Sizes (Q = θ·Dā)

| Stock | θ = 0.25 | θ = 0.5 | θ = 1 | θ = 2 |
|---|---|---|---|---|
| Kesko | 11,528 (€310k) | 23,055 (€621k) | 46,110 (€1,242k) | 92,220 (€2,483k) |
| Outokumpu | 73,344 (€939k) | 146,688 (€1,878k) | 293,375 (€3,755k) | 586,750 (€7,510k) |
| Sampo | 76,115 (€1,321k) | 152,230 (€2,641k) | 304,460 (€5,282k) | 608,920 (€10,565k) |
| Rautaruukki | 63,825 (€810k) | 127,650 (€1,621k) | 255,300 (€3,241k) | 510,600 (€6,482k) |
| Wärtsilä | 14,588 (€508k) | 29,175 (€1,016k) | 58,350 (€2,032k) | 116,700 (€4,064k) |

## A6: Effective Windows (N_eff)

Non-overlapping windows with B0=100 rows and stride T*m=400 rows (4,000 events):

- **Calibration (Days 1–5):** 451
- **Validation (Days 6–7):** 178
- **Test (Days 8–9):** 261
- **Total Non-Overlapping Windows:** 890

## Generated Figures

All figures generated and saved to `results/figures/` (300 DPI, event-time captions):

1. `fig1_lob_snapshot.png`: 10-level Limit Order Book ladder and volume profile.
2. `fig2_stock_boundaries_price_series.png`: Mid-price series and stock boundaries.
3. `fig3_depth_distribution_order_realism.png`: Depth distribution & order sizes.
4. `fig4_spread_and_imbalance.png`: Bid-ask spread and depth imbalance distributions.
5. `fig5_volatility_and_sigma_floor.png`: Return volatility and sigma_min floor.
6. `fig6_book_walk_cost_convexity.png`: Book-walk cost and quadratic approximation.
