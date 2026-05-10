# Phase 1 Data Model: ADR Bundle 2

**Feature**: 059-adr-bundle-2-post-spec-057
**Date**: 2026-05-09
**Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

Bundle 2 introduces no new domain entities, no new database tables, no new
TOML or JSON schemas, and no new game-logic types. It is a structural refactor
that re-organises existing types into new module shapes and lifts a Protocol
into an ABC. This document records the new abstractions and the package
shapes that hold them.

## Section 1 — New abstractions

### 1.1 `SystemBase` (ABC)

**Module**: `src/babylon/engine/systems/base.py` (new)

**Purpose**: Lift the shared scaffolding that all 22 System implementations
duplicate (constructor, helper methods for graph read/write, event publish)
into a single ABC. Surface schema bugs at the read site instead of silently
substituting defaults.

**Shape**:
```python
class SystemBase(ABC):
    name: ClassVar[str]                                 # subclass MUST set
    def __init__(self, defines: GameDefines) -> None: ...
    @abstractmethod
    def step(self, graph: nx.DiGraph[str], services: ServiceContainer,
             context: TickContext | dict[str, Any]) -> None: ...

    # shared helpers
    def _read(self, graph, node_id, key, *, required: bool = False) -> Any: ...
    def _write(self, graph, node_id, key, value) -> None: ...
    def _publish(self, services, event: TickEvent) -> None: ...
```

**Invariants**:
- `_read(..., required=True)` raises `KeyError` with a diagnostic message
  naming both the attribute and the node when the key is absent.
- `_read(..., required=False)` returns `node.get(key)` (i.e., `None` for
  missing keys) — preserves current `data.get("X")` semantics for genuinely
  optional fields.
- `_write` mutates the graph node in place; idempotent for repeated writes
  with the same value.
- `_publish` delegates to `services.event_bus.publish(event)`; `event` MUST be
  a `TickEvent` variant (Pydantic discriminator validation enforces).

**Subclasses** (all 22; migrated by ADR-003 step 2 and step 3):

| Wave | Files |
|---|---|
| Wave 1 — pilot (5 small) | `metabolism.py`, `reserve_army.py`, `vitality.py`, `dispossession_events.py`, `contradiction_field.py` |
| Wave A | `ideology.py`, `solidarity.py`, `survival.py`, `contradiction.py`, `lifecycle.py`, `ooda.py`, `decomposition.py` |
| Wave B | `economic.py`, `struggle.py`, `territory.py`, `edge_transition.py`, `control_ratio.py`, `field_derivative.py`, `production.py` |
| Wave C | `community.py`, `event_template.py` |
| Out-of-tree | `economics/tick/system/__init__.py:TickDynamicsSystem` (Bundle-1 facade composing imperial_rent and other sub-systems) |

`engine/systems/protocol.py:System` is preserved as a `runtime_checkable
Protocol` (re-exported from `base.py` or kept in place). Tests and mocks
that previously satisfied the Protocol structurally continue to work.

### 1.2 `TickEvent` (discriminated union)

**Module**: `src/babylon/models/events/__init__.py` (new package; replaces
`models/events.py`)

**Purpose**: Replace the implicit `event_type`-string dispatch in
`deserialize_event` with a Pydantic 2 discriminated union, so the
typechecker enforces variant exhaustiveness in observers and the `from_graph`
roundtrip.

**Shape**:
```python
TickEvent = Annotated[
    Union[
        # 19 leaf variants — see research.md D2 for the full list
        ExtractionEvent, SubsidyEvent, CrisisEvent, SuperwageCrisisEvent,
        ClassDecompositionEvent, ControlRatioCrisisEvent, TerminalDecisionEvent,
        TransmissionEvent, MassAwakeningEvent,
        SparkEvent, UprisingEvent, SolidaritySpikeEvent,
        RuptureEvent,
        PhaseTransitionEvent, BifurcationTendencyEvent,
        EndgameEvent, AxiomViolationEvent, QcewCarryForwardEvent,
        PhiHourOutlierEvent,
    ],
    Field(discriminator="kind"),
]
```

Each leaf variant carries a unique `kind: Literal[...]` field. The 5
intermediate bases (`EconomicEvent`, `ConsciousnessEvent`, `StruggleEvent`,
`ContradictionEvent`, `TopologyEvent`) and the root `SimulationEvent` remain
as field-bearing Pydantic models but do **not** participate in the
discriminated union.

**Invariants**:
- Each leaf's `kind` literal is unique across all 19 variants (Pydantic
  validates at class-definition time).
- `WorldState.events: list[TickEvent]` validates discriminator dispatch on
  every assignment; passing a dict with a missing or unknown `kind` raises
  `ValidationError`.
- `TypeAdapter(TickEvent).validate_python(d)` round-trips: for any variant
  `v`, `TypeAdapter(TickEvent).validate_python(v.model_dump()) == v`.
- Serialization is symmetric: `TickEvent` variants survive `to_graph()` /
  `from_graph()` roundtrips with byte-identical outputs.

**Mapping from current to new** — current leaf class → new `kind` literal:

| Class | Proposed `kind` literal |
|---|---|
| `ExtractionEvent` | `"extraction"` |
| `SubsidyEvent` | `"subsidy"` |
| `CrisisEvent` | `"crisis"` |
| `SuperwageCrisisEvent` | `"superwage_crisis"` |
| `ClassDecompositionEvent` | `"class_decomposition"` |
| `ControlRatioCrisisEvent` | `"control_ratio_crisis"` |
| `TerminalDecisionEvent` | `"terminal_decision"` |
| `TransmissionEvent` | `"transmission"` |
| `MassAwakeningEvent` | `"mass_awakening"` |
| `SparkEvent` | `"spark"` |
| `UprisingEvent` | `"uprising"` |
| `SolidaritySpikeEvent` | `"solidarity_spike"` |
| `RuptureEvent` | `"rupture"` |
| `PhaseTransitionEvent` | `"phase_transition"` |
| `BifurcationTendencyEvent` | `"bifurcation_tendency"` |
| `EndgameEvent` | `"endgame"` |
| `AxiomViolationEvent` | `"axiom_violation"` |
| `QcewCarryForwardEvent` | `"qcew_carry_forward"` |
| `PhiHourOutlierEvent` | `"phi_hour_outlier"` |

These literal values are load-bearing for the discriminator and must remain
stable; they are written into persisted `events` lists and trace JSON files.

### 1.3 `Scenario` (ABC)

**Module**: `src/babylon/engine/scenarios/base.py` (new)

**Purpose**: Lift the implicit "scenario builder" contract that 6 free
functions duplicate (build territories, classes, relationships; assemble into
`(WorldState, SimulationConfig, GameDefines)`) into an ABC, with auto-registry
via `__init_subclass__`.

**Shape**:
```python
class Scenario(ABC):
    name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def build_territories(self) -> dict[str, Territory]: ...
    @abstractmethod
    def build_classes(self) -> dict[str, SocialClass]: ...
    @abstractmethod
    def build_relationships(self) -> dict[str, Relationship]: ...

    def build(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Default composition. Override only when a scenario needs custom assembly."""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        _SCENARIO_REGISTRY[cls.name] = cls
```

**Subclasses** (all 6; ported by ADR-006.1):

| Old free function | New `Scenario` subclass | Module |
|---|---|---|
| `create_two_node_scenario` | `TwoNodeScenario` | `engine/scenarios/two_node.py` |
| `create_high_tension_scenario` | `HighTensionScenario` | `engine/scenarios/high_tension.py` |
| `create_labor_aristocracy_scenario` | `LaborAristocracyScenario` | `engine/scenarios/labor_aristocracy.py` |
| `create_imperial_circuit_scenario` | `ImperialCircuitScenario` | `engine/scenarios/imperial_circuit.py` |
| `create_us_scenario` | `USScenario` | `engine/scenarios/us.py` |
| `create_wayne_county_scenario` | `WayneCountyScenario` | `engine/scenarios/wayne_county.py` |

**Backward compatibility shims** (kept in `engine/scenarios/__init__.py`):
```python
def create_two_node_scenario(*args, **kwargs):
    return TwoNodeScenario(*args, **kwargs).build()
# … same shape for the other 5
```

The 2 utilities (`apply_scenario`, `get_multiverse_scenarios`) and 5 private
helpers (`_classify_hex` etc.) are not migrated to `Scenario` — they belong
on the registry or remain module-private to `engine/scenarios/`.

**Invariants**:
- `_SCENARIO_REGISTRY` maps `cls.name` → `Scenario` subclass. Two subclasses
  with the same `name` raise `ValueError` at import time (deterministic
  detection of name collisions).
- Each subclass's `build()` returns a `(WorldState, SimulationConfig,
  GameDefines)` tuple identical to its pre-migration free-function counterpart
  — verified by SC-007's byte-equality check on `imperial_circuit` and the
  pre-flight check on the other 5.

## Section 2 — New package shapes

### 2.1 `persistence/postgres_runtime/` (replaces `postgres_runtime.py`)

```
src/babylon/persistence/postgres_runtime/
├── __init__.py              # PostgresRuntime facade (~150 LOC)
├── _pool.py                 # AsyncConnectionPool ownership + retry
├── tick_io.py               # PostgresTickIO — per-tick state read/write
├── archival_io.py           # PostgresArchivalIO — Parquet + R2 (Phase 8 stub preserved)
├── spatial_io.py            # PostgresSpatialIO — PostGIS hex queries
├── community_io.py          # PostgresCommunityIO — XGI hyperedge state
└── trace_io.py              # PostgresTraceIO — TraceCollector impl
```

**Facade** (`__init__.py`):
```python
class PostgresRuntime:
    """Facade composing focused IO classes.
    Satisfies RuntimePersistence + PostgresRuntimeExtensions Protocols."""
    def __init__(self, pool: AsyncConnectionPool):
        self._tick = PostgresTickIO(pool)
        self._archival = PostgresArchivalIO(pool)
        self._spatial = PostgresSpatialIO(pool)
        self._community = PostgresCommunityIO(pool)
        self._trace = PostgresTraceIO(pool)
    # ~15 thin pass-through methods covering the public Protocol surface
```

**Per-file LOC budget**: each ≤400 LOC; facade ≤200 LOC (FR-001 / SC-002).

**Public-import preservation**: `from babylon.persistence import
PostgresRuntime` continues to resolve to the facade class (FR-003).

**Protocol satisfaction**:
- `isinstance(PostgresRuntime(pool), RuntimePersistence) is True`
- `isinstance(PostgresRuntime(pool), PostgresRuntimeExtensions) is True`

`PgVectorStore` (already in its own file `pgvector_store.py`) is left in
place; optional move to `postgres_runtime/vector_io.py` is deferred to a
follow-up commit.

### 2.2 `engine/simulation/` (replaces `simulation.py`)

```
src/babylon/engine/simulation/
├── __init__.py              # Simulation facade (~150 LOC)
├── orchestrator.py          # SimulationOrchestrator — runs tick() pipeline
├── observer_dispatch.py     # ObserverDispatcher — fanout to SimulationObserver impls
├── lifecycle.py             # SimulationLifecycle — start/pause/stop/reset state
└── error_recovery.py        # SimulationRecovery — invariant rollback
```

**Facade** (`__init__.py`):
```python
class Simulation:
    """Facade. Public API stable for embedders (UI, web backend, tests)."""
    def __init__(self, ...):
        self._lifecycle = SimulationLifecycle(...)
        self._orchestrator = SimulationOrchestrator(...)
        self._observers = ObserverDispatcher(...)
        self._recovery = SimulationRecovery(...)
    # public methods: tick(), run_to_completion(), pause(), …
```

**Per-file LOC budget**: each ≤400 LOC; facade ≤200 LOC (FR-002 / SC-002).

**Public-import preservation**: `from babylon.engine import Simulation`
continues to resolve to the facade class (FR-003).

**Module-level state preservation**: `_session_action_history` and
`_session_trap_state` in `web/game/engine_bridge.py` are explicitly out of
scope (per Edge Cases bullet, spec.md:130) — Bundle 2 does not touch the web
layer.

### 2.3 `models/events/` (replaces `events.py`)

```
src/babylon/models/events/
├── __init__.py              # Re-exports TickEvent + every variant + intermediate bases
├── _base.py                 # SimulationEvent root + _EventBase common fields + TickEvent assembly
├── economic.py              # ExtractionEvent, SubsidyEvent, CrisisEvent, SuperwageCrisisEvent,
│                            #   ClassDecompositionEvent, ControlRatioCrisisEvent, TerminalDecisionEvent
│                            #   + EconomicEvent intermediate base
├── consciousness.py         # TransmissionEvent, MassAwakeningEvent + ConsciousnessEvent base
├── struggle.py              # SparkEvent, UprisingEvent, SolidaritySpikeEvent + StruggleEvent base
├── contradiction.py         # RuptureEvent + ContradictionEvent base
├── topology.py              # PhaseTransitionEvent, BifurcationTendencyEvent + TopologyEvent base
└── system.py                # EndgameEvent, AxiomViolationEvent, QcewCarryForwardEvent, PhiHourOutlierEvent
```

**Per-file LOC budget**: ≤300 LOC per sub-file (FR-007).

**Public-import preservation**: every existing
`from babylon.models.events import X` resolves unchanged (FR-007).

**Roundtrip invariant**: `TickEvent` variants survive `to_graph()` /
`from_graph()` byte-identically, with Pydantic dispatch via
`TypeAdapter(TickEvent)` replacing `deserialize_event`.

### 2.4 `economics/circulation/types/` (replaces `circulation/types.py`)

```
src/babylon/economics/circulation/types/
├── __init__.py              # Re-exports all 19 types + 4 enums
├── flow.py                  # CircuitState, TurnoverProfile, AnnualSurplusValue,
│                            #   ReproductionBalance, ReproductionAnalysis
├── fixed_capital.py         # FixedCapitalItem, DepreciationFundState,
│                            #   MoralDepreciation, InventoryState
├── crisis.py                # RealizationCrisis, DisproportionalityCrisis,
│                            #   CirculationCrisisAssessment, CirculationCrisisState
└── _enums.py                # CapitalForm, ReplacementCyclePosition,
                             #   InventoryDiagnosis, CrisisSeverity
```

**Per-file LOC budget**: each ≤400 LOC (FR-013 / SC-002).

**Public-import preservation**: every existing
`from babylon.economics.circulation.types import X` resolves unchanged.

### 2.5 `engine/systems/edge_transition/` (replaces `edge_transition.py`)

```
src/babylon/engine/systems/edge_transition/
├── __init__.py              # Re-exports EdgeTransitionSystem + predicates
├── predicates.py            # PredicateCondition, CompoundPredicate, EdgeModeTransition
└── system.py                # EdgeTransitionSystem(SystemBase) — System class only
```

**Hard ordering**: `system.py`'s `EdgeTransitionSystem` inherits from
`SystemBase`, so this package depends on ADR-003 having merged. See research.md
D5.

**Per-file LOC budget**: each ≤400 LOC (FR-014).

**Public-import preservation**: `from babylon.engine.systems.edge_transition
import EdgeTransitionSystem` resolves unchanged. Predicate models are
accessible via `engine.systems.edge_transition.predicates` (a new path; no
existing import paths are broken because predicates were previously
co-located with the System).

### 2.6 `engine/scenarios/` (replaces `scenarios.py` + `scenarios_wayne_county.py`)

```
src/babylon/engine/scenarios/
├── __init__.py              # _SCENARIO_REGISTRY + get_multiverse_scenarios + apply_scenario
│                            #   + 6 backward-compat shim functions
├── base.py                  # Scenario ABC + __init_subclass__ registry
├── two_node.py              # TwoNodeScenario(Scenario)
├── high_tension.py          # HighTensionScenario(Scenario)
├── labor_aristocracy.py     # LaborAristocracyScenario(Scenario)
├── imperial_circuit.py      # ImperialCircuitScenario(Scenario)
├── us.py                    # USScenario(Scenario)
└── wayne_county.py          # WayneCountyScenario(Scenario)
```

**Public-import preservation**: every existing free-function import
(`from babylon.engine.scenarios import create_imperial_circuit_scenario`)
resolves unchanged via shims (FR-012). Direct subclass imports
(`from babylon.engine.scenarios.imperial_circuit import ImperialCircuitScenario`)
become available as a parallel import path.

**Byte-equality** (SC-007): each ported scenario produces byte-identical
output to its pre-migration free function for a fixed-tick `sim:trace` run.
Verified pre-flight per quickstart.md.

## Section 3 — Untouched data shapes

To make the boundary explicit, Bundle 2 does NOT modify:

- `WorldState` other than narrowing `events: list[TickEvent]` (currently
  `list[Event]` or similar parent type).
- `Territory`, `SocialClass`, `Relationship`, or any other domain entity in
  `models/entities/`.
- The PostgreSQL schema (`postgres_schema.py`).
- Any TOML data file under `data/` or `babylon-data/`.
- Any JSON schema file other than the orphan-audit annotations (FR-015 may
  add a top-level `description` field per affected schema; see ADR-006.6
  acceptance bullet (c)).
- The 4 stubbed Phase 8 archival functions in
  `persistence/postgres_runtime/archival_io.py` — moved into the new package
  but not unstubbed (Out of Scope, spec.md:208).

## Section 4 — Acceptance traceability

| Spec FR / SC | Data-model entity / package | Verification |
|---|---|---|
| FR-001 / SC-002 / US1 | `persistence/postgres_runtime/` package | Per-file LOC + facade isinstance check |
| FR-002 / SC-002 / US1 | `engine/simulation/` package | Per-file LOC + facade public API |
| FR-003 | All 6 packages | `git grep` byte-equality of import paths before/after |
| FR-004 / SC-010 | `TickEvent` discriminated union | Pydantic class-def-time validation |
| FR-005 | `WorldState.events: list[TickEvent]` | `pytest tests/unit/models/test_events.py` |
| FR-006 / SC-003 | `deserialize_event` deletion | `git grep -n "def deserialize_event" src/` returns 0 |
| FR-007 | `models/events/` package | Per-file LOC ≤300 |
| FR-008 / SC-004 | observer migration (D7-scoped) | `mypy --strict` on observer files |
| FR-009 / SC-005 / US3 | `SystemBase` ABC | `issubclass(S, SystemBase)` for all 22 |
| FR-010 | `System` Protocol re-export | `isinstance(stub, System)` still True |
| FR-011 / SC-006 | `_read(required=True)` migrations | ≥5 conversions documented per US3 |
| FR-012 / SC-007 / US4 | `Scenario` ABC + 6 subclasses | Byte-identical `sim:trace` output |
| FR-013 | `economics/circulation/types/` | Per-file LOC ≤400 |
| FR-014 | `engine/systems/edge_transition/` | Per-file LOC; SystemBase inheritance |
| FR-015 / SC-008 | Orphan schema audit | Disposition entry per schema in `ai-docs/decisions.yaml` |
| FR-016 / SC-001 | Test tally preservation | `mise run test:unit` + `mise run test:int` deltas |
| FR-017 | Commit sequencing | Reviewable commit boundaries in tasks.md |
| SC-009 | Lint/type cleanliness | `mise run check` passes with no new findings |
