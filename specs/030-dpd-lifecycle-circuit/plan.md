# Implementation Plan: D-P-D' Lifecycle Circuit

**Branch**: `030-dpd-lifecycle-circuit` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/030-dpd-lifecycle-circuit/spec.md`

## Summary

Model intergenerational class reproduction through the D-P-D' lifecycle circuit (Dependent → Productive → Dependent'). Adds a `LifecycleSystem` to the simulation engine that tracks population cohorts across three lifecycle phases per county, computes a legitimation index feeding into the existing bifurcation system, models inheritance flows at D' terminus with Pareto wealth distribution, transmits ideology during D-to-P transitions, encodes differential transition rates for racial/carceral inequality, and models dual circuit interference (D-P-D' x P-D-P') where resource competition, dispossession, and legitimation crises desynchronize individual lifecycle and class reproduction circuits. All population dynamics and class mobility parameters are tunable GameDefines coefficients with documented provenance from Chetty Opportunity Atlas calibration data.

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph — existing via Feature 022/029)
**Storage**: In-memory via GraphProtocol. No new database tables. DPDState persists via CountyEconomicState extension in the graph bridge. Mobility Atlas CSVs read once during parameter derivation (development-time, not runtime).
**Testing**: pytest with markers: `@pytest.mark.unit`, `@pytest.mark.math`, `@pytest.mark.integration`
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project — extends existing simulation engine
**Performance Goals**: LifecycleSystem.step() completes in <10ms per county per tick (cohort arithmetic, not agent-level simulation)
**Constraints**: All new models must use existing constrained types (Probability, Currency, Coefficient, Gini). Population conservation invariant must hold to 0.1% tolerance. No runtime file I/O.
**Scale/Scope**: ~3,200 counties per simulation. 23 functional requirements. 7 user stories. ~8 new source files + ~6 new test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I.1 Settler-Colonial Frame** | PASS | Differential transition rates (FR-010, FR-017) encode racial capitalism, not colorblind demographics. Black-White mobility gap from Chetty data explicitly modeled. |
| **I.2 Imperial Rent (Φ)** | PASS | Shadow subsidy metric (FR-023) quantifies unpaid reproductive labor extracted by M-C-M'. Connects to existing Φ_Repro in reproduction.py. |
| **I.4 George Jackson Bifurcation** | PASS | Legitimation index (FR-004–FR-006) feeds directly into BifurcationRiskMetric.legitimation via weighted blend. Low legitimation amplifies bifurcation risk. |
| **I.5 Department III** | PASS | Generational shadow subsidy is the lifecycle analog of γ_III daily shadow subsidy. D-phase socialization costs are Dept III at generational timescale. |
| **I.7 Quantitative → Qualitative** | PASS | Population quantities (floats) accumulate; crisis classification (CRISIS/UNSTABLE/STABLE) is discrete enum. Lifecycle phases are enums; transition rates are floats. |
| **I.8 Tragedy of Inevitability** | PASS | System models collapse as default trajectory when legitimation fails. No "fix" button for broken D' promise. |
| **I.18 Material-Ideological on Hyperedges** | PASS | Ideology transmission (FR-009) operates on the gap between material position (lifecycle phase) and ideological consciousness (caregiver influence vs institutional hegemony). |
| **II.2 Primitives vs Derived** | PASS | Store: pop_D, pop_P, pop_D_prime, transition rates, wealth. Compute: dependency_ratio, legitimation_index, inheritance_gini, shadow_subsidy. |
| **II.4 Quantities vs Coefficients** | PASS | Population counts flux per tick. Transition rates are α-smooth coefficients modified by events. Legitimation crisis = discontinuous threshold crossing. |
| **II.6 State is Data, Engine is Transformation** | PASS | DPDState is frozen Pydantic. LifecycleSystem is pure transformation. No DB I/O during tick. |
| **II.7 Edges vs Hyperedges** | PASS | Uses existing Category 3 (LIFECYCLE_PHASE) hyperedges for YOUTH/ADULT/ELDER. DPDState is the quantitative layer alongside the qualitative XGI layer. |
| **III.1 No Magic Constants** | PASS | All parameters trace to Mobility Atlas (KFR tables) or published demographic research. Provenance documented per FR-018. |
| **III.2 Falsifiability Required** | PASS | Spec includes 5 falsification criteria with H₁ hypotheses. SC-003 (Gini(inheritance) > Gini(income)) and SC-004 (differential accumulation) are directly testable. |
| **III.4 Data Source Traceability** | PASS | Uses approved sources: Census/ACS (already approved), Fed SCF (already approved). New source needed: Chetty Opportunity Atlas. |
| **VI.1 Material Base First** | PASS | Population dynamics (material base) computed before legitimation (superstructure) and ideology transmission. Turn order respects causality. |
| **VIII.6 Constants Without Data Sources** | PASS | Every default parameter has provenance citation (FR-018). _REPRO_EXTERNALIZATION_FACTOR TODO addressed by shadow subsidy metric. |

**New Data Source**: Chetty Opportunity Atlas (calibration-only, not runtime). Added to constitution III.4 approved list in v1.8.1 (BD-approved 2026-02-27). The Mobility Atlas provides county-level class mobility data (KFR by parental income and race) used to derive tunable parameters — not ingested at runtime.

**Gate Result**: PASS (no violations).

## Project Structure

### Documentation (this feature)

```text
specs/030-dpd-lifecycle-circuit/
├── plan.md              # This file
├── research.md          # Phase 0: resolved unknowns
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: integration test scenarios
├── contracts/           # Phase 1: internal system contracts
│   └── lifecycle-system-contract.md
├── checklists/
│   └── requirements.md  # Quality validation
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── config/
│   └── defines.py                          # ADD: LifecycleDefines category
├── economics/
│   ├── lifecycle/                          # NEW: lifecycle circuit module
│   │   ├── __init__.py
│   │   ├── types.py                        # DPDState, LegitimationState, InheritanceFlow
│   │   ├── cohort_dynamics.py              # Population transition calculator
│   │   ├── legitimation.py                 # Legitimation index + weighted blend
│   │   ├── inheritance.py                  # Inheritance flow + Pareto distribution
│   │   ├── dual_circuit.py                 # Resource competition, sandwich squeeze, shadow subsidy
│   │   └── mobility.py                     # Class mobility function (Chetty-derived params)
│   └── reproduction.py                     # MODIFY: Wire shadow subsidy to Φ_Repro
├── engine/
│   ├── systems/
│   │   └── lifecycle.py                    # NEW: LifecycleSystem
│   └── simulation_engine.py                # MODIFY: Add LifecycleSystem to turn order
├── formulas/
│   └── lifecycle.py                        # NEW: Pure lifecycle formulas
└── models/
    └── enums.py                            # MODIFY: Add lifecycle EventTypes

tests/
├── unit/
│   ├── economics/
│   │   └── lifecycle/                      # NEW: lifecycle unit tests
│   │       ├── test_cohort_dynamics.py
│   │       ├── test_legitimation.py
│   │       ├── test_inheritance.py
│   │       ├── test_dual_circuit.py
│   │       └── test_mobility.py
│   └── formulas/
│       └── test_lifecycle_formulas.py      # NEW: formula unit tests
└── integration/
    └── test_lifecycle_system.py            # NEW: system integration test
```

**Structure Decision**: Follows the existing `economics/` module pattern (see `economics/dynamics/`, `economics/crisis/`). The lifecycle module is a peer directory to `dynamics/`, `crisis/`, and `circulation/`. Formulas go in `formulas/lifecycle.py`. The system goes in `engine/systems/lifecycle.py`. This mirrors the structure of Features 018, 021, 023 which each have an economics submodule + engine system + formulas file.

## Post-Design Constitution Re-Check

*Verified after Phase 1 design artifacts (data-model.md, contracts/, quickstart.md) complete.*

| Principle | Pre-Design | Post-Design | Notes |
|-----------|-----------|-------------|-------|
| **II.2 Primitives vs Derived** | PASS | PASS | data-model.md confirms: store pop_D/P/D', rates, wealth. Compute dependency_ratio, legitimation_index, inheritance_gini. No derived quantities stored. |
| **II.6 State is Data, Engine is Transformation** | PASS | PASS | DPDState, LegitimationState, InheritanceFlow all frozen Pydantic. LifecycleSystem contract specifies pure step() transformation. |
| **II.7 Category 3 Lifecycle** | PASS | PASS | DPDState is quantitative layer alongside qualitative XGI YOUTH/ADULT/ELDER hyperedges. No conflation. |
| **III.1 No Magic Constants** | PASS | PASS | LifecycleDefines has 36 parameters, each with documented provenance in data-model.md. |
| **III.4 Data Source Traceability** | PASS | PASS | research.md documents all sources: CDC NVSS, Census, BLS NCS, SSA, Fed SCF, Chetty Opportunity Atlas. Chetty added to constitution III.4 approved list (v1.8.1). |
| **VI.1 Material Base First** | PASS | PASS | Contract specifies: population dynamics (steps 1-6) before legitimation (7-8) before ideology (10). Turn order position 7 confirmed. |

**Post-Design Gate Result**: PASS. No new violations introduced during design phase.

## Complexity Tracking

> No violations requiring justification. All patterns follow existing architecture.
