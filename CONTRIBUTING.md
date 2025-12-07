# Contributing to Babylon

## Prerequisites

- **Python 3.12+**
- **Poetry** - Dependency management
- **Mise** - Task runner (recommended)
- **Direnv** - Auto-activate virtualenv (recommended)

## Quick Setup

```bash
# 1. Clone and enter
git clone https://github.com/bogdanscarwash/babylon.git
cd babylon

# 2. Install mise (if not installed)
curl https://mise.run | sh

# 3. Install dependencies
mise run install
# Or without mise: poetry install --with dev

# 4. Install pre-commit hooks
mise run hooks
# Or: poetry run pre-commit install --hook-type commit-msg --hook-type pre-commit

# 5. (Optional) Allow direnv
direnv allow
```

## Daily Workflow

### Running Quality Checks

```bash
# Run ALL checks (lint, format, typecheck, fast tests)
mise run check

# Individual checks
mise run lint        # Ruff linter with auto-fix
mise run format      # Ruff formatter
mise run typecheck   # Mypy strict mode
```

### Running Tests

```bash
# Fast tests (formulas + engine) - run frequently
mise run test-fast

# All non-AI tests
mise run test

# All tests with coverage
mise run test-cov

# Specific test file
poetry run pytest tests/unit/formulas/test_fundamental_theorem.py -v
```

### Making Commits

Pre-commit hooks run automatically:
1. **Ruff** - Lint and format
2. **Mypy** - Type check (src/ only)
3. **Pytest** - Fast tests (formulas + engine)
4. **Commitizen** - Validate commit message format

Use conventional commits:
```bash
# Interactive commit (recommended)
poetry run cz commit
# Or: git cz

# Manual (must follow format)
git commit -m "feat: add imperial rent calculation"
git commit -m "fix: correct consciousness drift formula"
git commit -m "test: add survival calculus edge cases"
```

### Versioning

```bash
# Preview version bump
mise run bump-dry

# Bump version and update CHANGELOG
mise run bump
```

## Code Standards

### Type Hints

All code must be fully typed:
```python
def calculate_rent(alpha: float, wages: float) -> float:
    return alpha * wages
```

### Testing (TDD)

1. Write failing test first (Red)
2. Implement minimum code to pass (Green)
3. Refactor for clarity (Refactor)

```python
@pytest.mark.math
def test_rent_zero_when_revolution() -> None:
    """When consciousness = 1.0, rent must be 0."""
    rent = calculate_imperial_rent(alpha=0.5, wages=0.3, consciousness=1.0)
    assert rent == 0.0
```

### Pytest Markers

- `@pytest.mark.math` - Deterministic formulas
- `@pytest.mark.ledger` - Economic/political state
- `@pytest.mark.topology` - Graph operations
- `@pytest.mark.integration` - Database/external services
- `@pytest.mark.ai` - AI/RAG tests (slow, non-deterministic)

## Project Structure

```
babylon/
├── src/babylon/
│   ├── systems/          # Core mechanics (formulas, contradictions)
│   ├── core/             # Economy, politics, entities
│   ├── rag/              # Retrieval-augmented generation
│   └── data/             # Models and persistence
├── tests/
│   ├── unit/
│   │   ├── formulas/     # Math tests (40 tests)
│   │   └── engine/       # Contradiction tests (20 tests)
│   └── integration/      # Database tests
├── .mise.toml            # Task runner
├── .envrc                # Direnv config
└── .pre-commit-config.yaml
```

## Available Mise Tasks

| Task | Description |
|------|-------------|
| `mise run install` | Install all dependencies |
| `mise run check` | Run all quality checks |
| `mise run lint` | Run ruff linter |
| `mise run format` | Run ruff formatter |
| `mise run typecheck` | Run mypy |
| `mise run test` | Run non-AI tests |
| `mise run test-fast` | Run fast math tests |
| `mise run test-cov` | Run tests with coverage |
| `mise run bump` | Bump version with changelog |
| `mise run clean` | Clean build artifacts |
| `mise run hooks` | Install pre-commit hooks |
