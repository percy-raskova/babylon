# Feature Specification: D-P-D' Lifecycle Circuit

**Feature Branch**: `030-dpd-lifecycle-circuit`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "The D-P-D' Circuit: Lifecycle Reproduction of Labor-Power — modeling intergenerational class reproduction through Dependent, Productive, Dependent' phases with ideology transmission, legitimation bargain, inheritance mechanics, and eugenics contradiction"

## Clarifications

### Session 2026-02-27

- Q: How does new D-phase population enter the system (births)? → A: Endogenous — births = f(pop_P), a fertility rate applied to P-phase population each tick. Fertility rate parameters require empirical research from Census/CDC crude birth rate data.
- Q: Should the new structural legitimation index replace or augment the existing agitation-inverse computation? → A: Weighted blend — legitimation = w * structural_index + (1-w) * agitation_inverse, where w is a tunable coefficient. Structural index captures long-term institutional D' promise; agitation-inverse captures short-term worker mood.
- Q: What determines how much wealth transfers as inheritance vs consumed by D'-phase care? → A: Pareto wealth spread at the familial unit level (not individual). Top 1% of families owns 1/3 of wealth, next 9% owns 1/3, next 40% owns 1/3, bottom 50% owns net zero. Inheritance is emergent from the wealth distribution — families inherit whatever wealth the D' decedent family unit accumulated. No per-class transfer fractions needed.
- Q: Does Feature 030 implement data ingestion or assume pre-existing data? → A: Feature 030 ingests Census ACS (age cohorts, home ownership) and Chetty Opportunity Atlas mobility data (pre-collected CSVs). Population dynamics parameters (fertility, mortality, transition rates) use scientifically-based tunable defaults rather than CDC WONDER ingestion — explicitly declared as approximations, not empirical ingest. CDC ingestion was deemed too complex relative to simulation fidelity needs.
- Q: What empirical data source grounds intergenerational class mobility? → A: Chetty Opportunity Atlas (Mobility Atlas) CSV files at /media/user/data/babylon-data/mobility-atlas/. 9 CSV files covering 3,191 counties, 740 CZs, 15 birth cohorts (1978-1992). Used as a **calibration source** to derive tunable parameters (not runtime ingest). Key metrics: KFR, EMP, mortality, education, poverty — broken down by race and parental income percentile. Parameters derived from this data are documented with provenance and exposed as tunable GameDefines coefficients so they can shift in-game (e.g., racial discrimination events widen the racial mobility gap).

## Dual Circuit Ontology

The D-P-D' circuit has a complementary circuit that extends Marx's circuit algebra to intergenerational reproduction:

| Circuit | Formula | What It Traces | Analogous To |
|---------|---------|----------------|--------------|
| **D-P-D'** | Dependent → Productive → Dependent' | Individual lifecycle (one cohort traverses phases) | **C-M-C** (worker's daily circuit) |
| **P-D-P'** | P_g1 → D_g2 → P_g2 | Class reproduction (one generation produces the next) | **M-C-M'** (capital's self-expansion) |

**P-D-P' spelled out**: This generation's productive workers (P_g1) give birth to and raise the next generation's dependents (D_g2), who in turn grow into that generation's productive workers (P_g2). The subscripts denote distinct generations — P' is not the same person returning to P, but the *next generation's* P.

**The parallel to Marx is exact**:
- M-C-M' and C-M-C are complementary views of the same exchange relation (capital's circuit vs worker's circuit)
- D-P-D' and P_g1-D_g2-P_g2 are complementary views of the same reproductive relation (individual lifecycle vs class reproduction)

D-P-D' is where the individual traverses phases. P-D-P' is where the **class reproduces itself** across generations. The individual circuit is finite (one lifetime); the class circuit is potentially infinite (spiral across generations). This duality means every simulation mechanic has two readings: what it does to individuals in a lifecycle phase, and what it does to class reproduction across generations.

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

1. **Given** a bourgeois household (top 1%) with accumulated wealth representing ~1/3 of county wealth entering D' terminus, **When** the death transition fires, **Then** that accumulated wealth transfers to the next-generation D-phase dependents, reproducing bourgeois class position through the Pareto distribution.
2. **Given** a bottom-50% proletarian household with net zero accumulated wealth entering D' terminus, **When** the death transition fires, **Then** zero (or negative) wealth transfers as inheritance, reproducing proletarian class position. The Pareto distribution ensures this outcome without imposed transfer fractions.
3. **Given** a county where dispossession events (foreclosure) have stripped home equity from labor aristocracy households (next-40% tier), **When** D' terminus occurs, **Then** their inheritance drops toward the bottom-50% pattern (net zero), and the next generation's D-phase starts at a lower wealth baseline — dispossession pushes families down the Pareto distribution.

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

### User Story 6 - Class Mobility Parameterization from Chetty Opportunity Atlas (Priority: P3)

A simulation operator observes that intergenerational class mobility in the simulation is calibrated against empirical data from the Chetty Opportunity Atlas. The simulation uses derived parameters: if a child is born to parents at income percentile P25, what income percentile will they reach as an adult? The default answer (~P45 pooled) is derived from Mobility Atlas KFR data, with racial modifiers (Black children ~3-7 percentiles below White at same parental class). These parameters are tunable — in-game events like increased racial discrimination widen the racial gap, while educational improvements narrow it. The Mobility Atlas is a calibration source, not a runtime data dependency.

**Why this priority**: The Mobility Atlas provides the empirical backbone for the entire D-P-D' circuit. Without it, class reproduction parameters are arbitrary; with it, defaults are falsifiable against measured outcomes. Elevated to P3 because the data is already collected in CSV files and directly calibrates US1 (population dynamics), US3 (inheritance), and US5 (eugenics contradiction). Parameterization (rather than ingestion) means these values are tunable in response to simulation dynamics.

**Independent Test**: Can be tested by verifying that default class mobility parameters match Mobility Atlas KFR values for a reference CZ, and that in-game events (e.g., increasing racial discrimination coefficient) correctly shift mobility outcomes in the expected direction.

**Acceptance Scenarios**:

1. **Given** default class mobility parameters derived from Mobility Atlas (pooled KFR_P25 ~0.45), **When** the simulation computes D-to-P class transition for a cohort at parental P25, **Then** the resulting income percentile is approximately P45, matching the empirical calibration.
2. **Given** default racial mobility gap parameters (Black KFR ~3.7 percentiles below White at P25), **When** the simulation computes D-to-P transition by race, **Then** the racial gap is preserved. **When** an in-game racial discrimination event fires, **Then** the gap widens by the event's magnitude, reflecting dynamic caste effects.
3. **Given** default premature mortality parameters derived from Mobility Atlas (0.4% death rate by age 32 for P25 cohorts), **When** the simulation processes P-phase premature exit, **Then** the rate matches the calibrated default and shifts in response to in-game events (e.g., healthcare access changes).
4. **Given** default material condition parameters derived from Mobility Atlas covariates (Gini, median income, poverty share), **When** the simulation initializes, **Then** each parameter has documented provenance (Mobility Atlas table, column, aggregation) and is modifiable via GameDefines.

______________________________________________________________________

### User Story 7 - Dual Circuit Interference (D-P-D' x P-D-P') (Priority: P2)

The D-P-D' individual lifecycle circuit and the P_g1-D_g2-P_g2 class reproduction circuit run simultaneously but can **desynchronize under stress**, producing emergent crisis dynamics that neither circuit shows alone. A simulation operator observes these interference patterns:

**The Resource Competition**: P-phase workers must simultaneously fund three demands from a single wage: (1) their own daily reproduction (C-M-C), (2) their future D' security (savings, pension contributions), and (3) the next generation's D phase (child-rearing, education, housing). When M-C-M' accelerates extraction (wage cuts, austerity, longer hours), P-phase resources shrink and workers face a zero-sum choice between self-preservation (D-P-D') and class reproduction (P-D-P'). This is the **intergenerational austerity trap**.

**The Shadow Subsidy Extraction**: Capital receives P_g2 workers without paying for D_g2 socialization — the entire cost of producing the next generation's labor-power falls on P_g1 families. The gap between what capital pays (wages for P_g1's labor) and what it receives (a fully-formed P_g2 worker) is the generational shadow subsidy. This is the lifecycle analog of Department III's daily shadow subsidy (gamma visibility), operating at generational timescale.

**The Dispossession Short-Circuit**: When dispossession events (foreclosure, pension default) extract accumulated wealth from P_g1 families, this wealth transfers to capital rather than flowing through the P-D-P' circuit to D_g2. Dispossession is the mechanism by which capital **short-circuits P-D-P' to feed M-C-M'** — it interrupts class reproduction to accelerate capital accumulation. The dual circuit view reveals that dispossession doesn't just harm individual families (D-P-D' reading) but **structurally breaks class reproduction for targeted lineages** (P-D-P' reading).

**The Legitimation-Fertility Nexus**: When the D' promise fails (legitimation crisis), P_g1 workers respond in two ways that the dual circuit reveals: (1) In D-P-D', they become agitated (George Jackson bifurcation). (2) In P-D-P', they **reduce investment in the class circuit** — birth rates fall because raising children for a system that won't care for you is irrational. Or, they radicalize their D_g2 children (ideology transmission shifts toward revolutionary consciousness). The legitimation crisis doesn't just destabilize the current generation — it alters the **quality and quantity** of the next generation.

**The Sandwich Squeeze**: When D'_g1 (this generation's elderly) and D_g2 (next generation's children) both depend on P_g1 simultaneously, the P-phase worker is squeezed between the two circuits. This "sandwich generation" effect compounds the resource competition: P_g1 must fund their parents' D' phase AND their children's D phase from a single P-phase income. High dependency ratios make this structurally inevitable.

**Why this priority**: Elevated to P2 because the dual circuit interference is the central theoretical contribution of this feature — it's what makes D-P-D' more than demographic bookkeeping. The interference patterns explain real-world phenomena (declining birth rates, sandwich generation, "OK Boomer" intergenerational conflict, student debt as D→P transition burden) as emergent properties of circuit desynchronization. Without modeling interference, the simulation has two independent circuits that don't interact; with it, the circuits produce the contradictions that drive historical dynamics.

**Independent Test**: Can be tested by creating a county where P-phase resources are progressively squeezed (wages decline, extraction increases), and observing: (a) the intergenerational austerity trap forces tradeoffs between D' funding and D_g2 funding, (b) dispossession events break the P-D-P' inheritance pathway, (c) legitimation collapse produces measurable fertility rate decline and/or ideology transmission shift.

**Acceptance Scenarios**:

1. **Given** a county where P-phase wages are cut by 20% (M-C-M' acceleration), **When** P-phase workers can no longer fully fund both D' savings and D_g2 child-rearing, **Then** the system models the tradeoff: either D' funding declines (legitimation weakens) or D_g2 investment declines (next generation's class mobility degrades), or both. The specific split depends on the legitimation index — workers with high D' confidence prioritize children; workers with low D' confidence prioritize self-preservation.
2. **Given** a county where dispossession events extract $X from P_g1 families, **When** the dual circuit processes this, **Then** $X is removed from the P-D-P' inheritance pathway (D_g2 receives less), AND the D-P-D' circuit registers the wealth loss (D' security weakened). The same event produces effects in both circuits simultaneously.
3. **Given** a county in legitimation crisis (index < 0.3), **When** the P-D-P' circuit processes the next generation, **Then** fertility rate declines (fewer D_g2 births) AND ideology transmission shifts (D_g2 cohorts receive higher class consciousness / lower acquiescence from their radicalized P_g1 caregivers). Both effects are measurable and directionally correct.
4. **Given** a county with high dependency ratio (many D' + many D relative to P), **When** the sandwich squeeze is computed, **Then** P-phase per-capita resources decline, D_g2 investment quality degrades, AND the class mobility function produces worse P_g2 outcomes — the sandwich effect propagates from the current generation's resource constraint to the next generation's class position.

______________________________________________________________________

### Edge Cases

- What happens when pop_P reaches zero (no productive workers)? The system must handle division by zero in dependency_ratio and signal economic collapse.
- How does the system handle negative inheritance (debt transfer)? Lumpenproletariat D' terminus may transfer debt rather than wealth.
- What happens when legitimation_index is exactly at a threshold boundary (0.3 or 0.5)? The categorization uses consistent boundary rules: CRISIS if index < 0.3, UNSTABLE if 0.3 <= index < 0.5, STABLE if index >= 0.5.
- How does mass mortality (pandemic, war) affect phase transitions? A sudden spike in P-to-death or D'-to-death rates must be processable without numerical instability.
- What happens when dispossession severs the inheritance mechanism mid-simulation? The system must handle the case where accumulated wealth is forcibly transferred to capital rather than heirs.
- What happens when both circuits collapse simultaneously (legitimation crisis AND demographic crisis)? The system must handle the compound case where P-phase workers cannot fund either D' or D_g2 — a total reproduction failure.
- How does the sandwich squeeze interact with dispossession? If a sandwiched P-phase worker is dispossessed, the cascading effect hits both D' dependents (immediate care crisis) and D_g2 children (inheritance pathway destroyed).
- What happens when fertility rate drops to zero due to legitimation collapse? The P-D-P' circuit halts entirely — no new D_g2 births. The system must signal a class reproduction extinction event while the D-P-D' circuit continues for existing cohorts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track population distribution across three lifecycle phases (D, P, D') per county per simulation tick.
- **FR-002**: System MUST compute transition rates (D-to-P, P-to-D', D'-to-death) and a fertility rate, applying them each tick to update phase populations. Births are endogenous: new D-phase population = fertility_rate * pop_P per tick. **Disclaimer**: Fertility, mortality, and transition rate parameters use scientifically-based tunable defaults (not ingested from CDC WONDER). Default values are derived from published demographic research and clearly documented as approximations. These parameters are exposed for tuning.
- **FR-003**: System MUST compute dependency_ratio as (pop_D + pop_D_prime) / pop_P per county, handling the zero-population edge case gracefully.
- **FR-004**: System MUST compute a legitimation index as a weighted composite of pension coverage, social security replacement rate, healthcare security, home ownership rate, and retirement confidence.
- **FR-005**: System MUST classify legitimation crisis risk as CRISIS (index < 0.3), UNSTABLE (0.3 <= index < 0.5), or STABLE (index >= 0.5).
- **FR-006**: System MUST compute effective legitimation as a weighted blend: legitimation = w * structural_index + (1-w) * agitation_inverse, where w is a tunable coefficient. The structural index captures long-term institutional D' promise credibility; the agitation-inverse captures short-term worker mood. The blended value feeds into the existing BifurcationRiskMetric.legitimation field.
- **FR-007**: System MUST model intergenerational wealth transfer at D' terminus at the familial unit level. Inheritance amounts are emergent from the Pareto wealth distribution (top 1% of families owns 1/3, next 9% owns 1/3, next 40% owns 1/3, bottom 50% owns net zero). Families inherit whatever wealth the D' decedent family unit accumulated — class differentiation arises from wealth inequality, not imposed transfer fractions.
- **FR-008**: System MUST reduce inheritance when dispossession events (foreclosure, pension default) have consumed accumulated wealth.
- **FR-009**: System MUST transmit ideological orientation from P-phase caregivers to D-phase dependents during the D-to-P transition, with regression toward the population mean.
- **FR-010**: System MUST support differential transition rates by demographic group (race, incarceration status, community type) to encode structural inequality in lifecycle duration.
- **FR-011**: System MUST integrate D-phase dependency costs into the existing subsistence calculation, increasing the effective subsistence threshold for P-phase workers who support dependents.
- **FR-012**: System MUST respond to DispossessionType.PENSION_DEFAULT events by degrading legitimation indicators.
- **FR-013**: System MUST compute inheritance_gini as a measure of intergenerational transfer inequality per county.
- **FR-014**: System MUST derive tunable class mobility parameters from Chetty Opportunity Atlas data (CSV files at /media/user/data/babylon-data/mobility-atlas/). Parameters include: baseline class mobility rate by parental income quintile, racial mobility gap coefficients (Black-White, Hispanic-White, etc.), employment probability by class origin, and premature mortality rate by class/race. Each derived parameter MUST document its provenance (source table, column, aggregation method) and be exposed as a tunable GameDefines coefficient.
- **FR-015**: System MUST derive D-phase context parameters from Mobility Atlas covariate tables (Table_8/Table_9): baseline Gini, poverty share, employment rate, single-parent fraction, and college rate. These set initial conditions per county/CZ and are tunable in-game.
- **FR-016**: System MUST model a class mobility function for the D-to-P transition: given a parent's income percentile and race, what income percentile does the child reach? Default parameters calibrated from Mobility Atlas KFR data (e.g., P25 parents → ~P45 child pooled; Black children ~3-7 percentiles below White at same parental class). These parameters shift in-game in response to events (e.g., increased racial discrimination widens the racial gap; improved education narrows it).
- **FR-017**: System MUST derive premature P-phase exit rate parameters from Mobility Atlas mortality data (fraction dead by age 32, by race and parental income). Default: ~0.4% for P25 pooled. Race-specific differentials are tunable coefficients that shift with simulation events (carceral expansion, healthcare access changes).
- **FR-018**: System MUST expose ALL population dynamics parameters (fertility rate, D-to-P rate, P-to-D' rate, D'-to-death rate, class mobility rates, racial gap coefficients, premature mortality rates) as tunable coefficients in GameDefines with scientifically-based defaults. Each parameter MUST include: (a) default value, (b) source citation (Mobility Atlas table/column or demographic research), (c) explicit disclaimer that values are parameterized approximations. Parameters are modifiable by in-game events to model dynamic shifts (e.g., austerity policies degrade mobility, racial justice movements narrow gaps).
- **FR-019**: System MUST model the resource competition between D-P-D' and P-D-P' circuits: when P-phase per-capita resources decline (wage cuts, extraction increases), the system computes a tradeoff between D' savings (individual lifecycle security) and D_g2 investment (next-generation child-rearing). The allocation split depends on the current legitimation index — high legitimation biases toward D_g2 investment; low legitimation biases toward D' self-preservation.
- **FR-020**: System MUST model the dispossession short-circuit: when dispossession events extract wealth from P_g1 families, the extracted amount is simultaneously removed from (a) the D-P-D' circuit (D' security weakened) and (b) the P-D-P' circuit (inheritance pathway reduced). A single dispossession event produces effects in both circuits.
- **FR-021**: System MUST model the legitimation-fertility nexus: when legitimation index drops below configurable thresholds, fertility rate declines (P-D-P' quantity effect) AND ideology transmission during D-to-P shifts toward higher class consciousness (P-D-P' quality effect). Both effects are proportional to the legitimation deficit.
- **FR-022**: System MUST compute the sandwich squeeze: when dependency ratio exceeds a configurable threshold, P-phase per-capita resources are reduced by the combined burden of D' care AND D_g2 investment, degrading both the current generation's D' security and the next generation's class mobility outcomes.
- **FR-023**: System MUST compute a generational shadow subsidy metric: the difference between the cost of producing a P_g2 worker (D_g2 socialization costs borne by P_g1 families) and the wage premium capital pays for that labor-power. This metric quantifies the unpaid intergenerational reproduction cost extracted by M-C-M'.

### Key Entities

- **DPDState**: Per-county, per-tick snapshot of population distribution across D/P/D' phases, with transition rates (including endogenous fertility rate applied to pop_P for births) and computed dependency ratio. Connects to existing SocialClass.population for demographic accounting.
- **LegitimationState**: Per-county measure of D' promise credibility, composed of objective indicators (pension, SS, healthcare, homeownership) and subjective confidence. Feeds into BifurcationRiskMetric.
- **InheritanceFlow**: Per-county, per-tick record of intergenerational wealth transfer, differentiated by class origin. Tracks total inheritance and inheritance Gini coefficient.
- **LifecyclePhase**: Enum representing D, P, D' phases. Maps to existing CommunityType values (YOUTH, ADULT, ELDER) already defined in Feature 029.
- **LifecycleTransitionEvent**: Event emitted when population cohorts transition between phases (D-to-P, P-to-D', D'-to-death), carrying demographic and wealth-transfer data.
- **ClassMobilityParams**: Tunable parameters for intergenerational class mobility, derived from Chetty Opportunity Atlas KFR data. Includes: baseline mobility rate by parental quintile, racial gap coefficients by demographic group, premature mortality rates by class/race, and D-phase context modifiers (Gini, poverty share, education rate). All parameters include provenance documentation and are exposed via GameDefines for in-game modification.

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
- **SC-009**: All tunable population dynamics and class mobility parameters have documented provenance (source, derivation method, default value) and respond correctly to in-game events that modify them (e.g., a racial discrimination event widens the racial mobility gap parameter).
- **SC-010**: Default class mobility parameters produce D-to-P transition outcomes consistent with Mobility Atlas empirical values (within 5% tolerance for pooled KFR at P25, P50, P75).
- **SC-011**: When P-phase wages are reduced by 20%, the dual circuit resource competition produces a measurable shift in the D' savings vs D_g2 investment allocation, and the direction of the shift correlates with the current legitimation index.
- **SC-012**: A single dispossession event produces measurable effects in both circuits simultaneously: reduced D' security (D-P-D' reading) AND reduced inheritance pathway (P-D-P' reading).
- **SC-013**: Counties in legitimation crisis (index < 0.3) show both lower fertility rates AND higher class consciousness in the D_g2 cohort compared to counties with stable legitimation (index >= 0.5).
- **SC-014**: The generational shadow subsidy metric is positive for all class configurations (capital always extracts more from P_g2 than it paid to produce them through P_g1 wages).

## Assumptions

- **A-001**: D-P-D' is modeled as population cohort dynamics (aggregate per-county), not individual agent lifecycles. This is a deliberate simplification for computational tractability at the county level.
- **A-002**: Transition rates (D-to-P, P-to-D', D'-to-death) and fertility rates use scientifically-based tunable defaults exposed via GameDefines, not ingested from CDC WONDER. Defaults are derived from published demographic research (e.g., US crude birth rate ~11/1000, life expectancy tables) and documented as approximations. Rates are initialized at simulation start and modified by simulation events (dispossession, crisis, etc.). Mobility Atlas mortality-by-32 data supplements these defaults for race-specific differential rates.
- **A-003**: The existing CommunityType values YOUTH/ADULT/ELDER (Feature 029) serve as the hyperedge representation of lifecycle phases, while the new DPDState model tracks the quantitative population dynamics.
- **A-004**: Legitimation indicators (pension coverage, SS replacement rate, etc.) use scientifically-based tunable defaults initialized at simulation start and evolve based on simulation events. Mobility Atlas covariates (median income, Gini, poverty share, employment rate) provide county-level economic context that informs initial legitimation conditions. Data is not re-queried from external APIs each tick.
- **A-005**: Inheritance transfer operates at the familial unit level (not individual), aggregated to county-level flows differentiated by class. The Pareto wealth distribution determines transfer amounts emergently.
- **A-006**: Ideology transmission uses a weighted blend of caregiver ideology and community ideology with regression toward mean, not a direct copy of parental values.
- **A-007**: The generational timescale (~80 years) is compressed into the simulation's annual tick structure via transition rates, so a single tick represents one year of demographic change, not one full lifecycle.
- **A-008**: Population dynamics parameters (fertility, mortality, transition rates) and class mobility parameters are derived from empirical sources (Mobility Atlas, published demographic research) but stored as tunable GameDefines coefficients, not runtime data ingestion. This is an explicit design choice: parameterization over ingestion enables in-game modification in response to events (e.g., austerity policies degrade mobility, racial discrimination widens gaps). The tradeoff is reduced geographic specificity in exchange for simulation responsiveness.
- **A-009**: The Mobility Atlas CSV files are a calibration artifact used during development to derive parameter defaults, not a runtime dependency. The simulation does not read these files at startup.

## Dependencies

- **Feature 029** (Community Hyperedge Upgrade): Provides CommunityType.YOUTH/ADULT/ELDER, HyperedgeCategory.LIFECYCLE_PHASE, and ConsciousnessTendency framework that D-P-D' builds upon.
- **Feature 018** (Crisis Devaluation): Provides BifurcationRiskMetric.legitimation field and the bifurcation crisis detection system that D-P-D' legitimation feeds into.
- **Feature 021** (Capital Volume I): Provides the surplus extraction framework that D-P-D' inheritance quantifies across generations.
- **Existing Systems**: SurvivalSystem (P(S|A) calculation), ConsciousnessSystem (ideology drift), DispossessionType.PENSION_DEFAULT (event type already defined).
- **Chetty Opportunity Atlas** (calibration source): Pre-collected CSV files at /media/user/data/babylon-data/mobility-atlas/. Used to derive tunable parameters, not as a runtime dependency. 9 CSV files, 3,191 counties, 740 CZs, 15 birth cohorts (1978-1992).

## Out of Scope

- Individual agent-level lifecycle tracking (this feature uses cohort aggregates).
- Real-time demographic data re-querying during simulation ticks (data is ingested once at initialization, not refreshed per tick).
- Modeling of specific policy interventions (Social Security reform, Medicare expansion) — the feature provides the framework; policy scenarios are future work.
- Immigration and emigration effects on D/P/D' population (designated as Phase 2 extension, per the reproduction.py TODO).
- Eugenics as explicit policy mechanics — the feature encodes differential outcomes via transition rates, not policy decision trees.
