# Feature Specification: Capital Volume III Integration

**Feature Branch**: `024-capital-volume-iii`
**Created**: 2026-02-25
**Status**: Draft
**Input**: User description: "Capital Volume III Integration: Distribution of Surplus Value - Interest, Rent, and Fictitious Capital"

## Clarifications

### Session 2026-02-25

- Q: How should national-level financial data (FRED interest rates, credit aggregates, fictitious capital) map to county-level simulation state? → A: Hybrid model -- national financial state (interest rates, credit aggregates, fictitious capital stock, credit cycle phase) stored as shared national parameters; only rent and housing data are county-specific. Counties reference shared national values plus county-specific adjustments (e.g., county profit rate determines local interest burden).
- Q: How are the surplus value distribution shares (interest, rent, taxes, profit) determined? → A: Data-driven from federal sources (BEA rental income for rent, FRED interest data for interest, IRS tax data for taxes). Profit of enterprise is the residual: p = s - i - r - t.
- Q: Are concrete data loader implementations part of this feature or deferred? → A: Full data loaders included. This feature implements FRED API integration (interest rates, credit aggregates), Fed Z.1 financial accounts parsing, and Census/ACS housing data ingestion alongside the protocol interfaces.
- Q: What is the complete valid transition graph for credit cycle phases? → A: Directed cycle with shortcuts. Main cycle: EXPANSION → OVEREXTENSION → CRISIS → RECOVERY → EXPANSION. Shortcuts to STAGNATION: OVEREXTENSION → STAGNATION and RECOVERY → STAGNATION. No other transitions are valid.
- Q: How should surplus value distribution handle negative surplus? → A: Interest and rent obligations persist at data-driven levels (contractual, not voluntary). Enterprise profit absorbs the full shortfall as a negative value (loss). The accounting identity s = p + i + r + t still holds with p < 0. A separate debt accumulation field tracks cumulative shortfall across ticks to model the debt spiral.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Surplus Value Distribution Accounting (Priority: P1)

As a simulation operator, I need the system to track how total surplus value produced in each county divides among competing claimants (industrial profit, interest, ground rent, taxes), so that I can observe the material basis of class conflict between industrial capitalists, money-capitalists, and landowners.

Currently the system produces surplus value (`s` in ValueTensor4x3) and tracks it through circulation (Feature 023), but surplus value is treated as a monolithic quantity. In reality, surplus value is distributed among multiple claimants, and the *shares* of distribution shift over time, creating inter-capitalist conflict that shapes crisis dynamics.

The accounting identity `s = profit_of_enterprise + interest + rent + taxes` must hold at all times.

**Why this priority**: This is the foundational data model that all other Volume III stories depend on. Without the distribution split, interest, rent, and credit dynamics have nowhere to write their outputs.

**Independent Test**: Can be fully tested by providing a known surplus value and verifying the distribution sums to total `s`, with each component within valid bounds.

**Acceptance Scenarios**:

1. **Given** a county with computed surplus value `s >= 0`, **When** the distribution step runs, **Then** interest, rent, and taxes are each non-negative and the four components sum to `s` within floating-point epsilon. Enterprise profit may be negative if claims exceed surplus.
2. **Given** a county with zero surplus value, **When** distribution runs, **Then** all distribution components are zero (no value can be distributed that was not produced).
3. **Given** rising interest rates, **When** distribution runs across multiple ticks, **Then** the interest share of surplus rises while enterprise profit share falls (interest crowds out profit).

______________________________________________________________________

### User Story 2 - Interest-Bearing Capital and Credit Dynamics (Priority: P1)

As a simulation operator, I need the system to model interest rate dynamics and credit expansion/contraction cycles, so that I can observe how the credit system simultaneously accelerates accumulation and creates financial fragility.

Interest is bounded above by the profit rate (no industrial capitalist borrows at rates exceeding profit). The interest rate has no "natural" level but moves counter-cyclically: low during expansion (abundant credit), high during crisis (credit crunch). The credit system enables overproduction beyond actual purchasing power.

**Why this priority**: Interest-bearing capital is the mechanism through which financial crises propagate. Without credit dynamics, the existing crisis detection (Feature 018) cannot model the credit crunch that transforms production crises into systemic collapses.

**Independent Test**: Can be fully tested by providing known profit rates and credit conditions and verifying interest rate bounds, credit cycle phase detection, and crisis propagation mechanics.

**Acceptance Scenarios**:

1. **Given** a national interest rate and county-level profit rate, **When** interest is calculated, **Then** the effective interest rate for industrial borrowers never exceeds the county profit rate.
2. **Given** a credit state with positive expansion rate, falling profit rate trend, and rising defaults, **When** credit cycle phase is evaluated, **Then** the system identifies the OVEREXTENSION phase (expansion despite profit decline).
3. **Given** a county in DEEP crisis (Feature 018), **When** the credit system evaluates conditions, **Then** credit spreads widen, credit growth contracts, and default rates rise.
4. **Given** a recovery phase with rising profit rates, **When** credit conditions are assessed, **Then** credit gradually re-expands and spreads narrow.

______________________________________________________________________

### User Story 3 - Fictitious Capital Accumulation (Priority: P2)

As a simulation operator, I need the system to track the accumulation of fictitious capital (financial assets whose value derives from capitalization of expected future income rather than labor-value), so that I can observe the growing divergence between paper claims and real production capacity that precedes financial crises.

Fictitious capital includes government debt, corporate equity, corporate debt, household debt, and derivatives. Marx observed that the credit system makes "all capital seem to double itself, and sometimes treble itself" -- the ratio of fictitious to real capital is a structural crisis indicator.

**Why this priority**: The financialization ratio (fictitious/real capital) is a leading crisis indicator. Historical pattern: ratio peaked before 1929 crash, began secular rise in 1980s, peaked before 2008 crash, remains at all-time highs.

**Independent Test**: Can be fully tested by providing known real GDP, debt levels, and equity values, then verifying the financialization index calculation and its correlation with crisis phase transitions.

**Acceptance Scenarios**:

1. **Given** known government debt, corporate equity, corporate debt, and household debt levels, **When** fictitious capital stock is calculated, **Then** total claims equal the sum of all components (excluding derivatives notional).
2. **Given** a county with $1M real capital and $2.5M total fictitious claims, **When** the financialization ratio is computed, **Then** the ratio equals 2.5 (capital has been "doubled and then some").
3. **Given** historical data showing ratio exceeding a high threshold during DEEP crisis phase, **When** crisis assessment includes financialization, **Then** the overaccumulation signal activates.

______________________________________________________________________

### User Story 4 - Ground Rent Extraction (Priority: P2)

As a simulation operator, I need the system to model ground rent as a distinct claim on surplus value arising from monopoly over non-reproducible natural conditions (land, resources, location), so that I can observe how rent extraction drains industrial profit and shapes territorial inequality.

Ground rent has two forms: differential rent (surplus profit from better land/location captured by landowner) and absolute rent (exists even on worst land because landowners demand payment for access). Rent is particularly important for the Detroit gentrification model where housing combines ground rent, interest, and speculative fictitious capital.

**Why this priority**: Rent extraction is essential for modeling territorial dynamics. Housing costs (rent + mortgage interest) are the primary mechanism through which surplus value is extracted from workers outside the workplace. This directly connects to existing Territory system heat dynamics and eviction pipeline.

**Independent Test**: Can be fully tested by providing known rental income data, total surplus, and housing values, then verifying rent decomposition and share calculations.

**Acceptance Scenarios**:

1. **Given** county-level rental income data (agricultural, resource, urban), **When** total ground rent is calculated, **Then** it equals the sum of all rent categories.
2. **Given** total surplus value and total rent extraction, **When** the rentier share is computed, **Then** it equals rent/surplus and falls within [0, 1].
3. **Given** county housing data with construction value, location rent, and speculative premium, **When** the housing value decomposition runs, **Then** the fictitious fraction (rent + speculation divided by market price) is computed correctly.
4. **Given** a HIGH_PROFILE territory with rising heat, **When** ground rent is assessed alongside territory dynamics, **Then** rising rent correlates with increased eviction pressure.

______________________________________________________________________

### User Story 5 - Counter-Tendencies to the Falling Rate of Profit (Priority: P3)

As a simulation operator, I need the system to track the six counter-tendencies that offset the tendency of the rate of profit to fall (TRPF), so that I can observe why capitalism does not immediately collapse despite the tendency, and how the balance between tendency and counter-tendency shifts over time.

Marx identified: (1) increasing exploitation rate, (2) depression of wages below value, (3) cheapening of constant capital, (4) relative surplus population (reserve army), (5) foreign trade / imperial rent, (6) increase in stock capital (fictitious profits). The existing TRPF detector (Feature 018) tracks the *tendency* but not the *counter-tendencies*.

**Why this priority**: Counter-tendencies explain the cyclical nature of crisis rather than immediate collapse. They complete the TRPF analysis that is already partially implemented.

**Independent Test**: Can be fully tested by providing indicator values for each counter-tendency and verifying the net tendency calculation and its relationship to crisis phase transitions.

**Acceptance Scenarios**:

1. **Given** year-over-year changes in exploitation rate, wage suppression, capital goods prices, unemployment, imperial rent flow, and financial sector profit share, **When** counter-tendency strength is computed, **Then** a positive net value indicates counter-tendencies dominating, negative indicates TRPF dominating.
2. **Given** a scenario where counter-tendencies are weakening (exploitation rate plateau, wages rebounding, reserve army shrinking), **When** the TRPF analysis runs, **Then** it predicts acceleration of profit rate decline.
3. **Given** counter-tendency data and profit rate trajectory, **When** both are evaluated together, **Then** the sign of net counter-tendency correlates with profit rate direction (positive net = rising/stable profit, negative net = falling).

______________________________________________________________________

### User Story 6 - Integrated Financial Crisis Assessment (Priority: P3)

As a simulation operator, I need the system to integrate financial crisis indicators (credit fragility, overaccumulation, profit squeeze) with existing production and circulation crisis assessments (Features 018, 023), so that I can observe the complete crisis cascade from overproduction through credit crunch to devaluation.

Marx's insight: crisis appears as a money/credit crisis but the underlying cause is overproduction relative to profitable realization. The credit system delays but ultimately amplifies crisis.

**Why this priority**: This is the capstone integration that connects all Volume III components with the existing crisis framework to model complete crisis dynamics.

**Independent Test**: Can be fully tested by providing production state (Feature 018), circulation state (Feature 023), and financial state (this feature), then verifying the integrated assessment correctly identifies crisis cascade phases.

**Acceptance Scenarios**:

1. **Given** a profit rate squeeze (interest burden exceeds threshold), overaccumulation signal (financialization ratio exceeds threshold), and credit fragility indicator (default rate times spread exceeds threshold), **When** integrated crisis assessment runs, **Then** it identifies all three conditions and determines an overall crisis phase.
2. **Given** a county in NORMAL production state but with rising financialization ratio and expanding credit, **When** integrated assessment evaluates, **Then** it identifies latent financial vulnerability despite surface stability.
3. **Given** a crisis cascade (production crisis first, then circulation crisis, then credit crisis), **When** assessment evaluates the sequence, **Then** it tracks the progression through distinct phases.

______________________________________________________________________

### User Story 7 - Inflation and Value Basis Conversion (Priority: P3)

As a simulation operator, I need the system to express economic values in multiple bases (nominal dollars, real/inflation-adjusted dollars, and labor-time hours), so that I can distinguish genuine changes in material conditions from nominal monetary effects.

Marx distinguished between commodity money (intrinsic labor-value), credit money (promises to pay), and fiat money (state-enforced symbols). Inflation occurs when money supply grows faster than commodity production. All tensor values should be expressible in nominal, real, and labor-time terms.

**Why this priority**: Without value basis conversion, monetary inflation can mask real changes in exploitation, profit rates, and surplus distribution. This is especially important for multi-year simulation runs.

**Independent Test**: Can be fully tested by providing CPI data, GDP deflator, and total labor hours, then verifying correct conversion between nominal, real, and labor-time representations.

**Acceptance Scenarios**:

1. **Given** a nominal value, CPI index, and base year, **When** nominal-to-real conversion runs, **Then** the result equals nominal * (base_CPI / current_CPI).
2. **Given** a nominal GDP value and total annual labor hours, **When** SNLT-per-dollar is computed, **Then** it equals total_hours / nominal_GDP.
3. **Given** a nominal value and SNLT-per-dollar ratio, **When** nominal-to-labor-time conversion runs, **Then** the result is in hours and equals nominal * SNLT_per_dollar.

______________________________________________________________________

### Edge Cases

- What happens when surplus value is negative (losses)? Interest and rent obligations persist at data-driven levels. Enterprise profit absorbs the full shortfall (goes negative). A cumulative debt accumulation field tracks the running shortfall across ticks, modeling the debt spiral that deepens crisis.
- What happens when the profit rate equals zero? Interest must be zero (cannot borrow at rate exceeding profit), and credit should contract.
- What happens when fictitious capital data is unavailable for a county? Use `NoDataSentinel` with appropriate reason string; do not guess.
- What happens when credit expansion reaches extreme values? Apply reasonable upper bounds to prevent numerical overflow in financialization ratio.
- What happens when rent exceeds surplus? This represents a pathological state (landowner claims exceeding production). The system must flag this as a structural crisis condition rather than silently capping.
- What happens during multi-year simulation when CPI data spans inconsistent base years? The system must normalize all price indices to a common base year before conversion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST decompose surplus value into four distribution channels (profit of enterprise, interest, ground rent, taxes) that sum to total surplus within floating-point epsilon. Interest, rent, and taxes are derived from federal data sources; profit of enterprise is the residual (p = s - i - r - t).
- **FR-002**: System MUST track interest-bearing capital dynamics including effective interest rate, credit expansion/contraction rate, default rate, and credit spread relative to risk-free rate.
- **FR-003**: System MUST enforce the constraint that effective interest rate for industrial borrowers does not exceed the county profit rate.
- **FR-004**: System MUST track fictitious capital stock across five categories: government debt, corporate equity, corporate debt, household debt, and derivatives notional value.
- **FR-005**: System MUST compute the financialization index (total fictitious claims divided by real GDP) as a crisis indicator.
- **FR-006**: System MUST classify credit cycle phase as one of: EXPANSION, OVEREXTENSION, CRISIS, RECOVERY, or STAGNATION based on profit rate trend and credit growth. Valid transitions: EXPANSION → OVEREXTENSION → CRISIS → RECOVERY → EXPANSION (main cycle), plus OVEREXTENSION → STAGNATION and RECOVERY → STAGNATION (shortcuts). No other transitions are permitted.
- **FR-007**: System MUST decompose ground rent into three categories: agricultural rent, resource rent, and urban/building-site rent.
- **FR-008**: System MUST decompose housing value into three components: construction labor-value, capitalized ground rent, and speculative premium.
- **FR-009**: System MUST compute the fictitious fraction of housing price (capitalized rent plus speculative premium divided by market price).
- **FR-010**: System MUST track six TRPF counter-tendencies: increasing exploitation rate, wage depression below value, cheapening of constant capital, relative surplus population size, imperial rent flow magnitude, and fictitious profit share.
- **FR-011**: System MUST compute net counter-tendency strength as a signed aggregate: positive when counter-tendencies dominate, negative when TRPF dominates.
- **FR-012**: System MUST integrate financial crisis indicators (profit squeeze, overaccumulation, credit fragility) with existing production crisis (Feature 018) and circulation crisis (Feature 023) into a unified crisis assessment.
- **FR-013**: System MUST support value expression in three bases: nominal dollars, real (inflation-adjusted) dollars, and labor-time (SNLT hours).
- **FR-014**: System MUST persist all new county-level financial state via the existing graph bridge pattern (tick_* prefixed territory node attributes).
- **FR-015**: System MUST return `NoDataSentinel` with descriptive reason when federal data sources (FRED, Z.1, Census) lack coverage for a requested county-year combination.
- **FR-016**: System MUST detect the pathological state where rent plus interest claims exceed total surplus value and flag it as a structural crisis condition.
- **FR-017**: System MUST provide concrete data loaders for FRED (interest rates: FEDFUNDS, T10Y2Y, BAA-AAA spread; credit aggregates: TCMDO; government debt: GFDEBTN; stock market cap: WILSHIRE), Fed Z.1 Financial Accounts (sectoral debt and equity totals), and Census/ACS housing data (median home values, gross rent, construction cost indices).
- **FR-018**: Each data loader MUST implement the corresponding protocol interface and handle missing data by returning NoDataSentinel with source-specific reason strings.
- **FR-019**: System MUST track cumulative debt accumulation at the county level when enterprise profit is negative (interest + rent + taxes exceed surplus). Debt increases when p < 0 and decreases when positive surplus is applied to retire accumulated debt.

### Key Entities

- **SurplusValueDistribution**: Represents the decomposition of total surplus value into competing claims (profit of enterprise, interest, rent, taxes) for a given county-year. Validates the accounting identity s = p + i + r + t.
- **InterestRateState**: Captures the national interest rate environment including base rate, class-differentiated spreads, and effective borrowing rates. Stored at national level; county-level interest burden derived from national rate combined with county profit rate.
- **CreditState**: Tracks national credit system health including expansion rate, default rate, spread to risk-free rate, and money velocity. Stored at national level.
- **FictitiousCapitalStock**: Accumulated national financial claims (government debt, corporate equity/debt, household debt, derivatives) with ratio-to-real computation. Stored at national level.
- **CreditCyclePhase**: Categorical state of the credit cycle (EXPANSION, OVEREXTENSION, CRISIS, RECOVERY, STAGNATION).
- **RentExtraction**: Ground rent decomposition by category (agricultural, resource, urban) with share-of-surplus computation. Stored at county level.
- **HousingValueDecomposition**: Housing price split into construction value, capitalized ground rent, and speculative premium with fictitious fraction. Stored at county level.
- **CounterTendencyStrength**: Aggregate measure of the six identified counter-tendencies to TRPF with net signed indicator.
- **CreditCrisisIndicator**: Composite indicator combining overproduction signal, profit squeeze, and liquidity crisis flags.
- **DebtAccumulation**: Tracks cumulative shortfall when enterprise profit is negative across ticks. Stored at county level. Increases when p < 0 (interest + rent + taxes > surplus), decreases when p > 0 and surplus is applied to retire accumulated debt.
- **NationalFinancialParameters**: Container for all national-level financial state computed once per tick: InterestRateState, CreditState, FictitiousCapitalStock, CounterTendencyStrength, and MonetaryAdjustment. Extends the existing NationalTickParameters pattern.
- **MonetaryAdjustment**: Conversion factors between nominal, real, and labor-time value bases for a given year.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Surplus value accounting identity (s = p + i + r + t) holds within epsilon for 100% of county-year observations in simulation runs.
- **SC-002**: Interest rate constraint (effective rate <= county profit rate) is never violated across all simulation ticks.
- **SC-003**: Credit cycle phase transitions follow the valid state machine (EXPANSION → OVEREXTENSION → CRISIS → RECOVERY → EXPANSION main cycle, plus OVEREXTENSION → STAGNATION and RECOVERY → STAGNATION shortcuts) in 100% of observations.
- **SC-004**: Financialization index correctly identifies known historical crisis preconditions when backtested against pre-2008 data patterns.
- **SC-005**: Net counter-tendency sign correlates with profit rate direction (positive net = rising/stable, negative = falling) in at least 80% of simulation ticks.
- **SC-006**: Housing value decomposition components sum to market price within epsilon for all county observations.
- **SC-007**: All new county-level financial metrics are readable from the simulation graph via the existing graph bridge interface.
- **SC-008**: Value basis conversion is round-trip consistent: nominal -> real -> nominal produces original value within epsilon.
- **SC-009**: Integrated crisis assessment correctly identifies the three-stage cascade (production -> circulation -> financial) in scenario tests where crisis conditions are synthetically induced in sequence.
- **SC-010**: All new financial entity types are immutable (frozen) and use constrained Babylon types (Currency, Probability, Coefficient) rather than raw floats.

## Assumptions

- Federal Reserve (FRED) data for interest rates and credit aggregates will be accessible via the existing data loader protocol pattern, matching the approach used for QCEW and BEA data.
- The tax component of surplus distribution will initially use IRS corporate income tax data at the county level; more granular decomposition is deferred.
- Derivatives notional value is tracked for completeness but excluded from the primary financialization index due to double-counting concerns (derivatives are claims on claims).
- The housing value decomposition is particularly relevant for the Detroit focus area (Wayne County vs Oakland County) but will be implemented generically for all counties.
- Credit cycle phase detection uses heuristic thresholds rather than econometric modeling; threshold constants will be traceable to primary data sources per the project's threshold traceability standard.
- Imperial rent (Feature 013) already represents one component of counter-tendencies to TRPF (foreign trade / unequal exchange), so US5's counter-tendency tracker will reference existing phi_hour rather than duplicate it.
- The profit rate equalization / prices-of-production transformation (values -> prices) is out of scope for this feature; the system continues to use labor-values directly. The surplus distribution operates at county-aggregate level where Marx's first equality holds (total surplus = total profit). Federal data sources provide distribution shares already in price-space. The transformation matrix would only be required for per-industry surplus redistribution within counties, which is not in scope.

## Scope Boundaries

### In Scope

- Surplus value distribution accounting (profit, interest, rent, taxes)
- Interest rate state modeling and credit cycle dynamics
- Fictitious capital stock tracking and financialization metrics
- Ground rent extraction by category
- Housing value decomposition (construction, rent, speculation)
- TRPF counter-tendency tracking and net strength indicator
- Integrated financial crisis assessment
- Value basis conversion (nominal, real, labor-time)
- Graph bridge integration for all new metrics
- Data source protocols and concrete data loaders for FRED, Z.1, Census housing data

### Out of Scope

- Profit rate equalization / prices of production (transformation problem)
- Trinity Formula ideological mystification tracking
- Derivative pricing models or options valuation
- Real-time market data feeds or live financial API integration
- Monetary policy simulation (central bank decision-making)
- International capital flows between territories (covered by imperial rent)
- Commercial/merchant capital as distinct from industrial capital

## Dependencies

- **Feature 011** (Fundamental Tensor Primitive): Provides ValueTensor4x3 with surplus value `s`
- **Feature 013** (MELT/Basket/Visibility): Provides imperial rent Phi calculations
- **Feature 017** (Tick Dynamics System): Provides the orchestration pipeline and CountyEconomicState
- **Feature 018** (Crisis-Devaluation Mechanics): Provides CrisisPhase, bifurcation risk, wage compression
- **Feature 023** (Capital Volume II): Provides circulation state, turnover profiles, reproduction schema
