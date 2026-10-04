# DECISIONS — Design Rationale

| Field | Value |
|---|---|
| **Purpose** | Two registers. **Considered and rejected** — alternatives a reader might reasonably propose, with the reason each was not taken; and **load-bearing choices** — decisions that survive scrutiny and should not be disturbed |
| **Standing** | Not a source of truth for the design. Where this file and `PROPOSAL.md` disagree, `PROPOSAL.md` wins |
| **Relationship to `CHANGELOG.md`** | `CHANGELOG.md` records *changes to the document over time*. This file records *why the design is as it is*, which does not change |

Section references are to `PROPOSAL.md`.

Each rejected alternative below is a real option, not a strawman. Where an alternative would have been defensible under different assumptions, the row says so.

---

## 1. Considered and rejected

| Alternative | Why not taken | Authority |
|---|---|---|
| Recovering the price scale from the z-score or min–max variants | Both subtract an unknown location ($\bar x$ or $x_{\min}$), so the price *level* — hence $M_0$ and every bps metric — is not recoverable from the file. Under any scope the study reports the same ratios either way, so nothing is gained (section 4.1) | section 4.1 |
| Asserting that depth fluctuates by an order of magnitude within a session | Unsupported by the dataset paper, and the magnitude is not needed by any part of the design. Quantified during the Phase-1 audit if it matters | section 2.6 |
| Justifying MPC by dynamic inconsistency (Almgren–Chriss) | That literature concerns *price-adaptive* strategies. MPC here conditions on LOB state; the justification is progressive revelation of book state. Price-adaptive policies are out of scope | section 2.6 |
| Pricing the terminal sweep at $M_T$ or the final snapshot's worst ask | Look-ahead — the plan cannot use a price observed after its own horizon. T8 is the test that catches it | section 5.4 |
| Requiring paired bootstrap **and** Wilcoxon **and** Holm | Together they are a six-phase project, and three tests of the same null invite selective reading. One Holm family over H1/H2/H3(a)/H3(b) is mandatory; the rest is exploratory | section 8.3 |
| Deciding per-feature normalization scope in advance | Not settled by the paper's text. Audit check A1 decides it from the data, before anything downstream depends on it | section 4.1 |
| Feasibility rule "`T ≥ θ/ρ`" | Ignores the footprint. The rule that holds is $f(\varphi)=\rho\varphi/(\varphi+\rho(1-\varphi))\cdot D$ | section 8.1 |
| Accumulating price risk from $s=1$, with $\bar\alpha_t=\sum_{s\le t}$ | The $s=1$ shock never occurs — period 1 is the arrival snapshot — so including it adds a constant, and the drift sum then overcounts one period | section 5.3 |
| Solving the program in raw share units, pooled across stocks | Units are mixed across stocks at different price levels. Solved in dimensionless per-stock implementation units | section 5.2 |
| Defining "matched risk" by a fixed numeric tolerance | Not derivable from anything. Replaced by a paired-CI acceptance rule with an explicit dominance case | section 1.3 |
| Day-block bootstrap as the primary resampling scheme | Two test days cannot support day-blocking. Moving-block bootstrap over windows; day clusters are a sensitivity only | section 8.3 |
| "Market impact" as a metric name, $\mathrm{MI}=(P_{\text{exec}}-P_0)/P_0$ | Contains timing, so a strategy that traded badly on a rising tape scores well. Replaced by the IS decomposition; the term survives **only** as the calibrated coefficient $\eta_t$ | section 8.2 |
| VWAP as a baseline rung | FI-2010 rows carry no timestamps or volume profile, so no realised volume curve can be built. The report must say so rather than approximate one | section 6 |
| "Market-adjusted IS" | No market return exists in the data. Removed from the metric set | section 8.2 |
| Claiming rigorous convexity rules out price manipulation | Wrong mechanism. Buy-only trading plus temporary-only impact excludes it directly, which is the argument the design actually rests on | section 5.4 |
| Treating the session as 07:00–15:25 EET | The dataset's timestamps are shifted three hours. The kept window is 10:30–18:00 Helsinki local | section 4.1 |
| Assuming five large caps such as ASML, BP, BMO, RY, SAN over a January 2010 session | The dataset is Nasdaq Nordic (Helsinki): Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä, 1–14 **June** 2010 | section 4.1 [S]; section 7.3 S8 |

---

## 2. Load-bearing choices — do not disturb

Elements that carry the argument. Recorded because well-meant revisions tend to disturb exactly these.

| Element | Why it stays |
|---|---|
| Explicitly falsifiable hypotheses; a null result is a legitimate outcome (section 1.2) | Keeps the narrative outcome-agnostic |
| Exact walk-the-book $C_t(x)$ (section 5.1) | Mechanism, not a curve fitted to the mechanism; convex and piecewise linear |
| Risk term on inventory $y_t$, not on imbalance | Derivable in closed form; the correct object |
| Static / MPC / oracle information structure (section 5.5) | The oracle is a diagnostic ceiling, never a competitor |
| Baseline ladder, one idea per rung (section 6) | Every rung has an interpretable marginal contribution |
| Resilience footprint with a $\varphi$ sweep (section 7.2) | Addresses a real bias in naive replay |
| Shadow prices on the liquidity cap (section 5.4) | The OR reading of *why* a schedule bends: which periods are liquidity-bound |
| Causality test T8 (section 9) | Stops a mathematically impressive but broken system from shipping |
| Chronological splits with purge gaps; regime thresholds from calibration only (section 4.3) | Leakage control |
| Frozen-configuration pre-registration (`configs/experiment.yaml`, `config-frozen`) and the run-once test rule (section 8.5) | Makes the result defensible; no separate pre-registration document |
| The $\lambda \to 0$ limit gives TWAP$(T)$ | Cheap sanity check on the closed form, and the only one of the two the text relies on: it is asserted as T1. The companion limit $\lambda \to \infty$ giving immediate execution is **not** claimed anywhere; nothing depends on it |
