# Project Structure

This page provides an overview of the Babylon project's codebase organization and key components.

## Directory Structure

```
src/babylon/
├── __main__.py           # Entry point
├── exceptions.py         # Custom exception classes
├── ai/                   # AI/narrative components
├── config/               # Configuration (GameDefines, logging)
│   └── defines.py        # Tunable game coefficients
├── data/game/            # JSON entity definitions (17 collections)
├── engine/               # Simulation engine
│   ├── simulation_engine.py  # Core step() function
│   ├── simulation.py     # Stateful Simulation facade
│   ├── services.py       # ServiceContainer (DI)
│   ├── event_bus.py      # Publish/subscribe events
│   ├── formula_registry.py  # Hot-swappable formulas
│   ├── factories.py      # Entity factories
│   ├── scenarios.py      # Scenario creation
│   ├── observer.py       # SimulationObserver protocol
│   ├── topology_monitor.py  # Condensation monitor (percolation)
│   ├── history/          # Undo/redo, checkpointing
│   └── systems/          # Orchestrated by SimulationEngine
│       ├── economic.py   # Imperial rent extraction
│       ├── ideology.py   # Consciousness drift
│       ├── solidarity.py # Solidarity transmission
│       ├── survival.py   # P(S|A), P(S|R) calculations
│       ├── contradiction.py  # Tension/rupture dynamics
│       ├── territory.py  # Heat, eviction, displacement
│       └── struggle.py   # Agency layer (EXCESSIVE_FORCE → UPRISING)
├── models/               # Pydantic entities
│   ├── entities/         # SocialClass, Territory, Relationship, etc.
│   ├── config.py         # SimulationConfig
│   ├── enums.py          # EdgeType, SocialRole, IntensityLevel
│   ├── types.py          # Probability, Currency, Intensity
│   └── world_state.py    # WorldState (graph serialization)
├── systems/              # Formula implementations
│   └── formulas.py       # 12 core formulas
├── rag/                  # Retrieval Augmented Generation
│   └── retrieval.py      # ChromaDB integration
├── metrics/              # Performance tracking
├── schemas/              # JSON Schema definitions
└── utils/                # Utility functions

tests/
├── unit/                 # Fast deterministic tests
│   ├── engine/           # Engine tests
│   ├── models/           # Model tests
│   └── topology/         # TopologyMonitor tests
└── integration/          # Full simulation tests

docs/                     # Documentation
├── wiki/                 # Wiki pages
├── census/               # Census data references
└── character_sheets/     # Narrative content

ai-docs/                  # Machine-readable YAML specs
brainstorm/               # Design documents
```

## Core Systems

### Simulation Engine

Located in `src/babylon/engine/`, the engine orchestrates game mechanics:

- **simulation_engine.py**: The `step()` function for state transformation
- **simulation.py**: Stateful facade for multi-tick runs with history
- **services.py**: Dependency injection container (ServiceContainer)
- **event_bus.py**: Publish/subscribe event system

### Systems (Game Mechanics)

Located in `src/babylon/engine/systems/`, modular systems process each tick:

| System | Purpose |
|--------|---------|
| `economic.py` | Imperial rent extraction via EXPLOITATION edges |
| `ideology.py` | Consciousness drift and George Jackson bifurcation |
| `solidarity.py` | Solidarity transmission via SOLIDARITY edges |
| `survival.py` | Survival calculus: P(S|A), P(S|R) |
| `contradiction.py` | Tension accumulation and rupture detection |
| `territory.py` | Heat, eviction, displacement routing |
| `struggle.py` | Agency layer (EXCESSIVE_FORCE → UPRISING) |

### Pydantic Models

Located in `src/babylon/models/`, all game entities use Pydantic:

- **SocialClass**: Represents proletariat, bourgeoisie, lumpen, etc.
- **Territory**: Spatial substrate with heat, operational profiles
- **Relationship**: Edges (EXPLOITATION, SOLIDARITY, WAGES, etc.)
- **WorldState**: Container with `to_graph()`/`from_graph()` methods

### Formula System

Located in `src/babylon/systems/formulas.py`, 12 core formulas:

- **Fundamental Theorem**: `calculate_imperial_rent`, `calculate_labor_aristocracy_ratio`
- **Survival Calculus**: `calculate_acquiescence_probability`, `calculate_revolution_probability`
- **Unequal Exchange**: `calculate_exchange_ratio`, `calculate_value_transfer`

### RAG System

Located in `src/babylon/rag/`, provides ChromaDB integration for semantic history and AI narrative generation.

## Configuration

Game coefficients are centralized in `GameDefines` (`src/babylon/config/defines.py`):

```python
from babylon.config.defines import GameDefines

defines = GameDefines()
defines.economy.extraction_efficiency  # 0.8 default
defines.consciousness.drift_sensitivity_k
```

## Testing

The project uses pytest with markers:

```bash
poetry run pytest -m "not ai"     # Fast tests (default)
poetry run pytest -m "ai"         # AI evaluation tests
poetry run pytest -m "topology"   # Topology/graph tests
```

## Documentation

| Location | Content |
|----------|---------|
| `ai-docs/` | Machine-readable YAML specifications |
| `brainstorm/` | Design documents and mechanics specs |
| `docs/` | Sphinx documentation |
