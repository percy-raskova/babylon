# Implementation Plan: Property-Based Tests for Conservation Invariants

**Branch**: `053-conservation-invariants` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/user/projects/game/babylon/specs/053-conservation-invariants/spec.md`

## Summary

Add Hypothesis-driven property tests for five conservation invariants of the simulation engine: (1) c+v+s value conservation across non-creating systems (default-deny via a `creates_value` class marker, tested both per-system and via full `run_tick()`); (2) H3 hierarchical sum conservation across res-7 → res-6 → res-5 (the sheaf gluing condition); (3) variable-capital conservation under LODES OD circulation; (4) D-P-D′ cohort population conservation modulo births and deaths; (5) capital-stock perpetual-inventory recurrence `K_{t+1} = (1−δ) K_t + I_t`. The technical approach is purely additive: five new test files under `tests/property/invariants/` reuse the spec-040 strategy infrastructure under `tests/property/strategies/` (extended with hex-grid, OD-matrix, DPDState, and capital-stock strategies), plus a small `creates_value: ClassVar[bool]` marker added to each system class in the canonical pipeline. No production code semantics change; this work installs a falsifiability harness that catches silent value/population/capital regressions during refactors.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Hypothesis ^6.149.0 (already in `[tool.poetry.group.dev.dependencies]`), pytest 8.x, NetworkX 3.x, SciPy (sparse matrices for OD), Pydantic 2.x (frozen models). XGI 0.10 is available but not required for this work.
**Storage**: N/A at runtime. The Hypothesis example database persists generated counterexamples under `.hypothesis/` (already in `.gitignore` via `[tool.pytest.ini_options]` `cache_dir` settings).
**Testing**: pytest with the existing markers `unit`, `math`, `topology`. Property tests will be tagged `unit` so they run in `mise run test:unit`. Slow variants gated behind a new `slow` keyword filter (no new marker required, just a Hypothesis `settings(max_examples=...)` profile).
**Target Platform**: Linux (CI + developer workstations). No platform-specific code.
**Project Type**: Test infrastructure (single project). No new top-level package.
**Performance Goals**: <60 seconds total wall-clock for the five new test files in the `mise run test:unit` gate. Default `max_examples=100` per `@given`; slow profile `max_examples=500` runs out-of-band. The 60-second budget is achieved via Hypothesis's default size-biased shrinking — most generated examples remain small (1–10 hexes), and the upper-bound stress regime (up to 25 000-hex grids matching the Article IV statewide-Michigan scale) is exercised occasionally on the default profile and exhaustively on the `slow` profile. The budget is therefore an expectation under size-biased generation, not a flat per-example time bound.
**Constraints**: Deterministic given Hypothesis seed (no wall-clock, no unseeded random). No network access. No mutation of `src/babylon/` semantics (only the additive `creates_value` class marker).
**Scale/Scope**: Five new strategy modules (4 new files under `tests/property/strategies/` plus an extension to the existing `worldstate.py`), two new conftest fixtures (`service_container_fixture`, `tick_context_fixture`), ~27 single-line `creates_value: ClassVar[bool]` marker additions across engine system classes (~22) AND substrate computer classes (~5), 5 new test files under `tests/property/invariants/` (~150–250 lines each), and 62 tasks total across 8 phases. No production-code semantic changes — the markers are class-level constants only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Tier | Compliance |
|-----------|------|------------|
| **III.7 Determinism Hash and Replayability** | P0 | ✅ Hypothesis is deterministic given a seed; the example database enables exact replay of past failures. The property tests *enforce* III.7 by asserting that the same generated input always produces the same output. |
| **III.2 Falsifiability Required** | P1 | ✅ Each property test IS the falsifiability machinery: prediction (the invariant), null hypothesis (a bug introduces drift), distinguishing observable (sum mismatch beyond tolerance), falsifying data (the shrunk counterexample). This work makes III.2 operational rather than aspirational. |
| **III.8 Aleksandrov Test (Structural Provenance)** | P0 | ✅ All five invariants trace to material relations: c+v+s = labor-value content (Marx Vol I); H3 sheaf = spatial aggregation gluing on the immutable substrate; circulation v = wage flow following commute (Vol II realization); population = D-P-D′ cohort biology; K_t recurrence = perpetual-inventory method (Hulten 1990). No ungrounded operators. |
| **III.1 No Magic Constants** | P1 | ✅ Tolerances are derived from numerical analysis (`max(1e-10, 1e-11 * N)` from documented sparse-multiply error proportionality), not magic numbers. Bounds for K/δ/I are physical (`K ≥ 0`, `δ ∈ [0, 1]`, `I ≥ 0`). |
| **II.6 State is Data, Engine is Transformation** | P1 | ✅ Tests verify this exact principle — they compare pre-step `WorldState` against post-step `WorldState` and assert the engine transformation conserves the named quantity. |
| **I.20 Spatial Substrate Immutable** | P1 | ✅ The H3 hierarchical-sum invariant is a direct test that no system silently mutates the substrate's resolution structure. Strengthens, does not weaken. |
| **IV Michigan Test Case** | P1 | ✅ Property tests are scope-agnostic: generators produce grids of varying size, including subsets representative of the Michigan 83-county case. Works at any scale. |
| **II.11 Subsystem Table Ownership** | P1 | ✅ Tests read state via existing accessors only; no direct table reads, no cross-subsystem mutation. |
| **I.19 Dialectic Primitive** | P0 | ✅ Tests operate on substrate-level state (HexGrid, DPDState, K) and on derived totals (sum c+v+s). Do not redefine or store derived quantities. |

**Result**: PASS — no violations. This work strengthens P0 principles III.7 and III.8 by providing automated, replayable falsification machinery. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/053-conservation-invariants/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (one invariant predicate per file)
│   ├── value_conservation.md
│   ├── h3_hierarchical.md
│   ├── circulation_v.md
│   ├── population_lifecycle.md
│   └── capital_recurrence.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (created by /speckit.specify)
├── spec.md              # Feature specification (created by /speckit.specify)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
tests/property/
├── conftest.py                            # existing — EXTEND with service_container_fixture + tick_context_fixture (T014b)
├── strategies/
│   ├── primitives.py                      # existing — reused
│   ├── worldstate.py                      # existing — EXTEND with worldstate_with_hexes_strategy (T014a)
│   ├── hex_grid.py                        # NEW — HexGrid, HexEconomicState, parent-pointer maps; up to 25 000 hexes from MICHIGAN_RES7_SEED_CELLS (T011)
│   ├── od_matrix.py                       # NEW — sparse OD matrix generators (identity / empty_rows / dense / random; density ≤ 0.01 at large N) (T012)
│   ├── dpd_state.py                       # NEW — DPDState cohort distributions across hexes (T013)
│   └── capital_stock.py                   # NEW — (K_t, δ, I_t) triples within physical bounds (T014)
└── invariants/
    ├── test_invariant_harness.py          # existing — reused for harness conventions
    ├── test_value_conservation.py         # NEW — User Story 1 (per-substrate-computer + per-engine-system + full-pipeline = 3 predicates)
    ├── test_h3_hierarchical.py            # NEW — User Story 2 (sheaf gluing res-7 → res-6 → res-5)
    ├── test_circulation_v.py              # NEW — User Story 3 (LODES OD invariance)
    ├── test_population.py                 # NEW — User Story 4 (DPDState cohort accounting)
    └── test_capital_recurrence.py         # NEW — User Story 5 (perpetual-inventory recurrence via DepreciationConfig.next_K)

src/babylon/engine/systems/                # ENGINE-side markers
├── protocol.py                            # existing — System Protocol (NO change)
├── economic.py                            # ADD: creates_value = True (ImperialRentSystem — T005)
├── struggle.py                            # ADD: creates_value = True (uprising destruction — T006)
├── dispossession_events.py                # ADD: creates_value = True (default-deny pending audit — T007)
├── decomposition.py                       # ADD: creates_value = True (default-deny pending audit — T008)
├── solidarity.py                          # ADD: creates_value = False
├── ideology.py                            # ADD: creates_value = False
├── survival.py                            # ADD: creates_value = False (read-only)
├── contradiction.py                       # ADD: creates_value = False
├── territory.py                           # ADD: creates_value = False (eviction handled via dispossession_events)
├── production.py                          # ADD: creates_value = False (engine-side ProductionSystem)
├── lifecycle.py                           # ADD: creates_value = False
├── metabolism.py                          # ADD: creates_value = False
└── ...                                    # remaining ~10 systems (community, ooda, edge_transition, …): creates_value = False (T009 glob-driven)

src/babylon/economics/substrate/           # SUBSTRATE-side markers (NEW SCOPE — T009a)
├── production.py                          # ADD: DefaultHexProductionComputer.creates_value = False (observes; per spec)
├── circulation.py                         # ADD: DefaultHexCirculationComputer.creates_value = False (row-stochastic conservation by construction)
├── aggregation.py                         # ADD: DefaultResolutionAggregator.creates_value = False (sum aggregation)
├── equalization.py                        # ADD: DefaultHexEqualizationComputer.creates_value = False (default-deny)
└── ground_rent.py                         # ADD: creates_value = False (default-deny; flip if audit shows otherwise)

tests/unit/economics/substrate/
├── conftest.py                            # existing — reused (hydrated_hex_grid, MockCommuterFlowSource)
├── test_conservation.py                   # existing — preserved as regression (FR-009)
├── test_aggregation.py                    # existing — preserved as regression (FR-009)
└── test_circulation.py                    # existing — preserved as regression (FR-009)
```

**Structure Decision**: Single project, additive-only. New work lives under `tests/property/{strategies,invariants}/` following the spec-040 convention. The only `src/` changes are `creates_value: ClassVar[bool]` markers on engine system classes AND substrate computer classes — no semantic changes to either. Engine systems (`src/babylon/engine/systems/*.py`) operate on `nx.DiGraph[str]` with `wealth` attributes; substrate computers (`src/babylon/economics/substrate/*.py`) operate on `HexGrid` and own all c+v+s mutations. The c+v+s conservation invariant therefore tests substrate computers directly (per-computer parametrize) and asserts engine systems don't touch hex state at all (per-engine-system parametrize). The actual `True`/`False` value per class is decided in Phase 0 research (research.md R1/R2) and seeded in data-model.md §2.

## Complexity Tracking

> **Empty — Constitution Check passed with no violations.**

No deviations from constitutional principles. The work strengthens P0 principles III.7 (Determinism) and III.8 (Aleksandrov) and is purely additive to the test suite plus a single-line per-class marker.
