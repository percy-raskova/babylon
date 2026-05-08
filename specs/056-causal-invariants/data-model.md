# Phase 1 Data Model: Causal/Temporal Invariants

**Feature**: 056-causal-invariants
**Date**: 2026-05-07

## Purpose

Enumerate every test-side and production-side entity introduced or extended
by this feature. Each entity is named, given a Pydantic-or-frozen-dataclass
shape, and tied to the user story / functional requirement it serves.

This feature is testing infrastructure with a small production surface:
three System-classification constants in `simulation_engine.py`, one new
exception class in `persistence/protocols.py`, and overwrite-detection
additions to two `RuntimePersistence` implementations. Every other entity
lives under `tests/property/`.

---

## §1. Production-side entities

### §1.1 `MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` / `CONSEQUENCE_SYSTEMS`

**File**: `src/babylon/engine/simulation_engine.py`

**Type**: `Final[frozenset[type[System]]]`

**Shape**:

```python
from typing import Final

MATERIAL_BASE_SYSTEMS: Final[frozenset[type[System]]] = frozenset({
    VitalitySystem, TerritorySystem, ProductionSystem, TickDynamicsSystem,
    ReserveArmySystem, CommunitySystem, LifecycleSystem, SolidaritySystem,
    ImperialRentSystem, DispossessionEventSystem, DecompositionSystem,
    ControlRatioSystem, MetabolismSystem,
})
ACTION_PHASE_SYSTEMS: Final[frozenset[type[System]]] = frozenset({OODASystem})
CONSEQUENCE_SYSTEMS: Final[frozenset[type[System]]] = frozenset({
    SurvivalSystem, StruggleSystem, ConsciousnessSystem, ContradictionSystem,
    ContradictionFieldSystem, FieldDerivativeSystem, EdgeTransitionSystem,
})
```

**Invariants** (asserted at module import time):

- `MATERIAL_BASE_SYSTEMS | ACTION_PHASE_SYSTEMS | CONSEQUENCE_SYSTEMS == frozenset(type(s) for s in _DEFAULT_SYSTEMS)`
- `MATERIAL_BASE_SYSTEMS.isdisjoint(ACTION_PHASE_SYSTEMS)`
- `MATERIAL_BASE_SYSTEMS.isdisjoint(CONSEQUENCE_SYSTEMS)`
- `ACTION_PHASE_SYSTEMS.isdisjoint(CONSEQUENCE_SYSTEMS)`

**`_DEFAULT_SYSTEMS` reorder requirement (added 2026-05-07 per F6=α)**:
The list MUST be reordered so `OODASystem` executes at position 14
(immediately after `MetabolismSystem`, immediately before
`SurvivalSystem`). The current codebase orders OODA at position 21
(last); the reorder is part of T004's Phase 2 production work. Without
the reorder, US1 trivially passes (everything precedes OODA) and US2
trivially fails (every Consequence runs before OODA, never after).

**Used by**: US1 (`test_material_base_ordering.py`), US2
(`test_consequence_after_actions.py`).

**FR linkage**: FR-002.

---

### §1.2 `MonotonicityViolationError`

**File**: `src/babylon/persistence/protocols.py`

**Type**: Exception class.

**Shape**:

```python
class MonotonicityViolationError(Exception):
    """Raised when persist_tick is called with a DIFFERENT payload for
    an already-persisted tick.

    Per Constitution II.6 (State is Data) and III.7 (Determinism), the
    persisted record for tick N is immutable once written *with respect
    to its content*. Implementations of `RuntimePersistence.persist_tick`
    MUST raise this exception when a re-persist supplies a payload that
    differs from the already-stored payload for the same
    (session_id, tick) pair. A re-persist with the *same* payload (the
    canonical UPSERT-retry pattern used by the persistence observer
    and session recorder) succeeds idempotently and does NOT raise.

    See data-model.md §1.3 and research.md §5 for the comparison
    semantics (canonical-serialized-payload equality).
    """

    def __init__(
        self,
        tick: int,
        existing_payload: dict | None = None,
        attempted_payload: dict | None = None,
    ) -> None:
        self.tick = tick
        self.existing_payload = existing_payload
        self.attempted_payload = attempted_payload
        super().__init__(
            f"Cannot overwrite already-persisted tick {tick} with "
            f"different payload (use identical payload for idempotent retry)"
        )
```

**Used by**: US4 (`test_tick_persistence_monotonic.py`).

**FR linkage**: FR-007 (US4 monotonic-idempotent contract; revised
clarification 2026-05-07 Q2 + F7=B post-verification).

---

### §1.3 `RuntimePersistence.persist_tick` contract refinement

**File**: `src/babylon/persistence/protocols.py`

**Change**: Docstring **refinement** of the existing `persist_tick`
method (no signature change). The current docstring says:

> Idempotent via UPSERT semantics.

The refined docstring (per F7=B clarification) says:

> Monotonic-idempotent. If `(session_id, tick)` already has a
> persisted payload, the implementation MUST compare the new payload
> against the existing payload (canonical-serialized equality):
>
> - **Same payload**: succeed silently (idempotent retry — preserves
>   the existing observer / recorder retry semantics).
> - **Different payload**: raise `MonotonicityViolationError` with
>   `existing_payload`, `attempted_payload`, and `tick` populated.
>
> Silent overwrite of differing payloads is forbidden — it would
> silently rewrite history.

The actual method names on the existing `RuntimePersistence` Protocol
are confirmed at `protocols.py:40` (write) and `protocols.py:60`
(read):

- **Write**: `persist_tick(self, tick, graph, events=None, *, session_id=None) -> None`
- **Read**: `hydrate_graph(self, tick=None, *, session_id=None) -> nx.DiGraph[str]`

The earlier draft references to `write_state` / `read_tick` were
placeholders pre-verification; they are corrected throughout this
spec set.

Both implementations (`RuntimeDatabase`, `PostgresRuntime`) acquire
monotonic-idempotent detection. Per `research.md §5`:

- `RuntimeDatabase.persist_tick` performs an in-memory check:
  `if (session_id, tick) in self._states and self._states[(session_id, tick)] != new_payload: raise MonotonicityViolationError(...)` before writing; same payload returns silently.
- `PostgresRuntime.persist_tick` relies on a `UNIQUE (session_id, tick)`
  constraint at the schema level; on `psycopg.errors.UniqueViolation`,
  performs a SELECT to fetch the existing payload, compares against
  the new payload, and either returns silently (same) or raises
  `MonotonicityViolationError` (different).

**Used by**: US4.

**FR linkage**: FR-007.

**Existing-caller audit (from F7=B verification)**:

| Caller | File:line | Pattern | Behavior under new contract |
|--------|-----------|---------|------------------------------|
| `PersistenceObserver._persist_tick` | `persistence_observer.py:146` | One call per tick per session | Unchanged — never overwrites |
| `SessionRecorder.record_tick` | `session_recorder.py:168` | One call per tick per session | Unchanged — never overwrites |
| `tests/integration/test_postgres_integration.py` | for-loop, distinct ticks | Distinct `(tick, session_id)` per call | Unchanged |
| `tests/unit/persistence/test_postgres_runtime.py` | various tests | Distinct `(tick, session_id)` per call | Unchanged |

No production caller currently re-persists the same `(tick, session_id)`
with a different payload. The new contract is strictly additive:
preserves existing UPSERT-retry behavior, blocks silent rewrite.

---

## §2. Test-side entities

### §2.1 `causal_harness.py` module — shared dataclasses

**File**: `tests/property/harness/causal_harness.py`

**Note (revised 2026-05-07 per C1 finding)**: The original draft
declared a `CausalInvariantHarness` class with `run_tick_with_spies()`
and `run_tick_with_no_db_io()` methods. That class was unused — every
test in Phases 3–6 invokes the spy / context-manager primitives
(`SystemCallSpy`, `OrganizationActionSpy`, `no_db_io_during_tick`)
directly without going through a wrapper. Per C1 + YAGNI, the wrapper
class is dropped. The module remains as a thin home for the shared
event dataclasses (`SystemCallEvent`, `OrganizationActionEvent`,
`TickTrace`) defined in §2.2 / §2.3 / §2.4 — it has no class
definitions of its own.

**Module exports**: re-exports `SystemCallEvent` (from §2.2),
`OrganizationActionEvent` (from §2.3), `TickTrace` (from §2.4),
`SystemCallSpy` (from §2.2), `OrganizationActionSpy` (from §2.3),
`no_db_io_during_tick` (from §2.5), `DBIONotPermittedError`
(from §2.5). Tests import from this single module.

**Used by**: All four invariant tests (as the import surface).

**FR linkage**: FR-001 (consolidated import surface for one-test-per-invariant).

---

### §2.2 `SystemCallSpy`

**File**: `tests/property/harness/system_call_spy.py`

**Type**: Context manager.

**Shape**:

```python
@dataclass(frozen=True)
class SystemCallEvent:
    system_class_name: str
    call_index: int
    monotonic_timestamp_ns: int


class SystemCallSpy:
    """Wraps every System.step in the engine's system list.

    Records a `SystemCallEvent` on each invocation. Forwards args / kwargs
    and the return value unchanged (FR-003). The spy's only side-effect
    is appending to `self.events`.
    """

    events: list[SystemCallEvent]

    def __init__(self, engine: SimulationEngine) -> None: ...
    def __enter__(self) -> "SystemCallSpy": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

**Used by**: US1 (`test_material_base_ordering.py`), US2
(`test_consequence_after_actions.py`).

**FR linkage**: FR-003.

---

### §2.3 `OrganizationActionSpy`

**File**: `tests/property/harness/org_action_spy.py`

**Type**: Context manager.

**Shape**:

```python
@dataclass(frozen=True)
class OrganizationActionEvent:
    organization_id: str
    action_resolution_index: int
    monotonic_timestamp_ns: int


class OrganizationActionSpy:
    """Wraps the per-organization loop iteration inside OODASystem.step.

    Records an `OrganizationActionEvent` for every organization processed
    in the current tick. Implemented via `unittest.mock.patch.object`
    on the inner loop iteration closure (per research.md §2).
    """

    events: list[OrganizationActionEvent]

    def __init__(self) -> None: ...
    def __enter__(self) -> "OrganizationActionSpy": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

**Used by**: US2 (`test_consequence_after_actions.py`).

**FR linkage**: FR-004.

---

### §2.4 `TickTrace`

**File**: `tests/property/harness/causal_harness.py`

**Type**: Frozen dataclass aggregating one tick's spy events.

**Shape (simplified 2026-05-07 per C2 finding)**:

```python
@dataclass(frozen=True)
class TickTrace:
    """Frozen aggregator pairing system-call and per-organization-action
    event lists from a single tick.

    Tests iterate `system_calls` and `org_actions` directly with list
    comprehensions and standard helpers (`max`, `next`, etc.) — no
    helper methods on this dataclass. This matches Spec 055's
    light-touch use of its own harness aggregators. The shape is purely
    to bundle the two event sequences together for one-tick-at-a-time
    test loops.
    """

    system_calls: tuple[SystemCallEvent, ...]
    org_actions: tuple[OrganizationActionEvent, ...]  # empty tuple if not captured
```

The original draft included `call_index_of()`, `material_base_call_indices()`,
and `max_action_resolution_timestamp()` helper methods. Per C2 + YAGNI,
these are removed — every test task in Phases 3–6 uses inline
comprehensions over `spy.events` lists. If a future test pattern emerges
that calls one of these queries 3+ times, extract it into a helper at
that point; until then, keep the dataclass minimal.

**Used by**: US1 (`test_material_base_ordering.py`), US2
(`test_consequence_after_actions.py`).

**FR linkage**: FR-003 (system-call recording), FR-004 (org-action recording).

---

### §2.5 `no_db_io_during_tick`

**File**: `tests/property/harness/no_db_io_during_tick.py`

**Type**: Context-manager factory function.

**Shape**:

```python
class DBIONotPermittedError(Exception):
    """Raised when a patched DB surface is accessed inside a tick scope."""

    def __init__(self, surface: str, attribute: str) -> None: ...


@contextmanager
def no_db_io_during_tick(
    services: ServiceContainer,
) -> Iterator[None]:
    """Patch every DB-bearing service on `services` to raise on any access.

    Implementation per research.md §4: introspect `dataclasses.fields(services)`,
    identify DB-bearing fields by declared type or name regex, replace each
    with a sentinel that raises `DBIONotPermittedError` on attribute access.
    Restores originals on exit.

    Patch entry: immediately on `with` entry.
    Patch exit: immediately on `with` exit (including exception path).

    The harness's `run_tick_with_no_db_io` invokes
    `engine.run_tick(graph, services, context)` inside this context manager,
    matching the `run_tick` boundary chosen in clarification Q3.
    """
```

**Used by**: US3 (`test_no_db_io_during_tick.py`).

**FR linkage**: FR-005, FR-006.

---

### §2.6 `multi_tick_sequence_strategy`

**File**: `tests/property/strategies/multi_tick_sequence.py`

**Type**: Hypothesis strategy.

**Shape**:

```python
def multi_tick_sequence_strategy(
    *,
    n_ticks: int = 5,
) -> SearchStrategy[list[tuple[int, dict]]]:
    """Generate a list of (tick, payload) pairs for US4 monotonicity tests.

    Each payload is a minimal Pydantic-serializable dict matching the
    RuntimePersistence.persist_tick signature. Payloads need not be valid
    WorldStates — US4 tests the persistence contract, not engine semantics
    (per research.md §7).

    Returns:
        Strategy producing list[tuple[int, dict]] of length n_ticks.
    """
```

**Used by**: US4 (`test_tick_persistence_monotonic.py`).

**FR linkage**: FR-001.

---

### §2.7 `bypasses_causal_invariant` ClassVar marker

**Shape**: Mirrors Spec 054's `bypasses_bound_invariant` and Spec 055's
`bypasses_topology_invariant`:

```python
class SomeSystem:
    bypasses_causal_invariant: ClassVar[dict[str, str]] = {
        "no_db_io_during_tick": (
            "Reads static reference table that cannot be hydrated up front "
            "due to <reason>"
        ),
    }
```

**Default-deny**: A System without the marker cannot bypass any predicate.
Adding the marker requires a non-empty justification string per FR-011.

**Harness enforcement**: At test collection time, `causal_harness.py`
walks every System type in `_DEFAULT_SYSTEMS` and asserts that any
present `bypasses_causal_invariant` ClassVar maps each predicate name to
a non-empty string. Empty strings raise `AssertionError` at collection
time.

**Used by**: US1, US2, US3 (anywhere a legitimate bypass is required).

**FR linkage**: FR-011.

---

## §3. Cross-test reuse table

| Asset | US1 | US2 | US3 | US4 |
|-------|-----|-----|-----|-----|
| `causal_harness` module (shared imports) | ✓ | ✓ | ✓ | ✓ |
| `SystemCallSpy` | ✓ | ✓ | — | — |
| `OrganizationActionSpy` | — | ✓ | — | — |
| `TickTrace` | ✓ | ✓ | — | — |
| `no_db_io_during_tick` | — | — | ✓ | — |
| `multi_tick_sequence_strategy` | — | — | — | ✓ |
| `MATERIAL_BASE_SYSTEMS` (production) | ✓ | — | — | — |
| `ACTION_PHASE_SYSTEMS` (production) | ✓ | ✓ | — | — |
| `CONSEQUENCE_SYSTEMS` (production) | — | ✓ | — | — |
| `OODASystem._resolve_for_organization` (production helper, F1) | — | ✓ | — | — |
| `MonotonicityViolationError` (production) | — | — | — | ✓ |
| `RuntimeDatabase.persist_tick` (Spec 037, contract refined) | — | — | ✓ (patched) | ✓ |
| `PostgresRuntime.persist_tick` (Spec 037, contract refined) | — | — | ✓ (patched) | ✓ (integration only) |
| `worldstate_strategy` (Spec 040) | ✓ | ✓ (`min_entities=2`) | ✓ | — |
| `system_registry.all_systems` (Spec 054) | ✓ | ✓ | ✓ | — |
| Spec 055 exclude rules (`SOCIAL_CLASS_COMPUTED_FIELDS`, etc.) | ✓ (FR-012 spy non-interference) | — | — | — |

---

## §4. Validation rules

| Entity | Validation | Enforcement |
|--------|------------|-------------|
| `MATERIAL_BASE_SYSTEMS` ∪ `ACTION_PHASE_SYSTEMS` ∪ `CONSEQUENCE_SYSTEMS` | Must equal `frozenset(type(s) for s in _DEFAULT_SYSTEMS)` | Assertion at module import time of `simulation_engine.py` |
| The three partition sets | Pairwise-disjoint | Assertion at module import time |
| `MonotonicityViolationError` | Must be raised on every overwrite attempt by every `RuntimePersistence` implementation | Tested by US4 |
| `bypasses_causal_invariant` marker values | Non-empty `str` | Assertion at test collection time |
| `SystemCallSpy.events` ordering | Strictly monotonic in `monotonic_timestamp_ns` | Assertion in `SystemCallSpy.__exit__` |
| `OrganizationActionSpy.events` ordering | Strictly monotonic in `monotonic_timestamp_ns` | Assertion in `OrganizationActionSpy.__exit__` |
| Spy non-interference | Spied tick's post-state == unspied tick's post-state under Spec 055 exclude rules | Tested by `test_spy_does_not_alter_post_state` (FR-012) |

---

## §5. Migration impact

### §5.1 `simulation_engine.py`

**Adds**: 3 module-level Final frozensets + 4 import-time assertions (~30
LOC).
**Modifies**: `_DEFAULT_SYSTEMS` list — moves `OODASystem` from position
21 to position 14 (per F6=α; ~7 LOC reorder).

**Risk**: Import-time assertion failure if `_DEFAULT_SYSTEMS` is edited
without classifying the new System (intended fail-loud per FR-002).
Reorder risk: any existing test or production caller that depends on
OODA running *after* the field-topology Systems would break. Empirical
audit during T004 surfaces such callers; expected count is low because
OODA was placed last historically without a load-bearing reason.

### §5.2 `persistence/protocols.py`

**Adds**: 1 exception class (`MonotonicityViolationError`) + docstring
refinement on `persist_tick` to declare the monotonic-idempotent
contract (~20 LOC).

**Risk**: None for callers — exception is a new symbol; existing callers
don't catch it (it's expected to propagate). The docstring refinement
is contract-tightening: the existing "Idempotent via UPSERT semantics"
language becomes "Monotonic-idempotent: same payload succeeds, different
payload raises." Existing callers (audited via §1.3 table) continue to
work because none re-persists with a different payload.

### §5.3 `persistence/runtime_db.py`

**Adds**: ~6 LOC monotonic-idempotent check in `persist_tick` (compares
serialized payload against existing; raises if different, returns silently
if same).

**Risk**: Existing in-tree tests that re-persist the same `(tick,
session_id)` with a different payload (audit found zero) would start
failing. Same-payload retries (also audited as zero existing instances
but supported for future callers) succeed silently.

### §5.4 `persistence/postgres_runtime.py`

**Adds**: ~10 LOC monotonic-idempotent wrapper around the INSERT
(`UniqueViolation` → SELECT existing → compare → either return silently
or raise `MonotonicityViolationError`); plus a schema migration adding
a `UNIQUE (session_id, tick)` constraint on the runtime state table.

**Risk**: Migration coordination with existing Postgres deployments. The
migration is reversible; CI uses transient databases so no historical
state is at risk. Existing rows with duplicate `(session_id, tick)`
(very unlikely given current usage) would block the migration; T008
includes a dedup pre-check with a documented dedup pass if needed.

### §5.5 `engine/systems/ooda.py`

**Adds**: Extracted `_resolve_for_organization(self, graph, services,
context, org_id, org_data) -> None` helper method on `OODASystem`,
containing the per-organization loop body currently inlined in `step`
(per F1; ~30 LOC moved from inline to method, plus a 1-line method
call in the loop). Behavior-preserving refactor.

**Risk**: Any existing test or external code that reaches into the
inline loop body via monkey-patching `step` itself would need to update
to patch the helper. Audit during T011 surfaces such callers; expected
count is zero because the inline loop has no external test seam today.

### §5.6 `tests/property/`

**Adds**: 4 new test files + 4 new harness modules + 1 new strategy
module. No modifications to Spec 053 / 054 / 055 test files.

**Risk**: None. Pure addition.
