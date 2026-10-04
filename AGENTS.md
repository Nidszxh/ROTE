# AGENTS.md

## Repo state

- **ROTE** = Risk-Aware Optimal Trade Execution. PROPOSAL.md is authoritative; if it conflicts with any file, the other is corrected, not PROPOSAL.md.
- Implementation at repo root: `src/` (flat subpackages), `run_experiment.py` at root. No packaging/install from the project itself.
- Dataset: FI-2010 (DecPre, NoAuction) stored outside repo at `$ROTE_DATA_ROOT` (usually `~/data/FI-2010`). Data files are **never** committed.
- Authority order: PROPOSAL.md → AGENTS.md → CHANGELOG.md → DECISIONS.md, with dated decisions in `docs/decision_log.md`.

## Environment

```bash
# Environment
export ROTE_DATA_ROOT="$HOME/data/FI-2010"

# Setup (dependencies only — the project itself is never installed)
uv venv .venv && uv pip install -r pyproject.toml --extra dev

# Verify
uv run --no-sync python -c "import numpy,cvxpy; assert 'OSQP' in cvxpy.installed_solvers()"
```

`uv run --no-sync` = use `.venv` without re-resolving. `pyproject.toml` uses `pythonpath = ["src"]`; `run_experiment.py` also prepends `src/`. There is no build backend: never `uv pip install -e .` (it falls back to setuptools and drops a `src/rote.egg-info/`). Plain `pip` cannot read `pyproject.toml` as requirements — README.md lists the dependencies explicitly.

## Key commands

```bash
# Checks (run before experiments)
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest -m "not slow"
uv run --no-sync python run_experiment.py check-formulation

# T1–T14 gate (all correctness standards)
uv run --no-sync pytest -m "T1 or T2 or T3 or T4 or T5 or T6 or T7 or T8 or T9 or T10 or T11 or T12 or T13 or T14"

# Dataset/audit
uv run --no-sync python run_experiment.py audit
uv run --no-sync python run_experiment.py freeze-splits  # produces configs/splits.yaml, tag splits-frozen after

# Calibration/frontier (stubs until the model lands; no flags yet)
uv run --no-sync python run_experiment.py calibrate
uv run --no-sync python run_experiment.py frontier

# Full run (single acceptance command per spec)
uv run --no-sync python run_experiment.py
uv run --no-sync python run_experiment.py figures

# UI (Tier 1, PROPOSAL.md 1.1 — five panels, two guaranteed models: Static QP + Almgren–Chriss; not built yet)
uv run --no-sync streamlit run app.py
```

Run a single test: `uv run --no-sync pytest -m T8` (or `pytest tests/test_foo.py::test_bar`). T1–T14 have individual markers; `--strict-markers` is enabled.

## Architecture & boundaries

Dependency direction: `evaluation → simulator → baselines → optimize → cost → features → data`. **Nothing may import `evaluation/`** (enforced by `tests/test_layers.py`).

Packages (flat imports): `src/config.py`, `src/data/`, `src/features/`, `src/cost/`, `src/optimize/`, `src/baselines/`, `src/simulator/`, `src/evaluation/`. Today only `data/`, `cost/` and `optimize/` exist; the rest land with their phases (PROPOSAL.md section 12).

Entry: `run_experiment.py` (subcommands: `audit`, `freeze-splits`, `calibrate`, `frontier`, `check-formulation`, `figures`, default full). `check-formulation` will validate PROPOSAL.md section 5.4 against `optimize/qp_schedule.py`; it is a stub until the QP lands. A failed `audit` exits non-zero and leaves `data/README.md` untouched.

UI: `app.py` (Streamlit) and `notebooks/rote_analysis.ipynb` are thin wrappers over `src/` (PROPOSAL.md 1.1). They may import anything except `evaluation/`; nothing in `src/` imports the UI.

## Dataset (FI-2010)

- Location: `$ROTE_DATA_ROOT` (set in env). DecPre, NoAuction. Files are (149, N) = 144 features + 5 labels, transposed.
- Scale: k_decpre=6 (global). price_euros = stored×100, vol_shares = stored×10^6. Reconstructed from first 40 feature rows (10 levels × (ask_p, ask_v, bid_p, bid_v)).
- Layout: the train file is **stock-major** — 5 contiguous stock blocks, each spanning days 1–7. `loader.segment_boundaries` returns segment **edges** (`[0, …, N]`, so `len(edges) − 1` = stock count), never raw jump indices; `loader.sigma_min_floor` takes a percentile of **|returns|**, so a volatility floor is never negative. Both are locked by tests.
- Never read labels (forbidden). Loader: `src/data/loader.py` (load, scale recovery, LOB reconstruction). Audit: `src/data/audit.py`, report `data/README.md`.
- `.gitignore` is the only guard against committing data. Verify before adding: `git check-ignore -v data/raw/<file>`.

## Style & conventions

- Ruff: line-length 100, py311, `select = ["E","F","I","UP","B","SIM"]`, `extend-exclude = ["*.md"]`.
- No comments unless explicitly asked. Follow existing code style and conventions; check neighbors before adding deps.
- Section refs in prose: `PROPOSAL.md section N` (never abbreviated). Phases/gates/namespaces (R/T/G/A/E/H/S/Q) are fixed.
- Units: $10^4$ has exactly one home (reporting bps). See `src/cost/units.py` and PROPOSAL.md 5.2.

## Git discipline

- **Do not** `git add`/`commit` unless explicitly asked. Report working tree state.
- Tracked evidence: `results/tables/`, `results/figures/`, `results/runs/<run_id>/run_manifest.json`. Caches under `results/runs/**/cache/` ignored.
- Tags: `splits-frozen` (G2), `v0.1-mvp` (G8), `config-frozen` (G10), `v1.0` (G15). No dev branch.
- Commits: `type: summary` with types `feat fix data docs test exp chore`. Experiment runs separate from source. Post `config-frozen`, changes labeled *post hoc* in `docs/decision_log.md`.

## Critical rules

- No optimization code before A0–A2 pass (PROPOSAL.md 4.1). Audit must be complete first.
- Config is the source of truth for experiment numbers (configs/). No literals in modules for order sizes/horizons/caps/λ/φ/periods.
- T8 is the only test that catches look-ahead (arrival-frozen sweep). The sweep is priced net of $F_T + fill_T$ (conservative). No completion constraint (u = y_{T+1} definition).
- Matched risk = same realised risk (not same λ). `matched_risk.forbid_test_tuning: true`.
- Clean checkout must reproduce all tables/figures via `python run_experiment.py` (G14).
- The UI is **Tier 1** (PROPOSAL.md 1.1): dataset loader, statistics on demand, optimisation menu with ≥2 selectable models (ROTE-Static QP + Almgren–Chriss — both Tier 1, MPC optional), baseline comparison, results. Definition of Done (PROPOSAL.md 14) includes it.
