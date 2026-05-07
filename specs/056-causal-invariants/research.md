# Phase 0 Research: Causal/Temporal Invariants

**Feature**: 056-causal-invariants
**Date**: 2026-05-07
**Spec**: [spec.md](./spec.md)

## Purpose

Resolve open implementation patterns and surface findings that emerged from
reading the production code. The three `/speckit.clarify` decisions are
already in `spec.md` (Material Base / Action Phase / Consequences partition;
strict-raise monotonicity contract; `run_tick` patch boundary); this
document records the *technical* decisions that follow from them.

---

## §1. System partition constants — declaration site and integrity

**Decision**: Declare three module-level `Final[frozenset[type[System]]]`
constants in `src/babylon/engine/simulation_engine.py`, immediately
adjacent to the `_DEFAULT_SYSTEMS` list:

```python
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

**Partition integrity assertion**: at import time, the module asserts:

```python
_ALL_PARTITIONED = MATERIAL_BASE_SYSTEMS | ACTION_PHASE_SYSTEMS | CONSEQUENCE_SYSTEMS
_DEFAULT_SYSTEM_TYPES = frozenset(type(s) for s in _DEFAULT_SYSTEMS)
assert _ALL_PARTITIONED == _DEFAULT_SYSTEM_TYPES, (
    f"Partition drift: {_DEFAULT_SYSTEM_TYPES ^ _ALL_PARTITIONED}"
)
assert len(MATERIAL_BASE_SYSTEMS & ACTION_PHASE_SYSTEMS) == 0
assert len(MATERIAL_BASE_SYSTEMS & CONSEQUENCE_SYSTEMS) == 0
assert len(ACTION_PHASE_SYSTEMS & CONSEQUENCE_SYSTEMS) == 0
```

**`_DEFAULT_SYSTEMS` reorder requirement (F6 — added 2026-05-07
post-verification)**: The codebase currently orders `OODASystem` at
position 21 (last), after every Consequence System. This contradicts
the partition's *temporal* meaning. As part of T004's Phase 2
production work, `_DEFAULT_SYSTEMS` MUST be reordered so the list
reads:

```python
_DEFAULT_SYSTEMS: list[System] = [
    # Material Base (positions 1-13) — unchanged from current order
    VitalitySystem(), TerritorySystem(), ProductionSystem(),
    TickDynamicsSystem(), ReserveArmySystem(), CommunitySystem(),
    LifecycleSystem(), SolidaritySystem(), ImperialRentSystem(),
    DispossessionEventSystem(), DecompositionSystem(),
    ControlRatioSystem(), MetabolismSystem(),
    # Action Phase (position 14) — MOVED from position 21
    OODASystem(),
    # Consequences (positions 15-21) — unchanged from current order;
    # only their absolute positions shifted by +1 due to OODA insertion
    SurvivalSystem(), StruggleSystem(), ConsciousnessSystem(),
    ContradictionSystem(), ContradictionFieldSystem(),
    FieldDerivativeSystem(), EdgeTransitionSystem(),
]
```

**Reorder risk**: any existing test or production caller that depends
on OODA running *after* the field-topology Systems would break.
Empirical audit during T004 surfaces such callers; the resolution is
case-by-case: either move dependent computation upstream, or document
the dependency as a `bypasses_causal_invariant` exception with
escalation per IX governance. Default expectation per the user's
spec prompt is that the dependency does NOT exist — OODA was placed
last historically without a load-bearing reason.

**Rationale**: Three constants instead of one because (a) US1 needs to
identify Material Base members for the "before OODA" predicate, (b) US2
needs to identify Consequence members for the "after all OODA actions"
predicate, and (c) the Action Phase is currently a single class but
declared as a set so future Action Phase additions (e.g., a per-organization
"deliberation review" pass) extend the partition without restructuring.
The import-time assertions are the safety net for "adding a new System
forces classification into exactly one set" per FR-002. A maintainer
who adds a new System without classifying it gets an `AssertionError` at
the next module import — the test harness picks this up automatically
because `simulation_engine.py` imports during test collection.

**Alternatives considered**:

- *Per-System ClassVar marker*: `class VitalitySystem: causal_layer:
  ClassVar[CausalLayer] = CausalLayer.MATERIAL_BASE`. Rejected because it
  spreads classification across 21 files, increasing coordination cost and
  making the classification harder to read at a glance. The single-file
  partition is more legible and the import-time assertion catches drift.
- *Test-side hardcoded list*: Rejected by FR-002 ("no hand-maintained
  duplicate list in the test module").
- *Auto-classification via `__module__` heuristics* (e.g., everything in
  `engine/systems/economic.py` is Material Base): Rejected because it
  couples classification to file layout and breaks if a future refactor
  splits or merges System modules.

---

## §2. OODA per-organization action spy injection seam

**Decision (revised 2026-05-07 per F1 finding)**: Extract a private
helper method `_resolve_for_organization(self, graph, services,
context, org_id, org_data, ...)` on `OODASystem` that contains the
per-organization loop body currently inlined at `ooda.py:79–~190`. The
`OrganizationActionSpy` then uses `unittest.mock.patch.object` on this
named method — exactly the seam `unittest.mock.patch.object` expects.

The original "wrap the for-loop body via `patch.object`" decision was
unbuildable: `patch.object` patches **named class members**, not
inline loop bodies. There is no syntactic seam to grab without either
(a) a named helper method or (b) AST instrumentation. Option (a) is
the cleanest: a 5-line refactor that doesn't change behavior.

**The refactor in OODASystem.step**:

```python
def step(self, graph, services, context):
    org_nodes = _collect_org_nodes(graph)  # existing module-level helper
    max_orgs = ...
    for org_id, org_data in org_nodes[:max_orgs]:
        self._resolve_for_organization(
            graph, services, context, org_id, org_data
        )

def _resolve_for_organization(self, graph, services, context,
                               org_id, org_data) -> None:
    """Resolve one organization's action for the current tick.

    Extracted from `step` body for test-time instrumentation
    (Spec 056 US2). Behavior preserved; refactor is internal.
    """
    # ... body that was previously inlined inside the for loop
```

**Rationale**: Four reasons.

1. **`patch.object` requires a named target**. The original spec text
   was unbuildable as written.
2. **Refactor is behavior-preserving**. The loop body becomes a method;
   no semantic change. A short empirical audit during T011 confirms
   no regressions in existing OODA tests.
3. **Production overhead is zero**. A method call adds ~50 ns vs.
   inline; OODA already runs once per tick at low frequency.
4. **The seam is now stable**. Future internal refactors of
   `_resolve_for_organization` don't break the spy as long as the
   method name + signature are preserved. Rename / signature change
   triggers a loud test failure that points at the seam.

**Alternatives considered**:

- *Production hook seam* (`action_resolved_hooks: list[Callable]`):
  Heavier; injects test-only concerns into production constructor.
  Rejected.
- *AST instrumentation*: Overengineered.
- *Patching `OODASystem.step` entirely*: Cannot capture per-org
  timestamps. US2 needs per-org granularity for the order-independence
  predicate (Acceptance Scenario 3).

**Failure-mode analysis**: If a future refactor *removes* the
`_resolve_for_organization` helper, T011's `patch.object` call raises
`AttributeError` immediately on test setup. This is the desired
fail-loud behavior: the spy harness's docstring explicitly records the
seam dependency so a maintainer knows where to fix.

---

## §3. Spy non-interference verification (FR-012)

**Decision**: A dedicated test in
`test_material_base_ordering.py::test_spy_does_not_alter_post_state`
runs the same starting `WorldState` through `run_tick` twice — once
with `SystemCallSpy` + `OrganizationActionSpy` active, once without —
and asserts that the resulting post-tick `WorldState.model_dump()` is
equal under the same exclude rules used by Spec 055 US4
(`SOCIAL_CLASS_COMPUTED_FIELDS`, `TERRITORY_EXCLUDED_FIELDS`).

**Rationale**: FR-012 is the harness's own integrity guarantee — without
it, the spy itself could be the bug it's trying to catch. The Spec 055
exclude rules are already imported via the
`_build_exclude_paths_from_production` helper; reusing them keeps the
non-interference check aligned with the round-trip identity check from
Spec 055.

**Determinism caveat**: Both runs MUST use the same `random.seed` /
Hypothesis-injected seed. The `worldstate_strategy()` strategy is
deterministic per Hypothesis example, so this is automatic; the test
explicitly captures the starting state with `state.model_copy(deep=True)`
before the first run to insulate the comparison from any
shared-mutability surprises.

---

## §4. DB-bearing service introspection on ServiceContainer

**Decision**: The `no_db_io_during_tick` context manager enumerates
`ServiceContainer` attributes via `dataclasses.fields(container)` (since
`ServiceContainer` is a `@dataclass`) and patches every field whose
*declared type annotation* matches one of: `DatabaseConnection`,
`RuntimePersistence` (Protocol), `Any` (treated as opaque, conservatively
patched), or any class whose name matches the regex
`(?i).*(database|persistence|runtime|store).*`. The patch wraps each
field's `__getattr__` (or direct callable surface where applicable) with
a sentinel that raises `DBIONotPermittedError` on any access.

**Rationale**: Per FR-005 ("the list of surfaces MUST be derived from
introspection of `ServiceContainer` at test time"), a hardcoded list is
forbidden. Introspection over `dataclasses.fields` gives the canonical
attribute set and its declared types; the regex is a defense-in-depth
catch for service classes added via duck-typed `Any` fields (currently
just `persistence: Any`).

**Surface inventory at time of writing**:

| Field | Type | Patch behavior |
|-------|------|----------------|
| `database` | `DatabaseConnection` | Replace with sentinel; any attribute access raises `DBIONotPermittedError` |
| `persistence` | `Any` | If non-None and matches regex, patch the same way; if None, skip |
| `metrics` | `MetricsCollector` | NOT patched — metrics is an in-memory dict, no DB |
| `event_bus` | `EventBus` | NOT patched — events are in-memory pub/sub |
| `formula_registry` | `FormulaRegistry` | NOT patched — formulas are pure functions |
| `config` | `SimulationConfig` | NOT patched — config is frozen Pydantic model |

**Pgvector / Postgres extensions**: The `pgvector_store.py` and
`PostgresRuntimeExtensions` protocol are exposed via the `persistence`
field today. They get caught by the regex (`store` substring,
`runtime` substring) and patched.

**Alternatives considered**:

- *Hardcoded list `("database", "persistence")`*: Rejected by FR-005.
- *`isinstance` check against a `DBBearing` marker base class*: Would
  require touching every persistence module to inherit from a marker.
  Rejected as overengineering.
- *Block all non-frozen-model attribute access*: Too aggressive; would
  block `metrics.record(…)` which is legitimate in-memory state.

---

## §5. Persistence overwrite detection mechanism (revised 2026-05-07 per F7=B)

**Decision**: Implement **monotonic-idempotent** semantics in both
`RuntimeDatabase` and `PostgresRuntime` per the F7 clarification.
Same-payload re-`persist_tick` succeeds idempotently (preserving
existing UPSERT-retry callers — the audit found two:
`persistence_observer.py:146` and `session_recorder.py:168`, both
single-call-per-tick patterns that benefit from idempotent retry on
network glitches). Different-payload re-`persist_tick` raises
`MonotonicityViolationError`. Implementation differs by backend:

**`RuntimeDatabase.persist_tick`** (in-memory):

```python
def persist_tick(self, tick, graph, events=None, *, session_id=None):
    key = (session_id, tick)
    new_payload = self._serialize(graph, events)
    if key in self._states:
        existing = self._states[key]
        if existing == new_payload:
            return  # idempotent — same payload, accept
        raise MonotonicityViolationError(
            tick=tick,
            existing_payload=existing,
            attempted_payload=new_payload,
        )
    self._states[key] = new_payload
```

**`PostgresRuntime.persist_tick`** (durable):

```python
def persist_tick(self, tick, graph, events=None, *, session_id):
    new_payload = self._serialize(graph, events)
    try:
        # INSERT (no ON CONFLICT clause — let UniqueViolation surface)
        cursor.execute(INSERT_SQL, (session_id, tick, new_payload))
    except psycopg.errors.UniqueViolation:
        # SELECT existing payload for comparison
        existing = cursor.execute(SELECT_SQL, (session_id, tick)).fetchone()
        if existing == new_payload:
            return  # idempotent — same payload, accept
        raise MonotonicityViolationError(
            tick=tick,
            existing_payload=existing,
            attempted_payload=new_payload,
        )
```

**Rationale**: The `UNIQUE (session_id, tick)` constraint at the
schema level provides the fail-loud detection (cannot be silently
bypassed by raw SQL); the SELECT-then-compare on `UniqueViolation`
provides the idempotent same-payload acceptance. This combines the
strongest detection mechanism with the contract chosen in F7=B.

**Payload comparison strategy**: Both backends compare the *serialized*
payload (the final dict / JSON / bytes that would be written), not the
in-memory object. This avoids spurious mismatches from non-deterministic
ordering of dict keys, set iteration, etc. The serialization is
already deterministic (canonical JSON ordering) per Spec 037's existing
contract.

**Schema-migration impact**: If the existing runtime state table does
NOT already carry a `UNIQUE (session_id, tick)` constraint, this
requires a migration. The migration is part of T008. For local
development, the migration runs via the existing `mise run web:migrate`
task; for CI, the `mise run test:integration` invocation creates a
fresh transient database per run, so no historical state collision
risk. For existing databases with duplicate `(session_id, tick)` rows
(unlikely but possible), the migration script first runs a dedup pass
documenting which records were collapsed.

**Existing UPSERT-caller audit (F7=B prerequisite)**:

| Caller | File:line | Pattern | Behavior under new contract |
|--------|-----------|---------|------------------------------|
| `PersistenceObserver._persist_tick` | `persistence_observer.py:146` | One call per tick per session | Unchanged — never overwrites |
| `SessionRecorder.record_tick` | `session_recorder.py:168` | One call per tick per session | Unchanged — never overwrites |
| Test: `test_postgres_integration.py:154` | for-loop over distinct ticks | Each call has unique `tick` | Unchanged — never overwrites |
| Test: `test_postgres_runtime.py` various | Each call has unique `(tick, session_id)` | Unchanged — never overwrites |

No production caller currently retries `persist_tick` on the same
`(tick, session_id)` pair. The new monotonic-idempotent contract is
strictly more permissive than the *behavior* of existing callers (it
allows retries that don't occur today) and more restrictive than the
*documented* contract (it forbids silent overwrite-with-different).
Net: zero behavioral regressions expected.

**Alternatives considered**:

- *Strict raise (original Q2 answer)*: Rejected post-verification —
  the existing protocol docstring promises UPSERT idempotency, and
  some future caller may depend on it for retry safety. The
  monotonic-idempotent reframe preserves the retry promise while
  blocking history rewrites.
- *PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`*: Silent on different
  payload — exactly the bug we're catching.
- *PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`*: Silent rewrite of
  history.
- *`psycopg`-level `RETURNING` + caller-side comparison*: Pushes the
  contract enforcement out of the persistence layer; rejected as
  weaker discipline.

---

## §6. Aleksandrov Test trace (Constitution III.8)

Each invariant in this feature is grounded in a documented constitutional
or architectural commitment:

| Invariant | Grounded in | Material relation |
|-----------|-------------|-------------------|
| US1 (Material Base before Action Phase) | ADR032 Materialist Causality; Constitution I.18 (Material-Ideological Distinction) | Material conditions exist objectively before consciousness can deliberate over them; OODA reads a material snapshot, never a partial one |
| US2 (Consequences after all OODA actions) | Constitution I.17 OODA; III.7 Determinism | Replay requires order-independence over the organization set; per-organization actions complete before any aggregator runs |
| US3 (No DB I/O during tick) | Constitution II.6 ("No DB I/O during tick" — verbatim); II.10 World Runtime; II.11 Subsystem Table Ownership; ADR037 Postgres Runtime | The engine is a pure transformation; intra-tick I/O is non-determinism by another name |
| US4 (Persistence monotonic in tick) | Constitution II.6 (State is Data); II.10 World Runtime; III.7 Determinism (replay from any tick) | Audit trail is immutable; once tick N is durable it cannot be silently rewritten |

No invariant introduces a new primitive, redefines an existing one, or
relaxes a prohibition. Each is the *operational realization* of an
already-declared constitutional commitment.

---

## §7. Multi-tick sequence for US4 monotonicity

**Decision**: A small synthetic strategy
`tests/property/strategies/multi_tick_sequence.py` produces a
`list[tuple[int, dict]]` of `(tick, payload)` pairs of length 5. The
payloads are minimal Pydantic-serializable dicts (matching the
`RuntimePersistence.persist_tick` signature); they need not be valid
WorldStates because US4 tests the persistence contract, not the engine
trajectory.

The test exercises four predicates (revised 2026-05-07 per F7=B):

1. **Predicate A**: 5 sequential `persist_tick` calls succeed;
   `hydrate_graph` returns the originally-written payloads for each.
2. **Predicate B (different payload)**: After tick N is persisted,
   attempting `persist_tick(N, different_payload, ...)` raises
   `MonotonicityViolationError`. Re-`hydrate_graph(N)` returns the
   original payload.
3. **Predicate B' (same payload — idempotent retry)**: After tick N
   is persisted, attempting `persist_tick(N, same_payload, ...)`
   succeeds without raising. `hydrate_graph(N)` returns the
   payload unchanged. This validates the retry semantics for
   `persistence_observer.py:146` and `session_recorder.py:168`.
4. **Predicate C (back-in-time rewrite)**: After ticks 0..4 are
   persisted, attempting `persist_tick(2, different_payload, ...)`
   raises `MonotonicityViolationError` and leaves all 5 records
   intact.

**Rationale**: 5 ticks is enough to exercise the back-in-time predicate
without making the integration test slow. The synthetic payloads
isolate the persistence contract from engine semantics — the test
catches a regression in the persistence layer even if the engine itself
breaks elsewhere.

**Alternatives considered**:

- *Use a real engine to produce payloads*: Couples US4 to engine
  correctness, which is already covered by Specs 053–055. Rejected for
  isolation.
- *Single-tick test*: Cannot exercise the back-in-time predicate.
- *Full-state Hypothesis-generated payloads*: Slower than necessary;
  the persistence contract holds for any payload shape.

---

## §8. Test isolation: spies + patched services + real engine state

**Decision**: Each US1 / US2 / US3 test runs in a pytest-managed
function scope with fresh `SystemCallSpy`, `OrganizationActionSpy`, and
`no_db_io_during_tick` instances per example. The Hypothesis
`@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])`
allowance is reused from Spec 055 to permit per-example fixture
construction (matching the existing pattern in
`test_community_membership_lint.py`).

**Rationale**: Each Hypothesis example must run in isolation — a stale
spy recording or a leaked patched service would corrupt subsequent
examples. The function-scoped fixture pattern is established by Spec 055
and integrates cleanly with Hypothesis.

**Service container construction**: Tests build a
`ServiceContainer.testing()` instance per example (following Spec 053 /
054's `service_container_fixture`) so the patched-services scope does
not leak across examples.

---

## §9. Spec 053 / 054 / 055 reuse

| Asset | Reused as-is | Why |
|-------|--------------|-----|
| `tests/property/conftest.py` profile registration | ✓ | Same default / dev / ci / nightly profiles work for all four tests |
| `tests/property/strategies/worldstate.py::worldstate_strategy` | ✓ | US1 + US2 + US3 generate `WorldState` instances; US2 uses `min_entities=2` for org-bearing examples |
| `tests/property/harness/system_registry.py::all_systems` | ✓ | US1 + US2 wrap every System via SystemCallSpy |
| `tests/property/harness/bound_harness.py::HarnessResult` | ✓ | Same dataclass shape for spy assertions |
| `tests/property/harness/topology_harness.py` patterns | ✓ (style only) | `CausalInvariantHarness` mirrors `TopologyInvariantHarness` shape |
| `_iter_worldstate_collections` (Spec 054) | ✓ | Not directly used by US1–US4, but available for future causal predicates |
| `bypasses_*_invariant` ClassVar marker pattern | ✓ (rename to `bypasses_causal_invariant`) | Same semantics, same machine-enforcement of non-empty justifications |
| Spec 055 `_build_exclude_paths_from_production` | ✓ | Reused in US1 spy non-interference test (FR-012) |
| `ServiceContainer.testing()` factory | ✓ | Per-test container construction |

**New infrastructure**:
- `causal_harness.py` — small module declaring the `SystemCallEvent`,
  `OrganizationActionEvent`, `TickTrace` frozen dataclasses (the
  earlier `CausalInvariantHarness` runner class is dropped per
  C1 finding — tests use spy + context manager primitives directly,
  matching Spec 055's `TopologyInvariantHarness` light-touch usage)
- `system_call_spy.py` — wraps each System.step
- `org_action_spy.py` — patches `OODASystem._resolve_for_organization`
  via `patch.object` (post-F1 helper extraction)
- `no_db_io_during_tick.py` — context manager patching DB-bearing services
- `multi_tick_sequence.py` — strategy for US4 synthetic payloads
- Three production constants (`MATERIAL_BASE_SYSTEMS`,
  `ACTION_PHASE_SYSTEMS`, `CONSEQUENCE_SYSTEMS`)
- One production exception class (`MonotonicityViolationError`) and
  monotonic-idempotent overwrite detection in two `RuntimePersistence`
  implementations
- One production helper extraction:
  `OODASystem._resolve_for_organization` (loop-body lift; behavior-
  preserving refactor)
- One production reorder: `_DEFAULT_SYSTEMS` (move `OODASystem` from
  position 21 to position 14)

**Estimated harness LOC**: ~230 lines new (vs. ~210 LOC added by Spec 055
to the same harness directory; Spec 056 dropped `CausalInvariantHarness`
per C1 saving ~20 LOC). Most of the new LOC is in `system_call_spy.py`
+ `no_db_io_during_tick.py` due to the introspection logic.

**Production diff size**: ~50 LOC (3 partition constants + import-time
assertion + `MonotonicityViolationError` + 2 overwrite-detection
methods + 1 OODA helper extraction + 1 `_DEFAULT_SYSTEMS` reorder).
