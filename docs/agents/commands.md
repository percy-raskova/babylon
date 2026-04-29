# Commands Reference

## Setup

```bash
poetry install
poetry run pre-commit install
```

## CI & Quality (Fast Gate)

```bash
mise run check          # lint + format + typecheck + test:unit
mise run ci             # Same as check
mise run lint           # ruff linter
mise run format         # ruff formatter
mise run typecheck      # MyPy strict mode
mise run clean          # Clean build artifacts
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
mise run sim:run        # Main simulation entry point
mise run sim:trace      # Time-series CSV + JSON output
mise run sim:sweep      # Parameter sweep analysis
mise run sim:profile    # cProfile performance analysis
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
mise run qa:audit               # Simulation health check (3 scenarios)
mise run qa:verify              # Formula correctness verification
mise run qa:schemas             # JSON schema validation
mise run qa:security            # Dependency security audit
mise run qa:regression          # Baseline comparison (CI)
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
