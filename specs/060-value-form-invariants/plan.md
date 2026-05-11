# Implementation Plan: Marx Value-Form Invariants

**Branch**: `060-value-form-invariants` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/060-value-form-invariants/spec.md`

## Summary

Add a property/metamorphic test bundle that asserts seven cross-domain
invariants on the simulation engine: numeraire invariance, MELT-mediated
per-entity consistency, TSSI/NI aggregate value-price equalities, OCC-
conditional wage-shock asymmetry, productivity-shock value-price
decoupling, software metamorphic invariants (UUID relabeling, serialization
round-trip, Markovian step semantics, H3 round-trip), and Marxist sign /
monotonicity invariants (proportional c+v scaling, OCC monotonicity, Volume
III equalization variance reduction).

All seven user stories are test-only additions. The implementation:

- Adds new tests under `tests/integration/economics/test_invariants_*.py`
  and `tests/property/test_invariants_*.py` (and a few unit-level lifts to
  `tests/unit/economics/melt/`).
- Adds shared helpers under `tests/_helpers/invariants/` (monetary
  rescaling, UUID relabeler, transformation-mode probe, etc.).
- Registers one new pytest marker (`invariant`) in `pyproject.toml`.
- Permits at most one production-side change: a named H3 disaggregation
  rule constant under `babylon.config` if the engine has none today
  (FR-011 exception). Code-level investigation shows the engine has a real
  capital-migration mechanism (`economics/substrate/equalization.py` with
  a conservation proof in its docstring), a real
  `TransformationDialectic` (`engine/dialectics/transformation.py`), and a
  real MELT calculator (`DefaultMELTCalculator`); none of these need
  changing.

The bundle's load-bearing constraint: `mise run sim:trace 200` MUST remain
byte-identical to the pre-spec-060 baseline (the regression-guard inherited
from spec 059 SC-007 / spec 058's byte-equality discipline).

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard).

**Primary Dependencies**:
- Pydantic 2.x (frozen `WorldState`, `ValueTensor4x3`, `HexEconomicState`)
- NetworkX 3.x (`WorldState.to_graph()` / `from_graph()`, GraphProtocol via
  `NetworkXAdapter`)
- h3 4.2 (`h3.cell_to_parent`, `h3.cell_to_children`, already used in
  `infrastructure/r8_mesh.py` and `economics/substrate/spatial.py`)
- Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since
  spec 053)
- pytest 8.x with existing markers

**Storage**: N/A — fully in-memory. Tests use existing `WorldState` and
`HexGrid`; no new database tables, no new file formats, no persistence
round-trips beyond Pydantic `model_dump_json` ↔ `model_validate_json`.

**Testing**:
- pytest with new marker `@pytest.mark.invariant` (and existing
  `@pytest.mark.property` for Hypothesis-driven tests)
- Fast gate: `mise run test:unit` + `mise run test:int`
- Bundle run: `poetry run pytest -m invariant`
- Hypothesis derandomization: `derandomize=true` in CI mode (per spec 053
  convention); `.hypothesis/` example DB already gitignored

**Target Platform**: Linux x86_64 (CI parity); macOS development.

**Project Type**: Test addition to existing Python library
(`src/babylon/`). No new project, no new package, no new CLI entry point.

**Performance Goals**:
- Each per-tick test: < 10 s wall clock (FR-009)
- US7(c) Volume III long-run test (50 ticks): < 60 s (FR-009)
- Full `-m invariant` bundle: < 120 s (SC-006)
- Hypothesis property tests: 100 examples per CI invocation (FR-002)

**Constraints**:
- Test-only. No `src/babylon/` behavioral changes (FR-011).
- `mise run sim:trace 200` byte-identical to baseline (FR-012, SC-008).
- Tolerances: 1e-15 (US6 UUID/Markov), 1e-12 (US1 numeraire, US7 propor-
  tional scaling), 1e-9 (US2 per-entity MELT, US6 H3 round-trip), 1e-6 (US3
  TSSI aggregates).
- All assertions emit diagnostic strings naming offending entity + delta
  magnitude (FR-010).

**Scale/Scope**:
- 7 user stories, 22 functional requirements, 16 success criteria.
- Estimated 12–15 new test files; 6–8 shared helper modules; ~1,500–2,500
  LOC of test code.
- Skip footprint at landing: ≤ 5 SKIPs (US3-redistribution-arm, US4, US5,
  US7-c when migration inactive, US2-NoDataSentinel) per SC-007.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **II.6 State is Data, Engine is Transformation** | ✅ Aligned | FR-015 Markovian step semantics directly asserts the pure-function property required by this principle. |
| **III.1 No Magic Constants** | ✅ Aligned | Every tolerance (1e-15, 1e-12, 1e-9, 1e-6) is traced to either IEEE-754 precision in the documented scale band, or to a stated Marxian-theoretical bound (US3 aggregate equality). No magic floats; all named with rationale in the spec. |
| **III.2 Falsifiability Required** | ✅ Aligned | Every invariant has explicit prediction (the equality / sign / monotone claim), null hypothesis (drift > tolerance), distinguishing observable (the relative-error magnitude), and falsifying outcome (the test failure). Spec acceptance scenarios already document all four parts. |
| **III.3 Physics Cosplay Prohibition** | ✅ Reinforced | The entire bundle exists *because of* this principle: it ensures tensor notation `c/v`, `s/v`, `c+v`, `s + c + v`, `× τ` earns its keep through actual invariance. The principle reads as the spec's mission statement. |
| **III.4 Data Source Traceability** | ✅ Aligned | Tests use only validation-fixture scenarios (`two_node`, `wayne_county`); no runtime data. Hypothesis-generated configurations are explicitly scoped via property-test domain. No new data source enters the catalog. |
| **III.5 Empirical vs Strategic Separation** | ✅ Aligned | The invariants hold for both empirical-material configurations (FIPS-real QCEW-hydrated scenarios) and synthetic strategic configurations (Hypothesis-generated). The bundle does not embed strategic content in empirical fixtures or vice versa. |
| **VIII.4 Ungrounded Tensor Notation** | ✅ Reinforced | This bundle is the direct remediation for the named anti-pattern. |
| **VIII.5 Claims Without Falsifiability** | ✅ Reinforced | Every claim made by the existing MELT, tensor, and transformation modules becomes falsifiable via this bundle. |
| **I.19 Dialectic as Primitive** | ✅ Aligned | The three dialectic invariants (weight bound, type stability, step type-correctness) are *not* in scope for spec 060 — they belong to a different layer of testing (dialectic-level). Spec 060 tests the **value-form layer** sitting atop the dialectic substrate. The two layers are orthogonal: spec 053 / 054 / 055 / 056 / 060 form the property-test stack at successive layers. |
| **VI Scope Control: Material Base First** | ✅ Aligned | The invariants test the material base (c, v, s, τ, prices, hex aggregates), not the superstructure. Edge mode and consciousness are not touched. |

**No constitutional violations.** Constitution Check passes. Proceeding to
Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/060-value-form-invariants/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── invariant_test_contracts.md
│   ├── transformation_mode_probe.md
│   ├── monetary_rescaling.md
│   └── uuid_relabeler.md
├── checklists/
│   └── requirements.md  # Already written (/speckit.specify output)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

The bundle is **test-only**. Source-tree additions and edits:

```text
src/babylon/
└── config/
    └── h3_splitter.py    # NEW (optional, FR-016 / FR-011 exception):
                          # declares H3SplitterRule enum + per-quantity
                          # rule registry. Only added IF investigation in
                          # Phase 0 confirms no equivalent exists. ~50 LOC.

tests/
├── _helpers/
│   └── invariants/                   # NEW shared helpers
│       ├── __init__.py
│       ├── monetary_rescaling.py     # rescale_currency_fields(world, k)
│       ├── uuid_relabeler.py         # relabel_uuids(world, alias_fn)
│       ├── transformation_mode.py    # probe_transformation_mode()
│       ├── serialization.py          # roundtrip_via_json(world)
│       ├── h3_round_trip.py          # rollup_and_disaggregate()
│       ├── productivity_shock.py     # halve_snlt_in_sector()
│       └── variance_trace.py         # ProfitRateVarianceTrace
│
├── property/                                       # NEW directory
│   ├── test_numeraire_invariance.py                # FR-001, FR-002
│   ├── test_aggregate_equalities.py                # FR-005 (property variant)
│   └── test_proportional_scaling.py                # FR-017 (property variant)
│
├── integration/economics/
│   ├── test_melt_consistency.py                    # FR-003, FR-004
│   ├── test_wage_occ_asymmetry.py                  # FR-006
│   ├── test_productivity_shock_decoupling.py       # FR-007
│   ├── test_uuid_relabel_invariance.py             # FR-013
│   ├── test_serialization_roundtrip.py             # FR-014
│   ├── test_markovian_step.py                      # FR-015
│   ├── test_h3_round_trip.py                       # FR-016
│   ├── test_occ_monotonicity.py                    # FR-018
│   └── test_volume_iii_equalization.py             # FR-019
│
└── unit/economics/melt/
    └── (no new files; verify existing                 # FR-003 prerequisite
         test_melt_calculator.py coverage)              audit only

pyproject.toml                  # EDIT: register "invariant" marker
```

**Structure Decision**: Single-project test addition. Helpers live under
`tests/_helpers/invariants/` (sibling of existing `tests/factories/`,
`tests/constants.py`). The one allowed production-side change is the
named `H3SplitterRule` constant in `src/babylon/config/h3_splitter.py`
ONLY IF Phase 0 confirms no equivalent exists in
`src/babylon/economics/substrate/` or `src/babylon/infrastructure/`.

## Phase 0: Research

NEEDS CLARIFICATION items discovered during spec authoring → research
tasks:

1. **H3 disaggregation rule** — Does the engine have a named, single-
   source-of-truth disaggregation rule for spatial round-trips? If yes,
   reuse it. If no, declare one (FR-011 exception).
2. **Capital migration mechanism** — Is there an active capital-migration
   step the engine runs each tick? If yes, US7(c) runs against it. If no,
   US7(c) SKIPs cleanly.
3. **TransformationDialectic state** — Is the engine in proportional-
   prices mode or full-redistribution mode? Determines what US3/US4/US5
   do (run vs. skip).
4. **WorldState equality semantics** — How is `WorldState` equality
   defined? Round-trip identity in FR-014 needs an authoritative
   definition.
5. **UUID-typed fields inventory** — Which fields on `WorldState` and its
   nested models carry opaque string IDs? FR-013 needs the full list to
   build the relabeler.
6. **Scenario builders** — Confirm the entry points for the two-county
   and Wayne County scenarios.

**Output**: `research.md` with all six clarifications resolved against
the codebase, each with citations to file paths and line numbers.

## Phase 1: Design & Contracts

**Prerequisites**: Phase 0 `research.md` complete.

1. **Data model** → `data-model.md`:
   - Formalize the six test-only entities from the spec
     (`MonetaryRescaling`, `ConsistencyReport`,
     `TransformationModeFlag`, `MetamorphicPair`, `UUIDRelabeler`,
     `H3SplitterRule`, `ProfitRateVarianceTrace`).
   - For each: signature, fields, invariants, sample usage.
   - Show the (test-only) Pydantic models or dataclasses; no
     production-side data model changes.

2. **Contracts** → `contracts/`:
   - `invariant_test_contracts.md` — for each of FR-001..FR-019, the
     exact contract the test asserts about engine behavior, in
     Given-When-Then form. This is the test-facing API contract.
   - `transformation_mode_probe.md` — the single helper used by all
     transformation-gated tests (FR-021). Defines the probe's return
     type and decision rule.
   - `monetary_rescaling.md` — the field-by-field rule for scaling
     monetary fields by `k` while leaving labor-time fields alone.
   - `uuid_relabeler.md` — the full inventory of ID-typed fields and
     the relabeling sweep order (FR-013).

3. **Agent context update**:
   - Run `.specify/scripts/bash/update-agent-context.sh claude`.
   - Append (or, if first-time, create) the spec 060 entry under
     "Active Technologies": Python 3.12+ test additions, Hypothesis
     usage, pytest `invariant` marker.

4. **Quickstart** → `quickstart.md`:
   - End-to-end developer flow: how to run the bundle, how to interpret
     diagnostics, how to introduce a deliberate bug to verify a test
     catches it, how to confirm byte-equality preservation.

5. **Re-evaluate Constitution Check** post-design:
   - Re-check the gates table. The expected outcome is "✅ still aligned"
     because the design is purely additive and respects the principles
     it tests (especially II.6, III.1, III.2, III.3).

## Phase 2: Tasks (output of `/speckit.tasks`)

NOT created by this command. Will be produced by `/speckit.tasks` and
will include:

- Setup: register `invariant` marker; create `tests/_helpers/invariants/`
- Foundational: build the six test-helper modules (paths above)
- US1 → US7 phase tasks (each independently testable per spec)
- Polish: README in `tests/_helpers/invariants/`, byte-equality regression
  check, post-merge ADR-038 capturing the bundle's coverage

## Complexity Tracking

> **Filled ONLY if Constitution Check has violations that must be justified**

No constitutional violations identified. Table left empty by design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(none)* | *(none)* |

## Post-Design Constitution Re-Check

After Phase 1 (research, data model, contracts, quickstart) the gates
are re-evaluated:

| Principle | Status | Phase 1 Verification |
|---|---|---|
| **II.6 State is Data, Engine is Transformation** | ✅ Still aligned | The data model adds zero new persistence; all test entities are pure dataclasses/functions. `tests/_helpers/invariants/` does not mutate engine state. |
| **III.1 No Magic Constants** | ✅ Still aligned | The one new production constant (`H3SplitterRule.UNIFORM` in `src/babylon/config/h3_splitter.py`) is rationalized in research.md R1 with citations to four existing call sites in the codebase that all use uniform splitting de facto. Not magic — codification of existing convention. |
| **III.2 Falsifiability Required** | ✅ Still aligned | Every contract in `contracts/invariant_test_contracts.md` is Given-When-Then with a numeric threshold. Each FR has a corresponding SC pegging the falsification criterion. |
| **III.3 Physics Cosplay Prohibition** | ✅ Reinforced | The 4 contract files actively enforce this principle: they demand tensor notation `c/v`, `s/v`, `c+v+s`, `× τ` survive empirical metamorphic perturbations. |
| **III.4 Data Source Traceability** | ✅ Still aligned | Test scenarios `TwoNodeScenario` and `WayneCountyScenario` are validation fixtures (not runtime data sources). No new data sources added to the catalog. |
| **VIII.4 Ungrounded Tensor Notation** | ✅ Reinforced | The bundle is the named remediation. |
| **VIII.5 Claims Without Falsifiability** | ✅ Reinforced | Every existing claim about MELT, tensor, transformation modules becomes testable per `contracts/invariant_test_contracts.md`. |

**No new violations.** **No design changes required to satisfy the
constitution.** Phase 1 design is consistent with the pre-research
Constitution Check. Proceeding to /speckit.tasks.

## Generated Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Plan | `specs/060-value-form-invariants/plan.md` | This file |
| Research | `specs/060-value-form-invariants/research.md` | 6 NEEDS CLARIFICATION resolved with file:line citations |
| Data model | `specs/060-value-form-invariants/data-model.md` | 1 prod entity (`H3SplitterRule`) + 7 test-only entities |
| Test contracts | `specs/060-value-form-invariants/contracts/invariant_test_contracts.md` | FR-by-FR Given-When-Then |
| Transformation probe contract | `specs/060-value-form-invariants/contracts/transformation_mode_probe.md` | FR-021 single source of truth |
| Monetary rescaling contract | `specs/060-value-form-invariants/contracts/monetary_rescaling.md` | FR-001/FR-002 helper |
| UUID relabeler contract | `specs/060-value-form-invariants/contracts/uuid_relabeler.md` | FR-013 helper |
| Quickstart | `specs/060-value-form-invariants/quickstart.md` | End-to-end dev flow + deliberate-bug recipes |
| Agent context | `CLAUDE.md` | Auto-updated by `update-agent-context.sh claude` |
