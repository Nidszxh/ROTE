# REUSE vs REWRITE — what exists, what adapts, what is new

| Field | Value |
|---|---|
| **Purpose** | Inventory the current tree against the interface contract and model menu in `ROADMAP.md`, and classify every component as reuse-as-is, adapt, or rewrite from scratch |
| **Standing** | **Advisory analysis. It changes nothing.** It does not amend `PROPOSAL.md`, either roadmap, or any gate. Where the roadmaps conflict, this document names the conflict and asks for a decision rather than taking one |
| **Scope of "current"** | Working tree as of 2026-10-05, `d010895` plus 25 modified and 15 untracked paths. `222 passed` on the full suite (~17 s) |
| **Reviewed** | 2026-10-05 |

Following the user directive: `ROADMAP.md` (repo root) is now the **only source of truth**. The `docs/CORRECTIONS.md` file has been deleted. This analysis maps `ROADMAP.md`'s requirements onto the current codebase. See §1 for context.

---

## 1. The three-way direction conflict (read this first)

| Axis | `PROPOSAL.md` (existing implementation) | `ROADMAP.md` (root, new source of truth) |
|---|---|---|
| Deliverable | A falsifiable study: H1/H2/H3, single confirmatory run, frozen config | A graded tool: M1–M4, 5 tabs, benchmarks, deck, live demo |
| Success | A matched-risk CI that excludes zero, plus a validated cost model | Instructors can see two models, a frontier, a decision tab and a benchmark table |
| Models | 7 rungs (Immediate → ROTE-MPC), one QP + one closed form | M1 AC, M2 LOB LP, M3 fixed-charge IP, M4 AHP/GP — **different menu** |
| Side | Buy only | `Order(side, …)` — both (or per requirement) |
| Completion | Terminal sweep at arrival-frozen ψ | Hard completion `x_N = 0`, no sweep |
| Effort shape | Research implementation | 8 weeks, 4 members, PR-reviewed |
| Risk measure | std of IS across windows | Per ROADMAP, focus on mean/std as needed |

**Consequences that matter for reuse decisions:**

1. **The model menus are disjoint, not nested.** M2/M3/M4 have no counterpart in the study; the study's 7 rungs have no ID in the course menu. The user wants to follow ROADMAP - this is the key pivot.
2. **M1 is the only overlap, and it is partial** — see §5.3. Both want "AC mean-variance with a sinh closed form cross-checked against cvxpy".
3. **The existing QP implementation is valuable** - user wants to reuse the static QP rather than waste it. As analyzed in §5.8, best to reuse as-is for M1 (with adaptations) and show it; do not force it to become M4's technique.

**Decision needed before any code is written:** which document is the build plan. Everything below is written to be valid either way, but the *labels* and the *definition of done* are not.

---

## 2. Verdict summary

Legend — **R** reuse as-is · **A** adapt (existing module, non-trivial edit) · **W** rewrite from scratch · **N** new file, no predecessor.

| # | ROADMAP component | Current home | Verdict | New lines (est.) |
|---|---|---|---|---|
| 1 | `load_day(stock, day) -> LOBFrame` | `src/data/loader.py:127-261`, `src/data/windows.py:34-103` | **A** | ~70 |
| 2 | Cleaning + validation (bid<ask, monotone) | `src/data/audit.py:142-173` (check A4) | **R** | 0 |
| 3 | Scale/normalisation identification | `loader.py:114-124`, `audit.py:49-113` | **R** | 0 |
| 4 | `stats.py` (spread, depth-by-level, imbalance, returns, vol) | *does not exist*; `app.py:63-77` hardcodes 4 pooled numbers | **W** | ~150 |
| 5 | Impact calibration, quadratic arm | `src/cost/quadratic.py:6-46` | **R** | 0 |
| 6 | Impact: linear arm, square-root arm, CIs, RMSE/MAE/bias/R² | *does not exist* | **W** | ~150 |
| 7 | `simulate(...)` — walk the recorded book | `src/simulator/execution.py:20-156` | **A** (signature only) | ~40 |
| 8 | `CostReport.shortfall_bps` | `evaluation/metrics.py:14-78` | **R** | 0 |
| 9 | `CostReport.std` | `evaluation/metrics.py:81-86` + `experiment.py:256-260` | **R** | 0 |

| 11 | `CostReport.trades` | `execution.py:76-92` (`records`) | **A** (rename/expose) | ~10 |
| 12 | `Order(side, size, horizon, params)` | *no dataclass of that kind* | **W** | ~30 |
| 13 | `Schedule` | `ladder.build_plan` + `solve_static`'s dict | **W** (thin wrapper) | ~30 |
| 14 | `model.solve(order, book, params)` | `optimize/solve.py:53-164`, `ladder.py:164-174` | **A** (dispatcher) | ~50 |
| 15 | **M1** AC mean-variance | `baselines/ladder.py:74-125`; equivalence proven in `tests/test_solve.py:73-107` | **A** — and see §5.3 | ~80 |
| 16 | **M2** LOB LP + shadow prices | specification exists at `PROPOSAL.md:364`; duals already extracted at `solve.py:148` | **A** | ~70 |
| 17 | **M3** fixed-charge IP | *no IP anywhere; no MIP in the cascade* | **W** on top of #16 | ~130 |
| 18 | **M4** AHP + consistency ratio | *nothing* | **W** | ~220 |
| 19 | **M4-alt** goal programming | same constraint block as `qp_schedule.py:40` | **A** | ~50 |
| 20 | ROTE-Static as an M4 alternative / 5th model | `optimize/`, `evaluation/` | **R** + relabel | ~20 |
| 21 | Benchmarks: Immediate, TWAP | `ladder.py:52-71` | **R** | 0 |
| 22 | Benchmarks: VWAP | *no volume clock exists* | **W** or substitute (§5.9) | ~50 |
| 23 | UI tab 1 Data | `app.py:17-49` | **R** | 0 |
| 24 | UI tab 2 Statistics | `app.py:51-86` | **W** | ~150 |
| 25 | UI tab 3 Optimiser | `app.py:88-176` | **W** (logic), reuse the library | ~250 |
| 26 | UI tab 4 Compare | reads `run_experiment` CSVs | **A** | ~150 |
| 27 | UI tab 5 Decision (= M4) | *nothing* | **W** | ~120 |
| 28 | Test suite (222 tests) | `tests/` | **R**, partly | ~0 |

**Totals: ~2,100 new lines to satisfy the whole course roadmap**, of which roughly 900 are UI and 700 are the three genuinely new models (M3, M4, the impact comparators). The scientific core — loader, cost model, simulator, metrics, QP, AC closed form — is done.

---

## 3. Interface contract, mapped signature by signature

ROADMAP §4:

```python
load_day(stock: str, day: int) -> LOBFrame
Order(side, size, horizon, params)
model.solve(order, book, params) -> Schedule
simulate(schedule, book, impact) -> CostReport   # shortfall_bps, std, cvar, trades
```

| Contract item | What exists | Gap | Verdict |
|---|---|---|---|
| `load_day(stock, day)` | `loader.load_train_lob(cfg)` → `(X, Lob, boundaries)`; `loader.load_test_lob(cfg, day)` → one day, one stock; `windows.split_row_ranges(start, end, 7, 5, 2)` for day blocks | No `(stock, day)` addressing. **Day boundaries inside the train file are a uniform-length convention `[K]`, not a measurement** (`windows.py:1-15, 34-44`) because `rows(train_k) − rows(train_{k−1})` needs files FI-2010 does not ship | **A** — thin wrapper, caveat stated |
| `LOBFrame` | `loader.Lob` TypedDict (`loader.py:44-55`): `Pa, Va, Pb, Vb, Pa1, Pb1, M, S, Da, Db, OBI` | Shape is `(N,10)` arrays, not a long frame; no `side`, no `volume_t` | **R** — adopt as the contract type |
| `Order` | nothing. `experiment.Calibration` (`experiment.py:38-62`) and `windows.Window` (`windows.py:24-31`) are the only dataclasses | — | **W** |
| `model.solve` | `solve_static(Q, T, spread, depth, sigma2, eta0, mid0, rho, lambda_imp, p_max_arrival, …)` — flat kwargs, not an Order; `ladder.build_plan(rung, Q, T, **kw)` is a partial dispatcher that raises `KeyError` for online rungs (`ladder.py:164-174`) | — | **A** — one dispatcher over `LADDER` + `solve_static` |
| `Schedule` | every rung already yields `(plan: ndarray[T], schedule_fn, cap_flag)`: `ladder.build_plan` for the static four, `catch_up_schedule_fn` (`ladder.py:128-135`), `depth_proportional_schedule_fn` (`:138-152`), and `solve_static`'s dict (`solve.py:151-164`) | No named type; `solve_static` returns a dict while the others return bare arrays | **W** — ~30-line dataclass, ~15 lines of adapters |
| `simulate(schedule, book, impact)` | `run_simulation(Q, T, ask_prices, ask_volumes, mid_prices, schedule_fn, rho, phi, pi, capped)` — takes a *callable*, not a Schedule | Adapter only. **No `impact` parameter, and that is correct** — recorded data does not react to your orders (`PROPOSAL.md` section 7.3, `:458-470`), which ROADMAP §2 also states. Passing `impact` would mean inventing market reaction | **A** — accept and ignore, or reject loudly |
| `CostReport.shortfall_bps` | `metrics.components_bps()["is_bps"]` (`metrics.py:63-78`) | — | **R** |
| `CostReport.std` | `metrics.realised_risk` (`:81-86`), `experiment.aggregate`'s `realised_risk_bps` (`:256-260`) — cross-window std of IS, exactly ROADMAP's "std" | — | **R** |

| `CostReport.trades` | `result["records"]` (`execution.py:76-92`), `result["fills"]` | — | **A** |

**The contract's real content — "every model returns a `Schedule`; every schedule goes through the same `simulate()`" — is already satisfied in substance.** The seven rungs all funnel through `run_simulation` today (`experiment.py:141-152`). That is why the Compare tab is cheap and why M2/M3 are cheap: they are new `Schedule` producers, not a new evaluation path.

**One structural mismatch to fix in the adapter, not in the library:** the contract says `simulate(schedule, …)`. `run_simulation` needs `schedule_fn(t, y, fills, D_net)`, which is *online*. `catch_up_schedule_fn` and `depth_proportional_schedule_fn` are the only such producers, and both exist. So the adapter is `Schedule → schedule_fn` and it is already written for two of three cases.

---

## 4. Loader and statistics

### 4.1 REUSE AS-IS

| Asset | Location | Why it is done |
|---|---|---|
| Row parser, ragged-row and arity validation | `loader.py:76-111` | Rejects wrong column counts, enforces 149 rows, transposes correctly |
| Scale recovery `k=6` | `loader.py:114-124` | `price = stored×10⁴/10⁴`, `vol = stored×10⁶`, tick = 1 cent. ROADMAP §2's "identify your version now" is answered |
| LOB reconstruction + OBI | `loader.py:127-161` | Exactly the 10×4 raw block ROADMAP §2 says to use; derived columns never read |
| Stock-boundary detection | `loader.py:164-184` | `find_stock_boundaries` (mid jumps > €1) + `segment_boundaries` (edges) |
| Book-integrity validation | `audit.py:142-173` (A4) | `Pa>Pb`, monotone levels, volumes ≥ 0, no NaN, tick grid — **ROADMAP Week 1 exit criterion, already met** |
| Dataset-root resolution | `loader.py:187-202` | config → `$ROTE_DATA_ROOT` → `data/raw` → `data/FI-2010` |
| Six microstructure figures | `figures.py:60-405` | Snapshot, boundaries, depth distribution, spread/imbalance, volatility/sigma-floor, walk convexity — usable directly as ROADMAP presentation slides |

### 4.2 ADAPT — `load_day(stock, day)`

The honest blocker, which must survive into the report and the slides:

- **Days 8, 9, 10 are exact and single-stock.** `resolve_test_file` (`loader.py:234-250`) maps day→`CF−1`; `load_test_lob` returns `[0, n]` as the single segment (`loader.py:261`). No inference.
- **Days 1–7 are one stock-major file.** `load_train_lob` returns five segments spanning all seven days; a `(stock, day)` slice therefore requires `split_row_ranges`, which assumes uniform day lengths. That is tagged `[K]` at `windows.py:1-15` and recorded in `experiment.py:57-61`.

So `load_day` is ~70 lines (compose `resolve_data_root` + `resolve_train_file`/`resolve_test_file` + `segment_boundaries` + `split_row_ranges`, return `(lob_slice, day_index, convention_flag)`) and must return or log whether the day boundary is measured or assumed. Do not let the UI present an assumed boundary as a measured one.

### 4.3 REWRITE — `stats.py`

Does not exist. Every input it needs is loaded: `S` (full spread), `Da`/`Db` (aggregated) and `Pa,Va,Pb,Vb` (per level, so depth-by-level is derivable), `OBI`, `M`. `windows.causal_sigma2` (`windows.py:106-128`) is the volatility estimator and is already the *only* one in the project — reuse it rather than adding a second (`src/features/pipeline.py:6` is a duplicate EWMA and is imported by nothing).

`app.py:63-77` must be replaced, not adapted: it reports four pooled-over-the-whole-file numbers with no stock selector, no day selector, and `avg_spread` computed as `lob["S"].mean() * 10000` — that is a **full** spread labelled "bps", so it double-counts against every other spread statistic in the repo (the simulator's `half_spread_bps` of 8.87 bps is the half-spread; the pooled full spread is 16.70). Whoever writes the panel must use `S/2` or label it "full spread".

---

## 5. Models, one at a time

### 5.1 Impact model — REUSE + REWRITE

`calibrate_eta0_for_stock` (`cost/quadratic.py:6-46`) is a 40-line through-origin regression of exact walk premium on `x²/D^a_t`, probed at 10 sizes up to `ρ·D_t`. That is the *quadratic* arm, done, on real data, and it is exactly what `PROPOSAL.md:360` specifies. Reuse verbatim.

Missing, and named by both roadmaps under different labels (ROADMAP Week 2 exit; `docs/CORRECTIONS.md` §3 item "E0"):

| Arm | Status | Lines |
|---|---|---|
| Constant `c·x` comparator | absent | ~25 |
| Square-root impact fit | absent | ~25 |
| RMSE / MAE / bias / R² | absent | ~40 |
| Residual-vs-participation diagnostic | absent | ~30 |
| Bootstrap or analytic CIs | absent | ~30 |

Do this once and it satisfies the course Week-2 exit and the research Phase-C E0 gate. Note `PROPOSAL.md:360` warns that regressing on `x/D` instead of `x²/D` returns `η₀·D̄`, not `η₀`, and that the error is invisible in R² — get the regressor right.

### 5.2 Simulator — REUSE AS-IS, adapt the signature

`src/simulator/execution.py` is the single strongest asset in the tree, and it is *not* on the course roadmap's list at all. It implements footprint `F_{t+1} = (1−φ)(F_t + fill_t)`, net depth `max(0, D−F)`, per-rung caps, and the terminal sweep priced against **snapshot T's** book with a penalty at `P_max(1+π)`.

Evidence it is right, and reusable as-is:

- `tests/test_conservation.py:36-94` — the section 8.2 identity `components == Spend − Q·M0` and `executed == Q` across 85 parameterised cases over 3 books × 3 sizes × 3 horizons × 4 φ × 3 ρ × capped/uncapped.
- `tests/test_simulator.py` (11 tests, T9) — including `test_snapshots_past_the_horizon_are_never_read` and `test_sweep_is_priced_at_snapshot_T`. These are the *only* look-ahead tests in the project. Reintroducing the pre-2026-10-05 sweep index `t = T` fails 82 tests.
- T14 (`tests/test_baselines.py`) is substantive, not vacuous: AC-capped equals AC bit-for-bit when caps are slack and differs by up to 17.4 bps when the cap binds.

Gaps: no `cvar`, and `side` is buy-only (`walk_book_buy`, `cost/walk_book.py:20-108`). Sell is a sign convention on the book (mirror `Pa↔Pb`, `Va↔Vb`, negate the mid delta), which is ~15 lines in the adapter — do **not** fork the execution path, because the sweep, the footprint decay, the cost decomposition and every test above assume the buy side. State "we trade a sell as the mirrored book" rather than implying a second engine.

### 5.3 M1 — Almgren–Chriss mean-variance

#### Can the current ROTE-Static QP serve as M1?

**Yes, as a special case, and the reduction is already implemented and tested.**

`tests/test_solve.py:73-107` sets the sweep price to its neutralising value `ψ = S/2` (equivalently `P_max = (M0 + S/2)/(1+π)`), sets `α = 0`, slack caps, constant spread, and asserts

```
solve_static(...).plan  ≈  ladder.ac_plan(Q, T, omega)     # rtol 1e-3
```

So: **the section 5.4 QP with the cap dropped, the drift dropped, the spread frozen and the sweep tilt neutralised *is* the AC program on this project's cost model, and `ac_plan`'s `sinh` trajectory is its exact solution.** M1 is a *restriction* of the shipped solver, not a reimplementation. `ladder.ac_omega` / `lambda_from_omega` (`ladder.py:74-107`) already provide the ω↔λ bridge, and `tests/test_optimizer.py:75-106` (T4) already asserts the closed form against `build_qp`.

#### Where the two roadmaps' M1 disagree

| | ROADMAP M1 sketch | Shipped AC rung |
|---|---|---|
| Objective | `Σ[γ n_k x_k + ε n_k + (η/τ) n_k²] + λσ²τ Σ x_k²` | `Σ[½S x + (η₀/D̄) x²] + λΣ σ̃² (y/Q)²` |
| Impact terms | permanent γ, linear ε, quadratic η/τ | quadratic only, depth-scaled |
| Urgency | `cosh ω = 1 + λσ²/(2η)`, η **linear** | `cosh ω = 1 + λσ̃²/(2η̃₀θ)`, η̃₀θ = **η₀·Q/(M₀·D̄)** |
| Completion | `x_N = 0`, no sweep | terminal sweep `u = y_{T+1}` at arrival-frozen ψ |

`PROPOSAL.md:561` already anticipated this and refuses the paper's ω: *"Almgren–Chriss reaches the same functional form through a different term — its permanent impact — so its published ω relates λ to a linear impact coefficient, not to η₀/D̄. The formula is therefore derived here rather than cited."* And `PROPOSAL.md:366` warns that the two ω's **must never be used for different quantities**.

That is correct research practice and it is a grading risk. An instructor comparing your ω formula to Almgren & Chriss's will see a different constant, and the honest answer ("our impact coefficient is quadratic and depth-scaled, so ω is re-derived; T4 asserts the implementation-unit form") is a viva answer, not a slide.

#### Two paths, and the recommendation

**Path A — reuse only, 0 new lines.** M1 = `solve_static` with `eta = η₀/D̄`, `rho_D_net = ∞`, `α = 0`, `ψ = S/2`; closed form = `ladder.ac_plan`; the cross-check is `test_solve.py:73` as it already stands. Everything ROADMAP M1 asks for is delivered except the literal impact terms.

**Path B — Path A plus one small module, ~80 lines. Recommended.** Add `src/optimize/ac_classical.py` holding *the paper's* AC as written down: permanent + linear + quadratic temporary impact, `x₀ = X`, `n_k = x_{k−1} − x_k`, `y_t = Q·sinh(κ(T+1−t))/sinh(κT)`, `cosh κ = 1 + λσ²τ²/(2η)`, plus a cvxpy QP of the identical objective for the cross-check. Then:

- M1 is literally the roadmap's model, written from memory-able form (`ROADMAP.md` §7: "write M1 to M4 from memory").
- ROTE-Static becomes legible as **M1 plus three ingredients** — arrival-state `η = η₀/D_arr` instead of median depth, the cap moved inside the QP, and a completion rule that prices the shortfall instead of forbidding it. That is the same claim the research study makes, and it is the best slide in the deck.
- `ladder.ac_plan` stays as the *internal* reference rung for the ladder/experiments. The two ω's never mix: label them `κ_classical` and `ω` and keep the `PROPOSAL.md:366` rule that only one of them is ever the urgency for the study.

**Verdict: ADAPT (Path B). Path A alone is reuse-as-is but leaves a grading exposure that costs more to defend than 80 lines cost to write.**

### 5.4 M2 — LOB-aware slice allocation (LP + shadow prices)

**The specification already exists in the tree's own proposal.** `PROPOSAL.md:364`:

> Replace η_t x² by per-level variables q_{t,i} ∈ [0, v^a_{t,i}] with linear cost Σ_i p^a_{t,i} q_{t,i}; the cost is then exact and the program is quadratic only through the risk term. Ascending prices make the optimizer fill cheaper levels first, so no integer logic is needed.

That is M2, verbatim, minus the participation limit. The inputs are loaded (`Pa`, `Va` per level, `loader.py:135-136`). The greedy level-walking that the LP is supposed to reproduce exactly already exists as `walk_book_buy` (`walk_book.py:74-81`) — so the LP has an *independent oracle* to be tested against, which is a stronger test than ROADMAP §4's "sum of trades equals X".

**REUSE for M2:**

| Piece | Where |
|---|---|
| Inventory recursion + feasibility constraints | `qp_schedule.py:37-41` — copy verbatim |
| Risk term `λ Σ σ̃_s² (y_s/Q)²` | `qp_schedule.py:49-50` — identical |
| Per-rung participation cap pattern | `RUNG_CAPS` + `run_simulation`'s `ρ·D_net` (`execution.py:66-70`) |
| Shadow-price extraction | `solve.py:148-149` — `constraints[2].dual_value`, already done for the QP's caps |
| Exact-cost oracle | `walk_book_buy` |

**ADAPT:** new `build_lp(Q, T, Pa, Va, sigma2, lam, rho, …)` in `src/optimize/`, ~70 lines. Drop `η_t x_t²`, add `q[t,i]` with `0 ≤ q[t,i] ≤ Va[t,i]` and `Σ_i q[t,i] = x_t` (or eliminate `x_t` and constrain `Σ_i q[t,i] ≤ ρ·D^a_net_t` directly). Keep the sweep so the completion rule matches the rest of the tree.

**Two verified traps:**

1. **`φ·volume_t` does not exist.** ROADMAP M2's participation constraint is on *traded* volume per period. This project recomputes every execution quantity from the raw 40 LOB columns and never reads a derived column (`PROPOSAL.md:258`), and has no volume clock at all — `ROADMAP.md` §2 says rows are events, not timestamps. Substitute `ρ·D^a_net_t`, which is what the whole codebase already uses, and say so on the slide.
2. **φ means two different things.** In the ROADMAP, φ is a participation fraction. In this repo, `phi=0.5` is the **footprint-resilience decay** (`execution.py:97`, `configs/experiment.yaml:36-42`). Do not let the symbol onto a slide without disambiguation.
3. **The LP is not a QP.** Verified in this environment on a 3-variable LP with a binding cap: all three solvers return the same primal, but the **duals differ** — OSQP `[1.5492, 0.5492, 0]` and CLARABEL `[1.3359, 0.3359, 0]` against HIGHS's exact `[1.0, 0.0, 0]`. Since shadow prices *are* M2's deliverable, use HIGHS (or CLARABEL with a convergence check). Never OSQP duals — this is the same lesson as `SOLVER_OPTIONS` (`solve.py:22-35`), where OSQP's defaults return an arbitrary point of the optimal face.

### 5.5 M3 — Fixed-charge child-order scheduling (IP)

**Nothing exists.** No binaries, no `z_t`, no fixed-charge term, no MIP in `SOLVER_CASCADE`. Note the tension: the research roadmap puts "LP/IP reformulation" and "QP redesign" explicitly **out of scope** (`docs/CORRECTIONS.md` §6), and `PROPOSAL.md:364` argues integer logic is unnecessary here ("Ascending prices make the optimizer fill cheaper levels first, so no integer logic is needed"). So M3 is pure addition against the study's own grain, and it is also the first item the course roadmap's compression rules demote (`ROADMAP.md` §9: "Reduce M3 to a single-stock demonstration"). It does not touch the frozen configuration, the ladder or any hypothesis, so adding it does not invalidate the study — but it is a recorded decision, not a silent addition.

**REWRITE, but the base is M2's LP and the plumbing is all tested.** Add `z_t ∈ {0,1}`, `q_t ≤ M z_t`, `q_t ≥ L_min z_t`, objective `+ c_f Σ z_t`, optional `Σ z_t ≤ K`.

**Verified solver facts for this environment** (matters, because the naive build does not work):

| Formulation | Result |
|---|---|
| MILP, linear objective + binaries, cvxpy + `HIGHS` | **works** (`highspy` is installed; solved a 3-binary model) |
| MIQP, quadratic objective + binaries, `HIGHS` | **fails**: `SolverError: The solver HIGHS cannot solve this problem` |
| Installed solvers | `CLARABEL, SCS, SCIPY, HIGHS, OSQP` |

**Therefore: build M3 on M2's linear per-level cost, not on ROTE-Static's quadratic objective.** That is the natural choice anyway — a fixed-charge problem is about *how many* child orders, and a per-level linear cost is what makes the order count meaningful. It also means M3 costs +130 lines on a program that already exists. If someone insists on quadratic impact, the options are a piecewise-linear surrogate (breakpoints in `x_t`, one segment per period) or sequential convexification; both are worse and both must be stated as approximations. The "cost-vs-number-of-orders curve" deliverable falls out of the same loop by relaxing `Σ z_t ≤ K`.

**Needed:** a `MIP_CASCADE` alongside `SOLVER_CASCADE` (`solve.py:44-48`) — currently a `SolverError` for binaries, not a slow solve.

### 5.6 M4 — Strategy selection (AHP with consistency ratio)

**Nothing exists.** No pairwise matrices, no eigenvector, no random-index table, no CR. This is the one component with zero prior art in the tree: **REWRITE, ~220 lines.**

| Sub-step | Lines |
|---|---|
| Pairwise matrix assembly from UI judgements | 40 |
| Principal eigenvector (power iteration on `numpy`; `scipy` is available but not needed) | 25 |
| `λ_max`, CI, RI table for `n = 3…9`, `CR = CI/RI`, reject at `CR ≥ 0.1` | 40 |
| Alternatives × criteria matrix, normalisation, weighted score | 50 |
| Trader-profile presets (conservative / balanced / aggressive / liquidity-constrained) | 30 |
| Rendering (matrix, weights, CR, ranking) | 35 |

**What M4 gets for free from the tree:**

- **The alternatives list** — `ladder.LADDER` (`:28`) plus M1/M2/M3, with `RUNG_CAPS` (`:37-45`) supplying per-alternative attributes such as whether a cap is enforced.
- **The criteria values, almost exactly.** `experiment.aggregate` (`experiment.py:236-272`) already emits, per (rung, θ, ω): `is_bps` → **cost**, `realised_risk_bps` → **risk**, `completion_share` → **completion**, and `cap_event_rate` → a defensible fourth (execution fragility) if "simplicity" is unwanted. ROADMAP M4's four criteria are cost, risk, completion, simplicity; three of four are already computed and sitting in `results/runs/exploratory/summary_validation.csv`.
- **The Decision tab's data source** — the summary CSVs already exist for all seven rungs.

**So M4's cost is the AHP kernel plus a decision layer, not a data pipeline.** That is the cheapest of the three new models.

### 5.7 M4 alternative — goal programming: ADAPT, ~50 lines

ROADMAP §3 offers "AHP with consistency ratio (goal programming as alternative)". Goal programming reuses `build_qp`'s constraint block verbatim (`qp_schedule.py:40`) and replaces only the objective with weighted L1 deviation from three targets:

```
min  w_c·d_c⁺ + w_r·d_r⁺ + w_u·d_u⁺      s.t.  the same y/x/u constraints
      d ≥ cost − target_cost,  d ≥ target_cost − cost,  …
```

Verified: HIGHS and CLARABEL both solve that shape directly. The weights `w` are the trader-profile parameters, and `d` reports exactly how much each goal misses — which is a much more informative Decision tab than a CR number when the comparison is close. **Recommend shipping both**: AHP satisfies the stated requirement, GP satisfies the "which profile" question with actual trade-offs.

### 5.8 The user's question: repurpose ROTE-Static for M4?

**Verdict: the existing ROTE-Static QP should be kept as a separate, useful model implementation.** We will not attempt to repurpose it as M4. M4 requires AHP with consistency ratio (CR < 0.1) which is fundamentally different from a schedule optimization - it's a decision method over criteria, not a schedule generator.

ROTE-Static is valuable as-is and should be available in the application (as an additional model alongside M1-M4 if needed), but M4 itself must be properly implemented as AHP.

### 5.9 Benchmarks

| Benchmark | Status | Note |
|---|---|---|
| Immediate | **R** `ladder.immediate_plan` (`:67-71`) | residual swept at `t=1` |
| TWAP | **R** `twap_plan` (`:52-54`) | |
| TWAP(T′) | **R** `twap_prime_plan` (`:57-64`) | not asked for by the course; free, and it is the H1 comparator |
| Depth-Proportional | **R** `depth_proportional_schedule_fn` (`:138-152`) | online, trailing-median depth, cap inside `schedule_fn` |
| AC / AC-capped | **R** `ac_plan` + `RUNG_CAPS` | T14 is substantive |
| **VWAP** | **absent — and structurally hard** | see below |


**VWAP is the one benchmark with no honest implementation.** A VWAP schedule needs a volume clock; this codebase has none, and `ROADMAP.md` §2 itself says rows are events, not timestamps. Options, ranked:

1. **State it and substitute.** ROADMAP's own data-realities table is the justification: "event time is the clock: trade X over N book events". Offer TWAP + Depth-Proportional and say why VWAP is unavailable. Zero code, fully defensible.
2. **Depth-imbalance-weighted TWAP as a labelled proxy** (~50 lines): weight period `t` by `D_t^a/(D_t^a+D_t^b)` at the arrival snapshot. It is *not* VWAP — say "imbalance-weighted participation clock", not VWAP.
3. **Read a derived volume column from the 144 features.** This violates the project's own rule that execution quantities are recomputed from the raw 40 columns (`PROPOSAL.md:258`) and would need a `docs/decision_log.md` entry. Not worth it for one benchmark row.

---

## 6. UI, tab by tab

Three of five tabs exist (`app.py:27-30`). The panels are *skeletons*, not partial implementations.

| Tab | Current | Verdict | What to do |
|---|---|---|---|
| 1. Data | `app.py:17-49` — loads the train file, reports rows/stocks/scale | **R** | Add the stock/day selector so it feeds `load_day` |
| 2. Statistics | `app.py:51-86` — 4 hardcoded pooled metrics, one fixed 500-row depth chart | **W** | New `stats.py` + per-stock/day selectors; fix the full-vs-half spread labelling |
| 3. Optimiser | `app.py:88-176` — calls `build_qp` with **hardcoded η=0.1, σ²=1e-4, ψ=0.5** (`:129-133`), and its "Almgren–Chriss" option is the same QP with caps off and a constant spread (`:135-141`) | **W** (logic) | Call `solve_static`; add the ladder rungs and M1–M4 as options; read η₀ from `calibration.json`; drop the hardcodes. `docs/CORRECTIONS.md` §3 lists this as open Phase-A work |
| 4. Compare | *absent* | **A** | Reads `results/runs/*/summary_*.csv` and in-process `evaluate_window`. `aggregate()` is the whole data layer |
| 5. Decision | *absent* | **W** | M4 / goal-programming layer from §5.6–5.7 |

**One bug to fix before anything else in tab 3.** `app.py:124-126` slices `lob["S"][t_start : t_start+T]`, i.e. it treats **one row as one period**. Every other part of the tree defines a period as `m = 20` rows (`configs/experiment.yaml:30-32`, `windows.py:82`). So the UI's "Execution Horizon (T)" is `T` *rows* = `T/20` periods, and its cost numbers are on a different clock from every table in `results/`. Route the UI through `windows.window_book` and the two agree by construction. This is also why the UI currently reports a nonsense `u.value` in shares (`:174`): `build_qp` is dimensionless there, unlike `solve_static`.

---

## 7. Test suite: what transfers

222 tests pass. Reuse is total except where the object under test changes.

| Suite | Count | Transfers to |
|---|---|---|
| `test_conservation.py` (T12) | 85 cases | **Directly.** "Every schedule goes through the same `simulate()`" is exactly what this proves. M2 and M3 inherit it for free by going through `run_simulation` |
| `test_simulator.py` (T9/T13) | 11 | **Directly.** Look-ahead protection for every new model |
| `test_walk_book.py` | 10 | **Directly**, and the section 2.1 worked example is a ready-made slide |
| `test_solve.py` | 12 | **Directly.** M1's cross-check is line 73 of this file |
| `test_optimizer.py` (T1–T4) | 3 | **Directly.** M1's "closed form matches cvxpy" requirement, already asserted |
| `test_ladder.py`, `test_baselines.py` (T14) | 19 | **Directly** — every benchmark in §5.9 is already tested |
| `test_loader.py`, `test_audit.py`, `test_config.py` | 34 | **Directly** |
| `test_units.py` (T13) | 5 | **Directly.** Scale invariance is what makes pooled bps sound |
| `test_experiment.py`, `test_windows.py` | 16 | **Directly** |
| `test_t.py`, `test_causality.py`, `test_other.py` | 16 `assert True` placeholders | **No.** T5, T6, T7, T8, T11 are the only thing `docs/CORRECTIONS.md` §4 says must not be cut, and none of them asserts |
| New: `Order`, `Schedule`, `load_day`, `stats` | — | ROADMAP §4 asks for "sum of trades equals X, no negative trades, closed form matches solver". The first two are T12; the third is T4. **The course's unit-test requirement is already ~70% met** |

---

## 8. Do **not** reuse

| Thing | Why |
|---|---|
| `app.py:129-153` — hardcoded η/σ²/ψ and the QP-as-AC stand-in | Not AC at all. `ladder.ac_plan` is 6 lines and exact |
| The absolute-λ grid pattern | `configs/experiment.yaml:56-68` and `ladder.py:89-107`: the grid is on ω and λ is derived per stock and window. An absolute λ grid was off by 4–7 orders of magnitude and silently collapsed every risk-aware rung to TWAP(T) |
| `features/pipeline.py` in its entirety | Imported by nothing; its EWMA (`:6`) duplicates `windows.causal_sigma2`, which is the project's only volatility estimator. Its regime thresholds exist nowhere else. Use `causal_sigma2` |
| `src/features/pipeline.py:compute_regime_thresholds` for anything on a slide | Terciles of an unnamed metric with no units — not an analysis |
| `tests/test_t.py` and `tests/test_causality.py` as evidence | 16 `assert True`. A green gate here is not evidence; `AGENTS.md` is explicit |
| `run_experiment.py frontier` | `run_experiment.py:203-209` prints where the CSV is and computes nothing |
| `run_experiment.py check-formulation` | `run_experiment.py:210-221` shells out to pytest and checks only the return code. It validates the *tests*, not the formulation |
| OSQP for anything that reports a dual | §5.4. `SOLVER_OPTIONS` pins 1e-12 *because* OSQP's defaults return an arbitrary optimal-face point; on LPs the duals are simply wrong |
| Forcing `Σx = Q` in the QP adapter | `solve.py:142-146`. A binding cap deliberately leaves a residual for the sweep; forcing completion bypasses the cap the program just chose. `test_solve.py:65-70` covers it |
| Any write to `results/`, `data/` from a library module | All output paths are CWD-relative and `audit`/`figures` dirty tracked artifacts. `run_experiment.py calibrate` writing to `Path("results/tables")` regardless of `audit.report` is a known violation |
| Removing the `$10^4` guard | `cost/units.py` + `metrics.py:11` + `tests/test_units.py::test_identity_section52` pin it to exactly one home. A second placement breaks the program by `10⁴`/`10⁸` (`PROPOSAL.md:366`) |
| `src/baselines/`, `src/evaluation/`, `src/optimize/solve.py` staying untracked | They are **untracked**, so `HEAD` cannot reproduce any frontier. `src/data/windows.py` too. This is `PROPOSAL.md` §12's G14 and it is currently unmet |

---

## 9. What the course roadmap asked for and never mentions

Worth stating, because it is the counterweight to "reuse everything": this tree already contains five deliverables the course roadmap does not ask for, all tested, all cheap to keep.

| Asset | Not on the course roadmap | Keep it because |
|---|---|---|
| Phase-1 audit A0–A8 + `data/README.md` + 6 figures | "loader plus version/normalisation check, first validation" (Week 1) — it asks for the outcome, the tree has the mechanism | The audit is the *evidence* for the normalisation claim ROADMAP §2 tells you to make on a slide |
| Footprint/resilience simulator | Not mentioned | It is what makes the benchmarks comparable at all; TWAP over an event-time book with no footprint is not comparable to a model that consumes depth |
| Conservation identity `components == Spend − Q·M0` (85 cases) | "sum of trades equals X, no negative trades" | Stronger: it pins the cost *decomposition*, not just the share count |
| Look-ahead tests (T9's horizon/footprint properties) | Not mentioned | ROADMAP §7 asks you to say what the model cannot claim. These are how you know |
| Seven-rung ladder with paired windows and a per-rung cap policy | "benchmarks immediate, TWAP, VWAP" | Immediate/TWAP/TWAP(T′)/Depth-Proportional/AC/AC-capped — four more than asked, and the ladder is what turns "compare" into an *argument* |
| Matched-risk machinery + risk–cost frontier (exploratory) | "efficient frontier" for M1 only | The U-shape in realised risk across ω (38.40 → 13.59 → 14.00 bps at θ=1) is a genuine finding and it is the honest answer to "what does risk aversion cost" |

The reverse also holds: **the course roadmap's M2/M3/M4, `Order.side`, CVaR, VWAP, `stats.py` and tabs 4–5 are all new to the research tree**, and three of them (M3, CVaR, the `φ·volume_t` participation constraint) sit against `docs/CORRECTIONS.md` §6's out-of-scope list and `PROPOSAL.md` section 13's Tier 3. Adding them does not invalidate the study — none of them touches the frozen configuration, the ladder, or the hypotheses — but it must be a recorded decision, not a silent addition.

---

## 10. Sequencing

Two tracks that can run in parallel and do not block each other. Effort is one person's, excluding data-load time.

### Track A — course minimum (satisfies the definition of done)

| Step | Work | New lines | Depends on |
|---|---|---|---|
| A1 | `Order`, `Schedule` dataclasses + adapters over `LADDER` and `solve_static` | 80 | — |
| A2 | `load_day(stock, day)` on top of `loader` + `split_row_ranges`, with a measured-vs-assumed flag | 70 | — |
| A3 | `stats.py` + tab 2 rewrite (fix the spread label) | 150 | A2 |
| A4 | Impact comparators: constant, square-root, RMSE/MAE/bias/R², CIs | 150 | — |
| A5 | **M1 Path B**: `ac_classical.py`, closed form + cvxpy cross-check | 80 | A1 |
| A6 | **M2**: `build_lp` + shadow-price table via HIGHS; `test_lp_matches_walk_book` | 70 | A1 |
| A7 | **M3**: `build_mip` on M2's linear cost + `MIP_CASCADE` + order-count curve | 130 | A6 |
| A8 | **M4**: AHP kernel + CR + profiles + ranking | 220 | A4, A6 |
| A9 | Tab 3 rewrite on `solve_static` + ladder + M1–M4 | 250 | A1, A5–A8 |
| A10 | Tab 4 Compare from `aggregate()` | 150 | A9 |
| A11 | Tab 5 Decision on M4 | 120 | A8 |
| A12 | Tests for A1–A8 (ROADMAP §4 requires PR-reviewed tests) | 250 | all |
| A14 | Benchmarks: VWAP substitution note, or imbalance-weighted proxy | 50 | — |
| A15 | `docs/feedback_log.md`, pinned env, branch/PR convention | 0 | — |

### Track B — research continuation (`docs/CORRECTIONS.md`, unchanged by Track A)

T5, T6, T7, T8-as-its-own-standard, T11 → MDE → E0 (Track A4 *is* E0) → matched-risk in risk space → frontiers → freeze → test run. Cut order unchanged: MPC first.

### Shared

- **Commit the untracked modules before either track.** `src/baselines/`, `src/evaluation/`, `src/optimize/solve.py`, `src/data/windows.py`, `tests/test_{experiment,ladder,solve,windows}.py` are untracked; `HEAD` reproduces nothing.
- **Decide the ω labelling before writing M1** (Path A or B), because `PROPOSAL.md:366` forbids mixing the two and the two documents want different ones.
- **Do not touch `configs/experiment.yaml` values** on the course track. Track A adds UI-facing parameters (LOT size, fixed charge `c_f`, order cap `K`, AHP judgements); new keys are fine, changed values are not, and nothing after `config-frozen` may move.

---

## 11. Open decisions — these block work, and they are not mine to take

1. **Which roadmap is the build plan?** `ROADMAP.md` (root) is now the only source of truth as per user directive. The `docs/CORRECTIONS.md` file has been deleted. The build follows ROADMAP.md completely.
2. **Is M1 Path A or Path B?** Path B costs 80 lines and removes a viva exposure; Path A is free and leaves one.
3. **M3 or no M3?** It is the first item on `ROADMAP.md`'s own compression list and the only one needing a solver the project has never used. With the compression rules applied, dropping it is a documented, defensible choice.
4. **VWAP: substitute or build a proxy?** Option 1 is zero code and fully defensible under `ROADMAP.md` §2; option 3 costs a `decision_log` entry and breaks the raw-40-columns rule.
5. **Sell side: mirror the book, or declare buy-only?** The contract says `Order(side, …)`; every test and the cost decomposition assume buy. Mirroring is ~15 lines in the adapter.
5. **How to use the existing ROTE-Static QP?** Keep it as a separate model implementation. Do not use it as M4 - M4 must be properly implemented as AHP with CR < 0.1. It can be offered alongside M1-M4 as an additional model if useful, but it's not M4.