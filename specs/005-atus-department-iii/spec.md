# Feature Specification: ATUS Department III - Visibility Decomposition

**Feature Branch**: `005-atus-department-iii`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Integrate ATUS data to populate Department III visibility decomposition"

## Clarifications

### Session 2026-01-31

- Q: What specific processing time target for SC-008 "reasonable time bounds"? → A: 5 minutes (balanced, typical batch ETL)
- Q: How should system behave when BLS data sources are unavailable? → A: Fail fast with clear error message
- Q: How should Department III v and s be computed (QCEW-based vs ATUS-based)? → A: Replace v with ATUS hours × shadow_wage, set s=0 (shadow captured via shadow_subsidy mechanism)

### Scope Clarification

**Already Exists** (NOT in scope):

- `dept_III` field in `ValueTensor4x3` ✅
- `visibility_g33` field (defaults to 1.0) ✅
- `shadow_subsidy` computed property ✅
- `ShadowLaborService` with `ShadowLaborResult` ✅
- ATUS activity code mappings ✅
- ATUS seed data with occupation multipliers ✅
- Hydrator populating `dept_III` from QCEW ✅

**Actually New** (IN scope):

- Four-category visibility decomposition model
- g₃₃ computation from real data (not default 1.0)
- Falsifiability validation tests

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute g₃₃ from Data Sources (Priority: P1)

A simulation researcher requests the visibility coefficient g₃₃ for Department III. Instead of using the default 1.0, the system computes g₃₃ from three data sources: ATUS gender differential in unpaid care hours, OEWS median care worker wages, and QCEW public sector employment in care industries.

**Why this priority**: The existing `visibility_g33=1.0` default makes all reproductive labor fully visible, which contradicts Fortunati's theory. Computing g₃₃ from data enables the shadow subsidy calculation to reflect actual invisibility.

**Independent Test**: Can be tested by providing the three input values and verifying g₃₃ falls within [0.2, 0.5] range per SC-003.

**Acceptance Scenarios**:

1. **Given** ATUS gender differential (women do 2x unpaid care), OEWS care wage ($15.43/hr), and QCEW public care employment (15% of care sector), **When** computing g₃₃, **Then** result is between 0.2 and 0.5.
1. **Given** the computed g₃₃, **When** the existing `shadow_subsidy` property is evaluated, **Then** it returns `dept_III.v × (1 - g₃₃)` with the real g₃₃ value.

______________________________________________________________________

### User Story 2 - Four-Category Visibility Decomposition (Priority: P2)

A simulation researcher queries the visibility decomposition to understand WHERE reproductive labor invisibility comes from. The system returns a breakdown into four categories: domestic_unpaid, migrant_care, peripheral_subsistence, and state_socialized, with fractions summing to 1.0.

**Why this priority**: The single g₃₃ scalar hides the structural sources of invisibility. Decomposition enables analysis of which mechanisms (domestic unpaid work vs migrant labor vs externalized reproduction) drive shadow subsidy.

**Independent Test**: Can be tested by verifying decomposition fractions sum to 1.0 and each category has a distinct visibility coefficient.

**Acceptance Scenarios**:

1. **Given** a request for visibility decomposition, **When** the service returns results, **Then** the four fractions (domestic_unpaid, migrant_care, peripheral_subsistence, state_socialized) sum to 1.0 ± 0.001.
1. **Given** the decomposition, **When** computing g₃₃ as weighted average, **Then** result matches the single g₃₃ value from User Story 1.

______________________________________________________________________

### User Story 3 - Validate Falsifiability Criteria (Priority: P3)

A simulation researcher runs validation checks to confirm the model produces theoretically expected relationships. The system performs regression analysis of domestic_hours against inverse income and reports the coefficient (expected positive).

**Why this priority**: A model without falsifiability is not scientific. This validates that ATUS data shows the expected inverse relationship between income and unpaid care burden.

**Independent Test**: Can be tested using the existing ATUS seed data with occupation multipliers, verifying regression produces positive coefficient.

**Acceptance Scenarios**:

1. **Given** ATUS occupation multipliers (service workers do more housework than professionals), **When** running regression domestic_hours ~ 1/income proxy, **Then** coefficient is positive (β > 0).

______________________________________________________________________

### Edge Cases

- What if g₃₃ computation produces values outside [0, 1]? Values are clamped to [0, 1] with a warning.
- What if data sources are unavailable? System fails fast with clear error message identifying the unavailable source.
- What if visibility decomposition fractions don't sum to 1.0 due to floating point? Normalize to 1.0 with warning if drift > 0.01.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute visibility coefficient g₃₃ from ATUS gender differential, OEWS care wages, and QCEW public sector data
- **FR-002**: System MUST decompose visibility into four categories: domestic_unpaid, migrant_care, peripheral_subsistence, state_socialized
- **FR-003**: System MUST ensure decomposition fractions sum to 1.0 ± 0.001
- **FR-004**: System MUST provide a method to override the default g₃₃=1.0 in `ValueTensor4x3` with computed value
- **FR-005**: System MUST support validation regression: domestic_hours ~ 1/income with positive coefficient
- **FR-006**: System MUST fail fast with clear error if data sources unavailable

### Key Entities

- **VisibilityDecomposition**: Breakdown of g₃₃ into four categories. Attributes: domestic_unpaid_fraction, migrant_care_fraction, peripheral_subsistence_fraction, state_socialized_fraction, total_g33. Invariant: fractions sum to 1.0.
- **VisibilityComputer**: Service that computes g₃₃ and decomposition from data sources. Implements existing patterns from `ShadowLaborService`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: g₃₃ computed from data differs from default 1.0
- **SC-002**: Visibility decomposition categories sum to 1.0 ± 0.001
- **SC-003**: g₃₃ falls within theoretically plausible range (0.2 to 0.5 based on literature estimates)
- **SC-004**: Shadow subsidy S_shadow accounts for 50-80% of total reproductive labor value when using computed g₃₃
- **SC-005**: Regression of domestic_hours ~ 1/income produces positive coefficient (β > 0)
- **SC-006**: Computed values are deterministic given the same input data
- **SC-007**: Full visibility computation completes within 5 minutes for a survey year (per clarification session)

## Assumptions

- Existing ATUS seed data with occupation multipliers is sufficient for validation regression
- The four-category visibility decomposition is sufficient to capture major modes of invisibility
- National-level weights for decomposition are acceptable (no class-level variation initially)
- OEWS shadow wage ($15.43/hr) in seed_data.yaml is the care wage reference

## Out of Scope

- Replacing QCEW-based `dept_III.c` with CEX data (deferred - already works)
- Replacing QCEW-based `dept_III.v` with ATUS hours × shadow_wage (deferred - existing approach works)
- County-level visibility variation (ATUS sample too small)
- Class-disaggregated visibility decomposition (future enhancement)
