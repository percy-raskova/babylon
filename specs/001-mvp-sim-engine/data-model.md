# Data Model: MVP Simulation Engine

**Feature**: 001-mvp-sim-engine **Date**: 2026-01-30

## Overview

This document defines the data entities for the MVP simulation engine. These are **snapshot** types—immutable
representations of state at a point in time. They differ from the internal simulation entities which may be mutable.

## Entities

### TerritoryState

A snapshot of a territory's state at a specific tick. This is the GUI-facing representation.

| Field | Type | Required | Description | | ------------------ | -------- | -------- |
--------------------------------------------------------- | | territory_id | str | Yes | Unique identifier (FIPS code
for counties) | | controlling_polity | str | Yes | Current controller (equals territory_id for MVP) | | hex_claims |
set[str] | Yes | Set of H3 indices this territory claims | | tick | int | Yes | Tick number when this snapshot was taken
| | profit_rate | float | Yes | Current profit rate, range [0.0, 1.0] | | equilibrium_r | float | Yes |
Territory-specific equilibrium (= initial_r at hydration) |

**Validation Rules**:

- `territory_id` must be a 5-digit FIPS code (for county territories)
- `profit_rate` must be in range [0.0, 1.0], clamped if computed value is out of range
- `equilibrium_r` must be in range [0.0, 1.0], set once at hydration
- `hex_claims` may be empty if H3 mapping is incomplete (warning logged)
- `tick` must be non-negative

**Computed Properties**:

- Initial `profit_rate` is derived from c, v, s at tick 0
- Subsequent `profit_rate` values evolve via placeholder formula (see plan.md#Per-Tick Update Rule)
- `equilibrium_r` prevents convergence to universal constant—each territory maintains differentiation

______________________________________________________________________

### HexState

An immutable geographic cell. Hexes are the invariant substrate—they don't change during simulation.

| Field | Type | Required | Description | | -------- | ---- | -------- |
------------------------------------------------ | | h3_index | str | Yes | H3 cell index (15-char hex string,
resolution 5) |

**Validation Rules**:

- `h3_index` must match pattern `^[0-9a-f]{15}$`
- HexState is immutable—create new instances, never mutate

**Notes**:

- For MVP, HexState contains only the index. Future versions may add physical properties (terrain, resources).
- Hexes exist independently of territories—a hex can be claimed by different territories over time.

______________________________________________________________________

### EdgeState

A snapshot of a relationship (edge) between entities at a specific tick.

| Field | Type | Required | Description | | --------- | ----- | -------- |
------------------------------------------------------------------- | | source_id | str | Yes | ID of the source entity
| | target_id | str | Yes | ID of the target entity | | edge_type | str | Yes | Relationship type (ADJACENCY,
EXTRACTION, SOLIDARITY, ANTAGONISTIC) | | weight | float | No | Edge weight (default 1.0) |

**Validation Rules**:

- `edge_type` must be one of: ADJACENCY, EXTRACTION, SOLIDARITY, ANTAGONISTIC
- `source_id` and `target_id` must be valid entity IDs
- `weight` must be non-negative

**Notes**:

- For MVP, edges are empty (no inter-territory relationships yet).
- The edge_type values map to the constitution's four edge modes (I.6).

______________________________________________________________________

### SimulationSnapshot

Complete state of the simulation at a specific tick. This is the top-level container returned by `get_snapshot()`.

| Field | Type | Required | Description | | ----------- | ------------------------- | -------- |
------------------------------------ | | tick | int | Yes | Current tick number | | territories | dict\[str,
TerritoryState\] | Yes | Map of territory_id → TerritoryState | | hexes | dict[str, HexState] | Yes | Map of h3_index →
HexState | | edges | list[EdgeState] | Yes | List of relationship edges |

**Validation Rules**:

- `tick` must be non-negative
- All hex indices in territory `hex_claims` must exist in `hexes` dict
- `edges` may be empty

**Invariants**:

- Hexes are the invariant substrate—`hexes` dict should be identical across all ticks
- Territory hex_claims may change as territorial control shifts (not in MVP)

______________________________________________________________________

## Relationships

```text
SimulationSnapshot
├── territories: dict[str, TerritoryState]
│   └── TerritoryState
│       └── hex_claims: set[str] ──► references HexState.h3_index
├── hexes: dict[str, HexState]
│   └── HexState (immutable substrate)
└── edges: list[EdgeState]
    └── EdgeState
        ├── source_id ──► references entity ID
        └── target_id ──► references entity ID
```

## State Transitions

### Initialization (tick 0)

1. Query `dim_county` for county metadata (name, FIPS)
1. Query `bridge_county_h3` for H3 cells per county
1. Query `fact_qcew` via MarxianHydrator for c, v, s
1. Create HexState for each H3 cell (immutable, never changes)
1. Create TerritoryState for each county with:
   - `territory_id` = FIPS code
   - `controlling_polity` = FIPS code (same for MVP)
   - `hex_claims` = set of H3 indices from bridge table
   - `tick` = 0
   - `profit_rate` = computed from c, v, s
1. Create SimulationSnapshot containing all territories, hexes, and empty edges

### Per-Tick Update (tick N → N+1)

1. For each territory:
   - Compute new profit_rate using placeholder formula
   - Create new TerritoryState with updated values and tick = N+1
1. Create new SimulationSnapshot with:
   - `tick` = N+1
   - Updated territories dict
   - Same hexes dict (immutable)
   - Same edges list (empty for MVP)

## Mapping to Existing Models

| Snapshot Type | Internal Model | Location | | ------------------ | -------------- |
--------------------------------------------- | | TerritoryState | Territory |
`src/babylon/models/entities/territory.py` | | HexState | (new) | `src/babylon/models/snapshots.py` | | EdgeState |
Relationship | `src/babylon/models/entities/relationship.py` | | SimulationSnapshot | WorldState |
`src/babylon/models/world_state.py` |

The snapshot types are **projections** of the internal models, designed for the GUI interface. They may omit
internal-only fields and add computed properties.

______________________________________________________________________

## Implementation References

This section maps entities to where they are used in implementation.

### TerritoryState

| Used By | Method/Context | Notes | | --------------------------------------- | --------------------- |
-------------------------------------------------------------------------- | | `SimulationState.get_snapshot()` | Return
type component | See [contracts/simulation_state.py](contracts/simulation_state.py) | |
`SimulationState.get_territory_state()` | Return type | Convenience accessor | | `Simulation.step()` | Created each tick
| See [plan.md#Per-Tick Update Rule](plan.md#per-tick-update-rule) | | `profit_rate` computation | Derived field | See
[research.md#Profit Rate Dynamics](research.md#5-profit-rate-dynamics) |

### HexState

| Used By | Method/Context | Notes | | ------------------------------------------- | --------------------- |
\-------------------------------------------------------------------------------------------------- | |
`SimulationState.get_hexes_for_territory()` | Return type component | Set of H3 index strings | | Hydration from SQLite
| Initialization | See [research.md#SQLite Reference Database Schema](research.md#3-sqlite-reference-database-schema) |

### SimulationSnapshot

| Used By | Method/Context | Notes | | -------------------------------- | ----------------- |
------------------------------ | | `SimulationState.get_snapshot()` | Return type | Top-level container | | GUI
rendering | External consumer | Protocol boundary for GUI code |

### EdgeState

| Used By | Method/Context | Notes | | ------------------------------- | -------------- |
------------------------------------- | | `SimulationSnapshot.edges` | List member | Empty for MVP | | Future:
Solidarity/Exploitation | Deferred | See [spec.md#Deferred Items](spec.md) |

______________________________________________________________________

## Cross-Reference Index

| Topic | Document | Section | | -------------------- |
------------------------------------------------------------------ | ------------------------------------ | | Protocol
definitions | [contracts/simulation_state.py](contracts/simulation_state.py) | Full file | | Protocol definitions |
[contracts/simulation_control.py](contracts/simulation_control.py) | Full file | | profit_rate formula |
[research.md](research.md) | #5. Profit Rate Dynamics | | c/v/s computation | [research.md](research.md) | #4. Economics
Hydrator | | SQLite tables | [research.md](research.md) | #3. SQLite Reference Database Schema | | Hydration flow |
[plan.md](plan.md) | #Hydration Flow | | Update rule | [plan.md](plan.md) | #Per-Tick Update Rule | | Usage examples |
[quickstart.md](quickstart.md) | All sections |
