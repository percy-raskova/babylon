# Feature Specification: Gamma (Visibility) Tensor

**Feature Branch**: `015-gamma-visibility-tensor`
**Created**: 2026-02-04
**Status**: Draft
**Input**: User description: "Create a specification for the Gamma (Visibility) Tensor - measures fraction of labor-time that survives transformation to price-space through two mechanisms: International (ERDI-based compression) and Reproductive (naturalization of domestic labor)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Reproductive Labor Visibility (γ_III) (Priority: P1)

As a simulation researcher, I need to compute the reproductive labor visibility coefficient (γ_III) to quantify how much domestic care labor is invisible to the price system, enabling accurate shadow subsidy calculations.

**Why this priority**: γ_III is the core deliverable that enables quantification of the ~$2.3 trillion annual reproductive shadow subsidy. This is foundational for all other visibility calculations and directly integrates with existing ATUS and QCEW data infrastructure.

**Independent Test**: Can be fully tested by computing γ_III for the national aggregate using ATUS unpaid hours and QCEW care sector employment, validating the result falls within the expected range [0.20, 0.40].

**Acceptance Scenarios**:

1. **Given** ATUS annual unpaid care hours and QCEW care sector employment hours are available, **When** I compute γ_III using the formula `L_paid_care / (L_paid_care + L_unpaid_care)`, **Then** the result is a value between 0.0 and 1.0, with expected national value approximately 0.25-0.35
2. **Given** complete QCEW data for NAICS sectors 61, 62, 624, and 814, **When** I aggregate paid care hours, **Then** the total reflects formal + informal care employment
3. **Given** γ_III is computed for multiple years, **When** I analyze trends against female labor force participation, **Then** γ_III shows positive correlation (more women in workforce leads to more commodified care)

______________________________________________________________________

### User Story 2 - Calculate Reproductive Shadow Subsidy (Priority: P1)

As a simulation researcher, I need to calculate the dollar value of the reproductive shadow subsidy to quantify the hidden value transfer from unpaid domestic labor to capital.

**Why this priority**: The shadow subsidy calculation is the practical output that demonstrates theoretical significance. Combined with MELT, this produces the ~$2.3 trillion annual figure that parallels imperial extraction.

**Independent Test**: Can be tested by computing the shadow subsidy using the formula and validating the magnitude is in the $1.5-3.5 trillion range.

**Acceptance Scenarios**:

1. **Given** γ_III = 0.30, total unpaid care hours = 50 billion/year, and MELT = $65/hour, **When** I compute the shadow subsidy, **Then** the result approximates $2.3 trillion (order of magnitude validation)
2. **Given** γ_III and unpaid hours are available, **When** MELT is unavailable, **Then** the system returns the shadow subsidy in labor-hours instead of dollars
3. **Given** per-household reproductive hours, **When** I compute household-level subsidy, **Then** the subsidy equals (1 - γ_III) multiplied by hours multiplied by MELT

______________________________________________________________________

### User Story 3 - Compute International Import Visibility (Priority: P2)

As a simulation researcher, I need to compute the weighted-average visibility of imported goods based on ERDI (Exchange Rate Deviation Index) to quantify imperial extraction through unequal exchange.

**Why this priority**: Completes the visibility tensor by adding the international mechanism. Depends on Penn World Tables ERDI data which may require Phase 2 implementation or hardcoding initial values.

**Independent Test**: Can be tested by computing import visibility for known import shares and ERDI values, validating the result falls within [0.40, 0.70].

**Acceptance Scenarios**:

1. **Given** import shares by country of origin and ERDI values per country, **When** I compute import visibility as the sum of (import_share[origin] multiplied by 1/ERDI[origin]), **Then** the result falls in expected range [0.40, 0.70]
2. **Given** ERDI data shows China = 1.8, Vietnam = 2.5, Mexico = 1.5, **When** these countries represent significant import shares, **Then** visibility per origin = 1/ERDI correctly computes visibility per origin
3. **Given** imports from core countries (ERDI approximately 1.0), **When** I compute visibility, **Then** visibility = 1.0 (no compression)

______________________________________________________________________

### User Story 4 - Compute Consumption Basket Visibility (Priority: P2)

As a simulation researcher, I need to compute the combined visibility of the US consumption basket (domestic + imports) to determine the labor aristocracy threshold.

**Why this priority**: Basket visibility is the composite visibility that determines class position via wage comparison to MELT times basket visibility. It synthesizes domestic (visibility=1) and imported (visibility<1) consumption.

**Independent Test**: Can be tested by computing basket visibility from import share and import visibility, validating the formula produces expected values.

**Acceptance Scenarios**:

1. **Given** import share = 0.35 and import visibility = 0.50, **When** I compute basket visibility, **Then** result approximately 0.74 per the harmonic formula
2. **Given** import share = 0 (no imports), **When** I compute basket visibility, **Then** result = 1.0 (all domestic, fully visible)
3. **Given** import share = 1.0 (all imports), **When** I compute basket visibility, **Then** result = import visibility

______________________________________________________________________

### User Story 5 - Compute Imperial Shadow Subsidy (Priority: P3)

As a simulation researcher, I need to calculate the dollar value of the imperial shadow subsidy from consumption to compare against the reproductive subsidy.

**Why this priority**: Completes the "two subsidies" framework. Lower priority because it requires basket visibility which depends on US3 and US4.

**Independent Test**: Can be tested by computing imperial subsidy and validating magnitude approximates $2 trillion/year.

**Acceptance Scenarios**:

1. **Given** basket visibility = 0.74 and annual consumption = $15 trillion, **When** I compute imperial subsidy, **Then** result approximates $3.9 trillion (imperial extraction component of consumption)
2. **Given** basket visibility and total consumption, **When** I compute shadow values, **Then** shadow imperial + visible consumption = total consumption

______________________________________________________________________

### Edge Cases

- **What happens when ATUS data is unavailable?** System returns NoDataSentinel with reason "ATUS unpaid hours unavailable"
- **What happens when QCEW care sector data is missing for some NAICS codes?** System computes with available data and flags partial coverage
- **What happens when ERDI data is unavailable for a trade partner?** System defaults to ERDI = 1.0 (core assumption) and logs warning
- **What happens when import share data is unavailable?** System uses latest available year with warning
- **How does system handle visibility = 0 (all unpaid)?** Returns 0.0 with warning about extreme value
- **How does system handle division by zero in visibility calculations?** Returns 0.0 when total hours = 0

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute reproductive visibility (γ_III) as paid care hours divided by total care hours (paid + unpaid)
- **FR-002**: System MUST aggregate paid care hours from QCEW NAICS codes: 61 (Education), 62 (Healthcare), 624 (Social Assistance), 814 (Private Households)
- **FR-003**: System MUST retrieve unpaid care hours from ATUS time-use data
- **FR-004**: System MUST compute import visibility as weighted average of visibility per origin country (1/ERDI[origin])
- **FR-005**: System MUST compute basket visibility using harmonic formula combining domestic and import visibility
- **FR-006**: System MUST compute reproductive shadow subsidy as (1 - γ_III) multiplied by unpaid hours multiplied by MELT
- **FR-007**: System MUST compute imperial shadow subsidy as (1 - basket visibility) multiplied by consumption
- **FR-008**: All visibility values MUST be constrained to range [0.0, 1.0]
- **FR-009**: System MUST return NoDataSentinel with descriptive reason when required data is unavailable
- **FR-010**: System MUST log warnings when computed values fall outside expected ranges (γ_III: [0.20, 0.40], import visibility: [0.40, 0.70], basket visibility: [0.60, 0.85])
- **FR-011**: System MUST support intensive aggregation (weighted-average) of visibility values
- **FR-012**: System MUST NOT apply visibility coefficients to domestic core/periphery relations (use throughput position instead)

### Key Entities

- **GammaComponents**: Composite visibility coefficients for a location-year including import visibility, basket visibility, reproductive visibility, and derived properties
- **GammaIII**: Reproductive labor visibility with decomposition by category (domestic unpaid=0.0, formal care=1.0, informal care approximately 0.4)
- **ShadowSubsidy**: Value transfer calculations for both imperial (from basket visibility) and reproductive (from γ_III) mechanisms
- **ERDIData**: Exchange Rate Deviation Index by country, sourced from Penn World Tables

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reproductive visibility computed for national aggregate falls within [0.20, 0.40] range
- **SC-002**: Reproductive visibility shows expected directional behavior: higher paid care employment produces higher γ_III (validated via synthetic scenarios with varying paid/unpaid hour ratios). Full multi-year correlation with BLS female labor force participation deferred to FE-003.
- **SC-003**: Reproductive shadow subsidy magnitude is $1.5-3.5 trillion/year (order of magnitude check)
- **SC-004**: Import visibility computed from trade data falls within [0.40, 0.70] range
- **SC-005**: Basket visibility computed from import share and import visibility falls within [0.60, 0.85] range
- **SC-006**: Imperial shadow subsidy magnitude is $1.0-4.0 trillion/year
- **SC-007**: All edge cases (missing data, zero hours, extreme values) handled without system crashes
- **SC-008**: Fortunati exploitation rate computed as (1 - γ_III) / γ_III equals approximately 2.0-3.0 for typical γ_III values

## Assumptions

- ATUS time-use data loader exists (spec 005) and provides national unpaid care hours
- QCEW data infrastructure exists with access to NAICS sector employment
- MELT calculation exists from Feature 013 for dollar conversions
- Penn World Tables ERDI data will be hardcoded initially if loader not available
- Import share data available from Census Trade Data or BEA I-O Tables
- Department III (reproductive) labor has no throughput position - it is location-bound

## Constraints

- Visibility applies ONLY to international (ERDI) and reproductive (naturalization) mechanisms
- Visibility does NOT apply to domestic core/periphery geography (use throughput position from Feature 014)
- All visibility values are intensive properties (weighted-average under aggregation)
- ATUS provides national-level data only; county allocation requires demographic proxying (out of scope for MVP)

## Dependencies

- **Requires**: Feature 014 (Throughput Position) for throughput distinction and QCEW adapters
- **Requires**: Feature 005 (ATUS Department III) for unpaid care hours
- **Requires**: Feature 013 (MELT Basket Visibility) for MELT calculation
- **Data**: ATUS, QCEW care sectors (61, 62, 624, 814), Penn World Tables ERDI

## Future Enhancements

- **FE-001**: County-level reproductive visibility estimation via demographic proxy allocation
- **FE-002**: Penn World Tables loader for ERDI data (vs hardcoded values)
- **FE-003**: Time series analysis of visibility trends and commodification dynamics, including multi-year correlation of γ_III with BLS female labor force participation rates (original SC-002)
- **FE-004**: Integration with profit rate calculations (true vs apparent profit rate)
