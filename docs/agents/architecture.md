# Architecture

## The Embedded Trinity

Three-layer local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) — `src/babylon/data/game/`

   - Rigid material state: 17 JSON entity collections
   - Validated against JSON Schema Draft 2020-12

1. **The Topology** (NetworkX) — `src/babylon/models/world_state.py`

   - Fluid relational state via `to_graph()` / `from_graph()`
   - Node types: `SocialClass` (entities), `Territory` (spatial)
   - Edges: EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, TENANCY, ADJACENCY

1. **The Archive** (ChromaDB) — `src/babylon/rag/`

   - Semantic history for AI narrative generation
   - AI observes state changes, never controls mechanics

## Engine Architecture

Modular Systems with dependency injection:

```
step(WorldState, SimulationConfig) -> WorldState
     |
     v
SimulationEngine.run_tick(graph, services, context)
     |
     +-- 1. ImperialRentSystem   (economic.py)
     +-- 2. SolidaritySystem     (solidarity.py)
     +-- 3. ConsciousnessSystem  (ideology.py)
     +-- 4. SurvivalSystem       (survival.py)
     +-- 5. StruggleSystem       (struggle.py)
     +-- 6. ContradictionSystem  (contradiction.py)
     +-- 7. TerritorySystem      (territory.py)
     +-- 8. MetabolismSystem     (metabolism.py)
```

**Key principle**: State is pure data. Engine is pure transformation. They never mix.

## Type System

All game entities use Pydantic models with constrained types:

```python
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType
from babylon.models import SocialClass, Territory, Relationship, WorldState, SimulationConfig
```

## Formula System

17 formulas in `src/babylon/formulas/formulas.py`:

| Category            | Formulas                                                                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Fundamental Theorem | `calculate_imperial_rent`, `calculate_labor_aristocracy_ratio`, `is_labor_aristocracy`, `calculate_consciousness_drift`          |
| Survival Calculus   | `calculate_acquiescence_probability`, `calculate_revolution_probability`, `calculate_crossover_threshold`, `apply_loss_aversion` |
| Unequal Exchange    | `calculate_exchange_ratio`, `calculate_exploitation_rate`, `calculate_value_transfer`, `prebisch_singer_effect`                  |
| Solidarity          | `calculate_solidarity_transmission`, `calculate_ideological_routing`                                                             |
| Dynamic Balance     | `calculate_bourgeoisie_decision`                                                                                                 |
| Metabolic Rift      | `calculate_biocapacity_delta`, `calculate_overshoot_ratio`                                                                       |

## Configuration

All tunable coefficients in `GameDefines` (Pydantic model):

```python
from babylon.config.defines import GameDefines
defines = GameDefines()  # Load from pyproject.toml [tool.babylon]
defines.economy.extraction_efficiency  # 0.8 default
```

Categories: `economy`, `consciousness`, `solidarity`, `survival`, `territory`
