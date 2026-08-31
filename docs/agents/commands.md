# Commands Reference

## Setup

```bash
uv sync --extra server
uv run pre-commit install
```

## CI & Quality (Fast Gate)

```bash
mise run check            # Non-mutating static/local contracts + unit tests
mise run check:quick      # Non-mutating lint + format + typecheck
mise run check:full-local # Check plus workstation data/reference probes
mise run fix              # Apply Ruff fixes, then format sequentially
mise run ci               # Same as check
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
mise run sim:run           # Frozen Python one-tick reference smoke
mise run sim:sweep         # Intentional in-memory parameter-analysis periphery
mise run sim:e2e-michigan  # Rust-owned 520-tick PostgreSQL run
mise run sim:e2e-bg        # Run the Rust-owned Michigan campaign in the background
mise run sim:status        # Process plus Rust persistence-authority status
mise run sim:probe         # Rust persistence-authority and campaign-tail probe
mise run sim:archive       # Inspect Rust-owned Archive dirty receipts
```

## Tuning

```bash
mise run tune:optuna      # Bayesian optimization (Optuna TPE)
mise run tune:landscape   # 2D parameter grid search
mise run tune:params      # 1D sensitivity sweep
mise run tune:dashboard   # Optuna Dashboard visualization
```

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
