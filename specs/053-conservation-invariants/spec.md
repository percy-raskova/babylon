# Feature Specification: Property-Based Tests for Conservation Invariants

**Feature Branch**: `053-conservation-invariants`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: Property-based tests (using Hypothesis) for the conservation invariants — quantities that must survive a `step()` of the simulation engine. Five distinct invariants are in scope: (1) c+v+s value conservation across non-creating systems; (2) H3 hierarchical sum conservation (res-7 → res-6 → res-5 sheaf gluing); (3) variable capital conservation under LODES OD circulation; (4) population conservation modulo births and deaths across D-P-D′ cohort transitions; (5) capital-stock perpetual-inventory recurrence `K_{t+1} = (1−δ) K_t + I_t`. Most invariants currently have example-based tests; this work converts them to property-based tests with random generators, and adds explicit invariant assertions where they are missing.

## Clarifications

### Session 2026-05-05

- Q: How are "non-creating" systems identified for the c+v+s conservation test? → A: Default-deny — every pipeline system is tested unless it carries an explicit `creates_value=True` opt-out marker.
- Q: At what granularity should the c+v+s conservation test run — per-system, full pipeline, or both? → A: Both — per-system isolation tests for diagnosis, plus a full-pipeline `run_tick()` test for interaction coverage.
- Q: Which population registry is the conservation invariant measured against? → A: D-P-D′ lifecycle cohort counts (`DPDState`), as introduced by spec 030.
- Q: Where should the new property test files live? → A: `tests/property/invariants/test_<invariant>.py`, one file per invariant; reuses spec-040 strategy infrastructure under `tests/property/strategies/`.
- Q: Should the circulation tolerance scale with hex count, or stay fixed at 1e-8? → A: Scaled `max(1e-10, 1e-11 * N)`, where N is the generated hex count. The same scaled-tolerance policy applies to the c+v+s conservation test, since both depend on the same sparse-multiply accumulation behaviour.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — c+v+s Value Conservation Across Systems (Priority: P1)

A simulation maintainer changes a system that is *not* supposed to create or destroy value (for example, `ProductionSystem`, which observes value-in-hours from already-hydrated capital stocks; or routing/aggregation systems). They run the property-based test suite. If the change accidentally adds, drops, or rescales `c + v + s` anywhere in the grid, a Hypothesis-generated counterexample (a specific seed, OD matrix, and starting hex-state distribution) appears in the failure output, with a minimized example.

**Why this priority**: c+v+s conservation is the strongest claim about the engine's mathematical correctness and the one most likely to silently break under refactors. It is the load-bearing invariant for treating Marx's value accounting as a real model rather than a heuristic.

**Independent Test**: Generate random `HexGrid` / `WorldState` instances (varying hex count, varying per-hex c/v/s values, varying topology) using the spec-040 strategies in `tests/property/strategies/`. At per-system granularity, assert `sum(c+v+s)_post == sum(c+v+s)_pre` for each non-opt-out system in isolation. At full-pipeline granularity, assert the same after `SimulationEngine.run_tick()`. Both granularities use the same generators and tolerance. Verified standalone by running `pytest tests/property/invariants/test_value_conservation.py`.

**Acceptance Scenarios**:

1. **Given** a randomly-generated `WorldState` with N ∈ [1, 25 000] hexes (Article IV statewide-Michigan scale) and arbitrary non-negative c/v/s per hex, **When** any single non-opt-out system is invoked in isolation, **Then** `|sum(c+v+s)_post − sum(c+v+s)_pre| < max(1e-10, 1e-11 * N)` (per-system granularity, scaled tolerance).
2. **Given** the same generated `WorldState`, **When** `SimulationEngine.run_tick()` is invoked end-to-end, **Then** `|sum(c+v+s)_post − sum(c+v+s)_pre| < max(1e-10, 1e-11 * N)` (full-pipeline granularity, catches inter-system interaction bugs).
3. **Given** a `WorldState` where some hexes have c=v=s=0, **When** the per-system or full-pipeline test runs, **Then** the conservation assertion still holds (zero-capital edge case).
4. **Given** a `WorldState` where one hex carries the entire capital mass, **When** the per-system or full-pipeline test runs, **Then** the conservation assertion still holds (concentration edge case).
5. **Given** a counterexample is found, **When** Hypothesis shrinks it, **Then** the minimized failing input is recorded in the project's Hypothesis example database for fast regression replay, and the failure message identifies whether the violation was per-system (and which system) or only visible at the full-pipeline level.

---

### User Story 2 — H3 Hierarchical Sum Conservation (Sheaf Gluing) (Priority: P1)

A simulation maintainer adds or alters resolution-aware logic (aggregation, equalization, ground-rent computation). They run the property suite. If `sum(c, v, s)` over a parent's children at any resolution diverges from the parent-level aggregate, the test fails with a generated `HexGrid` whose hierarchy violates the gluing condition.

**Why this priority**: The constitution treats the H3 hierarchy as a sheaf — exact conservation across resolutions is the gluing condition that justifies treating per-county and per-state aggregates as derived rather than independent state. Breaking it silently corrupts every multi-resolution analysis downstream.

**Independent Test**: Generate random `HexGrid`s where hexes carry parent pointers at res-6 and res-5. Assert that for every res-6 parent, `sum_{r7 children}(c+v+s) == parent_aggregate(c+v+s)` within tolerance. Same assertion for res-5. Same assertion at any post-step tick.

**Acceptance Scenarios**:

1. **Given** a randomly-generated `HexGrid` with multiple res-6 parents and varying numbers of res-7 children per parent, **When** the aggregator is run, **Then** for every parent, `|sum_children(c+v+s) − parent_aggregate(c+v+s)| < 1e-10`.
2. **Given** the same grid, **When** aggregated to res-5, **Then** the res-5 totals equal both the sum of res-6 totals and the sum of res-7 hexes.
3. **Given** any tick-step that mutates per-hex c/v/s, **When** aggregation is re-run after the step, **Then** the gluing condition still holds (i.e., the system did not put a hex out-of-sync with its parent).
4. **Given** an empty grid or a grid with one hex, **When** aggregation is run, **Then** the invariant holds trivially (no false negatives on degenerate inputs).

---

### User Story 3 — Variable Capital Conservation Under LODES Circulation (Priority: P1)

A maintainer changes commute-flow handling (`circulate_wages`, OD-matrix construction, or LODES integration). They run the property suite. The invariant `sum(v)_post == sum(v)_pre` must hold for *any* sparse OD matrix and *any* starting hex state, not just the hydrated example used today.

**Why this priority**: LODES wage redistribution is the only mechanism in the substrate that moves `v` between hexes. The substrate's `circulate_wages` rescales rows to conserve `sum(v)` to ~1e-8 by construction; that property must be tested against arbitrary inputs because the rescaling is the load-bearing claim about the function's correctness.

**Independent Test**: Generate random OD matrices (varying sparsity, dimension, normalization) and random starting hex states. Assert `|sum(v)_post − sum(v)_pre| < max(1e-10, 1e-11 * N)`. Also assert `sum(c)` and `sum(s)` are unchanged exactly (circulation only touches `v`).

**Acceptance Scenarios**:

1. **Given** a random sparse OD matrix with N hexes (N ∈ [1, 25 000], with extreme sparsity — density ≤ 0.01 — at the upper end matching empirical LODES) and a random starting `HexGrid`, **When** `circulate_wages` is called, **Then** `|sum(v)_post − sum(v)_pre| < max(1e-10, 1e-11 * N)`.
2. **Given** the identity OD matrix, **When** `circulate_wages` is called, **Then** every hex's `v` is unchanged within `max(1e-10, 1e-11 * N)` (no spurious redistribution).
3. **Given** an OD matrix with empty rows (some hexes have no outflow), **When** `circulate_wages` is called, **Then** `sum(v)` is still conserved within the same tolerance.
4. **Given** any input, **When** circulation runs, **Then** `sum(c)_post == sum(c)_pre` and `sum(s)_post == sum(s)_pre` exactly (these fields must not be modified).

---

### User Story 4 — Population Conservation Modulo Births and Deaths (Priority: P2)

A maintainer changes the D-P-D′ lifecycle (spec 030 `DPDState`), REPRODUCE actions, recruitment, or mortality logic in `VitalitySystem`. The property suite asserts the explicit accounting equation: `population_{t+1} = population_t + births_t − deaths_t`, where `population_t` is the per-hex `DPDState` cohort total summed across the grid. If a cohort transition silently drops or duplicates members, the test fails with a generated initial `DPDState` distribution and tick history.

**Why this priority**: Today the population accounting equation is partially tested — births and deaths are exercised individually, but the explicit `pop_{t+1} = pop_t + births − deaths` equality is not asserted as an invariant. A silent off-by-one in cohort transitions could drift the population by minute amounts per tick and only show up after thousands of ticks. P2 because it is a known-tested area, not a known-broken one.

**Independent Test**: Generate random initial `DPDState` distributions across hexes and random tick sequences. After each tick, sum the per-hex cohort counts to obtain `population_t`, and assert `pop_{t+1} == pop_t + births_recorded_at_t − deaths_recorded_at_t` exactly (cohort counts are integer-valued, so tolerance is 0).

**Acceptance Scenarios**:

1. **Given** a random initial cohort distribution and a random tick step, **When** the lifecycle systems run, **Then** `pop_{t+1} = pop_t + births_t − deaths_t` exactly.
2. **Given** a tick with zero births and zero deaths, **When** the lifecycle systems run, **Then** `pop_{t+1} = pop_t`.
3. **Given** a tick where mortality removes more agents than births add, **When** the lifecycle systems run, **Then** the population decreases by exactly `deaths − births`, with no negative counts.
4. **Given** the test is run across multiple consecutive ticks, **When** births and deaths are summed across ticks, **Then** `pop_T = pop_0 + Σ births − Σ deaths`.

---

### User Story 5 — Capital Stock Perpetual-Inventory Recurrence (Priority: P2)

A maintainer changes `capital_stock` depreciation or investment handling. The property suite asserts the recurrence `K_{t+1} = (1 − δ) K_t + I_t` for any starting `K_t`, depreciation rate `δ ∈ [0, 1]`, and investment `I_t ≥ 0`. If the recurrence is violated, a counterexample is produced.

**Why this priority**: This is not strictly a conservation law — depreciation destroys K — but it is a recurrence invariant: the relationship between consecutive ticks must hold by construction. Catching drift here protects every downstream calculation that reads from `K`.

**Independent Test**: Generate random `(K_t, δ, I_t)` triples within physical bounds (K ≥ 0, δ ∈ [0,1], I ≥ 0). Apply the perpetual-inventory step. Assert `|K_{t+1} − ((1−δ) K_t + I_t)| < 1e-10`.

**Acceptance Scenarios**:

1. **Given** random `(K_t, δ, I_t)` within bounds, **When** the perpetual-inventory step runs, **Then** the recurrence holds within 1e-10.
2. **Given** `δ = 0` (no depreciation), **When** the step runs, **Then** `K_{t+1} = K_t + I_t`.
3. **Given** `δ = 1` (full depreciation), **When** the step runs, **Then** `K_{t+1} = I_t`.
4. **Given** `I_t = 0`, **When** the step runs, **Then** `K_{t+1} = (1 − δ) K_t` and is monotonically non-increasing in `δ`.

---

### Edge Cases

- **Empty grid / zero population / zero capital**: All invariants must hold trivially (no false positives on degenerate inputs).
- **Single-hex grid / single-cohort population**: Hierarchy and circulation tests must not divide by zero or assume N > 1.
- **Concentration on one hex / one cohort**: All capital or population in a single bucket; must not bias rounding.
- **Floating-point near-zero values**: Generated values close to but above 0 must not collapse to 0 silently.
- **Generated counterexamples are recorded**: Hypothesis must persist failing examples to its example database for fast replay across CI runs.
- **OD matrices with empty rows or empty columns**: Circulation must conserve `v` even when some hexes have no commuters.
- **Resolutions with single child**: H3 parents that contain exactly one res-7 child must still satisfy gluing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The test suite MUST use the Hypothesis library (already a dev dependency in `pyproject.toml`) for all property-based tests added under this feature.
- **FR-002**: The test suite MUST express each of the five invariants (c+v+s conservation, H3 hierarchical sum conservation, variable capital under circulation, population modulo births/deaths, capital-stock recurrence) as at least one Hypothesis-decorated test.
- **FR-003**: Each property test MUST define a Hypothesis strategy (`@composite` or built-in) that generates inputs across the realistic state space — varying grid size, varying per-hex magnitudes, varying topology where applicable.
- **FR-004**: For c+v+s conservation, the test MUST follow a default-deny policy: every system in the canonical engine pipeline is exercised by the property test and MUST satisfy `|sum(c+v+s)_post − sum(c+v+s)_pre| < tol(N)`, where `tol(N) = max(1e-10, 1e-11 * N)` and N is the generated hex count. A system that legitimately creates or destroys value MUST opt out by declaring an explicit class-level marker (e.g. `creates_value: ClassVar[bool] = True`); the test reads the marker and skips opt-out systems while logging which systems were skipped and why.
- **FR-004a**: The `creates_value` marker MUST default to `False` for any system that does not declare it. New systems added to the pipeline therefore enter the conservation test by default; a maintainer cannot silently add a value-mutating system without an explicit declaration.
- **FR-004b**: c+v+s conservation MUST be tested at two granularities: (i) per-system — one parametrized property test that invokes each non-opt-out system in isolation against a generated `WorldState` and asserts conservation, providing pinpoint diagnosis when a single system regresses; and (ii) full-pipeline — one property test that invokes `SimulationEngine.run_tick()` end-to-end and asserts conservation across the whole step, catching interaction bugs (e.g., one system rounds up and a downstream system rounds down differently) that per-system tests would miss.
- **FR-005**: For H3 hierarchical sum conservation, the test MUST assert that for every res-6 parent in a generated grid, `sum_{children}(c+v+s) == parent_aggregate(c+v+s)` within `1e-10`, and the same for res-5 parents. The assertion MUST also hold post-step.
- **FR-006**: For variable capital circulation, the test MUST generate sparse OD matrices and assert `|sum(v)_post − sum(v)_pre| < tol(N)`, where `tol(N) = max(1e-10, 1e-11 * N)` and N is the generated hex count. The test MUST additionally assert that `sum(c)` and `sum(s)` are unchanged exactly.
- **FR-007**: For population conservation, the test MUST assert `pop_{t+1} == pop_t + births_t − deaths_t` exactly across one or more simulated ticks, where `population_t` is the grid-wide sum of D-P-D′ lifecycle cohort counts read from per-hex `DPDState` instances. `births_t` and `deaths_t` are read from the same tick's REPRODUCE-action and `VitalitySystem` mortality bookkeeping.
- **FR-008**: For the capital-stock recurrence, the test MUST assert `|K_{t+1} − ((1 − δ) K_t + I_t)| < 1e-10` for generated `(K_t, δ, I_t)` triples within physical bounds.
- **FR-009**: The existing example-based tests in `tests/unit/economics/substrate/test_conservation.py`, `test_aggregation.py`, and `test_circulation.py` MUST be preserved as documentation/regression cases; the property-based tests are added alongside them, not as replacements.
- **FR-009a**: New property test files MUST live under `tests/property/invariants/`, one file per invariant: `test_value_conservation.py`, `test_h3_hierarchical.py`, `test_circulation_v.py`, `test_population.py`, `test_capital_recurrence.py`. Generators MUST reuse the spec-040 strategy infrastructure under `tests/property/strategies/` (extending it where needed) rather than introducing parallel generator code.
- **FR-010**: Failing counterexamples MUST be persisted via Hypothesis's example database so that CI replays them on subsequent runs without re-shrinking.
- **FR-011**: Property tests MUST be runnable via the existing `mise run test:unit` (or an equivalent existing namespace) without requiring new top-level commands or configuration.
- **FR-012**: Each property test MUST document its tolerance choice and the reason (e.g., "1e-8 because sparse-matrix multiplication accumulates rounding proportional to hex count") in the docstring.
- **FR-013**: When a property test fails, the failure output MUST identify which invariant was violated, the generated input that triggered it, and (where applicable) the system in the engine pipeline responsible.
- **FR-014**: Property tests MUST be deterministic given a seed. Hypothesis's default deterministic mode MUST be respected; no test may rely on wall-clock time or non-seeded randomness.

### Key Entities

- **Conservation Invariant**: A predicate over pre-step and post-step engine state that must hold across all valid inputs. Five named invariants in scope.
- **Hypothesis Strategy**: A generator that produces randomized but valid inputs (HexGrids, OD matrices, populations, K/δ/I triples) for property tests.
- **Tolerance**: A documented numerical threshold per invariant. For exact-arithmetic invariants (H3 hierarchical sum, capital-stock recurrence) the threshold is fixed at `1e-10`. For invariants whose error accumulates with hex count (c+v+s conservation, variable capital under circulation) the threshold scales as `tol(N) = max(1e-10, 1e-11 * N)`. For integer-valued invariants (population) the threshold is `0`.
- **Counterexample Database**: The Hypothesis-managed cache of failing inputs replayed at the start of each run to confirm regressions stay fixed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five invariants have at least one Hypothesis-decorated test in the suite, and each test runs at least 100 generated examples per CI invocation by default.
- **SC-002**: The property-based test file(s) execute in under 60 seconds in the unit-test gate (`mise run test:unit`) using the `default` Hypothesis profile (100 examples, size-biased toward small grids, large grids — up to 25 000 hexes — exercised occasionally). Exhaustive runs at the upper bound (e.g., the full 25 000-hex Michigan scale on every example) are gated behind the `slow` profile (`HYPOTHESIS_PROFILE=slow`) and do not block the fast CI loop.
- **SC-003**: A maintainer who introduces a deliberate violation of any of the five invariants (e.g., adding `+1` to a capital quantity in the wrong place) sees a failing test with a minimized counterexample within one local test invocation.
- **SC-004**: The Hypothesis example database under the project's configured `.hypothesis/` directory accumulates and replays failing examples between runs, so any regression that previously failed is caught on the very next run without re-shrinking.
- **SC-005**: Coverage of the engine-system pipeline is complete: every system documented as "non-creating" with respect to value is exercised by the c+v+s conservation property test.
- **SC-006**: The original example-based tests still pass and are kept as named regression scenarios, ensuring no loss of existing coverage.

## Assumptions

- Hypothesis is already a project dev dependency (`hypothesis = "^6.149.0"` in `pyproject.toml`) and the existing `[tool.hypothesis]` section in `pyproject.toml` provides usable defaults; no new tooling is introduced.
- The existing `tests/unit/economics/substrate/conftest.py` fixtures (`hydrated_hex_grid`, `MockCommuterFlowSource`, `WAYNE_HEX_IDS`) remain available for property tests to compose with, but the primary generator source is `tests/property/strategies/` (e.g., `worldstate_strategy`) so that the new files compose into the spec-040 invariant harness conventions.
- The list of "non-creating" systems is determined at test-discovery time by inspecting each system class in the canonical engine pipeline for a `creates_value` class-level marker (default `False`). Systems that mutate `c+v+s` legitimately (such as ones that destroy capital during dispossession events or create fresh value during ecological regeneration) MUST set `creates_value: ClassVar[bool] = True` to opt out. `ProductionSystem` does NOT opt out, because the user's framing is that it observes already-hydrated value-in-hours rather than generating fresh value.
- The Hypothesis default of 100 examples per `@given` test is sufficient for CI; specific tests may opt into a higher count for thorough but slower variants gated behind an existing pytest marker.
- For the H3 hierarchical invariant, the strategy generates parent-child pointer maps consistent with the `HexGrid` model, not arbitrary inconsistent structures; the invariant is about the engine's preservation of the structure, not about validating malformed input grids.
- For the population invariant, "population" is the grid-wide sum of per-hex `DPDState` cohort counts (the lifecycle representation introduced in spec 030). The test reads cohort totals via existing `DPDState` accessors and reads births/deaths via the existing REPRODUCE-action and `VitalitySystem` bookkeeping; no new persistence is introduced. Other registries (Organization membership, agent registry) are out of scope for this invariant.
- Capital-stock recurrence inputs (`K_t`, `δ`, `I_t`) are bounded to physically meaningful ranges (`K ≥ 0`, `δ ∈ [0, 1]`, `I ≥ 0`); the test does not attempt to validate behaviour outside these bounds.
- Numerical tolerances follow the precedents already used in the example-based tests, generalised to handle Hypothesis-generated grids of varying size: `1e-10` for exact aggregation, `max(1e-10, 1e-11 * N)` for sparse-multiply accumulation (c+v+s and circulation), `0` for integer populations. The scaled tolerance derives from the documented "error proportional to hex count" behaviour in the existing `circulate_wages` tests.
