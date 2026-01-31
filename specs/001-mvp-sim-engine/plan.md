# Implementation Plan: MVP Simulation Engine

**Branch**: `001-mvp-sim-engine` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md) **Input**: Feature
specification from `/specs/001-mvp-sim-engine/spec.md`

## Summary

Build a minimal viable simulation engine that enables GUI development by providing:

1. Two protocol definitions (`SimulationState`, `SimulationControl`) as stable interfaces
1. Direct modification of the existing `Simulation` class to implement both protocols
1. SQLite hydration from reference database (dim_county, fact_qcew, bridge_county_h3)
1. Deterministic profit_rate computation and per-tick updates for Wayne/Oakland counties

**Technical Approach**: Modify the existing `Simulation` class directly to implement the new protocols. No wrapper or
adapter—the class already has `step()`, `current_state`, and observer support. Adding protocol methods directly avoids
technical debt from wrappers.

## Technical Context

**Language/Version**: Python 3.12+ **Primary Dependencies**: NetworkX 3.x, Pydantic 2.x, SQLAlchemy 2.x **Storage**:
SQLite (data/sqlite/marxist-data-3NF.sqlite for reference; in-memory for simulation state) **Testing**: pytest with
markers: `@pytest.mark.unit`, `@pytest.mark.integration` **Target Platform**: Linux/macOS local development **Project
Type**: Single project (existing `src/babylon/` structure) **Performance Goals**: \<2s initialization for Detroit test
case (2 counties) **Constraints**: Deterministic (same seed → same output); no DuckDB for simulation **Scale/Scope**: 2
counties (Wayne 26163, Oakland 26125), ~100-500 H3 cells at res5

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes | | ---------------------------------- | ---------- |
\-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
| | **II.2 Primitives vs Derived** | ✅ PASS | profit_rate is computed from c, v, s (derived from QCEW v and BEA ratios),
never stored directly | | **II.3 NetworkX as Manifold** | ✅ PASS | Uses existing NetworkX graph infrastructure in
WorldState | | **III.1 No Magic Constants** | ⚠️ PARTIAL | Placeholder decay_rate (0.05) and base_rate (0.04) need
grounding. **Justified**: Spec explicitly states this is a stub to be replaced by TRPF mechanics. Flag in code as
`# STUB: Replace with TRPF` | | **III.4 Data Source Traceability** | ✅ PASS | profit_rate derives from QCEW wages (v)
and BEA c/v ratios | | **IV. Detroit Test Case** | ✅ PASS | Wayne (26163) and Oakland (26125) are explicit test
geography | | **V.1 Material Base First** | ✅ PASS | No superstructure mechanics—just profit_rate computation | | **V.3
Flag Scope Creep** | ✅ PASS | Deferred Items list in spec prevents scope expansion | | **VI.1 Solidarity as Scalar** | ✅
N/A | No solidarity mechanics in MVP | | **VI.6 Constants Without Data** | ⚠️ PARTIAL | See III.1 above—decay constants
flagged |

**Gate Status**: PASS with documented justification for placeholder constants.

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-sim-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Python protocols, not REST)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/
├── protocols/                      # NEW: Protocol definitions
│   ├── __init__.py
│   ├── simulation_state.py         # SimulationState protocol
│   └── simulation_control.py       # SimulationControl protocol
├── engine/
│   └── simulation.py               # MODIFIED: Add protocol methods directly
├── data/
│   └── reference/
│       └── hydrator.py             # NEW: SQLite → Territory hydration
└── models/
    └── snapshots.py                # NEW: TerritoryState, HexState, SimulationSnapshot

tests/
├── unit/
│   └── protocols/                  # NEW: Protocol compliance tests
│       ├── test_simulation_state.py
│       └── test_simulation_control.py
└── integration/
    └── mvp/                        # NEW: End-to-end MVP tests
        ├── test_hydration.py       # SQLite → Territory
        ├── test_determinism.py     # Reproducibility
        └── test_gui_readiness.py   # SC-001 acceptance test
```

**Structure Decision**: Extend existing `src/babylon/` structure with new `protocols/` package. The existing
`Simulation` class in `engine/simulation.py` is modified directly to implement both protocols—no wrapper class.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because | | ----------------------------------- |
\--------------------------------------------------- | --------------------------------------------------------- | |
Placeholder decay constants | GUI development requires state change per tick | Waiting for full TRPF would block GUI
work | | New `protocols/` package | Clean protocol/implementation separation | Embedding protocols in `engine/` mixes
concerns | | Modifying existing Simulation class | Direct implementation avoids wrapper technical debt | Wrapper
rejected—creates indirection and dual maintenance |

______________________________________________________________________

## Phase 0: Research

### Research Tasks

1. **Existing Simulation class API surface** — Understand what's already implemented
1. **Territory model H3 support** — Verify H3 field exists, understand usage
1. **SQLite schema for QCEW/BEA** — Confirm fact_qcew, dim_county, bridge_county_h3 structure
1. **Existing economics hydrator** — Check MarxianHydrator for c/v/s computation reuse

### Findings

**1. Existing Simulation Class**

- Location: `src/babylon/engine/simulation.py`
- Already implements: `run(ticks)`, `current_state`, `config`, Observer pattern
- WorldState has: `tick`, `entities`, `territories`, `relationships`
- Missing: Protocol-based interface, territory-centric query methods

**2. Territory Model**

- Location: `src/babylon/models/entities/territory.py`
- Has `h3_index` field (pattern: 15-char hex string)
- Has `id` field (pattern: T[0-9]{3} or 15-char H3)
- Missing: `profit_rate` field, `hex_claims` set

**3. SQLite Schema**

- Reference DB: `data/sqlite/marxist-data-3NF.sqlite`
- `dim_county`: county_id, fips (5-char), state_id, county_name
- `fact_qcew`: county_id, year, naics_code, wages, employment
- `bridge_county_h3`: h3_index (PK), county_id (FK), resolution, coverage_pct
- Access: `get_reference_session()` context manager

**4. Economics Hydrator**

- Location: `src/babylon/economics/hydrator.py`
- `MarxianHydrator.hydrate(fips_code, year)` → `ValueTensor4x3`
- Computes c, v, s from QCEW wages + BEA ratios
- Already handles Wayne (26163) and Oakland (26125)

### Decision Summary

| Decision | Rationale | Alternatives Rejected | | -------------------------------------------------- |
\---------------------------------------------------------------------- |
----------------------------------------------------------- | | Modify existing Simulation directly | Avoids wrapper
technical debt; class already has step(), current_state | Wrapper creates indirection tax and dual maintenance burden |
| Add `profit_rate` as computed property on snapshot | Follows II.2 (primitives vs derived) | Storing profit_rate
violates constitution | | Use MarxianHydrator for initial c/v/s | Already computes from QCEW/BEA | Re-implementing would
duplicate code | | New `protocols/` package | Clean separation for GUI dependency | Embedding in engine/ mixes concerns
|

______________________________________________________________________

## Phase 1: Design

### Data Model

See `data-model.md` for full entity definitions.

**Key Entities**:

- `TerritoryState`: Snapshot of territory at tick (territory_id, profit_rate, hex_claims, tick)
- `HexState`: Immutable geographic cell (h3_index only for MVP)
- `EdgeState`: Relationship snapshot (source, target, type, weight)
- `SimulationSnapshot`: Complete state (tick, territories dict, hexes dict, edges list)

**Relationships**:

- Territory 1:N HexState (via hex_claims set)
- SimulationSnapshot contains TerritoryState, HexState, EdgeState

### Protocol Contracts

See `contracts/` for full protocol definitions.

**SimulationState Protocol**:

```python
class SimulationState(Protocol):
    def get_current_tick(self) -> int: ...
    def get_snapshot(self) -> SimulationSnapshot: ...
    def get_territory_state(self, territory_id: str) -> TerritoryState | None: ...
    def get_hexes_for_territory(self, territory_id: str) -> set[str]: ...
```

**SimulationControl Protocol**:

```python
class SimulationControl(Protocol):
    def step(self, n: int = 1) -> None: ...
    def reset(self) -> None: ...
```

### Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                         GUI Layer                            │
│  (imports only protocols/ and models/snapshots.py)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ depends on
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     protocols/                               │
│  SimulationState, SimulationControl (Protocol definitions)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ implements
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 engine/simulation.py                         │
│  Simulation(SimulationState, SimulationControl)             │
│  - MODIFIED: Implements both protocols directly             │
│  - NEW: Hydrates from SQLite on init                        │
│  - NEW: get_snapshot(), get_territory_state(), reset()      │
│  - EXISTING: step(), run(), current_state, observers        │
└──────────────────────────────┬──────────────────────────────┘
                               │ uses
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Supporting Infrastructure                       │
│  - models/world_state.py (WorldState)                       │
│  - models/snapshots.py (TerritoryState, SimulationSnapshot) │
│  - economics/hydrator.py (MarxianHydrator)                  │
│  - data/reference/ (SQLite access)                          │
└─────────────────────────────────────────────────────────────┘
```

### Hydration Flow

```text
1. Simulation.from_sqlite(fips_codes=["26163", "26125"], year=2022)
   │
   ├─► Query dim_county for county metadata
   │
   ├─► Query bridge_county_h3 for H3 cells per county
   │
   ├─► MarxianHydrator.hydrate(fips) for each county
   │   └─► Returns ValueTensor4x3 with c, v, s
   │
   ├─► Create Territory for each county
   │   └─► Attach initial c, v, s from tensor
   │
   ├─► Create WorldState with territories
   │
   └─► Return initialized Simulation instance
```

**Note**: `from_sqlite()` is a new class method on `Simulation` that handles hydration. The existing `__init__`
signature remains unchanged for backward compatibility.

### Per-Tick Update Rule

**Placeholder formula** (to be replaced by TRPF):

```text
r_new = r_old * (1 - decay_rate) + equilibrium_r * decay_rate

Where:
  decay_rate = 0.05           # STUB: Calibrate from Piketty/WID
  equilibrium_r = initial_r   # Territory-specific, set at hydration

Each territory maintains its OWN equilibrium_r derived from its initial
QCEW/BEA-computed profit rate. This prevents convergence to a universal
constant while still providing per-tick change for GUI visualization.
```

**Why territory-specific equilibrium**: A universal base_rate (e.g., 0.04) causes all territories to converge after ~100
ticks, making GUI visualization meaningless. By anchoring each territory to its own initial_r, we preserve the
differentiation that makes Wayne ≠ Oakland visually distinguishable throughout the simulation.

**Determinism preserved**: `equilibrium_r` is set once at hydration from the same QCEW/BEA data, so identical
initialization produces identical trajectories.

### Constitution Re-Check (Post-Design)

| Principle | Status | Notes | | ------------------------------ | ---------- | -----------------------------------------
| | II.2 Primitives vs Derived | ✅ PASS | profit_rate computed on-demand from c/v/s | | II.3 NetworkX as Manifold | ✅
PASS | WorldState.to_graph() unchanged | | III.1 No Magic Constants | ⚠️ FLAGGED | decay_rate/base_rate documented as
STUB | | III.4 Data Source Traceability | ✅ PASS | c/v/s from QCEW/BEA via MarxianHydrator | | IV. Detroit Test Case | ✅
PASS | Wayne/Oakland explicit in hydration | | V.1 Material Base First | ✅ PASS | Only economic quantity (profit_rate) |

______________________________________________________________________

## Implementation Sequence

This section defines the **dependency order** for implementation. Items must be completed in sequence—later items depend
on earlier items.

### Dependency Graph

```text
                    ┌─────────────────────┐
                    │ 1. Snapshot Models  │
                    │    (snapshots.py)   │
                    └──────────┬──────────┘
                               │ depends on
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ 2. SimulationState  │ │ 3. SimulationControl│ │ 4. Reference        │
│    Protocol         │ │    Protocol         │ │    Hydrator         │
└──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ 5. Simulation Class Mods    │
                    │    (from_sqlite, protocols) │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ 6. Unit Tests       │ │ 7. Integration Tests│ │ 8. Determinism Tests│
│    (protocols)      │ │    (hydration)      │ │    (reproducibility)│
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

### Implementation Order with References

| Order | Component | Output File | References | | ----- | ------------------------------ |
\--------------------------------------------- |
\-----------------------------------------------------------------------------------------------------------------------------------------------------
| | **1** | Snapshot Models | `src/babylon/models/snapshots.py` |
[data-model.md#TerritoryState](data-model.md#territorystate),
[data-model.md#SimulationSnapshot](data-model.md#simulationsnapshot) | | **2** | SimulationState Protocol |
`src/babylon/protocols/simulation_state.py` | [contracts/simulation_state.py](contracts/simulation_state.py) | | **3** |
SimulationControl Protocol | `src/babylon/protocols/simulation_control.py` |
[contracts/simulation_control.py](contracts/simulation_control.py) | | **4** | Reference Hydrator |
`src/babylon/data/reference/hydrator.py` |
[research.md#3. SQLite Schema](research.md#3-sqlite-reference-database-schema),
[research.md#4. Economics Hydrator](research.md#4-economics-hydrator) | | **5** | Simulation Class Mods |
`src/babylon/engine/simulation.py` | [#Hydration Flow](#hydration-flow), [#Per-Tick Update Rule](#per-tick-update-rule)
| | **6** | Unit Tests: Protocols | `tests/unit/protocols/` |
[quickstart.md#Using Protocols](quickstart.md#using-protocols-for-type-safety) | | **7** | Integration Tests: Hydration
| `tests/integration/mvp/` | [quickstart.md#GUI Readiness Test](quickstart.md#gui-readiness-test) | | **8** |
Integration Tests: Determinism | `tests/integration/mvp/` |
[quickstart.md#Determinism Verification](quickstart.md#determinism-verification) |

### Why This Order?

1. **Snapshot models first**: Protocols reference `TerritoryState`, `SimulationSnapshot` as return types. These types
   must exist before protocols can be defined without forward references.

1. **Protocols before Simulation mods**: The `Simulation` class will implement these protocols. Having the protocols
   defined first ensures the interface contract is clear before implementation begins.

1. **Hydrator parallel to protocols**: The hydrator is independent of protocols—it queries SQLite and returns domain
   objects. Can be developed in parallel with protocols (items 2-4 are parallelizable).

1. **Simulation mods last**: This is the integration point where protocols meet hydration. Must wait for all
   dependencies.

1. **Tests follow implementation**: Each test layer validates its corresponding implementation layer.

______________________________________________________________________

## Generated Artifacts

- `specs/001-mvp-sim-engine/research.md` — Research findings (this section)
- `specs/001-mvp-sim-engine/data-model.md` — Entity definitions
- `specs/001-mvp-sim-engine/contracts/simulation_state.py` — Protocol definition
- `specs/001-mvp-sim-engine/contracts/simulation_control.py` — Protocol definition
- `specs/001-mvp-sim-engine/quickstart.md` — Usage examples

______________________________________________________________________

## Next Steps

Run `/speckit.tasks` to generate task breakdown for implementation.
