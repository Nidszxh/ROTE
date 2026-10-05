# CHANGELOG

Every change to `PROPOSAL.md` that a reader of the final text could otherwise be misled by: what the text used to say, what it says now, and what must not be reintroduced.

`PROPOSAL.md` carries no version number — entries are dated instead. Purely editorial changes (a broken cross-reference, a stale citation page) are not listed.

The 88 corrections made while drafting `PROPOSAL.md`, predating the current text, are **not** reproduced here and were dropped on 2026-10-04. They were transcribed from superseded drafts and are not re-verifiable against those drafts. What survives of that history is the register of retired claims in `DECISIONS.md`, which is the part that still does work: it stops a plausible-sounding error from being re-derived.

---

## 2026-10-04 — Corrections folded into the specification

Each entry below is already incorporated in `PROPOSAL.md`.

1. **The spread is not schedule-neutral.** Dropped the claim that `½S·Σx_t` is constant whenever the order completes, so `S` cannot move the minimizer. False, because `u` is a decision: `½S·Σx = ½S(Q−u)`, so the objective carries `u(ψ + ᾱ_T − ½S)`. *Now:* the exact condition. `S` cannot move the *shape* of the in-horizon schedule for fixed `u`, and cannot move the minimizer where `u = 0`; it moves the plan through the chosen sweep share wherever `u > 0` — the penalty-dominated cells. Consequently H3(a) tests arrival-state scaling of the cost coefficient **plus the in-QP cap**, nothing more.

2. **Calibrating `η₀`.** Dropped "regress `w_t(x)` on `x/D^a_t` through the origin". That fits a linear-in-participation model and returns `η₀·D̄`, not `η₀`, and `R²` cannot detect the error. *Now:* regress on the model's own regressor `x²/D^a_t`, pooled per stock; the slope **is** `η₀`.

3. **There is no completion dual.** E2 reported "dual variables (shadow prices) of the completion identity", but `u = y_{T+1}` is a definition, not a constraint. *Now:* E2 reports the **cap duals**, the terminal-inventory reduced cost `ψ + ᾱ_T` (the price of incompleteness) and `∂V/∂Q` (the dual of `y_1 = Q`) — three different numbers, labelled.

4. **The Almgren–Chriss comparator's impact.** Used `η = η̃₀/D̄`, which is not the impact at median depth under any unit convention here, so rung 3b was not AC-capped and H3(a) had no valid comparator. *Now:* `η = η₀/D̄`, i.e. `η̃₀θ` in implementation units.

5. **Depth-response regressions.** One regression was used for both strategies with slope zero expected for Static, which a frozen plan cannot have against a regressor that varies *within* the window. *Now:* two regressions. MPC positive within-window; Static zero on the within-window demeaned depth. Static's cross-window level does vary with arrival depth and is reported descriptively, not as a test.

6. **T11's qualifier.** "A deeper book never increases the optimal objective value" is false where `u > 0`: depth added at new, worse levels raises `P^max_a` and hence `ψ`. *Now:* "depth added **at unchanged price levels**", with the failure regime named.

7. **T4's conditions.** The closed-form comparison was asserted with no conditions. *Now:* asserted where it holds — caps slack, `α = 0`, sweep inactive, and in the implementation units actually solved.

8. **The sweep's footprint asymmetry.** The sweep is priced net of `F_T + fill_T` while the recursion gives `F_{T+1} = (1−φ)(F_T + fill_T)`, and the asymmetry was unstated. *Now:* stated as a deliberate conservative choice and asserted in T9, so it cannot be "corrected" silently.

9. **The oracle's sweep price** was unspecified, so "no price foresight" was unverified. *Now:* the oracle prices its sweep exactly as Static does — arrival-frozen `ψ` — and drift stays zero.

10. **`C^ex_sweep` was used but never defined**, and was confusable with `C_sweep`. *Now:* both defined and distinguished — cash paid, versus shortfall against `M₀`. Component rows use executed shares.

11. **Two symbols for one quantity.** `κ = √(λσ̃²/(η̃₀θ))` and `ω` with `cosh ω = 1 + λσ²/2η` were never related, and neither was in the notation table. *Now:* `ω` is canonical and carries both unit forms; `κ` is its shorthand, `κ = √(2(cosh ω − 1))`. The two must never denote different quantities.

12. **The units of `λ`.** `λ` was labelled "in bps⁻¹" with no conversion from the optimization coefficient and the `10⁴` never placed, so an implementer could be wrong by a factor of `10⁴·Q·M₀`. *Now:* `λ_imp = λ_raw·Q·M₀` with the `10⁴` placed once, and the identity `λ_imp·σ̃²/(η̃₀θ) = λ_raw·σ²/η` asserted so the raw and implementation `ω` are provably one number. Writing `Q/M₀` on that line is wrong by `M₀²`.

13. **H1's supporting argument** was stated without its conditions. *Now:* labelled a **within-model** statement, with its conditions (Gaussian increments, quadratic cost, no binding caps, frontier not truncated at the comparator's risk). Outside them H1 is an empirical question, not a theorem.

14. **S3's bias** was labelled simply "pessimistic". *Now:* recorded as **mixed** — excluding hidden liquidity is pessimistic, but granting instant fills at the touch with no queue-ahead is optimistic, and the queue assumption is the one that flatters aggressive strategies.

15. **Recovered prices were called "exact"** while the tick-grid test is one-sided. *Now:* exact up to a common power of ten, with the consequence stated — a residual exponent error changes nothing the study reports, only the euro translation of order size in A8. The case that *would* matter, a per-feature scope giving prices and volumes different exponents, is named as a blocker.

---

## 2026-10-04 — FE/OR course-guideline compliance folded into the specification

Each item below is already incorporated in `PROPOSAL.md`.

1. **Interactive UI was absent from the specification.** Both course guidelines require a user interface: FE — load/clean data, show descriptive statistics on demand, and run ≥2 distinct financial analyses from a menu; OR — load the dataset, generate statistics on demand, and perform ≥2 user-selectable optimisation models. *Now:* section 1.1 specifies the UI as a **Tier 1 deliverable** with five panels (dataset loader, statistics on demand, optimisation menu, baseline comparison, results), delivered as both a Streamlit app and a Jupyter/Colab notebook over the existing `src/` modules; wired into the roadmap (Phases 4, 5, 7), the deliverables tree, the risk register (R19) and the Definition of Done.
2. **The two selectable optimisation models depended on cuttable Tier 2.** MPC (rung 5) was the only second optimisation model and sits in Tier 2, which is the first thing cut. *Now:* the two guaranteed UI-selectable models are **Proposed-Static QP (rung 4) and Almgren–Chriss (rungs 3/3b), both Tier 1** (section 6); MPC is the optional third. Compliance holds even if every Tier 2 item is dropped (sections 1.1, 10.1).
3. **The FE analysis menu was implicit.** *Now:* section 1.1 defines Analysis A (optimal execution), Analysis B (strategy comparison) — the two required analyses — and Analysis C (risk–cost frontier) as a third.
4. **Tools & Technologies and First Review Alignment were not explicit headings.** *Now:* sections 2.5 and 2.4 list them against the OR first-review rubric (significance, methodology, tools, dataset+variables, research questions).
5. **Course-topic approval was unacknowledged.** *Now:* section 2.3 records that optimal execution / convex QP is outside the listed OR topics and that instructor approval is required before implementation, plus the FE group/dataset registration note.
6. **Section renumbering (cross-references updated everywhere, including `DECISIONS.md`).** The hypotheses subsection is now **section 1.2** (was 1.1, collided with the new UI section), matched risk is **section 1.3** (was a second 1.2), and Positioning is **section 2.6** (was 2.3, collided with the new 2.3–2.5).

---

## 2026-10-04 — Documentation simplified before implementation

Not design changes. Recorded so a later reader knows why the document set changed shape.

- Appendices removed from `PROPOSAL.md`. The corrections appendix became this file; the audit-recipe appendix was folded into section 4.1, where the recipes are used.
- The Python-package requirement was dropped. Packages sit directly under `src/` as the specification's tree already said; `pyproject.toml` declares dependencies and tool configuration only, with no build backend and no install step.
- The section symbol was replaced throughout by the word "section".
- `` was rewritten to a lean engineering guide. Its reconciliation record, its second notational layer (`[P]`/`[E]`), its four numbered conventions, its duplicated restatement of assumptions S1–S8, and its pre-submission checklist were removed as either superseded or restating the specification.
- **Correction to item 12.** The specification previously said an implementer who leaves the `10⁴` explicit on every block uses `λ_imp = 10⁴·λ_raw·Q·M₀` *and* `10⁴` inside every tilde, and "solves the identical program". Those three choices together put the risk ratio `λ·σ̃²/(η̃₀θ)` a factor `10⁸` away from `λ_raw·σ²/η`, so they do not. Exactly two placements preserve the ratio, and both were verified numerically: either the `10⁴` is suppressed everywhere and `λ_imp = λ_raw·Q·M₀`, or it is carried inside both tildes and `λ_imp` is *divided* by `10⁴`. Applying it to the tildes alone, or to `λ_imp` alone, is wrong by `10⁴` in opposite directions. One convention is now stated once; `PROPOSAL.md` section 5.2 records why the alternative is arithmetically forced rather than optional. Writing `Q/M₀` on the `λ_imp` line remains an error of `M₀²`.

---

## 2026-10-04 — Separate pre-registration document removed; progress recorded

Each entry below is already incorporated in `PROPOSAL.md`.

1. **`experiments/preregistration.md` was deleted as a redundant artifact.** The freeze requirement it carried is unchanged; only its location moved. *Now:* section 8.5 defines pre-registration **as** the frozen configuration — every numeric constant lives in `configs/experiment.yaml` (already the source of truth for experiment numbers), committed and tagged `config-frozen` with the config hash before any test row is read (G10), with the single test run (G11) executing from that frozen config. Sections 1.3 (R13), 10.2 (Phase 5), 11 (R13) and the repository tree were updated to match; `README.md` and `DECISIONS.md` follow. A post-freeze change to any constant remains labelled *post hoc*. **Must not be reintroduced:** a second document holding constants, which can drift from `configs/experiment.yaml`.
2. **Project progress and course milestones were not recorded anywhere in the specification.** *Now:* the header carries a **Progress (2026-10-05)** row, section 2.3 is marked **complete** — FE sign-off, OR prior permission, CR registration and the First Project Review all obtained/completed — and **section 10.5** tabulates progress: Phase 1 complete (audit A0–A8 all PASS, scale `k=6`, `splits-frozen`, test $N_{\text{eff}}=261$), Phases 2–3 in progress (`calibrate` and `check-formulation` SUCCESS), UI running, test suite green (72 tests), zero known lint debt.
