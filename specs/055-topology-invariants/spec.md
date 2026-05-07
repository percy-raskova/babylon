# Feature Specification: Topological Invariants — Property-Based Tests

**Feature Branch**: `055-topology-invariants`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "I need to create property and invariant tests for Topological invariants — graph structure properties. Edge mode state machine legality. Edges only transition between modes via legal paths. EXTRACTIVE → SOLIDARISTIC requires TRANSACTIONAL as intermediate. The invariant is that for any sequence of evidence events, every transition in the resulting trajectory is a legal edge in the state machine, and the final mode is always one of the five enum values. Probably tested per-transition; not tested as a sequence invariant. Hyperedges-not-pairwise. The graph should never contain edges that look like community-to-member fan-outs. Anti-Pattern VIII.9. The invariant is structural: at any tick, no edges of EdgeType MEMBERSHIP between a community node and an entity node should exist. Membership lives in XGI. Should be a graph linter; I didn't see this asserted anywhere. Frozen Pydantic discipline. Any mutation produces a new instance via model_copy(). The engine never mutates a model in place. Testable by patching model_copy to raise and asserting no in-place mutations slip through. Not currently tested as an invariant. WorldState round-trip identity. state == WorldState.from_graph(state.to_graph()) modulo the tick field. Tested in test_graph_roundtrip.py."

## Overview

The simulation engine declares a small number of *topological invariants* —
structural constraints that say, in plain English, "the shape of the graph
must remain in a particular discipline regardless of which legal sequence
of operations produced it." These are not numerical bounds (Spec 054) and
not flow conservation properties (Spec 053). They are statements about the
*structure* of the graph itself: which edges may exist between which nodes,
which sequences of mode transitions are legal, and which mutations may
exist as side-effects.

Each invariant in scope encodes a constitutional commitment:

- **Edge-mode transitions** (Constitution I.15) — the state machine of
  qualitative contradiction modes (EXTRACTIVE, TRANSACTIONAL,
  SOLIDARISTIC, ANTAGONISTIC, CO_OPTIVE) is a directed graph of 17
  permissible arcs. Edges may only move along those arcs.
- **Pairwise vs. hyperedge separation** (Constitution II.7, Anti-Pattern
  VIII.9) — community membership lives in the XGI hyperedge layer; the
  morphism graph MUST NOT carry community-to-member fan-out edges.
- **Frozen Pydantic discipline** (Constitution III.7 Determinism) —
  every Pydantic state model is `frozen=True`; the only legal mutation
  pathway is `model_copy(update=…)`, producing a new Python object.
- **Round-trip identity** — `WorldState.from_graph(state.to_graph())`
  must reproduce the input modulo the explicit `tick` parameter. An
  example test exists; this feature converts it to a property test.

Each invariant is independent: each can be implemented and shipped
separately, and each by itself meaningfully reduces the "structural
silent-violation" surface area. This feature follows the harness style
established by Spec 053 (conservation invariants) and Spec 054 (bound
invariants).

## Clarifications

### Session 2026-05-06

- Q: Canonical community-node detector for US2's hyperedges-not-pairwise linter → A: Detect via the existing `_node_type == "community"` graph-node attribute — matches the codebase's established `NodeFilter` / `_iter_worldstate_collections` pattern, single attribute lookup, no XGI coupling, single edit point if the convention changes.
- Q: Should US3 include both per-tick identity check AND class-level static `frozen=True` introspection? → A: Both — per-tick runtime identity check catches dunder-bypass mutations during a tick; collection-time static introspection over every state-bearing model class catches an accidentally-removed `frozen=True` setting. The two checks catch disjoint bug surfaces; the static one is cheap and impossible to false-positive.
- Q: How should US1 generate the evidence events that drive `EdgeTransitionSystem.step` between trajectory steps? → A: Hybrid — a *synthesized* Hypothesis sweep that writes `contradiction_fields[…]` and `field_derivatives[…]` directly on graph nodes between System steps (broad falsification of the state machine in isolation across the full predicate space), plus an *observed* end-to-end smoke check that runs at least one full `SimulationEngine.run_tick` trajectory and asserts the same legality property (catches wiring between FieldDerivativeSystem and EdgeTransitionSystem). Mirrors the Spec 054 US4 hybrid pattern exactly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Edge-mode trajectory legality across N evidence events (Priority: P1)

A maintainer changes `EdgeTransitionSystem` (or one of the formulas it
delegates to) and inadvertently introduces a path that lets an edge skip
a required intermediate mode — for example, jumping
`EXTRACTIVE → SOLIDARISTIC` directly without passing through
`TRANSACTIONAL`. Today there are per-transition example tests for the 17
declared arcs in `_TRANSITIONS`, but no end-to-end *trajectory* test:
running an arbitrary sequence of evidence events on a starting edge and
asserting that every consecutive `(prev_mode, next_mode)` pair along the
resulting trajectory belongs to the legal arc set, AND that the final
`edge_mode` value is a legitimate `EdgeMode` enum value (not `None`,
not a stale string, not a malformed enum).

**Why this priority**: P1. The state machine is load-bearing for the
dialectical field topology — the entire bifurcation logic depends on
edges respecting their declared transition graph. A bug that lets one
arc-skip slip through corrupts every downstream consciousness routing
decision and every bifurcation outcome. Per-transition tests cannot
catch trajectory-level violations because the bug surface is "what
sequences are reachable from a given starting state under arbitrary
event histories", which is combinatorially larger than the 17 arcs.

**Independent Test**: Hybrid — two complementary branches.
**(1) Synthesized Hypothesis sweep**: generate a random starting
`EdgeMode`, then a random sequence of `N` (configurable; default 10)
evidence events synthesized as direct writes to `contradiction_fields[…]`
and `field_derivatives[…]` on graph node attributes between
`EdgeTransitionSystem.step` calls. This branch falsifies the state
machine in isolation across the full predicate space.
**(2) Observed end-to-end smoke check**: run at least one full
`SimulationEngine.run_tick` trajectory of length ≥ 5 ticks against a
random `WorldState`, capture the resulting `edge_mode` trajectory for
every edge that carries a mode, and assert the same legality property.
This branch falsifies the wiring between `FieldDerivativeSystem` and
`EdgeTransitionSystem`. In both branches: assert that every consecutive
pair `(m_i, m_{i+1})` belongs to the canonical legal-arc set
`_VALID_TRANSITIONS` from `edge_transition.py` (which today already
includes the special case `(ANTAGONISTIC, ANTAGONISTIC)` for
persistence). Assert that the final `m_N` is a member of `EdgeMode`.
Independent of US2 / US3 / US4.

**Acceptance Scenarios**:

1. **Given** a starting edge with `edge_mode = EdgeMode.EXTRACTIVE` and
   a random sequence of 10 evidence events, **When**
   `EdgeTransitionSystem.step` runs once per event, **Then** the
   trajectory `(m_0, m_1, …, m_10)` satisfies
   `(m_i, m_{i+1}) in _VALID_TRANSITIONS` for every `i in [0, 10)` and
   `m_10 in EdgeMode`.

2. **Given** a starting edge with any `edge_mode` and any sequence of
   evidence events such that no predicate fires on a tick, **When** the
   System runs that tick, **Then** the edge's `edge_mode` is unchanged
   (the trivial-arc `(m, m)` is implicitly legal: no transition occurred).

3. **Given** an `EXTRACTIVE` starting edge, **When** any sequence of
   evidence events is applied that drives the trajectory toward
   `SOLIDARISTIC`, **Then** the trajectory contains at least one
   intermediate node in `{TRANSACTIONAL, ANTAGONISTIC, CO_OPTIVE}`
   before reaching `SOLIDARISTIC` (no direct `EXTRACTIVE → SOLIDARISTIC`
   arc exists in `_VALID_TRANSITIONS`).

---

### User Story 2 — Hyperedges-not-pairwise structural linter (Priority: P1)

A maintainer adds a feature that wires up community membership and,
under one code path, uses `EdgeType.MEMBERSHIP` to express
"this entity is a member of this community" — collapsing what should be
an XGI hyperedge into a combinatorial fan-out of pairwise edges. This
violates Constitution II.7 (Edges vs Hyperedges) and Anti-Pattern
VIII.9 (Community as Pairwise Edge): community memberships MUST live
in the XGI hyperedge layer, not the morphism graph. The
`EdgeType.MEMBERSHIP` enum value is reserved for **organization →
SocialClass** weighted membership (per the enum docstring) — not for
**community → member** fan-outs.

**Why this priority**: P1. This is a constitutional invariant that is
*currently asserted nowhere*. The closest existing safeguard is the
docstring on `EdgeType.MEMBERSHIP` and the `[TRANSITION STATE]` note
on Constitution II.7 stating Anti-Pattern VIII.9 must be preserved
during the v2 reconciliation (Amendment D). A property-based linter is
the right mechanism to land here: it converts the constitutional rule
into a machine-checkable structural assertion that any future PR
violating VIII.9 fails CI deterministically.

**Independent Test**: Generate random `WorldState` instances containing
community-bearing entities and run `SimulationEngine.run_tick`. After
the tick, walk every `EdgeType.MEMBERSHIP` edge in the resulting graph
and assert that **the source is not a community node**, where "community
node" is detected via the canonical helper that returns `True` iff the
graph-node attribute `_node_type == "community"`. Independent of US1 /
US3 / US4.

**Acceptance Scenarios**:

1. **Given** a random `WorldState` produced via the existing
   `worldstate_strategy` augmented with at least one community
   hyperedge, **When** `SimulationEngine.run_tick` runs the full
   21-System pipeline, **Then** no `EdgeType.MEMBERSHIP` edge in the
   post-graph has a source identified as a community node by the
   chosen canonical detector.

2. **Given** the same starting state, **When** the same tick runs,
   **Then** the count of *illegitimate* `EdgeType.MEMBERSHIP` edges
   (those whose source is a community node) in the post-graph is **0**.
   The linter does not track per-System entitlement to add legitimate
   organization-to-SocialClass MEMBERSHIP edges; the falsifiable claim
   is the simpler "no community fan-outs in any post-graph."

3. **Given** a deliberately seeded violation (a test-side
   `EdgeType.MEMBERSHIP` edge added with source = community node),
   **When** the linter runs against the post-graph, **Then** the test
   fails with a Hypothesis-shrunk minimal example naming the offending
   `(source_id, target_id, edge_type)` triple.

---

### User Story 3 — Frozen Pydantic discipline across a tick (Priority: P2)

A maintainer adds a System that — through dunder-bypass
(`entity.__dict__["wealth"] = X`), through a third-party library that
sidesteps Pydantic's `__setattr__` guard, or through subtle aliasing
(holding a reference to a sub-object and mutating it) — modifies a
state-bearing Pydantic model **in place**, without going through
`model_copy(update=…)`. Today every state-bearing model declares
`model_config = ConfigDict(frozen=True)`, which makes the canonical
attribute-write path raise `ValidationError`. But there is no test
that asserts the discipline holds *across a tick* — i.e., that for
every entity that survives from the pre-state into the post-state with
*different* field values, the post-state instance is a *different
Python object* (`id(pre_entity) != id(post_entity)`).

**Why this priority**: P2. The class-level `frozen=True` setting catches
the common attribute-write case at runtime, so the residual bug surface
is narrower than US1 or US2. But the residual cases are exactly the
ones property testing is best at finding: dunder-bypasses, list/dict
aliasing through frozen models, and library code that sidesteps the
guard. The constitutional commitment is **III.7 Determinism**: the
engine is a pure transformation `step(WorldState) → WorldState`, so any
in-place mutation is a determinism violation that breaks replay and
testing.

**Independent Test**: Two complementary checks at distinct layers.
**(1) Runtime per-tick identity check**: generate random `WorldState`
instances and snapshot the `id()` of every entity, territory,
relationship, and other state-bearing model in the pre-state. Run
`SimulationEngine.run_tick`. For every entity that exists in both
pre-state and post-state (matched by ID), assert either (a) field-equal
AND `id(pre) == id(post)` (no mutation occurred), OR (b) field-different
AND `id(pre) != id(post)` (a `model_copy` produced a fresh instance).
Failure case: same `id()` but different fields → in-place mutation.
**(2) Static class-level structural check**: at test collection time,
walk every state-bearing Pydantic model class in `babylon.models.entities`
and `babylon.models.world_state` and assert
`cls.model_config.get("frozen") is True`. The two checks catch disjoint
bug surfaces (dunder-bypass at runtime vs. accidentally-removed
`frozen=True` setting) and are both required. Independent of US1 / US2 / US4.

**Acceptance Scenarios**:

1. **Given** a random `WorldState` and a snapshot of `id()` for every
   state-bearing Pydantic model in it, **When**
   `SimulationEngine.run_tick` runs the full 21-System pipeline,
   **Then** for every (id-matched) entity that survived the tick:
   either (a) field-equal AND same `id()`, or (b) field-different AND
   different `id()`.

2. **Given** the same random `WorldState`, **When** the tick runs,
   **Then** every state-bearing Pydantic model class in
   `babylon.models.entities` (and `babylon.models.world_state`) carries
   `model_config = ConfigDict(frozen=True)` — checked via static
   introspection at test collection time so the structural property is
   enforced independently of any particular tick.

3. **Given** a deliberately seeded violation (a System monkey-patched
   to perform a dunder-bypass write on an entity), **When** the
   per-tick check runs, **Then** the test fails with a diagnostic
   message naming the offending entity ID, the field that changed in
   place, and (where possible) the System whose step produced the
   violation.

---

### User Story 4 — WorldState graph round-trip as a property (Priority: P3)

The existing `tests/unit/models/test_graph_roundtrip.py` carries
example-based assertions that hand-built `WorldState` instances survive
`WorldState.from_graph(state.to_graph())` lossless modulo the explicit
`tick` parameter. Those tests cover a handful of carefully-constructed
states. They do **not** falsify the round-trip across the input space
of valid `WorldState` shapes.

**Why this priority**: P3. The example tests already assert
`model_dump` equality on a comprehensive hand-built fixture, so the
round-trip is well-covered for the common case. The remaining bug
surface is unusual `WorldState` shapes that example tests don't reach
— dense relationship graphs, exotic event-list orderings, large
entity counts, and unusual combinations of optional fields. Property
testing tightens the safety net without invalidating the existing
example tests; both are kept.

**Independent Test**: Generate random `WorldState` instances via the
existing `worldstate_strategy` (Spec 040). Apply
`WorldState.from_graph(state.to_graph())`, then assert
`restored.model_dump(exclude={"tick"}) == state.model_dump(exclude={"tick"})`.
The `tick` field is excluded from the comparison because `from_graph`
takes `tick` as an explicit parameter (`from_graph(graph, tick=...)`)
and the round-trip helper passes `tick=state.tick` so the rest of the
state is preserved exactly. Independent of US1 / US2 / US3.

**Acceptance Scenarios**:

1. **Given** a random `WorldState` produced by `worldstate_strategy()`,
   **When** the round-trip
   `WorldState.from_graph(state.to_graph(), tick=state.tick)` runs,
   **Then**
   `restored.model_dump(exclude={"tick"}) == state.model_dump(exclude={"tick"})`.

2. **Given** a random `WorldState` containing the maximum supported
   number of entities, territories, and relationships allowed by the
   strategy, **When** the round-trip runs, **Then** the
   `model_dump`-equality assertion still holds and the test completes
   within the per-test budget defined in SC-005.

3. **Given** a random `WorldState` containing at least one
   `Relationship` of every legal `EdgeType`, **When** the round-trip
   runs, **Then** every relationship in the post-state preserves its
   `edge_type`, `source_id`, `target_id`, and all numeric fields
   exactly.

---

### Edge Cases

- **Empty trajectories**: A `WorldState` with zero edges trivially
  satisfies US1 (no transitions to check); zero MEMBERSHIP edges
  trivially satisfies US2. Tests must record a "0 edges, 0 violations"
  trace rather than skipping silently.
- **Boundary modes**: An edge that arrives at `EdgeMode.ANTAGONISTIC`
  and stays there across multiple ticks must not be flagged as an
  illegal `(ANTAGONISTIC, ANTAGONISTIC)` self-loop — this transition
  is explicitly added to `_VALID_TRANSITIONS` for persistence.
- **Mode field absence**: An edge whose `edge_mode` attribute is
  `None` or absent (no mode declared) is out of scope for US1; the
  trajectory test must filter such edges, not fail on them.
- **Pre-existing legitimate MEMBERSHIP edges**: Per the
  `EdgeType.MEMBERSHIP` docstring, organization → SocialClass
  weighted membership IS legal. The US2 linter must distinguish
  these from community-fan-out edges via the canonical
  community-node detector chosen in the clarification pass.
- **Object aliasing through frozen models**: A `WorldState.relationships`
  list is mutable at the list level even though `Relationship`
  instances are frozen. The US3 identity check operates per-Relationship
  (matched by `(source_id, target_id, edge_type)` tuple), not on the
  list object itself.
- **Round-trip and excluded computed fields**: `WorldState.from_graph`
  excludes a known set of computed fields (`consumption_needs`, etc.).
  The US4 round-trip property MUST mirror the existing example test's
  use of `exclude=` to avoid spurious failures on legitimately-excluded
  fields. The exclude-set is read from the production code (single
  source of truth), not duplicated in the test.
- **Per-tick violations vs. system-startup violations**: US3 only
  asserts identity discipline *across one tick*, not at engine
  initialization. The pre-tick state is taken as ground truth.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The harness MUST provide one Hypothesis test per
  topological invariant (US1, US2, US3, US4), each individually
  parametrized so a single failure isolates to a single
  (invariant, source) pair.
- **FR-002**: The edge-mode trajectory test (US1) MUST source its
  legal-arc set from the canonical `_VALID_TRANSITIONS` constant in
  `src/babylon/engine/systems/edge_transition.py`. No hand-maintained
  arc list is permitted in the test module; adding a new transition
  to `_TRANSITIONS` MUST automatically extend the legal-arc set the
  test compares against.
- **FR-003**: The US1 trajectory test MUST use a **hybrid** strategy:
  (a) a *synthesized* Hypothesis sweep that constructs sequences of at
  least 10 consecutive evidence events per starting `EdgeMode` value
  by writing directly to `contradiction_fields[…]` and
  `field_derivatives[…]` on graph node attributes between
  `EdgeTransitionSystem.step` calls (5 modes × at least 100 examples per
  mode under the default profile, per FR-007 — trajectories MUST start
  from each of the 5 legal `EdgeMode` enum values at least once per
  Hypothesis run); AND (b) an *observed* end-to-end smoke check that
  runs at least one full `SimulationEngine.run_tick` trajectory of
  length ≥ 5 ticks against a random `WorldState` and asserts the same
  legality property on every `edge_mode`-bearing edge in the resulting
  graph. The synthesized branch falsifies the state machine in
  isolation; the observed branch falsifies the wiring between
  `FieldDerivativeSystem` and `EdgeTransitionSystem`.
- **FR-004**: The US2 hyperedges-not-pairwise linter MUST run after
  every full `SimulationEngine.run_tick` exercised by the test, walking
  every `EdgeType.MEMBERSHIP` edge in the post-graph. The community-node
  detector MUST be a single named function (`is_community_node(graph,
  node_id) -> bool`) in the harness module that returns `True` iff the
  graph-node attribute `_node_type == "community"`. No alternative
  detection rules and no scattered duplicates of this check are
  permitted. The test failure message MUST name the offending
  `(source_id, target_id, edge_type)` triple.
- **FR-005**: The US3 frozen-discipline test MUST snapshot
  `id()` for every state-bearing Pydantic model in the pre-state
  (entities, territories, relationships, organizations, key_figures,
  institutions, state_finances, contradiction_frames, industries —
  the same canonical collection set defined in Spec 054's
  `_iter_worldstate_collections` helper). The same helper is reused
  here; a future addition to `WorldState` extends both Spec 054's bound
  check and Spec 055's identity check via a single edit.
- **FR-006**: The US3 test MUST additionally include a structural
  introspection assertion that runs at test collection time, walking
  every Pydantic model class in `babylon.models.entities` and
  `babylon.models.world_state` and asserting
  `cls.model_config.get("frozen") is True` (or the equivalent
  `ConfigDict` shape used by Pydantic v2). This is a class-level
  invariant separate from the per-tick identity check.
- **FR-007**: All four tests MUST use the same Hypothesis profile
  registration pattern as Spec 053 / Spec 054 (default / dev / ci /
  nightly registered in `tests/property/conftest.py`). The default
  profile MUST run with `max_examples >= 100` and `derandomize=True`.
- **FR-008**: All four tests MUST be runnable via
  `mise run test:unit` (default profile) and pass within the existing
  fast-CI budget. The slow profile (`HYPOTHESIS_PROFILE=slow`) MUST
  exercise at least 5× more examples per test.
- **FR-009**: Failures MUST surface a Hypothesis-shrunk minimal
  example, with a diagnostic message that names (a) the invariant
  violated, (b) the System or formula or graph element that produced
  the violation, and (c) the offending IDs / values / arcs.
- **FR-010**: The US4 round-trip test MUST reuse the existing
  `worldstate_strategy()` from `tests/property/strategies/worldstate.py`
  rather than introducing a parallel generator. The exclude-set for
  the `model_dump` comparison MUST be derived from production code
  (the same exclude rules `WorldState.from_graph` uses for computed
  fields), not hardcoded in the test.
- **FR-011**: Systems or graph elements that **legitimately** produce
  out-of-discipline structures (if any are discovered during
  implementation) MUST be flagged with the same
  `bypasses_topology_invariant: ClassVar[dict[str, str]]` opt-out
  marker shape established by Spec 054. The harness MUST consume this
  marker, skip the named predicate for the marked System / element,
  AND machine-assert at collection time that every value is non-empty.
  No silent skips are permitted.
- **FR-012**: The US1 trajectory test MUST distinguish trivial
  no-transition ticks (`m_i == m_{i+1}` because no predicate fired)
  from explicit `(ANTAGONISTIC, ANTAGONISTIC)` persistence
  transitions. Both are legal under the current state machine; the
  test reports them separately so trajectory-coverage statistics are
  meaningful.

### Key Entities

- **`Invariant` protocol**: Existing in
  `src/babylon/engine/invariants.py`. This feature adds two new
  concrete invariants alongside `NonNegativeWealth`,
  `HeatNonNegativity`, `ProbabilityInRange`, and `SimplexPreserved`:
  `EdgeModeTrajectoryLegal` and `NoCommunityFanOut`. The
  frozen-discipline invariant (US3) is implemented as a harness-level
  check rather than an `Invariant`-protocol object because it operates
  over `id()`, not over field values.
- **`TopologyInvariantHarness`**: New Hypothesis-driven runner that
  takes a System (or System pipeline) and a list of topology invariants
  and runs them against random `WorldState` instances. Mirrors the
  existing `BoundInvariantHarness` pattern from Spec 054.
- **`is_community_node(graph, node_id) -> bool`**: Single named helper
  in the test harness module that returns `True` iff the graph-node
  attribute `_node_type == "community"`. Drives US2's linter and is
  the single source of truth so future changes to the community-node
  convention update exactly one location.
- **`bypasses_topology_invariant` ClassVar**: Per-System and
  per-element opt-out marker shaped as `ClassVar[dict[str, str]]` —
  predicate name → justification string. Mirrors Spec 054's
  `bypasses_bound_invariant` exactly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer who introduces a regression that lets an
  edge skip a required intermediate mode (e.g., a direct
  `EXTRACTIVE → SOLIDARISTIC` arc, or a transition out of an enum
  value) has the regression caught by `mise run test:unit` in the
  same run that ships the change, with a Hypothesis-shrunk minimal
  failing trajectory pointing at the offending arc and the evidence
  events that produced it.
- **SC-002**: A regression that introduces an `EdgeType.MEMBERSHIP`
  edge whose source is a community node is caught by the US2 linter,
  with a failing example naming the offending `(source_id, target_id)`
  pair and the detector that flagged it.
- **SC-003**: An in-place mutation of a state-bearing Pydantic model
  during any tick is caught by the US3 identity check, with a failure
  message naming the entity ID, the changed field, and the System
  whose step produced the violation. The structural class-level
  `frozen=True` assertion runs at collection time and fails CI if any
  state-bearing model class loses its `frozen=True` setting.
- **SC-004**: Every random `WorldState` produced by `worldstate_strategy()`
  satisfies `restored.model_dump(exclude={…computed…}) ==
  state.model_dump(exclude={…computed…})` after the
  `from_graph(to_graph(...))` round-trip. Tests detect any reintroduced
  hydration loss the moment it ships.
- **SC-005**: The four invariant test files together complete in
  under 60 seconds on the default profile (`max_examples=100`,
  `derandomize=True`) and under 5 minutes on the slow profile
  (`max_examples=500`), measured on the same hardware as Spec 053
  and Spec 054 baselines. The combined `tests/property/` suite (Spec
  053 + Spec 054 + Spec 055) MUST stay under 3 minutes on default,
  matching the current ~83 s baseline plus headroom.
- **SC-006**: `bypasses_topology_invariant` markers, if any are
  introduced during implementation, carry a non-empty justification
  string in their `dict[str, str]` value. The harness machine-enforces
  this at collection time so empty or missing justifications fail CI
  rather than slipping through review.

## Assumptions

- Hypothesis ^6.149.0 is already in
  `[tool.poetry.group.dev.dependencies]` (added by Spec 053). No new
  dependency is required.
- The existing `Invariant` protocol in
  `src/babylon/engine/invariants.py` is the canonical interface for
  declaring topology invariants. New invariants implement the same
  protocol where the check fits the `(pre, post) -> InvariantResult`
  shape; US3's identity check operates outside that shape and is a
  harness-level routine.
- The 21 Systems listed in `src/babylon/engine/systems/` (excluding
  `__init__.py` and `protocol.py`) are the canonical System set,
  matching Spec 054's count exactly. If a new System is added during
  implementation, the harness picks it up via directory introspection
  rather than a hand-maintained list (same pattern as Spec 054).
- The `_VALID_TRANSITIONS` constant in
  `src/babylon/engine/systems/edge_transition.py` is the single source
  of truth for legal arcs. The trajectory test imports it directly,
  not a copy.
- `WorldState.from_graph` already excludes a documented set of
  computed fields (`consumption_needs`, etc.) — these are listed in
  the production code's `social_class_computed` and
  `territory_excluded` sets, and the US4 round-trip property reads
  those sets at runtime so a future change to the exclude rules does
  not require a parallel test edit.
- The Spec 053 conservation harness, Spec 054 bound harness, profile
  registration pattern, and `_iter_worldstate_collections` helper
  are the model for this work. Implementation reuses the same
  patterns rather than reinventing.
- Pydantic constrained types and `frozen=True` raise `ValidationError`
  at construction or at mutation. The topology test MUST verify the
  absence of *silent* identity-equal-but-fields-differ escapes (via
  dunder-bypass or library sidesteps), not the canonical
  attribute-write path that already raises.
- Constitution II.7 is currently marked `[TRANSITION STATE]` pending
  Amendment D. The US2 linter encodes the *current* discipline (no
  community → member fan-outs in the morphism graph) so that a future
  reconciliation maintains backward compatibility — the test is a
  ratchet, not a moving target.
- All four invariants are tested via Hypothesis property strategies;
  the existing example tests in `tests/unit/models/test_graph_roundtrip.py`
  remain untouched. The property variant complements rather than
  replaces them.
