# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**Name**: Babylon - The Fall of America
**Concept**: Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory
**Objective**: Model class struggle as deterministic output of material conditions within a compact topological phase space
**Mantra**: Graph + Math = History

## Commands

```bash
# Setup
poetry install
poetry run pre-commit install

# Testing (strict separation)
poetry run pytest -m "not ai"                              # Fast math/logic tests (704 total)
poetry run pytest -m "ai"                                   # Slow AI/narrative evals
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"                   # Pattern matching

# Linting & Type Checking
poetry run ruff check . --fix
poetry run ruff format .
poetry run mypy src

# Data Validation
poetry run python tools/validate_schemas.py
```

## Architecture: The Embedded Trinity

Three-layer local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) - `src/babylon/data/game/`
   - Rigid material state: 17 JSON entity collections
   - Validated against JSON Schema Draft 2020-12

2. **The Topology** (NetworkX) - `src/babylon/models/world_state.py`
   - Fluid relational state via `to_graph()`/`from_graph()`
   - Entities as nodes, relationships as edges

3. **The Archive** (ChromaDB) - `src/babylon/rag/`
   - Semantic history for AI narrative generation
   - AI observes state changes, never controls mechanics

## Engine Architecture (Phase 2 Complete)

The simulation engine uses modular Systems with dependency injection:

```
step(WorldState, SimulationConfig) → WorldState
     │
     ▼
SimulationEngine.run_tick(graph, services, context)
     │
     ├── 1. ImperialRentSystem   (economic.py)    - Wealth extraction
     ├── 2. ConsciousnessSystem  (ideology.py)    - Ideology drift
     ├── 3. SurvivalSystem       (survival.py)    - P(S|A), P(S|R)
     └── 4. ContradictionSystem  (contradiction.py) - Tension/rupture
```

**Key Components**:
- `src/babylon/engine/simulation_engine.py` - Orchestrates Systems
- `src/babylon/engine/services.py` - ServiceContainer (DI container)
- `src/babylon/engine/event_bus.py` - Publish/subscribe events
- `src/babylon/engine/formula_registry.py` - 12 hot-swappable formulas
- `src/babylon/engine/simulation.py` - Stateful facade for multi-tick runs
- `src/babylon/engine/factories.py` - `create_proletariat()`, `create_bourgeoisie()`

## Type System

All game entities use Pydantic models with constrained types:

```python
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType
from babylon.models import SocialClass, Relationship, WorldState, SimulationConfig
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
```

## Coding Standards

- **Pydantic First**: All game objects as `pydantic.BaseModel`, no raw dicts
- **Constrained Types**: Use `Probability`, `Currency`, `Intensity` instead of raw floats
- **Data-Driven**: Game logic in JSON data files, not hardcoded conditionals
- **Strict Typing**: MyPy strict mode, explicit return types
- **TDD**: Red-Green-Refactor cycle mandatory
- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, `refactor:` prefixes

## Mathematical Core

**Fundamental Theorem**: Revolution in Core impossible if W_c > V_c (wages > value produced). The difference is Imperial Rent (Φ).

**Survival Calculus**:
- P(S|A) = Sigmoid(Wealth - Subsistence) — survival by acquiescence
- P(S|R) = Organization / Repression — survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

## Current State

**Phase 2: COMPLETE** - 704 tests passing, modular System architecture with proven feedback loops.

**Next: Phase 3 - Observer Pattern** - AI narrates state changes (read-only). Prerequisites complete: EventBus, ServiceContainer, History system.

## Documentation

Machine-readable docs for AI assistants in `ai-docs/`:
- `state.yaml` - Current implementation status and sprint history
- `architecture.yaml` - System structure and data flow
- `formulas-spec.yaml` - All 12 formulas with signatures
- `decisions.yaml` - Architecture Decision Records (ADR001-ADR013)
- `ontology.yaml` - Domain term definitions

## Idea Management

Deferred ideas go to `brainstorm/deferred-ideas.md` tagged by phase. If it's not in `ai-docs/state.yaml:next_steps`, it's quarantine.

**Architecture Principle**: State is pure data. Engine is pure transformation. They never mix.
