# Implementation Plan: End-to-End Leontief Imperial Rent Integration

**Branch**: `057-leontief-rent-integration` | **Date**: 2026-05-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/057-leontief-rent-integration/spec.md`

## Summary

Spec 057 wires `ProductionChainRentCalculator` end-to-end so the simulation actually computes per-county imperial rent (`phi_hour`) every tick. The previous per-worker TVT calculator was deleted in commit `a5f73139` and `_compute_imperial_rent` was stubbed to write `0.0` everywhere "until tensor integration." This feature is that tensor integration.

**Technical approach**: (1) Implement two missing data-source `Default*` classes (`DefaultPeripheryLaborCoefficientsSource`, `DefaultFinalDemandSource`) as `CachedSource[T]` subclasses per the Spec 058 protocol_kit pattern; (2) implement `IndustryToCountyAllocator` (also `CachedSource[T]`) that converts per-industry rent vectors into per-county `phi_hour` via QCEW employment-share weighting with a 5-year carry-forward fallback; (3) extract the new pipeline body into a focused sub-module `src/babylon/economics/tick/system/imperial_rent.py` (≤400 LOC, completing Spec 058's deferred US2 decomposition), called from a thin `TickDynamicsSystem._compute_imperial_rent` facade method that preserves the Spec 058 / FR-007 behavioral fence (return-type class, exception class hierarchy, event-bus emission ordering); (4) introduce a typed `CalibrationWarning` event family (`AxiomViolation` / `QcewCarryForward` / `PhiHourOutlier`) emitted via the existing `EventBus`; (5) register the four new components via `SourceRegistry.builtin_economics()`; (6) delete the orphaned tests against the removed per-worker `ImperialRentCalculator` and `babylon.economics.reproduction` modules.

**Periphery-wage source choice**: Penn World Tables (PWT) v10.x — it is already a constitutionally-listed data source (`data-catalog.yaml id: PWT`) so III.4 compliance is automatic. The exact extraction (PPP-adjusted real labor compensation per worker, manufacturing-and-services aggregate, periphery defined as Hickel/Sullivan/Zoomkawala 2022 "Global South" country list) is documented in research.md §R1 and embedded as the source-metadata record per FR-002. Hickel et al. 2022 is the calibration anchor for SC-004 (order-of-magnitude check).

## Technical Context

**Language/Version**: Python 3.12+ (project standard)

**Primary Dependencies** (no new dependencies introduced — entire stack already in `pyproject.toml`):

- `pydantic` 2.x (frozen `BaseModel` for `PeripheryLaborCoefficients`, `ProductionChainRentResult`, the new `CalibrationWarning` event family)
- `numpy` (already used by `production_chain_rent.py` for matrix ops; `wage_ratios`, `final_demand`, `phi_vector` are `np.ndarray`)
- `scipy.sparse` (existing — used by `ProductionChainDecomposer` for the Leontief inverse `L_d = (I − A_d)⁻¹`; per Constitution II.12 this is the matrix-computation layer)
- `sqlalchemy` 2.x (existing — for QCEW reads via the `marxist-data-3NF.sqlite` reference DB)
- `babylon.core.protocol_kit` (introduced in Spec 058 — `CachedSource[T]`, `SourceRegistry`)
- `babylon.economics.tensor.NoDataSentinel` (existing — return type for missing-data per FR-007)
- `babylon.engine.event_bus.EventBus` (existing — channel for `CalibrationWarning` events per Clarifications 2026-05-08)

**Storage**:

- SQLite (`data/sqlite/marxist-data-3NF.sqlite` — read-only at simulation runtime, source for QCEW employment-share data, BEA Use Tables, BEA inter-industry coefficients, PWT wage data)
- In-memory via the existing `GraphProtocol` (county `phi_hour` writes go to `CountyEconomicState` graph node attributes — no schema change)
- `CachedSource[T]` LRU cache (process-local, year-keyed lookups; default `cache_negative_results = True` per Spec 058)

**Testing**:

- `pytest` 8.x with the existing markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
- `mise run test:unit` + `mise run test:int` is the regression net (current baseline post-058: 9000+ passed / 186 skipped / 1 xfailed / 0 failures / 0 errors, with the spec-057 quarantine still in place — those skip markers UNSKIP as part of this feature's test cleanup per FR-009)
- New tests (≥6 files): periphery-wage source unit tests, final-demand source unit tests, allocator unit tests (incl. carry-forward fallback), per-tick integration test (Wayne County baseline → non-zero phi_hour), behavioral-fence preservation test (`tests/integration/economics/tick/test_facade_behavioral_fence.py` — already exists from Spec 058, extended to cover the new sub-module), `CalibrationWarning` event emission tests
- Doctest examples in the new sub-module's module docstring per project standard

**Target Platform**: Linux dev (Debian 13) + CI (whatever the project's CI runs); no platform-specific code

**Project Type**: Single Python project with monorepo layout (`src/babylon/...`, `tests/...`, `specs/...`)

**Performance Goals**:

- SC-005 — new pipeline unit tests stay under 5 seconds per file (does not push fast `mise run check` gate beyond budget)
- **Per-tick performance budget** (research.md §R3): the Leontief decomposition + import-content matrix `M = A_m @ L_d` is computed once per (year, BEA matrix vintage) and cached — repeated calls within the same simulation year are O(1) cache hits. Per-tick cost is dominated by the per-county allocation step (3,000+ counties × ~71 BEA industries = ~213,000 multiply-adds per tick), expected wall-clock ≤ 100ms after cache warm-up (validated by a new performance smoke test in `tests/integration/economics/tick/test_imperial_rent_perf.py`)

**Constraints**:

- **Behavioral fence on `tick/system/`**: identical return-type classes, exception class hierarchies, event-bus emission ordering for `_compute_imperial_rent` (FR-001 + FR-007 carryover from Spec 058 — verified by the existing behavioral-snapshot test extended to cover the new sub-module)
- **400-LOC cap on `tick/system/imperial_rent.py`** (FR-001, completing Spec 058 / SC-002)
- **Public field stability**: `CountyEconomicState.phi_hour` keeps its float scalar shape; downstream `savings_schedule.py` and `accumulation.py` formulas unchanged (FR-011)
- **No-data signal contract**: every new source returns `NoDataSentinel` for missing-data, never raises (FR-007 per Clarifications 2026-05-08)
- **Carry-forward bounded look-back**: 5 years max for QCEW gaps (FR-004 per Clarifications 2026-05-08)
- **Pass-through with warning** for periphery-wage axiom violations (FR-002 per Clarifications 2026-05-08)
- **Calibration-warning channel**: `EventBus.publish(CalibrationWarning(...))` only — not `warnings.warn`, not `logging` (FR-002, FR-004, FR-008 per Clarifications 2026-05-08)
- **Pre-existing calculator clamp** (`production_chain_rent.py:181`, `loss_ratio = np.maximum(loss_ratio, 0.0)`) is preserved — see research.md §R5 for the reconciliation with the Q3 clarification's "naturally produces a small negative rent" language

**Scale/Scope**:

- 5 user stories (3 P1, 1 P2, 1 P3), 12 functional requirements, 7 measurable success criteria
- Touched files: ~12 source files (4 NEW, 3 EDITED in `src/`; ~6 test files NEW or restructured in `tests/`)
- ~6–8 conventional commits expected (per user-story-priority grouping with TDD red-green-refactor inside each)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature implements the **central thesis of MLM-TW** (Imperial Rent Φ flowing from periphery to core, per Constitution I.2). It is the first end-to-end realization of Φ in the simulation. The Constitution Check is therefore unusually load-bearing.

### Pre-Phase-0 Gate Evaluation

**P0 (Never Drop) — relevance to Spec 057:**

| Principle | Relevance | Compliance |
|-----------|-----------|------------|
| **I.2 Imperial Rent (Φ)** | **DIRECTLY IMPLEMENTED** — Φ = unequal exchange + externalized reproduction + domestic shadow labor; this feature computes the unequal-exchange portion via Leontief decomposition + periphery-wage coefficients | ✅ pass: feature implements `Φ_j = Σᵢ M[i,j] · (w_ratio_i − 1) · y_j` end-to-end (formula already in `production_chain_rent.py`); aligns with W_c > V_c → Φ derivation. The exposed-as-`phi_hour` per-county scalar is the field that downstream savings/accumulation dynamics already read (FR-011). |
| **I.19 Dialectic Primitive** | None directly — feature does not introduce new poles or morphisms; ValueTensor4x3 is derived per Amendment A; this feature consumes the existing Leontief tensor | ✅ pass (untouched) |
| **I.20 Spatial Substrate** | **Affected** — feature operates on county FIPS codes; QCEW employment shares are spatial substrate reads | ✅ pass: feature reads QCEW spatial data via the existing reference SQLite, never mutates the spatial substrate. County FIPS are immutable per Amendment G. The carry-forward fallback (FR-004) is a temporal carry, not a spatial mutation. |
| **II.9 Morphism Dyadic** | None — feature is per-county scalar computation; flows through the dyadic morphism graph but does not define new morphisms | ✅ pass (untouched) |
| **III.7 Determinism Hash & Replayability** | **CRITICAL** — bit-identical phi_hour across runs with same seed (SC-002) is a strict requirement for III.7 | ✅ pass: cache is process-local and deterministic; Leontief decomposition is pure linear algebra; `np.float64` arithmetic is reproducible; QCEW reads return ordered FIPS+NAICS rows; carry-forward look-back is a pure function of (county, year) inputs. SC-002 explicitly tests bit-identical output across two consecutive runs. |
| **III.8 Aleksandrov Test** | **Affected** — every formal construct must trace to a material relation | ✅ pass: every operator chains to a material process. (a) BEA inter-industry flow `A` = production network (input-output coefficient matrix). (b) Import-share `m_j` = empirical fraction of input `j` sourced from imports. (c) Leontief inverse `L_d = (I − A_d)⁻¹` = total domestic production requirement. (d) Periphery wage ratio `w_core / w_periphery` = labor-time arbitrage ratio (the unequal-exchange axis). (e) Final demand `y` = consumption + investment + government + net exports. (f) QCEW employment share = labor distribution. Each is a documented material observable. No ungrounded operators. |
| **V Verb Atomicity** | None — feature is engine-internal; does not touch player or state-AI verbs | ✅ pass (untouched) |

**P1 (Load-Bearing) — relevance to Spec 057:**

| Principle | Relevance | Compliance |
|-----------|-----------|------------|
| **I.4 George Jackson Bifurcation** | **Indirect downstream** — `phi_hour` feeds `phi_adjustment` in `savings_schedule.py`, which feeds bifurcation conditions | ✅ pass: feature only changes the upstream `phi_hour` value; downstream bifurcation logic in `accumulation.py` and `savings_schedule.py` is unchanged. After this feature, P(S\|R) > P(S\|A) calculations are driven by structurally-derived rent, not a constant zero — this is the *correct* operationalization of Bifurcation. |
| **I.7 Quantitative→Qualitative** | **Affected** — `phi_hour` is a quantitative scalar (continuous float); no qualitative transitions added | ✅ pass: feature stays in the quantitative layer. Edge mode transitions (qualitative) are not touched. |
| **I.13 Principal Contradiction** | **Affected** — Imperial Rent is one of the two primary contradictions per I.2 | ✅ pass: this feature is the operationalization of Imperial Rent as a *measurable* contradiction internal (per I.14 contradiction internals). The structural derivation makes the contradiction's intensity falsifiable per III.2. |
| **II.6 State is Data, Engine is Transformation** | **Affected** — pipeline is a transformation step in the per-tick engine | ✅ pass: pipeline shape is `step(world, services, context) → new_world` preserved; sources are pure-data Pydantic models; calculator is a pure function. No DB I/O during tick (sources cached at scenario-load via `CachedSource[T]`). |
| **II.11 Subsystem Table Ownership** | **Affected** — feature reads BEA + QCEW data from the reference SQLite; reads cross subsystem boundaries | ✅ pass: reads go through declared `Default*Source` interfaces (the existing `DefaultInterIndustryFlowSource`, `DBImportShareSource`, the new `DefaultPeripheryLaborCoefficientsSource`, `DefaultFinalDemandSource`, `IndustryToCountyAllocator`). No direct table access from outside the economics subsystem. |
| **II.12 Matrix Representation Layer** | **DIRECTLY USED** — Leontief inverse uses scipy.sparse | ✅ pass: matrix algebra layer is `scipy.sparse` per the existing `production_chain_rent.py` implementation; NetworkX is the authoring/inspection layer (used elsewhere in the engine for the morphism graph), not used for matrix ops in this feature. |
| **III.1 No Magic Constants** | **Affected** — every numerical constant in the new sources MUST trace to data | ✅ pass: periphery wage ratios trace to PWT v10.x (constitutionally-listed); final demand traces to BEA Use Table; QCEW employment shares trace to the QCEW (constitutionally-listed); the 5-year carry-forward look-back is the only tunable, lifted to `LeontiefRentDefines.qcew_carry_forward_max_years` per III.1 (added via Spec 058's `defines/` package shape). |
| **III.2 Falsifiability Required** | **CRITICAL** — every formula needs prediction + null + falsifying observable | ✅ pass: SC-004 makes phi_hour falsifiable against Hickel et al. 2022 ($2.8T drain, 2015) within order-of-magnitude — this IS the falsifying observation. Null hypothesis: phi_hour uniformly zero (the current stub state). Distinguishing observable: per-county `phi_hour` distribution variance is non-trivial AND order-of-magnitude matches an independent estimate. |
| **III.4 Data Catalog (Fixture vs Runtime)** | **CRITICAL** — periphery-wage source MUST be in `data-catalog.yaml` per III.4 | ✅ pass — using already-listed source: PWT (Penn World Tables) is already in `data-catalog.yaml` (id: `PWT`). No new constitutional addition required. The data-source object's `metadata` field per FR-002 will reference the PWT source ID and the specific extraction methodology (research.md §R1). |
| **III.6 Model Pinning** | None — feature is deterministic numerical computation; AI parsing is not in scope | ✅ pass (untouched) |
| **IV Michigan Test Case (incl. IV.2 Tri-County backward-compat)** | **CRITICAL** — Wayne County baseline is the canonical SC-002 reference | ✅ pass: SC-002 explicitly references the Wayne County scenario; the tri-county backward-compat test (IV.2) is preserved (this feature does not change the tri-county scenario shape, only the upstream `phi_hour` value). |

**P2 (Elaboration) — selectively relevant:**

- I.10 Terminal Crisis Arc: feature provides the upstream Φ value that drives the carceral turn (Φ exhaustion → Plantation→Prison→Camp transitions). Compliance: untouched in this feature.
- VI.1 Material Base First: feature operates entirely at the material base layer (production network, employment, wages) — strengthens compliance.
- VIII.6 Constants Without Data Sources: every new constant traces to PWT/BEA/QCEW. Strengthens III.1 compliance.

**Pre-Phase-0 verdict**: ✅ **PASS — no constitution violations identified.**

The feature is the first end-to-end realization of Constitution I.2 (Imperial Rent Φ) in the simulation. The Aleksandrov chain is intact (each operator traces to a material process). The Falsifiability gate (III.2) is operationalized via SC-004's order-of-magnitude check against Hickel et al. 2022. The Data Catalog gate (III.4) is met by using already-listed PWT data. The Determinism Hash gate (III.7) is met by deterministic linear algebra + bounded carry-forward + cache-aware sources.

### Post-Phase-1 Re-check

Performed against the generated `data-model.md`, `contracts/*.md`, and `quickstart.md`. All checks ✅ pass.

| Check | Verdict |
|-------|---------|
| **No new entity in `data-model.md` introduces a new Marxian primitive** | ✅ pass. Entities are: 2 new `Default*Source` classes (data-source plumbing inheriting `CachedSource[T]`), 1 new `IndustryToCountyAllocator` (allocation plumbing), 1 new `CalibrationWarning` event family (3 typed event subtypes, all `EconomicEvent` subclasses per existing `models/events.py` hierarchy), and 1 new `LeontiefRentDefines` Pydantic model (one tunable: `qcew_carry_forward_max_years`). None introduces a new pole type, morphism relation, transport edge type, or contradiction character. |
| **No `contracts/` interface lifts a hidden pole/morphism into the public surface** | ✅ pass. Contracts describe data-source Protocol shapes, the allocator's algorithm, and the typed event family — all infrastructural. They do not redefine dialectics, morphisms, hyperedges, or contradictions. |
| **No `quickstart.md` instruction violates the Data/Engine boundary** | ✅ pass. Quickstart recipes invoke the existing test runner, run a one-tick Wayne County simulation, inspect the resulting `phi_hour` distribution, and run the calibration check. None mutates state outside the engine; none creates persistent state in violation of II.6 or II.11. |
| **III.7 Determinism Hash preserved** | ✅ pass — the behavioral-fence test extended to cover the new sub-module asserts identical event-bus emission ordering AND identical `WorldState` (frozen Pydantic) post-tick across two runs with the same seed. The deterministic-hash function (computed over post-tick `WorldState` + emitted events) is the III.7 enforcement mechanism. |
| **III.1 No Magic Constants** | ✅ pass — every constant traces: (a) wage ratios → PWT v10.x extraction (research.md §R1); (b) final demand → BEA Use Table series (research.md §R2); (c) QCEW employment → existing reference SQLite; (d) the 5-year carry-forward look-back is lifted to `LeontiefRentDefines.qcew_carry_forward_max_years` (configurable, defaults documented). |
| **III.4 Data Catalog** | ✅ pass — PWT already in `data-catalog.yaml`; no new constitutional addition required. |
| **III.8 Aleksandrov Test** | ✅ pass — re-verified per-formula in research.md §R5. The pre-existing calculator clamp (`np.maximum(loss_ratio, 0.0)`) is preserved as a structural-axiom enforcement at the math layer, with the warning emitted at the source layer (where the violation is detected). The two-layer pattern (warning at source / clamp at calculator) means the data-integrity signal is preserved while the downstream math stays in a valid regime. |

**Post-Phase-1 verdict**: ✅ **PASS — no constitution violations introduced by Phase 1 design.** Ready for `/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/057-leontief-rent-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output — periphery-wage source, BEA series, performance, calculator clamp, etc.
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — verification recipes
├── contracts/           # Phase 1 output — Protocol contracts + event family + pipeline contract
│   ├── periphery_labor_coefficients_source.md
│   ├── final_demand_source.md
│   ├── industry_to_county_allocator.md
│   ├── calibration_warning.md
│   └── imperial_rent_pipeline.md
├── checklists/
│   └── requirements.md  # Spec quality (already complete from /speckit.specify)
├── spec.md              # Feature specification
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

Files marked **NEW** are introduced by this feature; **EDITED** receive surgical changes; **DELETED** are removed (orphan-test cleanup per FR-009).

```text
src/babylon/
├── config/
│   └── defines/
│       └── economy_basic.py          # EDITED — add LeontiefRentDefines (one field: qcew_carry_forward_max_years: int = 5)
├── economics/
│   ├── factory.py                    # EDITED — add 4 registrations to SourceRegistry.builtin_economics()
│   ├── tensor_hierarchy/
│   │   └── leontief_rent/            # NEW — package for the new sources
│   │       ├── __init__.py           # NEW — re-exports + __all__
│   │       ├── periphery_labor_coefficients.py  # NEW — Protocol + DefaultPeripheryLaborCoefficientsSource(CachedSource[PeripheryLaborCoefficients])
│   │       ├── final_demand.py       # NEW — DefaultFinalDemandSource(CachedSource[np.ndarray]) — Protocol already declared in production_chain_rent.py
│   │       └── industry_to_county_allocator.py  # NEW — Protocol + IndustryToCountyAllocator(CachedSource[dict[str, float]]) with carry-forward
│   └── tick/
│       └── system/
│           ├── __init__.py           # EDITED — _compute_imperial_rent becomes thin delegation to imperial_rent.compute()
│           └── imperial_rent.py      # NEW (≤400 LOC, completing Spec 058 US2) — orchestrates the new pipeline
├── engine/
│   └── services.py                   # EDITED — add 4 fields to ServiceContainer (periphery_labor_source, final_demand_source, industry_county_allocator, production_chain_calculator)
└── models/
    └── events.py                     # EDITED — add CalibrationWarning event family (AxiomViolation, QcewCarryForward, PhiHourOutlier as EconomicEvent subclasses)

tests/
├── unit/
│   └── economics/
│       ├── tensor_hierarchy/
│       │   └── leontief_rent/        # NEW directory
│       │       ├── test_periphery_labor_coefficients_source.py  # NEW (FR-002, US2)
│       │       ├── test_final_demand_source.py                  # NEW (FR-003, US3)
│       │       └── test_industry_to_county_allocator.py         # NEW (FR-004, US4 + carry-forward)
│       ├── test_factory.py           # EDITED — UNSKIP the spec-057 quarantine markers (per FR-009); update _EXPECTED_KEYS to include 4 new sources
│       ├── test_hydrator_mutants.py  # EDITED — UNSKIP the spec-057 quarantine markers
│       └── melt/
│           └── test_class_position.py  # EDITED — UNSKIP the spec-057 quarantine marker
├── integration/
│   ├── economics/
│   │   ├── conftest.py               # EDITED — UNSKIP the spec-057 quarantine marker
│   │   └── tick/
│   │       ├── test_facade_behavioral_fence.py  # EDITED — extend coverage to include the new imperial_rent.py sub-module
│   │       ├── test_imperial_rent_pipeline.py   # NEW (US1 acceptance scenarios — Wayne County + non-zero phi_hour + reproducibility)
│   │       └── test_imperial_rent_perf.py       # NEW (R3 — per-tick wall-clock budget after cache warm-up)
│   └── system/
│       └── test_phase1_blueprint.py  # EDITED — UNSKIP the spec-057 quarantine marker
└── unit/
    └── engine/
        ├── test_services.py          # EDITED — UNSKIP the spec-057 quarantine marker; assert 4 new fields exist on ServiceContainer
        └── test_formula_registry.py  # EDITED — UNSKIP the 3 spec-057 quarantine markers

# Files DELETED per FR-009 (orphans against the removed per-worker calculator API):
# Per spec FR-009, deletions are documented in implementing commit message and tested behaviour
# is superseded by tests against the new pipeline. Concrete deletion list determined at /speckit.tasks time;
# expected scope: ≤10 stale test functions (not entire files) plus removal of the spec-057 quarantine markers.
```

**Structure Decision**: Single Python project (no frontend changes — the dashboard graph bridge in `simulation.py` already exposes `phi_hour` per FR-011 and will pick up the new non-zero values automatically per SC-007). New sources cluster under a new `tensor_hierarchy/leontief_rent/` package that aligns with Spec 058's directory hygiene (one package per cohesive concern). The new sub-module `tick/system/imperial_rent.py` lands in the existing `tick/system/` package created by Spec 058's Phase A relocation, completing Spec 058's deferred US2 method-level decomposition.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations identified. The feature has zero complexity-tracking debt:

- No new dependencies introduced
- No new persistence tables
- No new constitutional data sources required (PWT already listed)
- No new theoretical primitives (the calculation is `Φ_j = Σᵢ M[i,j] · (w_ratio_i − 1) · y_j`, already implemented in `production_chain_rent.py`)
- No deferred TRANSITION STATE principles touched (II.7 hyperedges, I.17 OODA, I.18 material-ideological — all out of scope for this feature)

The one deliberate constraint that warrants explicit acknowledgement (not a violation, but a load-bearing design choice):

| Constraint | Why Needed | Simpler Alternative Rejected Because |
|------------|------------|--------------------------------------|
| Pre-existing calculator clamp (`np.maximum(loss_ratio, 0.0)` at `production_chain_rent.py:181`) preserved | Honors the structural axiom (W_c > V_c) at the math layer; the warning at source layer surfaces the violation without destabilizing downstream savings/accumulation arithmetic | Removing the clamp to honor Q3's "naturally produces small negative rent" language would propagate negative rents into `savings_schedule.py` formulas (`phi_adjustment = min(phi_hour · 2080 / wage, phi_cap)`) where `min(-, +)` semantics are not the savings model's intent and would silently flip sign on the savings adjustment. See research.md §R5 for the full analysis and the spec language reconciliation. |
