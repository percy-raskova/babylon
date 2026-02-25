# Quickstart: Capital Volume I Production Dynamics

**Feature**: 021-capital-volume-i

---

## What This Feature Does

Adds three production dynamics mechanisms from Marx's Capital Volume I to the Babylon simulation engine:

1. **Reserve Army of Labor** — Unemployment composition that disciplines wages
2. **Dispossession Events** — Aggregate tracking of ongoing primitive accumulation
3. **Working Day Classification** — Absolute vs. relative surplus value extraction

Plus five data loaders for empirical calibration against the Detroit metro case study.

## Architecture At a Glance

```
Data Loaders (5)
  BLS Unemployment → FactBLSUnemploymentDecomposition
  Eviction Lab     → FactEvictionLabFiling
  Foreclosure      → FactForeclosureRate
  Census Housing   → FactCensusInstitutionalOwnership
  BLS Productivity → FactBLSProductivity
        │
        ▼
Simulation Systems (2 new)
  #17 ReserveArmySystem      → reads unemployment data, applies wage pressure
  #18 DispossessionEventSystem → reads dispossession data, emits events, tracks transfers
        │
        ▼
Integration Points (3)
  CountyEconomicState.median_wage ← wage pressure from reserve army
  DefaultClassTransitionEngine    ← dispossession rates from new data source
  ConsciousnessSystem             ← exploitation visibility modifier from working day
```

## Key Files to Create

### Domain Models
- `src/babylon/economics/reserve_army/types.py` — ReserveArmyState, ReserveArmyDynamics
- `src/babylon/economics/reserve_army/calculator.py` — WagePressureCalculator
- `src/babylon/economics/dispossession/types.py` — DispossessionEvent, TerritoryDispossessionState, DispossessionType
- `src/babylon/economics/working_day/types.py` — WorkingDayState, ExploitationMode
- `src/babylon/economics/working_day/classifier.py` — DefaultWorkingDayClassifier

### Systems
- `src/babylon/engine/systems/reserve_army.py` — ReserveArmySystem (System #17)
- `src/babylon/engine/systems/dispossession_events.py` — DispossessionEventSystem (System #18)

### Data Loaders
- `src/babylon/data/bls_unemployment/loader.py`
- `src/babylon/data/eviction_lab/loader.py`
- `src/babylon/data/foreclosure/loader.py`
- `src/babylon/data/census_housing/loader.py`
- `src/babylon/data/bls_productivity/loader.py`

### Schema Extensions
- `src/babylon/data/reference/schema.py` — 5 new fact tables

### Configuration
- `src/babylon/config/defines.py` — ReserveArmyDefines, DispossessionDefines, WorkingDayDefines

## Running After Implementation

```bash
# Load data
mise run data:bls-unemployment   # Load BLS unemployment decompositions
mise run data:eviction-lab       # Load Eviction Lab filings
mise run data:foreclosure        # Load foreclosure rates
mise run data:census-housing     # Load Census housing data
mise run data:bls-productivity   # Load BLS hours/productivity

# Run simulation with new systems
mise run sim:run                 # All 18 systems execute in order

# Verify
mise run test:unit               # Reserve army + dispossession + working day tests
mise run qa:verify               # Formula correctness including wage pressure
```
