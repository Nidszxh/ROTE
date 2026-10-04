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
| Evaluation | paired moving-block bootstrap within stock-day series, one Holm family over H1, H2, H3(a), H3(b), and matched risk by an isotonic validation frontier |

## Status

The repository is mid-build. What exists, what it produces, and what it does not yet do:

| Area | State |
| :--- | :--- |
| Dataset audit A0–A8 | **works** — `run_experiment.py audit` regenerates `data/README.md` and the six audit figures; A0–A6 and A8 all `PASS`, A7 `N/A` |
| Microstructure figures | **works** — `run_experiment.py figures` |
| Splits (G2) | **works** — `run_experiment.py freeze-splits` regenerates `configs/splits.yaml` byte-identically; tagged `splits-frozen` |
| Calibration, risk–cost frontier, `check-formulation`, the full run | **stubs** — the subcommands print a placeholder and write nothing |
| QP, simulator, baselines, evaluation | partially scaffolded (`src/optimize/qp_schedule.py` raises `NotImplementedError`) |
| UI (`app.py`, `notebooks/`) | **not built** — specified in `PROPOSAL.md` section 1.1 |
| Test suite | 68 tests pass (`pytest -m "not slow"`), including the T1–T14 gate — but most T-markers sit on placeholder assertions, so a green gate is not yet evidence of correctness |
| Lint / format | `ruff check .` and `ruff format --check .` clean |
| Confirmatory results (E0–E5) | **not run.** The single test-set run happens once, from a configuration frozen and tagged `config-frozen`; `splits-frozen` exists, `config-frozen` does not |

So the only results a clean checkout can reproduce today are the **Phase-1 data audit**: `data/README.md`, the six figures in `results/figures/`, and `configs/splits.yaml`. `results/tables/` and `results/runs/` are wired up but empty.

## Requirements

- Python **≥ 3.11** (developed and verified on 3.12).
- ~1 GB free disk for the dataset (897 MiB) and < 1 GB RAM for the audit commands (measured peak RSS ≈ 0.7 GB).
- [`uv`](https://docs.astral.sh/uv/) or `pip` + `venv`. Nothing else.

There is **no packaging step**. The project is not installable and nothing from the repository is installed: `pyproject.toml` declares dependencies and tool configuration only, with no build backend. `run_experiment.py` puts `src/` on `sys.path` itself, and `pyproject.toml` sets `pythonpath = ["src"]` for pytest. Do not run `uv pip install -e .` — it falls back to setuptools and creates an `src/rote.egg-info/` that has nothing to do with the code.

Verified dependency set (`pyproject.toml`): numpy ≥ 1.26, pandas ≥ 2.1, scipy ≥ 1.11, matplotlib ≥ 3.8, seaborn ≥ 0.13, pyyaml ≥ 6.0, cvxpy ≥ 1.4, statsmodels ≥ 0.14; dev extras add pytest ≥ 8.0, pytest-cov ≥ 5.0, ruff ≥ 0.5. The environment these results were produced in: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, matplotlib 3.11.2, seaborn 0.13.2, PyYAML 6.0.3, cvxpy 1.9.3 (OSQP available), statsmodels 0.15.0, pytest 9.1.1, ruff 0.16.10.

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
            "pytest>=8.0" "pytest-cov>=5.0" "ruff>=0.5"
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

### 4. Checks

```bash
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest -m "not slow"
uv run --no-sync pytest -m "T1 or T2 or T3 or T4 or T5 or T6 or T7 or T8 or T9 or T10 or T11 or T12 or T13 or T14"
```

`T1`–`T14` are the correctness standards of `PROPOSAL.md` section 9, one pytest marker each (`--strict-markers` is on). Run a single one with `pytest -m T8`. **T8 is the look-ahead test** (arrival-frozen sweep) and is the one that catches a schedule priced with information from its own future. All four commands above are clean. The T-markers currently sit mostly on placeholder assertions, so treat a green gate as plumbing, not as proof: the substantive assertions land with the model implementation.

### Not yet runnable

`calibrate`, `frontier`, `check-formulation` and the bare `python run_experiment.py` (full run) print a placeholder. There is no `results/tables/` content to reproduce, and the confirmatory experiments E0–E5 have not been executed.

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
| `results/tables/` | experiment runs | yes — empty today |
| `results/runs/<run_id>/run_manifest.json` | experiment runs | yes — records config hash and commit |
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
- The bootstrap seed for the experiments is `run.bootstrap_seed: 20260101` and is unused until the evaluation module lands.
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
| `ruff check .` reports findings | Should not happen — both `ruff check .` and `ruff format --check .` are clean. If they are not, the working tree differs from the verified state. |

## Layout

```text
README.md       this file
PROPOSAL.md     the authoritative specification (design, gates, hypotheses)
CHANGELOG.md    corrections folded into PROPOSAL.md
DECISIONS.md    retired claims, so they are not re-derived
AGENTS.md       engineering conventions for agents and contributors
run_experiment.py  CLI: audit, freeze-splits, calibrate, frontier, check-formulation, figures
configs/        experiment.yaml (every constant, frozen at G10), splits.yaml (frozen at G2)
src/            config.py and data · cost · optimize · baselines · simulator · evaluation
data/README.md  the A0–A8 audit report; data/raw/ is git-ignored
tests/          T1–T14 correctness standards, one pytest marker each
results/        tables, figures, run manifests — the evidence
docs/           decision_log.md
notebooks/      rote_analysis.ipynb — notebook UI (PROPOSAL.md section 1.1, not built)
app.py          Streamlit UI (PROPOSAL.md section 1.1, not built)
report/         report and slides
```

Dependency direction is `evaluation → simulator → baselines → optimize → cost → features → data`; nothing imports `evaluation/` (enforced by `tests/test_layers.py`).

## User interface (course-guideline requirement)

The FE and OR course guidelines require an interactive tool (`PROPOSAL.md` section 1.1, Tier 1). It is specified but **not yet built**; when complete it will be launched with:

```bash
streamlit run app.py                        # web UI
jupyter lab notebooks/rote_analysis.ipynb   # notebook UI (Colab-compatible)
```

Five panels: dataset loader · descriptive statistics on demand · optimisation menu · baseline comparison · results. The optimisation menu exposes **two guaranteed Tier-1 models** — ROTE-Static QP and Almgren–Chriss — with ROTE-MPC as the optional third. The FE analysis menu offers optimal execution (A), strategy comparison (B) and the risk–cost frontier (C). Both interfaces are thin wrappers over `src/`; the CLI above remains the reproducibility path.

## Licence

MIT (see `LICENSE`). The dataset is licensed separately by its distributors, and the source URLs are listed above. FI-2010 data files are never committed to this repository.