# Feature Specification: MELT and Basket Visibility Computation

**Feature Branch**: `013-melt-basket-visibility`
**Created**: 2026-02-01
**Revised**: 2026-02-02 (wealth-based class position)
**Status**: Implementation Complete
**Input**: User description: "Create a specification for MELT and Basket Visibility Computation for determining Labor Aristocracy thresholds. MELT (τ) bridges labor-time and money-price. There is ONE national MELT per currency zone. γ_basket measures the imperial subsidy on the consumption basket. Together, τ and γ_basket determine the Labor Aristocracy threshold."
**TVT Reference**: Implements Axiom Groups B (Single-System Temporalism), C (International Value Transfer), D (Consumption Basket Visibility), and E (Class Position - REVISED) from `ai-docs/brainstorms/tensor/tvt_mathematical_formalization.md`

## Theoretical Clarification: Class vs Imperial Rent (2026-02-02)

**Class position** is determined by **wealth percentile** (accumulated extraction):
- LA = 50th-90th percentile wealth (~40% of population)
- They have positive net wealth and material stake in the system

**Imperial rent (Φ_hour)** measures **extraction rate** (flow):
- A proletarian CAN have Φ_hour > 0 (benefit from cheap imports)
- They consume rather than accumulate the imperial subsidy
- Φ_hour is used for aggregate drain validation (Hickel), NOT class position

This separation resolves the 30-50% vs 50-70% LA share debate:
- 40% LA emerges naturally from wealth distribution (50th-90th percentile)
- γ_basket stays empirically grounded (0.68)
- No parameter tuning required

### Class Structure (Wealth-Based)

| Class | Wealth Percentile | Pop Share | Wealth Share | Primary Characteristic |
|-------|-------------------|-----------|--------------|------------------------|
| Bourgeoisie | Top 1% | 1% | ~33% | Owns means of production |
| Petit Bourgeoisie | 90th-99th | 9% | ~33% | Small capital, professional-managerial |
| Labor Aristocracy | 50th-90th | 40% | ~33% | Positive net wealth, system stake |
| Proletariat | Bottom 50%, employed | ~35% | ~0% | No net wealth, sells labor |
| Lumpenproletariat | Bottom 50%, excluded | ~15% | ~0% | Outside formal labor market |

### What the Income Formulas Now Mean

| Formula | Measures | Used For |
|---------|----------|----------|
| τ_effective = τ × γ_basket | Imperial rent threshold | Φ_hour sign (net extractor or not) |
| Φ_hour = (W/τ)(1/γ_basket) - 1 | Hourly extraction rate | Aggregate drain validation (Hickel) |
| W vs τ_effective | Income position | Rate of wealth accumulation, NOT class |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute National MELT (Priority: P1)

Researchers analyzing labor-value relationships need to access the Monetary Expression of Labor Time (τ) for a given year, representing the dollars earned per hour of socially necessary labor nationally.

**Why this priority**: MELT is the foundational conversion factor between monetary and labor-time domains. Without τ[year], no class position calculations are possible. This is the enabling primitive for all imperial rent and labor aristocracy analysis.

**Independent Test**: Can be fully tested by retrieving BEA GDP and QCEW employment for 2022, computing τ = GDP / (employment × 2080), and validating the result falls within the expected $55-75/hour range.

**Acceptance Scenarios**:

1. **Given** BEA GDP data and QCEW national employment for year 2022, **When** requesting τ[2022], **Then** the system returns MELT computed as τ = GDP[2022] / (employment[2022] × 2080), with result in $/labor-hour units.

2. **Given** τ computed for 2022, **When** validating the result, **Then** τ falls within the sanity range $55-75/hour (outside $40-100 indicates data or calculation error).

3. **Given** QCEW data is unavailable for requested year, **When** requesting τ, **Then** the system returns NoDataSentinel with reason "National employment data unavailable for year YYYY".

______________________________________________________________________

### User Story 2 - Determine Class Position Thresholds (Priority: P1)

Economists studying class stratification need to access the three thresholds that define class position: τ_effective (labor aristocracy threshold), V_reproduction (subsistence floor), and τ (nominal MELT reference).

**Why this priority**: Class position determination is the primary use case for this feature. Without thresholds, counties cannot classify their workforce into labor aristocracy, proletariat, and subproletariat categories.

**Independent Test**: Can be fully tested by computing τ, γ_basket, and τ_effective for 2022, then classifying a set of wage rates into class positions.

**Acceptance Scenarios**:

1. **Given** τ = $65/hour and γ_basket = 0.68, **When** computing τ_effective, **Then** the system returns τ_effective = τ × γ_basket = $44.20/hour.

2. **Given** thresholds τ_effective = $44/hour and V_reproduction = $12/hour, **When** classifying wage W = $50/hour, **Then** classification returns "Labor Aristocracy" (W > τ_effective).

3. **Given** thresholds τ_effective = $44/hour and V_reproduction = $12/hour, **When** classifying wage W = $18/hour, **Then** classification returns "Proletariat" (τ_effective ≥ W > V_reproduction).

4. **Given** thresholds τ_effective = $44/hour and V_reproduction = $12/hour, **When** classifying wage W = $8/hour, **Then** classification returns "Subproletariat" (W ≤ V_reproduction).

______________________________________________________________________

### User Story 3 - Calculate Basket Visibility (Priority: P2)

Researchers analyzing imperial rent dynamics need to compute γ_basket, the visibility coefficient that measures how much the US consumption basket benefits from compressed peripheral labor.

**Why this priority**: Basket visibility determines the magnitude of imperial subsidy. However, for MVP, a hardcoded γ_basket ≈ 0.68 provides a reasonable approximation while data loaders are developed.

**Independent Test**: Can be fully tested by providing import share α = 0.25 and γ_import = 0.35, then verifying γ_basket = 1 / (α/γ_import + (1-α)) ≈ 0.68.

**Acceptance Scenarios**:

1. **Given** α = 0.25 (25% import share) and γ_import = 0.35, **When** computing γ_basket, **Then** the system returns γ_basket = 1 / (0.25/0.35 + 0.75) = 1/1.464 ≈ 0.683.

2. **Given** α = 0 (no imports), **When** computing γ_basket, **Then** the system returns γ_basket = 1.0 (no imperial subsidy when no imports).

3. **Given** α = 1 (100% imports), **When** computing γ_basket, **Then** the system returns γ_basket = γ_import (basket visibility collapses to import visibility when entire consumption is imported).

   **Algebraic derivation**: γ_basket = 1 / (1/γ_import + 0) = γ_import

4. **Given** γ_basket computed for 2022, **When** validating the result, **Then** γ_basket falls within range 0.60-0.80 (outside 0.4-0.95 indicates data error).

5. **Given** MVP mode enabled (default), **When** requesting γ_basket without import data, **Then** the system returns hardcoded γ_basket = 0.68 with a flag indicating "estimated" status.

______________________________________________________________________

### User Story 4 - County Workforce Classification (Priority: P2)

Policy analysts need to classify the workforce of a county into labor aristocracy, proletariat, and subproletariat shares using QCEW wage data and national thresholds.

**Why this priority**: Aggregating class position by county enables geographic analysis of imperial rent distribution. However, this depends on wage distribution data (OES or ACS) which may require additional loaders.

**Independent Test**: Can be fully tested by providing a mock wage distribution for Wayne County and verifying the classification sums to 100% with appropriate shares in each category.

**Acceptance Scenarios**:

1. **Given** national thresholds τ_effective = $44/hour and V_reproduction = $12/hour, and QCEW average wage for Wayne County = $28/hour, **When** classifying based on average wage, **Then** the county is classified as predominantly "Proletariat" (average wage between thresholds).

2. **Given** wage distribution data (from OES) for a county with percentiles, **When** classifying workforce, **Then** the system returns shares: labor_aristocracy_share + proletariat_share + subproletariat_share = 1.0.

3. **Given** national labor aristocracy share computed across all counties, **When** validating, **Then** the share falls within expected range 30-50% (outside 15-70% indicates model error).

______________________________________________________________________

### User Story 5 - Calculate Imperial Rent per Hour (Priority: P3)

Advanced analysts need to compute the imperial rent (Φ_hour) extracted by a worker earning wage W, representing the net hours of peripheral labor commanded through consumption.

**Why this priority**: Imperial rent calculation provides the quantitative foundation for MLM-TW theory. Lower priority because it requires the foundation of MELT and basket visibility to be in place.

**Independent Test**: Can be fully tested by computing Φ_hour for a $65/hour worker with τ = $65/hour and γ_basket = 0.68, verifying Φ_hour = (W/τ) × (1/γ_basket) - 1 ≈ 0.47.

**Acceptance Scenarios**:

1. **Given** W = $65/hour, τ = $65/hour, γ_basket = 0.68, **When** computing imperial rent, **Then** Φ_hour = (65/65) × (1/0.68) - 1 = 1.47 - 1 = 0.47 hours extracted per hour worked.

2. **Given** W = $30/hour, τ = $65/hour, γ_basket = 0.68, **When** computing imperial rent, **Then** Φ_hour = (30/65) × (1/0.68) - 1 = 0.68 - 1 = -0.32 (this worker is net exploited).

   **Theoretical bounds**: Negative Φ_hour occurs when W < τ_effective (wage below LA threshold). The lower bound approaches Φ_hour → -1 as W → 0. For typical US parameters (τ ≈ $65, γ_basket ≈ 0.68, τ_effective ≈ $44), workers earning below ~$44/hour have Φ_hour < 0. At $20/hour, Φ_hour ≈ -0.55. This captures the proletariat who, despite receiving imperial consumption subsidies (γ_basket < 1), still contribute more labor-value than they command.

3. **Given** W = τ_effective (break-even wage), **When** computing imperial rent, **Then** Φ_hour = 0 (worker neither extracts nor is extracted).

   **Algebraic proof**:
   ```
   W = τ_effective = τ × γ_basket
   Φ_hour = (W/τ) × (1/γ_basket) - 1
          = (τ × γ_basket / τ) × (1/γ_basket) - 1
          = γ_basket × (1/γ_basket) - 1
          = 1 - 1 = 0  ✓
   ```

______________________________________________________________________

### Edge Cases

- What happens when GDP or employment data is missing for a year? Return NoDataSentinel with descriptive reason.
- What happens when γ_basket would compute to > 1.0? Cap at 1.0 (cannot have negative imperial subsidy in this formulation).
- What happens when γ_basket would compute to ≤ 0? Return error (invalid import/ERDI data).
- What happens for years before 2010 (data range start)? Return NoDataSentinel (outside data range).
- What happens when V_reproduction threshold is higher than τ_effective? This is theoretically impossible but should be logged as warning (indicates data error).
- What happens when computing τ with zero employment? Return NoDataSentinel (cannot divide by zero).

### Validation Case: Detroit Metro (Wayne vs Oakland)

Per TVT political-theoretical exposition Section 4.2, the Detroit metro area provides a concrete validation case:

- **Wayne County (26163)**: Domestic periphery - more proletariat/subproletariat expected
- **Oakland County (26125)**: Domestic core - higher labor aristocracy share expected

Test: labor_aristocracy_share[Oakland] > labor_aristocracy_share[Wayne] consistently, demonstrating core-periphery wage stratification within the US.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute national MELT τ[year] per TVT Axiom B3:
  ```
  τ[year] = GDP[national, year] / L[national, year]
  ```
  Where L = total_employment × 2080 hours/year (standard work-year assumption).

- **FR-002**: System MUST compute basket visibility γ_basket per TVT Axiom D3:
  ```
  γ_basket[year] = 1 / (α/γ_import + (1 - α))
  ```
  Where α = import_share_of_consumption and γ_import = weighted average import visibility.

- **FR-003**: System MUST compute effective MELT τ_effective per TVT Axiom D4:
  ```
  τ_effective[year] = τ[year] × γ_basket[year]
  ```

- **FR-004**: System MUST provide reproduction floor V_reproduction per TVT Axiom E1:
  Default V_reproduction = $12/hour (2024 dollars), adjustable for inflation via CPI.

- **FR-005**: System MUST classify wage rates into class positions per TVT Axiom E2:
  - Labor Aristocracy: W > τ_effective
  - Proletariat: τ_effective ≥ W > V_reproduction
  - Subproletariat: W ≤ V_reproduction

- **FR-006**: System MUST compute imperial rent per hour per TVT Axiom E3:
  ```
  Φ_hour = (W/τ) × (1/γ_basket) - 1
  ```

- **FR-007**: System MUST compute labor commanded per hour per TVT Axiom E4:
  ```
  L_commanded = (W/τ) × (1/γ_basket)
  ```
  Labor aristocracy iff L_commanded > 1.

- **FR-008**: System MUST support MVP mode with hardcoded γ_basket = 0.68 when import/ERDI data is unavailable.

- **FR-009**: System MUST return NoDataSentinel with descriptive `.reason` attribute when requested data cannot be computed.

- **FR-010**: System MUST validate computed values against sanity ranges:
  - τ: $55-75/hour expected, $40-100 warning, fail outside $20-200
    - *Empirical basis*: US GDP ~$25T, employment ~150M, τ = 25T/(150M × 2080) ≈ $80/hour; historical range 2010-2024 spans $55-75
  - γ_basket: 0.60-0.80 expected, 0.4-0.95 warning, fail outside 0.1-1.0
    - *Empirical basis*: With α ≈ 0.25-0.35 (import share) and γ_import ≈ 0.35-0.60 (peripheral visibility), γ_basket = 1/(α/γ_import + (1-α)) yields 0.68-0.74
  - τ_effective: $35-55/hour expected, $25-70 warning
    - *Derived*: τ × γ_basket with above ranges
  - Labor aristocracy share: 30-50% expected, 15-70% warning
    - *Empirical basis*: Per TVT analysis, ~35% of US workers earn W > τ_effective, ~55% proletariat, ~10% subproletariat

- **FR-011**: System MUST cache computed annual parameters (τ, γ_basket, τ_effective) to avoid redundant calculations.

- **FR-012**: System MUST support inflation adjustment for V_reproduction using CPI data, with 2024 as base year.

### Key Entities

- **ClassPosition**: Enumeration for wealth-based class position (revised 2026-02-02):
  ```
  ClassPosition ∈ {BOURGEOISIE, PETIT_BOURGEOISIE, LABOR_ARISTOCRACY, PROLETARIAT, LUMPENPROLETARIAT}
  ```
  | Position | Wealth Percentile | Pop Share | Description |
  |----------|-------------------|-----------|-------------|
  | BOURGEOISIE | ≥ 99% | 1% | Owns means of production |
  | PETIT_BOURGEOISIE | 90-99% | 9% | Small capital, professional-managerial |
  | LABOR_ARISTOCRACY | 50-90% | 40% | Positive net wealth, system stake |
  | PROLETARIAT | < 50%, employed | ~35% | Sells labor, no net wealth |
  | LUMPENPROLETARIAT | < 50%, excluded | ~15% | Outside formal labor market |

  **Key insight**: Class position is determined by **wealth percentile** (stock), NOT income (flow).
  A proletarian CAN have Φ_hour > 0 while remaining proletarian—they consume rather than accumulate the imperial subsidy.

  **Backward compatibility**: The deprecated income-based classification (W vs τ_effective) is retained for imperial rent calculation and backward compatibility. Old SUBPROLETARIAT maps to LUMPENPROLETARIAT.

- **MELTCalculator**: Service that computes national MELT τ[year] from BEA GDP and QCEW employment. Caches computed values per year. Returns τ in $/labor-hour units, or NoDataSentinel with descriptive reason if data unavailable.

- **BasketVisibilityCalculator**: Service that computes γ_basket[year] from import shares and ERDI data. Supports MVP mode with hardcoded fallback.
  - **Input**: year (int), optional: α (import share), γ_import (peripheral visibility)
  - **Output**: γ_basket (dimensionless, 0 < γ_basket ≤ 1), or NoDataSentinel
  - **MVP behavior**: Returns hardcoded γ_basket = 0.68 with `estimated=True` flag when import/ERDI data unavailable

- **NationalParameters**: Immutable container holding annual parameters for a specific year. Used as input for all downstream calculations.
  - **Fields**: τ ($/labor-hour), α (dimensionless), γ_import (dimensionless), γ_basket (dimensionless), τ_effective ($/labor-hour), V_reproduction ($/labor-hour), year (int)
  - **Immutability rationale**: Parameters are point-in-time snapshots. Once computed for a year, they should not change during a simulation run. This enables caching and ensures consistent class position calculations across all consumers.

- **ClassPositionClassifier**: Service that classifies wage rates into class positions given NationalParameters.
  - **Input**: wage W ($/hour), NationalParameters
  - **Output**: ClassPosition enum value (LABOR_ARISTOCRACY | PROLETARIAT | SUBPROLETARIAT)
  - Supports both individual wage classification and county workforce distribution (returns shares summing to 1.0)

- **ImperialRentCalculator**: Service that computes imperial rent metrics for individual workers given wage and NationalParameters.
  - **Input**: wage W ($/hour), NationalParameters
  - **Output**: Φ_hour (labor-hours extracted per hour worked, can be negative), L_commanded (labor-hours commanded per hour worked, always ≥ 0)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: National MELT τ can be computed for all years 2010-2024 with available BEA/QCEW data, with results falling within expected range $55-75/hour.

- **SC-002**: Class position thresholds enable workforce classification with nationally aggregated results showing labor aristocracy share in range 30-50%, validating TVT theoretical predictions.

- **SC-003**: County-level classification produces expected core-periphery differentiation: Oakland County shows higher labor_aristocracy_share than Wayne County.

- **SC-004**: Imperial rent calculation produces values consistent with Hickel et al. estimates: average US worker Φ_hour > 0 (net extractors).

  **Definition of "average wage"**: Per CHK048 resolution, "average US worker" refers to the **arithmetic mean** hourly wage from QCEW national data (~$35/hour in 2022), not the median (~$28/hour). The mean is used because:
  1. Hickel et al. use aggregate measures that weight by total compensation
  2. SC-004 tests the *national average* extraction rate, not the typical worker's rate
  3. Mean wage > τ_effective validates the TVT prediction that "on average" US consumption extracts imperial rent

  **Clarification**: The **median** worker (at ~$28/hour) has Φ_hour < 0 (is exploited). This is expected: 50-60% of workers are proletariat. SC-004 uses mean to validate aggregate imperial rent flow, not individual worker experience.

- **SC-005**: System handles missing data gracefully, with NoDataSentinel returns for 100% of edge cases (no crashes or exceptions).

- **SC-006**: MVP mode with hardcoded γ_basket = 0.68 produces class distributions within 10% of expected values from literature.

- **SC-007**: All computed parameters integrate with existing economics module patterns (TensorRegistry, ValueTensor4x3, NoDataSentinel) without breaking existing consumers.

## Assumptions

- **A-001**: Using 2080 hours/year as standard work-year is acceptable for τ calculation. The systematic error cancels when comparing W/τ ratios. ACS mean hours could provide refinement in future.

- **A-002**: A single national τ (MELT) and γ_basket is appropriate for all US counties. Within a single currency zone:
  - **No ERDI differential**: PPP = MER domestically, so there is no exchange rate compression between regions
  - **No price-level distortion**: The same dollar buys the same basket of goods anywhere in the US (±5% regional variation via BEA RPP)
  - **γ_basket captures all imperial subsidy**: The visibility discount comes entirely from imported goods priced below their labor content

  Regional wage variation reflects throughput position (π), not visibility (γ). A Detroit auto worker and a San Francisco tech worker face the same τ and γ_basket; their class positions differ due to wage levels, not price levels.

- **A-003**: V_reproduction = $12/hour (2024 dollars) is an appropriate subsistence floor based on Census poverty thresholds and actual subsistence costs (~$25,000/year at 2080 hours).

- **A-004**: Hardcoded γ_basket ≈ 0.68 is a reasonable MVP approximation based on Hickel et al. methodology (unequal exchange via ERDI differentials) and trade data analysis. Derivation: with US import share α ≈ 0.25 and weighted average peripheral visibility γ_import ≈ 0.35, γ_basket = 1/(0.25/0.35 + 0.75) = 1/1.464 ≈ 0.68. Full computation requires Penn World Tables ERDI data and Census trade data loaders.

- **A-005**: ERDI (Exchange Rate Deviation Index) from Penn World Tables is the appropriate measure of international price distortion per TVT Axiom C1. ERDI is defined as:
  ```
  ERDI = PPP_rate / market_exchange_rate = GDP_PPP / GDP_MER = 1 / price_level
  ```
  For peripheral countries, ERDI > 1 indicates currency undervaluation relative to purchasing power, compressing the visibility of their labor in core consumption.

- **A-006**: County-level wage distribution can be approximated from QCEW average wages for MVP. Full distribution requires OES or ACS data loaders.

## Dependencies

- **D-001**: Requires Feature 012 (Capital Stock Dynamics) for integration with profit rate calculations and existing economics module patterns.

- **D-002**: Requires BEA GDP data (national) - currently available in data pipeline.

- **D-003**: Requires QCEW employment data (national) - currently available in data pipeline.

- **D-004**: Requires Penn World Tables 10.0 ERDI data (NEW LOADER NEEDED for full γ_basket calculation).

- **D-005**: Requires Census Trade Data for import shares by origin country (NEW LOADER NEEDED for full γ_basket calculation).

- **D-006**: Requires BEA Regional Price Parity for regional V_reproduction adjustment (optional, NEW LOADER NEEDED).

## Future Enhancements

Per TVT mathematical formalization (Sections 3-6), the following are identified as future extensions:

- **Penn World Tables Loader**: Implement `PWTLoader` to fetch ERDI by country from PWT 10.0, enabling computed (not hardcoded) γ_import.

- **Census Trade Data Loader**: Implement loader for import value by origin country, enabling computed import shares α and γ_import.

- **Regional V_reproduction**: Use BEA Regional Price Parity (RPP) to adjust V_reproduction by state/metro:
  ```
  V_reproduction[fips] = V_reproduction_national × RPP[fips] / 100
  ```

- **Wage Distribution Integration**: Integrate OES or ACS wage distribution data for precise county workforce classification rather than average-wage approximation.

- **Service Import Visibility**: Extend γ_basket to include service imports (call centers, software development) which don't appear in goods trade data but represent real labor arbitrage.

- **Domestic Subproletariat γ**: Model domestic production by undocumented workers as having implicit γ_domestic < 1, capturing value transfer that happens without crossing a border.

- **Time Series Tracking**: Track γ_basket[year] over time to validate TVT prediction P3: γ_basket should decrease as trade integration increases.
