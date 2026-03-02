# Implementation Plan: Unified Class System

**Branch**: `038-unified-class-system` | **Date**: 2026-03-01 | **Spec**: `specs/038-unified-class-system/spec.md`
**Input**: Feature specification from `/specs/038-unified-class-system/spec.md`

## Summary

Reconcile two class determination frameworks (accounting criterion + wealth percentile) into a single canonical architecture. Add community filtration predicates (FIRST_NATIONS, INCARCERATED, UNDOCUMENTED, DISABLED) that modify classification inputs based on hyperedge memberships. Introduce a 5x5 class-pair solidarity matrix for solidarity potential computation. Add national rent differential calculator from ACS earnings data. All coefficients centralized in GameDefines. Backward compatible with existing ClassPositionClassifier protocol.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models, validators), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph memberships — existing via Features 022/029)
**Storage**: In-memory via GraphProtocol. No new database tables. ClassSystemDefines loaded via GameDefines (pyproject.toml `[tool.babylon]` or YAML loader).
**Testing**: pytest with TDD (Red-Green-Refactor). Markers: `@pytest.mark.math` (pure formulas), `@pytest.mark.unit` (default).
**Target Platform**: Linux server (simulation engine)
**Project Type**: Single Python package (`src/babylon/`)
**Performance Goals**: Classification O(1) per household. Filtration O(k) where k = number of community memberships (bounded by 14 community types). Solidarity potential O(n^2) for n class blocks per county (bounded; ~5 class blocks per county).
**Constraints**: All coefficients in GameDefines (FR-011). Backward compatible with existing ClassPositionClassifier protocol (FR-012). No new WorldState schema changes.
**Scale/Scope**: ~3,200 US counties; Detroit tri-county (Wayne/Oakland/Macomb) validation case. 3 new modules, 1 new GameDefines sub-model, 2 existing files extended.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.1 Settler-Colonial Frame | PASS | Spec models settler vs internal colony explicitly via rent differential (FR-007). FIRST_NATIONS filtration acknowledges qualitatively different property regime. |
| I.2 Imperial Rent (Phi) | PASS | Rent differential (FR-007) models Phi distribution by nation. Solidarity penalty uses Phi gap. |
| I.4 George Jackson Bifurcation | PASS | Solidarity potential feeds bifurcation analysis. Class-pair matrix + rent differential determine whether crisis produces fascism or revolution. |
| I.5 Department III | PASS | DISABLED filtration uses `reproduction_cost_modifier` (V_reproduction inflation). Community cost modifier already integrates Dept III. |
| I.6 Solidarity as Edge Mode | PASS | `solidarity_potential` is a scalar condition for edge mode transitions, not the mode itself. SOLIDARITY edges retain four-mode types (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC). |
| I.7 Quantitative -> Qualitative | PASS | ClassPosition is an enum (qualitative). Wealth percentile is a float (quantitative). Thresholds (50th, 90th, 99th) are explicit fold crossings. |
| I.12 Catastrophe Surface | PASS | Class position changes are discrete at wealth threshold crossings. Crisis dispossession (FR-010) models discontinuous transitions. |
| II.1 Four-Node Recursive | PASS | FR-009 explicitly requires fractal consistency at zoom levels. Same ClassPosition enum at both scales. |
| II.2 Primitives vs Derived | PASS | ClassPosition is derived from wealth percentile (never stored as a persistent field on WorldState). Solidarity potential is computed per-tick. |
| II.3 NetworkX as Discretized Manifold | PASS | All operations on GraphProtocol. Community overlap via XGI. |
| II.6 State is Data, Engine is Transformation | PASS | All new types are frozen Pydantic models. FiltrationResult, DualCriteriaResult are immutable. |
| II.7 Edges vs Hyperedges | PASS | Community memberships via XGI hyperedges (Feature 029). Solidarity potential stored on SOLIDARITY edges. Two layers remain separate. |
| III.1 No Magic Constants | PASS | FR-011 requires all coefficients in GameDefines. Default values sourced from Fed SCF, BIA, ACS. |
| III.4 Data Source Traceability | PASS | All data sources in spec table: Fed SCF, ACS, QCEW, Eviction Lab, BIA. All are approved sources in constitution. |
| III.5 Empirical vs Strategic Separation | PASS | Classification and rent differential are empirical (from data). Solidarity potential conditions are strategic (affect edge modes that player can influence). |
| VI.1 Material Base First | PASS | Economic classification → community filtration → solidarity potential → THEN bifurcation dynamics. Correct causal order. |
| VIII.1 Solidarity as Scalar (Anti-Pattern) | PASS | solidarity_potential is a scalar, but it's a derived condition input, not solidarity itself. Actual solidarity remains edge mode types. |
| VIII.6 Constants Without Data Sources | PASS | Every default traces to a data source or game design rationale in ClassSystemDefines field descriptions. |
| VIII.9 Community as Pairwise Edge | PASS | Communities are XGI hyperedges. Solidarity potential computed from hyperedge overlap, not pairwise edge enumeration. |

**Gate Result**: PASS — No violations. No complexity tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/038-unified-class-system/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: all unknowns resolved (10 decisions)
├── data-model.md        # Phase 1: entity definitions and relationships
├── quickstart.md        # Phase 1: developer onboarding
├── contracts/
│   ├── unified-classifier.md   # UnifiedClassifier protocol + behavioral contracts
│   ├── filtration.md            # Filtration predicates + composition rules
│   ├── solidarity-potential.md  # Class-pair matrix + solidarity contracts
│   └── rent-differential.md    # RentDifferentialCalculator + contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── config/
│   └── defines.py                    # +ClassSystemDefines (new sub-model, ~80 lines)
├── economics/
│   └── melt/
│       ├── class_position.py         # UNCHANGED — base classifier
│       ├── filtration.py             # NEW — FiltrationResult, apply_filtration() (~120 lines)
│       ├── unified_classifier.py     # NEW — UnifiedClassifier protocol + default (~200 lines)
│       ├── rent_differential.py      # NEW — RentDifferentialCalculator + result (~180 lines)
│       ├── wealth_proxy.py           # EXTENDED — accept equity_factor from ClassSystemDefines (~10 lines)
│       ├── types.py                  # UNCHANGED — ClassPosition, PrecarityStatus
│       └── __init__.py               # +exports for new modules
├── formulas/
│   └── community.py                  # UNCHANGED — calculate_solidarity_potential
├── models/
│   └── enums.py                      # +CALIBRATION_DISAGREEMENT EventType (~2 lines)
└── engine/
    └── systems/
        └── community.py              # EXTENDED — class-pair matrix lookup in solidarity (~20 lines)

tests/
├── unit/
│   ├── config/
│   │   └── test_class_system_defines.py   # NEW — solidarity matrix tests (~10 tests)
│   ├── economics/
│   │   ├── lifecycle/
│   │   │   └── test_class_inheritance.py  # NEW — class-differentiated inheritance (~15 tests)
│   │   └── melt/
│   │       ├── test_filtration.py         # NEW — ~30 tests
│   │       ├── test_unified_classifier.py # NEW — ~25 tests
│   │       ├── test_rent_differential.py  # NEW — ~20 tests
│   │       ├── test_wealth_proxy.py       # EXTENDED — FR-005 equity_factor + trust_land tests
│   │       └── test_fractal_consistency.py # NEW — fractal zoom validation (~5 tests)
│   └── formulas/
│       └── test_community.py              # EXTENDED — solidarity potential with matrix (~10 tests)
├── integration/
│   └── economics/
│       └── test_class_system_integration.py # NEW — SC-001/002/004 stubs (skip pending data)
└── constants.py                           # +ClassSystem test constant group
```

**Structure Decision**: Single Python package. All new code in `economics/melt/` (classification subsystem) and `config/defines.py` (coefficients). No new packages or directories outside existing structure. Three new modules, three extended files (defines.py, wealth_proxy.py, community.py).

**Estimated New Code**: ~600 lines production, ~900 lines test. ~10 lines modified in existing `wealth_proxy.py` (R-011: equity_factor from ClassSystemDefines).

## Key Design Decisions

| # | Decision | Reference |
|---|----------|-----------|
| R-001 | Wrapper pattern for UnifiedClassifier (not subclass/extension) | research.md |
| R-002 | No Household model — classifier works on function arguments | research.md |
| R-003 | INDIGENOUS → CommunityType.FIRST_NATIONS (existing enum) | research.md |
| R-004 | Filtration logic in economics/melt/ (same subsystem as classifier) | research.md |
| R-005 | 5x5 solidarity matrix as nested dict with symmetric accessor | research.md |
| R-006 | Calibration log via event bus (CALIBRATION_DISAGREEMENT events) | research.md |
| R-007 | Rent differential as Protocol + Default in economics/melt/ | research.md |
| R-008 | Two integration points: CommunitySystem + EventType | research.md |
| R-009 | All filtration defaults verified against spec and code | research.md |
| R-010 | 5 of 7 requirements reuse existing code — 0 rewrites needed | research.md |
| R-011 | WealthProxyCalculator reads equity_factor from ClassSystemDefines (not hardcoded) | research.md |

## Dependency Map

```
Feature 013 (MELT)           Feature 029 (Community)      Feature 030 (DPD')
├─ ClassPosition enum        ├─ CommunityType enum        ├─ InheritanceCalculator
├─ PrecarityStatus           ├─ CommunityState            └─ DPDState
├─ ClassPositionClassifier   ├─ CommunityMembership
├─ WealthProxyCalculator     ├─ COMMUNITY_CATEGORY_MAP
└─ NationalParameters        └─ shared_communities()
        │                           │                           │
        └──────────┬────────────────┘                           │
                   │                                            │
           ┌──────────────────┐                                 │
           │  Feature 038     │                                 │
           │  Unified Class   │◄────────────────────────────────┘
           │  System          │
           └──────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Bifurcation  Solidarity  Organization
   Analysis     System      Model (031)
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Feature 026 (tri-county substrate) not implemented | High (spec-only) | Low | Spec says A-007: inheritance defaults to zero if DPD' not integrated. Rent differential uses mock data for testing. |
| base_class_solidarity values need tuning | Medium | Low | All values in GameDefines, tunable without code changes. Parameter sweep validates monotonicity (SC-007). |
| ACS race x NAICS data heavily suppressed | Medium | Medium | NoDataSentinel propagation is core design. County aggregate excludes suppressed NAICS. |
| CALIBRATION_DISAGREEMENT event type conflicts | Low | Low | EventType is a StrEnum — new values don't break existing code. |
