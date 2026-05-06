# Feature Specification: Bound Invariants — Property-Based Tests

**Feature Branch**: `054-bound-invariants`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "we need to create tests for Bound invariants — values stay in declared ranges. Probability ∈ [0,1]. P(S|A), P(S|R), credibility, success_probability, edge solidarity_strength. Your Probability constrained type enforces this at construction; the invariant is that no operation produces a probability that escapes the range. Type-enforced. Ternary consciousness simplex: r + l + f = 1 with each component in [0,1]. Already property-tested with simplex_points() strategy in test_simplex_invariants.py. Wealth ≥ 0 and Heat ≥ 0. The NonNegativeWealth and HeatNonNegativity invariants in engine/invariants.py. The constitutional commitment is that no system step produces negative wealth or heat for any entity. Invariant protocol exists; needs to run against all 22 Systems with random WorldStates. Coefficient α-smoothing: between non-crisis ticks, coefficient deltas are bounded by the α rate. Crisis phases are discontinuous resets — the invariant only holds in steady state, but in steady state it must hold. Not tested as an invariant; would catch unintended discontinuities."

## Overview

The simulation engine declares a small number of *bound invariants* —
algebraic constraints that say, in plain English, "this value cannot leave
its declared range, regardless of which legal sequence of operations
produced it." These constraints encode constitutional commitments
(`NonNegativeWealth`, `HeatNonNegativity`), type-system contracts
(`Probability ∈ [0, 1]`), geometric contracts (the ternary simplex
`r + l + f = 1`), and dynamical-system contracts (coefficient continuity
in steady state).

Each of these invariants today is either type-enforced at construction
(silently rescued by validation), example-tested for a handful of hand-picked
cases, or merely stated in the constitution with no executable check. This
feature converts them into property-based tests that **falsify the invariant
across the input space**, in the same harness style established by Spec 053
for conservation invariants.

The four invariants in scope are independent: each can be implemented and
shipped separately, and each by itself meaningfully reduces the "silent
violation" surface area.

## Clarifications

### Session 2026-05-06

- Q: How should the Probability-bound test discover which Pydantic fields to check? → A: Static introspection of `model_fields[name].annotation` matching the `Probability` constrained type — auto-discovery across `src/babylon/models/`, zero hand-maintenance.
- Q: How should US2 (Wealth/Heat) test isolation handle Systems whose `step` cannot run standalone? → A: Per-System with feasibility fallback — synthesize minimal pre-state per System; if preconditions cannot be built in isolation, skip with an explicit reason recorded in the per-System trace.
- Q: How should US4 capture the (prev, raw, post) triples it tests against? → A: Hybrid — synthesized triples for the bulk Hypothesis sweep across every α-smoothed coefficient, plus one observed end-to-end smoke check (one canonical coefficient, real `SimulationEngine.run_tick`, real `crisis_phase` classification) to catch wiring bugs.
- Q: What shape should the `bypasses_bound_invariant` opt-out marker take? → A: `ClassVar[dict[str, str]]` keyed by predicate name with the justification as the value — makes SC-006 machine-checkable via a one-line CI assertion (`all(v.strip() for v in marker.values())`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Probability values stay in [0, 1] (Priority: P1)

A maintainer changes a formula that produces a `Probability`-typed value
(`P(S|A)`, `P(S|R)`, `success_probability`, `credibility`, edge
`solidarity_strength`) and inadvertently introduces an arithmetic step that
can underflow or overflow the unit interval. The Pydantic constrained type
`Probability` raises a `ValidationError` *at construction*, but only if the
out-of-range value is actually wrapped — bare `float` arithmetic followed
by late wrapping (or `model_copy(update=…)` writes that bypass validation,
or in-place graph node-data mutation via `update_node`) can silently produce
illegal values that survive a tick.

**Why this priority**: P1. Probability is the most ubiquitous bounded type
in the engine — it appears on `SocialClass.p_acquiescence`,
`SocialClass.p_revolution`, `SocialClass.organization`,
`SocialClass.repression_faced`, edge `solidarity_strength`, `Trap.score`,
`VanguardCadre.reputation`, and several other fields. A silent escape
from `[0, 1]` cascades into `Sigmoid`, divisions, and downstream
comparisons that produce wrong rupture decisions and wrong simulation
outcomes. This is the largest blast-radius invariant of the four.

**Independent Test**: Generate random `WorldState` instances containing
every entity type that has at least one `Probability`-typed field. Assert
that after a single `SimulationEngine.run_tick`, every such field on every
entity remains in `[0, 1]` (inclusive of the boundary). Also assert that
every formula in `src/babylon/formulas/` whose declared return type is
`Probability` produces a value in `[0, 1]` for any input drawn from its
declared domain strategy. Independent of US2 / US3 / US4.

**Acceptance Scenarios**:

1. **Given** a `WorldState` with `SocialClass` entities holding randomly
   drawn `p_acquiescence`, `p_revolution`, `organization`,
   `repression_faced` values, **When**
   `SimulationEngine.run_tick(graph, services, context)` runs all 21
   Systems in their declared order, **Then** every `Probability`-typed
   field on every entity in the post-state is in `[0.0, 1.0]` and the
   round-trip `WorldState.from_graph(state.to_graph())` does not raise
   `ValidationError`.

2. **Given** any formula `f: D → Probability` declared in
   `src/babylon/formulas/`, **When** `f` is invoked with random inputs
   drawn from the declared domain `D`, **Then** the returned value
   satisfies `0.0 <= float(value) <= 1.0` for at least 100 examples per
   formula.

3. **Given** an edge `Relationship(EdgeType.SOLIDARITY,
   solidarity_strength=…)` between two `SocialClass` nodes with random
   initial strengths, **When** `SolidaritySystem.step` propagates
   consciousness, **Then** the resulting `solidarity_strength` on every
   SOLIDARITY edge in the post-graph is in `[0.0, 1.0]`.

---

### User Story 2 — Wealth ≥ 0 and Heat ≥ 0 across all 21 Systems (Priority: P2)

A maintainer extends a System (e.g., adds a new economic transfer to
`ImperialRentSystem` or a new repression dynamic to `TerritorySystem`)
that under some input distribution can drive an entity's `wealth` below
zero or a territory's `heat` below zero. The constitutional commitment in
`src/babylon/engine/invariants.py` says **no system step produces negative
wealth or heat for any entity**. The `Invariant` protocol exists with
concrete `NonNegativeWealth` and `HeatNonNegativity` implementations, but
nothing today actually runs them against every System with random states.

**Why this priority**: P2. Wealth/Heat negativity bugs are usually caught
by example-based tests with deliberately stressed inputs, but the failure
surface is large — there are 21 Systems × N entities × random
configurations. A property-based runner is the right tool to land here,
and the work is mechanical (the protocol is already in place).

**Independent Test**: Parametrize over all 21 Systems in
`src/babylon/engine/systems/`. For each System, generate random
`WorldState` instances with valid pre-conditions for that System's inputs.
Run the System's `step` (or its System-equivalent in
`SimulationEngine.run_tick` if `step` is not directly callable). Assert
both `NonNegativeWealth().check(pre, post).ok` and
`HeatNonNegativity().check(pre, post).ok` hold. Independent of
US1 / US3 / US4.

**Acceptance Scenarios**:

1. **Given** a System `S` from the 21 Systems in
   `src/babylon/engine/systems/` and a random `WorldState` with
   non-negative pre-state wealth and heat, **When** `S.step` runs,
   **Then** `NonNegativeWealth().check(pre, post).ok is True`.

2. **Given** the same System `S` and the same random `WorldState`,
   **When** `S.step` runs, **Then**
   `HeatNonNegativity().check(pre, post).ok is True`.

3. **Given** the full 21-System pipeline run via
   `SimulationEngine.run_tick`, **When** the pipeline runs to completion,
   **Then** both invariants hold against the final post-state for any
   random initial `WorldState` whose pre-state satisfies them.

---

### User Story 3 — Ternary consciousness simplex preserved across the pipeline (Priority: P2)

A maintainer changes consciousness routing
(`route_agitation_to_ternary`, `normalize_to_simplex`,
`compute_ternary_consciousness`) or a System that mutates
`TernaryConsciousness(r, l, f)` (e.g., `ConsciousnessSystem`,
`SolidaritySystem`, `IdeologySystem`, the community-level dynamics in
`CommunitySystem`) and inadvertently produces a state where
`r + l + f ≠ 1` or one of the components leaves `[0, 1]`. The
`TernaryConsciousness` Pydantic model validates the constraint at
construction, but in-place mutations to graph node data dictionaries
(the standard pattern via `update_node`) and the `from_graph`
reconstruction can both silently break it if a System writes raw floats.

**Why this priority**: P2. The simplex constraint is already covered by
`tests/test_simplex_invariants.py` at the construction level (the
`simplex_points()` strategy). What is *not* covered is preservation across
the full `run_tick` pipeline against the in-place graph-mutation pattern.
Catching a drift here is the difference between trustworthy bifurcation
behavior (Fascism vs. Revolution routing depends on simplex math) and
silent nonsense.

**Independent Test**: Generate random `WorldState` instances with at
least one `SocialClass` carrying a valid `TernaryConsciousness`. Run
`SimulationEngine.run_tick` once. Assert that on every entity in the
post-state, the simplex constraint and per-component bounds still hold
within tolerance. Extend with a multi-tick variant (≥ 5 ticks) to catch
incremental drift. Independent of US1 / US2 / US4.

**Acceptance Scenarios**:

1. **Given** a `WorldState` with `SocialClass` entities each holding a
   valid `TernaryConsciousness(r, l, f)` drawn from the existing
   `simplex_points()` strategy, **When** `SimulationEngine.run_tick`
   runs the full 21-System pipeline, **Then** for every entity in the
   post-state: `abs(r + l + f - 1.0) <= 1e-4` and each of
   `r, l, f ∈ [0.0, 1.0 + 1e-4]`.

2. **Given** the same starting state, **When** five consecutive ticks
   run (each tick consuming the previous post-state), **Then** the
   simplex constraint and per-component bounds still hold on the fifth
   post-state.

3. **Given** a `WorldState` exercising `route_agitation_to_ternary`
   with non-zero agitation (the routing actually moves probability
   mass), **When** the routing applies, **Then** the resulting
   consciousness distribution still lies on the simplex.

---

### User Story 4 — α-smoothing continuity in steady state (Priority: P3)

A maintainer changes a smoothed coefficient — `gamma` (via
`economics/tick/smoothing.py`'s EMA), institution `alpha_smoothing_rate`
(`institution/balance.py`), community `heat_decay_alpha` /
`cohesion_decay_alpha` / `infrastructure_decay_alpha`
(`engine/systems/community.py`) — and the change introduces a
discontinuous step (e.g., a hard reset that should only fire in crisis).
The α-smoothing contract is:

> Between non-crisis ticks `t → t+1`, for every smoothed coefficient
> `c`, `|c_{t+1} - c_t| ≤ α · |raw_{t+1} - c_t|` (canonical EMA bound),
> where `α` is the coefficient's declared smoothing rate.

In **crisis ticks** the contract is suspended — discontinuous resets are
legitimate. Identifying crisis vs. non-crisis is done via the existing
`crisis_detector` / `CrisisState` machinery already in
`src/babylon/economics/tick/`.

**Why this priority**: P3. Coefficient α-smoothing is a relatively narrow
surface area compared with US1–US3, and a discontinuity bug is more
likely to be caught by manual review of the offending change. But the
invariant is load-bearing for tuning workflows (Optuna / sensitivity
analysis): a discontinuous coefficient breaks the assumption that the
loss surface is smooth in non-crisis regions.

**Independent Test**: Generate random pairs of consecutive
`CountyEconomicState` (or equivalent host of α-smoothed coefficients)
where the `crisis_phase` field on both ticks is `None` (steady state).
Assert that for each smoothed coefficient `c`,
`|c_{t+1} - c_t| ≤ α · |raw_{t+1} - c_t| + ε` for small `ε` accounting
for float64 round-off. Independent of US1 / US2 / US3.

**Acceptance Scenarios**:

1. **Given** two consecutive `CountyEconomicState` snapshots `s_t` and
   `s_{t+1}`, both with `crisis_phase is None`, **When** the smoothed
   coefficient `c` was updated via the canonical EMA rule, **Then**
   `|s_{t+1}.c - s_t.c| <= α * |raw_{t+1} - s_t.c| + 1e-12`.

2. **Given** any list of α-smoothed coefficients identifiable from
   `defines.py` (those with `_alpha`, `alpha_smoothing_rate`, or
   `_decay_alpha` in their field name), **When** a non-crisis tick runs,
   **Then** the inequality from Scenario 1 holds for every such
   coefficient.

3. **Given** a tick where `crisis_phase` transitions from a crisis enum
   value to `None` (or vice versa), **When** the inequality above is
   evaluated, **Then** the test **does not** assert the inequality (the
   suspension contract is honored).

---

### Edge Cases

- **Boundary equality**: A `Probability` value of exactly `0.0` or `1.0`
  is legal (closed interval). A `Wealth` value of exactly `0.0` is
  legal. A `Heat` value of exactly `0.0` is legal. Tests must not treat
  these as violations.
- **Empty state**: A `WorldState` with zero entities or zero territories
  trivially satisfies all four invariants. The harness must not produce
  false positives or skip silently — it should pass with an explicit
  "0 entities, 0 violations" trace.
- **Float64 ULP accumulation**: For the simplex constraint and the
  α-smoothing inequality, the comparison must be *magnitude-aware* in
  the same style as Spec 053's `_tol(n, magnitude)` helper. Pure
  equality comparison fails on the boundary at large magnitudes.
- **Crisis-phase ambiguity**: If neither pre-state nor post-state
  carries an explicit `crisis_phase`, treat the tick as non-crisis
  (steady state) by default, and surface this in the failure message
  so a maintainer can add an explicit crisis marker if the default is
  wrong for their case.
- **In-place graph mutation**: Systems mutate the shared graph in
  place via `update_node`. Tests must read the post-state via the same
  `from_graph` reconstruction the production engine uses, so violations
  produced through the round-trip path are observable.
- **Missing fields**: Some entity types may not carry every bound field
  (e.g., a `Territory` has no `Probability`-typed field). The harness
  must filter rather than fail when a generator produces an entity that
  lacks the field under test.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The harness MUST provide one Hypothesis test per
  bound-invariant predicate (US1, US2, US3, US4), each individually
  parametrized so a single failure isolates to a single
  (System, predicate) pair.
- **FR-002**: The Probability-bound test (US1) MUST cover (a) every
  `Probability`-typed field on every Pydantic entity model in
  `src/babylon/models/`, (b) every formula in `src/babylon/formulas/`
  whose declared return type is `Probability`, and (c) every
  `solidarity_strength` value on `EdgeType.SOLIDARITY` edges in the
  post-graph. Field discovery for (a) MUST use static introspection of
  `model_fields[name].annotation` — the harness walks every Pydantic
  model under `src/babylon/models/` and yields each `(ModelClass,
  field_name)` pair whose annotation resolves to the `Probability`
  constrained type. Formula discovery for (b) MUST use static
  introspection of `typing.get_type_hints(formula).get("return")` — the
  harness walks every public function in `babylon.formulas.*` and yields
  each callable whose declared return type is the `Probability` alias.
  No hand-maintained registry is permitted for either (a) or (b); adding
  a new `Probability` field or narrowing a formula's return annotation
  to `Probability` automatically extends test coverage.
- **FR-003**: The Wealth/Heat test (US2) MUST exercise all 21 Systems
  in `src/babylon/engine/systems/` and report a per-System pass/fail
  trace. For each System, the harness MUST attempt to synthesize a
  minimal pre-state via factories that satisfy that System's
  preconditions and run `S.step` in isolation. When isolation is not
  feasible (e.g., the System reads state populated by an upstream
  System and no factory can produce that state alone), the per-System
  result MUST be `SKIPPED` with an explicit reason string (e.g.,
  `"requires post-ImperialRentSystem state"`); a `SKIPPED` System MUST
  still appear in the trace so coverage gaps are visible.
- **FR-004**: The simplex test (US3) MUST run against the full
  `SimulationEngine.run_tick` pipeline (not only per-formula), and MUST
  also validate preservation across at least 5 consecutive ticks.
- **FR-005**: The α-smoothing test (US4) MUST identify the set of
  α-smoothed coefficients automatically by introspecting `defines.py`
  for fields whose names match `*_alpha`, `alpha_smoothing_rate`, or
  `*_decay_alpha`, AND MUST suspend the inequality assertion in crisis
  ticks identified by `crisis_phase is not None`. The discovery walker
  MAY exclude documented false-positive fields (e.g., power-law
  exponents that share the `_alpha` suffix but are not EMA rates) via
  an explicit, named exclusion set maintained in the harness module
  alongside the discovery walker. Each exclusion entry MUST carry a
  one-line comment explaining why the field is not an EMA rate. The harness MUST
  use a **hybrid** test strategy: (a) a *synthesized* Hypothesis
  sweep that constructs random `(prev, raw, alpha)` triples for every
  α-smoothed coefficient and asserts the EMA inequality directly
  against the formula, AND (b) an *observed* end-to-end smoke check
  that runs at least one multi-tick `SimulationEngine.run_tick`
  simulation, captures `(prev, raw, post)` for one canonical
  coefficient (e.g., the gamma EMA in `economics/tick/smoothing.py`),
  classifies each tick via `crisis_phase`, and asserts the inequality
  on every steady-state pair. The synthesized sweep falsifies the
  formula; the observed smoke check falsifies the wiring.
- **FR-006**: All four tests MUST use the same Hypothesis profile
  registration pattern as Spec 053 (default / slow registered
  project-wide in `tests/conftest.py`; dev / ci / nightly registered in
  `tests/property/conftest.py`).
- **FR-007**: All four tests MUST be runnable with
  `mise run test:unit` (default profile) and pass within the existing
  fast-CI budget. The slow profile (`HYPOTHESIS_PROFILE=slow`) MUST
  exercise at least 5× more examples per test.
- **FR-008**: Numeric comparisons MUST be magnitude-aware in the same
  style as Spec 053:
  `tol = max(1e-10, 1e-11 * N, 1e-13 * |magnitude|)` for the simplex
  constraint and the α-smoothing inequality. The Probability and
  Wealth/Heat tests MAY use exact ≥ / ≤ comparison since the type
  contracts are inclusive of the boundary.
- **FR-009**: Failures MUST surface a Hypothesis-shrunk minimal
  example, with a diagnostic message that names (a) the invariant
  violated, (b) the System or formula that produced the violation,
  and (c) the offending field, entity ID, and value.
- **FR-010**: Systems and formulas that **legitimately** produce
  out-of-range intermediate values (if any are discovered during
  implementation) MUST be flagged with an explicit
  `bypasses_bound_invariant: ClassVar[dict[str, str]] = {…}` marker
  whose keys are predicate names (e.g.,
  `"probability_in_range"`, `"non_negative_wealth"`) and whose values
  are non-empty justification strings (one sentence each). The test
  harness MUST consume this marker and skip the named predicate for
  that System or formula, AND MUST assert at collection time that
  every value is non-empty (machine-enforced SC-006). This mirrors
  the `creates_value: ClassVar[bool]` pattern from Spec 053 while
  extending it with auditable justification.
- **FR-011**: The α-smoothing test MUST distinguish between
  coefficient *values* (which can drift by at most α · raw_delta) and
  coefficient *parameters* (the α rate itself, which is a configuration
  constant and is not subject to the inequality). Tests MUST only
  assert the inequality on values, not on parameters.
- **FR-012**: The Probability test MUST validate that the
  `WorldState.from_graph(WorldState.to_graph(state))` round-trip
  preserves the `[0, 1]` constraint on every `Probability`-typed
  field, not only on freshly constructed entities.

### Key Entities

- **`Invariant` protocol**: Existing in
  `src/babylon/engine/invariants.py`. This feature adds two new
  concrete invariants alongside `NonNegativeWealth` and
  `HeatNonNegativity`: `ProbabilityInRange` and `SimplexPreserved`.
- **`BoundInvariantHarness`**: New Hypothesis-driven runner that takes
  a System (or System pipeline) and a list of bound invariants and
  runs them against random `WorldState` instances. Mirrors the
  existing conservation harness pattern from Spec 053.
- **`CrisisStateInspector`**: Helper that reads `crisis_phase` from a
  `CountyEconomicState` (or equivalent) and answers "is this tick
  steady state?". Drives the suspend-in-crisis logic for US4.
- **`bypasses_bound_invariant` ClassVar**: Per-System and per-formula
  opt-out marker shaped as `ClassVar[dict[str, str]]` — predicate
  name → justification string. The harness skips the named predicate
  for the marked System / formula and machine-asserts that every
  value is a non-empty justification (mirrors and extends Spec 053's
  `creates_value: ClassVar[bool]` pattern).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer who introduces a regression that lets a
  `Probability` field exceed `1.0` in any post-state has the
  regression caught by `mise run test:unit` in the same run that
  ships the change, with a Hypothesis-shrunk minimal failing example
  pointing at the offending field, entity ID, and System or formula.
- **SC-002**: All 21 Systems in `src/babylon/engine/systems/` are
  exercised by the Wealth/Heat invariant test, with a per-System
  pass / fail / skip trace visible in test output (skips MUST carry
  an explicit reason string); adding a new System to the directory
  automatically extends the test coverage (no manual list
  maintenance).
- **SC-003**: The simplex constraint test detects any drift larger
  than `1e-4` after 5 consecutive ticks of full-pipeline execution
  against any randomly drawn `WorldState` containing at least one
  `TernaryConsciousness`-bearing entity.
- **SC-004**: The α-smoothing test detects any non-crisis tick on
  which any α-smoothed coefficient violates the EMA inequality
  `|c_{t+1} - c_t| ≤ α · |raw_{t+1} - c_t| + 1e-12`, both in the
  synthesized Hypothesis sweep (formula correctness, every coefficient)
  and in the observed end-to-end smoke check (wiring correctness, one
  canonical coefficient through real `run_tick`); tests that touch
  crisis-phase ticks pass silently.
- **SC-005**: The four invariant test files together complete in
  under 30 seconds on the default profile (max_examples=100,
  derandomize=True) and under 5 minutes on the slow profile
  (max_examples=500), measured on the same hardware as the Spec 053
  baseline (≈1 minute for the conservation suite).
- **SC-006**: `bypasses_bound_invariant` markers are present on any
  System or formula that the implementation discovers legitimately
  violates a predicate; every such marker carries a non-empty
  justification string in the marker's `dict[str, str]` value (e.g.,
  `{"probability_in_range": "rounds intermediate to 0.0 + ε before
  re-clipping"}`). The harness machine-enforces this at collection
  time so empty or missing justifications fail CI rather than slipping
  through review.

## Assumptions

- Hypothesis ^6.149.0 is already in
  `[tool.poetry.group.dev.dependencies]` (added by Spec 053). No new
  dependency is required.
- The existing `Invariant` protocol in
  `src/babylon/engine/invariants.py` is the canonical interface for
  declaring bound invariants. New invariants implement the same
  protocol.
- The 21 Systems listed in `src/babylon/engine/systems/` (excluding
  `__init__.py` and `protocol.py`) are the canonical System set. If
  a new System is added during implementation, the harness picks it
  up via directory introspection rather than a hand-maintained list.
- Crisis vs. steady-state classification uses the existing
  `crisis_phase` field on `CountyEconomicState` (and equivalents).
  `crisis_phase is None` ⇒ steady state; any non-`None` value ⇒
  crisis.
- The Spec 053 conservation harness, profile registration pattern,
  and magnitude-aware tolerance helper are the model for this work.
  Implementation reuses the same patterns rather than reinventing.
- Pydantic constrained types (`Probability`, `Currency`, `Intensity`,
  `Coefficient`, `Ideology`) raise `ValidationError` at construction
  for out-of-range inputs. The bound test MUST verify the absence of
  *silent* escapes (via in-place graph mutation, `model_copy` writes,
  or arithmetic-then-late-wrap), not the constructor itself.
- The α-smoothing identification heuristic (`*_alpha`,
  `alpha_smoothing_rate`, `*_decay_alpha`) covers the present
  coefficient set in `defines.py`. If implementation discovers
  additional smoothed coefficients with different naming, the
  heuristic is widened and the spec is updated in a follow-up
  `/speckit.clarify` pass.
- All four invariants are tested via Hypothesis property strategies;
  no example-based scaffold is added (existing example tests in
  `tests/test_simplex_invariants.py` and elsewhere remain untouched).
