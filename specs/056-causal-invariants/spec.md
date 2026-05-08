# Feature Specification: Causal/Temporal Invariants — Property-Based Tests

**Feature Branch**: `056-causal-invariants`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "Causal/temporal invariants — the 'material base first' rule. Layer 0 economic metabolism runs before Action Phase, always. If this order ever inverts, organizations decide on stale economic data. Should be asserted with a call-order spy on the engine pipeline; I didn't see this. Layer 3 consequence propagation runs after all organizations have acted, not interleaved. Otherwise initiative order matters for everything, not just for ordering of actions. No DB I/O during tick execution. Hydration happens before the tick, persistence after. Testable by patching the database connection to raise and asserting no calls occur during engine.step(). Promised in the constitution; not tested as an invariant. State persistence is monotone in tick. Once tick N is persisted, the persisted state for tick N is immutable. Editing tick N would rewrite history."

## Overview

The simulation engine declares a small number of *causal/temporal invariants*
— rules about **when** things happen relative to one another that say, in
plain English, "the order of operations encodes a metaphysical commitment,
and any deviation silently corrupts the meaning of the simulation
regardless of whether the resulting numbers look reasonable." These are
not value bounds (Spec 054), not flow conservation properties (Spec 053),
and not graph-structure rules (Spec 055). They are statements about
*time inside a tick* and *time across ticks*: which Systems may run
before which other Systems, when external I/O is permitted, and what
guarantees the persistence layer makes about historical writes.

Each invariant in scope encodes a constitutional commitment:

- **Material base before Action Phase** (ADR032 Materialist Causality;
  Constitution I.18 Material-Ideological Primacy) — the economic /
  metabolic Systems (Vitality, Territory, Production, Tick Dynamics,
  Reserve Army, Solidarity, Imperial Rent, Decomposition, Control
  Ratio, Metabolism) MUST execute before any organization deliberation
  phase (`OODASystem`). If this order inverts, organizations OBSERVE
  stale economic data and deliberate against last tick's material
  conditions.
- **Consequence propagation runs after all actions** (Constitution III.2
  Falsifiability + I.17 OODA) — every organization completes its action
  resolution before any consequence-aggregation System runs. Otherwise
  initiative order silently determines outcome shape for downstream
  Systems, not just the ordering of actions themselves.
- **No DB I/O during tick execution** (Constitution II.10 World Runtime;
  ADR037 Postgres Runtime DB) — `engine.run_tick()` operates over an
  in-memory graph already hydrated. Hydration happens *before* the
  tick, persistence happens *after*. A System that opens a DB
  connection, runs a query, or commits a transaction during tick
  execution violates the determinism contract and breaks replay /
  golden-master testing.
- **State persistence is monotone in tick** (Constitution II.6 State is
  Data, II.10 World Runtime) — once tick N has been written to durable
  storage, the persisted record for tick N is immutable. Editing tick N
  rewrites history; the persistence layer must reject overwrite
  attempts at the contract level, not at the convention level.

Each invariant is independent: each can be implemented and shipped
separately, and each by itself meaningfully reduces the
"causality silent-violation" surface area. This feature follows the
harness style established by Spec 053 (conservation invariants), Spec
054 (bound invariants), and Spec 055 (topology invariants).

## Clarifications

### Session 2026-05-07

- Q: For the US1/US2 invariants, which Systems comprise the Material Base, the Action Phase, and the Consequences partition? → A: Use the ADR032-documented partition exactly. **Material Base** = Vitality, Territory, Production, TickDynamics, ReserveArmy, Community, Lifecycle, Solidarity, ImperialRent, DispossessionEvents, Decomposition, ControlRatio, Metabolism. **Action Phase** = `OODASystem` only. **Consequences** = Survival, Struggle, Consciousness, Contradiction, ContradictionField, FieldDerivative, EdgeTransition. Survival/Struggle/Consciousness are classified as Consequences because they respond to material conditions and to organization actions resolved in OODA — they are not material data orgs deliberate against.
- Q: Should the US4 monotonicity contract require strict fail-loud behavior or accept dual-acceptance (raise OR silent no-op)? → A: **Monotonic-idempotent (revised 2026-05-07 post-verification)** — the persistence layer MUST treat a same-payload re-persist as an idempotent success (preserving existing UPSERT-retry callers), and MUST raise `MonotonicityViolationError` when a re-persist supplies a *different* payload for an already-persisted tick. This refines the original "strict raise" answer in light of the existing `RuntimePersistence` protocol's documented UPSERT semantics — fail-loud applies to *historical rewrite*, not to retries with identical state. Same constitutional alignment (III.7 + III.2): retries don't rewrite history; differing-payload writes do.
- Q: What is the canonical scope of "tick execution" that the US3 no-DB-I/O patch wraps? → A: The `SimulationEngine.run_tick(graph, services, context)` call boundary. Patch enters before `run_tick` is invoked, exits after it returns. Hydration and persistence happen outside this boundary (caller responsibility) and are explicitly *out of scope* for the patch. This matches the user's prompt language ("no calls occur during `engine.step()`") and aligns with the existing API surface — `run_tick` IS the canonical "tick execution" boundary in the codebase.

### Session 2026-05-07 (post-verification design decisions)

- Q (F6): `_DEFAULT_SYSTEMS` in `simulation_engine.py:184–208` currently orders OODA *last* (position 21), after every Consequence System — contradicting the spec's `Material Base → OODA → Consequences` partition. Resolution: **reorder `_DEFAULT_SYSTEMS` so OODA executes at position 14, immediately after `MetabolismSystem` (position 13) and before `SurvivalSystem` (now position 15)**. This makes the engine's actual execution order match ADR032's documented "Material Base → Action Phase → Consequences" partition AND matches the user's spec prompt ("Layer 0 economic metabolism runs before Action Phase, always"). The reorder is part of Phase 2 production work (T004) and may surface ordering assumptions in existing tests; those are remediated as discovered.
- Q (F7): The current `RuntimePersistence.persist_tick` Protocol docstring documents "Idempotent via UPSERT semantics" — i.e., overwrites silently succeed today. Resolution: **adopt monotonic-idempotent semantics (Q2-revised above)** rather than full strict-raise. Same payload → idempotent success (preserves existing observer/recorder retry callers found in `persistence_observer.py:146` + `session_recorder.py:168`). Different payload → `MonotonicityViolationError`. The spec/data-model/tasks reference the actual API names: `persist_tick` (write) and `hydrate_graph` (read), not the placeholders `write_state` / `read_tick` used in earlier drafts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Material base runs before Action Phase (Priority: P1)

A maintainer reorders the `_DEFAULT_SYSTEMS` list in
`src/babylon/engine/simulation_engine.py` — perhaps moving `OODASystem`
earlier "for performance reasons", or splitting a System into two halves
without updating the canonical ordering, or adding a new "deliberation
helper" System that references `wealth` / `s_bio` / `s_class` fields
*before* `ProductionSystem` and `ImperialRentSystem` have written this
tick's values. Today the ordering is documented in ADR032 and enforced
only by *example* tests on individual Systems. There is no
*pipeline-level* call-order spy that asserts every Material Base System
called `step()` before `OODASystem` did, regardless of how
`_DEFAULT_SYSTEMS` is mutated or how the engine is constructed.

**Why this priority**: P1. ADR032 ("Materialist Causality") is
load-bearing for the entire simulation: it is the operational expression
of Constitution I.18 (Material-Ideological Primacy). When organizations
deliberate against stale economic data, every downstream consciousness
update, every survival probability, every bifurcation outcome is
silently wrong — and *the numbers still look plausible*, because the
arithmetic is correct on the stale base. The bug is invisible to
end-state assertions; it can only be caught by a call-order spy. Per the
user's prompt: "I didn't see this."

**Note on the current codebase ordering**: Per the 2026-05-07 F6
clarification, `_DEFAULT_SYSTEMS` currently orders `OODASystem` *last*
(position 21), after every Consequence System. This contradicts the
spec's `Material Base → OODA → Consequences` partition. The Phase 2
production work includes reordering `_DEFAULT_SYSTEMS` so OODA executes
at position 14 (immediately after `MetabolismSystem`, immediately before
`SurvivalSystem`). After that reorder, the US1 invariant becomes a
positive guard against future re-inversion.

**Independent Test**: Wrap every System in `_DEFAULT_SYSTEMS` with a
call-order spy that records `(system_class_name, call_index)` each time
the engine invokes `system.step(graph, services, context)`. Run a full
`SimulationEngine.run_tick`. Assert that for every Material Base System
M and every Action Phase System A, `call_index(M) < call_index(A)`.
Independent of US2 / US3 / US4. The Material Base set MUST be sourced
from a canonical declaration (the same set ADR032 documents) so that
adding a new Material Base System extends the invariant automatically;
no hand-maintained duplicate list in the test.

**Acceptance Scenarios**:

1. **Given** a `SimulationEngine` constructed with the default System
   list, **When** `run_tick` runs once with a random `WorldState`,
   **Then** every Material Base System (per the canonical
   `MATERIAL_BASE_SYSTEMS` set: Vitality, Territory, Production,
   TickDynamics, ReserveArmy, Community, Lifecycle, Solidarity,
   ImperialRent, DispossessionEvents, Decomposition, ControlRatio,
   Metabolism) recorded its call before `OODASystem` recorded its call.

2. **Given** a `SimulationEngine` constructed with a deliberately
   permuted System list (Action Phase moved before some Material Base
   Systems), **When** `run_tick` runs, **Then** the call-order spy
   detects the inversion and the test fails with a Hypothesis-shrunk
   minimal example naming the offending System pair `(material_base,
   action_phase)` and the inverted ordering.

3. **Given** any `SimulationEngine` whose System list contains
   `OODASystem`, **When** `run_tick` runs, **Then** the call-order spy
   asserts that `OODASystem.step` was called *exactly once* per tick
   (no double-invocation through misconfiguration) and that its call
   index is strictly greater than every Material Base System's call
   index in the same tick.

---

### User Story 2 — Consequence propagation runs after all OODA actions (Priority: P1)

A maintainer adds a new "consequence" System (or splits an existing
consequence System into per-organization helpers) and accidentally wires
it into the engine such that some organizations' consequences are
applied *before* other organizations have completed their OODA
deliberation. Once that interleaving exists, *initiative order* (which
organization's `step()` runs first inside `OODASystem`) silently
determines downstream outcomes for every System, not just for the
ordering of the actions themselves. The simulation becomes
non-replayable in a subtle way: two engines with identical starting
states but different organization-iteration orders produce different
results, even though the OODA contract permits any iteration order over
the organization set.

**Why this priority**: P1. This is a hidden coupling between
`OODASystem` and the consequence-aggregation Systems
(`ContradictionSystem`, `ContradictionFieldSystem`,
`FieldDerivativeSystem`, `EdgeTransitionSystem`, `StruggleSystem`). The
contract is: all organizations deliberate, then consequences are
applied to the post-OODA graph state — no interleaving permitted. A
property test makes this contract machine-checkable. Catastrophic if
violated, because every replay assertion downstream relies on
order-independence over the organization set.

**Note on current codebase ordering**: As described in US1, the F6
clarification requires reordering `_DEFAULT_SYSTEMS` so OODA precedes
the Consequence Systems. US2's invariant is therefore meaningful
*after* the reorder; before the reorder, every Consequence System
would trivially fail the predicate because they all run before OODA.
The reorder is a Phase 2 production deliverable; this US2 invariant is
the regression guard once the order is correct.

**Independent Test**: Wrap `OODASystem.step` and every consequence
System's `step` with the same call-order spy from US1. Within
`OODASystem.step`, additionally instrument the per-organization action
loop so the spy records `(organization_id, action_resolution_index)`.
Assert that for every consequence System C, `call_index(C)` is strictly
greater than `max(action_resolution_index)` over all organizations
processed in the same tick. In other words: every per-organization
action MUST resolve before any consequence System touches the graph.
Independent of US1 / US3 / US4.

**Acceptance Scenarios**:

1. **Given** a `WorldState` containing at least 2 organizations,
   **When** `run_tick` runs, **Then** for every Consequence System
   (per the canonical `CONSEQUENCE_SYSTEMS` set: `SurvivalSystem`,
   `StruggleSystem`, `ConsciousnessSystem`, `ContradictionSystem`,
   `ContradictionFieldSystem`, `FieldDerivativeSystem`,
   `EdgeTransitionSystem`), the per-organization action-resolution
   events recorded by the spy all precede the Consequence System's
   call event.

2. **Given** a deliberately monkey-patched engine whose consequence
   System's `step` is invoked from inside the per-organization action
   loop (interleaving), **When** `run_tick` runs, **Then** the spy
   detects the interleaving and the test fails with a minimal example
   naming the offending `(consequence_system, organization_id)` pair.

3. **Given** any `WorldState`, **When** the same tick runs twice with
   the same starting state but with the per-organization iteration
   order shuffled inside `OODASystem`, **Then** the post-tick graph
   states are equal under the same `model_dump` exclude rules used in
   Spec 055 US4 — i.e., consequence propagation is order-independent
   over the organization set.

---

### User Story 3 — No DB I/O during tick execution (Priority: P2)

A maintainer adds a System (or modifies an existing one) and discovers
they need "just one quick lookup" from the reference SQLite database
or the Postgres runtime — a county FIPS lookup, a BEA series fetch,
a corporate org-chart join. They wire the call directly into
`step()`. The change passes all existing tests because the database
*is* available in the test environment. But the constitutional
contract (II.10 World Runtime; ADR037) is that `engine.run_tick()`
operates over an *in-memory* graph already hydrated by the
pre-tick hydration phase, and persists *after* the tick via the
post-tick persistence phase. Any DB I/O during the tick itself
violates determinism, breaks replay, and makes golden-master testing
impossible.

**Why this priority**: P2. Constitution II.10 and ADR037 promise this
discipline; the discipline is not currently asserted as a property.
The class-level `frozen=True` setting (covered by Spec 055 US3)
catches in-place mutation; this US3 catches the analogous in-place
*I/O*. The residual cases are exactly the ones property testing is
best at finding: a System that opportunistically opens a connection,
a third-party library that lazily evaluates a query handle, a cache
miss that triggers a DB fetch under load. The bug surface is narrower
than US1 / US2 (a System has to actively perform I/O, which is a
larger code change than reordering a list), but the consequences are
just as severe: replay diverges, golden masters become stale, and the
"engine is pure" contract becomes a lie.

**Independent Test**: Patch every database-connection entry point
exposed via `ServiceContainer` (the SQLite reference DB connection,
the Postgres runtime connection, the pgvector store, any
`RuntimePersistence` implementation) so that any attempted access
inside the patched scope raises `DBIONotPermittedError`. Run a full
`SimulationEngine.run_tick` against a random `WorldState`. Assert
that the tick completes without raising. Independent of US1 / US2 / US4.
The patching MUST cover every documented DB I/O surface — no
hand-maintained "known surfaces" list; the patch reads the canonical
list of DB-bearing services from `ServiceContainer` itself so a future
addition is caught automatically.

**Acceptance Scenarios**:

1. **Given** a `SimulationEngine` and a `ServiceContainer` whose
   database-access methods are patched to raise
   `DBIONotPermittedError`, **When** `run_tick` runs against a
   random `WorldState`, **Then** the tick completes successfully and
   no `DBIONotPermittedError` was raised inside the tick scope.

2. **Given** a deliberately monkey-patched System whose `step`
   performs a DB query, **When** the same patched-services `run_tick`
   runs, **Then** `DBIONotPermittedError` is raised and the test
   fails with a diagnostic message naming the offending System and
   the DB surface it touched.

3. **Given** the pre-tick hydration phase and post-tick persistence
   phase (both of which ARE permitted to touch the database), **When**
   the patch context wraps only the `SimulationEngine.run_tick`
   call — entered immediately before `run_tick` is invoked and
   exited immediately after it returns — **Then** the tick runs
   cleanly, hydration before the patch and persistence after the
   patch are unaffected, and the patch scope precisely matches the
   `run_tick` API surface (the canonical "tick execution" boundary).

---

### User Story 4 — State persistence is monotone in tick (Priority: P3)

The persistence layer (introduced by Spec 037 Postgres Runtime DB and
its `RuntimePersistence` protocol) is responsible for writing each
post-tick state to durable storage. The constitutional commitment is
that once tick N has been persisted, the persisted record for tick N
is **immutable** — editing tick N would rewrite history and silently
invalidate every downstream tick's audit trail. Today the persistence
layer does not assert this property at the contract level. A
maintainer who introduces an "upsert" path "for replay convenience" —
or who bypasses the protocol method and writes directly via SQL —
silently breaks the monotonicity guarantee.

**Why this priority**: P3. This invariant only applies to the
persistence boundary, which is exercised once per tick (vs. US1 / US2
which are checked every System call, and US3 which is checked
across the entire tick scope). The bug surface is narrowest. But the
consequence is severe: the entire premise of replay and audit relies
on once-written persistence being once-written.

**Independent Test**: Run a synthetic 5-tick simulation against a
real or in-memory `RuntimePersistence` instance using the actual API
methods (`persist_tick(tick, graph, events, *, session_id)` and
`hydrate_graph(tick, *, session_id)`). After tick N is persisted,
exercise both halves of the monotonic-idempotent contract: (a) a
*same-payload* re-persist succeeds idempotently (preserves existing
UPSERT-retry callers like `persistence_observer.py:146`), and (b) a
*different-payload* re-persist raises `MonotonicityViolationError`.
Re-read tick N afterward and assert the originally-persisted payload
is returned unchanged. Independent of US1 / US2 / US3. Per the
2026-05-07 clarification: monotonic-idempotent contract — retries
with identical state succeed; rewrites with differing state fail loudly.

**Acceptance Scenarios**:

1. **Given** a `RuntimePersistence` instance in which tick N has
   been persisted with `payload_N`, **When** `persist_tick(tick=N,
   graph=different_payload, ...)` is called, **Then** the call raises
   `MonotonicityViolationError`, AND a subsequent
   `hydrate_graph(tick=N)` returns the originally-persisted payload
   unchanged.

2. **Given** a `RuntimePersistence` instance in which tick N has
   been persisted with `payload_N`, **When** `persist_tick(tick=N,
   graph=payload_N, ...)` is called *again* with the **same** payload
   (idempotent retry), **Then** the call returns successfully without
   raising, AND `hydrate_graph(tick=N)` continues to return
   `payload_N` (state preserved). This preserves the existing
   `persistence_observer` and `session_recorder` retry semantics.

3. **Given** a 5-tick simulation that runs cleanly (each tick
   persisted once, in order), **When** the persistence layer is
   queried after the run, **Then** `hydrate_graph(tick=N)` returns
   the same payload that was originally written for every
   `N in [0, 5)`, regardless of read order or read count.

4. **Given** a `RuntimePersistence` instance where ticks 0..N have
   been written, **When** the engine attempts `persist_tick(tick=K,
   graph=any_payload, ...)` for some `K < N` already persisted with a
   **different** prior payload (a "go back in time" rewrite), **Then**
   the persistence layer raises `MonotonicityViolationError`, the
   existing records for all ticks 0..N remain intact, and
   `hydrate_graph` still returns the original payloads for all
   already-persisted ticks.

---

### Edge Cases

- **Empty action phases**: A `WorldState` with zero organizations
  trivially satisfies US2 (no per-organization actions to interleave
  with). The test must record a "0 organizations, 0 interleavings" trace
  rather than skipping silently.
- **Single organization**: With exactly one organization, "all
  organizations have acted" reduces to "the one organization has
  acted." US2 still asserts the consequence-System ordering; the
  per-organization spy records exactly one event.
- **Systems that legitimately need read-only DB access**: If any
  System legitimately reads from the SQLite reference database
  during a tick (for a static lookup that cannot be hydrated up
  front), it MUST flag itself with the
  `bypasses_causal_invariant: ClassVar[dict[str, str]]` opt-out
  marker shape established by Specs 054 / 055, naming the predicate
  it bypasses and the justification. Empty justifications fail CI.
- **Patched-service scope boundary**: The US3 patch must cover
  exactly the `SimulationEngine.run_tick(graph, services, context)`
  call — entered immediately before `run_tick` is invoked, exited
  immediately after it returns (per the 2026-05-07 clarification).
  Patching too early breaks hydration; patching too late breaks
  persistence. The harness exposes the boundary as a context manager
  (`no_db_io_during_tick(engine)`) that internally invokes
  `run_tick` under the patched scope so the boundary cannot drift.
- **Persistence backends — monotonic-idempotent semantics** (per the
  2026-05-07 F7 clarification): Both `RuntimeDatabase` and
  `PostgresRuntime` implement the same contract: same-payload
  re-`persist_tick` succeeds idempotently (returns successfully
  without raising), different-payload re-`persist_tick` raises
  `MonotonicityViolationError`. The implementation strategy differs
  by backend (in-memory: dict comparison; Postgres: SELECT-then-INSERT
  with payload comparison on `UniqueViolation`), but the contract is
  identical. No test-side decorators are permitted — production
  discipline must hold without test scaffolding.
- **Existing `persist_tick` retry callers** (per the 2026-05-07
  audit): `persistence_observer.py:146` and `session_recorder.py:168`
  are the two production callers; both call `persist_tick` exactly
  once per tick per session. Under the new monotonic-idempotent
  contract, single-call patterns continue to work; idempotent retries
  (if the observer is invoked twice for the same tick — e.g., during
  network-retry scenarios in PostgresRuntime mode) succeed silently.
  Test callers in `tests/integration/test_postgres_integration.py`
  and `tests/unit/persistence/test_postgres_runtime.py` use distinct
  `(tick, session_id)` pairs per call; their behavior is unchanged.
- **Partial-tick failure**: If a System raises mid-tick, the
  persistence phase MUST NOT run for that tick. The US3 / US4 tests
  must not interpret a System exception as a violation of either
  invariant; they assert no DB I/O *attempts* occurred (US3) and that
  no partial persisted record exists (US4 monotonicity is vacuously
  true if no record was ever written).
- **Engine constructed with custom System list**: Tests run against
  `_DEFAULT_SYSTEMS`, but the harness MUST also exercise at least one
  alternate System list (e.g., the same systems in shuffled order)
  to verify the call-order spy correctly detects violations and not
  just legitimate orderings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The harness MUST provide one Hypothesis test per
  causal/temporal invariant (US1, US2, US3, US4), each individually
  parametrized so a single failure isolates to a single
  (invariant, source) pair.
- **FR-002**: The Material Base, Action Phase, and Consequence System
  sets MUST be sourced from three single canonical declarations that
  live next to ADR032's documented ordering — module-level
  `MATERIAL_BASE_SYSTEMS: Final[frozenset[type[System]]]`,
  `ACTION_PHASE_SYSTEMS: Final[frozenset[type[System]]]`, and
  `CONSEQUENCE_SYSTEMS: Final[frozenset[type[System]]]` constants in
  `src/babylon/engine/simulation_engine.py`, or equivalent read-once
  imports. The three sets MUST partition `_DEFAULT_SYSTEMS` (no
  System belongs to two sets; every System belongs to exactly one).
  The Material Base set is `{VitalitySystem, TerritorySystem,
  ProductionSystem, TickDynamicsSystem, ReserveArmySystem,
  CommunitySystem, LifecycleSystem, SolidaritySystem,
  ImperialRentSystem, DispossessionEventSystem, DecompositionSystem,
  ControlRatioSystem, MetabolismSystem}`. The Action Phase set is
  `{OODASystem}`. The Consequence set is `{SurvivalSystem,
  StruggleSystem, ConsciousnessSystem, ContradictionSystem,
  ContradictionFieldSystem, FieldDerivativeSystem,
  EdgeTransitionSystem}`. **In addition** (per the 2026-05-07 F6
  clarification), `_DEFAULT_SYSTEMS` MUST be reordered so
  `OODASystem` executes at position 14 — immediately after
  `MetabolismSystem` (position 13) and before `SurvivalSystem` (now
  position 15). The current codebase orders OODA last (position 21),
  which contradicts the partition's *temporal ordering*; the
  reorder is a Phase 2 production deliverable. No hand-maintained
  duplicate list in the test module is permitted; adding a new
  System MUST require classification into exactly one of the three
  sets in the production source AND placement at a list index
  consistent with its layer, and the test invariants extend
  automatically.
- **FR-003**: The US1 call-order spy MUST wrap every System in
  `_DEFAULT_SYSTEMS` (and any alternate System list passed to the
  engine constructor) and record `(system_class_name, call_index,
  monotonic_timestamp_ns)` each time `step()` is invoked. The spy
  MUST be transparent to the System (forward all args/kwargs and the
  return value unchanged) and MUST NOT introduce reordering or
  filtering of its own.
- **FR-004**: The US2 per-organization action spy MUST record
  `(organization_id, action_resolution_index, monotonic_timestamp_ns)`
  for every action resolved inside `OODASystem.step`. The recording
  hook MUST live in the harness, not in `OODASystem` production code
  — instrumentation is added per-test via dependency injection or
  monkey-patch, never via permanent production-code wiring.
- **FR-005**: The US3 DB-I/O ban MUST patch every database-access
  surface exposed by `ServiceContainer` and `RuntimePersistence`
  implementations. The list of surfaces MUST be derived from
  introspection of `ServiceContainer` at test time (every attribute
  whose name matches `*database*`, `*persistence*`, `*runtime*`, or
  whose type is a known persistence protocol) so that adding a new
  DB-bearing service is caught automatically. No hand-maintained
  surface list is permitted.
- **FR-006**: The US3 patch context MUST precisely cover the
  `SimulationEngine.run_tick(graph, services, context)` call
  boundary — patch enters immediately before `run_tick` is invoked
  and exits immediately after `run_tick` returns. Hydration and
  persistence happen outside this boundary (caller responsibility)
  and are explicitly *out of scope* for the patch. The harness MUST
  expose this window as a context manager
  (`with no_db_io_during_tick(engine):`) that internally invokes
  `engine.run_tick(...)` under the patched scope, so manual
  placement in tests is unnecessary and the boundary cannot drift.
- **FR-007**: The US4 monotonic-idempotent test MUST run against at
  least two `RuntimePersistence` implementations: the in-memory
  `RuntimeDatabase` (fast, default) AND the `PostgresRuntime`
  implementation. Test gating is per FR-009 (single source of truth).
  The monotonic-idempotent contract MUST hold against both:
  same-payload re-`persist_tick` succeeds idempotently;
  different-payload re-`persist_tick` raises
  `MonotonicityViolationError`. Implementation strategy may differ
  per backend (in-memory: dict comparison; Postgres: SELECT-then-INSERT
  with payload comparison on `UniqueViolation`); the contract is
  identical. The protocol method names are `persist_tick` (write) and
  `hydrate_graph` (read) — earlier `write_state` / `read_tick`
  references in pre-2026-05-07 drafts were placeholders.
- **FR-008**: All four tests MUST use the same Hypothesis profile
  registration pattern as Specs 053 / 054 / 055 (default / dev / ci /
  nightly registered in `tests/property/conftest.py`). The default
  profile MUST run with `max_examples >= 100` and `derandomize=True`.
- **FR-009**: All four tests MUST be runnable via
  `mise run test:unit` (default profile) and pass within the existing
  fast-CI budget. The slow profile (`HYPOTHESIS_PROFILE=slow`) MUST
  exercise at least 5× more examples per test. The Postgres-backed
  US4 test branch is gated behind a separate `mise run test:integration`
  invocation, not the default fast gate. This is the single
  authoritative gate declaration; FR-007 defers to it.
- **FR-010**: Failures MUST surface a Hypothesis-shrunk minimal
  example, with a diagnostic message that names (a) the invariant
  violated, (b) the System or persistence operation that produced
  the violation, and (c) the offending IDs / timestamps / call
  indices. The diagnostic format is verified by a sanity assertion in
  Phase 7 polish (one synthetic failing example per invariant; assert
  the resulting message contains all three diagnostic elements as
  substring matches). This converts FR-010 from an implicit
  per-task obligation into a single machine-checkable verification.
- **FR-011**: Systems or persistence backends that **legitimately**
  bypass a causal invariant (e.g., a System that reads a static
  reference table mid-tick because it cannot be hydrated up front)
  MUST be flagged with the
  `bypasses_causal_invariant: ClassVar[dict[str, str]]` opt-out
  marker shape — predicate name → justification string. The harness
  MUST consume this marker, skip the named predicate for the marked
  System, AND machine-assert at collection time that every value is
  non-empty. No silent skips are permitted.
- **FR-012**: The US1 / US2 spies MUST NOT mutate the simulation
  state in any observable way. Their only side-effect is appending to
  an in-test recording list. The post-tick `WorldState` produced by a
  spied tick MUST `model_dump`-compare equal to the post-tick
  `WorldState` produced by an unspied tick from the same starting
  state (under the Spec 055 US4 exclude rules). This guarantees the
  spy itself does not introduce the bug it is trying to catch.

### Key Entities

- **`Invariant` protocol**: Existing in
  `src/babylon/engine/invariants.py`. This feature does NOT add new
  `(pre, post) -> InvariantResult` shaped invariants — the four
  invariants here operate over *call traces* and *I/O scopes*, not
  over field values, so they live in the test harness as procedural
  assertions rather than as `Invariant`-protocol objects. The
  harness style still mirrors `BoundInvariantHarness` / Spec 054 in
  its `assert_*` helper shape.
- **`CausalInvariantHarness`**: New Hypothesis-driven runner that
  takes a `SimulationEngine` and a list of trace assertions and runs
  them against random `WorldState` instances. Mirrors the
  `BoundInvariantHarness` (Spec 054) and `TopologyInvariantHarness`
  (Spec 055) patterns.
- **`SystemCallSpy`**: Test-only wrapper that wraps each System's
  `step` method, records `(system_class_name, call_index,
  monotonic_timestamp_ns)`, then forwards the call. Used by US1 and US2.
- **`OrganizationActionSpy`**: Test-only instrumentation hook
  injected into `OODASystem` (via test-time dependency injection)
  that records `(organization_id, action_resolution_index,
  monotonic_timestamp_ns)` for each per-organization action
  resolution. Used by US2.
- **`no_db_io_during_tick(engine)`**: Context manager that patches
  every DB-bearing service exposed by `ServiceContainer` and any
  `RuntimePersistence` implementation, then invokes
  `engine.run_tick(...)` within the patched scope. Patch entry is
  immediately before `run_tick`; patch exit is immediately after it
  returns. Inside the patched scope, any attempted DB access raises
  `DBIONotPermittedError`. Used by US3.
- **`MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` / `CONSEQUENCE_SYSTEMS`**:
  Three single canonical declarations in
  `src/babylon/engine/simulation_engine.py` (or equivalent module)
  partitioning `_DEFAULT_SYSTEMS` per ADR032 and the 2026-05-07
  clarification. Single source of truth for US1 (Material Base
  before OODA) and US2 (Consequences after all OODA actions).
- **`bypasses_causal_invariant` ClassVar**: Per-System and
  per-persistence-backend opt-out marker shaped as
  `ClassVar[dict[str, str]]` — predicate name → justification
  string. Mirrors Specs 054 / 055's marker shapes exactly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer who reorders `_DEFAULT_SYSTEMS` such that
  `OODASystem` runs before any Material Base System (or who adds a
  new System that violates the Material Base ordering) has the
  regression caught by `mise run test:unit` in the same run that
  ships the change, with a Hypothesis-shrunk failing trace pointing
  at the offending `(material_base_system, action_phase_system)`
  inversion.
- **SC-002**: A regression that interleaves consequence-System
  invocation with per-organization OODA action resolution is caught
  by the US2 spy, with a failing trace naming the
  `(consequence_system, organization_id)` pair where the
  interleaving was first observed.
- **SC-003**: An accidental DB I/O call inside a System's `step()`
  during a tick is caught by the US3 ban, with a failure naming the
  offending System, the DB surface it touched
  (`services.database.execute`, `runtime.persist_tick`, etc.), and
  the call site.
- **SC-004**: A regression that introduces a code path overwriting
  an already-persisted tick *with a different payload* (via raw SQL,
  bypass of the persistence protocol, or any other route) is caught
  by the US4 monotonic-idempotent test by failure to raise the
  required `MonotonicityViolationError`, with a diagnostic showing
  the original payload, the attempted overwrite payload, and the
  tick number that was overwritten. Same-payload retries (the
  legitimate UPSERT-retry pattern used by `persistence_observer.py`
  and `session_recorder.py`) succeed idempotently — the test
  asserts both halves of the contract: differing-payload raises,
  identical-payload succeeds.
- **SC-005**: The four invariant test files together complete in
  under 60 seconds on the default profile (`max_examples=100`,
  `derandomize=True`) and under 5 minutes on the slow profile
  (`max_examples=500`), measured on the same hardware as Specs 053 /
  054 / 055 baselines. The combined `tests/property/` suite (Specs
  053 + 054 + 055 + 056) MUST stay under 4 minutes on default,
  matching the current ~88 s baseline plus headroom for the new
  spy-based tests.
- **SC-006**: `bypasses_causal_invariant` markers, if any are
  introduced during implementation, carry a non-empty justification
  string in their `dict[str, str]` value. The harness
  machine-enforces this at collection time so empty or missing
  justifications fail CI rather than slipping through review.

## Assumptions

- Hypothesis ^6.149.0 is already in
  `[tool.poetry.group.dev.dependencies]` (added by Spec 053). No new
  dependency is required.
- The 21 Systems listed in `src/babylon/engine/systems/` (excluding
  `__init__.py` and `protocol.py`) are the canonical System set,
  matching Specs 054 / 055's count. If a new System is added during
  implementation, the harness picks it up via directory introspection
  rather than a hand-maintained list (same pattern as Specs 054 /
  055).
- `_DEFAULT_SYSTEMS` in `src/babylon/engine/simulation_engine.py`
  represents the canonical ordering documented by ADR032. The
  Material Base subset MUST be declared adjacent to this list (same
  module) so the two cannot drift out of sync.
- `OODASystem` (Feature 032) is the canonical "Action Phase" — it is
  where organizations deliberate. If a future feature splits the
  Action Phase into multiple Systems, the
  `MATERIAL_BASE_SYSTEMS` / Action Phase boundary becomes a documented
  constant rather than a single class reference; the test harness
  consumes the constant.
- `ServiceContainer` (in `src/babylon/engine/services.py`) exposes
  every DB-bearing service as a named attribute. New persistence
  backends added in future features MUST be exposed via the same
  pattern so the US3 patch picks them up via introspection.
- The `RuntimePersistence` protocol (Spec 037) is the canonical
  persistence interface. Both `RuntimeDatabase` (in-memory, SQLite)
  and `PostgresRuntime` (durable) implement it. The US4
  monotonicity contract is asserted against the protocol, not
  against a single implementation.
- The Spec 053 conservation harness, Spec 054 bound harness, Spec
  055 topology harness, profile registration pattern, and
  `_iter_worldstate_collections` helper are the model for this
  work. Implementation reuses the same patterns rather than
  reinventing.
- Constitution II.10 (World Runtime) and ADR037 (Postgres Runtime
  DB) are the binding sources for the no-DB-I/O-during-tick
  discipline. The US3 test encodes those documents' commitment as
  a property; if the documents change, the test must change with
  them, not silently drift.
- All four invariants are tested via Hypothesis property strategies;
  the default profile runs them as part of `mise run test:unit`. The
  Postgres-backed US4 branch is gated behind `mise run test:integration`
  so default fast-CI does not require a live Postgres.
