# Research: MVP Simulation Engine

**Feature**: 001-mvp-sim-engine **Date**: 2026-01-30

## Research Questions

### 1. Existing Simulation Infrastructure

**Question**: What does the existing `Simulation` class provide that we can reuse?

**Findings**:

- `src/babylon/engine/simulation.py` provides a `Simulation` class
- Already manages: `WorldState`, `SimulationConfig`, `ServiceContainer`, Observer pattern
- Methods: `run(ticks)`, `step()` (via `run(1)`), `current_state`, `history`
- WorldState has: `tick`, `entities`, `territories`, `relationships`, `events`
- Territory model exists at `src/babylon/models/entities/territory.py`

**Decision**: Modify the existing `Simulation` class directly to implement the new protocols. No wrapper or adapter
class.

**Rationale**: Wrappers create technical debt—indirection tax, dual maintenance burden, eventual consolidation anyway.
The existing class already has most of what we need (`step()`, `current_state`). Adding protocol methods directly is
cleaner and pays off long-term.

______________________________________________________________________

### 2. Territory Model H3 Support

**Question**: Does the Territory model already support H3 indices?

**Findings**:

- Territory has `h3_index: str | None` field (15-char hex pattern)
- Territory `id` can be either T[0-9]{3} format or 15-char H3 index
- H3 resolution 5 is used in `bridge_county_h3` table (~252 km² hexagons)
- No `hex_claims` set exists—a territory maps to a single H3 index

**Decision**: For MVP, treat county FIPS code as territory_id and aggregate all H3 cells from `bridge_county_h3` into a
`hex_claims` set on the snapshot. The underlying Territory model stores individual hex cells.

**Rationale**: Follows the GUI guiding star document which specifies `territory.hex_claims` as a set of H3 strings.

______________________________________________________________________

### 3. SQLite Reference Database Schema

**Question**: What tables and columns are available for hydration?

**Findings**:

- Database: `data/sqlite/marxist-data-3NF.sqlite`
- `dim_county`: county_id (PK), fips (5-char unique), state_id (FK), county_name
- `fact_qcew`: county_id (FK), year, naics_code, wages, employment
- `bridge_county_h3`: h3_index (PK, 15-char), county_id (FK), resolution (default 5), coverage_pct
- Access pattern: `get_reference_session()` context manager from `data/reference/database.py`

**Decision**: Query all three tables during initialization to build territory state.

**Rationale**: These tables provide the complete data needed: county identity, wage data, and spatial mapping.

______________________________________________________________________

### 4. Economics Hydrator

**Question**: Can we reuse the existing MarxianHydrator for c/v/s computation?

**Findings**:

- `src/babylon/economics/hydrator.py` has `MarxianHydrator` class
- `hydrate(fips_code, year)` → `ValueTensor4x3` with c, v, s per department
- Already handles Wayne (26163) and Oakland (26125) in tests
- Requires `QCEWDataSource`, `BEADataSource`, `DepartmentMapper` dependencies

**Decision**: Use MarxianHydrator for initial profit_rate calculation: `r = total_s / (total_c + total_v)`.

**Rationale**: Existing code already computes c/v/s from federal data sources per constitution III.4.

______________________________________________________________________

### 5. Profit Rate Dynamics

**Question**: How should profit_rate change each tick for GUI visualization?

**Findings**:

- Constitution requires TRPF with counter-tendencies (I.3)
- Full TRPF is out of scope for MVP (explicitly deferred in spec)
- GUI needs profit_rate to change each tick to demonstrate state mutation
- Placeholder must be deterministic for reproducibility

**Decision**: Use exponential smoothing toward territory-specific equilibrium:

```text
r_new = r_old * (1 - decay_rate) + equilibrium_r * decay_rate
```

Where decay_rate = 0.05, equilibrium_r = initial_r (set at hydration per territory).

**Rationale**:

- Deterministic (same input → same output)
- Visible change each tick
- Territories maintain differentiation (Wayne ≠ Oakland throughout simulation)
- A universal base_rate would cause convergence, making GUI visualization meaningless
- Explicitly flagged as STUB per constitution III.1

______________________________________________________________________

## Summary Table

| Question | Decision | Confidence | | ------------------------- | ------------------------------------------- |
------------- | | Simulation infrastructure | Modify existing `Simulation` class directly | High | | Territory H3
support | Aggregate H3 cells into `hex_claims` set | High | | SQLite schema | Use dim_county, fact_qcew,
bridge_county_h3 | High | | Economics hydrator | Reuse `MarxianHydrator` for c/v/s | High | | Profit rate dynamics |
Exponential smoothing placeholder | Medium (stub) |

______________________________________________________________________

## Implementation References

This section maps research findings to implementation artifacts.

### Finding → Implementation Mapping

| Finding | Informs | Implementation Location | | -------------------------------------- |
--------------------------------------- | ------------------------------------------------------------ | | #1. Existing
Simulation Infrastructure | `Simulation.from_sqlite()` class method | `src/babylon/engine/simulation.py` | | #1.
Existing Simulation Infrastructure | Protocol method additions | `src/babylon/engine/simulation.py` | | #2. Territory H3
Support | `TerritoryState.hex_claims` | [data-model.md#TerritoryState](data-model.md#territorystate) | | #2. Territory
H3 Support | Hydration query | `src/babylon/data/reference/hydrator.py` | | #3. SQLite Schema | `from_sqlite()` queries
| `src/babylon/data/reference/hydrator.py` | | #3. SQLite Schema | Database access pattern | `get_reference_session()`
from `data/reference/database.py` | | #4. Economics Hydrator | Initial profit_rate | `MarxianHydrator.hydrate()` call in
`from_sqlite()` | | #5. Profit Rate Dynamics | `step()` update logic |
[plan.md#Per-Tick Update Rule](plan.md#per-tick-update-rule) |

### Cross-Reference Index

| Topic | See Also | | ------------------------------------ |
-------------------------------------------------------------------- | | TerritoryState entity definition |
[data-model.md#TerritoryState](data-model.md#territorystate) | | SimulationSnapshot entity definition |
[data-model.md#SimulationSnapshot](data-model.md#simulationsnapshot) | | SimulationState protocol |
[contracts/simulation_state.py](contracts/simulation_state.py) | | SimulationControl protocol |
[contracts/simulation_control.py](contracts/simulation_control.py) | | Per-tick update formula |
[plan.md#Per-Tick Update Rule](plan.md#per-tick-update-rule) | | Hydration sequence |
[plan.md#Hydration Flow](plan.md#hydration-flow) | | Usage examples | [quickstart.md](quickstart.md) |
