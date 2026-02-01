# Copilot Instructions

**Babylon** - Geopolitical simulation engine modeling class struggle through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory.

> **Primary Reference:** [`CLAUDE.md`](CLAUDE.md) contains comprehensive development standards, architectural decisions, and coding patterns. Read it first.

## Quick Start

```bash
poetry install                      # Install dependencies
mise run ci                         # Fast CI gate: lint + format + typecheck + test:unit
mise run test:all                   # All non-AI tests (~1500 tests)
mise run docs-live                  # Live documentation server
```

## Essential Knowledge

### Architecture: The Embedded Trinity

Three-layer local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) - Persistent material state in [src/babylon/data/](src/babylon/data/)

   - 17 JSON entity collections validated against JSON Schema Draft 2020-12
   - `defines.yaml` - Single source of truth for all tunable coefficients
   - Hydration pattern: Load at startup → mutate in RAM → persist on save (NO DB I/O during tick)

1. **The Topology** (NetworkX/GraphProtocol) - Hot computational graph in [src/babylon/models/world_state.py](src/babylon/models/world_state.py)

   - `to_graph()` / `from_graph()` - Convert Pydantic ↔ DiGraph
   - Node types: `SocialClass` (entities), `Territory` (spatial)
   - Edge types: EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, REPRESSION, TENANCY
   - Future: Interface-first design enables swapping NetworkX for DuckDB+DuckPGQ without changing System code

1. **The Archive** (ChromaDB) - Semantic history for AI narrative in [src/babylon/rag/](src/babylon/rag/)

   - AI observes state changes, **never controls mechanics**
   - Non-deterministic narrative only, deterministic formulas separate

**Key Insight:** State is pure data. Engine is pure transformation. They never mix.

### Development Workflow (Critical!)

**COMMIT EARLY, COMMIT OFTEN** - After each logical unit of work:

```bash
# Anti-pattern: Accumulating multiple changes before committing
# ❌ BAD: Fix Genesis bug + Fix Zombie bug → try to commit separately → FAILS
#         Pre-commit hooks test only staged files; if Bug B tests need Bug A code, you're forced into giant commits

# ✅ GOOD: Fix Genesis bug → commit immediately → Fix Zombie bug → commit immediately
git add src/babylon/scenarios.py tests/unit/test_scenario_initialization.py
git commit -m "fix(genesis): resolve initialization order"  # Conventional commit format
```

**Why:** Pre-commit hooks run tests on staged files only. Accumulating work creates dependency chains that force large, unreviewable commits.

### Core Principles

- **Test-Driven Development (TDD):** Red-Green-Refactor cycle mandatory. Use `@pytest.mark.red_phase` for TDD RED phase.
- **Pydantic First:** All game objects as `pydantic.BaseModel`, no raw dicts. Use constrained types (`Probability`, `Currency`, `Intensity`).
- **Strict Typing:** MyPy strict mode enforced. Explicit return types on all functions.
- **Data-Driven Design:** Game logic in `defines.yaml` and JSON data files, not hardcoded conditionals.
- **Test Constants:** Use `tests/constants.py` for domain defaults (e.g., `TC.Wealth.WORKER_BASELINE`). Keep type boundaries inline (e.g., `0.0`, `1.0` for Probability).

## Task Runner (mise)

All development tasks use `mise` with namespace-driven organization:

```bash
mise tasks                          # List all available tasks

# CI & Quality (fast gate)
mise run check                      # lint + format + typecheck + test:unit (use before commits)
mise run lint                       # Ruff linter with auto-fix
mise run format                     # Ruff formatter
mise run typecheck                  # MyPy strict mode

# Testing (test:* namespace)
mise run test:unit                  # Unit tests only (fast, ~500 tests)
mise run test:int                   # Integration tests (mechanics & systems)
mise run test:all                   # All non-AI tests (~1500 tests)
mise run test:cov                   # Tests with coverage report
mise run test:doctest               # Doctest examples in formulas

# Simulation (sim:* namespace)
mise run sim:run                    # Main simulation entry point
mise run sim:trace                  # Time-series CSV + JSON output
mise run sim:sweep                  # Parameter sweep analysis
mise run sim:profile                # cProfile performance analysis

# QA (qa:* namespace)
mise run qa:verify                  # Formula correctness verification
mise run qa:schemas                 # JSON schema validation
mise run qa:security                # Dependency security audit

# Documentation (docs:* namespace)
mise run docs:build                 # Build Sphinx documentation
mise run docs:live                  # Live-reload documentation server
mise run docs:strict                # Build with warnings as errors (CI mode)
```

**Direct pytest** (for specific tests):

```bash
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"                   # Pattern matching
poetry run pytest -m "math"                                # Run specific markers
```

## Pytest Markers

Tests are categorized by performance and I/O characteristics:

- `@pytest.mark.math` - Deterministic formulas (fast, pure functions)
- `@pytest.mark.ledger` - Economic/political state manipulation
- `@pytest.mark.topology` - Graph/network operations (NetworkX)
- `@pytest.mark.integration` - Database/ChromaDB (I/O bound)
- `@pytest.mark.ai` - AI/RAG evaluation (slow, non-deterministic)
- `@pytest.mark.red_phase` - TDD RED phase (intentionally failing until GREEN)

**Filter examples:**

```bash
poetry run pytest -m "math"                    # Only fast math tests
poetry run pytest -m "not ai"                  # Exclude slow AI tests (default)
poetry run pytest -m "math or ledger"          # Multiple markers
```

## Engine Architecture

Modular systems with dependency injection:

```
step(WorldState, SimulationConfig) -> WorldState
     |
     v
SimulationEngine.run_tick(graph, services, context)
     |
     +-- 1. ImperialRentSystem   - Wealth extraction via imperial rent
     +-- 2. SolidaritySystem     - Consciousness transmission
     +-- 3. ConsciousnessSystem  - Ideology drift & bifurcation
     +-- 4. SurvivalSystem       - P(S|A), P(S|R) calculations
     +-- 5. StruggleSystem       - Agency Layer (George Floyd Dynamic)
     +-- 6. ContradictionSystem  - Tension/rupture dynamics
     +-- 7. TerritorySystem      - Heat, eviction, carceral geography
```

**Key Components:**

- `src/babylon/engine/simulation_engine.py` - Orchestrates Systems
- `src/babylon/engine/services.py` - ServiceContainer (DI container)
- `src/babylon/engine/event_bus.py` - Publish/subscribe events (12 EventTypes)
- `src/babylon/engine/formula_registry.py` - 17 hot-swappable formulas
- `src/babylon/config/defines.py` - GameDefines (all tunable coefficients)
- `src/babylon/formulas/formulas.py` - Mathematical formulas (17 total)

**Observer System:**

- `SimulationObserver` - Protocol for state change notifications
- `SessionRecorder` - Black box recording for debugging/replay
- `TopologyMonitor` - Phase transition detection via percolation theory

## Type System & Imports

All game entities use Pydantic models with constrained types:

```python
# Constrained numeric types (ALWAYS use these, never raw floats)
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient

# Enums
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType

# Core entities
from babylon.models import SocialClass, Territory, Relationship, WorldState, SimulationConfig

# Test constants
from tests.constants import TestConstants
TC = TestConstants  # Shorthand alias

# Example usage
worker = SocialClass(
    id="C001",
    name="Worker",
    wealth=Currency(TC.Wealth.WORKER_BASELINE),
    ideology=Ideology(TC.Ideology.AWAKENING),
    consciousness=Probability(0.7),
)
```

## Docstring Standards (Critical for CI)

**All public classes/functions MUST have Sphinx-compatible RST docstrings.** CI fails on malformed docstrings (`-W` flag).

```python
def calculate_imperial_rent(wages: Currency, value: Currency) -> Currency:
    """Calculate imperial rent extracted via unequal exchange.

    The fundamental theorem of MLM-TW: when wages exceed value produced,
    the difference represents imperial rent transferred from periphery.

    Args:
        wages: Currency amount paid to workers in core.
        value: Currency amount of value actually produced.

    Returns:
        Imperial rent (Phi) extracted from periphery workers.

    Raises:
        ValueError: If wages or value are negative.

    Example:
        >>> calculate_imperial_rent(wages=Currency(100.0), value=Currency(80.0))
        Currency(20.0)

    See Also:
        :func:`calculate_exploitation_rate`: Related exploitation metric.
        :class:`ImperialRentSystem`: System that applies this formula.
    """
```

**RST Rules:**

- Use `::` for code blocks (not markdown triple backticks)
- Use `Args:` / `Returns:` / `Raises:` sections
- Use `:func:`function_name\`\` for cross-references to functions
- Use `:class:`ClassName\`\` for cross-references to classes
- Examples should pass `pytest --doctest-modules`
- Blank line required before and after code blocks

## Verification Checklist

Before submitting any PR:

```bash
mise run check                      # Fast CI gate (lint + format + typecheck + test:unit)
mise run test:all                   # All non-AI tests
poetry run pytest --doctest-modules src/babylon/formulas/formulas/  # If you modified formulas
```

## Key Files Reference

| File/Directory                                                     | Purpose                                           |
| ------------------------------------------------------------------ | ------------------------------------------------- |
| [`CLAUDE.md`](CLAUDE.md)                                           | Comprehensive development guidelines (READ FIRST) |
| [`ai-docs/`](ai-docs/)                                             | Machine-readable YAML specs for all systems       |
| [`ai-docs/formulas-spec.yaml`](ai-docs/formulas-spec.yaml)         | All mathematical formulas                         |
| [`ai-docs/architecture.yaml`](ai-docs/architecture.yaml)           | System architecture deep-dive                     |
| [`ai-docs/pydantic-patterns.yaml`](ai-docs/pydantic-patterns.yaml) | Pydantic V2 patterns & reference                  |
| [`ai-docs/anti-patterns.yaml`](ai-docs/anti-patterns.yaml)         | What NOT to do                                    |
| [`tests/constants.py`](tests/constants.py)                         | Test constants and patterns                       |
| [`src/babylon/data/defines.yaml`](src/babylon/data/defines.yaml)   | All tunable game coefficients                     |
| [`pyproject.toml`](pyproject.toml)                                 | Project configuration                             |

## AI Agent Pitfalls (Critical!)

**NEVER:**

- ❌ Delete tests to make them pass - Fix the code, not the tests
- ❌ Hallucinate APIs - Only use imports from codebase or `pyproject.toml`
- ❌ Ignore edge cases - Check boundaries, empty inputs, error states
- ❌ Add dependencies without verification - Check PyPI first (`poetry show <package>`)
- ❌ Use raw dicts - All game objects must be Pydantic models
- ❌ Let AI control mechanics - AI observes only, formulas are deterministic
- ❌ Use `test_` prefix in production code - Pytest auto-collects these (use `check_`, `verify_`, `validate_`)

**Self-Review Questions:**

1. *"What tests validating this change don't exist yet?"* - Add them
1. *"What edge cases might this miss?"* - Handle them
1. *"Does this align with existing patterns in CLAUDE.md?"* - Follow them
1. *"Am I deleting or modifying tests just to make CI pass?"* - Don't

## Good Issue Patterns for AI Agents

These types of issues work well with coding agents:

- ✅ **Add unit tests for module X** - Well-scoped, clear success criteria
- ✅ **Fix lint/type errors in file Y** - Deterministic, verifiable
- ✅ **Add docstrings to module Z** - Follows existing patterns
- ✅ **Refactor function to use Pydantic model** - Clear transformation
- ✅ **Implement formula from ai-docs/formulas-spec.yaml** - Spec-driven

## Branch & Git Workflow

This project uses the **Benevolent Dictator** model:

```
main ────► stable releases (BD merges only)
  │              ▲
  ▼              │
dev ─────► integration (PRs welcome here)
  │    ▲
  ▼    │
feature/*, fix/*, docs/*, refactor/*
```

- **Contributors:** Branch from `dev`, PR to `dev`
- **BD only:** Merges `dev` → `main` for releases
- **Never:** Commit directly to `main` or `dev`

**Conventional commits:**

```bash
git commit -m "feat(solidarity): add consciousness transmission"
git commit -m "fix(genesis): resolve initialization order"
git commit -m "docs(formulas): add LaTeX for survival calculus"
git commit -m "refactor(ledger): extract GameDefines loading"
```

## Mathematical Core (Theory)

**Fundamental Theorem:** Revolution in Core impossible if W_c > V_c (wages > value produced). The difference is Imperial Rent (Phi).

**Survival Calculus:**

- P(S|A) = Sigmoid(Wealth - Subsistence) - survival by acquiescence
- P(S|R) = Organization / Repression - survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

**See:** [`ai-docs/formulas-spec.yaml`](ai-docs/formulas-spec.yaml) for full mathematical specifications.
