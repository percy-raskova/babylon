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
2. **Commit after each unit of work** - Don't let multiple logical changes accumulate
3. If working on a feature, ensure you're on a feature branch, not `main` or `dev`
4. See [CONTRIBUTORS.md](CONTRIBUTORS.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md) for full workflow

**Commit Early, Commit Often**: Each logical unit of work should be its own commit. This means:
- After completing a bug fix → commit immediately
- After adding a new feature → commit immediately
- After refactoring → commit immediately
- After adding tests for a feature → commit with the feature (same unit)

**Why This Matters**: Pre-commit hooks test only staged files. If you accumulate multiple units of work (e.g., Bug A fix + Bug B fix), and Bug B's tests depend on Bug A's code changes, you cannot commit them separately - the hooks will fail. This forces large, intertwined commits that are hard to revert and review.

**Anti-Pattern**:
```
# BAD: Multiple units of work in one session without commits
1. Fix Genesis bug (scenarios.py, test_scenario_initialization.py)
2. Fix Zombie bug (economic.py, social_class.py, defines.py, test_subsistence.py)
3. Try to commit Genesis fix alone → FAILS (tests need Zombie fix code)
4. Forced to make one giant commit with both fixes
```

**Correct Pattern**:
```
# GOOD: Commit after each unit
1. Fix Genesis bug → commit immediately
2. Fix Zombie bug → commit immediately
3. Each fix is independently revertable
```

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

# Task Runner (namespace-driven - see ADR035)
mise tasks                                        # List all available tasks

# CI & Quality (fast gate)
mise run check                                    # lint + format + typecheck + test:unit
mise run ci                                       # Same as check
mise run lint                                     # Run ruff linter
mise run format                                   # Run ruff formatter
mise run typecheck                                # MyPy strict mode
mise run clean                                    # Clean build artifacts

# Testing (test:* namespace)
mise run test:unit                                # Unit tests only (fast)
mise run test:int                                 # Integration tests (mechanics & systems)
mise run test:scenario                            # Scenario tests (slow, full arcs)
mise run test:all                                 # All non-AI tests
mise run test:cov                                 # Tests with coverage report
mise run test:doctest                             # Doctest examples in formulas

# Simulation (sim:* namespace)
mise run sim:run                                  # Main simulation entry point
mise run sim:trace                                # Time-series CSV + JSON output
mise run sim:sweep                                # Parameter sweep analysis
mise run sim:profile                              # cProfile performance analysis

# Tuning (tune:* namespace)
mise run tune:optuna                              # Bayesian optimization (Optuna TPE)
mise run tune:landscape                           # 2D parameter grid search
mise run tune:params                              # 1D sensitivity sweep
mise run tune:dashboard                           # Optuna Dashboard visualization

# QA (qa:* namespace)
mise run qa:audit                                 # Simulation health check
mise run qa:verify                                # Formula correctness verification
mise run qa:schemas                               # JSON schema validation
mise run qa:security                              # Dependency security audit

# Demo (demo:* namespace)
mise run demo:slice                               # Full pipeline demo (Engine->RAG->LLM)
mise run demo:persona                             # Persephone persona voice test
mise run demo:narrative                           # Narrative U-curve sweep

# Data (data:* namespace)
mise run data:ingest                              # Ingest Marxist corpus into ChromaDB
mise run data:db-init                             # Initialize SQLite database

# Documentation (docs:* namespace)
mise run docs:build                               # Build Sphinx documentation
mise run docs:live                                # Live-reload documentation server
mise run docs:strict                              # Build with warnings as errors

# UI
mise run ui                                       # Launch DearPyGui Synopticon dashboard

# Direct pytest (for specific tests)
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"                   # Pattern matching
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
- `src/babylon/engine/event_bus.py` - Publish/subscribe events (12 EventTypes)
- `src/babylon/engine/formula_registry.py` - 12 hot-swappable formulas
- `src/babylon/engine/simulation.py` - Stateful facade for multi-tick runs
- `src/babylon/engine/factories.py` - `create_proletariat()`, `create_bourgeoisie()`
- `src/babylon/engine/observer.py` - `SimulationObserver` protocol for state change notifications
- `src/babylon/engine/topology_monitor.py` - Phase transition detection via percolation theory
- `src/babylon/engine/systems/struggle.py` - George Floyd Dynamic (EXCESSIVE_FORCE, UPRISING events)
- `src/babylon/engine/systems/territory.py` - Carceral geography, heat dynamics, eviction pipeline
- `src/babylon/config/defines.py` - GameDefines (all tunable game coefficients)

**Observer System** (`src/babylon/engine/observer.py`):
- `SimulationObserver` - Protocol for state change notifications
- `SessionRecorder` - Black box recording for debugging/replay
- `EndgameDetector` - Detects simulation outcomes (IMPERIAL_COLLAPSE, etc.)
- `TopologyMonitor` - Phase transition detection via percolation theory

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

17 formulas in `src/babylon/systems/formulas.py`:

| Category | Formulas |
|----------|----------|
| Fundamental Theorem | `calculate_imperial_rent`, `calculate_labor_aristocracy_ratio`, `is_labor_aristocracy`, `calculate_consciousness_drift` |
| Survival Calculus | `calculate_acquiescence_probability`, `calculate_revolution_probability`, `calculate_crossover_threshold`, `apply_loss_aversion` |
| Unequal Exchange | `calculate_exchange_ratio`, `calculate_exploitation_rate`, `calculate_value_transfer`, `prebisch_singer_effect` |
| Solidarity | `calculate_solidarity_transmission`, `calculate_ideological_routing` |
| Dynamic Balance | `calculate_bourgeoisie_decision` |
| Metabolic Rift | `calculate_biocapacity_delta`, `calculate_overshoot_ratio` |

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/ChromaDB (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.unit        # Unit tests (default)
@pytest.mark.red_phase   # TDD RED phase (intentionally failing until GREEN)
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

## Test Constants Architecture

Test values are centralized in `tests/constants.py` using frozen dataclasses. See **ADR031** for full rationale.

**Pattern**:
```python
from tests.constants import TestConstants
TC = TestConstants

def test_worker_wealth(self) -> None:
    worker = create_worker(wealth=TC.Wealth.WORKER_BASELINE)
    assert worker.wealth == TC.Wealth.WORKER_BASELINE  # Semantic!
```

**Categories**: `Wealth`, `Probability`, `Ideology`, `Consciousness`, `Thresholds`, `Vitality`, `Organization`, `EconomicFlow`, `RevolutionaryFinance`, `MetabolicRift`, `TRPF`, `MarxCapitalExamples`

**Key Distinction - What to Extract vs Keep Inline**:

| Extract to Constants | Keep Inline |
|---------------------|-------------|
| Domain defaults (`DEFAULT_WEALTH = 10.0`) | Type boundaries (`0.0`, `1.0` for Probability) |
| Thresholds (`AWAKENING = 0.7`) | Edge cases (`-0.001` for "just below zero") |
| Scenario values (`PERIPHERY_WORKER = 20.0`) | Precision tests (`0.123456789` for quantization) |
| Theoretical values (`LOSS_AVERSION = 2.25`) | Computed results in assertions |

**Rationale**: Type boundary tests verify the TYPE DEFINITION itself. The values 0.0 and 1.0 ARE the Probability contract. Extracting them reduces clarity.

**Anti-Pattern**: Don't extract boundary values to constants:
```python
# BAD: Obscures what's being tested
assert Probability(TC.Probability.LOWER_BOUND) is valid

# GOOD: Boundary is self-documenting
assert Probability(0.0) is valid  # Lower bound of [0, 1]
```

## Test Infrastructure

**Factories** (`tests/factories/`):
- `DomainFactory`: Creates test entities with sensible defaults
- Pattern: Override only what matters for the test

**Fixtures** (`conftest.py` hierarchy):
- Root: Session-scoped infrastructure
- Per-domain: Domain-specific fixtures
- Avoid fixture duplication across conftest files

**TDD Markers**:
```python
@pytest.mark.red_phase  # Intentionally failing until GREEN phase
```

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

**Maintainability Refactoring Pattern**:
When refactoring to improve Maintainability Index (MI), move rich theory from function docstrings to RST files:

1. **Module docstring**: Keep theory summary, See Also cross-references
2. **Function docstring**: One-line summary + Args + Returns + minimal Example
3. **RST file** (`docs/reference/*.rst`): Full LaTeX formulas, historical context, code examples

This preserves rich documentation in Sphinx output while reducing LOC that penalizes MI scores.
The `ln(LOC)` term in MI formula treats docstrings and code equally.

**Why This Matters**: Sphinx autodoc generates API documentation from docstrings. Malformed docstrings produce warnings that block CI (we use `-W` flag). See `ai-docs/tooling.yaml` for configuration details.

## Mathematical Core

**Fundamental Theorem**: Revolution in Core impossible if W_c > V_c (wages > value produced). The difference is Imperial Rent (Phi).

**Survival Calculus**:
- P(S|A) = Sigmoid(Wealth - Subsistence) - survival by acquiescence
- P(S|R) = Organization / Repression - survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

**Bifurcation Formula**: When wages fall, agitation energy routes to either Fascism (+1 ideology) or Revolution (-1 ideology) based on SOLIDARITY edge presence.

**Heat Dynamics**: HIGH_PROFILE territories gain heat (state attention), LOW_PROFILE decays heat. Heat >=0.8 triggers eviction pipeline.

**Metabolic Rift**: Ecological limits on capital accumulation:
- Biocapacity Delta: ΔB = R - (E × η) where R=regeneration, E=extraction, η=entropy
- Overshoot Ratio: O = C / B where C=consumption, B=biocapacity (O>1 = ecological overshoot)

## Configuration: GameDefines

All tunable game coefficients are centralized in `GameDefines` (Pydantic model):

```python
from babylon.config.defines import GameDefines

defines = GameDefines()  # Load defaults from pyproject.toml [tool.babylon]
defines.economy.extraction_efficiency  # 0.8 default
defines.consciousness.drift_sensitivity_k  # Consciousness drift rate
```

Categories: `economy`, `consciousness`, `solidarity`, `survival`, `territory`

## Simulation Lab (Parameter Tuning)

The `tools/` directory contains analysis tooling for parameter optimization:

| Tool | Command | Purpose |
|------|---------|---------|
| `tune_agent.py` | `mise run tune` | Bayesian optimization via Optuna TPE with Hyperband pruning |
| `landscape_analysis.py` | `mise run map` | 2D parameter grid search (extraction × comprador cut) |
| `audit_simulation.py` | `mise run audit` | Health report with baseline/starvation/glut scenarios |
| `parameter_analysis.py` | `mise run analyze-trace` | Single simulation with time-series CSV + JSON metadata |

**Optimization Workflow**:
1. `mise run audit` - Validate simulation health under stress scenarios
2. `mise run map` - Visualize stability landscape for parameter pairs
3. `mise run tune` - Run Bayesian optimization to find optimal parameters
4. `mise run dashboard` - Visualize optimization results in Optuna Dashboard

Results are stored in `results/` (CSV, JSON) and `optuna.db` (SQLite study storage).

## Documentation

- Sphinx docs: `mise run docs-live` for development, `mise run docs` to build
- Design specs in `brainstorm/mechanics/`
- AI-readable specs in `ai-docs/` (YAML format) - **read `ai-docs/README.md` for catalog**
- Deferred ideas go to `brainstorm/deferred-ideas.md`
- Anti-patterns documented in `ai-docs/anti-patterns.yaml`

**Architecture Principle**: State is pure data. Engine is pure transformation. They never mix.

## Common Gotchas (from claude-mem)

These lessons emerged from debugging sessions and are preserved to prevent re-learning:

### WorldState.events is Per-Tick, NOT Cumulative

```python
# WRONG: Accumulating events across ticks
accumulated_events = accumulated_events + new_events
new_state = state.model_copy(update={"events": accumulated_events})

# RIGHT: Each tick gets fresh events
new_state = state.model_copy(update={"events": tick_events})
```

The simulation engine creates fresh WorldState each tick. `events` contains ONLY that tick's events. "No events this tick" = empty list `[]`, not duplicate events from previous tick.

### Graph Round-Trip Can Lose Mutations

`WorldState.to_graph()` → Systems mutate graph → `WorldState.from_graph()`

**Gotcha**: `from_graph()` excludes computed fields and uses model defaults for missing fields:
```python
# In from_graph(), these are excluded:
social_class_computed = {"consumption_needs"}
territory_excluded = {"p_acquiescence", "p_revolution"}
```

If you add a field to SocialClass, ensure `to_graph()` serializes it via `model_dump()` AND `from_graph()` doesn't exclude it.

**Gotcha**: Using `data.get("field", 0.0)` fallback masks missing field bugs:
```python
# This silently uses 0.0 if s_bio missing from graph node
consumption = data.get("s_bio", 0.0) + data.get("s_class", 0.0)
```

### Systems Mutate Shared Graph In-Place

Systems execute in strict order, each seeing previous systems' mutations:
```
ImperialRent → Solidarity → Consciousness → Survival → Struggle → Contradiction → Territory → Metabolism
```

Access node data via `graph.nodes[node_id]["wealth"]`, not model attributes.

### Mypy Misses Pydantic Attribute Errors

```python
# This passes mypy but fails at runtime:
snapshot: TopologySnapshot = monitor.history[-1]
phase = snapshot.phase  # AttributeError: 'TopologySnapshot' has no attribute 'phase'
```

Pydantic models use dynamic attributes that bypass static analysis. **Runtime tests are essential.**

### Immutability via model_copy()

WorldState is frozen. ALL mutations return new instances:
```python
# WRONG: Trying to mutate
state.tick = state.tick + 1  # Raises ValidationError

# RIGHT: Copy with updates
new_state = state.model_copy(update={"tick": state.tick + 1})
```

### Dependency Injection Over Discovery

```python
# WRONG: Discovering dependencies at runtime
def __init__(self):
    self.metrics = self._find_observer(MetricsCollector)  # Couples to internals

# RIGHT: Explicit injection
def __init__(self, metrics_collector: MetricsCollector):
    self.metrics = metrics_collector  # Testable, explicit
```

## CI Hygiene

**Fix Unrelated Issues When Encountered**: If CI reveals lint/type errors in files you didn't modify, fix them. Don't leave broken windows.

**Import Order Matters**:
```python
# Correct order to avoid E402 (module level import not at top)
from __future__ import annotations

import pytest                          # stdlib first
from pydantic import ValidationError   # third-party second

from babylon.models import SocialClass # local imports third
from tests.constants import TestConstants
TC = TestConstants                      # alias AFTER all imports
```

**Maintain `__all__` Exports**: When adding public functions to a package, update `__init__.py`:
```python
__all__ = [
    "existing_function",
    "new_function",  # Add new exports here
]
```

**Type Ignore Comments**: Use specific error codes, not blanket ignores:
```python
# GOOD: Specific error code
import dearpygui.dearpygui as dpg  # type: ignore[import-untyped]

# BAD: Blanket ignore
import something  # type: ignore
```

## Session Continuity

**claude-mem Integration**: This project uses claude-mem for cross-session memory. Discoveries, decisions, and features are automatically recorded.

**Before Re-investigating**:
- Search claude-mem for prior work on the topic
- Check ai-docs/decisions.yaml for relevant ADRs
- Review ai-docs/state.yaml for current project status

**After Completing Significant Work**:
1. Update `ai-docs/state.yaml` with new status/test counts
2. Create ADR in `ai-docs/decisions.yaml` for architectural patterns
3. Update `ai-docs/roadmap.md` if milestones changed

**ADR Format** (in decisions.yaml):
```yaml
ADR0XX_descriptive_name:
  status: "accepted"
  date: "YYYY-MM-DD"
  title: "Short descriptive title"
  context: |
    What problem were we solving?
  decision: |
    What did we decide?
  rationale:
    key_point: "Why this approach?"
  consequences:
    positive:
      - "Benefit 1"
    negative:
      - "Tradeoff 1"
```
