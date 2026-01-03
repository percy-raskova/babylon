# Copilot Instructions

This is a Python-based repository for Babylon, a geopolitical simulation engine modeling class struggle through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory.

> **Important:** For comprehensive development guidelines, see `CLAUDE.md` in the repository root. This file contains the authoritative development standards, architectural decisions, and coding patterns.

## Quick Reference

### Before You Start

1. **Read `CLAUDE.md`** - Contains all coding standards, architecture details, and patterns
1. **Check `ai-docs/`** - Machine-readable specs for formulas, systems, and architecture
1. **Run tests first** - `poetry run pytest -m "not ai" -q` to verify baseline

### Core Principles

- **Adhere to Test-Driven Development (TDD):** All new features and bug fixes should be covered by corresponding unit or integration tests. Red-Green-Refactor cycle mandatory.
- **Pydantic First:** All game objects as `pydantic.BaseModel`, no raw dicts. Use constrained types (`Probability`, `Currency`, `Intensity`).
- **Strict Typing:** MyPy strict mode enforced. Explicit return types on all functions.
- **Data-Driven:** Game logic in JSON data files, not hardcoded conditionals.
- **Commit After Each Unit of Work:** Don't accumulate multiple logical changes before committing.

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

## Verification Checklist

Before submitting any PR, ensure:

```bash
# 1. Lint passes
poetry run ruff check .

# 2. Format is correct
poetry run ruff format --check .

# 3. Types are correct
poetry run mypy src

# 4. Tests pass
poetry run pytest -m "not ai" -q

# 5. Doctests pass (if you modified formulas)
poetry run pytest --doctest-modules src/babylon/systems/formulas/
```

## AI-Generated Code Review Checklist

**CRITICAL - Avoid These AI Pitfalls:**

- **NEVER delete tests to make them pass** - Fix the code, not the tests
- **NEVER hallucinate APIs** - Only use imports that exist in the codebase or `pyproject.toml`
- **NEVER ignore edge cases** - Check boundary conditions, empty inputs, error states
- **NEVER add dependencies without verification** - Check they exist on PyPI first

**Self-Review Questions:**

Before submitting, ask yourself:

1. *"What tests validating this change don't exist yet?"* - Add them
1. *"What edge cases might this miss?"* - Handle them
1. *"Does this align with existing patterns in CLAUDE.md?"* - Follow them
1. *"Am I deleting or modifying tests just to make CI pass?"* - Don't

**Functional Verification:**

1. Run the full test suite, not just affected tests
1. Verify imports actually exist (`poetry show <package>`)
1. Check that new code integrates with existing architecture
1. Ensure error handling matches project patterns (see `src/babylon/utils/exceptions.py`)

## Good Issue Patterns for Copilot

These types of issues work well with the coding agent:

- **Add unit tests for module X** - Well-scoped, clear success criteria
- **Fix lint/type errors in file Y** - Deterministic, verifiable
- **Add docstrings to module Z** - Follows existing patterns
- **Refactor function to use Pydantic model** - Clear transformation
- **Implement formula from ai-docs/formulas-spec.yaml** - Spec-driven

## Files to Reference

| File                         | Purpose                              |
| ---------------------------- | ------------------------------------ |
| `CLAUDE.md`                  | Comprehensive development guidelines |
| `ai-docs/formulas-spec.yaml` | All mathematical formulas            |
| `ai-docs/architecture.yaml`  | System architecture                  |
| `tests/constants.py`         | Test constants and patterns          |
| `pyproject.toml`             | Project configuration                |
