# ROTE — Risk-Aware Optimal Trade Execution Using High-Frequency Limit Order Book Data

*A cost–risk optimal-execution study on FI-2010: convex optimisation models calibrated from limit order book data, benchmarked through historical LOB simulation, delivered as an interactive strategy-selection tool*

| Field | Value |
|---|---|
| **Project name** | **ROTE** — **R**isk-Aware **O**ptimal **T**rade **E**xecution |
| **Description** | A quantitative trade-execution framework that balances market impact, execution cost and inventory risk, using high-frequency limit order book (LOB) data |
| **Type** | Financial Engineering × Operations Research |
| **Approach and schedule** | **`ROADMAP.md` governs them** — the model menu (M1–M4), the interface contract, the eight-week plan, the four-owner split, the UI panel flow, the tech stack and the compression rules |
| **Status** | **Final** — the authoritative specification of *what* is built and *how it is judged*. Its hypotheses, primary tests and acceptance rule (section 1.5) are fixed and are not revised on the basis of test results |
| **Progress (2026-10-05)** | **Mid-migration to the ROADMAP architecture.** Review 1 passed, sign-offs obtained. The previous pipeline (`src/data`, `src/cost`, `src/optimize`, `src/simulator`, `run_experiment.py`) was removed in favour of the ROADMAP module layout (`src/loader`, `src/impact`, `src/models/m1_ac…m4_ahp`, `src/sim`, `src/stats`, `src/benchmarks`, `src/utils/contracts.py`), which exists today as skeleton stubs. The Phase-1 audit facts and frozen splits are recorded in `configs/experiment.yaml` and `configs/splits.yaml` and remain valid; the audit report and figures are **not** on disk and must be regenerated. Detail in section 11.5 |
| **Guideline compliance** | FE + OR course guidelines: public dataset (FI-2010); Python tool; UI with dataset loading, statistics on demand and ≥2 user-selectable optimisation models (section 1.3); ≥2 distinct financial analyses from a menu (section 1.3); Tools & Technologies (section 2.6); First Review Alignment (section 2.4); course-topic approval obtained (section 2.3) |
| **Evidence tags** | **[S]** stated in the dataset paper (Ntakaris et al., 2018); **[C]** confirmed by the Phase-1 audit run on the real dataset; **[K]** a design convention, not a fact |

> **Authority split.** `ROADMAP.md` fixes the approach, the deliverable checklist and the schedule; this file specifies that approach and governs the scientific content — hypotheses, correctness standards, evaluation protocol, acceptance rule and any number that appears in a result. Where the two differ in detail, `ROADMAP.md` owns the *shape* of the answer (which models exist, who owns them, when they are due) and this file owns the *validity* of the answer (what counts as evidence). Sections 1.4, 1.5, 4, 5, 9 and 10 are not revised on the basis of test results.

**Contents.** 1 Goal, questions, hypotheses · 2 Problem statement, course alignment, tools · 3 Notation · 4 Data: FI-2010 · 5 Cost of execution and the impact model · 6 Models (the menu) · 7 Baselines and the interface contract · 8 Execution simulator · 9 Correctness standards · 10 Evaluation protocol · 11 Delivery plan · 12 Presentation and viva · 13 Repository and reproducibility · 14 Risk register · 15 Stretch extensions · 16 Definition of done · 17 References

> **Project context:** This work satisfies FE and OR guidelines (group project) by implementing an interactive UI/menu (section 1.3) in addition to dataset analysis, statistics, and ≥2 optimisation models.

---

## 1. Goal, research questions, hypotheses and definition of done

### 1.1 What "done" means

A trader must liquidate (or buy) a large parent order. Trading fast pays market impact because the order walks the book. Trading slowly leaves price risk. ROTE is a Streamlit tool on FI-2010 that loads and cleans LOB data, shows liquidity statistics on demand, runs optimisation models that output execution schedules, benchmarks them, and helps the user choose a strategy for their risk preference.

**One build, two grading lenses** (ROADMAP.md §1):

| Lens | What the instructors look for | ROTE's answer |
|---|---|---|
| FE | Real data cleaned; descriptive stats; ≥2 analyses from a menu; interpretation; a genuine decision; financial theory as backbone | Mean–variance trade-off and efficient frontier of cost vs risk; risk aversion as utility; Decision tab |
| OR | Dataset loaded in UI; stats on demand; ≥2 optimisation models; formulations; sensitivity; results interpretation; viva on formulations | Convex QP (M1/ROTE-Static), LP with shadow prices (M2), fixed-charge IP (M3), AHP (M4) |
| Both | Review-1 feedback incorporated; every member presents and can answer on everything | Feedback log (`docs/feedback_log.md`); rotation of presenters and quiz sessions (section 12) |

The deliverable checklist in section 16 is the roadmap's definition of done, restated with the gate names this document uses.

### 1.2 Questions

The umbrella question is:

> **How does market-microstructure information change the optimal execution policy under a cost–risk trade-off?**

It is answered in two tiers, and the claim made is only as wide as the tier that was completed:

- **Q1 (core).** Does *arrival-state* LOB information — depth-scaled impact and depth-based participation limits, measured at the moment the order arrives — improve a risk-aware schedule relative to state-blind references, at matched risk?
- **Q2 (extension).** Does *re-solving as the book is progressively revealed* add value beyond Q1?

The optimiser is the instrument used to measure this, and the model menu of section 6 is the roadmap's answer to "which instruments": M1 is the state-blind reference, M2 makes the book the decision space, and **ROTE-Static is M1 and M2 linked** (quadratic depth-scaled impact plus the risk term plus the in-QP participation cap), which is the core deliverable. M3 and M4 complete the OR coverage and close the decision loop.

```text
                      RESEARCH QUESTION
                             │
                             ▼
                Cost–Risk Optimal Execution
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
           Financial Model          OR Model
        (LOB cost and risk)        (QP / LP / IP / AHP)
                  │                     │
                  └──────────┬──────────┘
                             ▼
                     Execution Policy
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
              M1 (AC)              M2 (LOB LP)        ← state-blind vs book-aware
                  │                     │
                  └──────────┬──────────┘
                             ▼
                  ROTE-Static (M1 + M2 linked)          ← Q1, core
                             │
                             ▼
                  Receding-horizon re-solve            ← Q2, extension
                             │
                             ▼
                  Walk-the-book Backtest
                             │
                             ▼
                      Statistical Study
```

### 1.3 User interface (UI) / interactive analysis tool

A user interface is **mandatory under both guidelines** (FE: run ≥2 distinct financial analyses from a menu; OR: load the dataset, generate statistics on demand, and perform ≥2 user-selectable optimisation models), so it is a **Tier 1 deliverable**, not an optional extra. The same capability is provided twice — a Streamlit web app (`app.py`) and a Jupyter/Colab notebook (`notebooks/rote_analysis.ipynb`) with widgets — and both are thin wrappers over the existing `src/` modules (no logic duplication). The UI follows the roadmap's five-panel flow **Data → Statistics → Optimiser → Compare → Decision**:

1. **Dataset Loader.** Upload or select the FI-2010 file (path defaulting to `$ROTE_DATA_ROOT`); display dataset dimensions (rows × columns), detected stocks and days (A2), the recovered normalisation/scale (A1), and the data-quality/audit status (A0–A4) read from the Phase-1 audit report.
2. **Descriptive Statistics (on demand).** Spread, bid/ask depth, mid-price, order-book imbalance (OBI), volatility and liquidity statistics — mean, std, min, max and depth percentiles — plus the relevant plots on demand, all computed by the audit/feature pipeline. Shown as *findings*, not raw charts (roadmap §6).
3. **Optimiser / Analysis Menu.** The user selects the optimisation model and its parameters ($\theta$ or $Q$, $T$, $\lambda$, $\rho$), runs it on a chosen window, and sees the optimal execution schedule together with expected cost, realised risk, implementation shortfall and completion share. **All four roadmap models are selectable, and both Tier-1 models are guaranteed:**
   - **M1 — Almgren–Chriss mean–variance schedule** (roadmap §3): closed form, risk aversion $\lambda$; the state-blind reference, same order/horizon/risk framework (section 6, rungs 3/3b).
   - **M2 — LOB-aware slice allocation**: LP with depth and participation limits, shadow prices reported (section 6, rung 4b).
   - **ROTE-Static** — M1 and M2 linked: arrival-state convex QP with quadratic depth-scaled impact, risk penalty, participation constraints and terminal sweep (section 6.2, rung 4b). This is Model 1 of the OR guideline.
   - **M3 — Fixed-charge child-order scheduling** (integer program) and **M4 — AHP strategy selection** (sections 6.5–6.6), the roadmap's full OR coverage.
   Because M1/ROTE-Static and M2 are all Tier 1, the UI satisfies the two-model requirement **even if M3 and M4 are cut under the compression rules of section 11.4**.
4. **Compare / Baseline.** Selectable registered baselines for side-by-side runs on a common simulator: Immediate, TWAP$(T)$, TWAP$(T')$, Depth-Proportional, Almgren–Chriss, AC-capped (section 7).
5. **Decision / Results.** Execution schedule plot, cost decomposition (section 10.2), risk–cost frontier (E3), the comparison table against the selected baseline, and M4's profile ranking — the genuine decision the FE guideline asks for.

**FE analyses menu (≥2 distinct financial analyses, as the FE guideline requires).** A and B are the two required analyses and C is a third:

- **Analysis A — Optimal Execution.** Given an order of size $Q$, determine the execution schedule that minimises expected execution cost plus inventory risk under LOB-derived liquidity constraints (the core QP / M2 LP).
- **Analysis B — Execution Strategy Comparison.** Compare the selected optimal strategy against TWAP, Almgren–Chriss and Depth-Proportional using implementation shortfall, realised risk, completion and cost decomposition.
- **Analysis C — Risk–Cost Frontier.** Evaluate how the optimal execution schedule and cost change as risk aversion $\lambda$ varies (E3), read as a mean–variance efficient frontier.

The CLI remains the reproducibility path (section 13); the UI is the **user-facing** path required by the guidelines, and both call the same code.

### 1.4 Hypotheses (falsifiable, fixed before the test set is touched)

| ID | Hypothesis | Tier | Evidence that would support it |
|---|---|---|---|
| H1 | **Risk-aware optimisation vs. the naive way of cutting risk.** At matched risk, ROTE-Static has lower mean implementation shortfall (IS) than **TWAP over a shortened horizon** $T'<T$ (trade evenly over the first $T'$ periods, then stop). Primary comparator: $T'=\lceil T/2\rceil$. | 1 | Matched-risk test (section 1.5): paired block-bootstrap 95% CI of the IS difference excludes 0 on the test set. |
| H2 | **The depth-scaled cost model predicts book-walk cost out of sample better than a constant-impact model.** | 1 | E0 (section 10.4): on test-split snapshots at pre-registered probe sizes, RMSE (bps) of $\tfrac12 S x+\eta_0 x^2/D^a_t$ below that of $\tfrac12 S x+c\,x$ (a constant slope $c$ fitted on the same calibration data); paired block-bootstrap CI of the RMSE difference excludes 0. |
| H3(a) | **Arrival-state information adds value beyond a state-blind risk-aware schedule.** ROTE-Static beats **capped** Almgren–Chriss (rung 3b, section 7) at matched risk. | 1 | Frontier comparison at three pre-registered risk levels (section 1.5); CI of the IS difference excludes 0. |
| H3(b) | **Progressive book revelation adds value beyond arrival state alone (Q2).** Re-solving with updated book state beats ROTE-Static at matched risk. | 2 | Same frontier machinery at the Tier-2 rung; if Tier 2 is cut, H3(b) lapses and the study answers Q1 only. |

**What is *not* a hypothesis.** Comparative statics — schedules front-load more as risk aversion $\lambda$ or volatility $\sigma$ rises, and the first-period share falls as $\eta$ rises — are mathematical properties of the program. They are **model-verification tests** (T2, T3, T11), not empirical findings. The depth-response of ROTE-Static (it trades more when the currently observed depth is high) is a **descriptive analysis** inside E6, and it needs **two** regressions, because the two strategies have different nulls. *Re-solved:* regress planned shares $\xi_{t,k}$ net of $\bar\xi_{\cdot,k}/\bar D$ across $k$ within windows; the expected slope is positive. *Static:* its plan is frozen at arrival, so the correct null is **no within-window variation** — regress the planned share on the within-window demeaned depth (equivalently, test constancy of the planned share in $k$), and expect slope zero there. Reported separately, Static's *cross-window* level of trading does vary with arrival depth, so a regression of the period-1 share on $D^{a,\text{arr}}/\bar D$ is **not** expected to have slope zero and is not a test of anything; it is shown only to document the arrival-state scaling H3(a) is about. All depth measures used as regressors are gross ($D^a$, $D^{a,\text{arr}}$) or net ($D^{a,\text{net}}$) as labelled; $\bar D$ is always the calibration-set median **gross** ask depth, so a net regressor is scaled by a gross constant and the slope sign is unaffected but its magnitude is not comparable across the two regressions.

**Structure of the claim.** ROTE-Static differs from capped Almgren–Chriss only through (i) $\eta$ evaluated at *arrival* depth rather than median depth, (ii) the arrival-frozen participation cap inside the optimization, and (iii) the arrival-frozen sweep price. It does **not** use any within-horizon variation of the book (section 6.3) and its schedule is **spread-blind except through the sweep**. Precisely: $u$ is a decision, so $\tfrac12S\sum_t x_t=\tfrac12S(Q-u)$ is *not* constant across feasible plans, and substituting $u=y_{T+1}$ in section 6.2 leaves the objective $\tfrac12SQ+[\text{in-horizon terms}]+u(\psi+\bar\alpha_T-\tfrac12S)$. The spread therefore cannot move the *shape* of the in-horizon schedule for any fixed $u$, and cannot move the minimizer at all wherever $u=0$; it moves the chosen sweep share, and hence the plan, wherever the sweep is cheaper than or forced over a capped slice — precisely the penalty-dominated cells of section 10.1 ($\theta=5$ at $\varphi=0.5$; every $\theta\ge1$ at $\varphi=0$). H3(a) therefore tests *arrival-state scaling of the cost coefficient plus the in-QP cap*, nothing more. Time variation is not in scope.

A null result on H1, H3(a) or H3(b) is acceptable and publishable; the study then characterizes *when* state-awareness matters. H1 is partly a sanity check, but the supporting statement is a **within-model** one and is labelled as such: under Gaussian independent increments with a quadratic cost and no binding caps, the mean–variance frontier point at any attainable risk level minimises mean cost at that level, and TWAP$(T')$ is not that point for any $\lambda$, so the frontier strictly dominates it — provided caps do not truncate the frontier at TWAP$(T')$'s risk. Outside those conditions H1 is a genuine empirical question, not a theorem. H2 is a model-fit result. **H3 carries the research claim (H3(a) focused).** If H3(b) lapses, the study answers Q1 only; this is stated in the report's abstract rather than discovered at the end.

### 1.5 What "matched risk" means

Realised risk of a strategy in a cell is the **standard deviation of IS (bps) across that cell's test windows**. **Cells are indexed by the participation level $\theta$, pooled over regimes and stocks, at the base resilience $\varphi=0.5$**, so each $\theta$-cell holds all $N_{\text{eff}}\ge100$ test windows (A6). **The one confirmatory cell is fixed in section 10.1: $\theta=1$, $\varphi=0.5$.** The other sizes are reported, and are outside the Holm family. The $3\times3$ volatility × liquidity cells (about $N_{\text{eff}}/9$ windows each) are descriptive and are not used for confirmatory matched-risk claims unless a cell holds at least 30 independent windows. Strategies with a risk parameter (Almgren–Chriss, ROTE-Static) trace a frontier as $\lambda$ varies; TWAP$(T')$ traces a discrete frontier as $T'$ varies; Immediate, TWAP$(T)$ and Depth-Proportional are single points.

- **Matched risk = same position on the risk axis, not the same $\lambda$.** Equal $\lambda$ is an equal *preference*, not equal realised risk, so it is never called matched risk.
- **Why the comparator for H1 is TWAP$(T')$.** At $\lambda=0$ with constant parameters and no binding caps the program *is* TWAP$(T)$ (T1), and TWAP$(T)$ is the minimum-expected-cost schedule when drift is zero. A risk-matched comparison against TWAP$(T)$ itself would therefore be an identity up to cap effects. The honest naive way to cut risk is to finish sooner.
- **Protocol for point comparators (H1).** On the validation split, take the comparator's realised risk, and choose $\lambda^\*$ so that ROTE-Static's realised risk equals it, interpolating along a **monotone (isotonic) fit** of the validation frontier. Freeze $\lambda^\*$. On the test split report the paired IS difference with a moving-block bootstrap CI (section 10.3) **and** the realised-risk gap with its own paired bootstrap CI.
- **Acceptance rule (replaces a fixed numeric tolerance).** (i) If the test risk-gap CI contains 0, the strategies are *matched* and the IS difference is the result. (ii) If the CI excludes 0 but ROTE-Static has both lower risk **and** lower mean IS, report **dominance** as such; it is stronger than matching. (iii) Otherwise the comparison is **not identifiable for that cell**: report the nearest frontier point and the realised-risk gap, and state that the comparison could not be formed. **No test-set tuning is performed to force a match.** Numeric constants — bootstrap block length, replications, the risk levels below — live in `configs/experiment.yaml`, not in this document (R13).
- **Non-identifiability on the validation frontier.** If the validation frontier does not reach the comparator's risk, the same case (iii) applies.
- **Protocol for frontier comparators (H3).** Compare mean IS at three pre-registered risk levels (validation-realised risk of the ROTE-Static strategy at low, medium and high $\lambda$), freezing the comparator's $\lambda$ at each level from its isotonic validation frontier. The same acceptance rule applies at each level.
- **The risk–cost frontier figure (E3)** is the visual statement of all of this, and is the roadmap's "efficient frontier of cost vs risk" read as a finding.

**What exists at the end.** (1) A clean loader and on-demand statistics for any stock and day; (2) an LOB-native execution-cost model calibrated on FI-2010 with an out-of-sample test (H2); (3) four selectable optimisation models behind one contract — M1, M2, M3, M4 plus the linked ROTE-Static QP; (4) a walk-the-book simulator with a resilience parameter; (5) a leakage-safe evaluation against a baseline ladder with matched-risk statistics; (6) an interactive UI with dataset loading, statistics on demand and ≥2 selectable optimisation models; (7) a reproducible repository where `python run_experiment.py` regenerates every table and figure.

---

## 2. Problem statement, course alignment and tools

### 2.1 The trade-off

An investor must buy $Q$ shares. Crossing the book at once consumes liquidity and pays a premium. Slicing the order lowers that premium but leaves unexecuted inventory exposed to price moves.

**Worked example.** Best bid $99.95$; asks $100.00\times800$, $100.05\times1{,}200$, $100.10\times2{,}500$. Mid $=99.975$.

Buying $2{,}000$ shares sweeps $800@100.00$ and $1{,}200@100.05$:

$$\text{cost}=80{,}000+120{,}060=200{,}060,\qquad \bar P=100.03.$$

Shortfall versus mid $=0.055$ per share $=5.5$ bps, which splits into half-spread $0.025$ (2.5 bps) plus book-walk premium $0.030$ (3.0 bps). This is the unit test for the cost function (T10) and the project's primary FE illustration: the cost is the *mechanism* of the book, not a curve fitted to it.

The toy book shows only $4{,}500$ shares. A $10{,}000$-share immediate order exceeds visible depth, so the project needs an explicit **completion rule** (section 6.2).

### 2.2 Why this is both FE and OR

- **FE** supplies the market model: mid-price, spread, depth, imbalance, volatility, walk-the-book execution cost, implementation shortfall. The implementation provides an interactive UI/menu for running financial analyses.
- **OR** supplies the decision models: choose the schedule to minimize expected cost plus a risk penalty subject to completion, non-negativity and liquidity constraints, and read the shadow prices (M2, section 6.4); add fixed costs and lot sizes and the problem becomes an integer program (M3); select a strategy for a trader profile with a consistency-checked weighting (M4). The UI allows users to select among multiple optimisation models on demand.

The deliverable is a market model and optimisation models that are genuinely coupled, not a heuristic such as "trade less when volatility is high." The interactive interface satisfies both guideline requirements (dataset loading, statistics on demand, and ≥2 selectable models/analyses).

### 2.3 Course alignment and approval — **complete**

**Course alignment:** The project applies optimization to financial execution using convex quadratic, linear and integer programming formulations. Optimal execution / convex QP is not explicitly listed among the supplied OR course topics (LP, transportation, assignment, network, integer, NLP, portfolio, goal programming, AHP), and optimal trade execution is outside the named FE topics — so instructor approval was required before implementation. **Status (2026-10-04): both approvals obtained.** The FE instructor sign-off is in place, the OR prior permission for this topic is in place, and the **First Project Review has been presented and completed**, with the methodology, tools, dataset and research questions of sections 2.4–2.6 accepted.

**Administrative (FE guideline):** a group of four members registers the project title and the dataset (FI-2010, public source) with the course representative on the CR's consolidated sheet, per the first-come-first-served dataset assignment. **Status: registration complete.** Registration is administrative and does not change this specification.

### 2.4 First Review Alignment

This proposal maps directly to the first review requirements:

1. **Significance** (sections 1, 2.1, 14) — Addresses the liquidity–risk trade-off in large-order execution and its relevance.
2. **Methodology** (sections 5–10) — Formal problem formulation, optimisation, baselines, simulation, and evaluation protocol.
3. **Tools and Technologies** (section 2.6) — Python ecosystem, optimisation, and UI tools.
4. **Dataset and Variables** (sections 3–4) — FI-2010 LOB data, preprocessing, variables, audit; shown live through the UI dataset-loader panel (section 1.3).
5. **Research/Business Questions** (sections 1, 10) — Q1/Q2, H1–H3b, with how optimisation answers them.

### 2.5 Review-1 feedback

Review-1 feedback and its disposition live in `docs/feedback_log.md` (roadmap §8), one row per comment: what was asked, what changed, in which commit. The absence of a row is itself a finding, and section 16 requires the log to be complete before the final presentation.

### 2.6 Tools and Technologies

The roadmap's stack (§10) is the committed one; the column on the right records the specific role in this project.

| Category | Tool/Library | Purpose |
|---|---|---|
| Programming | Python (≥3.11) | Core implementation language |
| Data processing | pandas, NumPy, pyarrow | Array operations, frame handling, columnar caching |
| Optimisation | CVXPY with OSQP (QP), `scipy.optimize` (LP fallback) | M1/ROTE-Static scheduling; M2 in the convex form |
| Linear & integer programming | OR-Tools or PuLP (one, chosen in Week 1) | M2's exact LP with shadow prices; M3's fixed-charge MIP |
| AHP / scoring | NumPy (in-house) | M4 pairwise matrices, eigenvector weights, consistency ratio |
| Visualisation | Plotly (frontier, schedule, book heatmap), matplotlib (static report figures) | Interactive tabs and printable figures |
| Interactive UI | Streamlit (`app.py`) | Web dashboard: Data → Statistics → Optimiser → Compare → Decision |
| Interactive notebooks | Jupyter/Colab (`notebooks/rote_analysis.ipynb`) | Alternative UI with widgets for easy demonstration |
| Statistics | in-house moving-block bootstrap, statsmodels (optional) | Paired CIs, Holm family, MDE (section 10.3) |
| Machine learning (stretch) | scikit-learn; LightGBM or PyTorch only in §15 | Drift-term ablation and the stretch model; labels never read in Tier 1 |
| Testing | pytest | Unit/integration testing, T1–T17 correctness gates (section 9) |
| Environment & CI | uv (dependency management), pytest as CI-lite, GitHub | Reproducible environments; branch-per-feature with one reviewer |
| Workflow | git, `requirements.txt`-equivalent lock via `uv` | Pinned environment for the demo machine (roadmap §9) |

Two roadmap stack entries are explicitly **not** used: `seaborn` (declared but never imported) and any volume-profile/`VWAP` construction — FI-2010 rows lack timestamps and volume profiles, so a historical volume curve cannot be built, and the report says so.

### 2.7 Positioning

The classical Almgren–Chriss (2000) programme minimises expected cost plus a variance penalty and yields the closed-form inventory trajectory $y_t=Q\,\sinh(\omega(T+1-t))/\sinh(\omega T)$ with $\cosh\omega=1+\lambda\sigma^2/2\eta$ in the discrete form used here. That form solves the program of section 6.2 as specified, where the curvature is transient quadratic impact; section 9 T4 says why it is re-derived rather than quoted. Those symbols are the paper's own, i.e. raw units; expressed in the implementation units in which this project actually solves the program (section 5.3) the same trajectory is $\cosh\omega=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$, and $\omega$ is the **single** urgency parameter used throughout this document (section 5.3 relates it to the square-root form; section 9 T4 tests against it). It is the reference this project is measured against (M1), and four of its assumptions are exactly what a recorded book violates:

1. **Homogeneity.** Impact and volatility are constants; displayed depth fluctuates substantially within a session and volatility clusters.
2. **No microstructure state.** The model is invariant to depth, spread and imbalance — the variables that the microstructure literature links to short-horizon price pressure and liquidity cost. (In this project depth enters the schedule; the spread enters only through the chosen sweep share, section 1.4.)
3. **Open-loop scheduling.** A schedule computed once at arrival cannot use what the book reveals afterwards: depth and volatility drift away from their arrival values, so the pre-computed schedule goes stale. Re-solving as the book state updates is the case for Q2, and why it is an extension rather than the core. Strategies that respond to realised *price* moves are a separate literature (Lorenz and Almgren, 2011) and are out of scope.
4. **Unconstrained trade sizes.** The classical solution ignores that displayed depth bounds what can physically be executed in a period. Here depth enters as a **constraint**, not only as a cost (M2).

| Axis | Almgren–Chriss (M1) | ML-only LOB papers | This work (ROTE-Static) |
|---|---|---|---|
| Cost model | constant impact | not the object of study | measured, walk-the-book |
| Liquidity | ignored | a feature | a feature **and** a hard constraint |
| Decision rule | closed form | point forecast | convex QP; LP shadow prices (M2) |
| ML role | none | end-to-end | ablation on the drift term only (section 6.7) |
| Claim | analytic | predictive accuracy | cost–risk improvement, falsifiable |

Explicitly **not** the claim: "a neural network was applied to FI-2010". The optimisation problems are the contribution; machine learning is admitted only where it measurably improves a coefficient, and is removed if it does not.

---

## 3. Notation

| Symbol | Meaning |
|---|---|
| $Q$, $T$ | Parent order size (buy); number of execution periods |
| $m$ | Rows of event time per execution period (A3); a period spans $10m$ events |
| $T'$ | Shortened horizon of the TWAP$(T')$ comparator ($T'\le T$) |
| $x_t\ge0$ | Shares *planned* for period $t$ (decision variable in the QP) |
| $\text{fill}_t$ | Shares actually filled in period $t$ by the simulator (section 8.1) |
| $y_t$ | Inventory remaining **before** period $t$; $y_1=Q$, $y_{t+1}=y_t-x_t$ in the QP and $y_t-\text{fill}_t$ in the simulator. Hence $y_s=Q-\sum_{t<s}x_t=\sum_{t\ge s}x_t+u$ |
| $u\ge0$ | Residual inventory sent to the forced terminal sweep. In the QP, $u=y_{T+1}$ by construction (section 6.2); after simulation the realised residual is $u^{\text{real}}=y_{T+1}$, which equals $u$ only if no period came up short (section 8.1) |
| $C_{\text{sweep}}(u)$ | QP cost of the sweep, expressed (like every other term) as shortfall versus the arrival mid: $(\psi+\bar\alpha_T)\,u$ with $\psi=P^{\max}_{a,\text{arr}}(1+\pi)-M_0$ |
| $C^{\text{ex}}_{\text{sweep}}(u^{\text{real}})$ | **Cash paid** at the terminal sweep, including the penalty-priced shares beyond visible depth (section 8.1); the quantity that enters $\text{Spend}$ in section 10.2. Distinct from $C_{\text{sweep}}$, which is this cash less $M_0u$, i.e. the same cash expressed as shortfall versus the arrival mid |
| $P^a_t,\;P^b_t$ | Best ask, best bid at the snapshot of period $t$ |
| $p^a_{t,i},\;v^a_{t,i}$ | Ask price and volume at level $i=1..L$ ($L=10$ in FI-2010) |
| $M_t=\tfrac12(P^a_t+P^b_t)$ | Mid-price; $M_0$ is the **arrival mid** (benchmark); period 1 is the arrival snapshot, $M_1=M_0$ |
| $S_t=P^a_t-P^b_t$ | **Full** spread ($P^a_t-P^b_t$), not the half-spread; the half-spread that enters the cost model is $\tfrac12S_t$ |
| $D^a_t=\sum_{i=1}^{L}v^a_{t,i}$, $D^b_t$ | Total ask / bid depth (gross) |
| $D^{a,\text{net}}_t=\max(0,D^a_t-F_t)$ | Ask depth available to us (section 6.2) |
| $\mathrm{OBI}_t=\dfrac{D^b_t-D^a_t}{D^b_t+D^a_t}\in[-1,1]$ | Depth imbalance (**not** inventory) |
| $\sigma_t$ | Volatility of mid-price changes **per period** ($m$ rows) |
| $\eta_t$ | Impact coefficient (price per share per share); $\eta_t=\eta_0/D^a_t$ |
| $\tilde\eta_0=\eta_0/M_0$, $\tilde\sigma_t=\sigma_t/M_0$ | Dimensionless, **per-stock** versions used to solve the program (section 5.3, "Implementation units") |
| $\omega$ | Almgren–Chriss urgency parameter, the document's single symbol for it: $\cosh\omega=1+\lambda\sigma^2/(2\eta)$ in raw units (section 2.7), $=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$ in implementation units (section 5.3). The square-root form $\kappa=\sqrt{\lambda\tilde\sigma^2/(\tilde\eta_0\theta)}=\sqrt{2(\cosh\omega-1)}$ is the same quantity (section 5.3) |
| $\alpha_t,\ \bar\alpha_t=\sum_{s=2}^{t}\alpha_s$ | Expected mid-price drift per period; cumulative drift from the arrival mid. The first drift that can act is in period 2, since $M_1=M_0$ |
| $\hat\alpha_{\text{arr}},\ \hat\sigma_{\text{arr}}$ | **Frozen arrival-time estimates** of $\alpha_t$ and $\sigma_t$, held constant over the horizon in ROTE-Static (section 6.3) |
| $P^{\max}_a$ | Worst (deepest) visible ask price; charged for penalty-priced shares |
| $\pi$ | Sweep penalty as a fraction of price (default $0.005=50$ bps) |
| $\theta=Q/\bar D$ | Participation level of the parent order; $\bar D$ = per-stock calibration-set median ask depth (section 10.1) |
| $\lambda$ | Risk aversion. Two forms, related by $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ (or $=\lambda_{\text{raw}}QM_0/10^4$ if the common $10^4$ is carried inside the tildes instead of suppressed, section 5.3): $\lambda_{\text{raw}}$ is the coefficient of section 6.2 as written, in units of **one per unit of currency**, $1/(\text{price}\cdot\text{shares})$ — that is what makes $\lambda\sigma^2y^2$ a currency sum, and the same unit is what makes $\lambda_{\text{imp}}$ dimensionless. Labelling it $1/\text{price}$ is the error of one share-count, since $y^2$ is then not $y$; from section 5.3 on, $\lambda$ means the dimensionless $\lambda_{\text{imp}}$, and only the ratio $\lambda\tilde\sigma^2/(\tilde\eta_0\theta)$ affects the solution |
| $\rho$ | Participation cap: the per-period ceiling $x_t\le\rho D^{a,\text{net}}_t$ (section 6.2), and the simulator's per-period fill ceiling. **Notation note:** ROADMAP.md §3 writes this limit as $\phi\cdot\text{volume}_t$; here $\phi$ is reserved for resilience (below) and the participation factor is always $\rho$ |
| $\varphi$ | Simulator resilience: the fraction of the footprint recovered per period (section 8.2) |
| $\tilde D_t$ | Trailing median of **gross** ask depth (causal), used only by the Depth-Proportional rung (section 7) |
| $c$ | The constant-impact slope fitted on the calibration data as H2's comparator (sections 1.4, 10.4 E0) |
| $B_0$ | Burn-in rows before the first window on the deterministic grid (A6, section 10.1); supplies trailing volatility estimates |
| $F_t$ | Footprint: our own unrecovered consumption, removed from the ask side before period $t$ (section 8.2) |
| $N_{\text{eff}}$, $b$ | Number of non-overlapping test windows (A6); bootstrap block length in windows (section 10.3) |

---

## 4. Data: FI-2010

### 4.1 Phase-1 data audit (the first deliverable; a gate, not an assumption)

**No optimisation code is written before A0–A2 are answered.** The walk-the-book cost is only meaningful if prices and volumes are on real scales. The open-access FI-2010 release is *normalized in order to prevent reconstruction of the original Nasdaq data* [S], so whether a mid-price level is recoverable is the first thing to establish. An unexamined file makes the calibration of section 5 regress on quantities with arbitrary units, and every downstream number inherits the distortion. ROADMAP.md §2 states the same risk from the other side ("if not recoverable, work in relative units and say so on a slide"); the decision rule below was run and its answer recorded before that fallback became necessary.

**What the dataset paper and its distribution say, and how sure we are.** Every row is a *documented expectation for the audit to confirm*, never an assumption to build on. [C] marks what the Phase-1 audit run on the real dataset confirmed.

| Property | Statement | Tag |
|---|---|---|
| Source | Nasdaq Nordic (Helsinki) ITCH feed; five stocks (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä); ten consecutive trading days, 1–14 June 2010 | [S] |
| Session | Helsinki trading runs 10:00–18:25 local; the dataset keeps only events between **10:30 and 18:00** local, excluding the pre- and post-opening auction periods. Original timestamps were shifted three hours from Eastern European Time (the paper quotes the day as 7:00–15:25 in the data's own clock) | [S] |
| Timestamps in the public files | Not among the 144 features + 5 labels, so no clock time is available; any intraday-seasonality control is therefore impossible | [S] |
| Row | Event-based: each representation is a vector for **10 consecutive events**. The paper reports **394,337 representations** from roughly four million events (its abstract's "≈4,000,000 samples" counts events). That ratio implies **non-overlapping blocks of 10 events**, not a stride of one | [S]; confirmed by total row count ≈394k [C] |
| Features | 144-dimensional Kercheval–Zhang representation. Basic block = raw 10-level book (price and volume, both sides) — **the first 40 columns**; the remaining blocks are derived time-insensitive and time-sensitive features | [S]; "first 40 columns" confirmed [C] |
| Columns and labels | 149 columns = 144 features + 5 label columns. Labels (up/stationary/down at horizons of 1, 2, 3, 5, 10 events) are built from **future** mid-prices and are never read (section 6.7) | [S] for labels; 149 [S] on the dataset's distribution documentation (rows 1–144 features, 145–149 labels) |
| Raw convention | Prices multiplied by $10^4$ and stored as integers; tick = one cent = **100 raw units**; volumes are integers | [S] |
| Folds and files | Day-anchored forward cross-validation: the training set grows by one day per fold (9 folds, training days $1..k$), the test set is the next day. Files are organised by {training, testing} × {with, without auction} × three normalizations; names look like `Test_Dst_NoAuction_ZScore_CF_9.txt` | [S] (layout); "every file holds all five stocks" [S] on the distribution documentation |
| Normalizations | z-score, min–max and decimal precision; the paper's Eq. (5)–(7) are $\frac{x-\bar x}{s}$, $\frac{x-x_{\min}}{x_{\max}-x_{\min}}$ and $x/10^k$ with $k$ the integer for which $\max\lvert x\rvert<1$ | [S] |
| **Statistics scope** | Whether $\bar x,s,x_{\min},x_{\max}$ and $k$ are taken **per row** across the 144 features or **per feature** across the sample is not settled by the paper's text. Resolved by the A1 discriminating test below: **global** (one exponent for the whole file) | [C] |
| Availability | No un-normalized variant is distributed | [S] |

**The working file.** The release used is the decimal-precision **NoAuction** training file, `Train_Dst_NoAuction_DecPre_CF_7.txt` (days 1–7), with `Test_..._CF_7/8/9.txt` as the day 8/9/10-reserve test files. In every case all execution-relevant quantities ($P^a$, $P^b$, $S$, $M$, $D^a$, $D^b$, $\mathrm{OBI}$) are **recomputed from the raw 10-level block** and never read from derived columns.

**Decision rule for A1 — which variant can support this project.**

- **Decimal precision** divides by a power of ten with **no additive term**. Whether $k$ is per row or per feature, within-snapshot ratios (spread, book shape, relative depth) are exact, and — because raw prices sit on a 100-unit tick grid — the grid pins the absolute scale up to a **common power of ten**: the recovered prices and volumes are exact rather than "up to a constant". This is the only variant that can support the project.
- **Z-score and min–max** subtract an unknown location ($\bar x$ or $x_{\min}$). Under either scope the price *level* — hence $M_0$ and every bps metric — is not recoverable from the file alone. **No inversion of these variants is attempted**; the option is closed in Phase 1 so it is not re-opened later (config `dataset.fallback.forbidden`).
- Identify $k$ with the tick-grid test: raw price entries are integer multiples of 100 raw units, so the **smallest** candidate exponent under which every price entry lands on that grid is a **lower bound** on $k$. Any larger exponent also passes, so the test is *one-sided*; the smallest passing value equals the truth unless every price shares extra trailing zeros, which is checked by cross-row continuity and by integer volumes.
- **What a residual ambiguity costs, and why it does not block the project.** If the recovered exponent is wrong by $\delta$ decimals, prices *and* volumes are both off by the same factor $10^\delta$, and then every quantity the study reports is unchanged: bps metrics and the spread-to-price ratio are price ratios; $\theta=Q/\bar D$ is a volume ratio; the implementation-unit impact coefficient $\tilde\eta_0\theta=\eta_0Q/(M_0D^a_t)$ has one $10^\delta$ in $\tilde\eta_0$ and one in $Q$ that cancel; and the sweep term $\psi u/(QM_0)$ scales as $10^{-2\delta}$ in both numerator and denominator. The **only** thing at stake is the absolute euro level, i.e. the euro translation of order size in A8. The scale question is therefore not a gate on the study — it is a gate on one row of one table — and the audit records the exponent because A8 needs it.

| # | Check | Why it matters | Decision rule | Outcome on the real dataset |
|---|---|---|---|---|
| A0 | **Provenance** of the working file | Everything below depends on what the file is | Record file name, source, fold, auction flag, rows, columns in the audit report | **PASS** — 4 files, NoAuction DecPre, fold 7 training + test 7/8/9 |
| A1 | Which normalization variant, which scope, and is the scale recoverable | Impact calibration needs real price and volume *scales* | Proceed only if the file is decimal-precision **and** the exponent is identified by the tick-grid test | **PASS** — DecPre, global $k=6$: `price_euros = stored×100`, `vol_shares = stored×10^6` |
| A2 | Day and stock boundaries; stock identity | A window straddling two stocks or two days is invalid; calibration is **per stock** | Day boundaries follow from the fold layout; stock boundaries detected as discontinuities in the recovered mid-price level; if that fails, cluster the mid level into five stocks | **PASS** — five stocks identified (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä); 10 days |
| A3 | Time axis | Rows are event blocks, not seconds | One period is $m$ rows $=10m$ events; windows start on a row grid; say "event time" in every figure caption | **PASS** — event time, no timestamps |
| A4 | Book integrity | Garbage in, garbage out | Assert $P^a>P^b$, ask prices non-decreasing in level, bid prices non-increasing, volumes $\ge0$, no NaN, prices on the recovered tick grid. Use the **NoAuction** files | **PASS** |
| A5 | Tick discretization | Mid-price often unchanged between rows, so $\hat\sigma$ can be 0 | EWMA over $\ge m$-row blocks with a floor $\sigma_{\min}$ [K]: the 10th percentile of non-zero calibration block volatilities, per stock | **PASS** — floor is non-negative by construction (percentile of $\lvert r\rvert$) |
| A6 | Effective sample size | Windows must not overlap | $N_{\text{eff}}=\sum_{\text{stock-day segments}}\lfloor (n_{\text{seg}}-B_0)/(T\cdot m)\rfloor$ over the test split, windows on a deterministic grid of stride $T\cdot m$ after burn-in $B_0$ [K, default 100]; need $N_{\text{eff}}\ge100$ pooled | **PASS** — 451 calibration / 178 validation / **261 test** windows |
| A7 | Fallback dataset | Last-resort insurance, **not** an equal-status branch | Only via the resolution order below | **N/A** — A1 passed, no fallback needed |
| A8 | **Order-size realism** | $\theta=Q/\bar D$ is relative to *total ten-level* depth; $\theta\ge1$ exceeds all visible depth | Report $\bar D$ per stock in shares and in euros, depth percentiles, and the euro size of $\theta\in\{0.25,0.5,1,2\}$. Immediate at $\theta\ge1$ is penalty-dominated by construction, and results at those sizes are labelled as such | **PASS** — full spread 12.2–23.0 bps by stock (pooled 16.70 bps full = 8.35 bps half) on €12–27 mid-caps |

**Resolution order if A1 fails (decided and logged in Phase 1, never discovered later):**

1. **Work with the decimal-precision files**, with the exponent recovered by the tick-grid test. No un-normalized variant is distributed, so this is the only in-family route.
2. **Do not attempt z-score or min–max.** Listed as an explicit decision so the option is closed.
3. **Fall back** to a raw-price LOB dataset such as the free LOBSTER sample files, after confirming in Phase 1 that suitable sample files exist. Samples are typically one trading day for a few tickers at message-level (not 10-event-block) rows, so the split, $m$, $N_{\text{eff}}$ and the narrative would all be rebuilt — the last resort.
4. **If no route recovers a price level**, work in **relative units** (ticks, bps of tick, normalised depth) and say so on a slide — ROADMAP.md §2's own fallback. Every result is then dimensionless by construction; only the euro column of A8 is lost.

**Sizing $T\cdot m$.** 394,337 rows over ten days is about 39k rows per day for all five stocks, so test days 8–9 hold about 79k rows. At $T\cdot m=400$ that gives about 197 non-overlapping windows before burn-in and boundary losses, so $N_{\text{eff}}\ge100$ holds with margin. This must hold *together with* the feasibility bound of section 10.1, $T\gtrsim\theta/f(\varphi)$; at the default $\rho=0.25$ and $\varphi=0.5$ that is $T\ge5\theta$, so $T=20$ with $m=20$ covers $\theta\le4$. If the audit finds materially fewer rows than assumed, the trade-off is decided explicitly and the binding constraint recorded (R15).

**Scale-recovery recipes.** Illustrative — they are stated here because the decision rule is stated here; in the code they belong to the loader and the audit module.

*Discriminate per-row from per-feature scope* (decimal-precision file, array `X`, rows × 144 features):

```python
row_max = np.abs(X).max(axis=1)      # per row
col_max = np.abs(X).max(axis=0)      # per feature
# per-row k    -> row_max concentrated in [0.1, 1) for (nearly) all rows
# per-feature k -> col_max in [0.1, 1) for each feature, row_max varies widely
```

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

Any larger exponent also passes, so keep the smallest — as a **lower bound**, not as the value — and cross-check with integer volumes (`vol * 10.0**k` integer) and with continuity of $k$ across neighbouring rows or columns. If the file's text precision truncates values, widen `tol` and re-check before trusting $k$. A residual $\delta$-decimal error in the exponent is **not** a blocker for the reasons given above; what *would* be a blocker is a per-feature scope that gave prices and volumes **different** exponents, because the two would then no longer cancel; test for that explicitly before accepting a scale.

### 4.2 Features (all strictly causal)

- Mid $M_t$, spread $S_t$, depths $D^a_t,D^b_t$, imbalance $\mathrm{OBI}_t$, **all recomputed from the raw LOB levels** and never read from precomputed columns.
- Log mid return $r_t=\ln(M_t/M_{t-1})$ and EWMA volatility $\hat\sigma_t$ per period, using data up to $t$ only, within the current stock-day segment. This is the **only** volatility estimate in the project and is shared by ROTE-Static and Almgren–Chriss.
- Regime labels (volatility and liquidity terciles) with **thresholds computed on the calibration split only, per stock**. Stock identity must therefore be recovered (A2).
- **Optional, Tier 2 / E6 only:** micro-price premium $(\mu^{\text{micro}}_t-M_t)/M_t$ with $\mu^{\text{micro}}_t=(P^a_tv^b_{t,1}+P^b_tv^a_{t,1})/(v^a_{t,1}+v^b_{t,1})$ (top-of-book sizes), and order-flow imbalance $\mathrm{OFI}_t$ (a proxy only: each row summarises ten events, which hides the message sequence OFI is computed from). Both are admissible **only** as extra regressors in the drift model of section 5.4, on the same out-of-sample gate as $\mathrm{OBI}_t$. They are never decision-time thresholds, and they cost nothing when unused.

### 4.3 Splits

Chronological, never random, and by whole-day blocks. ROADMAP.md §2 proposes "calibrate days 1 to 7, test days 8 to 10"; this protocol is that split refined into three parts so that a validation set exists for choosing $\lambda$ without touching test:

| Split | Days (of the day-10 release) | Share | Used for |
|---|---|---|---|
| Calibration | 1–5 | ≈56% | Fit $\eta_0$, $\beta$ (drift), $\sigma_{\min}$, regime thresholds, the constant slope $c$, per stock |
| Validation | 6–7 | ≈22% | Choose $\lambda$/$\omega$ grid and $\lambda^\*$, $\rho$, $T$, $m$, $T'$, model variants |
| Test | 8–9 | ≈22% | Run **once** from a frozen config |
| Reserve | 10 | — | Held back; exploratory only, never confirmatory |

The shares are 5/9, 2/9 and 2/9 of the training file — about 56/22/22, not exactly 60/20/20; the shares are rounded to whole days by design. A window straddling a day boundary is impossible by construction. What must not happen is a random split or a split that cuts inside a day. Leave a purge gap of at least $T\cdot m$ rows between splits (automatic with day blocks; the committed file records 400 rows). Split indices are committed to `configs/splits.yaml`, tagged `splits-frozen`, and the split is applied **within each stock segment and then pooled** — a single split over concatenated rows would put whole stocks into calibration, validation and test, an unintended leave-stock-out design that breaks the transfer of $\eta_0$ and the regime thresholds.

**Leave-one-stock-out is not part of this protocol.** It is a Tier 3 item (section 15). The split file must not carry an active generalisation mode until Tier 3 is opened.

The outcome and its reason go in `docs/decision_log.md`; the audit report lives in `data/README.md` beside the loader. Until A1 has recovered the absolute level, worked examples are written in "price units"; FI-2010 is a European venue quoted in euros, so A8's euro translation is possible only after A1.

---

## 5. Cost of execution and the impact model

### 5.1 Execution cost from the book

Buying $x$ shares at a snapshot walks the ask side: fill level 1 up to $v^a_{t,1}$, then level 2, and so on:

$$C_t(x)=\sum_{i=1}^{L}p^a_{t,i}\,q_{t,i},\qquad q_{t,i}=\min\Big(v^a_{t,i},\ \big(x-\textstyle\sum_{j<i}v^a_{t,j}\big)^+\Big).$$

Cost versus mid is $C_t(x)-xM_t=\tfrac12 S_t x+\big(C_t(x)-xP^a_t\big)$: half-spread plus **book-walk premium** $w_t(x)\cdot x$. Fills are limited to **net** depth (sections 6.3, 8.1); the full ordering of every cost term is in section 10.2.

### 5.2 Approximate cost model used by the QP, and how it is chosen

$$\text{cost}_t(x)\approx \tfrac12 S_t\,x+\eta_t\,x^2,\qquad \eta_t=\eta_0/D^a_t .$$

Three candidate families are fitted on the calibration days and compared out of sample on validation, as ROADMAP.md §3 requires ("impact model fitted from the book (linear vs square-root)"):

| Family | Form | Role |
|---|---|---|
| Constant (linear) | $\tfrac12S_tx+c\,x$ | H2's comparator; M1/Almgren–Chriss's classical assumption |
| Depth-scaled quadratic | $\eta_t x^2$, $\eta_t=\eta_0/D^a_t$ | **The model of this project** — the term ROTE-Static and M2 optimise |
| Square-root | $\kappa\,x\sqrt{x/D^a_t}$ | Robustness check for large $\theta$, reported as the local-vs-global crossover of Cont et al. (2014) and Tóth et al. (2011) |

The choice among them is made **on validation, before any test row is read**, and is recorded in the frozen config; H2 then tests the chosen depth-scaled model against the constant model on test (E0). Whichever family wins, the *delivery* is unaffected: M1 keeps its closed form, M2's LP and the ROTE-Static QP keep the quadratic term, and the square-root variant is reported as a robustness column.

**Calibrating $\eta_0$.** Per stock on the calibration split: sample snapshots, evaluate the exact walk premium $w_t(x)$ at probe sizes $x=sD^a_t$ for $s$ on a pre-registered grid up to $\rho$, and regress $w_t(x)$ on the model's own regressor $x^2/D^a_t$ through the origin, pooling every sampled snapshot of that stock; the slope **is** $\eta_0$. (Regressing on $x/D^a_t$ instead would fit a *linear-in-participation* form and return $\eta_0\bar D$, not $\eta_0$ — that is a different model and the specification error is not detectable from $R^2$.) Report $R^2$, the residual pattern, and the fraction of the premium that is exactly zero (small orders inside the top level pay none; the quadratic overstates there). Confidence intervals and cross-stock pooling follow ROADMAP.md §9 ("pool across stocks; show confidence intervals; compare fits").

**Exact-book alternative (reported as a robustness check, not a competing method).** Replace $\eta_tx^2$ by per-level variables $q_{t,i}\in[0,v^a_{t,i}]$ with linear cost $\sum_i p^a_{t,i}q_{t,i}$; the cost is then exact and the program is quadratic only through the risk term. Ascending prices make the optimizer fill cheaper levels first, so no integer logic is needed — and this is precisely M2's decision space (section 6.4).

### 5.3 Implementation units

The program is solved per stock in dimensionless form: $\xi_t=x_t/Q$, with the section 6.2 objective divided by the arrival notional $QM_0$ and reported in bps (a further $10^4$). A factor common to every block changes no minimizer, so the $10^4$ is placed **once**, in the reporting step, and is **suppressed** everywhere else: the bps block is written without it and the risk coefficient absorbs the whole conversion, $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ (section 3). With that convention a term $\eta_tx_t^2$ becomes $\tilde\eta_0\,(Q/D^a_t)\,\xi_t^2$, the half-spread term becomes $\tfrac12(S_t/M_0)\xi_t$, the drift term becomes $(\bar\alpha_t/M_0)\xi_t$, and risk becomes $\lambda\tilde\sigma_s^2(y_s/Q)^2$. Note the $QM_0$ in the conversion and the $Q/M_0$ in $\tilde\eta_0$: they are different, and a $Q/M_0$ written on the $\lambda$ line is wrong by $M_0^2$. Pooling $\lambda$ across stocks at different price levels is meaningful only in these units. The Almgren–Chriss urgency parameter is $\kappa=\sqrt{\lambda\tilde\sigma^2/(\tilde\eta_0\theta)}$ in these units, identical to the $\omega$ of section 2.7 and section 9 T4 via $\kappa=\sqrt{2(\cosh\omega-1)}$; $\omega$ is the canonical symbol and $\kappa$ its square-root shorthand, and **the two must never be used for different quantities**. T13 verifies invariance to price and volume rescaling.

**The $10^4$ has exactly one home, and the identity says where.** Only the ratio $\lambda\tilde\sigma^2/(\tilde\eta_0\theta)$ affects the solution, and that ratio must equal $\lambda_{\text{raw}}\sigma^2/\eta$. Exactly two placements satisfy it. The project uses the first: the $10^4$ is suppressed from the tildes, $\tilde\eta_0=\eta_0/M_0$, $\tilde\sigma_t=\sigma_t/M_0$, and $\lambda_{\text{imp}}=\lambda_{\text{raw}}QM_0$ as written, with the factor entering only when reporting bps. The second carries the factor in both tildes, $\tilde\eta_0=10^4\eta_0/M_0$ and $\tilde\sigma_t=10^4\sigma_t/M_0$, and **divides** $\lambda_{\text{imp}}$ by the same $10^4$. Any other placement breaks the ratio and changes the program: the tildes alone leave it $10^4$ too large, $\lambda_{\text{imp}}$ alone $10^4$ too small, and both together $10^8$ too large, because $\tilde\sigma_t^2$ then grows by $10^8$ against $\tilde\eta_0$'s $10^4$. Writing $Q/M_0$ on the $\lambda_{\text{imp}}$ line is likewise wrong, by $M_0^2$. The identity is asserted numerically in `tests/test_units.py` (`test_identity_section52`, marker T13), not assumed.

**Risk grid on $\omega$, never on absolute $\lambda$.** Because only the ratio above matters, the risk grid is defined on $\omega\in\{0,0.05,0.1,0.2,0.4,0.8,1.6\}$ (config `execution.omega_grid`) and $\lambda$ is *derived* per stock and window from $\cosh\omega=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$. An absolute $\lambda$ grid is not portable across stocks — $\tilde\eta_0$ scales as $1/M_0$ and $\tilde\sigma^2$ as $1/M_0^2$ — and an absolute grid that is too small makes every risk-aware rung silently return TWAP$(T)$ exactly, which is the single most dangerous failure mode in this project (R20).

### 5.4 Price risk and drift

Mid-price changes per period have variance $\sigma_s^2$ and drift $\alpha_s$. With period 1 the arrival snapshot ($M_1=M_0$), the timing cost is $\sum_{t}(M_t-M_0)x_t$ (plus the same exposure on any swept residual), whose variance is

$$\mathrm{Var}=\sum_{s=2}^{T}\sigma_s^2\,y_s^2,\qquad \text{and expected timing cost }\ \sum_t\bar\alpha_t x_t,\quad \bar\alpha_t=\sum_{s=2}^{t}\alpha_s .$$

(Summing from $s=2$ drops the arrival shock, which never occurs: period 1 is the arrival snapshot, so no drift risk is carried before the first decision.)

**Drift model (Tier 2, ablation).** $\alpha$ is $0$ unless an out-of-sample gate passes: regress the mid change over the next $m$ rows on $z_t=(\mathrm{OBI}_t,\dots)$ on the calibration split, and keep the term only if validation out-of-sample $R^2>0$ with a stable sign. When used, ROTE-Static freezes $\hat\alpha_{\text{arr}}$ and sets $\bar\alpha_t=(t-1)\hat\alpha_{\text{arr}}$; the re-solved rung accumulates $\hat\alpha_k$ over $t\ge k$.

---

## 6. Models (the menu)

The four roadmap models (ROADMAP.md §3) plus the linked core program. Every model takes the same inputs and returns the same `Schedule`, so every schedule goes through the same `simulate()` — that is what makes the Compare tab possible (section 7.2).

| ID | Model | Technique | Where it lives | Question answered |
|---|---|---|---|---|
| **M1** | Almgren–Chriss mean–variance schedule | Closed form + CVXPY cross-check | `src/models/m1_ac.py` | How does the schedule change with $\lambda$? What does the cost–risk frontier look like? |
| **M2** | LOB-aware slice allocation | LP with depth and participation limits; shadow prices | `src/models/m2_lp.py` | In thin or uneven books, how should the order be split to minimise walk-the-book cost? Which depth constraints bind? |
| **—** | **ROTE-Static** (M1 + M2 linked) | Convex QP | `src/models/` (core program) | Does arrival-state LOB information improve a risk-aware schedule at matched risk? (Q1) |
| **M3** | Fixed-charge child-order scheduling | Integer programming (binaries, minimum lot, order cap) | `src/models/m3_mip.py` | How many child orders, and what minimum lot, once each order has a fixed cost? |
| **M4** | Strategy selection | AHP with consistency ratio (goal programming as alternative) | `src/models/m4_ahp.py` | Which strategy suits which trader profile? |

### 6.1 M1 — Almgren–Chriss mean–variance schedule

Roadmap §3's formulation, in its own symbols: choose holdings $x_0=X,\dots,x_N=0$, trades $n_k=x_{k-1}-x_k$, and minimise

$$\sum_k\Big[\gamma\, n_k x_k+\varepsilon\, n_k+(\eta/\tau)\,n_k^2\Big]+\lambda\sigma^2\tau\sum_k x_k^2,$$

with $\gamma$ permanent impact, $\varepsilon$ fixed cost per trade, $\eta$ temporary impact, $\sigma$ volatility, $\tau$ step length. $\lambda=0$ gives TWAP-like trading; large $\lambda$ front-loads; the closed form $y_t=Q\sinh(\omega(T+1-t))/\sinh(\omega T)$ is cross-checked against CVXPY.

**Mapping to this project's symbols.** The three impact terms are not all present here. The transient quadratic $(\eta/\tau)n_k^2$ *is* our $\eta_t x_t^2$ with $\eta_t=\eta_0/\bar D$ (median depth, state-blind) — section 5.2's family with $D^a_t$ replaced by its calibration median. The fixed cost $\varepsilon n_k$ is M3's $c_f$ and does not appear in M1. The permanent term $\gamma n_kx_k$ shifts the entry price for the rest of the order; with drift zero and no reaction from others its only *economic* effect here is the benchmark against which shortfall is measured, so it enters this project as $\bar\alpha_t$ (section 5.4) rather than as a separate impact channel, and $\gamma=0$ in the base configuration. M1 is therefore solved as **our** program with $D^a_t\to\bar D$, no participation cap, and the sweep priced at the median-depth worst ask — the state-blind reference that H3(a) compares against.

### 6.2 ROTE-Static — M1 and M2 linked (the core)

For a buy order, with data frozen according to section 6.3:

$$\min_{x}\ \sum_{t=1}^{T}\Big(\tfrac12 S_t x_t+\eta_t x_t^2+\bar\alpha_t x_t\Big)+\lambda\sum_{s=2}^{T}\sigma_s^2 y_s^2+(\psi+\bar\alpha_T)\,u$$

subject to $y_1=Q$, $y_{t+1}=y_t-x_t$, $u=y_{T+1}\ge0$, $0\le x_t\le\rho\,D^{a,\text{net}}_t$.

Adding the risk term to M2's depth constraints is exactly what ROADMAP.md §3 means by "add the M1 variance term to make it a convex QP, which links M1 and M2". Design decisions and their reasons:

- **Sweep price uses arrival information only:** $\psi=P^{\max}_{a,\text{arr}}(1+\pi)-M_0$ (ROTE-Static); for the re-solved rung, $P^{\max}_{a,k}(1+\pi)-M_k$ with drift measured from the current mid. The horizon-end mid $M_T$ and the final snapshot's worst ask are look-ahead and are not admissible as a sweep price; T8 is the test that catches it.
- **Net depth.** $D^{a,\text{net}}_t=\max(0,D^a_t-F_t)$. At planning time ROTE-Static has $F=0$ and uses $D^a_{\text{arr}}$; the simulator enforces the cap on the *actual* net depth.
- **Why a terminal sweep and not a hard completion constraint:** a fixed horizon with caps can be infeasible. The sweep prices the shortfall at the worst visible ask plus penalty rather than leaving the instance undefined; the QP is always feasible. Because $u$ is determined by $x$, the objective is strictly convex in $x$ whenever $\eta_t>0$, so the minimizer is unique. Every strategy is judged against realised walk-the-book execution **including** the sweep, so no strategy can win by leaving inventory unfilled. There is therefore **no completion constraint and no completion dual** — $u=y_{T+1}$ is a definition, not a constraint.
- **Shadow prices (M2's deliverable).** The duals of the participation caps $x_t\le\rho D^{a,\text{net}}_t$ are reported as interpretable output: the marginal cost of a unit of extra depth, i.e. which periods are liquidity-bound. Two related quantities are reported instead of a completion dual, and they are **not** the same number: the reduced cost of terminal inventory, which is $\psi+\bar\alpha_T$ and is the cost of carrying one further share to the horizon end (the price of incompleteness, equal to the sweep price); and the marginal cost of one more share of $Q$, $\partial V/\partial Q$, which is the dual of $y_1=Q$ and depends on the whole solution path. Both are reported, labelled.

### 6.3 Information structure: ROTE-Static vs the re-solved rung

**ROTE-Static (Tier 1).** All parameters frozen at arrival: $S_t\to S_{\text{arr}}$ (no effect on the minimizer, see below), $\sigma_t\to\hat\sigma_{\text{arr}}$, $D^a_t\to D^a_{\text{arr}}$ (so $\eta_t=\eta_0/D^a_{\text{arr}}$ and the cap is $\rho D^a_{\text{arr}}$), $\bar\alpha_t\to(t-1)\hat\alpha_{\text{arr}}$, $\psi\to\psi_{\text{arr}}$. Consequences stated plainly: its schedule is a function of arrival depth, arrival volatility and the cap, **and nothing else**; $S$ affects realised cost but never the minimizer.

**Re-solved (Tier 2, Q2).** Re-solves at every period $k$ over the remaining horizon with parameters frozen at their period-$k$ values, actual inventory $y_k$, observed footprint $F_k$, and executes only $x_k$ (subject to the cap on actual net depth). Differences from ROTE-Static come from **two** sources: updated state (depth, volatility, drift) and re-optimization after shortfalls. To separate them, E6 includes a re-solve-with-frozen-arrival-state rung (re-solved only for realised inventory).

**Oracle-state (diagnostic, never a competitor).** The same program with the *true future* $S_t$, $D^a_t$ (hence $\eta_t$, caps) and $\sigma_t$ known and $\alpha=0$. It bounds the value of knowing the future *book state*; it has no price foresight, and to keep it that way its sweep is priced exactly as ROTE-Static's — arrival-frozen $\psi$ — never from a future worst ask, and drift is still zero.

### 6.4 M2 — LOB-aware slice allocation (the exact-book LP)

Variables $q_{t,l}\ge0$, shares filled in slice $t$ at price level $l$. Minimise $\sum_{t,l}(M_t-p^a_{t,l})\,q_{t,l}$ (roadmap writes the sell side as mid $-$ price; the buy-side shortfall is the mirror) subject to

$$\sum_{t,l} q_{t,l}=Q-u,\qquad q_{t,l}\le v^a_{t,l},\qquad \sum_l q_{t,l}\le\rho\,D^{a,\text{net}}_t,\qquad u\ge0,$$

with the terminal residual $u$ priced at $(\psi+\bar\alpha_T)$ exactly as in section 6.2, so that M2 and ROTE-Static answer the *same* completion question and differ only in how cost is represented (exact per-level vs quadratic). Adding the section 6.2 risk term $\lambda\sum_s\sigma_s^2y_s^2$ in $\xi$-space makes the program the linked convex QP of section 6.2; without it M2 is the roadmap's plain LP.

**What M2 contributes that the QP cannot.** Per-level decisions mean the answer is *exact* rather than a quadratic approximation, and the LP's shadow prices are the interpretability deliverable of the OR guideline: for each period, the dual on $\sum_lq_{t,l}\le\rho D^{a,\text{net}}_t$ says how much cheaper execution would be with one more unit of permitted participation, and the duals on $q_{t,l}\le v^a_{t,l}$ say which *levels* are exhausted. A schedule that binds at level $l$ and not $l+1$ is a statement about the book's shape, and the tab shows it.

### 6.5 M3 — Fixed-charge child-order scheduling

Binaries $z_t$ with $q_t\le Mz_t$, $q_t\ge L_{\min}z_t$, objective plus $c_f\sum_t z_t$, optional $\sum_t z_t\le K$. Each child order carries a fixed cost $c_f$ (roadmap's $\varepsilon$), a minimum lot $L_{\min}$ and an order cap $K$. The cost-vs-number-of-orders curve is the FE/OR interpretation: too few orders and the book is walked deep; too many and fixed costs dominate. Solved as a MIP (OR-Tools/PuLP), with the LP relaxation reported alongside so the integrality gap is visible.

### 6.6 M4 — Strategy selection (AHP)

Criteria: cost, risk, completion, simplicity. Pairwise comparisons per trader profile (conservative, balanced, aggressive); eigenvector weights; consistency ratio $CR<0.1$ required or the matrix is re-elicited. The ranking selects among the *simulated* outputs of M1–M3 and the baselines on the selected window — i.e. M4 closes the loop the FE guideline wants: a genuine decision, not just a plot. Goal programming is the named alternative if the OR viva prefers it (roadmap §9's compression rule keeps AHP unless told otherwise).

### 6.7 Role of machine learning

Admitted only as the drift term, behind the out-of-sample gate of section 5.4, and as a labelled ablation. FI-2010's up/stationary/down labels are built from future mid-prices and are **never read** in Tier 1; they are reserved for the stretch model of section 15, which is Tier 3 and uses its own chronological split. Any ML component that does not beat the no-ML version on validation is removed and the negative result reported. Explicitly **not** the claim: "a neural network was applied to FI-2010" (section 2.7).

---

## 7. Baselines and the interface contract

### 7.1 The ladder

| # | Strategy | Info used | Caps | Tier |
|---|---|---|---|---|
| 0 | **Immediate** (market order at arrival; residual priced as a sweep at $t=1$) | none | no | 1 |
| 1 | **TWAP$(T)$** (equal slices over $T$) | none | no | 1 |
| 1b | **TWAP$(T')$**, $T'<T$ (H1 comparator) | none | no | 1 |
| 2 | **Depth-Proportional**: $x_t=\min\!\big(\rho D^{a,\text{net}}_t,\ y_t,\ \tfrac{y_t}{T-t+1}\cdot\tfrac{D^{a,\text{net}}_t}{\tilde D_t}\big)$, $\tilde D_t$ = trailing median of gross ask depth (causal) | depth | yes | 1 |
| 3 | **Almgren–Chriss (M1)** closed form, $\eta=\eta_0/\bar D$ — impact at the **median** depth — volatility $\hat\sigma_{\text{arr}}$ (same estimator as ROTE-Static), same $\omega$ grid | none | no | 1 |
| 3b | **AC-capped**: the rung-3 trajectory executed with $\min(\text{offered},\rho D^{a,\text{net}}_t)$ and catch-up | depth (cap only) | yes | 1 |
| 4 | **M2 LP** (section 6.4), exact per-level cost | arrival state | in LP | 1 |
| 4b | **ROTE-Static** (section 6.2) | arrival state | in QP | 1 |
| 5 | **Re-solved ROTE-Static** (section 6.3) | updated state | in QP | 2 |
| 6 | ROTE-Static + drift | + OBI drift | in QP | 2 |
| — | Oracle-state | true future state | in QP | diagnostic |

**Execution rule shared by all static schedules (TWAP, AC, AC-capped, Depth-Prop, M2, ROTE-Static):** at period $t$ the offered quantity is $\min\big(y_t,\ \sum_{s\le t}x^{\text{plan}}_s-\sum_{s<t}\text{fill}_s\big)$ ("catch-up to the planned cumulative schedule"); capped strategies then apply $\min(\cdot,\rho D^{a,\text{net}}_t)$. Each rung adds exactly one ingredient: **2 vs 1** isolates depth-proportional slicing, **3b vs 3** isolates the cap, **4b vs 3b** isolates arrival-state scaling of $\eta$ and the in-QP cap and sweep (H3(a)), **5 vs 4b** separates progressive state (Q2), **5a vs 5** separates re-optimization from information. VWAP is not used: FI-2010 rows lack timestamps and volume profiles, so a historical volume curve cannot be built, and the report says so.

**The two guaranteed UI-selectable optimisation models (OR guideline).** Rungs **4b (ROTE-Static QP)** and **3/3b (Almgren–Chriss, M1)** are the two models the UI must offer (section 1.3), and **both are Tier 1** — Almgren–Chriss is a genuine risk–cost optimisation (closed-form solution of the classical mean–variance execution programme), not a heuristic. M2 (rung 4) is Tier 1 as well because the roadmap grades it directly. The re-solved rung (5) is the optional extension. Even if Tier 2 is dropped, the UI therefore always exposes two selectable optimisation models.

### 7.2 One contract, one simulator

ROADMAP.md §4's interface contract, as implemented in `src/utils/contracts.py`:

```python
load_day(stock: str, day: int) -> LOBFrame    # clean, validated, event-indexed
Order(side, size, horizon, params)            # dataclass
model.solve(order, book, params) -> Schedule  # shares per event slice
simulate(schedule, book, impact) -> CostReport  # shortfall_bps, std, trades
```

`Order`, `Schedule` and `CostReport` are frozen dataclasses (`CostReport.to_dict()` carries `shortfall_bps`, `std`, `trades`). Every model returns a `Schedule`; every schedule goes through the same `simulate()`. **No model may implement its own cost loop** — a model that reports its own shortfall is a spec violation, because the comparison is then between two simulators rather than two policies. This is also why `tests/` asserts `sum(shares) == X` and `shares >= 0` for every model (section 9).

---

## 8. Execution simulator

### 8.1 Algorithm

```text
for t = 1 .. T:                                  # snapshot t = w + (t-1)*m, w = window start
    offered_t ← strategy(state_t, y_t, fills so far)       # catch-up rule (section 7.1) or QP x_t, capped by ρ·D_net_t
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

**Consequence for the $\varphi=1$ label, stated because it is easy to get wrong.** The asymmetry above is unconditional, so at $\varphi=1$ the in-horizon footprint recursion collapses to $F_t=0$ for every $t$ — naive replay holds *inside the horizon* — while the sweep still deducts $F_T+\text{fill}_T=\text{fill}_T>0$. "$\varphi=1$ is naive replay" is therefore a statement about the in-horizon recursion only, never about the whole instance. T9 asserts the in-horizon half directly (against a footprint-free per-snapshot walk) and asserts the sweep half separately; a run claiming that $\varphi=1$ matches naive replay *including* its sweep is reading this clause wrongly.

**Indexing.** Snapshot $t$ is index $t-1$ of the in-horizon array, so a horizon of $T$ periods consumes indices $0,\dots,T-1$ and "snapshot $T$'s book" is index $T-1$ — the last snapshot inside the horizon. Passing a longer array must not change the answer, and an array shorter than $T$ is an error rather than a silent truncation. T9 asserts both. The sweep is priced **net of $F_T+\text{fill}_T$, read off the period-$T$ record** — never $F/(1-\varphi)$.

### 8.2 Footprint and resilience

Our own fills remove displayed liquidity that the replayed book does not know about. The **footprint** $F_t$ is deducted from ask depth, and recovers by a fraction $\varphi$ per period. $\varphi=1$ is naive replay **inside the horizon** (an optimistic bias); $\varphi=0$ is permanent consumption (pessimistic). Neither label extends to the terminal sweep, which deducts $F_T+\text{fill}_T$ at every $\varphi$ (section 8.1). **Base case $\varphi=0.5$**; $\varphi\in\{1,0.5,0.25,0\}$ is a pre-registered sensitivity (E5).

### 8.3 Assumptions and limitations (stated in the report, not hidden)

ROADMAP.md §9 names the headline limitation — "recorded data doesn't react to your orders" — and the table below is the full list, with the direction of each bias.

| ID | Assumption | Bias |
|---|---|---|
| S1 | The book replays historically; no reaction to our orders beyond $F_t$ (roadmap: "walk the recorded book for immediate cost, add calibrated impact for the rest; state the assumption") | optimistic |
| S2 | Other participants' behaviour is static | optimistic |
| S3 | Orders fill only against **visible** depth and hidden liquidity is ignored — pessimistic in itself; but the replay also assumes an offered quantity fills at the touch with **no queue-ahead uncertainty** and no partial-fill probability — optimistic. The two effects push in opposite directions | mixed; the queue assumption is the one that flatters aggressive strategies, and it is stated as a limitation rather than netted out |
| S4 | Taker-only; no passive orders, no fees, no latency | neutral/optimistic |
| S5 | Quadratic cost model is a local approximation (square-root crossover for large sizes) | model risk |
| S6 | Rows are 10-event blocks without timestamps: no intraday-seasonality control; calendar-time results cannot be stated | scope |
| S7 | Stock-windows within a day share a market factor; pooled windows are not fully independent | CI optimism, handled in section 10.3 |
| S8 | 10 days in June 2010 on a Nordic venue; 5 stocks — no claim about other venues or regimes (roadmap §6's "limitations" slide) | external validity |

---

## 9. Correctness standards

**Unit and property tests (all must pass before any experiment).** T1–T14 are the scientific standards of the original specification; T15–T17 are the roadmap's own §4 requirement — "unit tests required for models (sum of trades equals X, no negative trades, closed form matches solver)" — made falsifiable. Markers T1–T14 are declared in `pyproject.toml`; **T15–T17 must be added to `[tool.pytest.ini_options].markers` when they are implemented.**

| ID | Test |
|---|---|
| T1 | Constant parameters, $\lambda=0$, no binding caps, $\alpha=0$: the QP returns TWAP$(T)$ |
| T2 | Model verification: larger $\lambda$ or $\sigma$ front-loads the schedule |
| T3 | First-period share is non-decreasing in $\lambda$ and $\sigma$, non-increasing in $\eta$ |
| T4 | Unconstrained QP — caps slack, $\alpha=0$, sweep inactive so $u=0$ — matches the closed form $y_t=Q\sinh(\omega(T+1-t))/\sinh(\omega T)$, $\cosh\omega=1+\lambda\tilde\sigma^2/(2\tilde\eta_0\theta)$ in implementation units (section 5.3), equivalently $1+\lambda\sigma^2/2\eta$ in raw units (section 2.7). **This is ROADMAP §4's "closed form matches solver", for M1 and ROTE-Static** |
| T5 | Solution satisfies constraints and KKT conditions to tolerance; **no negative trades** for any model |
| T6 | $T=3$ brute-force grid search agrees with the solver |
| T7 | Infeasibility is detected; the sweep is never cheaper than a feasible marginal slice: $\psi>\tfrac12S_t+2\eta_t\rho D_t+\bar\alpha_t-\bar\alpha_T$ (the risk term only strengthens it, since an earlier fill removes exposure) |
| T8 | **Causality:** perturbing every datum after arrival leaves the ROTE-Static plan unchanged; perturbing data after period $k$ leaves the re-solved plan for period $k$ unchanged |
| T9 | Simulator invariants: $\sum\text{fill}_t+u^{\text{real}}=Q$ (conservation across all rungs); fills and cash equal a per-snapshot walk with no footprint deduction when $\varphi=1$; Immediate cost is non-decreasing in $Q$; caps are never exceeded; the sweep is priced against depth net of $F_T+\text{fill}_T$, i.e. no resilience recovery on period $T$'s own fill (section 8.1), and it is priced at snapshot $T$ — the last snapshot inside the horizon, so no book printed after the horizon is ever read |
| T10 | The worked example of section 2.1 returns 5.5 bps (2.5 + 3.0) |
| T11 | Liquidity monotonicity: adding depth **at the price levels already in the book** never increases the optimal objective value. The qualifier is required: depth added at **new, worse** far levels raises $P^{\max}_a$ and therefore $\psi$, so with $u>0$ the unqualified statement is false — which is exactly the penalty-dominated regime of section 10.1 |
| T12 | Conservation: planned vs executed shares and the section 10.2 components sum to $\text{Spend}-QM_0$; **for every model, `sum(Schedule.shares) == Q`** (roadmap §4: "sum of trades equals X") |
| T13 | Scale invariance: multiplying all prices by $c>0$ and all volumes by $d>0$ leaves bps metrics, $\theta$ and participation schedules unchanged |
| T14 | AC-capped equals AC when caps are slack; TWAP$(T'=T)$ equals TWAP$(T)$ |
| **T15** | **M2 shadow prices are the LP's own duals:** complementary slackness holds (dual $\ne0$ only where the constraint binds), duals are non-negative for $\le$ constraints, and recovering the objective from primal + dual (weak duality) matches to tolerance. The tab's "which depth constraints bind?" claim rests on this |
| **T16** | **M3 structure:** every child order respects $L_{\min}\le q_t\le Mz_t$ with $z_t\in\{0,1\}$; sum of trades equals $X$; the cost-vs-number-of-orders curve is minimised somewhere in the reported range (not at a boundary artefact); the LP relaxation's bound is a valid lower bound on the MIP optimum |
| **T17** | **M4 validity:** pairwise matrix is positive with unit diagonal, $CR<0.1$ on the shipped matrices, weights sum to 1 and are non-negative, and a strictly preferred strategy under every criterion ranks first (consistency sanity) |

**Why T4 compares against a re-derived closed form.** The $\sinh$ trajectory with $\cosh\omega=1+\lambda\sigma^2/2\eta$ is the exact solution of *this* program, whose only curvature is the transient quadratic $\eta x^2$. Almgren–Chriss reaches the same functional form through a different term — its permanent impact — so its published $\omega$ relates $\lambda$ to a *linear* impact coefficient, not to $\eta_0/\bar D$. The formula is therefore derived here rather than cited, T4 asserts the implementation-unit form of section 5.3, and matching AC's published $\omega$ instead would be a different and wrong check.

**Experimental correctness.** Chronological splits; calibration quantities (including regime thresholds) fit on calibration only; $\lambda^\*$ and the comparator $\lambda$s chosen on validation only; one test run from a frozen config; every table carries config hash and git commit; figures regenerate from `python run_experiment.py`.

**A green test run is not evidence of a scientific claim.** Before citing any standard, know what it asserts: T1–T4, T9, T10, T12, T13, T14 have asserted bodies in the previous pipeline; placeholders marked `assert True` assert nothing and must not be cited in the report. The status of each standard is reported in section 11.5 at each checkpoint.

---

## 10. Evaluation protocol

### 10.1 Instances and parameter grid

- **Instances.** Windows start on the **deterministic non-overlapping grid** of A6 (stride $T\cdot m$ rows, after burn-in $B_0$), fixed once and **reused for every strategy and every $\theta$**. Random start rows are not used, so $N_{\text{eff}}$ is real and every comparison is paired.
- **Sizes.** $\theta\in\{0.25,0.5,1,2\}$, plus a stress size $\theta=5$ (expected to force sweeps). $\bar D$ is the per-stock calibration-set median ask depth; $Q=\theta\bar D$. A8 translates each $\theta$ into euros.
- **Defaults [K].** $T=20$, $m=20$ (so $T\cdot m=400$), $\rho=0.25$, $\pi=0.005$, $\varphi=0.5$, $\omega$ on the grid of section 5.3, chosen on validation.

**Feasibility must include the footprint.** With constant fills $f$ per period and resilience $\varphi>0$, the steady-state footprint is $F^\*=(1-\varphi)f/\varphi$ and $f\le\rho(D-F^\*)$ gives the sustainable throughput

$$f(\varphi)=\frac{\rho\,\varphi}{\varphi+\rho(1-\varphi)}\,D .$$

| $\varphi$ | $f(\varphi)/D$ at $\rho=0.25$ | Approx. $T$ needed to finish without sweep |
|---|---|---|
| 1 | 0.250 | $\approx 4\theta$ |
| 0.5 | 0.200 | $\approx 5\theta$ |
| 0.25 | 0.143 | $\approx 7\theta$ |
| 0 | total fill $\le D\,(1-(1-\rho)^T)<D$ | impossible for $\theta\ge1$; $\theta=0.5$ needs $T\gtrsim3$ |

These ignore depth variation and the initial transient, so they are guides, not guarantees. Consequences: at $T=20$, $\varphi=0.5$ every grid size completes without the sweep on average and $\theta=5$ does not; **at $\varphi=0$ every $\theta\ge1$ hits the sweep**, so slicing comparisons at $\varphi=0$ are restricted to $\theta\le0.5$ and larger sizes are reported as penalty-exposure comparisons.

### 10.2 Metrics

$$\text{Spend}=\sum_t C_t(\text{fill}_t)+C^{\text{ex}}_{\text{sweep}}(u^{\text{real}}),\qquad \text{IS}_{\text{bps}}=10^4\,\frac{\text{Spend}-QM_0}{QM_0}.$$

| Component | Definition |
|---|---|
| Half-spread | $\sum_t\tfrac12S_t\,\text{fill}_t$ |
| Book-walk (in horizon) | $\sum_t\big(C_t(\text{fill}_t)-P^a_t\,\text{fill}_t\big)$ |
| Timing (in horizon) | $\sum_t(M_t-M_0)\,\text{fill}_t$ |
| Sweep execution | $C^{\text{ex}}_{\text{sweep}}(u^{\text{real}})-M_Tu^{\text{real}}$ |
| Sweep timing | $(M_T-M_0)\,u^{\text{real}}$ |
| of which penalty premium | shares beyond visible depth $\times\big(P^{\max}_a(1+\pi)-M_T\big)$ |

The execution-cost terms (half-spread, book-walk, sweep execution) plus the two timing terms sum exactly to $\text{Spend}-QM_0$, which T12 checks. All three sweep rows use $u^{\text{real}}$, the residual actually left after simulation, which equals the QP's planned $u$ only when no period came up short (sections 3, 8.1); every component row is computed from executed shares, never from the plan. Also reported: realised risk (std of IS), completion share (non-swept), peak participation, win rate versus TWAP$(T)$, and **predicted vs realised cost** (QP expected cost without the $\lambda$ term versus realised IS, both converted to bps of $QM_0$ before comparison; calibration slope near 1 is the target). Mean and standard deviation of shortfall in bps are exactly ROADMAP §3's "shared pieces".

**The risk–cost frontier is read as an efficient frontier, not just a chart.** E3 plots mean IS against realised risk for every $\omega$ of both M1 and ROTE-Static; a point below-and-left of another dominates it; the FE framing (mean–variance trade-off, risk aversion as utility) is satisfied by reading $\omega$ as the marginal rate of substitution between the two axes and reporting the slope along the fitted frontier.

**Full spread vs half-spread, stated because every spread statistic hinges on it.** `S` is the **full** spread ($P^a-P^b$); the cost model uses the **half**-spread $\tfrac12S_t$ because it is measured against the period-$t$ mid. Pooled mean full spread is 16.70 bps = 8.35 bps half. Calling `S` a half-spread doubles every spread statistic. T12 cannot detect a mis-split (its identity holds for any split of the same total); spread figures are checked against the book directly instead.

### 10.3 Statistics

- **Resampling unit and dependence.** Windows are non-overlapping, but regimes persist, so use a **moving-block bootstrap over windows within each stock-day series**, block length $b$ windows (pre-registered; default 5). All comparisons are **paired** by window. Day-clustered intervals (10 stock-day series in the test split) are reported as a *sensitivity only*: two test days cannot support day-blocking as the primary scheme.
- **Cross-stock dependence.** Stock-windows on the same day share a market factor; stock-wise results are shown alongside the pooled result, and the pooled CI is read with S7 in mind. Measured on the previous exploratory run, between-stock variance was 0.0% of total IS variance (within-stock by construction, since IS is in bps), so the pooled metric is sound; the check is re-run per configuration.
- **One confirmatory family.** Primary tests, all in the primary cell $\theta=1$, $\varphi=0.5$: H1 at $T'=\lceil T/2\rceil$, H2 pooled, H3(a) at the **medium** risk level.
- **Power.** Before the test run, compute the minimum detectable effect, $\text{MDE}\approx2.8\cdot \mathrm{SE}_{\text{paired}}$, for 80% power. $\mathrm{SE}_{\text{paired}}$ is the **block-bootstrap** standard error of the paired difference at the pre-registered block length, taken on validation — *not* $\mathrm{SD}/\sqrt{N_{\text{eff}}}$, which assumes independence and therefore understates it: the resampling unit is a block, so only about $N_{\text{eff}}/b$ independent units exist. If the MDE exceeds the paired difference observed on validation, **or** the block length is not supported by the shortest stock-day series, the primary tests are declared **descriptive** in advance.
- **Matched risk** is judged by the acceptance rule of section 1.5, not by a fixed percentage; the standard deviation of IS over about 100 windows carries roughly 7% sampling error (more under fat tails), which is why a fixed tolerance would reject most cells.
- **Thin cells.** The $3\times3$ regime grid has about $N_{\text{eff}}/9$ windows per cell. Show CIs; prefer the **tercile marginals** (one dimension at a time, $N_{\text{eff}}/3$ windows).

### 10.4 Experiments

| ID | Experiment | Tier | Split |
|---|---|---|---|
| E0 | Cost-model out-of-sample test (H2). The development run of this experiment uses **validation**; only the single test run below is confirmatory | 1 | test |
| E1 | Ladder table: mean IS, risk, completion, by $\theta$ (primary cell first) | 1 | test |
| E2 | Shadow prices and cost decomposition (M2/ROTE-Static cap duals, terminal-inventory reduced cost and $\partial V/\partial Q$, section 6.2; components, section 10.2) | 1 | test |
| E3 | Risk–cost frontier figure with matched-risk tests (sections 1.5, 10.2) | 1 | test ($\omega$/λ frozen on validation) |
| E4 | Regime analysis: tercile marginals; $3\times3$ grid descriptive | 1 | test |
| E5-min | Resilience $\varphi\in\{1,0.5\}$ (and $\{0.25,0\}$ for $\theta\le0.5$) | 1 | test |
| E5 | Full sensitivity: $\varphi$, $\pi\in\{25,50,100\}$ bps, $\rho$ | 2 | test |
| E6 | Ablations: re-solve with frozen arrival state, drift, depth-response regression (section 1.4), exact-book variant | 2 | test |
| E7 | Design sensitivity ($T$, $m$, $b$, $\sigma_{\min}$, $T'$) | 2 | **validation only** |

Priority order for the sprint: E0, E1, E3, E4, E5-min, then E2, E6, E5, E7. E1 and E3 are the roadmap's "benchmark comparison table (cost, std)" and "M1 frontier" of presentation section 6 (roadmap §6).

### 10.5 Pre-registration (frozen configuration)

There is **no separate pre-registration document**; the mechanism is the frozen configuration. Every numeric constant lives in `configs/experiment.yaml` — the source of truth for experiment numbers — and is **frozen by committing it and tagging `config-frozen` with the config hash before any test row is read**. The single test run must execute from that frozen config. It fixes: the primary tests and Holm family, $\theta$ grid, $T$, $m$, $\rho$, $\pi$, $\varphi$, $T'$, the three risk levels, bootstrap block length and replications, the $\sigma_{\min}$ rule, $B_0$, the MDE and which tests are descriptive, and the experiments run on test. The acceptance rule of section 1.5 is in the text; its numeric parameters are set *after the validation frontier exists and before the first test run*, written into `configs/experiment.yaml` before the `config-frozen` tag. A post-freeze change to any constant is labelled *post hoc* (section 11.6).

---

## 11. Delivery plan

`ROADMAP.md` §5 owns the schedule (weeks, owners, exit criteria); this section states how a *phase* maps onto it and what gate a week must clear.

### 11.1 Owners (ROADMAP §4)

Name owners in the repo README. Everyone reviews at least one other person's pull requests.

| # | Workstream | Owns | Also owns |
|---|---|---|---|
| 1 | **Data and app shell** | `src/loader/`, `src/stats/`, Data and Statistics tabs, Streamlit skeleton | Final integration and deployment |
| 2 | **Finance and simulation** | `src/impact/`, `src/sim/`, `src/benchmarks/`, Compare tab | Financial interpretation of results; Decision-tab wording |
| 3 | **Optimisation A** | M1 (closed form + cvxpy), ROTE-Static frontier over $\omega$, M4 (AHP) | Optimiser tab for M1/ROTE-Static; Decision tab logic |
| 4 | **Optimisation B** | M2 (LP, shadow prices), M3 (MIP), sensitivity analysis | Optimiser tab for M2 and M3 |

Branch per feature, pull request with one reviewer, unit tests required for models (section 9).

### 11.2 Weeks → gates

| Weeks | Focus (ROADMAP §5) | Gate here | Definition of done for that gate |
|---|---|---|---|
| 1 (5–11 Oct) | Interface contract, branches, CI-lite; loader + normalisation check; M1/M2 on a toy book | **G1** | `load_day()` works for all 5 stocks and 10 days; contract merged; review-1 feedback listed in `docs/feedback_log.md`; audit report regenerated (`A0–A4` PASS) |
| 2 | Statistics module + Statistics tab; impact calibration days 1–7 validated on 8–10; M1/M2 on real data | **G2** | Statistics on demand in the UI; impact parameters per stock with intervals; `splits-frozen` |
| 3–4 | $\omega$ sweep and frontier; M4 with consistency check; M3 + sensitivity; backtest with Immediate and TWAP; Optimiser and Compare tabs wired | **G3** | Every model returns a `Schedule`; benchmark table reproducible; T1–T17 pass; **G4** (MVP): Tier-1 pipeline runs end to end on validation |
| 5 | Full flow Data → Statistics → Optimiser → Compare → Decision; caching, validation, defaults, error messages | **G5** | Someone outside the group completes the flow without help in under 5 minutes; matched-risk machinery tested on synthetic frontiers with a known crossing |
| 6 | Analysis and interpretation: stocks, order sizes, horizons, held-out days | **G6** | At least three defensible conclusions with numbers; **freeze** — numeric constants finalised in `configs/experiment.yaml`, committed, tag `config-frozen` |
| 7 | Deck, report, rehearsal; each member writes the slides for the parts they built; two dress rehearsals; backup demo recording; quiz round | **G7** | **The single test run**, first and unattended, from the frozen config; every claim has a CI and a mechanism; report complete; UI all five panels |
| 8 | Buffer and final polish; fix bugs from rehearsal; freeze code; tag release; final rehearsal | **G8** | Clean-checkout reproduction of every table and figure; repository tidy; definition of done (section 16) |

**Stop-loss.** If the MVP gate (G4) is missed at the end of Week 4, drop all Tier 2 items (re-solve, drift ablation, E6/E7 and the exact-book robustness column); the study answers Q1 only. The drift ablation is the first thing cut. M3 reduced to a single-stock demonstration and M4 kept as AHP are the compression rules of section 11.4, not ad-hoc cuts.

### 11.3 Phase-by-phase notes

Week 1 must produce a written answer to every row of section 4.1 before any optimisation code exists (the audit is regenerated as G1 because the loader is being rebuilt). Matched-risk machinery (section 1.5) is tested on synthetic frontiers with a known crossing during Week 5. The test run is **single** and automated: results are read only after it completes.

### 11.4 Compression rules (ROADMAP §9)

**If the final presentation is under about 6 weeks away**, cut in this order:

1. Reduce M3 to a single-stock demonstration.
2. Replace AHP with a simple weighted scoring layer *only if* the instructors accept it; keep AHP if the OR viva is going to probe it.
3. **Never drop:** M1, M2, the benchmarks, the stats-on-demand UI, and the Decision tab. These are what both courses grade. Tier-1 in this spec: loader/audit, cost model + E0, ROTE-Static + M1/M2, simulator, baselines 0–3b, E1/E3/E4/E5-min, the five-panel UI with two guaranteed models, and the report.

### 11.5 Progress (as of 2026-10-05)

Recorded so this document alone tells the reader where the project stands. A phase counts as complete only when its gate is met; the gate, not the presence of a file, is the test.

| Item | Status | Evidence |
|---|---|---|
| FE instructor sign-off (section 2.3) | **Complete** | Approval obtained before implementation |
| OR prior permission for the QP/optimal-execution topic (section 2.3) | **Complete** | Permission obtained; topic accepted |
| First Project Review (sections 2.4–2.5) | **Complete** | Presented and completed 2026-10-04; feedback incorporated; log in `docs/feedback_log.md` |
| CR dataset/group registration (section 2.3) | **Complete** | FI-2010 registered on the CR sheet |
| Phase-1 audit A0–A8 | **Complete, facts recorded** | All checks PASS on the real dataset (A7 N/A); results recorded in `configs/experiment.yaml` (`variant: DecPre`, `scale_exponent: 6`, `scope: global`) and this section 4.1. **The report file `data/README.md` and the six figures were removed with the old pipeline and must be regenerated in Week 1 (G1)** |
| Scale recovery (A1) | **Complete** | Decimal-precision DecPre, global $k=6$: `price_euros = stored×100`, `vol_shares = stored×10^6` |
| Stock/day boundaries (A2) | **Complete** | Five stocks identified (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä); 10 days |
| Splits | **Frozen** | Tag `splits-frozen`; `configs/splits.yaml`: calibration days 1–5, validation 6–7, test 8–9, reserve 10; purge gap 400 rows; $N_{\text{eff}}$ = 451/178/261 windows |
| Phase-1 decision log | **Complete** | `docs/decision_log.md` |
| **Migration to the ROADMAP architecture** | **In progress (Week 1)** | Old pipeline removed (`src/data`, `src/cost`, `src/optimize`, `src/simulator`, `src/features`, `run_experiment.py`, `CHANGELOG.md`, `DECISIONS.md`); new layout in place as skeletons: `src/utils/contracts.py` (implemented — `Order`, `Schedule`, `CostReport`), `src/loader/loader.py`, `src/impact/impact.py`, `src/models/{m1_ac,m2_lp,m3_mip,m4_ahp}.py`, `src/sim/simulate.py`, `src/stats/stats.py`, `src/benchmarks/twap.py` (stubs) |
| Test suite | **Not yet migrated** | Only `tests/test_basic.py` (2 contract tests) remains; the previous 222-test suite was removed with the old pipeline. **Nothing in section 9 has been re-implemented yet**, so no T-standard currently asserts. G1's audit tests, G2's impact tests and G3's T1–T17 are the Week 1–4 work |
| UI (`app.py`) | **Reset** | Streamlit entry point present with title and roadmap reference; the five panels of section 1.3 are to be built in Weeks 1–5 |
| Correctness test suite | **Historical reference only** | The previous pipeline had 222 tests with 9 of 14 standards asserting (T1–T4, T9, T10, T12, T13, T14) and 16 `assert True` placeholders (T5–T8, T11). That evidence does not carry over to the new tree and must not be cited for it |
| Gates G1–G8 | **0 of 8 met** | See section 11.2 |

### 11.6 Document discipline

Hypotheses, primary tests and the acceptance rule are **fixed** by this file, and nothing in it is revised on the basis of test results. Before the single test-set run they may be changed for two reasons only: the Phase-1 audit outcome (section 4.1), which supplies the empirical facts the design depends on; or a factual error or internal inconsistency, which is a property of the text rather than a result. After the test run they are frozen, and any later change is labelled *post hoc* in the report.

**Companion documents.** `ROADMAP.md` (approach, schedule, model menu) and `AGENTS.md` (engineering scaffold) are companions: where `ROADMAP.md` and this file differ on *what is due when*, `ROADMAP.md` governs; where they differ on *how something is measured or claimed*, this file governs. Design decisions are recorded in `docs/decision_log.md`, review feedback in `docs/feedback_log.md`, and the rejected alternatives register is `docs/REUSE_ANALYSIS.md`. `CHANGELOG.md` and `DECISIONS.md` were retired with the old pipeline. No superseded draft exists as a file or is relied on here.

---

## 12. Presentation and viva readiness

**Final presentation outline** (roadmap §6):

1. Problem, and **what changed since review 1** (feedback addressed — cite `docs/feedback_log.md`)
2. Data and cleaning, including the stated assumptions (relative units, event time) — sections 4.1–4.2
3. Liquidity statistics, as findings rather than charts
4. Impact model calibration and out-of-sample validation — section 5, E0
5. Models M1 to M4: formulation, result, interpretation (M1 frontier, M2 shadow prices, M3 order-count trade-off, M4 weights and consistency) — section 6
6. Benchmark comparison table (cost, std) — E1, section 10.2
7. Live UI demo, ending on the Decision tab
8. Conclusions, limitations (no own-order market reaction, 5 stocks / 10 days), future work — sections 8.3, 15

**Speaker allocation:** one section per member (the owner of section 11.1 for that part), but rotate who answers questions so everyone fields questions outside their own part.

**Viva readiness** (roadmap §7). Each member must be able to:

- write M1 to M4 from memory and explain every symbol (sections 6.1–6.6 and the notation table of section 3);
- explain every FI-2010 column used and the normalisation caveat (section 4);
- interpret a shadow price, an AHP consistency ratio, and the efficient frontier (sections 6.4, 6.6, 10.2);
- say what the model **cannot** claim (no own-order market reaction, small sample, event time) — section 8.3.

Two mutual quiz rounds are scheduled (Weeks 5 and 7) where each member is quizzed on someone else's model. Demos have a recorded backup and a pinned environment (section 13).

---

## 13. Repository and reproducibility

### 13.1 Target tree

```text
ROTE/
├── README.md                 # operational guide; team owners (section 11.1)
├── ROADMAP.md                # approach and schedule
├── PROPOSAL.md               # this specification
├── app.py                    # Streamlit UI (section 1.3)
├── pyproject.toml            # dependencies, pytest markers (T1–T17), ruff config
├── configs/
│   ├── splits.yaml           # frozen day blocks (tag: splits-frozen)
│   └── experiment.yaml       # every experiment number; frozen at tag config-frozen
├── data/README.md            # audit report (section 4.1) — regenerated in Week 1
├── docs/
│   ├── decision_log.md       # design decisions
│   ├── feedback_log.md       # review-1 feedback and disposition (section 2.5)
│   └── REUSE_ANALYSIS.md
├── notebooks/rote_analysis.ipynb   # notebook UI (section 1.3)
├── src/
│   ├── utils/contracts.py    # Order, Schedule, CostReport (section 7.2)
│   ├── config.py
│   ├── loader/               # load_day, scale recovery, boundaries (A0–A2)
│   ├── stats/                # statistics on demand (panel 2)
│   ├── impact/               # calibration of η₀ and the family choice (section 5.2)
│   ├── models/               # m1_ac, m2_lp, m3_mip, m4_ahp, ROTE-Static QP
│   ├── sim/                  # simulate() (section 8)
│   ├── benchmarks/           # Immediate, TWAP, Depth-Proportional, AC, AC-capped
│   └── evaluation/           # matched risk, bootstrap, frontier (sections 1.5, 10.3)
├── run_experiment.py         # CLI: audit, calibrate, figures, full
├── tests/                    # T1–T17 (section 9)
├── results/                  # tables, figures (generated), runs/<run_id>/
└── report/                   # report and slides
```

Rules: configs are committed before results; every result file records config hash and git commit; no notebook output is a source of record. Data files are never committed (`.gitignore` guards this).

### 13.2 Reproducibility

`python run_experiment.py` regenerates every table and figure from a clean checkout — this is the acceptance check, and it is the one item of the definition of done that has historically gone unmet, so it is a Week-8 gate (G8) with buffer reserved for a failure. Environment: `uv venv .venv && uv pip install -r pyproject.toml --extra dev` (no editable install, no build backend); `uv run --no-sync` reuses the venv. The demo machine is tested with the same pinned environment in Week 7.

### 13.3 Commands

```bash
uv run --no-sync ruff check .                    # lint (line-length 100, py311)
uv run --no-sync ruff format --check .           # format
uv run --no-sync pytest                          # full suite (T1–T17)
uv run --no-sync python run_experiment.py audit  # regenerate data/README.md + figures
uv run --no-sync python run_experiment.py full   # calibration + validation run
uv run --no-sync python run_experiment.py full --test --confirm   # the single test run
```

Run every command from the repo root: output paths are CWD-relative. The test split is gated behind `--test --confirm` and `test_split_consumed` is recorded in the run manifest, so the single-use split cannot be reached by accident.

---

## 14. Risk register

| ID | Risk | Mitigation |
|---|---|---|
| R1 | FI-2010 scale not recoverable (normalization variant or scope misread) | A1 discriminating tests first; resolution order of section 4.1; relative-units fallback (roadmap §2) if no route works |
| R2 | Cost model misfits (quadratic vs real walk) | Three families compared out of sample, choice frozen on validation (section 5.2); E0 test; exact-book variant as robustness check |
| R3 | Arrival-state effect too small to detect (H3(a)) | Matched-risk acceptance rule with paired CI; dominance reported separately; MDE computed in advance; null result published as a characterisation of *when* state-awareness matters |
| R4 | Solver issues | Small convex QP; T4–T6 against closed form and brute force; LP/MIP reported with relaxation bounds (T16) |
| R5 | Backtest optimism | Footprint with $\varphi$ sensitivity; S1–S8 stated; sweep penalty sensitivity |
| R6 | Leakage | Chronological splits, calibration-only fitting, T8 causality test, labels never read |
| R7 | Scope creep | Tiering and stop-loss (section 11.2); compression rules (section 11.4) |
| R8 | Hypotheses vacuous or degenerate | Each hypothesis is stated as a claim the data can refute; comparative statics are demoted to tests |
| R9 | Look-ahead in the sweep or drift timing | Arrival-frozen $\psi$; risk accumulated from $s=2$; T8 |
| R10 | Overlapping windows inflate evidence | Deterministic non-overlapping grid; A6 |
| R11 | Multiple comparisons | Single Holm family; rest exploratory |
| R12 | Matched-risk claims unreliable | Acceptance rule with paired CI; dominance reported separately |
| R13 | Tolerances tuned after seeing the test set | Numeric constants frozen in `configs/experiment.yaml` (`config-frozen`), set before the first test run |
| R14 | Stock/day boundaries unrecoverable | A2 fallback by price-level clustering; else stop at the resolution order |
| R15 | $N_{\text{eff}}$ vs feasibility $T\gtrsim\theta/f(\varphi)$ conflict | Decide explicitly at Week 1 and record the binding constraint |
| R16 | Primary effect smaller than the MDE | MDE in Week 1; declare tests descriptive in advance |
| R17 | Order sizes unrealistic for the venue ($\theta\ge1$ exceeds visible depth) | A8 euro translation; label penalty-dominated results |
| R18 | Cross-stock dependence overstates precision | Stock-wise results; day-cluster sensitivity; S7 |
| R19 | UI under-delivered (guideline non-compliance) | UI is Tier 1 (section 1.3); Week 1 skeleton, Week 2 statistics, Weeks 3–5 panels; both Tier-1 models guaranteed regardless of Tier 2 |
| R20 | Risk grid silently degenerate — an absolute $\lambda$ grid that is too small makes every risk-aware rung return TWAP$(T)$ exactly | Grid is on $\omega$, never on $\lambda$ (section 5.3); a test asserts that the first-period share at the largest $\omega$ differs from TWAP$(T)$'s, so a degenerate grid fails loudly |
| R21 | Migration churn (the ROADMAP rewrite discards a green 222-test pipeline) | Facts already verified are recorded in `configs/` and section 4.1; each Week 1–4 exit re-establishes its own gate; no result from the removed pipeline is cited for the new tree (section 11.5) |
| R22 | One person holds the maths (roadmap §9) | Pairing on formulations; quiz rounds (section 12) |
| R23 | Demo fails live (roadmap §9) | Recorded backup; pinned environment; test on the presentation machine |

---

## 15. Stretch extensions (Tier 3)

- **Stretch ML model (roadmap §10):** a supervised model on the FI-2010 labels (scikit-learn; LightGBM or PyTorch only if a Tier-1 and Tier-2 gap does not claim the time). Chronological split preserved; labels read only here; the model must beat the no-ML drift on validation or it is reported as a negative result (section 6.7).
- Leave-one-stock-out generalisation (needs its own split mode); time-varying $\rho$; passive-order extension; transient-impact kernel; nonlinear (power-law) cost; sell-side full replication.

---

## 16. Definition of done

All of the following (the roadmap's checklist, section 1.1, with this document's gates named):

- [ ] Clean loader and on-demand statistics for any stock and day; audit report `A0–A8` regenerated (G1, sections 4.1–4.2)
- [ ] Impact model calibrated and validated out of sample; family choice frozen on validation (G2, section 5.2)
- [ ] M1, M2, M3, M4 and ROTE-Static working, tested and interpreted behind the single contract (G3, G4; section 9 — T1–T17 pass)
- [ ] Immediate and TWAP benchmarks compared on cost and risk, plus AC, AC-capped and Depth-Proportional (E1; section 7)
- [ ] Streamlit app: Data → Statistics → Optimiser → Compare → Decision, all five panels, with ≥2 selectable optimisation models (G5, G7; section 1.3)
- [ ] Review-1 feedback addressed and logged (section 2.5)
- [ ] E0, E1, E3, E4, E5-min complete with CIs; every confirmatory result reported with its Holm-adjusted outcome; every other result labelled exploratory (section 10)
- [ ] `splits-frozen` and `config-frozen` tags precede the single test run (section 10.5)
- [ ] The report names the tier reached and states which hypotheses lapsed (H3(b) lapses with Tier 2)
- [ ] A clean checkout reproduces every table and figure with `python run_experiment.py` (G8, section 13.2)
- [ ] Final deck, report, README, demo backup recording (G7, G8)

---

## 17. References

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

**Verification note.** The FI-2010 structural statements tagged [S] were checked against the text of Ntakaris et al. (the arXiv version), which also lists Kercheval–Zhang with the volume and pages above, and then re-checked against the paper's full text **and** the dataset's own distribution documentation. They confirm: 394,337 representations from ~4 million events; Nasdaq Nordic ITCH, Helsinki, five stocks, 1–14 June 2010 (10 trading days); the 3-hour EET shift with the trading day at 7:00–15:25 in the data's clock; the retained window **10:30–18:00 local**, excluding the pre- and post-opening auction periods; prices ×10,000 with a 1-cent tick in euros; 144 features with rows 145–149 as the five labels; Eq. (5)–(7) verbatim; and the file-naming convention, `Test_Dst_NoAuction_ZScore_CF_9.txt` being a real filename among several one-day test files. Two facts the paper does not state — the 149-column total and "every file holds all five stocks" — are stated in the distribution documentation and are tagged accordingly in section 4.1. The remaining reference entries were **not** re-opened against publisher records, with one exception (Rockafellar–Uryasev, corrected to 21–41).

*End of specification.*
