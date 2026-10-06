# AGENTS.md

ROTE = Risk-Aware Optimal Trade Execution on FI-2010. Research code, not a product.

## Authority order

`PROPOSAL.md` (the spec) → this file. `PROPOSAL.md` section 9 defines the T1–T17
correctness standards; section 5.4 defines the QP. Trust the tree over both docs — several
described directories do not exist.

## Environment

```bash
uv venv .venv && uv pip install -r pyproject.toml --extra dev
```

- Dataset files belong in `data/raw/FI-2010/`, which is the first repository-local fallback.
  `ROTE_DATA_ROOT` is an optional override for a dataset stored elsewhere. Missing-data tests
  skip with an explicit setup message.
- There is **no build backend**. Never `uv pip install -e .` / `pip install .` — it silently
  falls back to setuptools and drops a `src/rote.egg-info/`. Deps are declared in
  `pyproject.toml` and installed as a requirements file.
- `uv run --no-sync` reuses `.venv` without re-resolving. Python 3.12, cvxpy solvers available:
  CLARABEL, HIGHS, OSQP, SCIPY, SCS.
- There is intentionally no `uv.lock`; install from `pyproject.toml` with `uv pip install`.
- **Run everything from the repo root.** Output paths (`results/`, `data/`, `report/`) are CWD-relative.

## Commands

```bash
uv run --no-sync ruff check . && uv run --no-sync ruff format --check . && uv run --no-sync pytest
uv run --no-sync pytest tests/test_models.py::test_name      # one test
uv run --no-sync pytest -m T8                                 # one correctness standard
uv run --no-sync python run_experiment.py audit               # rewrites data/README.md
uv run --no-sync python run_experiment.py freeze-splits       # rewrites configs/splits.yaml
uv run --no-sync python run_experiment.py calibrate
uv run --no-sync python run_experiment.py figures
uv run --no-sync python run_experiment.py check-formulation  # just pytest tests/test_optimizer.py -v
uv run --no-sync python -m src.reports.generate_report
uv run --no-sync streamlit run app.py
```

CLI notes:

- `full` runs the audit, calibration, figures, and report pipeline. Add `--test --confirm` to
  select the held-out day 8 report; the confirmation flag is required for that mode.
- `audit` only overwrites `data/README.md` on success; a failed audit preserves the last good
  report (`tests/test_audit.py::test_failed_audit_preserves_existing_report`).
- `freeze-splits` regenerates `configs/splits.yaml`, which is covered by the only tag in the
  repo (`splits-frozen`). Don't casually re-run it.
- `calibrate` prints η₀ and persists the estimates in `results/tables/calibration.json`.
- `audit` / `calibrate` / `figures` parse the full 607 MB train file (~3 s each); they are the
  slow part of the suite. The `slow` marker is declared but unused, so `-m "not slow"` is a no-op.

## Two import roots

`pyproject.toml` sets `pythonpath = [".", "src"]`, so under pytest *both* styles resolve:

- `src.*` — `app.py`, `src/models/`, `src/reports/`, `src/sim/`, `src/stats/`, `src/utils/`
- bare top-level — `data`, `config`, `cost`, `optimize` — used by `run_experiment.py`,
  `src/data/`, `tests/test_optimizer.py`, `tests/test_units.py`, `tests/test_walk_book.py`

`run_experiment.py` inserts only `src/` at runtime. So a module reachable from the CLI must use
bare imports, and `app.py` / `src/reports/` need the repo root. The tree is already mixed
(`src/cost/quadratic.py` uses `from cost.walk_book import ...`, `src/impact/impact.py` uses
`from src.cost.walk_book import ...`) — match whichever form the target's own siblings use.

## Duplicated modules — pick deliberately

| Need | Use | Not |
|---|---|---|
| Loader for CLI/audit | `src/data/loader.py` — input validation, config-aware `dataset.file`, `period_log_returns`, `sigma_min_floor` | `src/loader/loader.py` — drops validation, ignores `dataset.file` |
| Loader for UI/reports | `src/loader/loader.py` — adds `load_day`, `load_test_lob` | |
| η₀ calibration | `src/cost/quadratic.py` → `float` (what `run_experiment.py` uses) | `src/impact/impact.py` → `dict` (quad/lin/sqrt + R²), the one `src/impact/__init__.py` re-exports |
| Simulator | `src/sim/simulate.py::simulate` → `CostReport` | — |

`src/utils/` remains a namespace package; obsolete duplicate implementations were removed.

## Dataset invariants

- Files are `(149, N)` = 144 features + 5 labels, transposed. **Labels are forbidden**
  (`dataset.labels: forbidden`) — the loader slices `rows[:144]`. Never widen that.
- Scale: `k_decpre = 6` globally. `price_euros = stored × 100`, `vol_shares = stored × 10^6`.
  LOB = first 40 feature columns, 10 levels × interleaved (ask_p, ask_v, bid_p, bid_v).
- The train file is **stock-major**: 5 contiguous blocks spanning days 1–7.
  `segment_boundaries` returns **edges** `[0, …, N]` (`len(edges) - 1` = stock count), never raw
  jump indices. Passing jumps silently drops the first stock and the last segment.
  Locked by `tests/test_loader.py::test_segment_boundaries_are_edges_not_jumps`.
- **`lob["S"]` is the FULL spread `Pa1 - Pb1`, never the half-spread** (pooled mean 16.70 bps
  full, 8.35 half). `walk_book_buy` prices the half-spread against the *period-t* mid
  (`p1 - mid_t`). T12's `components == Spend - Q·M0` identity is satisfied by any split, so it
  cannot catch a mis-split — compare `half_spread_bps` against the raw arrays instead.
- `sigma_min_floor` = 10th percentile of **|returns|**, so the volatility floor is never negative.
- Days 1–7 are carved out of the train file assuming **uniform day lengths** (no timestamps, no
  `train_6` exists). Days 8/9/10 map to `Test*CF_{day-1}.txt`. `configs/splits.yaml` freezes
  calibration = 1–5, validation = 6–7, test = 8–9, reserve = 10.
- `load_day` parses source files on demand. The setup command and processed cache are the
  preferred path for interactive use.
- `.gitignore`'s `/data/raw/*` is the **only** guard against committing the dataset. Verify with
  `git check-ignore -v data/raw/<file>` before any `git add`.

## Simulation rules

- The terminal sweep must be priced at the **last snapshot inside the horizon** (index `T-1`),
  never at index `T`, and no snapshot after the horizon may be read. Behavioral tests assert this.
- The sweep deducts `F_T + fill_T` — no resilience recovery on period T's own fill. `phi = 1`
  is naive replay **inside the horizon only**, not end to end.
- No completion constraint: `u = y_{T+1}` is a decision variable chosen by the program, never
  forced into the final period.

## Testing quirks

- `--strict-markers` is on, and `T1`–`T17` plus `A1`/`A4` are all declared in `pyproject.toml`.
  `T15`–`T17` are declared but **carried by no test** (`pytest -m T15` collects 0 tests).
- Correctness markers point to behavioral assertions; cite the asserting test, never the marker
  alone.
- Real assertions: `test_loader.py`, `test_audit.py`, `test_walk_book.py` (T10), `test_units.py`
  (T13), `test_models.py`, `test_baselines.py`, `test_visualizations.py`, `test_optimizer.py`,
  `test_figures.py`, `test_config.py`, `test_splits.py`, `test_run_experiment.py`, `test_layers.py`,
  `test_e2e.py`.
- `tests/conftest.py` supplies `synthetic_lob` (hand-built 300×10 book, no dataset) and
  `tmp_config` (writes into `tmp_path`). Model/visualization tests need only `synthetic_lob`;
  the loader/audit/CLI tests read the real dataset.
- `tests/test_layers.py` AST-scans `src/*` and fails if anything imports `evaluation`; keep this
  layer rule as the evaluation package is extended.

## Stale tracked artifacts

- `data/README.md` and the figures are generated evidence artifacts. Regenerate them only when
  source data or experiment configuration changes.
- Keep the README tree synchronized with the actual source packages.
- Generated analysis and planning registers are not retained in `docs/`.

## Config as source of truth

Every experiment number lives in `configs/experiment.yaml` — no literals for order size, horizon,
caps, λ, φ or period lengths inside modules. `src/config.py::load` requires the `dataset`,
`audit` and `period` sections and injects `_sha256` / `_proposal_sha256`.

- The AC/ROTE-Static grid is `omega_grid`, **not** an absolute `lambda_grid`.
  `kappa² = lambda~·sigma~²/(eta~0·theta) = 2(cosh ω − 1)` is the single quantity that sets the
  schedule; `eta~0` scales as 1/M₀ and `sigma~²` as 1/M₀², so a fixed λ means a different urgency
  per stock and collapses every model to TWAP.
- The section 5.4 program is badly conditioned: at dimensionless scale (`psi = 0.5`) OSQP
  defaults return a solution up to 75 shares off TWAP at `lambda = 0`, where T1 requires TWAP. At
  the raw scale `psi = 100.0` that `tests/test_optimizer.py` uses, defaults are fine — so a green
  test does not prove the program is safe. Do not loosen solver tolerances to raise the solve rate.
- bps ×10^4 has exactly one home: `src/cost/units.py`.

## Conventions

- Ruff: line-length 100, `target-version = "py311"`, `select = ["E","F","I","UP","B","SIM"]`,
  `extend-exclude = ["*.md"]`. New modules start with `from __future__ import annotations`.
- Section references in prose: `PROPOSAL.md section N`, never abbreviated. Namespaces
  (R/T/G/A/E/H/S/Q) are fixed.
- Model contract (README section 1): `load_day` → `Order` → `model.solve` → `Schedule` →
  `simulate` → `CostReport`. `Order`/`Schedule`/`CostReport` are frozen dataclasses in
  `src/utils/contracts.py`; `sum(Schedule.shares) == Q` is the invariant.
- No comments unless explicitly asked.
- Do not `git add` / commit unless asked. Commit style is `type: summary` with
  `feat fix data docs test exp chore`; experiment runs are separate from source commits.