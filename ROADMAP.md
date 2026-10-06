# ROTE: Roadmap (post-review-1)
**Risk-Aware Optimal Trade Execution on the FI-2010 Limit Order Book**
Status: Project complete. Full FE + OR pipeline validated on FI-2010. 110/110 pytest tests passing, 0 linter errors, end-to-end multi-window evaluation completed across $n = 176$ independent windows on Validation Days 6–7, 300 DPI research paper figures generated, and interactive 5-tab Streamlit UI running.

---

## 1. Goal and what "done" means

A trader must liquidate (or buy) a large parent order. Trading fast pays market impact because the order walks the book. Trading slowly leaves price risk. ROTE is a Streamlit tool on FI-2010 that loads and cleans LOB data, shows liquidity statistics on demand, runs several optimisation models that output execution schedules, benchmarks them, and helps the user choose a strategy for their risk preference.

**One build, two grading lenses**

| Lens | What the instructors look for | ROTE's answer |
|---|---|---|
| FE | Real data cleaned; descriptive stats; ≥2 analyses from a menu; interpretation; a genuine decision; financial theory as backbone | Mean-variance trade-off and efficient frontier of cost vs risk; risk aversion as utility; Decision tab |
| OR | Dataset loaded in UI; stats on demand; ≥2 optimisation models; formulations; sensitivity; results interpretation; viva on formulations | NLP/QP (M1), LP with shadow prices (M2), fixed-charge IP (M3), AHP/goal programming (M4) |
| Both | Review-1 feedback incorporated; every member presents and can answer on everything | Review-1 feedback incorporated into implementation; rotation of presenters and quiz sessions (Section 7) |

**Definition of done**
- [x] Clean loader and on-demand statistics for any stock and day
- [x] Impact model calibrated and validated out of sample
- [x] M1 and M2 working, tested, interpreted (the minimum for both courses)
- [x] M3 and M4 working (full OR coverage)
- [x] Immediate and TWAP benchmarks compared on cost and risk
- [x] Streamlit app: Data → Statistics → Optimiser → Compare → Decision
- [x] Review-1 feedback addressed and integrated into models
- [x] Final deck, report, README, demo backup recording

---

## 2. Data realities to settle in the first days

Verify on first load; they shape everything downstream.

| Issue | Consequence | Plan |
|---|---|---|
| FI-2010 ships **normalised** (Z-score, min-max, decimal-precision) | Real prices and sizes may not be recoverable | Identify your version now. Decimal-precision is reversible; Z-score needs the per-file mean and std. If not recoverable, work in **relative units** (ticks, bps, normalised depth) and say so on a slide |
| Rows are **events, not timestamps** | No calendar-time schedules | Event time is the clock: "trade X over N book events" |
| **5 stocks, 10 days** | Overfitting; noisy calibration | Calibrate days 1 to 7, test days 8 to 10; report per stock |
| 10 levels per side (40 raw LOB features) plus labels | Enough to walk the book | Optimiser uses the 40 raw columns; labels used only in the stretch ML model |
| Recorded data **doesn't react to your orders** | Backtest can't show your own market impact | Walk the recorded book for immediate cost, add calibrated impact for the rest; state the assumption |

---

## 3. Models (the menu)

| ID | Model | Technique | Question answered |
|---|---|---|---|
| **M1** | Almgren-Chriss mean-variance schedule | Quadratic/nonlinear programming; risk aversion λ | How does the schedule change with λ? What does the cost-risk frontier look like? |
| **M2** | LOB-aware slice allocation | LP with depth and participation limits; shadow prices | In thin or uneven books, how should the order be split to minimise walk-the-book cost? Which depth constraints bind? |
| **M3** | Fixed-charge child-order scheduling | Integer programming (binaries, minimum lot, order cap) | How many child orders, and what minimum lot, once each order has a fixed cost? |
| **M4** | Strategy selection | AHP with consistency ratio (goal programming as alternative) | Which strategy suits which trader profile? |

**Formulation sketches (for slides and viva)**

- **M1:** choose holdings x_0 = X, …, x_N = 0, trades n_k = x_{k−1} − x_k. Minimise Σ_k [γ n_k x_k + ε n_k + (η/τ) n_k²] + λ σ² τ Σ_k x_k². γ is permanent impact, ε and η temporary impact, σ volatility, τ step length. λ = 0 gives TWAP-like trading; large λ front-loads. Closed form (sinh) cross-checked with cvxpy.
- **M2:** variables q_{t,l} ≥ 0 (shares in slice t at level l). Minimise Σ (mid_t − p_{t,l}) q_{t,l} for a sell, subject to Σ q = X, q_{t,l} ≤ depth_{t,l}, Σ_l q_{t,l} ≤ φ·volume_t. Add the M1 variance term to make it a convex QP, which links M1 and M2.
- **M3:** binaries z_t with q_t ≤ M z_t, q_t ≥ L_min z_t, objective plus c_f Σ z_t, optional Σ z_t ≤ K.
- **M4:** criteria cost, risk, completion, simplicity; pairwise comparisons per trader profile; weights; CR < 0.1.

**Shared pieces:** implementation shortfall in bps as the cost metric (mean, std); impact model fitted from the book (linear vs square-root); benchmarks immediate, TWAP.

---

## 4. Team split (4 members)

Name owners in the repo README. Everyone reviews at least one other person's pull requests.

| # | Workstream | Owns | Also owns |
|---|---|---|---|
| 1 | **Data and app shell** | `loader.py`, cleaning, validation, `stats.py`, Data and Statistics tabs, Streamlit integration | Final integration and deployment |
| 2 | **Finance and simulation** | `impact.py` (calibration), `simulate.py`, benchmarks, Compare tab | Financial interpretation of results; Decision-tab wording |
| 3 | **Optimisation A** | M1 (closed form + cvxpy), frontier over λ, M4 (AHP/goal programming) | Optimiser tab for M1; Decision tab logic |
| 4 | **Optimisation B** | M2 (LP, shadow prices), M3 (MIP), sensitivity analysis | Optimiser tab for M2 and M3 |

**Interface contract (agree this on Day 1 so all four can work in parallel):**

```python
load_day(stock: str, day: int) -> LOBFrame            # clean, validated, event-indexed
Order(side, size, horizon, params)                    # dataclass
model.solve(order, book, params) -> Schedule          # shares per event slice
simulate(schedule, book, impact) -> CostReport        # shortfall_bps, std, trades
```

Every model returns a `Schedule`; every schedule goes through the same `simulate()`. This is what makes the Compare tab easy.

**Repo conventions:** branch per feature, pull request with one reviewer, unit tests required for models (sum of trades equals X, no negative trades, closed form matches solver), a `requirements.txt` pinned.

---

## 5. Timeline

Default: 8 weeks. **If your final presentation is sooner, use the compression rules in Section 9.**

### Week 1: Foundations (Completed)
- Day 1: agree the interface contract; set up branches, CI-lite (pytest), folder structure.
- #1: loader plus version/normalisation check, first validation (bid < ask, monotone levels).
- #2: draft the walk-the-book cost function on a sample day.
- #3 and #4: write M1 and M2 on a toy order book so they are ready to plug in.
- **Exit (Completed):** `load_day()` works for all 5 stocks and 10 days; shared contract covered by unit tests.

### Week 2: Statistics and impact model (Completed)
- #1: stats module (spread, depth by level, imbalance, mid-price returns, volatility) plus the Statistics tab.
- #2: impact calibration on days 1 to 5, validation on 6 to 7; linear vs quadratic fit with intervals (`results/tables/calibration.json`).
- #3: M1 on real data; schedule plot and CVXPY verification.
- #4: M2 on real data; shadow-price table and diagnostics.
- **Exit (Completed):** statistics on demand in the UI; calibrated impact parameters per stock.

### Weeks 3 to 4: Models and benchmarks (Completed)
- #3: λ sweep, efficient frontier; M4 (AHP) with the consistency check ($CR < 0.10$).
- #4: M3 (fixed charge, minimum lot, order cap), cost-vs-number-of-orders curve; M2 sensitivity.
- #2: backtest engine with immediate, TWAP, TWAP', and depth-proportional benchmarks.
- #1: Optimiser and Compare tabs wired to real model outputs.
- **Exit (Completed):** every model returns a `Schedule`; benchmark table reproducible; T1–T17 unit tests pass.

### Week 5: Integrate and harden the UI (Completed)
- Full flow Data → Statistics → Optimiser → Compare → Decision.
- Caching, input validation, sensible defaults, error messages.
- **Exit (Completed):** interactive 5-tab application running seamlessly on Streamlit port 8501.

### Week 6: Analysis and interpretation (Completed)
- Robustness: stocks, order sizes ($\Theta \in [0.25, 5.0]$), horizons, held-out days.
- Microstructural cost decomposition: half-spread, book walk, timing risk, sweep impact.
- **Exit (Completed):** three defensible conclusions with numbers; multi-window evaluation report ($n = 176$).

### Week 7: Deck, report, rehearsal (Completed)
- Final deck (`docs/PRESENTATION_DECK.md`) and report (`docs/FINAL_REPORT.md`) drafted.
- Publication-grade 300 DPI research figure generated (`results/figures/fig_paper_empirical_results.png`).
- Quiz round preparation and viva alignment complete.
- **Exit (Completed):** report and 8-slide defense deck complete; UI verified.

### Week 8: Buffer and final polish (Completed)
- Complete quality gate: 110/110 pytest tests pass, 0 ruff errors.
- Code frozen, documentation synchronized across all packages.
- **Exit (Completed):** clean reproduction of every table and figure; 100% test pass rate.

---

## 6. Final presentation outline

1. Problem, and **what changed since review 1** (feedback addressed)
2. Data and cleaning, including the stated assumptions (relative units, event time)
3. Liquidity statistics, as findings rather than charts
4. Impact model calibration and out-of-sample validation
5. Models M1 to M4: formulation, result, interpretation (M1 frontier, M2 shadow prices, M3 order-count trade-off, M4 weights and consistency)
6. Benchmark comparison table (cost, std)
7. Live UI demo, ending on the Decision tab
8. Conclusions, limitations (no reaction to own orders, 5 stocks / 10 days), future work

**Speaker allocation:** one section per member, but rotate who answers questions so everyone fields questions outside their own part.

---

## 7. Viva readiness

Each member must be able to:
- write M1 to M4 from memory and explain every symbol;
- explain every FI-2010 column used and the normalisation caveat;
- interpret a shadow price, an AHP consistency ratio, and the efficient frontier;
- say what the model **cannot** claim (no own-order market reaction, small sample, event time).

Schedule two mutual quiz rounds (Weeks 5 and 7) where each member is quizzed on someone else's model.

---

## 9. Risks and compression rules

| Risk | Mitigation |
|---|---|
| Real prices unrecoverable from normalised data | Relative units; state it openly |
| Impact calibration unstable (tiny sample) | Pool across stocks; show confidence intervals; compare fits |
| Integration chaos | Interface contract from Day 1; one `Schedule` format; weekly integration check |
| One person holds the maths | Pairing on formulations; quiz rounds |
| Demo fails live | Recorded backup; pinned environment; test on the presentation machine |

**If the final presentation is under about 6 weeks away,** cut in this order:
1. Reduce M3 to a single-stock demonstration.
2. Replace AHP with a simple weighted scoring layer *only if* the instructors accept it; keep AHP if the OR viva is going to probe it.
3. Never drop: M1, M2, the benchmarks, the stats-on-demand UI, and the Decision tab. These are what both courses grade.

---

## 10. Tech stack

pandas, numpy, pyarrow (data) · cvxpy, scipy.optimize (QP/LP) · PuLP or OR-Tools (MIP) · scikit-learn, LightGBM or PyTorch (stretch) · Plotly (frontier, schedule, book heatmap) · Streamlit (UI) · pytest · GitHub

---

## 11. References

- Ntakaris, Magris, Kanniainen, Gabbouj, Iosifidis (2018). *Benchmark dataset for mid-price forecasting of limit order book data with machine learning methods.* Journal of Forecasting.
- Almgren and Chriss (2000). *Optimal execution of portfolio transactions.* Journal of Risk.
- Bertsimas and Lo (1998). *Optimal control of execution costs.* Journal of Financial Markets.
- Obizhaeva and Wang (2013). *Optimal trading strategy and supply/demand dynamics.* Journal of Financial Markets.
- Cont, Kukanov, Stoikov (2014). *The price impact of order book events.* Journal of Financial Econometrics.