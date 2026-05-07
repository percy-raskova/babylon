# Implementation Plan: Topological Invariants — Property-Based Tests

**Branch**: `055-topology-invariants` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/055-topology-invariants/spec.md`

## Summary

Convert four topological invariants — edge-mode trajectory legality across
the 17-arc state machine, the hyperedges-not-pairwise rule (Constitutional
Anti-Pattern VIII.9), frozen-Pydantic discipline (`model_copy` is the only
mutation pathway), and `WorldState.from_graph(state.to_graph())` round-trip
identity — into Hypothesis-driven property tests. Each predicate becomes a
single parametrized test file under `tests/property/invariants/` that
mirrors the Spec 053 / Spec 054 harness style: project-wide profile
registration, default-deny + opt-out marker pattern, single-source-of-truth
imports from production code (`_VALID_TRANSITIONS`, `_iter_worldstate_collections`,
`from_graph` exclude rules). Two new concrete `Invariant` implementations
are added to `src/babylon/engine/invariants.py`
(`EdgeModeTrajectoryLegal`, `NoCommunityFanOut`) alongside the existing
four; US3's frozen-discipline check is a harness-level utility because it
operates over `id()` rather than field values; US4's round-trip is a
property test that uses the existing `worldstate_strategy()` and the
production `from_graph` exclude-set with no new Invariant class.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models), NetworkX 3.x (graph protocol). XGI 0.10 is available but not required for the chosen US2 detector (`_node_type == "community"` graph attribute, per the 2026-05-06 clarification).
**Storage**: N/A — `.hypothesis/` example DB persists generated counterexamples (already in `.gitignore`)
**Testing**: pytest with `@pytest.mark.unit` markers; profile registration in `tests/conftest.py` (project-wide) and `tests/property/conftest.py` (per-package) per Spec 053 / Spec 054 pattern
**Target Platform**: `mise run test:unit` (default fast gate) + `HYPOTHESIS_PROFILE=slow` (nightly / pre-release)
**Project Type**: Testing infrastructure extending the existing `tests/property/` module
**Performance Goals**: 4 invariant test files complete in ≤ 60 s on default profile (`max_examples=100`, `derandomize=True`); ≤ 5 min on slow profile (`max_examples=500`); combined `tests/property/` suite (Spec 053 + 054 + 055) ≤ 3 min on default profile (current baseline 83 s)
**Constraints**: Must reuse Spec 053 / Spec 054 harness style (profile registration, opt-out ClassVar markers, single-source-of-truth imports); zero new third-party dependencies; deterministic on default profile; failure messages must point at offending arc / source-target pair / entity ID / changed field
**Scale/Scope**: 5 starting `EdgeMode` values × ≥ 100 examples × ≥ 10 evidence events per trajectory (US1 synthesized); 1 observed end-to-end trajectory of length ≥ 5 ticks (US1 observed); 21 Systems × random `WorldState` (US2 + US3 reuse Spec 054's `_iter_worldstate_collections`); ≈ 12+ state-bearing Pydantic model classes for the structural `frozen=True` audit (US3); single round-trip property over `worldstate_strategy()` (US4)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Tier | Compliance |
|-----------|------|------------|
| **III.2 Falsifiability Required** | P1 | **PASS — direct alignment.** Each topological invariant becomes a Hypothesis-driven falsifiability harness. Predictions are encoded as predicates; falsifying observations are Hypothesis-shrunk minimal trajectories / edge-triples / id-mismatch entities / round-trip dump diffs. |
| **III.7 Determinism Hash and Replayability** | P0 | **PASS — direct alignment for US3.** US3 *is* the operational test of III.7: the engine's purity claim (`step(WorldState) → WorldState` produces no in-place mutations) is asserted per-tick. Default profile uses `derandomize=True` (per Spec 053 / Spec 054 convention); a failing Hypothesis seed is reproducible across runs. |
| **III.8 Aleksandrov Test (Structural Provenance)** | P0 | **PASS — explicit alignment table in research.md §6.** Each of the four invariants ties to a material relation: edge-mode trajectories encode the dialectical-field state machine (Constitution I.15); the hyperedges-not-pairwise rule encodes the dyadic-morphism / hypergraph-membership distinction (II.7 / VIII.9); frozen discipline encodes the III.7 purity contract; round-trip identity encodes the State/Engine separation (II.6). |
| **I.15 Edge Mode Transitions** | P1 | **PASS — US1 IS the state-machine guard.** Trajectory legality is the operational test of I.15's transition topology; the 17 arcs in `_VALID_TRANSITIONS` are imported as the single source of truth, not duplicated. |
| **II.6 State is Data, Engine is Transformation** | P1 | **PASS — US3 + US4 ARE the operational tests.** US3 asserts the "Engine is Transformation" half (no in-place state mutation); US4 asserts the "State is Data" half (round-trip serialization preserves the data exactly modulo the explicit `tick` parameter). |
| **II.7 Edges vs Hyperedges** | P2 | **PASS, with care.** The principle is currently `[TRANSITION STATE]` pending Amendment D. US2's linter encodes the *current* discipline (no community→member fan-outs in the morphism graph); the test is a ratchet that does not depend on the unresolved reconciliation. The detector lives in a single helper so a future Amendment D shift is a one-line edit. |
| **VIII.9 Community as Pairwise Edge** | P1 | **PASS — US2 IS the operational lint.** The Anti-Pattern VIII.9 commitment is currently asserted *nowhere*; this feature converts it into a machine-checkable structural assertion. |
| **II.11 Subsystem Table Ownership** | P1 | **N/A — no DB I/O.** Tests are pure in-memory; no cross-subsystem table reads. |
| **I.20 Spatial Substrate Immutable** | P0 | **PASS — substrate is read-only.** Tests do not mutate hex grid; round-trip respects substrate immutability via the same `WorldState.from_graph` the production engine uses. |
| **II.4 Quantities vs Coefficients** | P2 | **N/A — no smoothed-coefficient assertions.** Bound-invariant US4 (Spec 054) handles this. |
| **V Verb Atomicity** | P0 | **N/A — no verb invocation.** Tests exercise Systems / serialization, not player verbs. |

**Gate decision (Phase 0 pre-research): PASS.** No constitutional violations.
The one `[TRANSITION STATE]` principle in scope (II.7) is handled by
encoding the *current* discipline behind a single-helper detector; a future
Amendment D ratification updates one location. Proceed to Phase 0.

**Re-evaluation (post-Phase 1 design): PASS.** The design (`data-model.md`
+ four contracts in `contracts/`) introduces:

- Two new `Invariant` Protocol implementations (`EdgeModeTrajectoryLegal`,
  `NoCommunityFanOut`) — both consume `WorldState` (or its graph
  representation) only, mutate nothing.
- A `TopologyInvariantHarness` that observes `(pre, post)` pairs and a
  `frozen_audit.py` helper that snapshots `id()` and asserts the
  identity-discipline post-tick — neither mutates engine internals.
- A `model_class_registry.py` discovery walker that enumerates state-bearing
  Pydantic model classes for the static `frozen=True` audit (read-only).
- New Hypothesis strategies (`tests/property/strategies/`) — produce frozen
  test inputs.
- Reuse of Spec 054's `_iter_worldstate_collections` helper, `system_registry`,
  and profile-registration infrastructure (no duplication).

Nothing in the design adds primitives (no new dialectic types, morphism
relations, transport edge types), mutates substrate (I.20), introduces
non-determinism (default profile `derandomize=True`), uses magic constants
(legal-arc set imported from production), produces unfalsifiable formalism
(each invariant has a falsification predicate), invokes AI adjudication
(II.5), reads cross-subsystem tables (II.11), or depends on `[TRANSITION
STATE]` principles (the II.7 dependency is mediated by the single helper
described above). Aleksandrov Test trace is documented in `research.md §6`.
Proceed to Phase 2 (`/speckit.tasks`).

## Project Structure

### Documentation (this feature)

```text
specs/055-topology-invariants/
├── plan.md                              # This file (/speckit.plan command output)
├── spec.md                              # Already written (/speckit.specify + /speckit.clarify)
├── research.md                          # Phase 0 output — patterns + decisions
├── data-model.md                        # Phase 1 output — entities, attributes, relationships
├── quickstart.md                        # Phase 1 output — how to run + interpret failures
├── contracts/                           # Phase 1 output — per-invariant predicate contracts
│   ├── edge_mode_trajectory.md
│   ├── community_membership_lint.md
│   ├── frozen_discipline.md
│   └── round_trip_identity.md
├── checklists/
│   └── requirements.md                  # Already written (spec quality checklist)
└── tasks.md                             # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code (repository root)

```text
tests/property/
├── conftest.py                          # MODIFY — only if Spec 053 / 054 fixtures are insufficient
│                                        #          (default: reuse as-is)
├── invariants/                          # Existing directory from Spec 053 / 054
│   ├── test_value_conservation.py       # Spec 053 — unchanged
│   ├── test_h3_hierarchical.py          # Spec 053 — unchanged
│   ├── test_circulation_v.py            # Spec 053 — unchanged
│   ├── test_population.py               # Spec 053 — unchanged
│   ├── test_capital_recurrence.py       # Spec 053 — unchanged
│   ├── test_probability_bounds.py       # Spec 054 — unchanged
│   ├── test_wealth_heat_bounds.py       # Spec 054 — unchanged
│   ├── test_simplex_pipeline.py         # Spec 054 — unchanged
│   ├── test_alpha_smoothing.py          # Spec 054 — unchanged
│   ├── test_edge_mode_trajectory.py     # NEW — US1 (P1)
│   ├── test_community_membership_lint.py  # NEW — US2 (P1)
│   ├── test_frozen_discipline.py        # NEW — US3 (P2)
│   └── test_round_trip_identity.py      # NEW — US4 (P3)
├── strategies/                          # Existing from Spec 053 / 054
│   ├── hex_grid.py                      # Spec 053 — unchanged
│   ├── od_matrix.py                     # Spec 053 — unchanged
│   ├── dpd_state.py                     # Spec 053 — unchanged
│   ├── capital_stock.py                 # Spec 053 — unchanged
│   ├── worldstate.py                    # MODIFY — add `worldstate_with_community_node_strategy`
│   ├── probability_field.py             # Spec 054 — unchanged
│   ├── alpha_coefficient.py             # Spec 054 — unchanged
│   ├── consciousness_simplex.py         # Spec 054 — unchanged
│   ├── edge_mode_evidence.py            # NEW — synthesized evidence-event triples (US1 branch a)
│   └── primitives.py                    # MODIFY — extend Relationship strategy to cover all EdgeType values (US4 acceptance scenario 3)
└── harness/                             # Existing from Spec 054
    ├── __init__.py                      # MODIFY — re-export `topology_harness`, `frozen_audit`, `model_class_registry`
    ├── bound_harness.py                 # Spec 054 — unchanged
    ├── crisis_inspector.py              # Spec 054 — unchanged
    ├── probability_discovery.py         # Spec 054 — unchanged
    ├── alpha_discovery.py               # Spec 054 — unchanged
    ├── system_registry.py               # Spec 054 — REUSED for US1 observed branch + US2 + US3
    ├── topology_harness.py              # NEW — TopologyInvariantHarness runner
    ├── frozen_audit.py                  # NEW — id() snapshot + post-tick identity check (US3)
    └── model_class_registry.py          # NEW — discovers state-bearing Pydantic model classes
                                         #       under babylon.models.entities + babylon.models.world_state

src/babylon/engine/invariants.py         # MODIFY — add `EdgeModeTrajectoryLegal`, `NoCommunityFanOut`
                                         #          alongside `NonNegativeWealth`, `HeatNonNegativity`,
                                         #          `ProbabilityInRange`, `SimplexPreserved`

src/babylon/engine/systems/*.py          # MODIFY (per-System, on-demand) — add
src/babylon/models/entities/*.py         # `bypasses_topology_invariant: ClassVar[dict[str, str]] = {…}`
                                         # markers ONLY for Systems / models that the harness empirically
                                         # finds violate a predicate legitimately. Default-deny —
                                         # most Systems / models will not need a marker.
```

**Structure Decision**: This is a testing-infrastructure feature; the new
artifacts live almost entirely under `tests/property/`, mirroring the
Spec 054 layout. The only changes to `src/` are (a) two new concrete
`Invariant` implementations in `engine/invariants.py` and (b) opt-out
markers on the small set of Systems / models that the harness empirically
finds need them. The `harness/` directory was created in Spec 054; this
feature adds three modules to it
(`topology_harness.py`, `frozen_audit.py`, `model_class_registry.py`)
and reuses `system_registry.py` and the `_iter_worldstate_collections`
helper without modification. No new third-party dependencies; no changes
to `pyproject.toml`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Section intentionally empty.
