# Implementation Plan: Bound Invariants — Property-Based Tests

**Branch**: `054-bound-invariants` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/054-bound-invariants/spec.md`

## Summary

Convert four bound-invariant predicates that the engine declares but does not
exhaustively test — `Probability ∈ [0, 1]`, `Wealth ≥ 0` and `Heat ≥ 0`,
the ternary simplex `r + l + f = 1`, and the α-smoothing EMA inequality —
into Hypothesis-driven property tests. Each predicate becomes a single
parametrized test file under `tests/property/invariants/` that mirrors the
Spec 053 conservation harness: project-wide profile registration, magnitude-
aware tolerance helper, default-deny + opt-out marker pattern. The new tests
runs in the `mise run test:unit` fast gate (default profile, ≤ 30 s) and a
slow profile (`HYPOTHESIS_PROFILE=slow`, ≤ 5 min) for nightly / pre-release
sweeps. Two new concrete `Invariant` implementations are added to
`src/babylon/engine/invariants.py` (`ProbabilityInRange`, `SimplexPreserved`)
alongside the existing `NonNegativeWealth` / `HeatNonNegativity`.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models), NetworkX 3.x (graph protocol)
**Storage**: N/A — `.hypothesis/` example DB persists generated counterexamples (already in `.gitignore`)
**Testing**: pytest with `@pytest.mark.unit` markers; profile registration in `tests/conftest.py` (project-wide) and `tests/property/conftest.py` (per-package) per Spec 053 pattern
**Target Platform**: `mise run test:unit` (default fast gate) + `HYPOTHESIS_PROFILE=slow` (nightly / pre-release)
**Project Type**: Testing infrastructure extending the existing `tests/property/` module
**Performance Goals**: 4 invariant test files complete in ≤ 30 s on default profile (max_examples=100, derandomize=True); ≤ 5 min on slow profile (max_examples=500); per-System trace fits in standard pytest verbose output
**Constraints**: Must reuse Spec 053's harness style (magnitude-aware tolerance helper, profile pattern, `@composite` strategies, opt-out ClassVar markers); zero new third-party dependencies; deterministic on default profile; failure messages must point at offending field, entity ID, and System / formula
**Scale/Scope**: 21 Systems × random `WorldState` (US2); ≈ 10–20 `Probability`-typed fields auto-discovered across `src/babylon/models/` (US1); ≈ 17 formulas in `src/babylon/formulas/` filtered by return type (US1); ≈ 8–12 α-smoothed coefficients auto-discovered from `defines.py` (US4); 5 consecutive ticks for simplex drift (US3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Tier | Compliance |
|-----------|------|------------|
| **III.2 Falsifiability Required** | P1 | **PASS — direct alignment.** Each bound invariant becomes a Hypothesis-driven falsifiability harness. Predictions are encoded as predicates; falsifying observations are Hypothesis-shrunk minimal examples. |
| **III.7 Determinism Hash and Replayability** | P0 | **PASS.** Default profile uses `derandomize=True` (per Spec 053 convention); a failing Hypothesis seed is reproducible across runs. Tests do not introduce engine non-determinism. |
| **III.8 Aleksandrov Test (Structural Provenance)** | P0 | **PASS — explicit alignment table in research.md §6.** Each of the four invariants ties to a material relation: Probability bounds encode survival-probability semantics (P(S\|A) cannot exceed certainty); Wealth/Heat non-negativity encodes physical-resource semantics; simplex constraint encodes mass-conservation of consciousness routing across `{r, l, f}`; α-smoothing encodes II.4 Quantities-vs-Coefficients (coefficients smooth, quantities flux). |
| **II.4 Quantities vs Coefficients** | P2 | **PASS — US4 is the codification.** "Crisis = discontinuous coefficient reset, not gradual drift" is exactly what US4 asserts via the suspend-in-crisis contract. |
| **II.6 State is Data, Engine is Transformation** | P1 | **PASS.** Tests operate on frozen `WorldState` instances; harnesses observe pre/post pairs without mutating engine internals. |
| **II.11 Subsystem Table Ownership** | P1 | **N/A — no DB I/O.** Tests are pure in-memory; no cross-subsystem table reads. |
| **I.20 Spatial Substrate Immutable** | P0 | **PASS — substrate is read-only.** Tests do not mutate hex grid; US3 multi-tick variant respects substrate immutability via the same `WorldState.from_graph` round-trip the production engine uses. |
| **V Verb Atomicity** | P0 | **N/A — no verb invocation.** Tests exercise Systems, not player verbs. |

**Gate decision (Phase 0 pre-research): PASS.** No constitutional violations, no `[TRANSITION STATE]` principles in scope, no Amendment proposals required. Proceed to Phase 0.

**Re-evaluation (post-Phase 1 design): PASS.** The design (`data-model.md` + four contracts in `contracts/`) introduces:

- Two new `Invariant` Protocol implementations (`ProbabilityInRange`, `SimplexPreserved`) — both consume `WorldState` only, mutate nothing.
- A `BoundInvariantHarness` that observes `(pre, post)` pairs — no engine mutation.
- Auto-discovery walkers (`probability_discovery.py`, `alpha_discovery.py`, `system_registry.py`) — read-only over `src/babylon/models/`, `src/babylon/config/defines.py`, and `src/babylon/engine/systems/`.
- Hypothesis strategies (`tests/property/strategies/`) — produce frozen test inputs.

Nothing in the design adds primitives (no new dialectic types, morphism relations, transport edge types), mutates substrate (I.20), introduces non-determinism (default profile `derandomize=True`), uses magic constants (tolerances derived; alphas from `defines.py`), produces unfalsifiable formalism (each invariant has a falsification predicate), invokes AI adjudication (II.5), reads cross-subsystem tables (II.11), or depends on `[TRANSITION STATE]` principles. Aleksandrov Test trace is documented in `research.md §6`. Proceed to Phase 2 (`/speckit.tasks`).

## Project Structure

### Documentation (this feature)

```text
specs/054-bound-invariants/
├── plan.md                              # This file (/speckit.plan command output)
├── spec.md                              # Already written (/speckit.specify + /speckit.clarify)
├── research.md                          # Phase 0 output — patterns + decisions
├── data-model.md                        # Phase 1 output — entities, attributes, relationships
├── quickstart.md                        # Phase 1 output — how to run + interpret failures
├── contracts/                           # Phase 1 output — per-invariant predicate contracts
│   ├── probability_bounds.md
│   ├── wealth_heat_bounds.md
│   ├── simplex_pipeline.md
│   └── alpha_smoothing.md
├── checklists/
│   └── requirements.md                  # Already written (spec quality checklist)
└── tasks.md                             # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code (repository root)

```text
tests/property/
├── conftest.py                          # MODIFY — add bound-invariant fixtures only if Spec 053
│                                        #          fixtures are insufficient (default: reuse as-is)
├── invariants/                          # Existing directory from Spec 053
│   ├── test_value_conservation.py       # Spec 053 — unchanged
│   ├── test_h3_hierarchical.py          # Spec 053 — unchanged
│   ├── test_circulation_v.py            # Spec 053 — unchanged
│   ├── test_population.py               # Spec 053 — unchanged
│   ├── test_capital_recurrence.py       # Spec 053 — unchanged
│   ├── test_probability_bounds.py       # NEW — US1 (P1)
│   ├── test_wealth_heat_bounds.py       # NEW — US2 (P2)
│   ├── test_simplex_pipeline.py         # NEW — US3 (P2)
│   └── test_alpha_smoothing.py          # NEW — US4 (P3)
├── strategies/                          # Existing directory from Spec 053
│   ├── hex_grid.py                      # Spec 053 — unchanged
│   ├── od_matrix.py                     # Spec 053 — unchanged
│   ├── dpd_state.py                     # Spec 053 — unchanged
│   ├── capital_stock.py                 # Spec 053 — unchanged
│   ├── worldstate.py                    # MODIFY — add `worldstate_with_probability_fields_strategy`
│   │                                    #          and `worldstate_with_simplex_consciousness_strategy`
│   ├── probability_field.py             # NEW — Pydantic introspection + value strategy
│   ├── alpha_coefficient.py             # NEW — `(prev, raw, alpha)` triple strategy
│   └── consciousness_simplex.py         # NEW — re-export `simplex_points()` for invariant tests
└── harness/                             # NEW directory
    ├── __init__.py
    ├── bound_harness.py                 # NEW — `BoundInvariantHarness` runner
    ├── crisis_inspector.py              # NEW — `CrisisStateInspector` (steady vs crisis classifier)
    ├── probability_discovery.py         # NEW — Pydantic `model_fields` walker
    ├── alpha_discovery.py               # NEW — `defines.py` field-name heuristic
    └── system_registry.py               # NEW — auto-discovers `src/babylon/engine/systems/*.py`

src/babylon/engine/invariants.py         # MODIFY — add `ProbabilityInRange`, `SimplexPreserved`
                                         #          alongside `NonNegativeWealth`, `HeatNonNegativity`

src/babylon/engine/systems/*.py          # MODIFY (per-System, on-demand) — add
                                         # `bypasses_bound_invariant: ClassVar[dict[str, str]] = {…}`
                                         # markers ONLY for Systems that the harness empirically
                                         # finds violate a predicate legitimately. Default-deny —
                                         # most Systems will not need a marker.

src/babylon/formulas/*.py                # MODIFY (per-formula, on-demand) — same as above for
                                         # any formula returning `Probability` that legitimately
                                         # produces an unwrapped intermediate value.
```

**Structure Decision**: This is a testing-infrastructure feature; the new
artifacts live entirely under `tests/property/`, mirroring the Spec 053
layout. The only changes to `src/` are (a) two new concrete `Invariant`
implementations in `engine/invariants.py` and (b) opt-out markers on the
small set of Systems / formulas that the harness empirically finds need
them. The `harness/` directory is new — Spec 053 inlined harness logic
into the test files; this spec extracts it into reusable modules because
four invariants share more cross-cutting plumbing (Pydantic introspection,
crisis classification, System registry) than five conservation invariants
did.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Section intentionally empty.
