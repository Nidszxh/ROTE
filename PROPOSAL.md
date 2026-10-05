# ROTE — Risk-Aware Optimal Trade Execution Using High-Frequency Limit Order Book Data

*A cost–risk optimal-execution study on FI-2010: a convex-QP approximation of a constrained stochastic control problem, evaluated through historical LOB simulation*

| Field | Value |
|---|---|
| **Project name** | **ROTE** — **R**isk-Aware **O**ptimal **T**rade **E**xecution |
| **Description** | A quantitative trade-execution framework that balances market impact, execution cost and inventory risk, using high-frequency limit order book (LOB) data |
| **Type** | Financial Engineering × Operations Research |
| **Status** | **Final** — the authoritative specification. Its hypotheses, primary tests and acceptance rule are fixed (section 8.5) and are not revised on the basis of test results; section 10.4 governs any change |
| **Progress (2026-10-05)** | Course milestones **complete**: First Project Review completed; FE sign-off and OR prior permission **obtained** (section 2.3). Phase 1 **complete** (audit A0–A8 all PASS, `splits-frozen`); Phase 2–3 mostly complete (`calibrate` and `check-formulation` SUCCESS); Phase 4 UI running; tests green (72 tests). Detail in section 10.5 |
| **Guideline compliance** | FE + OR course guidelines: public dataset (FI-2010); Python tool; UI with dataset loading, statistics on demand and ≥2 user-selectable optimisation models (section 1.1); ≥2 distinct financial analyses from a menu (section 1.1); Tools & Technologies (section 2.5); First Review Alignment (section 2.4); course-topic approval obtained (section 2.3) |
| **Evidence tags** | **[S]** stated in the dataset paper (Ntakaris et al., 2018); **[C]** to be confirmed by the Phase-1 audit; **[K]** a design convention, not a fact |

> **This document is the single source of truth.** Code, report and slides are derived from it and are updated when it changes; if any of them disagrees with this specification, the other artifacts are corrected, not this file (section 10.4).

**Contents.** 1 Summary · 2 Problem Statement · 3 Notation · 4 Data: FI-2010 · 5 Model · 6 Baselines · 7 Execution Simulator · 8 Evaluation Protocol · 9 Correctness Standards · 10 Roadmap · 11 Risk Register · 12 Deliverables and Repository · 13 Stretch Extensions · 14 Definition of Done · 15 References

> **Project context:** This work satisfies FE and OR guidelines (group project) by implementing an interactive UI/menu (section 1.1) in addition to dataset analysis, statistics, and ≥2 optimization models.

---

## 1. Summary

A large order cannot be executed instantly without paying for liquidity, and it cannot be executed slowly without exposure to adverse price moves. This project treats that trade-off as a **constrained stochastic optimal-control problem, approximated by a convex quadratic program (QP)** whose cost parameters are calibrated from limit order book (LOB) data and **evaluated through historical LOB simulation**.

The umbrella question is:

> **How does market-microstructure information change the optimal execution policy under a cost–risk trade-off?**

It is answered in two tiers, and the claim made is only as wide as the tier that was completed:

- **Q1 (core, Tier 1).** Does *arrival-state* LOB information — depth-scaled impact and depth-based participation limits, measured at the moment the order arrives — improve a risk-aware schedule relative to state-blind references, at matched risk?
- **Q2 (extension, Tier 2).** Does *re-solving as the book is progressively revealed* (receding-horizon MPC) add value beyond Q1?

The optimizer is the instrument used to measure this. The **core deliverable** is the LOB-native cost model plus the static convex program.

```text
                      RESEARCH QUESTION
                             │
                             ▼
                Cost–Risk Optimal Execution
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
           Financial Model          OR Model
        (LOB cost and risk)        (convex QP)
                  │                     │
                  └──────────┬──────────┘
                             ▼
                     Execution Policy
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
              Static QP                MPC
            (CORE, Q1)          (EXTENSION, Q2)
                  │                     │
                  └──────────┬──────────┘
                             ▼
                  Walk-the-book Backtest
                             │
                             ▼
                     Statistical Study
```

### 1.1 User Interface (UI) / Interactive Analysis Tool

A user interface is **mandatory under both guidelines** (FE: run ≥2 distinct financial analyses from a menu; OR: load the dataset, generate statistics on demand, and perform ≥2 user-selectable optimisation models), so it is a **Tier 1 deliverable**, not an optional extra. The same capability is provided twice — a Streamlit web app (`app.py`) and a Jupyter/Colab notebook (`notebooks/rote_analysis.ipynb`) with widgets — and both are thin wrappers over the existing `src/` modules (no logic duplication). The UI exposes five panels:

1. **Dataset Loader.** Upload or select the FI-2010 file (path defaulting to `$ROTE_DATA_ROOT`); display dataset dimensions (rows × columns), detected stocks and days (A2), the recovered normalisation/scale (A1), and the data-quality/audit status (A0–A4) read from the Phase-1 audit report.
2. **Descriptive Statistics (on demand).** Spread, bid/ask depth, mid-price, order-book imbalance (OBI), volatility and liquidity statistics — mean, std, min, max and depth percentiles — plus the relevant plots on demand, all computed by the audit/feature pipeline.
3. **Optimisation / Analysis Menu.** The user selects the optimisation model and its parameters ($\theta$ or $Q$, $T$, $\lambda$, $\rho$), runs it on a chosen window, and sees the optimal execution schedule together with expected cost, realised risk, implementation shortfall and completion share. **At least two optimisation models are selectable, and both are guaranteed in Tier 1:**
   - **Model 1 — ROTE-Static (risk-aware optimal execution):** arrival-state convex QP with quadratic impact, risk penalty, participation constraints and terminal sweep (sections 5.4–5.5, rung 4).
   - **Model 2 — Almgren–Chriss:** classical risk–cost optimisation, state-blind reference, same order/horizon/risk framework (section 6, rungs 3/3b).
   - **Model 3 — ROTE-MPC (extension, Tier 2):** receding-horizon re-solve with updated book state (section 5.5, rung 5).
   Because Models 1 and 2 are both Tier 1, the UI satisfies the two-model requirement **even if MPC is cut** at the Phase-5 gate (section 10.2).
4. **Baseline / Comparison.** Selectable registered baselines for side-by-side runs: Immediate, TWAP$(T)$, TWAP$(T')$, Depth-Proportional (section 6).
5. **Results.** Execution schedule plot, cost decomposition (section 8.2), risk–cost frontier (E3), and the comparison table against the selected baseline.

**FE analyses menu (≥2 distinct financial analyses, as the FE guideline requires).** The same UI defines the following menu; A and B are the two required analyses and C is a third:

- **Analysis A — Optimal Execution.** Given an order of size $Q$, determine the execution schedule that minimises expected execution cost plus inventory risk under LOB-derived liquidity constraints (the core QP).
- **Analysis B — Execution Strategy Comparison.** Compare the selected optimal strategy against TWAP, Almgren–Chriss and Depth-Proportional using implementation shortfall, realised risk, CVaR, completion and cost decomposition.
- **Analysis C — Risk–Cost Frontier (optional third).** Evaluate how the optimal execution schedule and cost change as risk aversion $\lambda$ varies (E3).

The CLI (`run_experiment.py`) remains the reproducibility path (G14); the UI is the **user-facing** path required by the guidelines, and both call the same code.

### 1.2 Hypotheses (falsifiable, fixed before the test set is touched)

| ID | Hypothesis | Tier | Evidence that would support it |
|---|---|---|---|
| H1 | **Risk-aware optimization vs. the naive way of cutting risk.** At matched risk, Proposed-Static has lower mean implementation shortfall (IS) than **TWAP over a shortened horizon** $T'<T$ (trade evenly over the first $T'$ periods, then stop). Primary comparator: $T'=\lceil T/2\rceil$. | 1 | Matched-risk test (section 1.3): paired block-bootstrap 95% CI of the IS difference excludes 0 on the test set. |
| H2 | **The depth-scaled cost model predicts book-walk cost out of sample better than a constant-impact model.** | 1 | E0 (section 8.4): on test-split snapshots at pre-registered probe sizes, RMSE (bps) of $\tfrac12 S x+\eta_0 x^2/D^a_t$ below that of $\tfrac12 S x+c\,x$ (a constant slope $c$ fitted on the same calibration data); paired block-bootstrap CI of the RMSE difference excludes 0. |
| H3(a) | **Arrival-state information adds value beyond a state-blind risk-aware schedule.** Proposed-Static beats **capped** Almgren–Chriss (rung 3b, section 6) at matched risk. | 1 | Frontier comparison at three pre-registered risk levels (section 1.3); CI of the IS difference excludes 0. |
| H3(b) | **Progressively revealed state adds value beyond arrival state.** Proposed-MPC beats Proposed-Static at matched risk, with larger gains where within-horizon depth variability is high. | 2 | Same protocol; gain stratified by depth-variability tercile (variability is measured ex post and used only for stratification, never as a decision input). |

**What is *not* a hypothesis.** Comparative statics — schedules front-load more as risk aversion $\lambda$ or volatility $\sigma$ rises, and the first-period share falls as $\eta$ rises — are mathematical properties of the program. They are **model-verification tests** (T2, T3, T11), not empirical findings. The depth-response of Proposed-MPC (it trades more when the currently observed depth is high) is a **descriptive analysis** inside E6, and it needs **two** regressions, because the two strategies have different nulls. *MPC:* regress the planned share $x_k/y_k$ on $D^{a,\text{net}}_k/\bar D$ across $k$ within windows; the expected slope is positive. *Static:* its plan is frozen at arrival, so the correct null is **no within-window variation** — regress the planned share on the within-window demeaned depth (equivalently, test constancy of the planned share in $k$), and expect slope zero there. Reported separately, Static's *cross-window* level of trading does vary with arrival depth, so a regression of the period-1 share on $D^{a,\text{arr}}/\bar D$ is **not** expected to have slope zero and is not a test of anything; it is shown only to document the arrival-state scaling H3(a) is about. All depth measures used as regressors are gross ($D^a$, $D^{a,\text{arr}}$) or net ($D^{a,\text{net}}$) as labelled; $\bar D$ is always the calibration-set median **gross** ask depth, so a net regressor is scaled by a gross constant and the slope sign is unaffected but its magnitude is not comparable across the two regressions.

**Structure of the claim.** Proposed-Static differs from capped Almgren–Chriss only through (i) $\eta$ evaluated at *arrival* depth rather than median depth, (ii) the arrival-frozen participation cap inside the optimization, and (iii) the arrival-frozen sweep price. It does **not** use any within-horizon variation of the book (section 5.5) and its schedule is **spread-blind except through the sweep**. Precisely: $u$ is a decision, so $\tfrac12S\sum_t x_t=\tfrac12S(Q-u)$ is *not* constant across feasible plans, and substituting $u=y_{T+1}$ in section 5.4 leaves the objective $\tfrac12SQ+[\text{in-horizon terms}]+u(\psi+\bar\alpha_T-\tfrac12S)$. The spread therefore cannot move the *shape* of the in-horizon schedule for any fixed $u$, and cannot move the minimizer at all wherever $u=0$; it moves the chosen sweep share, and hence the plan, wherever the sweep is cheaper than or forced over a capped slice — precisely the penalty-dominated cells of section 8.1 ($\theta=5$ at $\varphi=0.5$; every $\theta\ge1$ at $\varphi=0$). H3(a) therefore tests *arrival-state scaling of the cost coefficient plus the in-QP cap*, nothing more. Time variation is H3(b)'s subject.

A null result on H1, H3(a) or H3(b) is acceptable and publishable; the study then characterizes *when* state-awareness matters. H1 is partly a sanity check, but the supporting statement is a **within-model** one and is labelled as such: under Gaussian independent increments with a quadratic cost and no binding caps, the mean–variance frontier point at any attainable risk level minimises mean cost at that level, and TWAP$(T')$ is not that point for any $\lambda$, so the frontier strictly dominates it — provided caps do not truncate the frontier at TWAP$(T')$'s risk. Outside those conditions H1 is a genuine empirical question, not a theorem. H2 is a model-fit result. **H3 carries the research claim.** If MPC is dropped at the Phase 5 gate (section 10.2), H3(b) lapses and the study answers Q1 only; this is stated in the report's abstract rather than discovered at the end.

### 1.3 What "matched risk" means

Realised risk of a strategy in a cell is the **standard deviation of IS (bps) across that cell's test windows**. **Cells are indexed by the participation level $\theta$, pooled over regimes and stocks, at the base resilience $\varphi=0.5$**, so each $\theta$-cell holds all $N_{\text{eff}}\ge100$ test windows (A6). **The one confirmatory cell is fixed in section 8.3: $\theta=1$, $\varphi=0.5$.** The other sizes are reported, and are outside the Holm family. The $3\times3$ volatility × liquidity cells (about $N_{\text{eff}}/9$ windows each) are descriptive and are not used for confirmatory matched-risk claims unless a cell holds at least 30 independent windows. Strategies with a risk parameter (Almgren–Chriss, Proposed) trace a frontier as $\lambda$ varies; TWAP$(T')$ traces a discrete frontier as $T'$ varies; Immediate, TWAP$(T)$ and Depth-Proportional are single points.

- **Matched risk = same position on the risk axis, not the same $\lambda$.** Equal $\lambda$ is an equal *preference*, not equal realised risk, so it is never called matched risk.
- **Why the comparator for H1 is TWAP$(T')$.** At $\lambda=0$ with constant parameters and no binding caps the program *is* TWAP$(T)$ (T1), and TWAP$(T)$ is the minimum-expected-cost schedule when drift is zero. A risk-matched comparison against TWAP$(T)$ itself would therefore be an identity up to cap effects. The honest naive way to cut risk is to finish sooner.
- **Protocol for point comparators (H1).** On the validation split, take the comparator's realised risk, and choose $\lambda^\*$ so that Proposed-Static's realised risk equals it, interpolating along a **monotone (isotonic) fit** of the validation frontier. Freeze $\lambda^\*$. On the test split report the paired IS difference with a moving-block bootstrap CI (section 8.3) **and** the realised-risk gap with its own paired bootstrap CI.
- **Acceptance rule (replaces a fixed numeric tolerance).** (i) If the test risk-gap CI contains 0, the strategies are *matched* and the IS difference is the result. (ii) If the CI excludes 0 but Proposed has both lower risk **and** lower mean IS, report **dominance** as such; it is stronger than matching. (iii) Otherwise the comparison is **not identifiable for that cell**: report the nearest frontier point and the realised-risk gap, and state that the comparison could not be formed. **No test-set tuning is performed to force a match.** Numeric constants — bootstrap block length, replications, the risk levels below — live in `configs/experiment.yaml`, not in this document (R13).
- **Non-identifiability on the validation frontier.** If the validation frontier does not reach the comparator's risk, the same case (iii) applies.
- **Protocol for frontier comparators (H3).** Compare mean IS at three pre-registered risk levels (validation-realised risk of the Proposed strategy at low, medium and high $\lambda$), freezing the comparator's $\lambda$ at each level from its isotonic validation frontier. The same acceptance rule applies at each level.
- The **risk–cost frontier figure (E3)** is the visual statement of all of this.

**What exists at the end.** (1) An LOB-native execution-cost model calibrated on FI-2010 with an out-of-sample test (H2); (2) a convex QP and, if time allows, an MPC wrapper; (3) a walk-the-book simulator with a resilience parameter; (4) a leakage-safe evaluation against a baseline ladder plus an oracle diagnostic; (5) an interactive UI (Streamlit app and/or Jupyter notebook) with dataset loading, statistics on demand and ≥2 selectable optimisation models (section 1.1); (6) a reproducible repository where `python run_experiment.py` regenerates every table and figure.

---

## 2. Problem Statement

### 2.1 The trade-off

An investor must buy $Q$ shares. Crossing the book at once consumes liquidity and pays a premium. Slicing the order lowers that premium but leaves unexecuted inventory exposed to price moves.

**Worked example.** Best bid $99.95$; asks $100.00\times800$, $100.05\times1{,}200$, $100.10\times2{,}500$. Mid $=99.975$.

Buying $2{,}000$ shares sweeps $800@100.00$ and $1{,}200@100.05$:

$$\text{cost}=80{,}000+120{,}060=200{,}060,\qquad \bar P=100.03.$$

Shortfall versus mid $=0.055$ per share $=5.5$ bps, which splits into half-spread $0.025$ (2.5 bps) plus book-walk premium $0.030$ (3.0 bps). This is the unit test for the cost function (T10) and the project's primary FE illustration: the cost is the *mechanism* of the book, not a curve fitted to it.

The toy book shows only $4{,}500$ shares. A $10{,}000$-share immediate order exceeds visible depth, so the project needs an explicit **completion rule** (section 5.4).

### 2.2 Why this is both FE and OR

- **FE** supplies the market model: mid-price, spread, depth, imbalance, volatility, walk-the-book execution cost, implementation shortfall. The implementation provides an interactive UI/menu for running financial analyses.
- **OR** supplies the decision model: choose $x_1,\dots,x_T$ to minimize expected cost plus a risk penalty subject to completion, non-negativity and liquidity constraints, and read the shadow prices. The UI allows users to select among multiple optimization models on demand.

The deliverable is a market model and an optimization model that are genuinely coupled, not a heuristic such as "trade less when volatility is high." The interactive interface satisfies both guideline requirements (dataset loading, statistics on demand, and ≥2 selectable models/analyses).

### 2.3 Course Alignment & Approval — **complete**

**Course alignment:** The project applies optimization to financial execution using a convex quadratic programming formulation. Optimal execution / convex QP is not explicitly listed among the supplied OR course topics (LP, transportation, assignment, network, integer, NLP, portfolio, goal programming, AHP), and optimal trade execution is outside the named FE topics — so instructor approval was required before implementation. **Status (2026-10-04): both approvals obtained.** The FE instructor sign-off is in place, the OR prior permission for this topic is in place, and the **First Project Review has been presented and completed**, with the methodology, tools, dataset and research questions of sections 2.4–2.5 accepted.

**Administrative (FE guideline):** a group of four members registers the project title and the dataset (FI-2010, public source) with the course representative on the CR's consolidated sheet, per the first-come-first-served dataset assignment. **Status: registration complete.** Registration is administrative and does not change this specification.

### 2.4 First Review Alignment

This proposal maps directly to the first review requirements:

1. **Significance** (sections 1, 2.1, 11) — Addresses the liquidity–risk trade-off in large-order execution and its relevance.
2. **Methodology** (sections 5-9) — Formal problem formulation, optimization, baselines, simulation, and evaluation protocol.
3. **Tools and Technologies** (section 2.5) — Python ecosystem, optimization, and UI tools.
4. **Dataset and Variables** (sections 3-4) — FI-2010 LOB data, preprocessing, variables, audit; shown live through the UI dataset-loader panel (section 1.1).
5. **Research/Business Questions** (sections 1, 8) — Q1/Q2, H1-H3b, with how optimization answers them.

### 2.5 Tools and Technologies

The following tools and technologies will be used to implement this project:

| Category | Tool/Library | Purpose |
|---|---|---|
| Programming | Python (>=3.11) | Core implementation language |
| Numerical Computing | NumPy, SciPy | Array operations, numerical methods |
| Optimization | CVXPY with OSQP (or ECOS) | Convex QP solver for execution scheduling |
| Data Processing | pandas | Data manipulation and analysis |
| Visualization | matplotlib, seaborn, Plotly | Static and interactive plots |
| Interactive UI | Streamlit | Web-based dashboard for dataset loading, stats, model selection |
| Interactive Notebooks | Jupyter/Colab | Alternative UI with widgets for easy demonstration |
| Statistics | statsmodels, bootstrapped | Statistical testing, bootstrap CIs |
| Testing | pytest | Unit/integration testing, T1-T14 correctness gates |
| Environment | uv | Dependency management and reproducible environments |

### 2.6 Positioning

The classical Almgren–Chriss (2000) programme minimises expected cost plus a variance penalty and yields the closed-form inventory trajectory $y_t=Q\,\sinh(\omega(T+1-t))/\sinh(\omega T)$ with $\cosh\omega=1+\lambda\sigma^2/2\eta$ in the discrete form used here. That form solves the program of section 5.4 as specified, where the curvature is transient quadratic impact; section 9 T4 says why it is re-derived rather than quoted. Those symbols are the paper's own, i.e. raw units; expressed in the implementation units in which this project actually solves the program (section 5.2) the same trajectory is $\cosh\omega=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$, and $\omega$ is the **single** urgency parameter used throughout this document (section 5.2 relates it to the square-root form; section 9 T4 tests against it). It is the reference this project is measured against, and four of its assumptions are exactly what a recorded book violates:

1. **Homogeneity.** Impact and volatility are constants; displayed depth can fluctuate substantially within a session (to be quantified in the Phase-1 audit) and volatility clusters.
2. **No microstructure state.** The model is invariant to depth, spread and imbalance — the variables that the microstructure literature links to short-horizon price pressure and liquidity cost. (In this project depth enters the schedule; the spread enters only through the chosen sweep share, section 1.2.)
3. **Open-loop scheduling.** A schedule computed once at arrival cannot use what the book reveals afterwards: depth and volatility drift away from their arrival values, so the pre-computed schedule goes stale. Re-solving as the book state updates is the case for Proposed-MPC (section 5.5), and why it is an extension rather than the core. Strategies that respond to realised *price* moves are a separate literature (Lorenz and Almgren, 2011) and are out of scope.
4. **Unconstrained trade sizes.** The classical solution ignores that displayed depth bounds what can physically be executed in a period. Here depth enters as a **constraint**, not only as a cost.

| Axis | Almgren–Chriss | ML-only LOB papers | This work |
|---|---|---|---|
| Cost model | constant impact | not the object of study | measured, walk-the-book |
| Liquidity | ignored | a feature | a feature **and** a hard constraint |
| Decision rule | closed form | point forecast | convex QP |
| ML role | none | end-to-end | ablation on the drift term only (section 5.6) |
| Claim | analytic | predictive accuracy | cost–risk improvement, falsifiable |

Explicitly **not** the claim: "a neural network was applied to FI-2010". The optimization problem is the contribution; machine learning is admitted only where it measurably improves a coefficient, and is removed if it does not.

---

## 3. Notation

| Symbol | Meaning |
|---|---|
| $Q$, $T$ | Parent order size (buy); number of execution periods |
| $m$ | Rows of event time per execution period (A3); a period spans $10m$ events |
| $T'$ | Shortened horizon of the TWAP$(T')$ comparator ($T'\le T$) |
| $x_t\ge0$ | Shares *planned* for period $t$ (decision variable in the QP) |
| $\text{fill}_t$ | Shares actually filled in period $t$ by the simulator (section 7.1) |
| $y_t$ | Inventory remaining **before** period $t$; $y_1=Q$, $y_{t+1}=y_t-x_t$ in the QP and $y_t-\text{fill}_t$ in the simulator. Hence $y_s=Q-\sum_{t<s}x_t=\sum_{t\ge s}x_t+u$ |
| $u\ge0$ | Residual inventory sent to the forced terminal sweep. In the QP, $u=y_{T+1}$ by construction (section 5.4); after simulation the realised residual is $u^{\text{real}}=y_{T+1}$, which equals $u$ only if no period came up short (section 7.1) |
| $C_{\text{sweep}}(u)$ | QP cost of the sweep, expressed (like every other term) as shortfall versus the arrival mid: $(\psi+\bar\alpha_T)\,u$ with $\psi=P^{\max}_{a,\text{arr}}(1+\pi)-M_0$ |
| $C^{\text{ex}}_{\text{sweep}}(u^{\text{real}})$ | **Cash paid** at the terminal sweep, including the penalty-priced shares beyond visible depth (section 7.1); the quantity that enters $\text{Spend}$ in section 8.2. Distinct from $C_{\text{sweep}}$, which is this cash less $M_0u$, i.e. the same cash expressed as shortfall versus the arrival mid |
| $P^a_t,\;P^b_t$ | Best ask, best bid at the snapshot of period $t$ |
| $p^a_{t,i},\;v^a_{t,i}$ | Ask price and volume at level $i=1..L$ ($L=10$ in FI-2010) |
| $M_t=\tfrac12(P^a_t+P^b_t)$ | Mid-price; $M_0$ is the **arrival mid** (benchmark); period 1 is the arrival snapshot, $M_1=M_0$ |
| $S_t=P^a_t-P^b_t$ | Spread |
| $D^a_t=\sum_{i=1}^{L}v^a_{t,i}$, $D^b_t$ | Total ask / bid depth (gross) |
| $D^{a,\text{net}}_t=\max(0,D^a_t-F_t)$ | Ask depth available to us (section 5.4) |
| $\mathrm{OBI}_t=\dfrac{D^b_t-D^a_t}{D^b_t+D^a_t}\in[-1,1]$ | Depth imbalance (**not** inventory) |
| $\sigma_t$ | Volatility of mid-price changes **per period** ($m$ rows) |
| $\eta_t$ | Impact coefficient (price per share per share); $\eta_t=\eta_0/D^a_t$ |
| $\tilde\eta_0=\eta_0/M_0$, $\tilde\sigma_t=\sigma_t/M_0$ | Dimensionless, **per-stock** versions used to solve the program (section 5.4, "Implementation units") |
| $\omega$ | Almgren–Chriss urgency parameter, the document's single symbol for it: $\cosh\omega=1+\lambda\sigma^2/(2\eta)$ in raw units (section 2.6), $=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$ in implementation units (section 5.2). The square-root form $\kappa=\sqrt{\lambda\tilde\sigma^2/(\tilde\eta_0\theta)}=\sqrt{2(\cosh\omega-1)}$ is the same quantity (section 5.2) |
| $\alpha_t,\ \bar\alpha_t=\sum_{s=2}^{t}\alpha_s$ | Expected mid-price drift per period; cumulative drift from the arrival mid. The first drift that can act is in period 2, since $M_1=M_0$ |
| $\hat\alpha_{\text{arr}},\ \hat\sigma_{\text{arr}}$ | **Frozen arrival-time estimates** of $\alpha_t$ and $\sigma_t$, held constant over the horizon in Proposed-Static (section 5.5); MPC replaces them by their period-$k$ values |
| $P^{\max}_a$ | Worst (deepest) visible ask price; charged for penalty-priced shares |
| $\pi$ | Sweep penalty as a fraction of price (default $0.005=50$ bps) |
| $\theta=Q/\bar D$ | Participation level of the parent order; $\bar D$ = per-stock calibration-set median ask depth (section 8.1) |
| $\lambda$ | Risk aversion. Two forms, related by $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ (or $=\lambda_{\text{raw}}QM_0/10^4$ if the common $10^4$ is carried inside the tildes instead of suppressed, section 5.2): $\lambda_{\text{raw}}$ is the coefficient of section 5.4 as written, in units of **one per unit of currency**, $1/(\text{price}\cdot\text{shares})$ — that is what makes $\lambda\sigma^2y^2$ a currency sum, and the same unit is what makes $\lambda_{\text{imp}}$ dimensionless. Labelling it $1/\text{price}$ is the error of one share-count, since $y^2$ is then not $y$; from section 5.2 on, $\lambda$ means the dimensionless $\lambda_{\text{imp}}$, and only the ratio $\lambda\tilde\sigma^2/(\tilde\eta_0\theta)$ affects the solution |
| $\rho$ | Participation cap: the per-period ceiling $x_t\le\rho D^{a,\text{net}}_t$ (section 5.4), and the simulator's per-period fill ceiling |
| $\varphi$ | Simulator resilience: the fraction of the footprint recovered per period (section 7.2) |
| $\tilde D_t$ | Trailing median of **gross** ask depth (causal), used only by the Depth-Proportional rung (section 6) |
| $c$ | The constant-impact slope fitted on the calibration data as H2's comparator (sections 1.2, 8.4 E0) |
| $B_0$ | Burn-in rows before the first window on the deterministic grid (A6, section 8.1); supplies trailing volatility estimates |
| $F_t$ | Footprint: our own unrecovered consumption, removed from the ask side before period $t$ (section 7.2) |
| $N_{\text{eff}}$, $b$ | Number of non-overlapping test windows (A6); bootstrap block length in windows (section 8.3) |

---

## 4. Data: FI-2010

### 4.1 Phase-1 data audit (the first deliverable; a gate, not an assumption)

**No optimization code is written before A0–A2 are answered.** The walk-the-book cost is only meaningful if prices and volumes are on real scales. The open-access FI-2010 release is *normalized in order to prevent reconstruction of the original Nasdaq data* [S], so whether a mid-price level is recoverable is the first thing to establish. An unexamined file makes the calibration of section 5.2 regress on quantities with arbitrary units, and every downstream number inherits the distortion.

**What the dataset paper and its distribution say, and how sure we are.** Every row is a *documented expectation for the audit to confirm*, never an assumption to build on.

| Property | Statement | Tag |
|---|---|---|
| Source | Nasdaq Nordic (Helsinki) ITCH feed; five stocks (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä); ten consecutive trading days, 1–14 June 2010 | [S] |
| Session | Helsinki trading runs 10:00–18:25 local; the dataset keeps only events between **10:30 and 18:00** local, excluding the pre- and post-opening auction periods. Original timestamps were shifted three hours from Eastern European Time (the paper quotes the day as 7:00–15:25 in the data's own clock) | [S] |
| Timestamps in the public files | Not among the 144 features + 5 labels, so no clock time is available; any intraday-seasonality control is therefore impossible | [C] |
| Row | Event-based: each representation is a vector for **10 consecutive events**. The paper reports **394,337 representations** from roughly four million events (its abstract's "≈4,000,000 samples" counts events). That ratio implies **non-overlapping blocks of 10 events**, not a stride of one | [S]/[C]: confirm by total row count (≈394k) |
| Features | 144-dimensional Kercheval–Zhang representation. Basic block = raw 10-level book (price and volume, both sides); the remaining blocks are derived time-insensitive and time-sensitive features | [S]; "first 40 columns" is [C] |
| Columns and labels | 149 columns = 144 features + 5 label columns. Labels (up/stationary/down at horizons of 1, 2, 3, 5, 10 events) are built from **future** mid-prices and are never read (section 5.6) | [S] for labels; 149 is [C] on the paper's text, **[S] on the dataset's distribution documentation** (rows 1–144 features, 145–149 labels) |
| Raw convention | Prices multiplied by $10^4$ and stored as integers; tick = one cent = **100 raw units**; volumes are integers | [S] |
| Folds and files | Day-anchored forward cross-validation: the training set grows by one day per fold (9 folds, training days $1..k$), the test set is the next day. Files are organised by {training, testing} × {with, without auction} × three normalizations; names look like `Test_Dst_NoAuction_ZScore_CF_9.txt` | [S] (layout); "every file holds all five stocks" is [C] on the paper's text and **[S] on the dataset's distribution documentation** |
| Normalizations | z-score, min–max and decimal precision; the paper's Eq. (5)–(7) are $\frac{x-\bar x}{s}$, $\frac{x-x_{\min}}{x_{\max}-x_{\min}}$ and $x/10^k$ with $k$ the integer for which $\max\lvert x\rvert<1$ | [S] |
| **Statistics scope** | Whether $\bar x,s,x_{\min},x_{\max}$ and $k$ are taken **per row** across the 144 features or **per feature** across the sample is *not settled by the paper's text* (Eq. (5) is written over a sample of $N$ vectors, which reads as per-feature). An earlier draft asserted per-row; that is withdrawn until A1 decides it | [C] |
| Availability | No un-normalized variant is distributed | [S] |

**The working file.** The author's file is described as roughly 48 columns and about 2 lakh (200,000) rows. That is not the published 149-column layout, so **A0 must first establish what the file is** (name, source, column count, row count, fold, auction flag). The day-block construction of section 4.3 applies only if it turns out to be a published training file; otherwise the general rule of section 4.3 applies. In every case all execution-relevant quantities ($P^a$, $P^b$, $S$, $M$, $D^a$, $D^b$, $\mathrm{OBI}$) are **recomputed from the raw 10-level block** and never read from derived columns.

**Decision rule for A1 — which variant can support this project.**

- **Decimal precision** divides by a power of ten with **no additive term**. Whether $k$ is per row or per feature, within-snapshot ratios (spread, book shape, relative depth) are exact, and — because raw prices sit on a 100-unit tick grid — the grid pins the absolute scale up to a **common power of ten**: the recovered prices and volumes are exact rather than "up to a constant" (the paragraph below on what the residual ambiguity does and does not affect; recipe at the end of this section). This is the only variant that can support the project.
- **Z-score and min–max** subtract an unknown location ($\bar x$ or $x_{\min}$). Under either scope the price *level* — hence $M_0$ and every bps metric — is not recoverable from the file alone; at most the tick scale and relative shape could be. **No inversion of these variants is attempted**; the option is closed in Phase 1 so it is not re-opened in Phase 4.
- Identify $k$ with the tick-grid test: raw price entries are integer multiples of 100 raw units, so the **smallest** candidate exponent under which every price entry of the row (or column) lands on that grid is a **lower bound** on $k$. Any larger exponent also passes, so the test is *one-sided*; the smallest passing value equals the truth unless every price in the unit shares extra trailing zeros, which is checked by cross-row/cross-column continuity and by integer volumes (recipe at the end of this section).
- **What a residual ambiguity costs, and why it does not block the project.** If the recovered exponent is wrong by $\delta$ decimals, prices *and* volumes are both off by the same factor $10^\delta$ (one exponent governs the file or the row), and then every quantity the study reports is unchanged: bps metrics and the spread-to-price ratio are price ratios; $\theta=Q/\bar D$ is a volume ratio; the implementation-unit impact coefficient $\tilde\eta_0\theta=\eta_0Q/(M_0D^a_t)$ has one $10^\delta$ in $\tilde\eta_0$ and one in $Q$ that cancel; and the sweep term $\psi u/(QM_0)$ scales as $10^{-2\delta}$ in both numerator and denominator. The **only** thing at stake is the absolute euro level, i.e. the euro translation of order size in A8. The scale question is therefore not a gate on the study — it is a gate on one row of one table — and the Phase-1 audit still records the exponent because A8 needs it.
- Run the discriminating recipes at the end of this section first. Their outcome decides whether the resolution order below is entered at step 1 or step 3.

| # | Check | Why it matters | Decision rule |
|---|---|---|---|
| A0 | **Provenance** of the working file | Everything below depends on what the file is | Record file name, source, fold, auction flag, rows, columns in `data/README.md`. If it is not a published file, skip the day-block recipe of section 4.3 |
| A1 | Which normalization variant, which scope (per-row vs per-feature), and is the scale recoverable | Impact calibration needs real price and volume *scales* | Proceed only if the file is decimal-precision **and** the exponent is identified by the tick-grid test. Otherwise enter the resolution order at step 3 |
| A2 | Day and stock boundaries; stock identity | A window straddling two stocks or two days is invalid; calibration is **per stock** | Day boundaries follow from the fold layout: rows of day $k$ = rows(train$_k$) − rows(train$_{k-1}$) and test$_k$ = day $k{+}1$ (confirm nesting by comparing leading rows). Stock boundaries are detected as discontinuities in the recovered mid-price level. If boundaries cannot be recovered, cluster the recovered mid level into five stocks; if that fails too, A2 fails and the project stops at the resolution order |
| A3 | Time axis | Rows are event blocks, not seconds | One period is $m$ rows $=10m$ events; windows start on a row grid; say "event time" in every figure caption |
| A4 | Book integrity | Garbage in, garbage out | Assert $P^a>P^b$, ask prices non-decreasing in level, bid prices non-increasing, volumes $\ge0$, no NaN, prices on the recovered tick grid. Use the **NoAuction** files; the auction-period data are structurally different and are expected to fail |
| A5 | Tick discretization | Mid-price often unchanged between rows, so $\hat\sigma$ can be 0 | EWMA over $\ge m$-row blocks with a floor $\sigma_{\min}$ [K]: the 10th percentile of non-zero calibration block volatilities, per stock |
| A6 | Effective sample size | Windows must not overlap | $N_{\text{eff}}=\sum_{\text{stock-day segments}}\lfloor (n_{\text{seg}}-B_0)/(T\cdot m)\rfloor$ over the test split, where windows start on a deterministic grid of stride $T\cdot m$ rows after a burn-in of $B_0$ rows [K, default 100] that supplies trailing estimates. Need $N_{\text{eff}}\ge100$ pooled; else shorten $T\cdot m$ or add data. If rows were found to overlap (A3), the stride is at least the overlap window |
| A7 | Fallback dataset | Last-resort insurance, **not** an equal-status branch | Only via the resolution order below |
| A8 | **Order-size realism** | $\theta=Q/\bar D$ is relative to *total ten-level* depth; $\theta\ge1$ exceeds all visible depth | Report $\bar D$ per stock in shares and in euros, depth percentiles, and the euro size of $\theta\in\{0.25,0.5,1,2\}$ against typical depth. Immediate at $\theta\ge1$ is penalty-dominated by construction, and results at those sizes are labelled as such |

**Resolution order if A1 fails (decided and logged in Phase 1, never discovered in Phase 4):**

1. **Work with the decimal-precision files**, with the exponent recovered by the tick-grid test. No un-normalized variant is distributed, so this is the only in-family route.
2. **Do not attempt z-score or min–max.** Listed as an explicit decision so the option is closed in Phase 1.
3. **Fall back** to a raw-price LOB dataset such as the free LOBSTER sample files. **Confirm in Phase 1 that suitable sample files exist and what they contain before relying on this route**: samples are typically one trading day for a few tickers at message-level (not 10-event-block) rows, so the split, $m$, $N_{\text{eff}}$ and the narrative would all be rebuilt. The seven-phase budget barely contains this; it is the last resort.

**Sizing $T\cdot m$ in Phase 1.** If the full ten-day set is available, 394,337 rows over ten days is about 39k rows per day for all five stocks, so test days 8–9 hold about 79k rows. At $T\cdot m=400$ that gives about 197 non-overlapping windows before burn-in and boundary losses, so $N_{\text{eff}}\ge100$ holds with margin. (If the file in hand has about 2 lakh rows, a 20% test split leaves about 40k rows and $T\cdot m\lesssim400$ is the binding bound.) This must hold *together with* the feasibility bound of section 8.1, $T\gtrsim\theta/f(\varphi)$; at the default $\rho=0.25$ and $\varphi=0.5$ that is $T\ge5\theta$, so $T=20$ with $m=20$ covers $\theta\le4$. If the audit finds materially fewer rows than assumed, the trade-off is decided explicitly and the binding constraint recorded (R15).

The outcome and its reason go in `docs/decision_log.md`; the audit report lives in `data/README.md` beside the loader. Until A1 has recovered the absolute level, worked examples are written in "price units"; FI-2010 is a European venue quoted in euros (the "Raw convention" row above), so A8's euro translation is possible only after A1.

**Scale-recovery recipes.** These are the discriminating tests referred to above. They are illustrative — verify them on the real file. In the code they belong to the loader and the audit module, not to this document; they are stated here because the decision rule is stated here.

*Discriminate per-row from per-feature scope* (decimal-precision file, array `X`, rows × 144 features):

```python
row_max = np.abs(X).max(axis=1)      # per row
col_max = np.abs(X).max(axis=0)      # per feature
# per-row k    -> row_max concentrated in [0.1, 1) for (nearly) all rows
# per-feature k -> col_max in [0.1, 1) for each feature, row_max varies widely
```

For z-score files compare column means/stds across rows (≈0/1 means per-feature) with row means/stds across features.

*Tick-grid exponent* for the raw price entries `p` of one row (or column): raw price $=x\cdot10^k$ must be an integer multiple of 100.

```python
def smallest_grid_exponent(p, kmax=12, tol=1e-6):
    for k in range(kmax + 1):
        raw = p * 10.0**k
        if np.all(np.abs(raw - np.rint(raw)) < tol * max(1.0, np.abs(raw).max())) \
           and np.all(np.rint(raw) % 100 == 0):
            return k
    return None   # fails: investigate precision of the text format
```

Any larger exponent also passes, so keep the smallest — as a **lower bound**, not as the value — and cross-check with integer volumes (`vol * 10.0**k` integer) and with continuity of $k$ across neighbouring rows or columns. If the file's text precision truncates values, widen `tol` and re-check before trusting $k$.

A residual $\delta$-decimal error in the exponent is **not** a blocker, for the reasons given in the bullet above. What *would* be a blocker is a per-feature scope that gave prices and volumes **different** exponents, because the two would then no longer cancel; test for that explicitly before accepting a scale.

*Day boundaries:* `rows_day_k = len(train_k) - len(train_{k-1})`; confirm `train_{k-1}` equals the leading rows of `train_k` (day-major) before relying on it.

### 4.2 Features (all strictly causal)

- Mid $M_t$, spread $S_t$, depths $D^a_t,D^b_t$, imbalance $\mathrm{OBI}_t$, **all recomputed from the raw LOB levels** and never read from precomputed columns.
- Log mid return $r_t=\ln(M_t/M_{t-1})$ and EWMA volatility $\hat\sigma_t$ per period, using data up to $t$ only, within the current stock-day segment. This is the **only** volatility estimate in the project and is shared by Proposed and Almgren–Chriss.
- Regime labels (volatility and liquidity terciles) with **thresholds computed on the calibration split only, per stock**. Stock identity must therefore be recovered (A2).
- **Optional, Tier 2 / E6 only:** micro-price premium $(\mu^{\text{micro}}_t-M_t)/M_t$ with $\mu^{\text{micro}}_t=(P^a_tv^b_{t,1}+P^b_tv^a_{t,1})/(v^a_{t,1}+v^b_{t,1})$ (top-of-book sizes), and order-flow imbalance $\mathrm{OFI}_t$ (a proxy only: each row summarises ten events, which hides the message sequence OFI is computed from). Both are admissible **only** as extra regressors in the drift model of section 5.3, on the same out-of-sample gate as $\mathrm{OBI}_t$. They are never decision-time thresholds, and they cost nothing when unused.

### 4.3 Splits

Chronological, never random, and by whole-day blocks wherever days are identifiable:

| Split | Share | Used for |
|---|---|---|
| Calibration | first ≈60% | Fit $\eta_0$, $\beta$ (drift), $\sigma_{\min}$, regime thresholds, per stock |
| Validation | next ≈20% | Choose $\lambda$ grid and $\lambda^\*$, $\rho$, $T$, $m$, $T'$, model variants |
| Test | final ≈20% | Run **once** from a frozen config |

Leave a purge gap of at least $T\cdot m$ rows between splits (automatic with day blocks). Split indices are committed to `configs/splits.yaml` in Phase 1 and tagged `splits-frozen`. If several stocks or days are concatenated in the file (A2), **apply the split within each stock segment and pool the results**. A single split over the concatenated rows would put whole stocks into calibration, validation and test, an unintended leave-stock-out design that breaks the transfer of $\eta_0$ and the regime thresholds.

**Leave-one-stock-out is not part of this protocol.** It is a Tier 3 item (section 13). The split file must not carry an active generalisation mode until Tier 3 is opened.

**Building the split from the published fold layout** (applies only if A0 shows a published training file). The public testing files hold a single day each, so the split is constructed *inside the largest available training file* (fold 9: days 1–9), cut on whole days: days 1–5 calibration, 6–7 validation, 8–9 test, with day 10 (fold 9's testing file) held in reserve and, if ever used, treated as exploratory. Whole days give shares of 5/9, 2/9 and 2/9 — about 56/22/22, not exactly 60/20/20; the shares are rounded to whole days by design. A window straddling a day boundary is impossible by construction. What must not happen is a random split or a split that cuts inside a day.

---

## 5. Model

### 5.1 Execution cost from the book

Buying $x$ shares at a snapshot walks the ask side: fill level 1 up to $v^a_{t,1}$, then level 2, and so on:

$$C_t(x)=\sum_{i=1}^{L}p^a_{t,i}\,q_{t,i},\qquad q_{t,i}=\min\Big(v^a_{t,i},\ \big(x-\textstyle\sum_{j<i}v^a_{t,j}\big)^+\Big).$$

Cost versus mid is $C_t(x)-xM_t=\tfrac12 S_t x+\big(C_t(x)-xP^a_t\big)$: half-spread plus **book-walk premium** $w_t(x)\cdot x$. Fills are limited to **net** depth (sections 5.4, 7.1); the full ordering of every cost term is in section 8.2.

### 5.2 Approximate cost model used by the QP

$$\text{cost}_t(x)\approx \tfrac12 S_t\,x+\eta_t\,x^2,\qquad \eta_t=\eta_0/D^a_t .$$

$\eta_0$ is calibrated **per stock on the calibration split**: sample snapshots, evaluate the exact walk premium $w_t(x)$ at probe sizes $x=sD^a_t$ for $s$ on a pre-registered grid up to $\rho$, and regress $w_t(x)$ on the model's own regressor $x^2/D^a_t$ through the origin, pooling every sampled snapshot of that stock; the slope **is** $\eta_0$. (Regressing on $x/D^a_t$ instead would fit a *linear-in-participation* form and return $\eta_0\bar D$, not $\eta_0$ — that is a different model and the specification error is not detectable from $R^2$.) Report $R^2$, the residual pattern, and the fraction of the premium that is exactly zero (small orders inside the top level pay none; the quadratic overstates there).

*Why depth in the denominator:* Cont, Kukanov and Stoikov (2014) show that price impact scales inversely with depth; Tóth et al. (2011) and Bucci et al. (2019) show a linear-to-square-root crossover for large metaorders, so the quadratic form is a **local** approximation inside the participation range used here (a limitation stated in the report, section 7.3).

**Exact-book alternative (reported as a robustness check, not a competing method).** Replace $\eta_tx^2$ by per-level variables $q_{t,i}\in[0,v^a_{t,i}]$ with linear cost $\sum_i p^a_{t,i}q_{t,i}$; the cost is then exact and the program is quadratic only through the risk term. Ascending prices make the optimizer fill cheaper levels first, so no integer logic is needed.

**Implementation units.** The program is solved per stock in dimensionless form: $\xi_t=x_t/Q$, with the section 5.4 objective divided by the arrival notional $QM_0$ and reported in bps (a further $10^4$). A factor common to every block changes no minimizer, so the $10^4$ is placed **once**, in the reporting step, and is **suppressed** everywhere else: the bps block is written without it and the risk coefficient absorbs the whole conversion, $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ (section 3). With that convention a term $\eta_tx_t^2$ becomes $\tilde\eta_0\,(Q/D^a_t)\,\xi_t^2$, the half-spread term becomes $\tfrac12(S_t/M_0)\xi_t$, the drift term becomes $(\bar\alpha_t/M_0)\xi_t$, and risk becomes $\lambda\tilde\sigma_s^2(y_s/Q)^2$. Note the $QM_0$ in the conversion and the $Q/M_0$ in $\tilde\eta_0$: they are different, and a $Q/M_0$ written on the $\lambda$ line is wrong by $M_0^2$. Pooling $\lambda$ across stocks at different price levels is meaningful only in these units. The Almgren–Chriss urgency parameter is $\kappa=\sqrt{\lambda\tilde\sigma^2/(\tilde\eta_0\theta)}$ in these units, identical to the $\omega$ of section 2.6 and section 9 T4 via $\kappa=\sqrt{2(\cosh\omega-1)}$; $\omega$ is the canonical symbol and $\kappa$ its square-root shorthand, and **the two must never be used for different quantities**. T13 verifies invariance to price and volume rescaling.

**The $10^4$ has exactly one home, and the identity says where.** Only the ratio $\lambda\tilde\sigma^2/(\tilde\eta_0\theta)$ affects the solution, and that ratio must equal $\lambda_{\text{raw}}\sigma^2/\eta$. Exactly two placements satisfy it. The project uses the first: the $10^4$ is suppressed from the tildes, $\tilde\eta_0=\eta_0/M_0$, $\tilde\sigma_t=\sigma_t/M_0$, and $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ as written, with the factor entering only when reporting bps. The second carries the factor in both tildes, $\tilde\eta_0=10^4\eta_0/M_0$ and $\tilde\sigma_t=10^4\sigma_t/M_0$, and **divides** $\lambda_{\text{imp}}$ by the same $10^4$. Any other placement breaks the ratio and changes the program: the tildes alone leave it $10^4$ too large, $\lambda_{\text{imp}}$ alone $10^4$ too small, and both together $10^8$ too large, because $\tilde\sigma_t^2$ then grows by $10^8$ against $\tilde\eta_0$'s $10^4$. Writing $Q/M_0$ on the $\lambda_{\text{imp}}$ line is likewise wrong, by $M_0^2$. The identity is asserted numerically in `` section 3, not assumed.

### 5.3 Price risk and drift

Mid-price changes per period have variance $\sigma_s^2$ and drift $\alpha_s$. With period 1 the arrival snapshot ($M_1=M_0$), the timing cost is $\sum_{t}(M_t-M_0)x_t$ (plus the same exposure on any swept residual), whose variance is

$$\mathrm{Var}=\sum_{s=2}^{T}\sigma_s^2\,y_s^2,\qquad \text{and expected timing cost }\ \sum_t\bar\alpha_t x_t,\quad \bar\alpha_t=\sum_{s=2}^{t}\alpha_s .$$

(Summing from $s=2$ drops the arrival shock, which never occurs: period 1 is the arrival snapshot, so no drift risk is carried before the first decision.)

**Drift model (Tier 2, ablation).** $\alpha$ is $0$ unless an out-of-sample gate passes: regress the mid change over the next $m$ rows on $z_t=(\mathrm{OBI}_t,\dots)$ on the calibration split, and keep the term only if validation out-of-sample $R^2>0$ with a stable sign. When used, Static freezes $\hat\alpha_{\text{arr}}$ and sets $\bar\alpha_t=(t-1)\hat\alpha_{\text{arr}}$; MPC at period $k$ sets $\bar\alpha_t=(t-k)\hat\alpha_k$ over $t\ge k$.

### 5.4 The optimization problem

For a buy order, with data frozen according to section 5.5:

$$\min_{x}\ \sum_{t=1}^{T}\Big(\tfrac12 S_t x_t+\eta_t x_t^2+\bar\alpha_t x_t\Big)+\lambda\sum_{s=2}^{T}\sigma_s^2 y_s^2+(\psi+\bar\alpha_T)\,u$$

subject to $y_1=Q$, $y_{t+1}=y_t-x_t$, $u=y_{T+1}\ge0$, $0\le x_t\le\rho\,D^{a,\text{net}}_t$.

- **Sweep price uses arrival information only:** $\psi=P^{\max}_{a,\text{arr}}(1+\pi)-M_0$ (Static); MPC at period $k$ uses $\psi_k=P^{\max}_{a,k}(1+\pi)-M_k$, with drift measured from the current mid. The horizon-end mid $M_T$ and the final snapshot's worst ask are look-ahead and are not admissible as a sweep price; T8 is the test that catches it.
- **Net depth.** $D^{a,\text{net}}_t=\max(0,D^a_t-F_t)$. At planning time Static has $F=0$ and uses $D^a_{\text{arr}}$; the simulator enforces the cap on the *actual* net depth. MPC uses the observed $F_k$.
- **Why a terminal sweep and not a hard completion constraint:** a fixed horizon with caps can be infeasible. The sweep prices the shortfall at the worst visible ask plus penalty rather than leaving the instance undefined; the QP is always feasible. Because $u$ is determined by $x$, the objective is strictly convex in $x$ whenever $\eta_t>0$, so the minimizer is unique. Every strategy is judged against realised walk-the-book execution **including** the sweep, so no strategy can win by leaving inventory unfilled.
- **Shadow prices.** The duals of the participation caps $x_t\le\rho D^{a,\text{net}}_t$ are reported in E2 as interpretable output: the marginal cost of a unit of extra depth, i.e. which periods are liquidity-bound. There is **no** completion constraint and therefore **no** completion dual — $u=y_{T+1}$ is a definition, not a constraint. Two related quantities are reported instead, and they are **not** the same number: the reduced cost of terminal inventory, which is $\psi+\bar\alpha_T$ and is the cost of carrying one further share to the horizon end (the price of incompleteness, equal to the sweep price); and the marginal cost of one more share of $Q$, $\partial V/\partial Q$, which is the dual of $y_1=Q$ and depends on the whole solution path. E2 reports both, labelled.
- **Risk alternative.** CVaR via the Rockafellar–Uryasev linearization is a Tier 3 option (section 13).

### 5.5 Information structure: Static vs MPC

**Proposed-Static** is solved once at arrival with every time-varying input frozen at its arrival value: $S_t\to S_{\text{arr}}$, $\sigma_t\to\hat\sigma_{\text{arr}}$, $D^a_t\to D^a_{\text{arr}}$ (so $\eta_t=\eta_0/D^a_{\text{arr}}$ and the cap is $\rho D^a_{\text{arr}}$), $\bar\alpha_t\to(t-1)\hat\alpha_{\text{arr}}$, $\psi\to\psi_{\text{arr}}$. Consequences stated plainly: its schedule is a function of arrival depth, arrival volatility and the cap, **and nothing else**; $S$ affects realised cost but never the minimizer.

**Proposed-MPC** re-solves at every period $k$ over the remaining horizon with parameters frozen at their period-$k$ values, actual inventory $y_k$, observed footprint $F_k$, and executes only $x_k$ (subject to the cap on actual net depth). Differences from Static come from **two** sources: updated state (depth, volatility, drift) and re-optimization after shortfalls. To separate them, E6 includes **MPC-inventory-only** (rung 5a: parameters frozen at arrival, re-solved only for realised inventory).

**Oracle-state (diagnostic, never a competitor).** The same program with the *true future* $S_t$, $D^a_t$ (hence $\eta_t$, caps) and $\sigma_t$ known and $\alpha=0$. It bounds the value of knowing the future *book state*; it has no price foresight, and to keep it that way its sweep is priced exactly as Static's — arrival-frozen $\psi=P^{\max}_{a,\text{arr}}(1+\pi)-M_0$ — never from a future worst ask, and drift is still zero.

### 5.6 Role of machine learning

Admitted only as the drift term, behind the out-of-sample gate of section 5.3, and as a labelled ablation. FI-2010's up/stationary/down labels are built from future mid-prices and are **never read**. Any ML component that does not beat the no-ML version on validation is removed and the negative result reported.

---

## 6. Baselines (the ladder)

| # | Strategy | Info used | Caps | Tier |
|---|---|---|---|---|
| 0 | **Immediate** (market order at arrival; residual priced as a sweep at $t=1$) | none | no | 1 |
| 1 | **TWAP$(T)$** (equal slices over $T$) | none | no | 1 |
| 1b | **TWAP$(T')$**, $T'<T$ (H1 comparator) | none | no | 1 |
| 2 | **Depth-Proportional**: $x_t=\min\!\big(\rho D^{a,\text{net}}_t,\ y_t,\ \tfrac{y_t}{T-t+1}\cdot\tfrac{D^{a,\text{net}}_t}{\tilde D_t}\big)$, $\tilde D_t$ = trailing median of gross ask depth (causal) | depth | yes | 1 |
| 3 | **Almgren–Chriss** closed form, $\eta=\eta_0/\bar D$ — impact at the **median** depth, i.e. $\tilde\eta_0\theta$ in implementation units (section 5.2) — volatility $\hat\sigma_{\text{arr}}$ (same estimator as Proposed), same $\lambda$ grid | none | no | 1 |
| 3b | **AC-capped**: the rung-3 trajectory executed with $\min(\text{offered},\rho D^{a,\text{net}}_t)$ and catch-up | depth (cap only) | yes | 1 |
| 4 | **Proposed-Static** (section 5.4–5.5) | arrival state | in QP | 1 |
| 5 | **Proposed-MPC** | updated state | in QP | 2 |
| 5a | MPC-inventory-only (ablation) | inventory only | in QP | 2 |
| 6 | Proposed-MPC + drift | + OBI drift | in QP | 2 |
| — | Oracle-state | true future state | in QP | diagnostic |

**Execution rule shared by all static schedules (TWAP, AC, AC-capped, Depth-Prop, Proposed-Static):** at period $t$ the offered quantity is $\min\big(y_t,\ \sum_{s\le t}x^{\text{plan}}_s-\sum_{s<t}\text{fill}_s\big)$ ("catch-up to the planned cumulative schedule"); capped strategies then apply $\min(\cdot,\rho D^{a,\text{net}}_t)$. MPC's $x_k$ comes from the re-solve. Each rung adds exactly one ingredient: **2 vs 1** isolates depth-proportional slicing, **3b vs 3** isolates the cap, **4 vs 3b** isolates arrival-state scaling of $\eta$ and the in-QP cap and sweep (H3(a)), **5 vs 4** isolates progressive state (H3(b)), **5a** separates re-optimization from information. VWAP is not used: FI-2010 rows lack timestamps and volume profiles, so a historical volume curve cannot be built, and the report says so.

**The two guaranteed UI-selectable optimisation models (OR guideline).** Rungs **4 (Proposed-Static QP)** and **3/3b (Almgren–Chriss)** are the two optimisation models the UI must offer (section 1.1), and **both are Tier 1** — Almgren–Chriss is a genuine risk–cost optimisation (closed-form solution of the classical mean–variance execution programme), not a heuristic. Rung 5 (MPC) is the optional third model. Even if Tier 2 is dropped, the UI therefore always exposes two selectable optimisation models.

---

## 7. Execution Simulator

### 7.1 Algorithm

```text
for t = 1 .. T:                                  # snapshot t = w + (t-1)*m, w = window start
    offered_t ← strategy(state_t, y_t, fills so far)       # catch-up rule (section 6) or MPC re-solve
    if strategy is capped: offered_t ← min(offered_t, ρ · D_net_t)
    fill_t   ← walk the NET ask side until offered_t is filled or net depth is exhausted
    y_{t+1}  ← y_t − fill_t
    F_{t+1}  ← (1 − φ) · (F_t + fill_t)                   # footprint with resilience φ
after t = T:
    sweep y_{T+1} against snapshot T's book net of (F_T + fill_T);
    # NB: no resilience recovery on period T's own fill, unlike the F_{t+1} line above.
    # Stated, not incidental — it is the conservative choice and T9 asserts it.
    shares beyond visible depth are charged P_max · (1 + π)
```

Immediate is the case $T=1$ with $\text{offered}_1=Q$ and the sweep rule applied at $t=1$ (so its residual is never left exposed). For a **sell** order mirror the bid side; the sell-side sanity run reproduces the buy-side pattern by symmetry. Note one deliberate asymmetry inside the loop: within the horizon the footprint entering period $t$ is $F_t=(1-\varphi)(F_{t-1}+\text{fill}_{t-1})$, whereas the sweep is priced against depth net of $F_T+\text{fill}_T$, so the final period's own fill earns **no** recovery. Charging the less-recovered alternative is the conservative choice, and it is asserted in T9 so that a later reader cannot "fix" it silently.

### 7.2 Footprint and resilience

Our own fills remove displayed liquidity that the replayed book does not know about. The **footprint** $F_t$ is deducted from ask depth, and recovers by a fraction $\varphi$ per period. $\varphi=1$ is naive replay (an optimistic bias); $\varphi=0$ is permanent consumption (pessimistic). **Base case $\varphi=0.5$**; $\varphi\in\{1,0.5,0.25,0\}$ is a pre-registered sensitivity (E5).

### 7.3 Assumptions and limitations (stated in the report, not hidden)

| ID | Assumption | Bias |
|---|---|---|
| S1 | The book replays historically; no reaction to our orders beyond $F_t$ | optimistic |
| S2 | Other participants' behaviour is static | optimistic |
| S3 | Orders fill only against **visible** depth and hidden liquidity is ignored — pessimistic in itself; but the replay also assumes an offered quantity fills at the touch with **no queue-ahead uncertainty** and no partial-fill probability — optimistic. The two effects push in opposite directions | mixed; the queue assumption is the one that flatters aggressive strategies, and it is stated as a limitation rather than netted out |
| S4 | Taker-only; no passive orders, no fees, no latency | neutral/optimistic |
| S5 | Quadratic cost model is a local approximation (square-root crossover for large sizes) | model risk |
| S6 | Rows are 10-event blocks without timestamps: no intraday-seasonality control; calendar-time results cannot be stated | scope |
| S7 | Stock-windows within a day share a market factor; pooled windows are not fully independent | CI optimism, handled in section 8.3 |
| S8 | 10 days in June 2010 on a Nordic venue; no claim about other venues or regimes | external validity |

---

## 8. Evaluation Protocol

### 8.1 Instances and parameter grid

- **Instances.** Windows start on the **deterministic non-overlapping grid** of A6 (stride $T\cdot m$ rows, after burn-in $B_0$), fixed once and **reused for every strategy and every $\theta$**. Random start rows are not used, so $N_{\text{eff}}$ is real and every comparison is paired.
- **Sizes.** $\theta\in\{0.25,0.5,1,2\}$, plus a stress size $\theta=5$ (expected to force sweeps). $\bar D$ is the per-stock calibration-set median ask depth; $Q=\theta\bar D$. A8 translates each $\theta$ into euros.
- **Defaults [K].** $T=20$, $m=20$ (so $T\cdot m=400$), $\rho=0.25$, $\pi=0.005$, $\varphi=0.5$, $\lambda$ on a log grid chosen on validation.

**Feasibility must include the footprint.** With constant fills $f$ per period and resilience $\varphi>0$, the steady-state footprint is $F^\*=(1-\varphi)f/\varphi$ and $f\le\rho(D-F^\*)$ gives the sustainable throughput

$$f(\varphi)=\frac{\rho\,\varphi}{\varphi+\rho(1-\varphi)}\,D .$$

| $\varphi$ | $f(\varphi)/D$ at $\rho=0.25$ | Approx. $T$ needed to finish without sweep |
|---|---|---|
| 1 | 0.250 | $\approx 4\theta$ |
| 0.5 | 0.200 | $\approx 5\theta$ |
| 0.25 | 0.143 | $\approx 7\theta$ |
| 0 | total fill $\le D\,(1-(1-\rho)^T)<D$ | impossible for $\theta\ge1$; $\theta=0.5$ needs $T\gtrsim3$ |

These ignore depth variation and the initial transient, so they are guides, not guarantees. Consequences: at $T=20$, $\varphi=0.5$ every grid size completes without the sweep on average and $\theta=5$ does not; **at $\varphi=0$ every $\theta\ge1$ hits the sweep**, so slicing comparisons at $\varphi=0$ are restricted to $\theta\le0.5$ and larger sizes are reported as penalty-exposure comparisons. The stale v4 rule "$T\ge\theta/\rho$" ignored the footprint and is withdrawn.

### 8.2 Metrics

$$\text{Spend}=\sum_t C_t(\text{fill}_t)+C^{\text{ex}}_{\text{sweep}}(u^{\text{real}}),\qquad \text{IS}_{\text{bps}}=10^4\,\frac{\text{Spend}-QM_0}{QM_0}.$$

| Component | Definition |
|---|---|
| Half-spread | $\sum_t\tfrac12S_t\,\text{fill}_t$ |
| Book-walk (in horizon) | $\sum_t\big(C_t(\text{fill}_t)-P^a_t\,\text{fill}_t\big)$ |
| Timing (in horizon) | $\sum_t(M_t-M_0)\,\text{fill}_t$ |
| Sweep execution | $C^{\text{ex}}_{\text{sweep}}(u^{\text{real}})-M_Tu^{\text{real}}$ |
| Sweep timing | $(M_T-M_0)\,u^{\text{real}}$ |
| of which penalty premium | shares beyond visible depth $\times\big(P^{\max}_a(1+\pi)-M_T\big)$ |

The execution-cost terms (half-spread, book-walk, sweep execution) plus the two timing terms sum exactly to $\text{Spend}-QM_0$, which T12 checks. All three sweep rows use $u^{\text{real}}$, the residual actually left after simulation, which equals the QP's planned $u$ only when no period came up short (sections 3, 7.1); every component row is computed from executed shares, never from the plan. Also reported: realised risk (std of IS) and CVaR$_{95}$, completion share (non-swept), peak participation, win rate versus TWAP$(T)$, and **predicted vs realised cost** (QP expected cost without the $\lambda$ term versus realised IS, both converted to bps of $QM_0$ before comparison; calibration slope near 1 is the target).

### 8.3 Statistics

- **Resampling unit and dependence.** Windows are non-overlapping, but regimes persist, so use a **moving-block bootstrap over windows within each stock-day series**, block length $b$ windows (pre-registered; default 5). All comparisons are **paired** by window. Day-clustered intervals (10 stock-day series in the test split) are reported as a *sensitivity only*: two test days cannot support day-blocking as the primary scheme.
- **Cross-stock dependence.** Stock-windows on the same day share a market factor; stock-wise results are shown alongside the pooled result, and the pooled CI is read with S7 in mind.
- **One confirmatory family.** Primary tests, all in the primary cell $\theta=1$, $\varphi=0.5$: H1 at $T'=\lceil T/2\rceil$, H2 pooled, H3(a) at the **medium** risk level, and (if run) H3(b) at the same cell. Holm correction across this family at 0.05. Everything else (other $\theta$, risk levels, $T'$, $\varphi$, regimes, stocks) is **secondary/exploratory**, reported with unadjusted CIs and a stated count of comparisons. In particular the low and high risk levels of section 1.3 are reported with the same acceptance rule but sit **outside** the Holm family.
- **Power.** In Phase 1 compute the minimum detectable effect, $\text{MDE}\approx2.8\cdot \mathrm{SE}_{\text{paired}}$, for 80% power. $\mathrm{SE}_{\text{paired}}$ is the **block-bootstrap** standard error of the paired difference at the pre-registered block length, taken on validation — *not* $\mathrm{SD}/\sqrt{N_{\text{eff}}}$, which assumes independence and therefore understates it: the resampling unit is a block, so only about $N_{\text{eff}}/b$ independent units exist. If the MDE exceeds the paired difference observed on validation, **or** the block length is not supported by the shortest stock-day series (section 8.3), the primary tests are declared **descriptive** in advance.
- **Matched risk** is judged by the acceptance rule of section 1.3, not by a fixed percentage; the standard deviation of IS over about 100 windows carries roughly 7% sampling error (more under fat tails), which is why a fixed tolerance would reject most cells.
- **Thin cells.** The $3\times3$ regime grid has about $N_{\text{eff}}/9$ windows per cell. Show CIs; prefer the **tercile marginals** (one dimension at a time, $N_{\text{eff}}/3$ windows).

### 8.4 Experiments

| ID | Experiment | Tier | Split |
|---|---|---|---|
| E0 | Cost-model out-of-sample test (H2). The Phase-2 development run of this experiment uses **validation**; only the single test run below is confirmatory | 1 | test |
| E1 | Ladder table: mean IS, risk, CVaR, completion, by $\theta$ (primary cell first) | 1 | test |
| E2 | Shadow prices and cost decomposition (cap duals, terminal-inventory reduced cost and $\partial V/\partial Q$, section 5.4; components, section 8.2) | 2 | test |
| E3 | Risk–cost frontier figure with matched-risk tests (section 1.3) | 1 | test (λ frozen on validation) |
| E4 | Regime analysis: tercile marginals; $3\times3$ grid descriptive | 1 | test |
| E5-min | Resilience $\varphi\in\{1,0.5\}$ (and $\{0.25,0\}$ for $\theta\le0.5$) | 1 | test |
| E5 | Full sensitivity: $\varphi$, $\pi\in\{25,50,100\}$ bps, $\rho$ | 2 | test |
| E6 | Ablations: MPC-inventory-only (5a), drift, depth-response regression (section 1.2), exact-book variant | 2 | test |
| E7 | Design sensitivity ($T$, $m$, $b$, $\sigma_{\min}$, $T'$) | 2 | **validation only** |

Priority order for the sprint: E0, E1, E3, E4, E5-min, then E2, E6, E5, E7.

### 8.5 Pre-registration (frozen configuration)

There is **no separate pre-registration document**; the mechanism is the frozen configuration. Every numeric constant lives in `configs/experiment.yaml` — the source of truth for experiment numbers — and is **frozen by committing it and tagging `config-frozen` with the config hash before any test row is read** (G10). The single test run (G11) must execute from that frozen config. It fixes: the primary tests and Holm family, $\theta$ grid, $T$, $m$, $\rho$, $\pi$, $\varphi$, $T'$, the three risk levels, bootstrap block length and replications, the $\sigma_{\min}$ rule, $B_0$, the MDE and which tests are descriptive, and the experiments run on test. The acceptance rule of section 1.3 is in the text; its numeric parameters are set *after the validation frontier exists and before the first test run*, written into `configs/experiment.yaml` before the `config-frozen` tag. A post-freeze change to any constant is labelled *post hoc* (section 10.4).

---

## 9. Correctness Standards

**Unit and property tests (all must pass before any experiment).**

| ID | Test |
|---|---|
| T1 | Constant parameters, $\lambda=0$, no binding caps, $\alpha=0$: the QP returns TWAP$(T)$ |
| T2 | Model verification: larger $\lambda$ or $\sigma$ front-loads the schedule |
| T3 | First-period share is non-decreasing in $\lambda$ and $\sigma$, non-increasing in $\eta$ |
| T4 | Unconstrained QP — caps slack, $\alpha=0$, sweep inactive so $u=0$ — matches the closed form $y_t=Q\sinh(\omega(T+1-t))/\sinh(\omega T)$, $\cosh\omega=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$ in implementation units (section 5.2), equivalently $1+\lambda\sigma^2/2\eta$ in raw units (section 2.6) |
| T5 | Solution satisfies constraints and KKT conditions to tolerance |
| T6 | $T=3$ brute-force grid search agrees with the solver |
| T7 | Infeasibility is detected; the sweep is never cheaper than a feasible marginal slice: $\psi>\tfrac12S_t+2\eta_t\rho D_t+\bar\alpha_t-\bar\alpha_T$ (the risk term only strengthens it, since an earlier fill removes exposure) |
| T8 | **Causality:** perturbing every datum after arrival leaves the Static plan unchanged; perturbing data after period $k$ leaves MPC's $x_k$ unchanged |
| T9 | Simulator: $\varphi=1$ reproduces naive replay; Immediate cost is non-decreasing in $Q$; caps are never exceeded; the sweep is priced against depth net of $F_T+\text{fill}_T$, i.e. no resilience recovery on period $T$'s own fill (section 7.1) |
| T10 | The worked example of section 2.1 returns 5.5 bps (2.5 + 3.0) |
| T11 | Liquidity monotonicity: adding depth **at the price levels already in the book** never increases the optimal objective value. The qualifier is required: depth added at **new, worse** far levels raises $P^{\max}_a$ and therefore $\psi$, so with $u>0$ the unqualified statement is false — which is exactly the penalty-dominated regime of section 8.1 |
| T12 | Conservation: planned vs executed shares and the section 8.2 components sum to $\text{Spend}-QM_0$ |
| T13 | Scale invariance: multiplying all prices by $c>0$ and all volumes by $d>0$ leaves bps metrics, $\theta$ and participation schedules unchanged |
| T14 | AC-capped equals AC when caps are slack; TWAP$(T'=T)$ equals TWAP$(T)$ |

**Why T4 compares against a re-derived closed form.** The $\sinh$ trajectory with $\cosh\omega=1+\lambda\sigma^2/2\eta$ is the exact solution of *this* program, whose only curvature is the transient quadratic $\eta x^2$. Almgren–Chriss reaches the same functional form through a different term — its permanent impact — so its published $\omega$ relates $\lambda$ to a *linear* impact coefficient, not to $\eta_0/\bar D$. The formula is therefore derived here rather than cited, T4 asserts the implementation-unit form of section 5.2, and matching AC's published $\omega$ instead would be a different and wrong check.

**Experimental correctness.** Chronological splits; calibration quantities (including regime thresholds) fit on calibration only; $\lambda^\*$ and the comparator $\lambda$s chosen on validation only; one test run from a frozen config; every table carries config hash and git commit; figures regenerate from `python run_experiment.py`.

---

## 10. Roadmap

### 10.1 Tiers

- **Tier 1 (must ship):** audit and decision log, loader and recovered scales, cost model and E0, static QP, simulator, baselines 0–4 incl. 1b and 3b, E1, E3, E4, E5-min, **the interactive UI (section 1.1) with two guaranteed selectable optimisation models — Proposed-Static QP and Almgren–Chriss**, report.
- **Tier 2 (first to be cut):** MPC and 5a (the UI's third model), drift gate and rung 6, E2, E5, E6, E7.
- **Tier 3:** section 13.

**Why MPC being cuttable is not a compliance problem.** The OR guideline requires ≥2 user-selectable optimisation models in the UI (section 1.1). Those two are Proposed-Static (rung 4) and Almgren–Chriss (rungs 3/3b), both Tier 1, so the requirement holds even when every Tier 2 item is dropped; MPC is the optional third model and carries H3(b), not the compliance obligation.

### 10.2 Phase plan

Work is organised in **phases**, not calendar days. A phase is a stage with an entry gate, not a fixed duration; the phases below are ordered and numbered, and the word "day" is reserved in this document for a *trading day of the FI-2010 dataset* ("ten consecutive trading days", "test days 8–9", `day blocks`), never for a unit of project schedule.

| Phase | Focus | Gate |
|---|---|---|
| 1 | Audit A0–A8, scale recovery, splits frozen, MDE computed | G1 audit passed or resolution order logged; G2 `splits-frozen` |
| 2 | Features, cost model, E0 (**development variant on validation** — the confirmatory E0 is the single test run, section 8.4), simulator + T9/T10/T12/T13 | G3 loader tests; G4 simulator tests |
| 3 | Static QP, T1–T8, T11, T14, baselines 0–3b | G5 QP tests; G6 baselines run |
| 4 | Frontier on validation, matched-risk machinery, **UI skeleton** (dataset loader + statistics panels, section 1.1), **MVP gate:** Tier-1 pipeline runs end to end on validation | G7 matched-risk code tested; G8 MVP |
| 5 | If MVP gate passed: MPC and 5a on validation; else polish. **UI analysis menu** wired to both Tier-1 models and baselines. **Freeze:** numeric constants finalised in `configs/experiment.yaml`, committed, tag `config-frozen` | G9 MPC tests (if run); G10 `config-frozen` |
| 6 | **The single test run**, first and unattended, from the frozen config; then analysis, CIs, figures | G11 test run logged with hash and commit; G12 every claim has a CI and a mechanism |
| 7 | Report, slides, **UI finalisation and demonstration pass** (all five panels, section 1.1), repository tidy, reproducibility check, **buffer reserved for a failed reproduction check** | G13 report complete; G14 clean-checkout reproduction; G15 definition of done (section 14) |

**Stop-loss.** If the MVP gate is missed at the end of Phase 4, drop all Tier 2 items; the study answers Q1 only. The drift ablation is the first thing cut if Phase 5 slips. If the audit forces the resolution-order fallback, replan in Phase 1.

### 10.3 Phase-by-phase notes

Phase 1 must produce a written answer to every row of section 4.1 before any QP code exists. Phase 4's matched-risk machinery is tested on synthetic frontiers with a known crossing. Phase 6's test run is **single** and automated: results are read only after it completes.

### 10.4 Document discipline

Hypotheses, primary tests and the acceptance rule are **fixed** by this file, and nothing in it is revised on the basis of test results. Before the single test-set run they may be changed for two reasons only: the Phase-1 audit outcome (section 4.1), which supplies the empirical facts the design depends on; or a factual error or internal inconsistency, which is a property of the text rather than a result. After the test run they are frozen, and any later change is labelled *post hoc* in the report. Every change is recorded in `CHANGELOG.md`.

**Companion documents.** Two are present and are *not* sources of truth for this file: ``, the engineering scaffold (how the work is packaged, which is not restated here), and `DECISIONS.md`, a register of design alternatives that were considered and rejected, with the reason. Where either disagrees with this specification, this file governs and the companion is corrected. No superseded draft exists as a file or is relied on here.

### 10.5 Progress (as of 2026-10-04)

Recorded so this document alone tells the reader where the project stands. Phases and gates are section 10.2.

| Item | Status | Evidence |
|---|---|---|
| FE instructor sign-off (section 2.3) | **Complete** | Approval obtained before implementation |
| OR prior permission for the QP/optimal-execution topic (section 2.3) | **Complete** | Permission obtained; topic accepted |
| First Project Review (sections 2.4–2.5) | **Complete** | Presented and completed 2026-10-04; feedback incorporated |
| CR dataset/group registration (section 2.3) | **Complete** | FI-2010 registered on the CR sheet |
| Phase 1 — audit A0–A8 (section 4.1) | **Complete (G1)** | All checks PASS (A7 N/A — no fallback needed); report in `data/README.md` |
| Scale recovery (A1) | **Complete** | Decimal-precision DecPre, global $k=6$: price_euros = stored×100, vol_shares = stored×10^6 |
| Stock/day boundaries (A2) | **Complete** | Five stocks identified (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä); 10 days |
| Splits | **Frozen (G2)** | Tag `splits-frozen`; `configs/splits.yaml`; pooled test $N_{\text{eff}}=261$ |
| Phase-1 decision log | **Complete** | `docs/decision_log.md` |
| Audit figures | **Complete** | `results/figures/fig1`–`fig6` |
| MDE (section 8.3) | **Pending** | Computed in Phase 1 before confirmatory tests |
| Phase 2 — features, cost model, simulator | **Complete** | Cost model calibrated (`calibrate`), simulator checked and linted |
| Phase 3 — static QP, baselines | **In progress** | `src/optimize/qp_schedule.py` exists; `check-formulation` is SUCCESS; `src/baselines/` pending |
| Correctness test suite | **Green** | 72 tests pass (`pytest`); T1–T14 markers in place |
| Phase 4 — frontier, matched risk, UI skeleton, MVP gate (G7, G8) | **In progress** | Streamlit UI (`app.py`) exists and runs; frontier stubbed |
| Phase 5 — MPC, UI menu, `config-frozen` (G9, G10) | **Not started** | |
| Phase 6 — single test run (G11, G12) | **Not started** | No test-set result exists; `results/tables/` empty |
| Phase 7 — report, UI finalisation, reproduction (G13–G15) | **Not started** | |
| UI — five panels, two guaranteed models (section 1.1) | **In progress** | Tier 1; scheduled in Phases 4, 5, 7 |
| Known lint debt | **Resolved** | All previous ruff errors fixed; `ruff format --check` clean |

---

## 11. Risk Register

| ID | Risk | Mitigation |
|---|---|---|
| R1 | FI-2010 scale not recoverable (normalization variant or scope misread) | A1 discriminating tests first; resolution order of section 4.1; fallback only after confirming its availability |
| R2 | Cost model misfits (quadratic vs real walk) | E0 out-of-sample test; exact-book variant as robustness check |
| R3 | MPC or drift does not pay | Tier 2; drift gated; claim scoped to Q1 (section 1.2) |
| R4 | Solver issues | Small convex QP; T4–T6 against closed form and brute force |
| R5 | Backtest optimism | Footprint with $\varphi$ sensitivity; S1–S8 stated; sweep penalty sensitivity |
| R6 | Leakage | Chronological splits, calibration-only fitting, T8 causality test, labels never read |
| R7 | Scope creep | Tiering and stop-loss (section 10.2) |
| R8 | Hypotheses vacuous or degenerate | Each hypothesis is stated as a claim the data can refute; comparative statics are demoted to tests |
| R9 | Look-ahead in the sweep or drift timing | Arrival-frozen $\psi$; risk accumulated from $s=2$; T8 |
| R10 | Overlapping windows inflate evidence | Deterministic non-overlapping grid; A6 |
| R11 | Multiple comparisons | Single Holm family; rest exploratory |
| R12 | Matched-risk claims unreliable | Acceptance rule with paired CI; dominance reported separately |
| R13 | Tolerances tuned after seeing the test set | Numeric constants frozen in `configs/experiment.yaml` (`config-frozen`), set before the first test run |
| R14 | Stock/day boundaries unrecoverable | A2 fallback by price-level clustering; else stop at the resolution order |
| R15 | $N_{\text{eff}}$ vs feasibility $T\gtrsim\theta/f(\varphi)$ conflict | Decide explicitly in Phase 1 and record the binding constraint |
| R16 | Primary effect smaller than the MDE | MDE in Phase 1; declare tests descriptive in advance |
| R17 | Order sizes unrealistic for the venue ($\theta\ge1$ exceeds visible depth) | A8 euro translation; label penalty-dominated results |
| R18 | Cross-stock dependence overstates precision | Stock-wise results; day-cluster sensitivity; S7 |
| R19 | UI under-delivered (guideline non-compliance) | UI is Tier 1 (section 1.1); Phase 4 skeleton, Phase 5 menu wiring, Phase 7 finalisation; both Tier-1 models guaranteed regardless of MPC |

---

## 12. Deliverables and Repository

```text
ROTE/
├── README.md
├── run_experiment.py
├── app.py               # Streamlit UI (section 1.1)
├── pyproject.toml       # dependencies and tool config; not an installable package
├── configs/            # splits.yaml, experiment config
├── data/README.md      # audit report (section 4.1)
├── docs/decision_log.md
├── notebooks/rote_analysis.ipynb  # notebook UI (section 1.1)
├── src/
│   ├── data/           # loader, scale recovery, boundaries
│   ├── features/
│   ├── cost/           # walk-the-book, quadratic calibration
│   ├── optimize/       # QP, MPC
│   ├── baselines/
│   ├── simulator/
│   └── evaluation/     # metrics, matched_risk.py, bootstrap
├── tests/              # T1–T14
├── results/            # tables, figures (generated)
└── report/             # report and slides
```

Deliverables: the repository, the interactive UI (section 1.1), a report that states the tier completed and every limitation of section 7.3, a slide deck, and the decision log. Rules: configs are committed before results; every result file records config hash and commit; no notebook output is a source of record.

---

## 13. Stretch Extensions (Tier 3)

CVaR objective via Rockafellar–Uryasev; leave-one-stock-out generalisation (needs its own split mode); time-varying $\rho$; passive-order extension; transient-impact kernel; nonlinear (power-law) cost; sell-side full replication.

---

## 14. Definition of Done

All of: T1–T14 pass; Phase-1 audit report and decision log exist; `splits-frozen` and `config-frozen` tags precede the single test run; E0, E1, E3, E4, E5-min complete with CIs; every confirmatory result is reported with its Holm-adjusted outcome and every other result is labelled exploratory; the report names the tier reached and states which hypotheses lapsed; a clean checkout reproduces every table and figure with `python run_experiment.py`; **the interactive UI (Streamlit `app.py` and/or notebook) is complete with all five panels of section 1.1 — dataset loader, statistics on demand, optimisation menu exposing at least the two Tier-1 models (ROTE-Static QP and Almgren–Chriss), baseline comparison and results — and the FE analysis menu (Analyses A and B) runs end to end.**

---

## 15. References

- Almgren, R., & Chriss, N. (2000). Optimal execution of portfolio transactions. *Journal of Risk*, 3(2), 5–39.
- Bertsimas, D., & Lo, A. W. (1998). Optimal control of execution costs. *Journal of Financial Markets*, 1(1), 1–50.
- Bucci, F., Benzaquen, M., Lillo, F., & Bouchaud, J.-P. (2019). Crossover from linear to square-root market impact. *Physical Review Letters*, 122, 108302.
- Cartea, Á., Jaimungal, S., & Penalva, J. (2015). *Algorithmic and High-Frequency Trading*. Cambridge University Press.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88.
- Gatheral, J. (2010). No-dynamic-arbitrage and market impact. *Quantitative Finance*, 10(7), 749–759.
- Huberman, G., & Stanzl, W. (2004). Price manipulation and quasi-arbitrage. *Econometrica*, 72(4), 1247–1275.
- Kercheval, A. N., & Zhang, Y. (2015). Modelling high-frequency limit order book dynamics with support vector machines. *Quantitative Finance*, 15(8), 1315–1329.
- Lorenz, J., & Almgren, R. (2011). Mean–variance optimal adaptive execution. *Applied Mathematical Finance*, 18(5), 395–422.
- Ntakaris, A., Magris, M., Kanniainen, J., Gabbouj, M., & Iosifidis, A. (2018). Benchmark dataset for mid-price forecasting of limit order book data with machine learning methods. *Journal of Forecasting*, 37(8), 852–866.
- Obizhaeva, A., & Wang, J. (2013). Optimal trading strategy and supply/demand dynamics. *Journal of Financial Markets*, 16(1), 1–32.
- Perold, A. F. (1988). The implementation shortfall: Paper versus reality. *Journal of Portfolio Management*, 14(3), 4–9.
- Rockafellar, R. T., & Uryasev, S. (2000). Optimization of conditional value-at-risk. *Journal of Risk*, 2(3), 21–41.
- Tóth, B., Lempérière, Y., Deremble, C., de Lataillade, J., Kockelkoren, J., & Bouchaud, J.-P. (2011). Anomalous price impact and the critical nature of liquidity in financial markets. *Physical Review X*, 1, 021006.

**Verification note.** The FI-2010 structural statements tagged [S] were checked against the text of Ntakaris et al. (the arXiv version), which also lists Kercheval–Zhang with the volume and pages above, and then re-checked against the paper's full text **and** the dataset's own distribution documentation. They confirm: 394,337 representations from ~4 million events; Nasdaq Nordic ITCH, Helsinki, five stocks, 1–14 June 2010 (10 trading days); the 3-hour EET shift with the trading day at 7:00–15:25 in the data's clock; the retained window **10:30–18:00 local** (the paper's "we retain exclusively the events occurring between 10:30 and 18:00"), excluding the pre- and post-opening auction periods; prices ×10,000 with a 1-cent tick in euros; 144 features with rows 145–149 as the five labels; Eq. (5)–(7) verbatim; and the file-naming convention, `Test_Dst_NoAuction_ZScore_CF_9.txt` being a real filename among several one-day test files. Two facts the paper does not state — the 149-column total and "every file holds all five stocks" — are stated in the distribution documentation and are tagged accordingly in section 4.1. The remaining reference entries were **not** re-opened against publisher records, with one exception (Rockafellar–Uryasev, corrected to 21–41). Items tagged [C] are unverified until the Phase-1 audit.

*End of specification.*
