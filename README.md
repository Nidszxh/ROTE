# ROTE — Risk-Aware Optimal Trade Execution

A cost–risk optimal-execution study on FI-2010: a walk-the-book execution cost model calibrated on high-frequency limit order book data, a convex QP for the execution schedule, and a receding-horizon evaluation against a leakage-safe baseline ladder.

`PROPOSAL.md` is the authoritative specification. This file is the operational guide: how to set up a clean checkout, obtain the dataset, and regenerate everything that currently exists.

## The problem

Given a parent order of size `Q` to execute in a limit order book over `T` periods, choose the schedule `x₁ … x_T` that minimises expected implementation shortfall subject to a participation cap on net ask depth. The trade-off is explicit: risk-averse schedules front-load, and the cost of front-loading is spread and impact. FI-2010 supplies Nasdaq Nordic ITCH data from five Finnish stocks over ten trading days in June 2010, and the study asks what a risk-aware convex program buys against the usual ways of cutting risk.

## What is not claimed

- No product, no live-trading system, no claim of execution alpha.
- The execution-cost terms are a **local quadratic approximation**; the exact-book variant is reported as a robustness check (E6), not as the model.
- The simulator replays a historical book. It does not model market reaction beyond its own footprint, other participants' behaviour, queue-ahead uncertainty, fees or latency. Assumptions S1–S8 are stated in full, with their bias, in `PROPOSAL.md` section 7.3.
- Rows are **10-event blocks with no timestamps**, so no intraday-seasonality control is possible and no calendar-time statement is made.
- Nothing is claimed about other venues, other periods or other regimes.

## Method summary

| Piece | What it is |
| :--- | :--- |
| Cost | `C_t(x)` from walking the book; a depth-scaled quadratic `½Sx + η₀x²/D^a_t` for the QP, with `η₀` fitted per stock on calibration only |
| Program | a convex QP over `x_t`, `y_t` and the residual `u`, with the sweep priced at arrival and the caps inside the optimization |
| Risk | one EWMA volatility estimate, shared with Almgren–Chriss so the comparison is not a comparison of two volatility models |
| Simulator | historical replay with a resilience parameter `φ`, a footprint recursion, and unfilled quantity carried into the next period |
| Evaluation | realised risk = cross-window std of IS within a cell; mean IS, cap-binding rate and the section 8.2 decomposition per cell. **The inferential layer is specified but not implemented** — no paired bootstrap, no Holm family, no isotonic frontier. What exists is `matched_risk_table`, which reports each policy's *distance* to the TWAP risk rather than interpolating a common-risk frontier |

## Status

The repository is mid-build. What exists, what it produces, and what it does not yet do:

| Area | State |
| :--- | :--- |
| Dataset audit A0–A8 | **works** — `run_experiment.py audit` regenerates `data/README.md` and the six audit figures. Against the real four files A0–A6 and A8 all `PASS`, A7 `N/A`, and the **tracked report now says so** — it was regenerated from the real dataset on 2026-10-05; see the note below |
| Microstructure figures | **works** — `run_experiment.py figures`; deterministic, verified bit-identical run to run |
| Splits (G2) | **works** — `run_experiment.py freeze-splits` regenerates `configs/splits.yaml` byte-identically; tagged `splits-frozen`. The file is written from fixed day-block constants (`src/data/splits.py`), so that idempotence is by construction, not by measurement |
| `calibrate`, `check-formulation` | **works** — `calibrate` prints a per-stock η₀ in ~25 s **and persists it** to `results/tables/calibration.json`; `check-formulation` shells out to `pytest tests/test_optimizer.py tests/test_solve.py` and reports SUCCESS |
| Risk–cost frontier, the full run | **works on the exploratory splits** — `run_experiment.py full` runs calibrate → windows → the section 6 ladder → section 8.2 decomposition → aggregation in **148 s** (451 calibration + 178 validation windows × 125 cells), writing per-window, summary and matched-risk CSVs plus a manifest. The confirmatory days are reachable only via `full --test --confirm`, so the single-use split cannot be consumed by accident; they remain **unconsumed** (`test_split_consumed: false`) |
| Static QP | **implemented and solved** — `src/optimize/qp_schedule.py` builds the program of PROPOSAL.md section 5.4 and `src/optimize/solve.py` solves it in section 5.2's dimensionless units, reproducing AC's closed form to 0.1% when the sweep tilt is neutralised. OSQP's tolerances are pinned (`SOLVER_OPTIONS`) because **the defaults silently return a wrong point of the optimal face**. There is no MPC; `src/baselines/ladder.py` now implements all seven Tier-1 rungs with section 6's per-rung cap flags |
| Simulator | **implemented and tested (G4)** — `src/simulator/execution.py` implements PROPOSAL.md section 7.1 and `src/evaluation/metrics.py` the section 8.2 decomposition; T9, T12 and T13 assert against both. The sweep is priced at snapshot `T` (index `T-1`), the last snapshot inside the horizon |
| Features | **scaffolded, unreviewed** — `src/features/pipeline.py` is imported by nothing and has no tests |
| UI (`app.py`) | **partial** — 3 of the 5 panels (loader, statistics, optimisation menu); serves under `streamlit run app.py`. Baseline-comparison and results panels are missing and `notebooks/` does not exist. The "Almgren–Chriss" option is the same QP with caps disabled and a constant spread, not an AC implementation — the independent closed form **does** exist in `src/baselines/ladder.py`, and it is the one the CLI and experiment path use; the UI is the only caller still substituting the QP |
| Test suite | 222 tests pass (`pytest`); the T1–T14 gate selects 134. **9 of the 14 standards assert**: T1–T4 (`tests/test_optimizer.py`), T9 (`tests/test_simulator.py`, 11 tests), T10 (`tests/test_walk_book.py`, incl. the section 2.1 worked example), T12 (`tests/test_conservation.py`, 85 parameterised cases), T13 (`tests/test_units.py` + simulator scale invariance), T14 (`tests/test_baselines.py`, AC-capped = AC when slack and ≠ when the cap binds). **T5, T6, T7, T8, T11 remain `assert True` placeholders** (16 of them across `tests/test_t.py`, `test_other.py`, `test_causality.py`), so a green gate is still not evidence of correctness |
| Lint / format | `ruff check .` clean. `ruff format --check .` clean across all 43 files |
| Confirmatory results (E0–E5) | **not run.** The single test-set run happens once, from a configuration frozen and tagged `config-frozen`; `splits-frozen` exists, `config-frozen` does not |

**What happens next** is in `docs/ROADMAP.md`: phases A–G with their gates, the cut order, and an item-by-item list of what is still open — MDE, E0, matched risk, T5–T8/T11, UI panels 4–5, the notebook. It executes this proposal rather than redefining it, so it never becomes a competing source of experiment numbers.

> **The tracked audit evidence was stale until 2026-10-05; this note is the canonical history.** `data/README.md` and the six tracked PNGs at HEAD had been generated from a directory holding nine *synthetic* `Train_*_CF_*.txt` files, so the report read "9 files (9 train, 0 test)" with A6 `WARN` (`Test=0`). Running `audit` against the real FI-2010 release rewrites all seven: 4 files (1 train, 3 test) and A6 `PASS` with 451/178/261 windows. **That diff was a correction, not a regression** — it is sitting in the working tree now. Check `git diff data/README.md` line by line before assuming a code change caused it. Other documents (`PROPOSAL.md` §10.5, `AGENTS.md`, `CHANGELOG.md`, `docs/decision_log.md`) point here rather than restating it.

A clean checkout can now reproduce the **Phase-1 data audit** (`data/README.md`, the six figures, `configs/splits.yaml`) **and the exploratory frontier** (`run_experiment.py full` → `results/runs/exploratory/`). What it still cannot reproduce is any **confirmatory** number: E0–E5 have not been run, and the single test-set run has not been spent.

## Requirements

- Python **≥ 3.11** (developed and verified on 3.12).
- ~1 GB free disk for the dataset (897 MiB) and < 1 GB RAM for the audit commands (measured peak RSS ≈ 0.7 GB).
- [`uv`](https://docs.astral.sh/uv/) or `pip` + `venv`. Nothing else.

There is **no packaging step**. The project is not installable and nothing from the repository is installed: `pyproject.toml` declares dependencies and tool configuration only, with no build backend. `run_experiment.py` puts `src/` on `sys.path` itself, and `pyproject.toml` sets `pythonpath = ["src"]` for pytest. Do not run `uv pip install -e .` — it falls back to setuptools and creates an `src/rote.egg-info/` that has nothing to do with the code.

Verified dependency set (`pyproject.toml`): numpy ≥ 1.26, pandas ≥ 2.1, scipy ≥ 1.11, matplotlib ≥ 3.8, seaborn ≥ 0.13, pyyaml ≥ 6.0, cvxpy ≥ 1.4, statsmodels ≥ 0.14, streamlit ≥ 1.37; dev extras add pytest ≥ 8.0, pytest-cov ≥ 5.0, ruff ≥ 0.5. The environment these results were produced in: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, matplotlib 3.11.2, seaborn 0.13.2, PyYAML 6.0.3, cvxpy 1.9.3 (OSQP available), statsmodels 0.15.0, streamlit 1.65.0, pytest 9.1.1, ruff 0.16.10. Of these, `scipy`, `seaborn` and `statsmodels` are declared for the later phases but not yet imported anywhere; `seaborn` is currently used only for its matplotlib style name. `streamlit` is needed only to run the UI (`app.py`); the CLI and the test suite do not import it.

## Setup

```bash
git clone <this repository> rote && cd rote
uv venv .venv
uv pip install -r pyproject.toml --extra dev      # deps only, no build of this project
export ROTE_DATA_ROOT="$HOME/data/FI-2010"        # see "The dataset" below
```

Equivalent without `uv` — plain `pip` cannot read a `pyproject.toml` as a requirements file, so the dependencies are named explicitly:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install "numpy>=1.26" "pandas>=2.1" "scipy>=1.11" "matplotlib>=3.8" \
            "seaborn>=0.13" "pyyaml>=6.0" "cvxpy>=1.4" "statsmodels>=0.14" \
            "streamlit>=1.37" "pytest>=8.0" "pytest-cov>=5.0" "ruff>=0.5"
```

Sanity check — the QP path needs a conic solver:

```bash
uv run --no-sync python -c "import numpy, cvxpy; assert 'OSQP' in cvxpy.installed_solvers(); print('ok')"
```

`uv run --no-sync` reuses `.venv` without re-resolving the environment. Plain `.venv/bin/python …` or an activated venv works identically.

## The dataset

**FI-2010 is not redistributed here and must be obtained from its distributors** (Nasdaq Nordic ITCH via the FI-2010 benchmark release; its licence is separate from this repository's MIT licence). The credible sources are recorded in `src/data/download.py` (`CREDIBLE_SOURCES`):

- `https://etsin.fairdata.fi/dataset/6aa3ad3c-15ad-421f-bbd0-c44c2a0f66c2`
- `https://github.com/VPeterV/fi2010`

Place the four **DecPre / NoAuction** files in one directory — `$ROTE_DATA_ROOT`, or `data/raw/FI-2010/`, or `data/FI-2010/` inside the checkout:

| File | Trading days | Bytes | SHA-256 |
| :--- | :--- | ---: | :--- |
| `Train_Dst_NoAuction_DecPre_CF_7.txt` | 1–7 | 607,324,298 | `11af4bbcf26f08a43a436c43619bdf772f552870d54a3b06de7b5344957279fc` |
| `Test_Dst_NoAuction_DecPre_CF_7.txt` | 8 | 132,259,850 | `1acd92e13df8f499aa9475729e1d54455db1ab37894616d0c582cdd012351273` |
| `Test_Dst_NoAuction_DecPre_CF_8.txt` | 9 | 124,378,346 | `950559383a3cf823fd373e6573434cc00c94b9bceac77fe5ee9f1adb38e1abb2` |
| `Test_Dst_NoAuction_DecPre_CF_9.txt` | 10 (reserve) | 76,138,106 | `c09785b0aed0825ad566f8fe33a3b7d8c3fbb8993856d162976cb4e1c410aca0` |

Verify before running anything:

```bash
cd "$ROTE_DATA_ROOT" && sha256sum -c <<'EOF'
11af4bbcf26f08a43a436c43619bdf772f552870d54a3b06de7b5344957279fc  Train_Dst_NoAuction_DecPre_CF_7.txt
1acd92e13df8f499aa9475729e1d54455db1ab37894616d0c582cdd012351273  Test_Dst_NoAuction_DecPre_CF_7.txt
950559383a3cf823fd373e6573434cc00c94b9bceac77fe5ee9f1adb38e1abb2  Test_Dst_NoAuction_DecPre_CF_8.txt
c09785b0aed0825ad566f8fe33a3b7d8c3fbb8993856d162976cb4e1c410aca0  Test_Dst_NoAuction_DecPre_CF_9.txt
EOF
```

Two facts about the files that the rest of the code depends on:

- Each file is **149 rows × N columns**: 144 feature rows plus 5 label rows, transposed. The loader parses the file row-wise but keeps only the 144 feature rows — labels are never used (`dataset.labels: forbidden`). Prices are stored ×10⁻² (i.e. `price_euros = stored × 100`, `k = 6`), volumes ×10⁻⁶ (`vol_shares = stored × 10⁶`). The first 40 feature rows are 10 levels × (ask price, ask volume, bid price, bid volume).
- `Train_Dst_NoAuction_DecPre_CF_7.txt` holds days 1–7 concatenated, so **day boundaries are not recorded in the files**. Splits are day blocks reconstructed by proportion (`configs/splits.yaml`), and the audit recovers the five stock blocks from mid-price discontinuities (check A2).

Dataset files are never committed. `.gitignore` is the only guard — verify it is in force before staging anything:

```bash
git check-ignore -v data/raw/Train_Dst_NoAuction_DecPre_CF_7.txt   # must print a .gitignore rule
```

## Reproducing the results

Run from the repository root, in this order. Timings are from a 20-core x86-64 Linux box; the audit is single-pass and not parallelised.

### 1. Dataset audit — regenerates `data/README.md` and all six figures

```bash
uv run --no-sync python run_experiment.py audit
```

Reads the train file plus the two test files for days 8–9, runs checks A0–A8, writes `data/README.md`, and writes the figures listed below. ~7 s, peak RSS ≈ 0.7 GB. Exit status is non-zero if the audit does not complete, and **a failed audit does not overwrite the report** — the last good one stays until a run completes. The run prints one line per check, e.g.:

```text
Audit completed: complete. Report written to data/README.md
  [A0] pass: Found 4 files (1 train, 3 test), all DecPre NoAuction format with 149 features/labels per event.
  [A1] pass: DecPre variant confirmed. Global exponent k=6. …
```

The figures to compare against, all of which are deterministic given the four input files: **A2** five stock blocks (Kesko, Outokumpu, Sampo, Rautaruukki, Wärtsilä, in that order); **A5** σ_min 1.4–3.9 bps; **A6** 451 calibration / 178 validation / 261 test windows. A stock-major file layout is what makes the day blocks proportional — see `docs/decision_log.md`.

The report is overwritten in place, so `git diff data/README.md` is the review step after any change to the audit code. Checks A0, A1, A2 and A4 are **blocking** (`audit.blocking` in the config): no optimization code is written until they pass. The audit loads the train file and the two day 8–9 test files; day 10 is the reserve split and is not read.

### 2. Freeze the splits — regenerates `configs/splits.yaml`

```bash
uv run --no-sync python run_experiment.py freeze-splits   # {'status': 'written', 'path': 'configs/splits.yaml'}
```

Day blocks: calibration days 1–5, validation 6–7, test 8–9, day 10 reserve, purge gap 400 rows, applied within stock segments. Re-running is idempotent — the file is reproduced byte-for-byte, which is what makes the G2 tag meaningful. The freeze is already recorded as the `splits-frozen` tag on the commit that produced this file; only re-tag if you are redoing the freeze on a different commit (`git tag -f splits-frozen` would move it).

### 3. Figures only

```bash
uv run --no-sync python run_experiment.py figures
```

~5 s. Writes the same six figures as step 1 without touching `data/README.md`. Deterministic: repeated runs are bit-identical PNGs (verified by comparing SHA-256 of the outputs).

### 4. The exploratory frontier — the full run

```bash
uv run --no-sync python run_experiment.py full            # calibration + validation
uv run --no-sync python run_experiment.py full --test --confirm   # confirmatory; one-shot
```

~148 s. Calibrates η₀ per stock, builds A6 windows, evaluates every rung of the PROPOSAL.md section 6 ladder over `omega_grid`, simulates each under section 7.1, decomposes with section 8.2 and aggregates across windows. Writes `results/tables/calibration.json` and, under `results/runs/<run_id>/`, `windows_<split>.csv`, `summary_<split>.csv`, `matched_risk_<split>.csv` and `run_manifest.json`.

Useful flags: `--splits calibration validation`, `--theta 1.0`, `--omega 0.4`, `--rungs rote_static ac_capped`, `--limit 20` (smoke-test a subset), `--run-id NAME`.

**The default run never touches the test days.** Day 8–9 require `--test --confirm`, which prints the manifest that would be written and asks for confirmation; `run_manifest.json` records `test_split_consumed: true` for that run and `false` otherwise. Reproducibility rests on the manifest's `config_sha` — the exploratory run recorded `c978c02b6c472aff`, so a rerun that reports a different hash is not the same experiment.

The grid is on the **urgency** `omega`, not on `lambda`: section 5.2 fixes `kappa^2 = lambda~*sigma~^2/(eta~0*theta) = 2(cosh omega - 1)` as the one quantity that determines the schedule, and `lambda~` needed to reach even `omega = 0.4` is `2.0e4`–`1.4e6` on these stocks (up to `6.9e6` at `theta=5`), not the `0.1` an absolute grid would suggest. See `CHANGELOG.md` for why the old grid made every rung return TWAP(T) exactly.

### 5. Checks

```bash
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest -m "not slow"
uv run --no-sync pytest -m "T1 or T2 or T3 or T4 or T5 or T6 or T7 or T8 or T9 or T10 or T11 or T12 or T13 or T14"
```

`T1`–`T14` are the correctness standards of `PROPOSAL.md` section 9, one pytest marker each (`--strict-markers` is on). Run a single one with `pytest -m T8`. **T8 is the look-ahead test** (arrival-frozen sweep) and is the one that catches a schedule priced with information from its own future — but it still does not exist as its own standard: `tests/test_causality.py` is an `assert True` placeholder. Its property is asserted inside T9 instead (`test_snapshots_past_the_horizon_are_never_read`), and not hypothetically: the shipped simulator priced the terminal sweep at index `T`, one snapshot past the horizon, until 2026-10-05. Of the gate, **9 of 14 standards assert** — T1–T4 (`tests/test_optimizer.py`: the λ→0 TWAP limit, front-loading in λ, the closed-form `sinh` match), T9 (`tests/test_simulator.py`, 11 tests), T10 (`tests/test_walk_book.py`, 10 tests including the section 2.1 worked example), T12 (`tests/test_conservation.py`, 85 parameterised cases of the section 8.2 identity) T13 (`tests/test_units.py` plus 11 simulator scale-invariance tests) and T14 (`tests/test_baselines.py`: AC-capped is bit-identical to AC when the cap is slack and differs by tens of bps when it binds — the property that was vacuous while every rung was capped). The remaining five (T5, T6, T7, T8, T11) are placeholders — 16 `assert True` in total across `tests/test_t.py`, `test_other.py` and `test_causality.py` — so treat a green gate as plumbing, not as proof. All five commands above pass.

### Not yet runnable

The confirmatory experiments E0–E5. `full` covers the exploratory splits only; the test days need `full --test --confirm`, and that run is deliberately gated rather than convenient. There is also no MPC (PROPOSAL.md rung 5), no drift ablation, and `frontier` only points at the `matched_risk_*.csv` artifacts rather than plotting them.

## Outputs

Everything a run writes, and whether it is tracked:

| Path | Written by | Tracked |
| :--- | :--- | :--- |
| `data/README.md` | `audit` | yes — the A0–A8 report |
| `configs/splits.yaml` | `freeze-splits` | yes — frozen at G2 |
| `results/figures/fig1_lob_snapshot.png` | `audit`, `figures` | yes |
| `results/figures/fig2_stock_boundaries_price_series.png` | `audit`, `figures` | yes |
| `results/figures/fig3_depth_distribution_order_realism.png` | `audit`, `figures` | yes |
| `results/figures/fig4_spread_and_imbalance.png` | `audit`, `figures` | yes |
| `results/figures/fig5_volatility_and_sigma_floor.png` | `audit`, `figures` | yes |
| `results/figures/fig6_book_walk_cost_convexity.png` | `audit`, `figures` | yes |
| `results/tables/calibration.json` | `calibrate`, `full` | yes — per-stock η₀ and `D_bar`, with their units |
| `results/runs/<run_id>/windows_<split>.csv` | `full` | yes — one row per (window, rung, θ, ω) |
| `results/runs/<run_id>/summary_<split>.csv` | `full` | yes — per-cell means plus cross-window realised risk |
| `results/runs/<run_id>/matched_risk_<split>.csv` | `full` | yes — each policy against the reference risk, never against a λ |
| `results/runs/<run_id>/run_manifest.json` | `full` | yes — records `config_sha`, `test_split_consumed` and the solver used |
| `results/runs/**/cache/` | experiment runs | **no** — bulk intermediates, ignored |

Figures are 300 DPI and captioned in event time. Figures and tables are the evidence behind every claim, so they are deliberately not ignored; caches are.

## Configuration

`configs/experiment.yaml` is the source of truth for every experiment number — order sizes, horizons, caps, `λ`, `φ`, periods, seed. No module carries a literal for any of them. The config is hashed canonically (`src/config.py`); the hash travels with every result file so a number can always be traced to the configuration that produced it:

```bash
uv run --no-sync python -c "import sys; sys.path.insert(0,'src'); from config import load, sha256; print(sha256(load()))"
```

Before the confirmatory run the config is frozen and tagged `config-frozen`; any later change is labelled *post hoc* in `docs/decision_log.md`. Post-hoc edits are legitimate — unlabelled ones are not.

Where the dataset is looked up, in order: `dataset.root` in the config → `$ROTE_DATA_ROOT` → `data/raw/FI-2010/` → `data/FI-2010/`. Set `dataset.root` if you want the path pinned in the repository rather than the environment; `dataset.source` is a provenance note only and no code reads it.

## Determinism

- The audit and the figures are deterministic: no sampling, no RNG, fixed input file. Re-running produces identical files, so a diff means a real change.
- The bootstrap seed for the experiments is `run.bootstrap_seed: 20260101` and is **still unused** — the evaluation module landed, but the paired bootstrap, Holm family and isotonic frontier of section 8.3 have not, so no seed is consumed.
- Every experiment run records `config_sha` (a hash of the resolved config) and `test_split_consumed` in `results/runs/<run_id>/run_manifest.json`. Reproduce a run by checking that hash, not by trusting the command line: the exploratory run pinned `c978c02b6c472aff`.
- Nothing is wall-clock or machine dependent, except floating-point association in `numpy`/`cvxpy` — a different BLAS or solver version can move the last digits of a QP solution, and solver choice (`OSQP`, `CLARABEL`, `SCS` are all installed) changes them more.

## Troubleshooting

| Symptom | Cause and fix |
| :--- | :--- |
| `FileNotFoundError: no FI-2010 data directory found; tried: …` | `$ROTE_DATA_ROOT` unset or wrong. `export ROTE_DATA_ROOT=/path/to/dir` containing the four `.txt` files, or put them in `data/raw/FI-2010/`. |
| `FileNotFoundError: FI-2010 file not found` / `expected 149 rows …, got N` | Wrong or truncated file. Check the SHA-256 table above. |
| `Audit completed: error` with an `error:` line | The command prints the exception and exits non-zero; `data/README.md` is **left untouched**, so a failed run can never destroy the last good report. The usual cause is `$ROTE_DATA_ROOT` unset or a non-FI-2010 file — the `error:` line names it. |
| `ImportError` / `ModuleNotFoundError: cvxpy` | Dependencies not installed. Re-run `uv pip install -r pyproject.toml --extra dev` **without** `-e .`; verify with the sanity check above. |
| `ModuleNotFoundError: data` / `config` when running a module directly | Run through `run_experiment.py` or pytest, which put `src/` on the path, or `PYTHONPATH=src`. |
| Figures land somewhere unexpected | `results/figures/` is relative to the **current working directory**. Run the commands from the repository root, or the PNGs appear under `$PWD/results/figures/`. |
| `ruff check .` reports findings | Should not happen — `ruff check .` and `ruff format --check .` are both clean on the verified tree. Fix either with `uv run --no-sync ruff format <file>`. |

## Layout

```text
README.md       this file
PROPOSAL.md     the authoritative specification (design, gates, hypotheses)
CHANGELOG.md    corrections folded into PROPOSAL.md
DECISIONS.md    retired claims, so they are not re-derived
docs/ROADMAP.md the execution plan: phases, gates, cut order
AGENTS.md       engineering conventions for agents and contributors
opencode.json   agent permissions: read/edit of data/raw/ is denied
run_experiment.py  CLI: audit, freeze-splits, calibrate, full, frontier, check-formulation, figures
configs/        experiment.yaml (every constant, frozen at G10), splits.yaml (frozen at G2)
src/            config.py plus the packages that exist: data · features · cost · optimize ·
                simulator · baselines · evaluation. Notable modules: data/windows.py,
                baselines/ladder.py, optimize/solve.py, evaluation/{metrics,experiment}.py
data/README.md  the A0–A8 audit report; data/raw/ is git-ignored
tests/          T1–T14 correctness standards, one pytest marker each
results/        tables, figures, run manifests — the evidence
docs/           decision_log.md (dated decisions), ROADMAP.md (execution plan)
app.py          Streamlit UI (PROPOSAL.md section 1.1) — 3 of the 5 panels
report/         report and slides (empty; nothing writes it yet)
```

`notebooks/rote_analysis.ipynb` is specified in `PROPOSAL.md` section 1.1 and does **not** exist yet; the notebook UI is unbuilt.

Dependency direction is `evaluation → simulator → baselines → optimize → cost → features → data`; nothing imports `evaluation/` (enforced by `tests/test_layers.py`).

## User interface (course-guideline requirement)

The FE and OR course guidelines require an interactive tool (`PROPOSAL.md` section 1.1, Tier 1). It is **partly built**: `app.py` serves three of the five panels — dataset loader, descriptive statistics on demand, and an optimisation menu — and launches with:

```bash
uv run --no-sync streamlit run app.py       # web UI — works today
# jupyter lab notebooks/rote_analysis.ipynb  # notebook UI — NOT built, the file does not exist
```

Five panels are required: dataset loader · descriptive statistics on demand · optimisation menu · baseline comparison · results. **Baseline comparison and results are missing**, and nothing tests the UI. The optimisation menu exposes the two guaranteed Tier-1 models — ROTE-Static QP and Almgren–Chriss — with ROTE-MPC as the optional third, but the Almgren–Chriss option is currently the same QP with the capacity caps disabled and the spread held constant, so it is a labelled comparator rather than a true AC implementation. The FE analysis menu (Analyses A and B; Analysis C is the optional third) is not wired up. `app.py` is a thin wrapper over `src/`; the CLI remains the reproducibility path.

## Licence

MIT (see `LICENSE`). The dataset is licensed separately by its distributors, and the source URLs are listed above. FI-2010 data files are never committed to this repository.