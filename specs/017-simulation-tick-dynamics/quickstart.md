# Quickstart: Simulation Tick Dynamics (Feature 017)

**Date**: 2026-02-06
**Feature**: 017-simulation-tick-dynamics

## What This Feature Does

Feature 017 orchestrates all prior economic calculators (Features 012-016) into a unified per-tick state evolution pipeline. It takes a complete simulation state at year t, runs an 8-step update pipeline, and produces the state at year t+1.

## Key Concepts

### Two Modes

1. **Initialization**: Seeds the initial `SimulationTickState` from census data (QCEW, BEA, ATUS, FRED/BLS). Data gaps are expected and handled via NoDataSentinel.
2. **Simulation**: Executes tick pipeline. The engine produces ALL county values -- no external data queries during simulation ticks.

### Tick Pipeline (8 Steps)

1. Load economic data (initialization only)
2. Compute national parameters (tau, gamma_basket, gamma_III)
3. Compute county-level state (K, pi, D per county)
4. Compute imperial rent flows (phi_hour per county)
5. Check dispossession triggers (crisis flag)
6. Simulate class transitions (Feature 016 engine)
7. Update class distribution (validate invariant)
8. Compute derived rates (r, OCC, e, Phi_aggregate)

### Coefficient vs Quantity

- **Quantities** (T, K, unemployment, wages): Update to new values each tick
- **Coefficients** (gamma_basket, gamma_III): Update via alpha-smoothing for stability

## Module Location

```
src/babylon/economics/tick/
    __init__.py           # Public API: TickSimulator protocol + factory
    types.py              # SimulationTickState, NationalTickParameters, etc.
    simulator.py          # DefaultTickSimulator implementation
    initializer.py        # Census data initialization logic
    smoothing.py          # Alpha-smoothing for coefficients
    crisis_detector.py    # Threshold-based crisis detection
    derived_rates.py      # Profit rate, OCC, exploitation rate computation
    precarity.py          # Precarity indicator derivation from class state

tests/unit/economics/tick/
    conftest.py           # Mock calculators, fixtures
    test_types.py         # Model validation tests
    test_simulator.py     # Single-tick execution tests
    test_initializer.py   # Census data seeding tests
    test_smoothing.py     # Alpha-smoothing tests
    test_crisis.py        # Crisis detection tests
    test_derived.py       # Derived rate computation tests
    test_precarity.py     # Precarity derivation tests

tests/integration/economics/
    test_tick_integration.py  # Multi-tick pipeline tests
```

## Usage Pattern

### Initialize from Census Data

```python
from babylon.economics.tick import create_tick_simulator, TickInitializer

# Build simulator with all calculator dependencies
simulator = create_tick_simulator(
    melt_calculator=melt_calc,
    basket_calculator=basket_calc,
    gamma_calculator=gamma_calc,
    capital_calculator=capital_calc,
    throughput_calculator=throughput_calc,
    transition_engine=transition_engine,
    imperial_rent_calculator=rent_calc,
)

# Seed initial state from census data
initializer = TickInitializer(
    melt_calculator=melt_calc,
    capital_calculator=capital_calc,
    throughput_calculator=throughput_calc,
)
initial_state = initializer.initialize(
    year=2010,
    county_fips=["26163", "26125", "36061", ...],
)
```

### Execute Single Tick

```python
# Advance one year
next_state = simulator.tick(initial_state)
assert next_state.year == 2011
assert all(
    cs.class_distribution.total_share_check()
    for cs in next_state.county_states.values()
)
```

### Execute Multi-Tick Simulation

```python
# Run 2010-2024
state = initial_state
history: list[SimulationTickState] = [state]

for _ in range(14):
    state = simulator.tick(state)
    history.append(state)

# Validate final distribution
final_dist = state.tick_summary.national_class_distribution
assert 0.30 <= final_dist["labor_aristocracy"] <= 0.50
```

### Access Tick Summary

```python
summary = state.tick_summary
print(f"Year: {summary.year}")
print(f"Counties: {summary.counties_processed}")
print(f"Phi_aggregate: ${summary.phi_aggregate:,.0f}")
print(f"Mean profit rate: {summary.mean_profit_rate:.4f}")
```

## Dependencies

Feature 017 depends on all prior economics features:

| Feature | What It Provides | Used For |
|---------|-----------------|----------|
| 011 | TensorRegistry, ValueTensor4x3 | County value tensors |
| 012 | CapitalStockCalculator | Capital stock K, profit rate |
| 013 | MELTCalculator, BasketVisibilityCalculator, ImperialRentCalculator | National MELT, gamma_basket, phi_hour |
| 014 | ThroughputCalculator | County throughput position pi |
| 015 | GammaIIICalculator | Reproductive visibility gamma_III |
| 016 | ClassTransitionEngine | Class distribution evolution |

## Testing

```bash
# Unit tests
poetry run pytest tests/unit/economics/tick/ -v

# Integration tests
poetry run pytest tests/integration/economics/test_tick_integration.py -v

# All economics tests
poetry run pytest tests/ -k "economics" -v
```
