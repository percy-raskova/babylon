# Quickstart: Simulation Tick Dynamics (Feature 017)

**Date**: 2026-02-06
**Feature**: 017-simulation-tick-dynamics

## What This Feature Does

Feature 017 orchestrates all prior economic calculators (Features 012-016) into a unified per-tick state evolution pipeline, integrated as a System in the engine's materialist causality chain. It takes county-level economic data from the shared graph, runs an 8-step update pipeline on year boundaries, and writes results back to the graph for downstream Systems to consume.

## Key Concepts

### Engine System Integration

The `TickDynamicsSystem` conforms to the engine's System protocol (`step(graph, services, context) -> None`) and is registered in `_DEFAULT_SYSTEMS` after ProductionSystem and before ImperialRentSystem. Economics calculators are injected via the extended ServiceContainer.

### Two Modes

1. **Initialization**: Seeds the initial state from census data (QCEW, BEA, ATUS, FRED/BLS). Data gaps are expected and handled via NoDataSentinel.
2. **Simulation**: Executes tick pipeline within the engine's System chain. The engine produces ALL county values -- no external data queries during simulation ticks.

### Timescale Bridging

The engine operates at weekly timescale (~52 ticks/year). The TickDynamicsSystem gates full pipeline execution to year boundaries (`context.tick % weeks_per_year == 0`). On intermediate weekly ticks, cached annual results remain in the graph without re-computation.

### Tick Pipeline (8 Steps)

1. Load economic data (initialization only)
2. Compute national parameters (tau, gamma_basket, gamma_III)
3. Two parallel branches after Step 2:
   - **3a.** Compute county-level state (K, pi, D per county)
   - **3b.** Apply coefficient smoothing (alpha-smooth gamma values)
4. Compute imperial rent flows (phi_hour per county)
5. Check dispossession triggers (crisis flag)
6. Simulate class transitions (Feature 016 engine)
7. Validate sum-to-one invariant and commit class distribution
8. Compute derived rates (r, OCC, e, Phi_aggregate)

### Coefficient vs Quantity

- **Quantities** (T, K, unemployment, wages): Update to new values each tick
- **Coefficients** (gamma_basket, gamma_III): Update via alpha-smoothing for stability

## Module Location

```
src/babylon/economics/tick/
    __init__.py           # Public API: TickDynamicsSystem + factory
    types.py              # SimulationTickState, NationalTickParameters, etc.
    system.py             # TickDynamicsSystem (System protocol implementation)
    initializer.py        # Census data initialization logic
    smoothing.py          # Alpha-smoothing for coefficients
    crisis_detector.py    # Threshold-based crisis detection
    derived_rates.py      # Profit rate, OCC, exploitation rate computation
    precarity.py          # Precarity indicator derivation from class state
    graph_bridge.py       # Read/write tick state from/to NetworkX graph

src/babylon/engine/services.py  # Extended with economics calculator fields

tests/unit/economics/tick/
    conftest.py           # Mock calculators, graph builders, fixtures
    test_types.py         # Model validation tests
    test_system.py        # TickDynamicsSystem step() tests
    test_initializer.py   # Census data seeding tests
    test_smoothing.py     # Alpha-smoothing tests
    test_crisis.py        # Crisis detection tests
    test_derived.py       # Derived rate computation tests
    test_precarity.py     # Precarity derivation tests

tests/integration/economics/
    test_tick_integration.py  # Multi-tick pipeline, engine integration tests
```

## Usage Pattern

### Register System in Engine

```python
from babylon.economics.tick import TickDynamicsSystem
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS

# TickDynamicsSystem is registered in _DEFAULT_SYSTEMS at module level:
# _DEFAULT_SYSTEMS = [
#     VitalitySystem(),
#     TerritorySystem(),
#     ProductionSystem(),
#     TickDynamicsSystem(),    # <-- After Production, before ImperialRent
#     SolidaritySystem(),
#     ImperialRentSystem(),
#     ...
# ]
```

### Create ServiceContainer with Economics Calculators

```python
from babylon.engine.services import ServiceContainer

services = ServiceContainer.create(
    config=config,
    defines=defines,
    melt_calculator=melt_calc,
    basket_calculator=basket_calc,
    gamma_calculator=gamma_calc,
    capital_calculator=capital_calc,
    throughput_calculator=throughput_calc,
    transition_engine=transition_engine,
    imperial_rent_calculator=rent_calc,
)
```

### Initialize from Census Data

```python
from babylon.economics.tick import DefaultTickInitializer, write_tick_state_to_graph

# Seed initial state from census data via ServiceContainer
initializer = DefaultTickInitializer()
initial_state = initializer.initialize(
    year=2010,
    county_fips=["26163", "26125", "36061"],
    services=services,  # ServiceContainer with calculator fields set
)

# Write initial state to graph for engine consumption
graph = world_state.to_graph()
write_tick_state_to_graph(graph, initial_state)
```

### Access Tick Data from Graph (Downstream Systems)

```python
# In another System's step() method:
def step(self, graph, services, context):
    tick_data = graph.graph.get("tick_dynamics", {})
    national_melt = tick_data.get("national_params", {}).get("tau")

    # Access county data from Territory nodes
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "territory":
            capital_stock = data.get("tick_capital_stock", 0.0)
            crisis = data.get("tick_crisis", False)
```

### Access Tick Summary

```python
tick_data = graph.graph.get("tick_dynamics", {})
summary = tick_data.get("tick_summary")
# summary.year, summary.counties_processed, summary.phi_aggregate, etc.
```

## Dependencies

Feature 017 depends on all prior economics features and the engine infrastructure:

| Feature | What It Provides | Used For |
|---------|-----------------|----------|
| 011 | TensorRegistry, ValueTensor4x3 | County value tensors |
| 012 | CapitalStockCalculator | Capital stock K, profit rate |
| 013 | MELTCalculator, BasketVisibilityCalculator, ImperialRentCalculator | National MELT, gamma_basket, phi_hour |
| 014 | ThroughputCalculator | County throughput position pi |
| 015 | GammaIIICalculator | Reproductive visibility gamma_III |
| 016 | ClassTransitionEngine | Class distribution evolution |
| Engine | System protocol, ServiceContainer, SimulationEngine | Integration infrastructure |

## Testing

```bash
# Unit tests
poetry run pytest tests/unit/economics/tick/ -v

# Integration tests (including engine integration)
poetry run pytest tests/integration/economics/test_tick_integration.py -v

# All economics tests
poetry run pytest tests/ -k "economics" -v
```
