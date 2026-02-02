# Implementation Plan: MELT and Basket Visibility Computation

**Branch**: `013-melt-basket-visibility` | **Date**: 2026-02-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/013-melt-basket-visibility/spec.md`

## Summary

Implement the MELT (τ) and basket visibility (γ_basket) computation system for determining Labor Aristocracy thresholds. MELT bridges labor-time and money-price domains (τ = GDP / L), while γ_basket measures the imperial subsidy on the US consumption basket. Together, τ_effective = τ × γ_basket defines the wage threshold above which workers extract imperial rent (Φ_hour > 0). Implements TVT Axioms B3-B4 (Single-System Temporalism), C1 (ERDI), D3-D4 (Basket Visibility), and E1-E4 (Class Position).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: TensorRegistry, ValueTensor4x3, NoDataSentinel from spec 011; CapitalStockCalculator from spec 012; BEA GDP data, QCEW employment data
**Storage**: In-memory cache (follows TensorRegistry pattern); no new database tables
**Testing**: pytest with markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.math`
**Target Platform**: Linux server (simulation engine context)
**Project Type**: Single Python package extension to existing `babylon.economics` module
**Performance Goals**: <100ms per NationalParameters computation; <10ms per wage classification
**Constraints**: Must integrate with existing TensorRegistry without breaking consumers; thread-safe
**Scale/Scope**: National-level MELT (single τ per year); 3,143 counties for wage classification

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I.2 Imperial Rent (Φ) | ✅ PASS | Spec explicitly models imperial rent extraction via Φ_hour formula (FR-006); identifies Labor Aristocracy as W > τ_effective |
| I.5 Department III | ✅ PASS | γ_basket implicitly captures reproductive labor compression (domestic shadow labor component); spec references TVT Axiom D3 |
| II.2 Primitives vs Derived | ✅ PASS | τ is derived from GDP/L primitives; γ_basket derived from α and γ_import; never stored directly |
| II.4 Quantities vs Coefficients | ✅ PASS | τ and γ_basket are coefficients (slow-evolving, annual); W is a quantity |
| III.1 No Magic Constants | ✅ PASS | τ derives from BEA GDP and QCEW employment; γ_basket derives from trade data or Hickel et al. methodology (A-004); V_reproduction = $12/hour traces to Census poverty data (A-003) |
| III.2 Falsifiability Required | ✅ PASS | SC-001-SC-004 provide testable predictions: τ ∈ [$55-75], LA share ∈ [30-50%], Oakland > Wayne LA share, average worker Φ_hour > 0 |
| III.4 Data Source Traceability | ✅ PASS | BEA GDP (D-002), QCEW employment (D-003), Penn World Tables ERDI (D-004), Census trade data (D-005), BEA RPP (D-006) |
| IV. Metro Detroit Validation | ✅ PASS | Spec includes Wayne (26163) vs Oakland (26125) validation case per Section IV |
| VII.3 Determinism from Material | ✅ PASS | Class position is derived from wage relative to thresholds, not directly determined by material conditions alone |

**All gates pass. Proceeding to Phase 0 research.**

## Project Structure

### Documentation (this feature)

```text
specs/013-melt-basket-visibility/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── melt_calculator.py
│   ├── basket_visibility_calculator.py
│   ├── class_position_classifier.py
│   └── imperial_rent_calculator.py
├── checklists/          # Validation checklists
│   ├── requirements.md
│   └── tvt-domain-review.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/economics/
├── tensor.py                    # EXISTING: NoDataSentinel, ValueTensor4x3
├── tensor_registry.py           # EXISTING: TensorRegistry caching
├── capital_stock.py             # EXISTING (Feature 012): CapitalStockCalculator
├── melt.py                      # NEW: MELTCalculator service
├── basket_visibility.py         # NEW: BasketVisibilityCalculator service
├── national_parameters.py       # NEW: NationalParameters container
├── class_position.py            # NEW: ClassPosition enum, ClassPositionClassifier
├── imperial_rent.py             # NEW: ImperialRentCalculator (refactor from reproduction.py)
└── __init__.py                  # EXTEND: Export new modules

tests/unit/economics/
├── test_melt.py                 # NEW: Unit tests for MELTCalculator
├── test_basket_visibility.py    # NEW: Unit tests for BasketVisibilityCalculator
├── test_national_parameters.py  # NEW: Unit tests for NationalParameters
├── test_class_position.py       # NEW: Unit tests for ClassPositionClassifier
└── test_imperial_rent_tvt.py    # NEW: Unit tests for TVT-style imperial rent

tests/integration/economics/
└── test_labor_aristocracy.py    # NEW: Integration tests for LA threshold validation
```

**Structure Decision**: Single project (Option 1). Extends existing `babylon.economics` module with new files for MELT and basket visibility computation. Follows established patterns from TensorRegistry (caching, thread safety, NoDataSentinel).

## Complexity Tracking

> **No violations to justify** - This feature adheres to all Constitution constraints.

## Design Decisions

### D1: National MELT as Separate Service vs Computed Property

**Decision**: Implement as separate `MELTCalculator` service, not as a computed property on existing models.

**Rationale**:
- MELT requires national GDP and employment aggregation across all counties
- Service pattern matches existing `MarxianHydrator` and `CapitalStockCalculator` architecture
- Enables caching of computed τ values per year
- Separates national-level calculations from county-level tensor operations

### D2: MVP Hardcoded γ_basket vs Computed

**Decision**: Support both MVP mode (hardcoded γ_basket = 0.68) and computed mode (from α and γ_import).

**Rationale**:
- MVP enables immediate class position analysis without Penn World Tables loader
- Computed mode provides path to full implementation
- `estimated` flag distinguishes MVP approximation from computed values
- Spec explicitly scopes this as acceptable (FR-008, A-004)

### D3: ClassPosition as Enum vs String

**Decision**: Implement `ClassPosition` as Python enum with three values.

**Rationale**:
- Type safety prevents invalid class position values
- Aligns with Constitution VII.7 (No continuous quality gradients)
- Enum values: `LABOR_ARISTOCRACY`, `PROLETARIAT`, `SUBPROLETARIAT`
- Scope limitation documented: wage-based only, cannot identify bourgeoisie/lumpen

### D4: NationalParameters Immutability

**Decision**: Make `NationalParameters` a frozen Pydantic model (immutable).

**Rationale**:
- Parameters are point-in-time snapshots
- Immutability enables safe caching and sharing across consumers
- Aligns with Constitution II.6 (State is Data)
- Once computed for a year, parameters should not change during simulation

### D5: Integration with Existing ImperialRentCalculator

**Decision**: Create new TVT-aligned `ImperialRentCalculator` separate from existing `reproduction.py` module.

**Rationale**:
- Existing `ImperialRentCalculator` in `reproduction.py` uses Emmanuel-Amin framework
- This feature implements TVT Axiom E3 formula: Φ_hour = (W/τ) × (1/γ_basket) - 1
- Different theoretical frameworks, different formulas, coexist in codebase
- Future consolidation possible once both are validated

## Implementation Phases

### Phase 0: Research
- Review TVT mathematical formalization for formula precision (completed in spec phase)
- Analyze BEA GDP data availability and format
- Identify QCEW national employment aggregation patterns
- Research CPI data sources for V_reproduction inflation adjustment

### Phase 1: Data Model & Contracts
- Define ClassPosition enum with scope limitations
- Define NationalParameters frozen dataclass
- Define MELTCalculator protocol/interface
- Define BasketVisibilityCalculator protocol/interface
- Define ClassPositionClassifier protocol/interface
- Define ImperialRentCalculator protocol/interface (TVT version)
- Document contracts in `contracts/` directory

### Phase 2: Task Generation
- Run `/speckit.tasks` to generate detailed tasks

### Phase 3: Core Implementation
- Implement ClassPosition enum
- Implement NationalParameters with validation and caching
- Implement MELTCalculator with BEA/QCEW integration
- Implement BasketVisibilityCalculator with MVP fallback
- Implement ClassPositionClassifier
- Implement ImperialRentCalculator (TVT formulas)

### Phase 4: Integration
- Integrate with existing TensorRegistry patterns
- Add NationalParameters caching with annual invalidation
- Implement county-level wage classification via QCEW
- Add sanity range validation per FR-010

### Phase 5: Validation
- Implement τ range validation tests (SC-001)
- Implement LA share range tests (SC-002)
- Implement Detroit validation case - Wayne vs Oakland (SC-003)
- Implement average worker Φ_hour > 0 test (SC-004)
- Implement edge case coverage tests (SC-005)

### Phase 6: Documentation
- Write quickstart.md with usage examples
- Update data-model.md with final implementation
- Document integration patterns with Feature 012 (Capital Stock Dynamics)
