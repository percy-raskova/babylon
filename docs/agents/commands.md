# Commands Reference

## Setup

```bash
mise install
mise run install
mise run hooks
```

## CI & Quality (Fast Gate)

```bash
mise run check            # Non-mutating static/local contracts + unit tests
mise run check:quick      # Non-mutating lint + format + typecheck
mise run check:full-local # Check plus workstation data/reference probes
mise run fix              # Apply Ruff fixes, then format sequentially
mise run ci               # Same as check
mise run lint:check       # Ruff linter, no fixes
mise run format:check     # Ruff formatter check, no rewrites
mise run lint             # Apply Ruff lint fixes
mise run format           # Apply Ruff formatting
mise run typecheck        # MyPy strict mode
mise run clean            # Clean build artifacts
```

## Testing

```bash
mise run test:unit      # Unit tests only (fast)
mise run test:int       # Integration tests (mechanics & systems)
mise run test:scenario  # Scenario tests (slow, full arcs)
mise run test:all       # All non-AI tests
mise run test:cov       # Tests with coverage report
mise run test:doctest   # Doctest examples in formulas
```

## Simulation

```bash
mise run sim:e2e-michigan     # Fresh 520-tick Rust run unless campaign ID is explicit
mise run sim:e2e-bg           # Resume explicit campaign, or worktree default, in background
mise run sim:status           # Process, its recorded campaign tail, and global totals
mise run sim:probe            # Explicit campaign, or worktree default, plus global totals
mise run sim:archive          # Inspect global Rust-owned Archive dirty receipts
mise run sim:report                    # Local 60-tick report; shared database attribution
mise run sim:report 520 3000 exclusive # Canonical Rust Michigan diagnostic bundle
mise run reference:python-smoke  # Frozen Python one-tick reference smoke
```

``sim:report`` is authoritative Rust persistence observability. The canonical
520-tick run writes a collision-safe bundle below ``reports/sim-runs/`` and
labels its Postgres database and WAL observations ``exclusive``.

## Development Tooling

```bash
mise run dev:doctor  # Report worktree, Mise, and repository Rust host-policy facts
```

## Frozen-reference analysis

```bash
mise run analysis:optuna      # Bayesian optimization (Optuna TPE)
mise run analysis:landscape   # 2D parameter grid search
mise run analysis:sweep       # 1D sensitivity sweep
mise run analysis:monte-carlo # Monte Carlo uncertainty analysis
mise run analysis:campaign    # Weekly frozen-Python reference profile
mise run analysis:campaign -- full # Full MC + Optuna + Morris/Sobol profile
mise run analysis:dashboard   # Root optuna.db by default
mise run analysis:dashboard -- /absolute/campaign/study.sqlite3
```

``analysis:campaign`` is non-authoritative frozen-Python analysis. Each run
writes ``campaign.json`` and leg artifacts below
``reports/frozen-reference-analysis/<run>/``. Pass a campaign's absolute
``optuna/study.sqlite3`` path to ``analysis:dashboard`` to open that study.

## QA

```bash
mise run qa:verify              # Formula correctness verification
mise run qa:schemas             # JSON schema validation
mise run qa:security            # Dependency security audit
mise run qa:regression          # Baseline comparison (CI)
mise run qa:vault-regression    # Retained projection-vault byte gate
mise run qa:regression-generate # Create regression baselines
```

## Data

```bash
mise run data:ingest     # Ingest Marxist corpus into ChromaDB
mise run data:db-init    # Initialize SQLite database
```

## Documentation

```bash
mise run docs:build   # Build Sphinx documentation
mise run docs:live    # Live-reload documentation server
mise run docs:strict  # Build with warnings as errors
```

## UI

```bash
mise run ui           # Launch DearPyGui Synopticon dashboard
```

## Full Task Listing

```bash
mise tasks            # List all available tasks
```
