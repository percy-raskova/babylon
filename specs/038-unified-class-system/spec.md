# Feature Specification: Unified Class System

**Spec ID**: `038-unified-class-system`
**Feature Branch**: `038-unified-class-system`
**Created**: 2026-03-01
**Status**: Draft
**Depends On**: `013-melt-basket-visibility`, `026-tri-county-economic-substrate`, `029-community-hyperedge-upgrade`, `030-dpd-lifecycle-circuit`, `031-organization-base-model`

---

## Theoretical Foundation

This spec reconciles two class determination frameworks developed across the Babylon project into a single canonical architecture and integrates them with the community hyperedge layer (029), lifecycle circuit (030), and organization model (031). The design doc's accounting + topological criteria define what class *is*. The TVT/MELT wealth percentile framework from Feature 013 operationalizes how to *measure* it with available data. They are the same claim at different levels of abstraction.

### The Canonical Hierarchy

**Level 1 --- Theoretical Definition (accounting criterion):**

Class position is determined by two complementary criteria operating simultaneously:

*Accounting Criterion:* Compare value produced (V_produced) to value required for reproduction (V_reproduction). If V_produced > V_reproduction + extraction, the household accumulates surplus --- bourgeois relation. If V_produced ~ V_reproduction, simple reproduction --- proletarian relation. If V_produced < V_reproduction, dependent on transfers --- lumpen or dependent relation.

*Topological Criterion:* Where does the household sit in the graph of extraction? Who extracts from it, who does it extract from? This is the class-in-itself dimension --- objective structural position independent of consciousness.

**Level 2 --- Empirical Operationalization (wealth percentile):**

Accumulated wealth is the observable trace of the accounting criterion over time. A household that persistently extracts surplus accumulates wealth. A household that persistently has surplus extracted does not. Wealth percentile from the Fed SCF maps cleanly:

| Class | Wealth Percentile | Pop Share | Wealth Share |
|-------|-------------------|-----------|--------------|
| BOURGEOISIE | >= 99th | ~1% | ~33% |
| PETIT_BOURGEOISIE | 90th--99th | ~9% | ~33% |
| LABOR_ARISTOCRACY | 50th--90th | ~40% | ~33% |
| PROLETARIAT | < 50th, labor-active | ~35% | ~0% |
| LUMPENPROLETARIAT | < 50th, excluded | ~15% | ~0% |

This is the Pareto distribution: the 1%/9%/40%/50% split emerges from wealth data, not parameter tuning. LA = 40% is a consequence of the 50th--90th percentile window, not a chosen constant.

**Level 3 --- County-Level Data Proxy (home ownership):**

At county resolution, the Fed SCF's national wealth percentiles must be proxied. Home equity is the primary wealth vehicle for the 50th--90th percentile bracket. ACS home ownership rates, corrected by an equity factor calibrated from SCF data (~0.6), produce county-level LA share estimates. Raw home ownership overstates LA share by ~40% because it includes underwater mortgages and minimal-equity ownership.

### The Unit of Analysis: Households

The unit of class analysis is the **household**, not the individual. Theoretical and empirical reasons converge:

*Theoretical:* Class reproduction operates at the household level. The household is the site where reproductive labor (Department III) produces labor power. V_reproduction is a household-level quantity --- it includes housing, food, childcare, eldercare. Individual wages are pooled; individual consumption is shared.

*Empirical:* The Fed SCF measures wealth at the household level. Census/ACS data reports household characteristics. LODES commute flows originate from household locations. The data resolution matches the theoretical unit.

*Internal contradiction:* Fortunati's insight is that the household is *also* a site of exploitation --- Department III labor (overwhelmingly gendered female) produces value appropriated by capital through the husband's wage. The household's aggregate class position (e.g., LABOR_ARISTOCRACY by wealth) coexists with internal exploitation of the reproductive laborer. Resolution: household is the unit for *class position* (wealth, relationship to property). Internal household dynamics --- who does reproductive labor, how value distributes within the unit --- are tracked separately as Department III dynamics (Feature 030 D-P-D' lifecycle). The household can be LA; the wife within it exploited. Both true simultaneously, operating at different levels of analysis. Same fractal pattern: zoom out -> class node; zoom in -> internal relations of production/reproduction.

### Hypergraph Filtration of Class Position

Community hyperedge membership (Feature 029) modifies which economic relationships are operative for a household. This is **filtration** --- a first-class architectural concept, not an ad hoc override.

Each community type can impose filtration predicates that modify class determination inputs:

**INDIGENOUS filtration:** Reservation home ownership does not function as settler property. No appreciation trajectory, no equity extraction, different tenure system (trust land). A flat `trust_land_discount` (initially 0.5, calibrate from BIA data) reduces the effective home ownership weight. This is not an exception --- it's the general principle that the settler property system doesn't apply uniformly.

**INCARCERATED filtration:** Incarceration severs labor market participation entirely. Regardless of prior wealth, an incarcerated household member's productive capacity is zero (or near-zero given prison labor at sub-minimum wages). Precarity assessment escalates to EXCLUDED.

**UNDOCUMENTED filtration:** Legal exclusion from formal labor protections, housing markets, and banking compresses effective wealth accumulation regardless of income. Home ownership pathway is structurally blocked or severely impaired. Precarity floor is PRECARIOUS minimum.

**DISABLED filtration:** Higher reproduction costs (V_reproduction inflated by accommodation, medical, care needs) shift the accounting criterion --- the same nominal wealth buys less class security. Effective wealth percentile is discounted by a reproduction cost modifier from CommunityState.

The general pattern: `effective_input = raw_input x filtration_modifier(community_memberships)`. When a household holds multiple community memberships with conflicting filtrations, the most restrictive (most disadvantaged) filtration applies. INDIGENOUS always overrides SETTLER interpretation of property.

### National Rent Differential

Imperial rent (Phi) does not distribute uniformly across the core working class. Settler-nation workers receive full Phi; internally colonized workers receive partial or no Phi, with the gap captured by racialized wage differentials within the same NAICS codes at county level.

The race-specific rent differential uses ACS median earnings by race x industry:

```
Phi_differential[nation, fips, naics] =
    median_earnings[SETTLER, fips, naics] - median_earnings[nation, fips, naics]
```

This differential is the empirical trace of the theoretical claim that the principal contradiction within US borders is imperialism vs. oppressed nations. If the wage gap within the same job at the same location is non-zero, the difference is structural --- it measures the portion of imperial rent that is withheld from the internally colonized nation.

### Solidarity Potential

Solidarity potential between two households (or between household-blocks at county resolution) is a derived quantity incorporating class proximity, community overlap, and rent differential:

```
solidarity_potential(A, B) = base_class_solidarity
    + community_bonus x |communities(A) intersection communities(B)|
    - rent_differential_penalty x |Phi_A - Phi_B|
```

This feeds directly into the George Jackson bifurcation (Feature 002 dialectical field topology): whether crisis produces fascism or revolution depends on whether solidarity edges cross the colonial divide. The rent differential penalty is the formal expression of why cross-colonial solidarity is structurally difficult --- the imperial rent difference is a material barrier to shared class interest.

### Home Ownership as the LA Mechanism

Home ownership is not merely a proxy for wealth --- it IS the mechanism of labor aristocracy formation in the US core. The mortgage/equity accumulation pathway:

*Upward mobility:* Renting -> ownership with equity -> LA. Access is gated by nation (redlining, lending discrimination, HOA exclusion, appraisal bias) and community (disability accommodation costs, documentation status). Hypergraph modifiers on V_reproduction determine who can make this transition at what rate.

*Downward mobility:* Foreclosure = wealth destruction = LA -> Proletariat. The 2008 crisis was mass de-settling, disproportionately hitting Black and Latino homeowners (subprime targeting as racialized dispossession). Maps directly to: crisis -> wealth destruction -> LA -> Proletariat, concentrated in internally colonized populations.

*DPD' connection:* Inheritance is the intergenerational class reproduction mechanism. Housing equity is the primary inheritance vehicle for the 50th--90th percentile bracket. Foreclosure severs the inheritance mechanism --- accumulated V transfers to institutional investors instead of children. Detroit 2008--2012: the foreclosure wave broke the inheritance mechanism for a generation of Black homeowners. The inheritance mechanism is severed for the whole household unit simultaneously.

*The Indigenous exception:* INDIGENOUS hyperedge filters out the settler property interpretation. Reservation home ownership does not count toward settler-LA threshold because the property is not functioning as settler property --- nominal value, no appreciation trajectory, no equity extraction mechanism, different tenure system. Handled by filtration, not ad hoc exception.

---

## Clarifications

### Session 2026-03-01

- Q: Can solidarity_potential produce negative values, or should it be clamped? -> A: Negative values are meaningful. They represent active hostility (scapegoating, nativism) that feeds fascism dynamics in the George Jackson bifurcation. No floor clamp. The bifurcation analysis distinguishes "no solidarity" (zero) from "active antagonism" (negative).
- Q: Is base_class_solidarity a flat constant or class-pair dependent? -> A: Symmetric 5x5 class-pair matrix (15 unique values in GameDefines). Two proletarians share higher base solidarity than a bourgeois-proletariat pair. Class proximity shapes the base term.
- Q: What is the default value for UNDOCUMENTED documentation_exclusion_factor? -> A: 0.6 (40% discount on effective wealth). More severe than the suggested 0.7 --- undocumented exclusion from formal property/banking is structurally deep.

### Session 2026-02-25 (original development)

- Q: Should class position be measured at individual or household level? -> A: Household. Fed SCF measures household wealth. V_reproduction is household-level. The household is the unit of class reproduction. Internal household exploitation (Dept III) tracked separately.
- Q: How do Indigenous reservations fit the wealth-based framework? -> A: INDIGENOUS filtration with trust_land_discount. Reservation property operates under qualitatively different property regime. General pattern, not exception.
- Q: What about mixed-nation households? -> A: At current resolution (county-level class blocks), "most disadvantaged membership" rule is adequate. At finer resolution, revisit.
- Q: Does this spec prescribe household instances vs statistical class blocks? -> A: No. The spec is agnostic --- works either way. Implementation decision for plan phase.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 --- Classify Household Class Position (Priority: P1)

A simulation researcher classifies a household's class position from wealth data and precarity indicators, producing one of five class positions consistent with both the theoretical accounting criterion and the empirical wealth operationalization.

**Why this priority**: Foundation --- every other system depends on knowing what class a household occupies. Without this, no transitions, no dynamics, no bifurcation analysis.

**Independent Test**: Provide known household wealth + precarity data, verify classification matches expected position. Verify that the accounting criterion and the wealth percentile produce the same classification for calibration test cases.

**Acceptance Scenarios**:

1. **Given** a household with wealth at the 75th percentile nationally, **When** classifying, **Then** the system returns LABOR_ARISTOCRACY regardless of income level or Phi_hour value.
2. **Given** a household with wealth at the 25th percentile and PrecarityStatus.STABLE, **When** classifying, **Then** the system returns PROLETARIAT.
3. **Given** a household with wealth at the 10th percentile and PrecarityStatus.EXCLUDED (incarcerated primary earner), **When** classifying, **Then** the system returns LUMPENPROLETARIAT.
4. **Given** a household with wealth at the 95th percentile, **When** classifying, **Then** the system returns PETIT_BOURGEOISIE.
5. **Given** a household with wealth at the 99.5th percentile, **When** classifying, **Then** the system returns BOURGEOISIE.
6. **Given** a household with wealth at the 55th percentile and PrecarityStatus.EXCLUDED, **When** classifying, **Then** the system returns LABOR_ARISTOCRACY (wealth overrides precarity above 50th percentile --- wealth is the dominant criterion for the upper half).

______________________________________________________________________

### User Story 2 --- Apply Community Filtration to Class Determination (Priority: P1)

A simulation researcher classifies households that hold community hyperedge memberships with filtration predicates, producing class positions that reflect the modified economic relationships imposed by those memberships.

**Why this priority**: Without filtration, the classifier treats all households as if they operate within the settler property system. This produces systematically wrong classifications for Indigenous, incarcerated, undocumented, and disabled populations.

**Independent Test**: Provide households with known community memberships and wealth data. Verify that filtration modifies classification relative to the unfiltered baseline in the expected direction.

**Acceptance Scenarios**:

1. **Given** a household with 60th percentile wealth and INDIGENOUS community membership on trust land, **When** classifying with filtration, **Then** the effective wealth percentile is discounted by trust_land_discount and the household may classify as PROLETARIAT rather than LABOR_ARISTOCRACY.
2. **Given** a household with 45th percentile wealth and INCARCERATED membership (primary earner incarcerated), **When** classifying with filtration, **Then** PrecarityStatus is overridden to EXCLUDED and the household classifies as LUMPENPROLETARIAT.
3. **Given** a household with 55th percentile wealth and UNDOCUMENTED membership, **When** classifying with filtration, **Then** the precarity floor is PRECARIOUS minimum and effective wealth is discounted by documentation exclusion factor.
4. **Given** a household with 65th percentile wealth and DISABLED membership, **When** classifying with filtration, **Then** effective wealth is discounted by the reproduction_cost_modifier from the DISABLED CommunityState, potentially shifting from LA to PROLETARIAT.
5. **Given** a household with multiple community memberships (INDIGENOUS + DISABLED), **When** classifying with filtration, **Then** both filtrations apply and the most restrictive effective position is used.
6. **Given** a household with SETTLER membership and no other filtration-triggering memberships, **When** classifying with filtration, **Then** the classification is identical to the unfiltered baseline (SETTLER is the default operating condition of the property system).
7. *(FR-005)* **Given** county-level ACS home ownership data for Wayne County (26163), **When** the home ownership LA proxy is computed with equity_factor from ClassSystemDefines (~0.6), **Then** the resulting LA share is lower than the raw home ownership rate.

______________________________________________________________________

### User Story 3 --- Compute Solidarity Potential (Priority: P2)

A simulation researcher computes solidarity potential between household-pairs (or class-block pairs at county resolution) to determine the structural basis for cross-group organizing.

**Why this priority**: Solidarity potential feeds the George Jackson bifurcation. Without it, the simulation cannot distinguish crisis outcomes (fascism vs revolution) based on the topology of cross-colonial solidarity.

**Independent Test**: Provide household pairs with known community memberships and rent values. Verify that community overlap increases solidarity potential and rent differential decreases it.

**Acceptance Scenarios**:

1. **Given** two households both in the NEW_AFRIKAN and PROLETARIAT communities with identical Phi_hour, **When** computing solidarity potential, **Then** the result includes a community_bonus for shared membership and zero rent_differential_penalty.
2. **Given** one SETTLER LA household (Phi_hour = 0.15) and one NEW_AFRIKAN proletariat household (Phi_hour = 0.02), **When** computing solidarity potential, **Then** the rent_differential_penalty significantly reduces potential relative to same-nation pairs.
3. **Given** two households sharing INCARCERATED community membership across the colonial divide (one SETTLER, one NEW_AFRIKAN), **When** computing solidarity potential, **Then** shared INCARCERATED membership provides a community_bonus that partially offsets the rent differential --- this is the cross-class bridge mechanism from Feature 029.
4. **Given** two households with zero community overlap and maximum rent differential, **When** computing solidarity potential, **Then** the result is at or near the minimum (this is the structural basis of fascism --- no solidarity edges cross the colonial divide).

______________________________________________________________________

### User Story 4 --- Compute National Rent Differential (Priority: P2)

A simulation researcher computes nation-specific Phi_hour using the racial wage gap within the same NAICS codes at county level, producing the empirical measure of differential imperial rent distribution.

**Why this priority**: The rent differential is the material basis for the solidarity potential penalty and the principal contradiction within US borders. Without it, the simulation cannot explain why cross-colonial solidarity is structurally difficult.

**Independent Test**: Provide county-level ACS earnings data by race x NAICS. Verify that the computed differential matches expected patterns (positive for most industries, larger for industries with known discrimination).

**Acceptance Scenarios**:

1. **Given** ACS median earnings for SETTLER and NEW_AFRIKAN workers in Manufacturing (NAICS 31-33) in Wayne County, **When** computing Phi_differential, **Then** the result is positive (settler earnings exceed New Afrikan earnings in same industry).
2. **Given** ACS data where a NAICS code is suppressed for a minority group due to small sample, **When** computing Phi_differential, **Then** the system returns NoDataSentinel for that code and continues with available data.
3. **Given** county-level Phi_differential for all available NAICS x nation combinations, **When** aggregating to county-level average, **Then** the result is employment-weighted by NAICS composition at county level.
4. **Given** Phi_differential for Wayne vs Oakland counties, **When** comparing, **Then** Wayne shows larger absolute differentials (consistent with the internal colony thesis --- the gap is wider where the extractive relationship is more direct).

______________________________________________________________________

### User Story 5 --- Track DPD' Lifecycle Class Reproduction (Priority: P3)

A simulation researcher tracks intergenerational class reproduction through the D-P-D' lifecycle circuit, with inheritance flows at phase transitions differentiated by class position.

**Why this priority**: Without lifecycle integration, the class system is static --- it classifies but doesn't reproduce. Class dynamics require modeling how class position transmits (or fails to transmit) across generations.

**Independent Test**: Provide a household at a known class position undergoing a DPD' phase transition. Verify that inheritance flows preserve or disrupt class position as expected.

**Acceptance Scenarios**:

1. **Given** an LA household transitioning D' -> D (elder wealth transfer to next generation), **When** inheritance is computed, **Then** the primary transfer is home equity and the receiving household's wealth percentile reflects the inheritance.
2. **Given** a proletariat household undergoing the same transition, **When** inheritance is computed, **Then** minimal or zero wealth transfers --- class poverty reproduces itself.
3. **Given** an LA household that experienced foreclosure (crisis dispossession), **When** D' -> D transition occurs, **Then** the inheritance mechanism is severed --- no home equity to transfer, class reproduction interrupted.
4. **Given** Wayne County 2008--2012 crisis period, **When** tracking LA -> Proletariat transitions via homeownership decline, **Then** the rate of class downward mobility correlates (r > 0.6) with foreclosure rates.

______________________________________________________________________

### User Story 6 --- Validate Fractal Consistency (Priority: P3)

A simulation researcher verifies that zooming into Core Non-Bourgeoisie replicates the four-node pattern internally, with the expanded class taxonomy applying at the sub-scale.

**Why this priority**: Fractal consistency is a constitutional requirement (Architecture Principle: Four-Node Recursive Pattern). If the class system breaks the fractal at any zoom level, the architecture is violated.

**Independent Test**: Instantiate the four-node model at metro Detroit scale. Zoom into Core Non-Bourgeoisie. Verify that the internal structure replicates {Settler Nation, Internal Semi-Colony} x {LA/PB, Proletariat/Lumpen}.

**Acceptance Scenarios**:

1. **Given** the metro Detroit Core Non-Bourgeoisie population, **When** applying the four-node recursive zoom, **Then** the internal structure shows Settler Nation (comprising PB, LA, Settler Lumpen) and Internal Semi-Colonies (comprising Comprador B, National PB, LA subset, Lumpen).
2. **Given** the same ClassPosition enum and classification logic used at the metro scale, **When** applied at the sub-scale, **Then** it produces valid classifications --- the same code path works at both resolutions.
3. **Given** Wayne County (internal colony) and Oakland County (settler suburb), **When** comparing class distributions, **Then** Wayne has higher Proletariat + Lumpen share and lower LA share than Oakland across all available years.

______________________________________________________________________

### Edge Cases

- **Zero-wealth household**: Classifies as PROLETARIAT or LUMPENPROLETARIAT depending on precarity. Wealth of exactly zero is bottom-50th percentile.
- **Negative-wealth household**: Negative net worth (e.g., student debt exceeding assets) classifies as bottom 50%. Debt does not produce a class position below LUMPENPROLETARIAT.
- **Household with one incarcerated and one employed member**: Household-level classification uses aggregate. INCARCERATED filtration applies because at least one member holds the membership. Effective productive capacity is reduced but not zeroed.
- **Mixed-nation household at county resolution**: "Most disadvantaged membership" rule applies per A-006. At current resolution this is adequate.
- **County with fully suppressed ACS race x industry data**: Return NoDataSentinel for rent differential. Do not impute.
- **Home ownership rate = 0% in a hex**: LA proxy returns 0% LA share. All households classified as below-50th percentile pending other data.
- **Accounting criterion and wealth percentile disagree**: Log the disagreement with both values per FR-002. The wealth percentile classification is used for simulation (it's the operationalization); the disagreement log feeds calibration.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Household Classification)**: System MUST classify households into one of five ClassPosition values (BOURGEOISIE, PETIT_BOURGEOISIE, LABOR_ARISTOCRACY, PROLETARIAT, LUMPENPROLETARIAT) using wealth percentile as the primary criterion, with precarity status distinguishing PROLETARIAT from LUMPENPROLETARIAT within the bottom 50%.

- **FR-002 (Dual-Criteria Validation)**: System MUST compute both the accounting criterion (V_produced vs V_reproduction) and the wealth percentile for each household, and log disagreements between the two to a calibration log. The calibration log MUST record: household identifier, tick, accounting classification, wealth classification, magnitude of disagreement.

- **FR-003 (Community Filtration)**: System MUST apply community hyperedge memberships (from Feature 029) as filtration predicates that modify classification inputs. Filtration rules MUST be explicitly defined for each filtration-triggering community type:
  - INDIGENOUS: trust_land_discount on effective wealth (default 0.5, tunable)
  - INCARCERATED: override PrecarityStatus to EXCLUDED
  - UNDOCUMENTED: documentation_exclusion_factor on effective wealth (default 0.6, tunable), precarity floor PRECARIOUS
  - DISABLED: reproduction_cost_modifier from CommunityState discounts effective wealth

- **FR-004 (Filtration Override Hierarchy)**: When a household holds multiple community memberships with conflicting filtrations, the system MUST apply the most restrictive (most disadvantaged) result. INDIGENOUS MUST always override SETTLER interpretation of property.

- **FR-005 (Home Ownership LA Proxy)**: System MUST compute county-level LA share proxy from ACS home ownership data using: `LA_share_proxy = home_ownership_rate x equity_factor`. equity_factor is calibrated from SCF data (default ~0.6, tunable). INDIGENOUS trust_land_discount applies to reservation-county home ownership rates.

- **FR-006 (Solidarity Potential)**: System MUST compute solidarity potential between agent-pairs using community overlap, base class solidarity, and rent differential penalty. The formula MUST be: `solidarity_potential(A, B) = base_class_solidarity(class_A, class_B) + community_bonus x |communities(A) intersection communities(B)| - rent_differential_penalty x |Phi_A - Phi_B|`. base_class_solidarity is a symmetric 5x5 class-pair matrix (15 unique values) stored in GameDefines; class proximity yields higher base solidarity. Negative output values are permitted and represent active hostility (feeds fascism dynamics in bifurcation analysis). No floor clamp. All coefficients in GameDefines.

- **FR-007 (National Rent Differential)**: System MUST compute nation-specific Phi_hour differentials using ACS median earnings by race x NAICS at county level. Suppressed data cells MUST propagate as NoDataSentinel. County-level aggregate MUST be employment-weighted.

- **FR-008 (DPD' Inheritance Integration)**: System MUST integrate with Feature 030 D-P-D' lifecycle to compute inheritance flows at D' -> D phase transitions, differentiated by class position. Foreclosure/dispossession events MUST sever the inheritance mechanism for the affected household.

- **FR-009 (Fractal Consistency)**: When the simulation zooms into Core Non-Bourgeoisie, the expanded class taxonomy MUST replicate the four-node pattern internally. The same ClassPosition enum and classification logic MUST apply at both zoom levels.

- **FR-010 (Crisis Dispossession)**: System MUST model crisis-driven LA -> Proletariat transitions via wealth destruction (foreclosure, eviction). The dispossession rate MUST be modifiable by community membership (racialized subprime targeting is a historical input, not a random process).

- **FR-011 (All Coefficients in GameDefines)**: trust_land_discount, documentation_exclusion_factor, equity_factor, base_class_solidarity, community_bonus, rent_differential_penalty, and all other tunable parameters MUST be centralized in GameDefines, not hardcoded.

- **FR-012 (Backward Compatibility)**: The existing ClassPositionClassifier protocol and DefaultClassPositionClassifier in Feature 013 MUST continue to work for callers that do not supply community membership data. Filtration is additive --- no filtration input produces identical results to the current implementation.

### Key Entities

- **Household**: Unit of class analysis. Holds wealth percentile, precarity status, community memberships, imperial rent share (Phi_hour). Can be instantiated individually or as statistical class-blocks at county resolution.
- **ClassPosition**: Five-value enum (BOURGEOISIE, PETIT_BOURGEOISIE, LABOR_ARISTOCRACY, PROLETARIAT, LUMPENPROLETARIAT) determined by wealth percentile with precarity sub-classification.
- **FiltrationPredicate**: Community-type-specific modifier that adjusts classification inputs. Each community type (INDIGENOUS, INCARCERATED, UNDOCUMENTED, DISABLED) defines its own predicate with specific parameters.
- **SolidarityPotential**: Derived quantity between household-pairs incorporating class proximity, community overlap, and rent differential. Feeds bifurcation analysis.
- **RentDifferential**: Nation-specific Phi_hour computed from ACS earnings gaps within same NAICS codes at county level. Measures differential imperial rent distribution.
- **CalibrationLog**: Record of disagreements between accounting criterion and wealth percentile classifications. Contains household ID, tick, both classifications, and magnitude of disagreement. Implemented as `CALIBRATION_DISAGREEMENT` event payloads on the event bus (see research.md R-006), not as a standalone persistence model.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Accounting-Wealth Agreement)**: For the Detroit test case (Wayne + Oakland + Macomb, 2010--2024), the accounting criterion and wealth percentile classifications agree for >=90% of household-equivalents (county-level class share comparison).

- **SC-002 (Pareto Emergence)**: Running the accounting dynamics forward from initial conditions, the simulation produces a wealth distribution approximating the empirical Pareto pattern (1%/9%/40%/50% +/- 5 percentage points per bracket).

- **SC-003 (Oakland > Wayne LA Share)**: The home ownership proxy produces higher LA share for Oakland County (26125) than Wayne County (26163) for every year 2010--2024.

- **SC-004 (Crisis Dispossession)**: The 2008--2012 period shows accelerated LA -> Proletariat transitions in Wayne County, with homeownership decline correlating (r > 0.6) with class share shifts.

- **SC-005 (Filtration Direction)**: INDIGENOUS filtration reduces effective LA share relative to unfiltered baseline. INCARCERATED filtration increases LUMPENPROLETARIAT share. DISABLED filtration reduces effective wealth percentile. All directionally correct.

- **SC-006 (Rent Differential Sign)**: Phi_differential is positive (settler > colonized earnings) for >=80% of non-suppressed NAICS x county x nation combinations in the Detroit tri-county area.

- **SC-007 (Solidarity Gradient)**: Solidarity potential is monotonically increasing with community overlap and monotonically decreasing with rent differential, verified by parameter sweep.

---

## Assumptions

- **A-001**: The Pareto wealth distribution (1%/9%/40%/50%) is sufficiently stable across 2010--2024 that national SCF thresholds can be applied to county-level proxies without annual recalibration.
- **A-002**: Home ownership with positive equity is a valid proxy for the 50th percentile wealth threshold at county level. Calibration factor from SCF (~0.6) accounts for underwater mortgages and minimal equity.
- **A-003**: Reservation counties can be identified by FIPS code cross-referenced with BIA tribal land boundaries. Imperfect but sufficient for MVP.
- **A-004**: The racial wage gap within same NAICS codes is a valid proxy for differential Phi distribution by nation. Assumes the gap reflects structural position, not individual productivity differences (consistent with MLM-TW theory).
- **A-005**: Feature 029 community hyperedge layer is implemented and provides CommunityState with reproduction_cost_modifier for DISABLED filtration and the full community taxonomy for filtration predicates.
- **A-006**: Mixed-nation households are sufficiently rare in the simulation's current resolution (county-level class blocks, not individual households) that the "most disadvantaged membership" rule is adequate. At finer resolution, this may need revisiting.
- **A-007**: Feature 030 D-P-D' lifecycle circuit provides inheritance flow mechanics. If not yet integrated, inheritance flows default to zero (no intergenerational transmission) and DPD'-dependent scenarios are deferred.

---

## Dependencies

- **013-melt-basket-visibility**: ClassPosition enum, wealth percentile thresholds, PrecarityStatus, ClassPositionClassifier protocol
- **026-tri-county-economic-substrate**: H3 spatial substrate, county-level economic tensors, QCEW/BEA data hydration
- **029-community-hyperedge-upgrade**: CommunityType taxonomy, CommunityState (reproduction_cost_modifier, rent_access_modifier), CommunityConsciousness, HyperedgeCategory, ContradictionAxis, cross-class bridge detection
- **030-dpd-lifecycle-circuit**: D-P-D' phase tracking, inheritance flow mechanics, legitimation index
- **031-organization-base-model**: Organization composition queries (class, community, lifecycle) that consume class position data from this spec

---

## What This Spec Does NOT Include

- Full XGI hypergraph algorithm implementation (uses the interface provided by Feature 029 --- community membership, overlap computation, filtration predicates)
- Organization-level dynamics (handled by 031 org base model and 032 OODA)
- GUI/visualization of class distribution or hypergraph structure
- International class dynamics (periphery proletariat, comprador bourgeoisie outside US borders)
- Climate modeling interactions with class dynamics
- Religious institution capture dynamics (separate spec)
- NPC AI decision-making based on class analysis (deferred to OODA Phase 2)
- Full individual-level household agent instantiation (the spec works at either individual or statistical-block resolution --- implementation decides)

---

## Data Sources

| Data Element | Source | Resolution | Purpose |
|--------------|--------|------------|---------|
| Wealth Percentile Thresholds | Fed SCF | National, triennial | Class position boundaries |
| Home Ownership Rates | ACS (B25003) | County, annual | LA share proxy |
| Median Earnings by Race x Industry | ACS (S2001/B20017) | County x Race x NAICS | Rent differential |
| Employment by NAICS | QCEW | County x NAICS, annual | Rent differential weighting |
| Foreclosure/Eviction Rates | Eviction Lab + ATTOM/FRED | County, annual | Crisis dispossession |
| Trust Land Boundaries | BIA / TIGER | County FIPS | Indigenous filtration |
| CPI Adjustment | FRED (CPIAUCSL) | National, monthly | V_reproduction inflation adjustment |
| Labor Force Participation | BLS LAUS | County, annual | Precarity assessment |
| U-6 Unemployment | BLS CPS | State/metro, monthly | Precarity refinement |
