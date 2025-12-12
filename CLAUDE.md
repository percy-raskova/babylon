# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**Name**: Babylon - The Fall of America
**Concept**: Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory
**Objective**: Model class struggle as deterministic output of material conditions within a compact topological phase space
**Mantra**: Graph + Math = History

## Governance & Git Workflow

This project uses the **Benevolent Dictator** model. Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova)) has final authority on all merges to `main`.

### Branch Structure

```
main ────► stable releases (BD merges only)
  │              ▲
  ▼              │
dev ─────► integration (PRs welcome here)
  │    ▲
  ▼    │
feature/*, fix/*, docs/*, refactor/*
```

### Key Rules

- **Contributors** branch from `dev`, PR to `dev`
- **BD only** merges `dev` → `main` for releases
- **Hotfixes** go `fix/*` → `main` (BD only), then backport to `dev`
- **Never** commit directly to `main` or `dev`

### Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code improvements |
| `test/` | Test changes |

### For Claude Instances

When making commits:
1. Use conventional commit format: `type(scope): description`
2. After significant work, commit with the standard footer
3. If working on a feature, ensure you're on a feature branch, not `main` or `dev`
4. See [CONTRIBUTORS.md](CONTRIBUTORS.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md) for full workflow

### Documentation Maintenance (ai-docs/)

**IMPORTANT**: After completing significant work, update `ai-docs/` to reflect the new state.

**When to Update:**
- After implementing a new System or feature
- After fixing bugs that affect documented behavior
- After refactoring that changes architecture
- When discovering issues or edge cases worth noting
- When completing a sprint or phase milestone

**Files to Consider:**

| File | Update When... |
|------|----------------|
| `state.yaml` | Test counts change, sprint status changes, new components added |
| `roadmap.md` | Phase/sprint milestones reached, new planned work identified |
| `tooling.yaml` | New tools added, configuration changes, testing infrastructure updates |
| `observer-layer.yaml` | Observer system changes, event types added |
| `architecture.yaml` | System architecture changes, new Systems added |
| `decisions.yaml` | Architectural decisions made (ADRs) |

**Update Guidelines:**
1. Keep status markers accurate (COMPLETE, IN PROGRESS, PLANNED)
2. Update test counts when they significantly change
3. Add new issues/TODOs discovered during work
4. Document any deferred work in `brainstorm/deferred-ideas.md`
5. Break large changes into discrete, trackable items
6. Reference file paths for implemented features
7. Add cross-references between related documents

**Anti-Pattern**: Do NOT mark features as implemented without verifying the code exists.

## Commands

```bash
# Setup
poetry install
poetry run pre-commit install

# Task Runner (preferred - use mise for all tasks)
mise tasks                                        # List all available tasks
mise run ci                                       # Quick CI: lint + format + typecheck + test-fast
mise run test                                     # Run all non-AI tests (~1500 tests)
mise run test-fast                                # Fast math/engine tests only
mise run typecheck                                # MyPy strict mode
mise run docs-live                                # Live-reload documentation server
mise run doctest                                  # Run doctest examples in formulas
mise run clean                                    # Clean build artifacts and caches

# Parameter Analysis
mise run analyze-trace                            # Single sim with full time-series CSV
mise run analyze-sweep                            # Parameter sweep with summary metrics

# Testing (direct pytest)
poetry run pytest -m "not ai"                     # All non-AI tests
poetry run pytest -m "ai"                         # Slow AI/narrative evals
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"          # Pattern matching

# Linting & Type Checking (ruff replaces black/isort/flake8)
poetry run ruff check src tests --fix
poetry run ruff format src tests
poetry run mypy src                               # Strict mode

# Data/RAG Operations
mise run ingest-corpus                            # Ingest Marxist corpus into ChromaDB
mise run validate-schemas                         # Validate JSON schemas
mise run vertical-slice                           # Run integration test
```

## Architecture: The Embedded Trinity

Three-layer local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) - `src/babylon/data/game/`
   - Rigid material state: 17 JSON entity collections
   - Validated against JSON Schema Draft 2020-12

2. **The Topology** (NetworkX) - `src/babylon/models/world_state.py`
   - Fluid relational state via `to_graph()`/`from_graph()`
   - Two node types: `SocialClass` (entities) and `Territory` (spatial)
   - Edges: EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, TENANCY, ADJACENCY, etc.

3. **The Archive** (ChromaDB) - `src/babylon/rag/`
   - Semantic history for AI narrative generation
   - AI observes state changes, never controls mechanics

## Engine Architecture

The simulation engine uses modular Systems with dependency injection:

```
step(WorldState, SimulationConfig) -> WorldState
     |
     v
SimulationEngine.run_tick(graph, services, context)
     |
     +-- 1. ImperialRentSystem   (economic.py)      - Wealth extraction via imperial rent
     +-- 2. SolidaritySystem     (solidarity.py)    - Consciousness transmission
     +-- 3. ConsciousnessSystem  (ideology.py)      - Ideology drift & bifurcation
     +-- 4. SurvivalSystem       (survival.py)      - P(S|A), P(S|R) calculations
     +-- 5. StruggleSystem       (struggle.py)      - Agency Layer (George Floyd Dynamic)
     +-- 6. ContradictionSystem  (contradiction.py) - Tension/rupture dynamics
     +-- 7. TerritorySystem      (territory.py)     - Heat, eviction, carceral geography
```

**Key Components**:
- `src/babylon/engine/simulation_engine.py` - Orchestrates Systems
- `src/babylon/engine/services.py` - ServiceContainer (DI container)
- `src/babylon/engine/event_bus.py` - Publish/subscribe events (9 EventTypes)
- `src/babylon/engine/formula_registry.py` - 12 hot-swappable formulas
- `src/babylon/engine/simulation.py` - Stateful facade for multi-tick runs
- `src/babylon/engine/factories.py` - `create_proletariat()`, `create_bourgeoisie()`
- `src/babylon/engine/observer.py` - `SimulationObserver` protocol for state change notifications
- `src/babylon/engine/topology_monitor.py` - Phase transition detection via percolation theory
- `src/babylon/engine/systems/struggle.py` - George Floyd Dynamic (EXCESSIVE_FORCE, UPRISING events)
- `src/babylon/engine/systems/territory.py` - Carceral geography, heat dynamics, eviction pipeline
- `src/babylon/config/defines.py` - GameDefines (all tunable game coefficients)

## Type System

All game entities use Pydantic models with constrained types:

```python
# Constrained numeric types
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient

# Enums
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType
from babylon.models import OperationalProfile, SectorType  # Territory system

# Core entities
from babylon.models import SocialClass, Territory, Relationship, WorldState, SimulationConfig
```

## Formula System

12 formulas in `src/babylon/systems/formulas.py`:

| Category | Formulas |
|----------|----------|
| Fundamental Theorem | `calculate_imperial_rent`, `calculate_labor_aristocracy_ratio`, `is_labor_aristocracy`, `calculate_consciousness_drift` |
| Survival Calculus | `calculate_acquiescence_probability`, `calculate_revolution_probability`, `calculate_crossover_threshold`, `apply_loss_aversion` |
| Unequal Exchange | `calculate_exchange_ratio`, `calculate_exploitation_rate`, `calculate_value_transfer`, `prebisch_singer_effect` |

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/ChromaDB (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.unit        # Unit tests (default)
```

## Coding Standards

- **Pydantic First**: All game objects as `pydantic.BaseModel`, no raw dicts
- **Constrained Types**: Use `Probability`, `Currency`, `Intensity` instead of raw floats
- **Data-Driven**: Game logic in JSON data files, not hardcoded conditionals
- **Strict Typing**: MyPy strict mode, explicit return types
- **TDD**: Red-Green-Refactor cycle mandatory
- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, `refactor:` prefixes
- **SQLAlchemy 2.0**: Use `DeclarativeBase` with `Mapped` types for ORM models
- **Sphinx-Compatible Docstrings**: All public classes/functions require RST-formatted docstrings
- **No `test_` Prefix in Production Code**: Pytest auto-collects functions starting with `test_`. Use `check_`, `verify_`, or `validate_` instead for production functions that "test" something (e.g., `check_resilience`, not `test_resilience`).

## Docstring Standards

**IMPORTANT**: All public classes, functions, and modules MUST have Sphinx-compatible docstrings.

**Format**: RST (reStructuredText) - Sphinx's native format

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

**RST Rules**:
- Use `::` for code blocks (not markdown triple backticks)
- Use `:param name:` or `Args:` section for parameters
- Use `:returns:` or `Returns:` section for return values
- Use `:raises ExceptionType:` or `Raises:` section for exceptions
- Use `:class:`ClassName`` for cross-references to classes
- Use `:func:`function_name`` for cross-references to functions
- Use `:mod:`module.path`` for cross-references to modules
- Blank line required before and after code blocks
- Examples should pass `pytest --doctest-modules`

**Why This Matters**: Sphinx autodoc generates API documentation from docstrings. Malformed docstrings produce warnings that block CI (we use `-W` flag). See `ai-docs/tooling.yaml` for configuration details.

## Mathematical Core

**Fundamental Theorem**: Revolution in Core impossible if W_c > V_c (wages > value produced). The difference is Imperial Rent (Phi).

**Survival Calculus**:
- P(S|A) = Sigmoid(Wealth - Subsistence) - survival by acquiescence
- P(S|R) = Organization / Repression - survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

**Bifurcation Formula**: When wages fall, agitation energy routes to either Fascism (+1 ideology) or Revolution (-1 ideology) based on SOLIDARITY edge presence.

**Heat Dynamics**: HIGH_PROFILE territories gain heat (state attention), LOW_PROFILE decays heat. Heat >=0.8 triggers eviction pipeline.

## Configuration: GameDefines

All tunable game coefficients are centralized in `GameDefines` (Pydantic model):

```python
from babylon.config.defines import GameDefines

defines = GameDefines()  # Load defaults from pyproject.toml [tool.babylon]
defines.economy.extraction_efficiency  # 0.8 default
defines.consciousness.drift_sensitivity_k  # Consciousness drift rate
```

Categories: `economy`, `consciousness`, `solidarity`, `survival`, `territory`

## Documentation

- Sphinx docs: `mise run docs-live` for development, `mise run docs` to build
- Design specs in `brainstorm/mechanics/`
- AI-readable specs in `ai-docs/` (YAML format) - **read `ai-docs/README.md` for catalog**
- Deferred ideas go to `brainstorm/deferred-ideas.md`
- Anti-patterns documented in `ai-docs/anti-patterns.yaml`

**Architecture Principle**: State is pure data. Engine is pure transformation. They never mix.
