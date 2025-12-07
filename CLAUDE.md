# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**Name**: Babylon - The Fall of America
**Concept**: Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW theory and topological manifolds
**Objective**: Model class struggle as deterministic output of material conditions within a compact topological phase space

## Commands

```bash
# Setup
poetry install
poetry run pre-commit install

# Testing (strict separation)
poetry run pytest -m "not ai"           # Fast math/logic tests (TDD)
poetry run pytest -m "ai"               # Slow AI/narrative evals
poetry run pytest tests/unit/test_foo.py::test_specific  # Single test

# Linting & Type Checking
poetry run ruff check . --fix
poetry run ruff format .
poetry run mypy src

# Data Validation
poetry run python tools/validate_schemas.py      # Validate JSON against schemas
```

## Architecture: The Embedded Trinity

Three-pillar local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) - `src/babylon/data/`
   - Rigid material state: economics, resources, turn history
   - JSON data files validated against JSON Schema Draft 2020-12

2. **The Topology** (NetworkX) - `src/babylon/systems/`
   - Fluid relational state: class solidarity, tension, contradiction dynamics
   - `ContradictionAnalysis` tracks tensions and phase transitions

3. **The Archive** (ChromaDB) - `src/babylon/rag/`
   - Semantic history and theory (RAG)
   - AI as Observer: generates narrative from state, doesn't control math

## Type System (Sprint 1 & 2 Complete)

All game entities use Pydantic models with constrained types:

```python
# Import constrained types
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient, Ratio

# Import enums
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType

# Import Phase 1 entity models
from babylon.models import SocialClass, Relationship

# Import other entity models
from babylon.models import Effect, ContradictionState, Contradiction, Trigger
```

**Location**: `src/babylon/models/`
- `types.py` - Constrained float types with validation
- `enums.py` - StrEnum definitions for categorical values
- `entities/` - Pydantic models for game objects
  - `social_class.py` - Phase 1 node (SocialClass)
  - `relationship.py` - Phase 1 edge (Relationship)

## Formula System (Implemented)

All mathematical formulas exist in `src/babylon/systems/formulas.py` with 40 passing tests:

- `calculate_imperial_rent()` - Value extraction (Φ = α × Wp × (1 - Ψp))
- `calculate_acquiescence_probability()` - P(S|A) sigmoid survival
- `calculate_revolution_probability()` - P(S|R) based on organization/repression
- `calculate_crossover_threshold()` - When revolt becomes rational
- `calculate_labor_aristocracy_ratio()` - Wc/Vc ratio
- `calculate_consciousness_drift()` - dΨ/dt ideology change

## Contradiction Engine

`src/babylon/systems/contradiction_analysis.py` - The dialectical engine:
- `ContradictionState` - Tracks tension, momentum, thesis/antithesis
- `ContradictionAnalysis` - Registers contradictions, propagates tension, triggers resolutions
- When tension reaches 1.0 → rupture; when it reaches 0.0 → synthesis

## Current Focus

**Phase 1: COMPLETE** - Two nodes, one edge, proven equations (202 tests passing).

**Next: Phase 2 - Topological Engine** - The physics/update loop.

Check `ai-docs/state.yaml` for current implementation status and `brainstorm/plans/four-phase-engine-blueprint.md` for the roadmap.

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state (fast, deterministic)
@pytest.mark.topology    # Graph/network operations (fast, deterministic)
@pytest.mark.integration # Database/ChromaDB (medium, I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
```

## Coding Standards

- **Pydantic First**: All game objects as `pydantic.BaseModel`, no raw dicts
- **Use Sprint 1 Types**: `Probability`, `Currency`, `Intensity` instead of raw floats
- **Data-Driven**: Logic in JSON/TOML, not hardcoded conditionals
- **Strict Typing**: MyPy strict mode, explicit return types
- **TDD**: Red-Green-Refactor cycle mandatory

## Mathematical Core

**Fundamental Theorem**: Revolution in Core impossible if W_c > V_c (wages > value produced). Difference = Imperial Rent (Φ).

**Survival Calculus**: P(S|A) = Sigmoid(Wealth - Subsistence), P(S|R) = Organization/Repression. Rupture when P(S|R) > P(S|A).

## Idea Management

Good ideas go to `brainstorm/deferred-ideas.md` tagged by phase. If it's not in `ai-docs/state.yaml:next_steps`, it's quarantine.

**Mantra**: Two nodes. One edge. Passing tests. Ship.
