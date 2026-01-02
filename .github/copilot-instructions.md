# Copilot Instructions

This is a Python-based repository for Babylon, a geopolitical simulation engine modeling class struggle through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory.

## Core Principles

- **Adhere to Test-Driven Development (TDD):** All new features and bug fixes should be covered by corresponding unit or integration tests. Red-Green-Refactor cycle mandatory.
- **Pydantic First:** All game objects as `pydantic.BaseModel`, no raw dicts. Use constrained types (`Probability`, `Currency`, `Intensity`).
- **Strict Typing:** MyPy strict mode enforced. Explicit return types on all functions.
- **Data-Driven:** Game logic in JSON data files, not hardcoded conditionals.

## Development Workflow

### Dependency Management

Use Poetry for dependency management and packaging:

- Install dependencies: `poetry install`
- Add a dependency: `poetry add <package>`

### Task Runner (Preferred)

Use mise for all tasks:

```bash
mise tasks                    # List all available tasks
mise run ci                   # Quick CI: lint + format + typecheck + test-fast
mise run test                 # Run all non-AI tests (~1500 tests)
mise run test-fast            # Fast math/engine tests only
mise run typecheck            # MyPy strict mode
mise run docs-live            # Live-reload documentation server
```

### Testing

Use the Pytest suite for all tests:

```bash
poetry run pytest -m "not ai"                     # All non-AI tests
poetry run pytest -m "ai"                         # Slow AI/narrative evals
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"          # Pattern matching
```

**Pytest Markers:**

- `@pytest.mark.math` - Deterministic formulas (fast, pure)
- `@pytest.mark.ledger` - Economic/political state
- `@pytest.mark.topology` - Graph/network operations
- `@pytest.mark.integration` - Database/ChromaDB (I/O bound)
- `@pytest.mark.ai` - AI/RAG evaluation (slow, non-deterministic)

### Formatting & Linting

Ruff handles all linting and formatting (replaces black/isort/flake8):

```bash
poetry run ruff check src tests --fix    # Lint with auto-fix
poetry run ruff format src tests         # Format code
poetry run mypy src                      # Type checking (strict mode)
```

### Documentation

- Document all public APIs with Sphinx-compatible RST docstrings
- Use `mise run docs-live` for live-reload documentation server
- Design specs in `brainstorm/mechanics/`
- AI-readable specs in `ai-docs/` (YAML format)

## Architecture

**The Embedded Trinity** (three-layer local system, no external servers):

1. **The Ledger** (SQLite/Pydantic) - Rigid material state
1. **The Topology** (NetworkX) - Fluid relational state via graphs
1. **The Archive** (ChromaDB) - Semantic history for AI narrative

**Key Principle:** State is pure data. Engine is pure transformation. They never mix.

## Key Guidelines

1. Use Poetry for all dependency and environment management
1. Write or update Pytest-based tests for every new feature or bugfix (TDD preferred)
1. Format, lint, and type-check before submitting code
1. Document your code with Sphinx-compatible RST docstrings
1. Use conventional commit messages (`feat:`, `fix:`, `docs:`, `refactor:`)
1. See `CLAUDE.md` for comprehensive development guidelines
