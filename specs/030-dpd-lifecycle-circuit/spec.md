# Feature Specification: D-P-D' Lifecycle Circuit

**Feature Branch**: `030-dpd-lifecycle-circuit`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "The D-P-D' Circuit: Lifecycle Reproduction of Labor-Power — modeling intergenerational class reproduction through Dependent, Productive, Dependent' phases with ideology transmission, legitimation bargain, inheritance mechanics, and eugenics contradiction"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Population Cohort Tracking by Lifecycle Phase (Priority: P1)

A simulation operator runs the engine and observes that each county's population is distributed across three lifecycle phases: D (pre-productive dependents: children, adolescents), P (productive workers selling labor-power), and D' (post-productive dependents: elderly, disabled, retired). Each simulation tick, population transitions occur between phases at rates derived from Census ACS data. The dependency ratio ((D + D') / P) is computed per county and directly modifies the subsistence burden on P-phase workers.

**Why this priority**: Without population distribution by lifecycle phase, no other D-P-D' mechanic can function. This is the foundational data model that all other user stories depend on.

**Independent Test**: Can be fully tested by creating a county with known D/P/D' populations, advancing one tick, and verifying that transition rates produce correct population shifts and dependency ratio.

**Acceptance Scenarios**:

1. **Given** a county with pop_D=1000, pop_P=3000, pop_D_prime=500, **When** a simulation tick runs with rate_D_to_P=0.056 (1/18 years), rate_P_to_D_prime=0.021 (1/47 years), rate_D_prime_to_death=0.067 (1/15 years), **Then** population transitions are applied correctly and dependency_ratio updates to reflect the new distribution.
2. **Given** a county where D-phase population drops to zero (no children), **When** the simulation advances, **Then** the P-phase population begins declining in subsequent ticks as no new workers enter the productive phase, and the system signals a demographic crisis.
3. **Given** a county with an aging population (large D', small D), **When** dependency_ratio exceeds a critical threshold, **Then** the subsistence burden on P-phase workers increases proportionally, affecting their wealth accumulation and P(S|A).

______________________________________________________________________

### User Story 2 - Legitimation Bargain and Crisis Detection (Priority: P2)

A simulation operator observes that worker acquiescence is partially sustained by the "D' promise" — the expectation that P-phase exploitation will be rewarded with security in the D' phase. The legitimation index is a composite measure of pension coverage, social security replacement rate, healthcare security, home ownership rate, and retirement confidence. When the legitimation index drops below critical thresholds, workers become more agitated, feeding into the George Jackson bifurcation pathway.

**Why this priority**: The legitimation bargain is the primary mechanism through which D-P-D' connects to the existing consciousness and bifurcation systems. Without it, lifecycle phases are inert demographic data with no simulation consequence.

**Independent Test**: Can be tested by constructing a LegitimationState with known indicator values, computing the legitimation index, and verifying it correctly modifies the existing BifurcationRiskMetric.legitimation field.

**Acceptance Scenarios**:

1. **Given** a county with pension_coverage=0.6, ss_replacement=0.4, healthcare_security=0.7, home_ownership=0.65, retirement_confidence=0.5, **When** legitimation index is computed, **Then** the index equals the weighted sum (0.25*0.6 + 0.25*0.4 + 0.25*0.7 + 0.15*0.65 + 0.10*0.5 = 0.5725) and crisis risk is assessed as "STABLE".
2. **Given** a county where pension coverage collapses from 0.6 to 0.1 over multiple ticks (e.g., employer defaults), **When** the legitimation index crosses below 0.3, **Then** the system flags "CRISIS" status and the BifurcationRiskMetric receives the reduced legitimation value, amplifying bifurcation risk.
3. **Given** a DispossessionType.PENSION_DEFAULT event fires, **When** the legitimation system processes it, **Then** pension_coverage_rate and retirement_confidence are degraded proportionally, reflecting the broken D' promise.

______________________________________________________________________

### User Story 3 - Intergenerational Inheritance Flow (Priority: P3)

A simulation operator observes that when agents in D' phase exit the simulation (death), accumulated wealth transfers to D-phase dependents in the same county. The inheritance amount varies dramatically by class: bourgeoisie pass substantial capital, labor aristocracy pass moderate home equity and savings, proletariat pass minimal amounts (often consumed by D'-phase care costs), and lumpenproletariat may pass negative inheritance (debt). This inheritance mechanism reproduces class position across generations.

**Why this priority**: Inheritance is how class position becomes sticky across generations. Without it, the simulation treats each generation as independent, missing the core insight that capitalism reproduces itself through intergenerational wealth transfer.

**Independent Test**: Can be tested by placing agents of different classes in D' phase, triggering death transitions, and verifying that wealth transfers to D-phase agents follow class-differentiated patterns, with the correct Gini coefficient for inheritance inequality.

**Acceptance Scenarios**:

1. **Given** a bourgeois household with wealth=500,000 entering D' terminus, **When** the death transition fires, **Then** a large fraction of accumulated wealth transfers to the next-generation D-phase dependents, reproducing bourgeois class position.
2. **Given** a proletarian household with wealth=5,000 entering D' terminus where D'-phase care costs are 4,500, **When** the death transition fires, **Then** only 500 (or less) transfers as inheritance, reproducing proletarian class position.
3. **Given** a county where dispossession events (foreclosure) have stripped home equity from labor aristocracy households, **When** D' terminus occurs, **Then** inheritance is dramatically reduced compared to non-dispossessed households, and the next generation's D-phase starts at a lower wealth baseline.

______________________________________________________________________

### User Story 4 - Ideological Socialization in D Phase (Priority: P4)

A simulation operator observes that children in the D phase absorb the ideological orientation of their P-phase caregivers. A child raised by labor aristocrats with high acquiescence enters the P phase with a consciousness baseline tilted toward acquiescence. A child raised by radicalized proletarians enters P phase with elevated class consciousness. This "stickiness" of ideology across generations explains why consciousness change is slow even when material conditions shift rapidly.

**Why this priority**: Ideology transmission through the D phase is what makes consciousness "sticky" across generations — a core theoretical insight. However, it depends on the population tracking (US1) and consciousness model (Feature 029) being in place first.

**Independent Test**: Can be tested by creating D-phase agents with P-phase caregivers of known ideology, advancing through the D-to-P transition, and verifying that the new P-phase agent's consciousness baseline reflects the caregiver's ideological influence.

**Acceptance Scenarios**:

1. **Given** a D-phase cohort whose P-phase caregivers have mean class_consciousness=0.8 and national_identity=0.2, **When** the D-to-P transition occurs, **Then** the new P-phase agents enter with a consciousness baseline weighted toward their caregivers' values (e.g., class_consciousness=0.6, national_identity=0.3, reflecting partial inheritance with regression toward population mean).
2. **Given** a D-phase cohort in a community with ConsciousnessTendency.REVOLUTIONARY, **When** the D-to-P transition occurs, **Then** the ideology transmission is amplified by the community's consciousness tendency, producing higher revolutionary consciousness than individual caregiver influence alone would predict.
3. **Given** a D-phase cohort subject to strong hegemonic schooling (high state institutional presence), **When** the D-to-P transition occurs, **Then** the ideology baseline is pulled toward the dominant ideology regardless of caregiver influence, reflecting the pre-subsumption function of public schooling.

______________________________________________________________________

### User Story 5 - Eugenics Contradiction and Differential P-Phase Duration (Priority: P5)

A simulation operator observes that different populations experience systematically different durations in each lifecycle phase. Black men have shorter average P phases (earlier transition to D' or death) due to environmental racism, carceral geography, and differential healthcare access. Incarcerated populations experience premature P-to-D' transitions (removed from productive labor). These differential durations are not random but are structural features of racial capitalism that the simulation must encode.

**Why this priority**: The eugenics contradiction is the most theoretically advanced aspect of D-P-D', connecting lifecycle dynamics to racial oppression and carceral geography. It depends on all prior user stories being functional.

**Independent Test**: Can be tested by creating two population cohorts with identical starting conditions but different transition rates (reflecting structural racism), running the simulation for multiple generations, and verifying that the affected population shows shorter P phases, less accumulation, and weaker inheritance — reproducing racial wealth gaps.

**Acceptance Scenarios**:

1. **Given** two county populations with identical starting wealth but different P-to-D' transition rates (0.021 for white workers, 0.028 for Black workers), **When** the simulation runs for 5 generational cycles, **Then** the population with faster P-to-D' transition accumulates less wealth per generation, and the wealth gap compounds intergenerationally.
2. **Given** a county with high incarceration rates, **When** the simulation processes incarceration events, **Then** affected P-phase individuals are removed from productive labor (premature P-to-D' transition) and their potential inheritance is eliminated, contributing to the "stagnant reserve army."
3. **Given** a county with environmental racism (higher pollution, fewer healthcare facilities), **When** transition rates are computed, **Then** the rate_P_to_D_prime for affected racial groups is elevated relative to the county average, reflecting differential health outcomes.

______________________________________________________________________

### Edge Cases

- What happens when pop_P reaches zero (no productive workers)? The system must handle division by zero in dependency_ratio and signal economic collapse.
- How does the system handle negative inheritance (debt transfer)? Lumpenproletariat D' terminus may transfer debt rather than wealth.
- What happens when legitimation_index is exactly at a threshold boundary (0.3 or 0.5)? The categorization uses consistent boundary rules: CRISIS if index < 0.3, UNSTABLE if 0.3 <= index < 0.5, STABLE if index >= 0.5.
- How does mass mortality (pandemic, war) affect phase transitions? A sudden spike in P-to-death or D'-to-death rates must be processable without numerical instability.
- What happens when dispossession severs the inheritance mechanism mid-simulation? The system must handle the case where accumulated wealth is forcibly transferred to capital rather than heirs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track population distribution across three lifecycle phases (D, P, D') per county per simulation tick.
- **FR-002**: System MUST compute transition rates (D-to-P, P-to-D', D'-to-death) from demographic data sources and apply them each tick to update phase populations.
- **FR-003**: System MUST compute dependency_ratio as (pop_D + pop_D_prime) / pop_P per county, handling the zero-population edge case gracefully.
- **FR-004**: System MUST compute a legitimation index as a weighted composite of pension coverage, social security replacement rate, healthcare security, home ownership rate, and retirement confidence.
- **FR-005**: System MUST classify legitimation crisis risk as CRISIS (index < 0.3), UNSTABLE (0.3 <= index < 0.5), or STABLE (index >= 0.5).
- **FR-006**: System MUST feed the legitimation index into the existing BifurcationRiskMetric.legitimation field, replacing or augmenting the current agitation-inverse computation.
- **FR-007**: System MUST model intergenerational wealth transfer at D' terminus, with transfer amounts differentiated by class position (bourgeoisie, labor aristocracy, proletariat, lumpenproletariat).
- **FR-008**: System MUST reduce inheritance when dispossession events (foreclosure, pension default) have consumed accumulated wealth.
- **FR-009**: System MUST transmit ideological orientation from P-phase caregivers to D-phase dependents during the D-to-P transition, with regression toward the population mean.
- **FR-010**: System MUST support differential transition rates by demographic group (race, incarceration status, community type) to encode structural inequality in lifecycle duration.
- **FR-011**: System MUST integrate D-phase dependency costs into the existing subsistence calculation, increasing the effective subsistence threshold for P-phase workers who support dependents.
- **FR-012**: System MUST respond to DispossessionType.PENSION_DEFAULT events by degrading legitimation indicators.
- **FR-013**: System MUST compute inheritance_gini as a measure of intergenerational transfer inequality per county.

### Key Entities

- **DPDState**: Per-county, per-tick snapshot of population distribution across D/P/D' phases, with transition rates and computed dependency ratio. Connects to existing SocialClass.population for demographic accounting.
- **LegitimationState**: Per-county measure of D' promise credibility, composed of objective indicators (pension, SS, healthcare, homeownership) and subjective confidence. Feeds into BifurcationRiskMetric.
- **InheritanceFlow**: Per-county, per-tick record of intergenerational wealth transfer, differentiated by class origin. Tracks total inheritance and inheritance Gini coefficient.
- **LifecyclePhase**: Enum representing D, P, D' phases. Maps to existing CommunityType values (YOUTH, ADULT, ELDER) already defined in Feature 029.
- **LifecycleTransitionEvent**: Event emitted when population cohorts transition between phases (D-to-P, P-to-D', D'-to-death), carrying demographic and wealth-transfer data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each county's population sums (pop_D + pop_P + pop_D_prime) are conserved across ticks (accounting for births and deaths), with no unexplained population gain or loss exceeding 0.1%.
- **SC-002**: The legitimation index correctly predicts crisis classification for all documented test scenarios, with the composite weighted formula producing values within [0.0, 1.0].
- **SC-003**: Inheritance Gini coefficient for a simulation with standard class distribution exceeds income Gini (Gini(inheritance) > Gini(income)), consistent with empirical data showing inheritance is more unequal than income.
- **SC-004**: After 5 simulated generational cycles, populations with structurally shorter P phases (higher P-to-D' transition rates) accumulate measurably less intergenerational wealth than populations with standard P phases.
- **SC-005**: Ideology transmission during D-to-P transition produces measurable correlation between caregiver consciousness and new-worker consciousness (r > 0.3), while still allowing divergence from parental ideology.
- **SC-006**: A DispossessionType.PENSION_DEFAULT event produces a measurable decrease in legitimation index within the same tick, and the BifurcationRiskMetric reflects the change.
- **SC-007**: The dependency ratio correctly increases subsistence burden on P-phase workers, and counties with higher dependency ratios show lower per-capita wealth accumulation over time.
- **SC-008**: All D-P-D' models validate against existing constrained types (Probability, Currency, Gini, Coefficient) with no type violations at runtime.

## Assumptions

- **A-001**: D-P-D' is modeled as population cohort dynamics (aggregate per-county), not individual agent lifecycles. This is a deliberate simplification for computational tractability at the county level.
- **A-002**: Transition rates (D-to-P, P-to-D', D'-to-death) are derived from Census ACS age-cohort data and CDC mortality data, initialized at simulation start and modified by simulation events (dispossession, crisis, etc.).
- **A-003**: The existing CommunityType values YOUTH/ADULT/ELDER (Feature 029) serve as the hyperedge representation of lifecycle phases, while the new DPDState model tracks the quantitative population dynamics.
- **A-004**: Legitimation indicators (pension coverage, SS replacement rate, etc.) are initialized from BLS/ACS data at simulation start and evolve based on simulation events, not re-queried from external data each tick.
- **A-005**: Inheritance transfer is modeled as an aggregate county-level flow differentiated by class, not as individual household-to-household transfers.
- **A-006**: Ideology transmission uses a weighted blend of caregiver ideology and community ideology with regression toward mean, not a direct copy of parental values.
- **A-007**: The generational timescale (~80 years) is compressed into the simulation's annual tick structure via transition rates, so a single tick represents one year of demographic change, not one full lifecycle.

## Dependencies

- **Feature 029** (Community Hyperedge Upgrade): Provides CommunityType.YOUTH/ADULT/ELDER, HyperedgeCategory.LIFECYCLE_PHASE, and ConsciousnessTendency framework that D-P-D' builds upon.
- **Feature 018** (Crisis Devaluation): Provides BifurcationRiskMetric.legitimation field and the bifurcation crisis detection system that D-P-D' legitimation feeds into.
- **Feature 021** (Capital Volume I): Provides the surplus extraction framework that D-P-D' inheritance quantifies across generations.
- **Existing Systems**: SurvivalSystem (P(S|A) calculation), ConsciousnessSystem (ideology drift), DispossessionType.PENSION_DEFAULT (event type already defined).

## Out of Scope

- Individual agent-level lifecycle tracking (this feature uses cohort aggregates).
- Real-time demographic data ingestion during simulation (data is initialized at start).
- Modeling of specific policy interventions (Social Security reform, Medicare expansion) — the feature provides the framework; policy scenarios are future work.
- Immigration and emigration effects on D/P/D' population (designated as Phase 2 extension, per the reproduction.py TODO).
- Eugenics as explicit policy mechanics — the feature encodes differential outcomes via transition rates, not policy decision trees.
