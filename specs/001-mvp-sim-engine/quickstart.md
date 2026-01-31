# Quickstart: MVP Simulation Engine

**Feature**: 001-mvp-sim-engine **Date**: 2026-01-30

## Overview

This guide demonstrates how to use the MVP simulation engine for GUI development.

## Installation

The MVP simulation engine is part of the Babylon package. Ensure you have the project set up:

```bash
cd babylon
poetry install
```

## Basic Usage

### Initialize and Run

```python
from babylon.engine.simulation import Simulation

# Create simulation with Detroit test case
sim = Simulation.from_sqlite(
    fips_codes=["26163", "26125"],  # Wayne County, Oakland County
    year=2022
)

# Get initial state
snapshot = sim.get_snapshot()
print(f"Tick: {snapshot.tick}")
print(f"Territories: {list(snapshot.territories.keys())}")

# Run one tick
sim.step()

# Get updated state
snapshot = sim.get_snapshot()
print(f"Tick: {snapshot.tick}")
```

### Query Territory State

```python
# Get Wayne County state
wayne = sim.get_territory_state("26163")
if wayne:
    print(f"Wayne County profit rate: {wayne.profit_rate}")
    print(f"Wayne County hex claims: {len(wayne.hex_claims)} cells")

# Get Oakland County state
oakland = sim.get_territory_state("26125")
if oakland:
    print(f"Oakland County profit rate: {oakland.profit_rate}")
```

### GUI Readiness Test

This test validates that the simulation is ready for GUI development:

```python
from babylon.engine.simulation import Simulation

# Initialize
sim = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)

# Get initial state
state = sim.get_snapshot()
territory = state.territories["26163"]
initial_profit_rate = territory.profit_rate

print(f"Initial profit_rate: {initial_profit_rate}")
print(f"Hex claims: {territory.hex_claims}")

# Step and verify change
sim.step()
state = sim.get_snapshot()
territory = state.territories["26163"]

assert territory.profit_rate != initial_profit_rate, "profit_rate should change after step()"
print(f"After step: {territory.profit_rate}")
print("GUI readiness test PASSED")
```

### Using Protocols for Type Safety

GUI code should depend only on protocol types:

```python
from babylon.protocols import SimulationState, SimulationControl

def render_territories(sim: SimulationState) -> None:
    """Render all territories. GUI code depends only on protocol."""
    snapshot = sim.get_snapshot()
    for territory_id, state in snapshot.territories.items():
        print(f"{territory_id}: r={state.profit_rate:.4f}, hexes={len(state.hex_claims)}")

def step_simulation(sim: SimulationControl) -> None:
    """Advance simulation. GUI code depends only on protocol."""
    sim.step()

# Usage
from babylon.engine.simulation import Simulation

sim = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)
render_territories(sim)  # Works because Simulation implements SimulationState
step_simulation(sim)     # Works because Simulation implements SimulationControl
render_territories(sim)
```

### Reset to Initial State

```python
sim = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)

# Run 100 ticks
sim.step(100)
print(f"After 100 ticks: {sim.get_current_tick()}")

# Reset to tick 0
sim.reset()
print(f"After reset: {sim.get_current_tick()}")
```

## Data Sources

The simulation initializes from the SQLite reference database:

| Table | Purpose | | ------------------ | ------------------------------------- | | `dim_county` | County metadata
(FIPS, name) | | `fact_qcew` | Wage data for profit rate computation | | `bridge_county_h3` | H3 hex indices for spatial
mapping |

Ensure the reference database is populated:

```bash
# Check database exists
ls data/sqlite/marxist-data-3NF.sqlite

# Verify data for Detroit test case
sqlite3 data/sqlite/marxist-data-3NF.sqlite \
  "SELECT fips, county_name FROM dim_county WHERE fips IN ('26163', '26125')"
```

## Determinism Verification

```python
from babylon.engine.simulation import Simulation

# Create two identical simulations
sim1 = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)
sim2 = Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)

# Run 100 ticks on each
sim1.step(100)
sim2.step(100)

# Verify identical results
for tid in ["26163", "26125"]:
    r1 = sim1.get_territory_state(tid).profit_rate
    r2 = sim2.get_territory_state(tid).profit_rate
    assert r1 == r2, f"Determinism violation for {tid}: {r1} != {r2}"

print("Determinism test PASSED")
```

## Troubleshooting

### Database Not Found

```text
FileNotFoundError: data/sqlite/marxist-data-3NF.sqlite
```

**Solution**: Run the data loaders to populate the reference database:

```bash
poetry run python -m babylon.data.loaders
```

### Missing County Data

```text
ValueError: No QCEW data for county 26163 in year 2022
```

**Solution**: Ensure the QCEW loader has been run for the target year:

```bash
poetry run python -m babylon.data.qcew.loader --year 2022
```

### Missing H3 Mapping

If `hex_claims` is empty, the H3 bridge table may not be populated:

```bash
sqlite3 data/sqlite/marxist-data-3NF.sqlite \
  "SELECT COUNT(*) FROM bridge_county_h3 WHERE county_id IN (SELECT county_id FROM dim_county WHERE fips IN ('26163', '26125'))"
```

If count is 0, run the H3 loader:

```bash
poetry run python -m babylon.data.h3.loader
```

______________________________________________________________________

## Cross-Reference Index

This quickstart demonstrates usage patterns. For implementation details, see:

| Topic                      | Document                        | Section                          |
| -------------------------- | ------------------------------- | -------------------------------- |
| TerritoryState fields      | data-model.md                   | TerritoryState                   |
| SimulationSnapshot         | data-model.md                   | SimulationSnapshot               |
| SimulationState protocol   | contracts/simulation_state.py   | Full file                        |
| SimulationControl protocol | contracts/simulation_control.py | Full file                        |
| profit_rate formula        | research.md                     | Profit Rate Dynamics             |
| Hydration sequence         | plan.md                         | Hydration Flow                   |
| Per-tick update rule       | plan.md                         | Per-Tick Update Rule             |
| Implementation order       | plan.md                         | Implementation Sequence          |
| SQLite schema              | research.md                     | SQLite Reference Database Schema |
| MarxianHydrator reuse      | research.md                     | Economics Hydrator               |
