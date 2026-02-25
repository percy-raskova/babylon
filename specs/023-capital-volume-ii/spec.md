# Feature Specification: Capital Volume II Integration

**Feature Branch**: `023-capital-volume-ii`
**Created**: 2026-02-25
**Status**: Draft
**Depends On**: Feature 011 (ValueTensor4x3), Feature 018 (Crisis Devaluation), Feature 021 (Capital Volume I)
**Input**: User description: "Capital Volume II Integration - The Circulation of Capital: Time, Turnover, and Reproduction"

## Overview

Where Volume I models **production** (extraction of surplus value via the ValueTensor4x3) and Volume III models **distribution** (tendency of the rate of profit to fall via TRPF formulas), Volume II models **circulation** — the movement of capital through its metamorphoses and the conditions for its reproduction.

This feature adds the temporal and circulatory dimensions missing from the existing static tensor. Capital is not a thing but a process: a continuous flow of value through Money (M), Productive (P), and Commodity (C) forms. The simulation currently captures value composition per tick but does not model **how long** capital takes to complete a circuit, **what form** capital currently occupies, or **whether departments exchange proportionally** for reproduction to continue.

**Core theoretical contributions:**
- **Circuit M-C-P-C'-M'**: Capital as state machine cycling through three forms
- **Turnover time**: Speed of circulation determines annual rate of surplus value
- **Fixed vs circulating capital**: Different components of constant capital have different temporalities (depreciation vs full consumption per cycle)
- **Reproduction schemata**: Inter-departmental balance conditions (I(v+s) = IIc) that must hold for accumulation to continue
- **Realization crisis**: Production does not guarantee sale; inventory accumulation signals crisis

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capital Circuit State Tracking (Priority: P1)

As a simulation designer, I want each economic entity's capital to be distributed across Money, Productive, and Commodity forms so that I can observe how capital circulates through its metamorphoses and identify where blockages occur (e.g., capital stuck in commodity form = realization problem).

**Why this priority**: The circuit (M-C-P-C'-M') is the foundational abstraction of Volume II. Without it, no other circulation dynamics can be modeled. This is the minimum viable representation of "capital as process."

**Independent Test**: Can be fully tested by creating a county with initial capital allocation across three forms, running a single tick, and verifying that capital transitions between forms according to turnover profile rules.

**Acceptance Scenarios**:

1. **Given** a county with $100M total capital, **When** the simulation initializes, **Then** capital is distributed across Money, Productive, and Commodity forms according to the county's industry mix turnover profile.
2. **Given** a county with capital in Productive form, **When** the production phase completes (working period elapses), **Then** the capital transitions to Commodity form with surplus value embodied (C' = c + v + s).
3. **Given** a county with capital in Commodity form, **When** the sale phase completes (sale time elapses), **Then** the capital transitions to Money form with surplus value realized (M' = M + delta_M).
4. **Given** a county with capital in Money form, **When** the purchase phase completes (purchase time elapses), **Then** the capital transitions to Productive form (means of production + labor power acquired).
5. **Given** a county's circuit state, **When** I query the liquidity ratio, **Then** I receive the fraction of total capital currently in Money form.
6. **Given** a county's circuit state, **When** I query the commodity overhang, **Then** I receive the fraction of total capital currently stuck in Commodity form.

______________________________________________________________________

### User Story 2 - Turnover Time and Annual Surplus Value (Priority: P1)

As a simulation designer, I want capital turnover time to vary by industry so that the annual rate of surplus value reflects how many times capital completes the M-C-P-C'-M' circuit per year, because faster turnover extracts more surplus from the same capital advanced.

**Why this priority**: Turnover time is what makes Volume II dynamics distinct from Volume I. Two counties with identical exploitation rates (s/v) but different turnover times will have different annual surplus extraction. This directly affects accumulation speed and competitive dynamics.

**Independent Test**: Can be fully tested by computing annual surplus value for two entities with identical per-cycle s/v but different turnover times, and verifying the faster turner produces proportionally more annual surplus.

**Acceptance Scenarios**:

1. **Given** an entity with s/v = 100% and turnover time of 2 months, **When** I calculate annual surplus value, **Then** the annual rate of surplus value = 600% (100% x 6 turnovers).
2. **Given** an entity with s/v = 100% and turnover time of 6 months, **When** I calculate annual surplus value, **Then** the annual rate of surplus value = 200% (100% x 2 turnovers).
3. **Given** an industry's turnover profile, **When** I decompose turnover time, **Then** I receive production time (working period + non-working production time) and circulation time (purchase time + sale time) separately.
4. **Given** two counties with the same industry mix, **When** one has shorter average sale times (better market access), **Then** that county's turnovers per year are higher and annual surplus extraction is greater.

______________________________________________________________________

### User Story 3 - Fixed vs Circulating Capital Decomposition (Priority: P2)

As a simulation designer, I want constant capital (c) decomposed into fixed capital (machinery, buildings) and circulating capital (raw materials, fuel) so that depreciation dynamics and the depreciation fund problem can be modeled, because fixed capital transfers value gradually while circulating capital transfers value completely each cycle.

**Why this priority**: The fixed/circulating distinction creates the temporal mismatch (continuous depreciation vs discrete replacement) that is the material basis for business cycles. Without it, the replacement investment wave and its crisis potential cannot be modeled.

**Independent Test**: Can be fully tested by creating a fixed capital item with known service life, running multiple ticks, and verifying that annual depreciation accumulates correctly and the depreciation fund tracks the amount reserved for replacement.

**Acceptance Scenarios**:

1. **Given** a fixed capital item worth $1M with 10-year service life, **When** I compute annual depreciation, **Then** the result is $100K/year (straight-line).
2. **Given** a fixed capital item aged 5 years, **When** I compute remaining value, **Then** it equals initial value minus accumulated depreciation ($500K remaining).
3. **Given** a county's total constant capital, **When** I decompose into fixed and circulating portions, **Then** the decomposition uses industry-level BEA Fixed Asset ratios.
4. **Given** an economy-level depreciation fund state, **When** replacement expenditure significantly exceeds annual depreciation flow (ratio > 1.5), **Then** the system identifies an "INVESTMENT_BOOM" replacement cycle position.
5. **Given** an economy-level depreciation fund state, **When** replacement expenditure falls well below annual depreciation flow (ratio < 0.7), **Then** the system identifies "DISINVESTMENT."

______________________________________________________________________

### User Story 4 - Reproduction Schema Balance Conditions (Priority: P2)

As a simulation designer, I want the system to check whether inter-departmental exchange satisfies simple and extended reproduction conditions so that I can detect disproportionality crises, because Departments I, II, and III must exchange at specific ratios for the economy to reproduce itself.

**Why this priority**: The reproduction schema connects the existing Department structure (from Feature 011) to Volume II's circulation analysis. It reveals whether the economy can sustain itself or is heading toward structural crisis due to sectoral imbalance.

**Independent Test**: Can be fully tested by providing Department I and II output values, computing the simple reproduction condition I(v+s) = IIc, and verifying the gap and interpretation are correct.

**Acceptance Scenarios**:

1. **Given** Department I with v=30, s=20 and Department II with c=50, **When** I check simple reproduction, **Then** the condition is met (I(v+s) = 50 = IIc = 50, gap = 0).
2. **Given** Department I with v=30, s=30 and Department II with c=40, **When** I check simple reproduction, **Then** the condition fails with gap = +20, interpreted as "OVERPRODUCTION_DEPT_I."
3. **Given** Departments I, II, and III with their c, v, s values, **When** I check extended reproduction with Department III, **Then** the system reports whether total labor power demand (sum of all v) exceeds Department III's reproduction capacity (III's c+v+s).
4. **Given** a reproduction analysis showing a negative reproduction gap (demand > capacity), **When** I check sustainability, **Then** the system flags this as unsustainable, revealing exploitation of reproductive labor.

______________________________________________________________________

### User Story 5 - Inventory Tracking and Realization Crisis Detection (Priority: P3)

As a simulation designer, I want the system to track inventory levels (raw materials, work-in-progress, finished goods) and detect when rising finished goods inventory signals a realization crisis, because production does not guarantee sale and the gap between value produced and value realized is a distinct crisis mechanism.

**Why this priority**: Realization crisis (C' -> M' fails) is the most directly observable Volume II crisis tendency. It complements the existing TRPF-based crisis mechanics (Feature 018) with a demand-side crisis mechanism.

**Independent Test**: Can be fully tested by providing a sequence of inventory states with rising finished goods and flat/falling production, and verifying the system correctly identifies a realization crisis.

**Acceptance Scenarios**:

1. **Given** a county with finished goods inventory covering 30 days of sales, **When** I check inventory status, **Then** the diagnosis is "NORMAL."
2. **Given** a county with finished goods inventory covering 75 days of sales, **When** I check inventory status, **Then** the diagnosis is "OVERPRODUCTION."
3. **Given** a county with raw materials covering only 3 days of production, **When** I check inventory status, **Then** the diagnosis is "SUPPLY_CRISIS."
4. **Given** a time series where finished goods inventory is rising while production output is flat or falling, **When** I check for realization crisis, **Then** the system returns true.
5. **Given** commodity value produced of $100M and commodity value realized of $72M, **When** I compute realization metrics, **Then** the realization rate is 72% and severity is "RECESSION."

______________________________________________________________________

### User Story 6 - Circulation Costs Classification (Priority: P3)

As a simulation designer, I want labor and costs classified as productive (value-creating) or unproductive (pure circulation) so that the system distinguishes between labor that adds value (production workers, transport workers) and labor that merely facilitates exchange (salespeople, accountants, advertisers), because this distinction is essential for accurate surplus value accounting.

**Why this priority**: Circulation costs are a drain on surplus value that must be accounted for. As economies financialize and tertiarize, the share of unproductive labor grows, which affects the rate of profit calculation. This classification extends the existing labor analysis with a Volume II lens.

**Independent Test**: Can be fully tested by providing circulation cost breakdowns and verifying the total pure circulation cost and circulation burden ratio are computed correctly.

**Acceptance Scenarios**:

1. **Given** circulation costs (sales labor $10M, accounting $5M, marketing $3M, facilities $2M, advertising $4M, transaction costs $1M), **When** I compute total pure circulation costs, **Then** the result is $25M.
2. **Given** total pure circulation costs of $25M and total revenue of $250M, **When** I compute the circulation burden, **Then** the result is 10%.
3. **Given** a transport worker, **When** I classify their labor, **Then** it is classified as productive (transportation adds use-value by changing location).
4. **Given** an advertising creative, **When** I classify their labor, **Then** it is classified as unproductive (creates no use-value, facilitates exchange only).

______________________________________________________________________

### User Story 7 - Integrated Circulation Crisis Detection (Priority: P3)

As a simulation designer, I want the system to detect multiple Volume II crisis types (realization, disproportionality, turnover disruption) in an integrated assessment so that the crisis detection system captures demand-side and circulatory failures alongside the existing supply-side TRPF mechanism.

**Why this priority**: Volume II crisis tendencies are distinct from TRPF. A system can have a stable profit rate but still enter crisis because commodities cannot be sold (realization), departments are out of balance (disproportionality), or working capital is insufficient to continue the circuit (turnover disruption). This completes the crisis detection picture.

**Independent Test**: Can be fully tested by providing circuit state, turnover profile, inventory state, and reproduction conditions, and verifying the integrated crisis assessment correctly identifies which crisis types are active.

**Acceptance Scenarios**:

1. **Given** commodity overhang > 30% and normal liquidity, **When** I run crisis detection, **Then** a realization crisis is flagged.
2. **Given** liquidity ratio < 10% and circulation time exceeding production time, **When** I run crisis detection, **Then** a turnover disruption crisis is flagged.
3. **Given** reproduction conditions where effective demand is inadequate and labor supply is short, **When** I run crisis detection, **Then** reproduction crisis is flagged with vulnerabilities ["REALIZATION_CRISIS", "LABOR_SHORTAGE"].
4. **Given** all conditions normal, **When** I run crisis detection, **Then** no crisis is flagged.

______________________________________________________________________

### Edge Cases

- What happens when total capital is zero? (Division by zero in liquidity_ratio and commodity_overhang must return 0.0)
- What happens when turnover time is zero? (Turnovers-per-year must handle division by zero gracefully, returning 0.0)
- What happens when a county has no industry-level turnover data? (System should use reasonable defaults or NoDataSentinel pattern)
- How does the system handle a county transitioning from one dominant industry to another mid-simulation? (Turnover profile should update based on current industry mix)
- What happens when all capital is stuck in one form (100% commodity, 0% money, 0% productive)? (This is a valid crisis state — total liquidity crisis — and should be detectable)
- What happens when Department III (reproductive labor) has zero output? (Reproduction gap should equal total v, signaling complete failure of labor power reproduction)
- What happens when depreciation fund accumulates beyond replacement cost? (Fund adequacy > 1.0 is valid — represents latent money capital available for credit/investment)

## Requirements *(mandatory)*

### Functional Requirements

**Circuit State & Form Transitions**

- **FR-001**: System MUST represent capital in three forms: Money (M), Productive (P), and Commodity (C), with the sum of all three equaling total capital for any entity at any tick.
- **FR-002**: System MUST track capital form transitions through the circuit M -> C -> P -> C' -> M' as a state machine, with transition timing governed by the entity's turnover profile.
- **FR-003**: System MUST compute liquidity ratio (money_capital / total_capital) and commodity overhang (commodity_capital / total_capital) as diagnostic indicators, returning 0.0 when total capital is zero.

**Turnover Time & Annual Surplus**

- **FR-004**: System MUST decompose turnover time into production time (working period + non-working production time) and circulation time (purchase time + sale time).
- **FR-005**: System MUST compute turnovers per year as 365 / turnover_time, returning 0.0 when turnover time is zero.
- **FR-006**: System MUST compute annual rate of surplus value as (s/v per cycle) x (turnovers per year), correctly amplifying exploitation rate by turnover speed.
- **FR-007**: System MUST support industry-level turnover profiles derived from federal data sources (Census inventory-to-sales ratios, BEA fixed asset depreciation schedules).

**Fixed vs Circulating Capital**

- **FR-008**: System MUST decompose constant capital (c) into fixed capital (machinery, buildings — value transferred gradually via depreciation) and circulating capital (raw materials, fuel — value transferred completely each production cycle).
- **FR-009**: System MUST compute straight-line annual depreciation for fixed capital items as initial_value / service_life_years.
- **FR-010**: System MUST track depreciation fund state: accumulated depreciation, annual depreciation flow, and replacement expenditure, enabling replacement cycle position classification (INVESTMENT_BOOM, EXPANSION, MAINTENANCE, DISINVESTMENT).
- **FR-011**: System MUST model moral depreciation (obsolescence) as the ratio of economic remaining life to physical remaining life, capturing the effect of technological change on fixed capital values.

**Reproduction Schemata**

- **FR-012**: System MUST check simple reproduction conditions: I(v + s) = IIc, reporting the gap and direction of imbalance (overproduction Dept I vs underproduction Dept I).
- **FR-013**: System MUST check extended reproduction conditions accounting for Department III (reproductive labor), comparing total labor power demand (sum of all departments' v) against Department III's reproduction capacity (III's c + v + s).
- **FR-014**: System MUST compute disproportionality metrics: actual Department I share vs required share, imbalance magnitude, and direction (overproduction of means of production vs overproduction of consumption goods).

**Inventory & Realization**

- **FR-015**: System MUST track inventory state: raw materials, work-in-progress, and finished goods, with diagnostic thresholds (finished goods > 60 days = OVERPRODUCTION, raw materials < 7 days = SUPPLY_CRISIS).
- **FR-016**: System MUST compute realization metrics: realization gap (produced - realized), realization rate (realized / produced), and crisis severity classification (NORMAL > 95%, MILD_SLOWDOWN > 85%, RECESSION > 70%, CRISIS <= 70%).
- **FR-017**: System MUST detect realization crisis from time series: rising finished goods inventory combined with flat or falling production output.

**Circulation Costs**

- **FR-018**: System MUST classify labor as productive (value-creating: production, transportation) or unproductive (pure circulation: sales, accounting, marketing, advertising, security).
- **FR-019**: System MUST compute total pure circulation costs and circulation burden (pure circulation costs / total revenue).
- **FR-020**: System MUST model transportation as productive labor that adds value (c + v + s) to commodity value, with transport value ratio as fraction of final commodity value.

**Crisis Integration**

- **FR-021**: System MUST provide an integrated circulation crisis assessment that detects realization crisis, turnover disruption, and reproduction failure independently, reporting which vulnerabilities are active.
- **FR-022**: Circulation crisis detection MUST complement (not replace) the existing TRPF-based crisis mechanics from Feature 018, providing demand-side and circulatory crisis signals alongside supply-side profit rate decline.

### Key Entities

- **CircuitState**: The distribution of an entity's capital across Money, Productive, and Commodity forms at a given tick, including fixed/circulating breakdown of productive capital.
- **TurnoverProfile**: Temporal characteristics of capital circulation for an entity/industry: working period, non-working production time, purchase time, sale time, and derived metrics (turnovers per year, production ratio).
- **FixedCapitalItem**: A durable means of production with initial value, service life, current age, and computed depreciation/remaining value.
- **DepreciationFundState**: Economy-level tracking of gross fixed capital stock, accumulated depreciation, annual depreciation flow, replacement expenditure, and replacement cycle position.
- **InventoryState**: Stock of commodities in three stages (raw materials, work-in-progress, finished goods) with diagnostic days-of-coverage metrics.
- **ReproductionBalance**: Result of checking simple reproduction conditions (I(v+s) = IIc), including gap magnitude and direction interpretation.
- **ReproductionAnalysis**: Result of extended reproduction check including Department III, with labor power demand, reproduction capacity, gap, and sustainability flag.
- **RealizationCrisis**: Metrics for the gap between value produced and value realized, with realization rate and severity classification.
- **DisproportionalityCrisis**: Department-level output imbalance metrics with required vs actual proportions and imbalance direction.
- **CirculationCrisisAssessment**: Integrated assessment combining realization crisis, turnover disruption, and reproduction failure flags with active vulnerability list.
- **PureCirculationCosts**: Breakdown of unproductive circulation costs (sales, accounting, marketing, facilities, advertising, transaction costs) with total and burden ratio.
- **TransportationValue**: Value added by transportation (c + v + s of transport), with origin value, destination value, and transport value ratio.
- **MoralDepreciation**: Obsolescence tracking for fixed capital items, comparing physical remaining life to economic remaining life.

## Assumptions

- **Tick-to-day mapping**: Each simulation tick is 1 week (existing codebase convention: WEEKS_PER_YEAR = 52). The annual economics pipeline fires once every 52 ticks. Turnover profiles express durations in days; turnovers-per-year is computed as 365 / turnover_time_days. Circuit phase transitions are simulated as sub-steps within the annual pipeline call.
- **Industry-level turnover**: Turnover profiles are defined at the industry (NAICS) level, not per-entity. A county's effective turnover profile is a weighted average of its industry mix.
- **Straight-line depreciation**: Fixed capital uses straight-line depreciation as the default method, consistent with Marx's treatment. More complex depreciation schedules (declining balance, etc.) are out of scope.
- **Department structure**: Uses the existing four-department structure from Feature 011 (I, IIa, IIb, III). Department IIa and IIb are treated as a single Department II for reproduction schema checks.
- **Federal data availability**: Turnover profiles will initially use BEA Fixed Asset Tables and Census inventory-to-sales ratios. Where data is unavailable for specific industries, the system uses NoDataSentinel and falls back to reasonable defaults.
- **Complementary crisis detection**: Volume II crisis detection extends (does not replace) existing Feature 018 crisis mechanics. Both systems run independently and their signals are available to downstream consumers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 22 functional requirements have corresponding passing tests (unit + integration) covering both normal and edge cases.
- **SC-002**: Annual surplus value computation correctly amplifies per-cycle surplus by turnover speed — verified against Marx's own numerical examples (e.g., s/v=100%, 6 turnovers/year = 600% annual rate).
- **SC-003**: Simple reproduction condition check correctly identifies balanced and imbalanced department configurations, validated against at least 5 distinct test scenarios.
- **SC-004**: Realization crisis detection correctly identifies rising inventory + falling production patterns from synthetic time series data.
- **SC-005**: Circuit state form transitions preserve total capital invariant (M + P + C = constant, modulo surplus value creation during production phase).
- **SC-006**: Depreciation fund tracking correctly classifies replacement cycle positions, validated against BEA Fixed Asset data patterns.
- **SC-007**: Integrated crisis assessment correctly detects all three crisis types (realization, turnover, reproduction) independently and in combination.
- **SC-008**: All new models are frozen Pydantic BaseModel instances following project conventions (ConfigDict(frozen=True), constrained types).
- **SC-009**: All new formulas pass doctest examples and are registered in the formula registry where applicable.
- **SC-010**: Feature integrates with existing TickDynamicsSystem via the GraphProtocol, writing circulation state to territory nodes alongside existing tick_* attributes.
