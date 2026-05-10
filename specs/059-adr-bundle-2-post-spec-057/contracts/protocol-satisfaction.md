# Contract: Protocol & ABC Satisfaction

**Bundle**: 059-adr-bundle-2-post-spec-057 · **Phase**: 1
**Reference**: spec.md FR-009, FR-010, US1 acceptance scenario 1, US3
acceptance scenario 1; data-model.md §1

The decomposition (ADR-005) and ABC migration (ADR-003) preserve every
runtime-checkable Protocol that the public API satisfies today. This
contract enumerates the `isinstance` / `issubclass` checks that MUST pass
post-Bundle-2.

## P1 — `PostgresRuntime` satisfies `RuntimePersistence` AND `PostgresRuntimeExtensions`

```python
from babylon.persistence import PostgresRuntime
from babylon.persistence.protocols import RuntimePersistence, PostgresRuntimeExtensions
from psycopg_pool import AsyncConnectionPool

pool = AsyncConnectionPool(...)
runtime = PostgresRuntime(pool)

assert isinstance(runtime, RuntimePersistence), \
    "PostgresRuntime facade must satisfy RuntimePersistence (FR-001)"
assert isinstance(runtime, PostgresRuntimeExtensions), \
    "PostgresRuntime facade must satisfy PostgresRuntimeExtensions (FR-001)"
```

Both Protocols are defined in `src/babylon/persistence/protocols.py`. The
facade implements them by composing focused IO sub-classes; each pass-through
method MUST preserve the Protocol's signature.

**Test location**: `tests/contract/persistence/test_postgres_runtime_protocol.py`
(existing; should pass unchanged after decomposition).

## P2 — `Simulation` satisfies its public API contract

```python
from babylon.engine import Simulation
import inspect

# Captured from pre-bundle-2-baseline:
EXPECTED_PUBLIC_METHODS = {
    "tick", "run_to_completion", "pause", "resume", "stop", "reset",
    "current_state", "history", "register_observer", "deregister_observer",
    # … full list captured at task time
}

actual = {n for n, _ in inspect.getmembers(Simulation, predicate=inspect.isfunction)
          if not n.startswith("_")}
missing = EXPECTED_PUBLIC_METHODS - actual
assert not missing, f"Simulation facade is missing methods: {missing}"
```

**Test location**: `tests/contract/engine/test_simulation_facade_surface.py`
(new; introduced by ADR-005 step 5 to lock the surface before decomposition).

## P3 — All 22 Systems satisfy `SystemBase` AND `System` Protocol

```python
from babylon.engine.systems.base import SystemBase
from babylon.engine.systems.protocol import System

ALL_SYSTEMS = [
    # 21 in engine/systems/
    "babylon.engine.systems.survival.SurvivalSystem",
    "babylon.engine.systems.territory.TerritorySystem",
    "babylon.engine.systems.vitality.VitalitySystem",
    "babylon.engine.systems.dispossession_events.DispossessionEventSystem",
    "babylon.engine.systems.ooda.OODASystem",
    "babylon.engine.systems.production.ProductionSystem",
    "babylon.engine.systems.decomposition.DecompositionSystem",
    "babylon.engine.systems.event_template.EventTemplateSystem",
    "babylon.engine.systems.reserve_army.ReserveArmySystem",
    "babylon.engine.systems.community.CommunitySystem",
    "babylon.engine.systems.lifecycle.LifecycleSystem",
    "babylon.engine.systems.control_ratio.ControlRatioSystem",
    "babylon.engine.systems.contradiction_field.ContradictionFieldSystem",
    "babylon.engine.systems.metabolism.MetabolismSystem",
    "babylon.engine.systems.economic.ImperialRentSystem",
    "babylon.engine.systems.solidarity.SolidaritySystem",
    "babylon.engine.systems.struggle.StruggleSystem",
    "babylon.engine.systems.edge_transition.EdgeTransitionSystem",  # uses ADR-006.4 split
    "babylon.engine.systems.contradiction.ContradictionSystem",
    "babylon.engine.systems.ideology.ConsciousnessSystem",
    "babylon.engine.systems.field_derivative.FieldDerivativeSystem",
    # 1 in economics/tick/system/
    "babylon.economics.tick.system.TickDynamicsSystem",
]

for fqn in ALL_SYSTEMS:
    mod_path, cls_name = fqn.rsplit(".", 1)
    mod = __import__(mod_path, fromlist=[cls_name])
    cls = getattr(mod, cls_name)
    assert issubclass(cls, SystemBase), \
        f"{fqn} must inherit from SystemBase (FR-009)"
```

**Test location**: `tests/contract/engine/test_systembase_inheritance.py`
(new; introduced by ADR-003 step 4 as the green-phase regression).

## P4 — `System` Protocol structural typing preserved (FR-010)

```python
from babylon.engine.systems.protocol import System

class StubSystem:
    """Test mock — does NOT inherit from SystemBase."""
    name = "stub"
    def step(self, graph, services, context) -> None:
        pass

assert isinstance(StubSystem(), System), \
    "Protocol structural typing must work for non-ABC mocks (FR-010)"
```

**Rationale**: ADR-003 keeps the `runtime_checkable Protocol System` alongside
`SystemBase` so that test mocks and any third-party System implementations
that don't inherit from the ABC continue to satisfy the structural type.

**Test location**: `tests/unit/engine/systems/test_system_protocol.py` (new
or expanded).

## P5 — `TickEvent` discriminator dispatch

```python
from pydantic import TypeAdapter, ValidationError
from babylon.models.events import TickEvent, ExtractionEvent

adapter = TypeAdapter(TickEvent)

# Valid: known kind
event = ExtractionEvent(kind="extraction", tick=0, timestamp="2026-01-01T00:00:00Z",
                        amount=100.0, source="test")
roundtrip = adapter.validate_python(event.model_dump())
assert roundtrip == event, "Variant must roundtrip via discriminator"

# Invalid: missing kind
try:
    adapter.validate_python({"tick": 0, "timestamp": "..."})
    assert False, "Missing 'kind' must raise ValidationError"
except ValidationError as e:
    assert "discriminator" in str(e).lower()

# Invalid: unknown kind
try:
    adapter.validate_python({"kind": "fake_kind", "tick": 0, "timestamp": "..."})
    assert False, "Unknown 'kind' must raise ValidationError"
except ValidationError as e:
    assert "discriminator" in str(e).lower()
```

**Test location**: `tests/unit/models/test_tick_event_discriminator.py` (new;
introduced by ADR-004 step 1).

## P6 — `Scenario` registry contract

```python
from babylon.engine.scenarios.base import Scenario, _SCENARIO_REGISTRY
from babylon.engine.scenarios.imperial_circuit import ImperialCircuitScenario

# Registry populated at import time
assert "imperial_circuit" in _SCENARIO_REGISTRY
assert _SCENARIO_REGISTRY["imperial_circuit"] is ImperialCircuitScenario

# Subclass collision is fatal
try:
    class DuplicateName(Scenario):
        name = "imperial_circuit"  # collision
        description = "duplicate"
        def build_territories(self): return {}
        def build_classes(self): return {}
        def build_relationships(self): return {}
    assert False, "Duplicate scenario name must raise"
except ValueError:
    pass
```

**Test location**: `tests/unit/engine/scenarios/test_scenario_registry.py`
(new; introduced by ADR-006.1).

## Acceptance gate

This contract is satisfied when:

1. All `assert isinstance(...)` and `issubclass(...)` checks pass on the
   post-Bundle-2 branch.
2. `tests/contract/persistence/`, `tests/contract/engine/` directories are
   green.
3. `mise run test:int` includes the new contract tests and they pass.
