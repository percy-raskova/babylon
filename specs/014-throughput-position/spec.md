# Feature Specification: Throughput Position and Domestic Value Geography

**Feature Branch**: `014-throughput-position`
**Created**: 2026-02-02
**Status**: Draft
**Input**: User description: "Create a specification for Throughput Position and Domestic Value Geography."
**TVT Reference**: Implements domestic value geography theory from `ai-docs/brainstorms/tensor/tvt_throughput_extension.md`

## Summary

This specification defines how to measure and analyze domestic value geography within the US (single currency zone). Unlike international value transfer which operates through visibility (γ) and ERDI differentials, domestic geography operates through **throughput position** (π) - the relative flow of accumulated value through a location.

**Key Insight**: Within a single currency zone, wages track THROUGHPUT, not value creation. A retail worker in Manhattan handles enormous throughput but captures little (low λ), while an extraction worker in Appalachia creates value but sees little flow through (low π).

## Theoretical Foundation

### The Supply Chain Funnel

Value is created at extraction points and flows upward through coordination nodes. At each layer, wages are proportional to accumulated throughput, not local value creation:

| Depth | Layer | Examples | Characteristic |
|-------|-------|----------|----------------|
| d=0 | Extraction | Mines, farms, wells | Creates value, captures little |
| d=1 | Processing | Refineries, mills | Initial transformation |
| d=2 | Manufacturing | Factories, assembly | Secondary transformation |
| d=3 | Logistics | Ports, warehouses, distribution | Coordination chokepoints |
| d=4 | Services | Retail, healthcare, education | High throughput, variable λ |
| d=5 | Finance | Banks, funds, management | Highest throughput capture |

### Core Concepts

**Throughput Intensity** (τ_through): The amount of accumulated value flowing through a location per hour of local labor. This is NOT a local MELT - it measures throughput, not value creation.

**Throughput Position** (π): A county's throughput intensity relative to the national average. Values above 1.0 indicate coordination chokepoints; values below 1.0 indicate value creation/export nodes.

**Wage Share** (λ): The fraction of throughput captured as wages. This is an institutional variable determined by union density, skill scarcity, and bargaining power.

### The Wage Formula

Wages are the product of throughput and capture rate:
```
W = λ × τ_through
```

This explains why retail workers remain proletariat despite high throughput - they have high τ_through but λ ≈ 0.05. The longshoreman has both high τ_through AND high λ (strong union).

### Connection to Class Position

Throughput and wage share determine income. Income determines the rate of wealth accumulation. Accumulated wealth determines class position:

| Throughput (π) | Wage Share (λ) | Income (W) | Accumulation | Typical Class |
|----------------|----------------|------------|--------------|---------------|
| High | High | High | Fast | Labor Aristocracy |
| High | Low | Low | Slow/None | Proletariat |
| Low | Any | Low | Slow/None | Proletariat |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute County Throughput Position (Priority: P1)

Researchers analyzing domestic value geography need to compute the throughput position (π) for any US county, revealing whether it functions as a coordination chokepoint or value creation node.

**Why this priority**: Throughput position is the foundational metric for all domestic geography analysis. Without π, no supply chain depth or wage share analysis is possible.

**Independent Test**: Can be fully tested by retrieving BEA county GDP and QCEW employment for 2022, computing τ_through and π, and validating Detroit metro shows Oakland π > Wayne π.

**Acceptance Scenarios**:

1. **Given** BEA county GDP and QCEW employment for Oakland County (26125) in 2022, **When** computing throughput position, **Then** the system returns π > 1.0 (coordination chokepoint).

2. **Given** BEA county GDP and QCEW employment for Wayne County (26163) in 2022, **When** computing throughput position, **Then** the system returns π < Oakland's π (lower throughput than suburban coordination center).

3. **Given** New York County (36061 - Manhattan) data, **When** computing throughput position, **Then** the system returns one of the highest π values nationally (financial center).

4. **Given** a rural extraction county (e.g., Sweetwater County, WY - 56037, coal mining), **When** computing throughput position, **Then** the system returns π < 1.0 (value creation node, not coordination).

______________________________________________________________________

### User Story 2 - Calculate Supply Chain Depth (Priority: P1)

Economic analysts need to compute the average supply chain depth (D) for a county based on its industry mix, indicating whether it specializes in extraction, manufacturing, or coordination activities.

**Why this priority**: Supply chain depth complements throughput position by revealing WHY a county has its π value - whether it's at the extraction end or coordination end of value chains.

**Independent Test**: Can be fully tested by providing NAICS employment distribution for a county and computing weighted average depth using the NAICS-to-depth mapping.

**Acceptance Scenarios**:

1. **Given** NAICS employment distribution for a finance-heavy county (e.g., New York County), **When** computing supply chain depth, **Then** D > 4.0 (high coordination depth).

2. **Given** NAICS employment distribution for an extraction county (e.g., coal mining region), **When** computing supply chain depth, **Then** D < 1.5 (low extraction depth).

3. **Given** NAICS employment distribution for Oakland vs Wayne County, **When** computing supply chain depth, **Then** D[Oakland] > D[Wayne] (Oakland has higher-depth industries).

4. **Given** a county with missing NAICS employment data, **When** computing supply chain depth, **Then** the system returns a data unavailable indicator rather than a default value.

______________________________________________________________________

### User Story 3 - Estimate Wage Share by Industry (Priority: P2)

Labor economists need to estimate the wage share (λ) for industry-county combinations, revealing which sectors capture more of the value flowing through them.

**Why this priority**: Wage share explains why workers in high-throughput locations may still be proletariat (the Walmart effect). This connects throughput analysis to class position.

**Independent Test**: Can be fully tested by comparing λ for retail vs longshoremen in a port county, validating longshoremen have higher λ despite similar or lower τ_through.

**Acceptance Scenarios**:

1. **Given** QCEW average wages and county GDP for retail (NAICS 44-45), **When** computing wage share proxy, **Then** λ_retail < 0.10 (low capture despite high throughput).

2. **Given** QCEW average wages for transportation (NAICS 48-49) in a port county, **When** computing wage share proxy, **Then** λ_transport > λ_retail (higher union density).

3. **Given** QCEW wages for finance (NAICS 52) vs accommodation (NAICS 72), **When** computing wage share proxies, **Then** λ_finance > λ_accommodation (finance captures more throughput).

______________________________________________________________________

### User Story 4 - Analyze Throughput-Class Correlation (Priority: P2)

Policy researchers need to validate that throughput position (π) and wage share (λ) jointly predict class composition, confirming the theoretical model.

**Why this priority**: This validates the entire theoretical framework - that class position emerges from the interaction of throughput and institutional wage capture.

**Independent Test**: Can be fully tested by correlating county-level (π × λ) product with estimated LA share from wealth proxies.

**Acceptance Scenarios**:

1. **Given** throughput position and wage share data for multiple counties, **When** correlating (π × λ) with LA share estimates, **Then** correlation coefficient r > 0.5 (moderate positive correlation).

2. **Given** high-π, high-λ counties (e.g., port cities with strong unions), **When** examining class distribution, **Then** LA share exceeds national average (40%).

3. **Given** high-π, low-λ counties (e.g., retail distribution centers), **When** examining class distribution, **Then** proletariat share exceeds LA share despite high throughput.

______________________________________________________________________

### User Story 5 - Track Commuter Flows (Priority: P3)

Urban planners need to understand how labor flows between counties via commuting, revealing residence-work mismatches that affect where wages are spent vs where value flows.

**Why this priority**: Commuter flows add nuance to throughput analysis - a bedroom community may have low local π but residents work in high-π locations.

**Independent Test**: Can be fully tested by loading LODES data and computing net commuter flow for suburban vs urban counties.

**Acceptance Scenarios**:

1. **Given** LODES origin-destination data for Oakland County (26125), **When** computing net commuter flow, **Then** the system returns net inflow (more workers commute IN than OUT).

2. **Given** LODES data for a bedroom community county, **When** computing net commuter flow, **Then** the system returns net outflow (residents commute to work elsewhere).

3. **Given** commuter-adjusted throughput for a bedroom community, **When** comparing to raw throughput, **Then** adjusted π better predicts resident class composition.

______________________________________________________________________

### Edge Cases

- What happens when county GDP data is unavailable? Return data unavailable indicator with reason.
- What happens when NAICS employment breakdown is incomplete? Use available sectors, flag as partial estimate.
- What happens when π would compute to > 3.0 (extreme outlier)? Flag as outlier for review but do not cap.
- What happens for very small counties with few employers? Flag as low-confidence estimate due to small sample.
- What happens when computing λ and wages exceed GDP/employment? Indicates data quality issue - flag for review.

### Validation Case: Detroit Metro (Wayne vs Oakland)

The Detroit metro area provides a key validation case demonstrating domestic core-periphery dynamics:

- **Wayne County (26163)**: Contains Detroit proper - manufacturing legacy, lower π expected
- **Oakland County (26125)**: Northern suburbs - corporate headquarters, finance, higher π expected

**Expected Results**:
- π[Oakland] > π[Wayne]
- D[Oakland] > D[Wayne]
- LA_share[Oakland] > LA_share[Wayne] (from Feature 013)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute throughput intensity for any US county:
  ```
  τ_through[fips, year] = GDP[fips, year] / (employment[fips, year] × 2080)
  ```
  Units: $/labor-hour (throughput, not value creation)

- **FR-002**: System MUST compute throughput position relative to national MELT:
  ```
  π[fips, year] = τ_through[fips, year] / τ[year]
  ```
  Where τ[year] is the national MELT from Feature 013.

- **FR-003**: System MUST provide NAICS-to-supply-chain-depth mapping for all 2-digit NAICS sectors:
  | NAICS | Industry | Depth |
  |-------|----------|-------|
  | 11 | Agriculture | 0 |
  | 21 | Mining | 0 |
  | 22 | Utilities | 2 |
  | 23 | Construction | 2 |
  | 31-33 | Manufacturing | 1.5 (average) |
  | 42 | Wholesale | 3 |
  | 44-45 | Retail | 4 |
  | 48-49 | Transportation | 3 |
  | 51 | Information | 4 |
  | 52 | Finance | 5 |
  | 53 | Real Estate | 5 |
  | 54 | Professional Services | 4 |
  | 55 | Management | 5 |
  | 56 | Admin/Support | 3 |
  | 61 | Education | 4 |
  | 62 | Healthcare | 4 |
  | 71 | Entertainment | 4 |
  | 72 | Accommodation/Food | 4 |
  | 81 | Other Services | 3 |
  | 92 | Government | 4 |

- **FR-004**: System MUST compute employment-weighted average supply chain depth for a county:
  ```
  D[fips, year] = Σ_naics (employment[fips, naics, year] × depth[naics]) / Σ employment[fips, year]
  ```

- **FR-005**: System MUST compute wage share proxy for industry-county combinations:
  ```
  λ_proxy[fips, naics, year] = avg_wage[fips, naics, year] / τ_through[fips, year]
  ```
  Note: This is a proxy; true λ requires additional institutional data.

- **FR-006**: System MUST integrate with national MELT (τ) from Feature 013 to compute π.

- **FR-007**: System MUST return data unavailable indicators with descriptive reasons when required data cannot be computed.

- **FR-008**: System MUST validate computed values against sanity ranges:
  - τ_through: $20-200/hour expected range (flag outliers outside $10-500)
  - π: 0.2-3.0 expected range (flag extreme values for review)
  - D: 0-5 by definition (error if outside)
  - λ: 0-1 theoretical range (flag if > 1.0 indicating data quality issue)

- **FR-009**: System MUST support optional LODES commuter flow data for adjusted throughput analysis (future enhancement).

### Key Entities

- **ThroughputMetrics**: Container for county-level throughput analysis results.
  - Attributes: fips, year, tau_through ($/hour), pi (dimensionless ratio), supply_chain_depth (0-5 scale), is_estimated (boolean)

- **NAICSDepthMapping**: Mapping from 2-digit NAICS codes to supply chain depth values (0-5 scale).

- **WageShareEstimate**: Container for industry-county wage share proxy.
  - Attributes: fips, naics, year, lambda_proxy (0-1 ratio), confidence (high/medium/low based on data quality)

- **ThroughputCalculator**: Service that computes throughput position and related metrics for counties.

- **SupplyChainAnalyzer**: Service that computes supply chain depth from NAICS employment distributions.

### Data Sources

| Data Element | Source | Resolution | Purpose |
|--------------|--------|------------|---------|
| County GDP | BEA CAGDP1 | County, annual | τ_through numerator |
| County Employment | QCEW | County, annual | τ_through denominator |
| NAICS Employment | QCEW | County × NAICS, annual | Supply chain depth |
| NAICS Average Wages | QCEW | County × NAICS, annual | Wage share proxy |
| National MELT (τ) | Feature 013 | National, annual | π computation |
| Commuter Flows | LODES | County pairs, annual | Adjusted throughput (optional) |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Throughput position (π) can be computed for all US counties with available BEA and QCEW data (target: 3,000+ counties).

- **SC-002**: Detroit metro validation passes: π[Oakland] > π[Wayne] consistently across available years.

- **SC-003**: Supply chain depth computation produces expected rankings: finance centers (D > 4.5) > manufacturing (D ~ 2) > extraction (D < 1).

- **SC-004**: High-π counties show higher average wages when controlling for industry mix (validates throughput-wage relationship).

- **SC-005**: Product (π × λ) correlates positively with LA share estimates from Feature 013 (r > 0.4).

- **SC-006**: System handles missing data gracefully - returns data unavailable indicators for 100% of edge cases without crashes.

- **SC-007**: Wage share proxy λ < 0.15 for retail sector nationally, validating the "Walmart effect" theoretical prediction.

### Theoretical Predictions to Validate

- **P1**: τ_through correlates with supply chain depth D (higher-depth industries have higher throughput)
- **P2**: High-π, high-λ counties have higher LA share (wealth accumulation pathway)
- **P3**: High-π, low-λ counties have higher proletariat share (Walmart effect)
- **P4**: π predicts income; income predicts wealth accumulation rate

## Assumptions

- **A-001**: BEA county GDP adequately measures value throughput, not just local production. GDP includes the value of goods flowing through distribution and coordination, not only manufacturing output.

- **A-002**: Using 2080 hours/year as standard work-year is acceptable for τ_through calculation. This matches Feature 013's MELT calculation.

- **A-003**: The NAICS-to-depth mapping captures the essential structure of supply chains. Refinement (e.g., 3-digit NAICS) can improve accuracy but is not required for MVP.

- **A-004**: Wage share proxy (λ = avg_wage / τ_through) is a reasonable approximation when true institutional data (union density, bargaining outcomes) is unavailable.

- **A-005**: County boundaries are adequate for throughput analysis. Some economic activity crosses county lines, but county-level data is the finest resolution available from BEA/QCEW.

- **A-006**: Manufacturing depth is assigned 1.5 as an average because NAICS 31-33 spans both primary (depth 1) and secondary (depth 2) manufacturing.

## Dependencies

- **D-001**: Requires Feature 013 (MELT and Basket Visibility) for national MELT (τ) used in π calculation.

- **D-002**: Requires BEA CAGDP1 county GDP data - new data loader needed.

- **D-003**: Requires QCEW county employment by NAICS - may exist in data pipeline, verify availability.

- **D-004**: Requires QCEW county wages by NAICS - may exist in data pipeline, verify availability.

- **D-005**: Optionally requires LODES (Longitudinal Employer-Household Dynamics) for commuter flow analysis - new loader needed for future enhancement.

## Future Enhancements

- **FE-001**: Add 3-digit NAICS depth mapping for more granular supply chain analysis (e.g., distinguishing primary vs secondary manufacturing).

- **FE-002**: Implement LODES commuter flow integration to compute commuter-adjusted throughput.

- **FE-003**: Add union density data (BLS) to improve λ estimation beyond wage proxy.

- **FE-004**: Implement temporal analysis to track how π changes over time (deindustrialization dynamics).

- **FE-005**: Add port and airport throughput metrics from transportation statistics to validate logistics chokepoint identification.

- **FE-006**: Integrate with simulation engine to model how π changes affect class composition dynamics over time.
