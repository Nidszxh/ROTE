# AGENTS.md

## Repo state (read first)

- **ROTE** = Risk-Aware Optimal Trade Execution. Authority split: `PROPOSAL.md` = the specification (what is built, how it is judged); root `ROADMAP.md` = approach, model menu (M1–M4), 8-week schedule and owner split; `AGENTS.md` (this file) = engineering scaffold; `docs/decision_log.md` = dated decisions; `docs/feedback_log.md` = review-1 feedback; `docs/REUSE_ANALYSIS.md` = rejected alternatives. `CHANGELOG.md` and `DECISIONS.md` were **deleted** — don't reference them. Experiment numbers live only in `configs/experiment.yaml`.
- **The working tree is mid-migration and UNCOMMITTED.** HEAD (`d010895`) still contains the old pipeline; the tree deleted it (`src/data`, `src/cost`, `src/optimize`, `src/simulator`, `src/features`, `run_experiment.py`, `data/README.md`, all six `results/figures/*.png`, all 17 committed test files) and added ROADMAP-shaped stubs: `src/loader`, `src/impact`, `src/models/{m1_ac,m2_lp,m3_mip,m4_ahp}`, `src/sim`, `src/stats`, `src/benchmarks`, `src/utils/contracts.py`. Only `src/config.py` and `src/utils/contracts.py` have real code. So `git show HEAD:src/data/loader.py` works even though the file is gone — history is not the tree.
- **`README.md` is stale** (it documents `run_experiment.py`, `src/data`, 222 tests and `docs/ROADMAP.md`, none of which exist now). Trust code and `PROPOSAL.md` over it. Its setup/dependency sections are still accurate.
- **`PROPOSAL.md` was rewritten 2026-10-05** to be ROADMAP-governed and renumbered: section 6 = models, 7 = baselines/interface, 8 = simulator, **9 = correctness standards (T1–T17)**, 10 = evaluation protocol, 11 = delivery plan/progress. Section numbers are cross-referenced from `pyproject.toml` markers — keep section 9 as the T-gate section if you edit it.
- No packaging, no CI, no pre-commit: every check below is manual. Dataset: FI-2010 (DecPre, NoAuction), outside the repo, **never committed**; labels are forbidden (`configs/experiment.yaml: dataset.labels`).

## Environment

```bash
export ROTE_DATA_ROOT="$HOME/data/FI-2010"   # 4 files, ~897 MiB; required by anything that reads the data
uv venv .venv && uv pip install -r pyproject.toml --extra dev   # deps only, never -e .
uv run --no-sync python -c "import numpy,cvxpy; assert 'OSQP' in cvxpy.installed_solvers()"
```

- `uv run --no-sync` reuses `.venv` without re-resolving; plain `uv run` also works.
- **There is no build backend.** `uv pip install -e .` falls back to setuptools and drops a stray `src/rote.egg-info/`. Plain `pip` cannot read `pyproject.toml` as requirements (README lists the deps explicitly).
- Verified here: Python 3.12.13, numpy 2.5.3, pandas 3.0.6, cvxpy 1.9.3 (solvers `CLARABEL SCS SCIPY HIGHS OSQP`), ruff 0.16.10, pytest 9.1.1, streamlit 1.65.0. `scipy`, `seaborn`, `statsmodels` are declared but imported nowhere.
- `uv.lock` is deliberately **not** gitignored — it is the reproducibility record if it is ever generated. `.env*` is ignored and must stay ignored.

## Commands (run from the repo root)

```bash
uv run --no-sync ruff check .              # NOT green: 4 F401 (2 unused imports in stubs, 2 in tests/test_basic.py)
uv run --no-sync ruff format --check .     # NOT green: 7 files (stubs use single quotes; ruff format wants double)
uv run --no-sync pytest                    # NOT green: 2 failures — see "import path is broken" below
uv run --no-sync pytest tests/test_basic.py::test_contracts_import   # single test
uv run --no-sync pytest -m T1              # marker subset; --strict-markers is on
uv run --no-sync streamlit run app.py      # 5-line placeholder page
```

- **There is no `run_experiment.py`** (deleted with the old pipeline). Any command in README that names it is dead until the CLI is rebuilt.
- **Import path is broken right now.** `pyproject.toml` has `pythonpath = ["src"]` (the old convention: `from data import loader`, never `src.data`), but every new stub and test imports with the `src.` prefix (`from src.utils.contracts import ...`). Result: `pytest` fails with `ModuleNotFoundError: No module named 'src'`. Pick one convention; `pythonpath = ["."]` matches the code as written. Do not "fix" it by rewriting imports to top-level while `src/__init__.py` and the `src.` prefix exist.
- **Markers are declared T1–T14, A1, A4, slow** and `--strict-markers` rejects anything else. `PROPOSAL.md` section 9 now also defines **T15–T17** (shadow prices, MIP structure, AHP CR) — register them in `pyproject.toml` before writing a test with those markers. No test currently uses `slow`.
- When lint/test are green again, verify with the three commands above in that order (lint → format → test). There is no typechecker.

## Conventions that differ from defaults

- **Contracts are the architecture.** `src/utils/contracts.py` defines `Order`, `Schedule`, `CostReport`; every model must return a `Schedule` and every schedule must go through the one `simulate()` (`PROPOSAL.md` section 7.2). A model that computes its own cost/shortfall is a spec violation — the comparison is then between two simulators, not two policies.
- Model modules are named after the roadmap menu: `m1_ac.py` (Almgren–Chriss), `m2_lp.py` (LOB LP + shadow prices), `m3_mip.py` (fixed-charge IP), `m4_ahp.py` (AHP). The core ROTE-Static QP is *M1 + M2 linked*, not a fifth menu item.
- Ruff: line-length 100, `target-version py311`, select `E,F,I,UP,B,SIM`, `*.md` excluded. No quote-style configured → format normalises to double quotes.
- Config is the source of truth for every experiment number: `configs/experiment.yaml` (risk grid on **`omega`**, never absolute `lambda` — an absolute grid is off by orders of magnitude and silently returns TWAP; `theta`, `rho`, `pi`, resilience `phi`, bootstrap), `configs/splits.yaml` (frozen day blocks 1–5/6–7/8–9, reserve 10; tag `splits-frozen` exists). Never hardcode a grid or tolerance in code.
- `config.load()` anchors on `REPO_ROOT` (`src/config.py`), so it works from any CWD; anything else you add should do the same or be run from the repo root.
- **Prose convention:** section references are written `PROPOSAL.md section N`, never abbreviated `§N`. R/T/G/A/E/H/S/Q identifiers (risks, tests, gates, audits, experiments, hypotheses, assumptions, questions) are fixed — renumbering them breaks cross-references in `pyproject.toml` and in the tests themselves. No comments in code unless explicitly asked.
- **Spec rules that are easy to break and cheap to violate** (none currently enforced by a test): the sweep is priced at arrival state and net of `F_T + fill_T` — reading a horizon-end mid or worst ask is look-ahead (`PROPOSAL.md` section 9 T8); there is **no** completion constraint — `u = y_{T+1}` is a definition, so there is no completion dual; the UI is Tier 1 with two guaranteed selectable models (section 1.3).
- **Matched risk** means equal *realised* risk, never equal `lambda`; the acceptance rule is `PROPOSAL.md` section 1.5. No optimisation code ahead of the audit gates (section 4.1 / week-1 gate G1).
- **Roadmap notation vs spec notation:** roadmap's participation factor `φ` is `rho` here; `phi`/`varphi` is resilience in the simulator. Don't mix them.

## Git discipline

- Do **not** `git add`/`commit`/`tag` unless explicitly asked; report working-tree state instead. Tags today: `splits-frozen` only (on `1397870`); `main` only, no dev branch. Planned by the spec: `config-frozen` before the single test run (`PROPOSAL.md` section 10.5), then `v0.1-mvp` / `v1.0` at the release gates. After `config-frozen`, any constant change must be labelled *post hoc* in `docs/decision_log.md`.
- Commit style when asked: `type: summary`, types `feat fix data docs test exp chore`. Data files are never committed: `.gitignore` `/data/raw/*` is the only guard (`data/` is empty right now — `data/raw/` was removed in the migration; if a `data/raw/FI-2010` symlink is recreated, note `git check-ignore` *through* a symlink fails "beyond a symbolic link" — check the link itself).
