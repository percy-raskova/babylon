# Implementation Plan: ATUS Department III - Visibility Decomposition

**Branch**: `005-atus-department-iii` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-atus-department-iii/spec.md`

## Summary

Implement g₃₃ visibility decomposition for Department III. The existing infrastructure already provides `dept_III` field, `visibility_g33` (default 1.0), and `shadow_subsidy` computation. This feature:

1. **Computes g₃₃ from data** instead of using default 1.0
1. **Decomposes visibility** into four categories (domestic_unpaid, migrant_care, peripheral_subsistence, state_socialized)
1. **Validates model falsifiability** through regression analysis

**Scope Clarification**: This feature does NOT add new data loaders (ATUS, CEX already exist). It adds the visibility computation layer on top of existing infrastructure.

## Technical Context

**Language/Version**: Python 3.12+ (matches existing Babylon stack)
**Primary Dependencies**: Pydantic 2.x, SQLAlchemy 2.x, pandas (for regression), scipy (for statistics)
**Storage**: SQLite 3NF schema (existing `babylondata.sqlite`), YAML for mappings
**Testing**: pytest with TDD (red-green-refactor), markers: `@pytest.mark.unit`, `@pytest.mark.integration`
**Target Platform**: Linux (development), cross-platform compatible
**Performance Goals**: Process ATUS survey year in ≤5 minutes (SC-007)
**Constraints**: Fail fast on BLS data source unavailability; no county-level disaggregation
**Scale/Scope**: National-level coefficients applied uniformly; ~6 occupation groups × 5 categories = 30 coefficient combinations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                                        | Status  | Notes                                                        |
| ------------------------------------------------ | ------- | ------------------------------------------------------------ |
| **I.2 Imperial Rent (Φ)**                        | ✅ PASS | Department III shadow labor is Fortunati component of Φ      |
| **I.5 Department III**                           | ✅ PASS | Directly implements reproductive labor tracking              |
| **II.2 Primitives vs Derived**                   | ✅ PASS | T³_v (hours) is primitive; g₃₃ is derived from data sources  |
| **II.4 Quantities vs Coefficients**              | ✅ PASS | National-level coefficients update annually (slow evolution) |
| **II.5 AI Observes, Never Controls**             | ✅ PASS | Pure data pipeline, no AI involvement                        |
| **II.6 State is Data, Engine is Transformation** | ✅ PASS | Pydantic models for data, services for transformation        |
| **III.1 No Magic Constants**                     | ✅ PASS | All values trace to BLS (ATUS, OEWS, QCEW)                   |
| **III.2 Falsifiability Required**                | ✅ PASS | Explicit regression and correlation tests defined            |
| **III.4 Data Source Traceability**               | ✅ PASS | ATUS, OEWS, QCEW, CEX all in approved source list            |
| **VI.7 Superstructure Before Base**              | ✅ PASS | This is material base (reproduction), not superstructure     |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/005-atus-department-iii/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal protocols, not REST APIs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/
├── data/
│   └── atus/                    # EXISTING - enhance
│       ├── __init__.py          # (existing)
│       ├── models.py            # Existing models (add VisibilityDecomposition)
│       ├── protocol.py          # Existing protocol (add visibility methods)
│       ├── mappings.py          # Existing mappings (complete, no changes)
│       ├── loader.py            # Existing loader (no changes)
│       ├── seed_data.yaml       # Existing seed data (ADD visibility weights)
│       └── visibility.py        # NEW: g₃₃ computation service
├── economics/
│   ├── shadow_labor.py          # EXISTING - integrate visibility decomposition
│   ├── tensor.py                # EXISTING - ValueTensor4x3 (no changes needed)
│   └── validation/              # NEW - falsifiability checks
│       ├── __init__.py
│       └── regression.py        # domestic_hours ~ 1/income

tests/
├── unit/
│   ├── data/
│   │   └── atus/               # EXISTING - add visibility tests
│   │       └── test_visibility.py  # NEW
│   └── economics/
│       └── validation/         # NEW
│           └── test_regression.py
└── integration/
    └── economics/
        └── test_visibility_integration.py  # NEW: end-to-end test
```

**Structure Decision**: Minimal additions to existing modules. The ATUS module already has comprehensive infrastructure; we add visibility computation. Validation is a new submodule for falsifiability testing.

## Complexity Tracking

> **No violations requiring justification.** Constitution check passes.

## Implementation Phases

### Phase 1: VisibilityDecomposition Model (User Story 2)

**Goal**: Create the four-category visibility decomposition data model.

**Files**:

- `src/babylon/data/atus/models.py` - Add `VisibilityDecomposition` Pydantic model
- `tests/unit/data/atus/test_visibility.py` - Unit tests for model

**Acceptance Criteria**:

- Model has four fraction fields (domestic_unpaid, migrant_care, peripheral_subsistence, state_socialized)
- Model validator ensures fractions sum to 1.0 ± 0.001
- Each category has a visibility coefficient (g_domestic=0.0, g_migrant=0.3, g_peripheral=0.0, g_state=1.0)
- Computed `total_g33` property returns weighted average

**Test Commands**:

```bash
pytest tests/unit/data/atus/test_visibility.py -v
```

______________________________________________________________________

### Phase 2: Visibility Computation Service (User Story 1)

**Goal**: Create service that computes g₃₃ from seed data weights.

**Files**:

- `src/babylon/data/atus/visibility.py` - NEW: `VisibilityComputer` service
- `src/babylon/data/atus/seed_data.yaml` - ADD visibility weights section
- `src/babylon/data/atus/protocol.py` - Add `VisibilityComputerProtocol`
- `tests/unit/data/atus/test_visibility.py` - Service tests

**Acceptance Criteria**:

- Service computes g₃₃ from weighted average of four components
- Result falls within [0.2, 0.5] range per SC-003
- Service integrates with existing `ShadowLaborService`
- Fail fast with `DataSourceUnavailableError` if weights missing

**Test Commands**:

```bash
pytest tests/unit/data/atus/test_visibility.py -v
```

______________________________________________________________________

### Phase 3: Falsifiability Validation (User Story 3)

**Goal**: Implement regression validation for theoretical claims.

**Files**:

- `src/babylon/economics/validation/__init__.py` - NEW module
- `src/babylon/economics/validation/regression.py` - Regression analysis
- `tests/unit/economics/validation/test_regression.py` - Unit tests

**Acceptance Criteria**:

- Regression `domestic_hours ~ 1/income` produces positive coefficient (β > 0)
- Uses existing ATUS occupation multipliers as proxy data
- scipy.stats.linregress for simplicity (per research.md decision)

**Test Commands**:

```bash
pytest tests/unit/economics/validation/test_regression.py -v
```

______________________________________________________________________

### Phase 4: Integration & Shadow Subsidy Update

**Goal**: Wire visibility decomposition into existing shadow subsidy calculation.

**Files**:

- `src/babylon/economics/shadow_labor.py` - Integrate `VisibilityComputer`
- `tests/integration/economics/test_visibility_integration.py` - End-to-end test

**Acceptance Criteria**:

- `ShadowLaborService` accepts `VisibilityComputer` via dependency injection
- `shadow_subsidy = v × (1 - g₃₃)` uses computed g₃₃ instead of default 1.0
- SC-004: Shadow subsidy accounts for 50-80% of total reproductive labor value

**Test Commands**:

```bash
pytest tests/integration/economics/test_visibility_integration.py -v
mise run test:all
```

______________________________________________________________________

## Dependencies

```mermaid
flowchart LR
    P1[Phase 1: Model] --> P2[Phase 2: Service]
    P2 --> P3[Phase 3: Validation]
    P2 --> P4[Phase 4: Integration]
    P3 --> P4
```

**Critical Path**: Phase 1 → Phase 2 → Phase 4 (Phase 3 can run in parallel after Phase 2)
