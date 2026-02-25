# Feature Specification: Unified Class System

**Spec ID**: `026-unified-class-system`
**Feature Branch**: `026-unified-class-system`
**Created**: 2026-02-25
**Status**: Draft
**Depends On**: 014-wealth-based-class-position, 016-class-dynamics-engine, 020-organization-base-model

---

## Theoretical Foundation

This spec reconciles two class determination frameworks developed across the Babylon project into a single canonical architecture. The design doc's accounting + topological criteria define what class *is*. The TVT/MELT wealth percentile framework operationalizes how to *measure* it with available data. They are the same claim at different levels of abstraction.

### The Canonical Hierarchy

**Level 1 — Theoretical Definition (from class system design doc):**

Class position is determined by two complementary criteria:

*Accounting Criterion:* Compare value produced to value required for reproduction.

| Class Position | Condition | Interpretation |
|----------------|-----------|----------------|
| Proletariat | V_produced > V_reproduction | Exploited; surplus extracted |
| Labor Aristocracy | V_produced < V_reproduction | Net beneficiary; receives Φ |
| Lumpen | V_produced ≈ 0 | Excluded from production |

*Topological Criterion:* Position in global value chains (chain_position index 0.0 = extraction origin, 1.0 = consumption terminus). LA sits at accumulation terminus (downstream). Proletariat sits upstream. Comprador class is downstream-but-peripheral.

**Level 2 — Empirical Operationalization (from TVT/MELT work):**

Wealth percentile is the integral over time of the accounting criterion:

```
Wealth(t) = ∫₀ᵗ (W - V_reproduction) dt
```

Where W includes imperial rent Φ for LA. The Pareto distribution (1%/9%/40%/50%) *emerges from* the accounting dynamics — it is an empirical regularity, not an independent stipulation. If the simulation's accounting dynamics don't reproduce something approximating that distribution, the model is falsified.

**Level 3 — Data Proxies (county-level):**

| Theoretical Quantity | Empirical Proxy | Data Source |
|----------------------|-----------------|-------------|
| Wealth percentile (≥50th) | Home ownership with equity | ACS B25003, B25077 |
| Wealth percentile (≥90th) | Investment income + business ownership | IRS SOI |
| Precarity (P vs L split) | U-6, PTER, discouraged, incarcerated | BLS LAUS, ACS, BJS/Vera |
| V_reproduction | Consumer expenditure by county | BLS CEX via ACS proxy |
| Φ_hour | Imperial rent flow rate | Derived from τ, γ_basket, W |

### The Household as Unit of Class Analysis

Class position is determined at the **household unit** level, not the individual level. This is both theoretically and empirically correct:

*Theoretical basis:* The family/household is the production unit of Department III (reproductive labor). V_reproduction is a household cost — food, shelter, care are consumed and produced at household scale. The DPD' lifecycle circuit (dependency → production → dependency') operates through family structures. Inheritance — the intergenerational class reproduction mechanism — flows through households.

*Empirical basis:* The Fed SCF (Survey of Consumer Finances) that produces the Pareto wealth distribution measures *household* net worth. ACS home ownership is measured at household level. A non-working spouse in a homeowning household is LA by household membership, not lumpen by individual labor market status.

*Internal structure:* The household is LA as a unit; internal exploitation (gendered reproductive labor) is tracked separately as Department III dynamics. Zoom out → class node. Zoom in → relations of reproduction. Same fractal pattern as everything else in Babylon.

*Implementation:* The simulation agent for class dynamics is the Household, not the Individual. Each Household has: aggregate_wealth (determines class position), member_count (affects V_reproduction), community_memberships (via hyperedge, see below), dpdprime_phase (D, P, or D' — the lifecycle position), and internal_labor_allocation (who does reproductive work — gendered, tracked for γ_III).

### The Hypergraph as Filtration Mechanism

Identity categories (nation, race, gender, sexuality, disability, documentation status) are modeled as hyperedges in an XGI hypergraph. These hyperedges do not create new class positions. They serve three functions:

**Function 1 — Modulate access to class position.** Nation and race structure the *probability* of occupying a given wealth percentile. A NEW_AFRIKAN household and a SETTLER household in the same county have different effective Φ (measurable via racial wage gap within same NAICS codes). Over time, differential Φ → differential wealth accumulation → differential class composition by nation. Wayne County's lower homeownership rate *is* the national question expressed in property relations.

**Function 2 — Create solidarity pathways.** Shared community membership creates potential solidarity edges that bypass the settler/colonized divide. A DISABLED QUEER SETTLER worker and a DISABLED QUEER NEW_AFRIKAN worker have shared exclusion from the imperial bargain that creates material basis for solidarity. The George Jackson bifurcation operates on this: which hyperedges do the solidarity edges cross?

**Function 3 — Filter which economic relationships are operative.** This is the critical architectural innovation. The hypergraph acts as a **filtration** — a nested sequence of predicates that determines which rules of the game apply to a given agent.

The canonical filtration example: **INDIGENOUS overrides the settler property interpretation.** An Indigenous homeowner on a reservation is not participating in the settler property regime. Trust land ≠ fee simple. The property doesn't appreciate on the same trajectory, can't be leveraged the same way, doesn't carry the same class-ascendancy meaning. The INDIGENOUS hyperedge filters out the settler-LA interpretation of home ownership.

Generalized filtration rules:

| Hyperedge | Filters | Economic Effect |
|-----------|---------|-----------------|
| INDIGENOUS | Settler property regime | Home ownership ≠ settler-LA; different property relation (trust land) |
| UNDOCUMENTED | State transfer access | Reduced V_reproduction sources; wage suppression |
| INCARCERATED | Labor market participation | Total exclusion; forced labor at sub-subsistence rates |
| DISABLED | Labor market access + V_reproduction | Higher reproduction costs; constrained employment |
| SETTLER | (default — no filtration) | Full access to imperial rent, property regime, state services |

In algebraic topology terms: the hyperedges define a filtration on agent-space that determines which simplicial complex (which set of relationships) is active at each level.

### Home Ownership as Settler-Colonial Metric

Home ownership is the primary empirical proxy for the LA wealth threshold (50th percentile), and this is not an empirical coincidence — it is the material form of the settler colonial bargain.

*Theoretical claim:* Home ownership in the US is title to stolen land. The original dispossession of Indigenous nations is the precondition for the entire property regime. Imperial rent flows to core workers; those who successfully accumulate it convert it into real property (land); land title is the institutional expression of settler colonialism. The 50th percentile wealth threshold mapping roughly to home ownership is the settler bargain materialized.

*Upward mobility mechanism:* Stable employment → savings → home purchase → cross 50th percentile → enter LA. Access to this path is gated by nation (redlining, lending discrimination, HOA exclusion, appraisal bias) and community (disability accommodation costs, documentation status). The hypergraph modifiers on V_reproduction determine who can make this transition at what rate.

*Downward mobility mechanism:* Foreclosure = wealth destruction = LA → Proletariat. The 2008 crisis was mass de-settling, disproportionately hitting Black and Latino homeowners (subprime targeting as racialized dispossession). This maps directly to: crisis → wealth destruction → LA → Proletariat, concentrated in internally colonized populations.

*DPD' connection:* Inheritance is the intergenerational class reproduction mechanism. Housing equity is the primary inheritance vehicle for the 50th-90th percentile bracket. Foreclosure severs the inheritance mechanism — accumulated V transfers to institutional investors instead of to children. Detroit 2008-2012: the foreclosure wave broke the inheritance mechanism for a generation of Black homeowners.

*The Indigenous exception:* INDIGENOUS hyperedge filters out the settler property interpretation. Reservation home ownership does not count toward settler-LA threshold because the property is not functioning as settler property — nominal value, no appreciation trajectory, no equity extraction mechanism, different tenure system. This is handled by the filtration mechanism, not by ad hoc exception.

---

## User Scenarios & Testing

### User Story 1 — Classify Household Class Position (Priority: P1)

A simulation researcher needs to classify a household's class position from wealth data and precarity indicators, producing one of five class positions that is consistent with both the theoretical accounting criterion and the empirical wealth operationalization.

**Why this priority**: This is the foundation — every other system depends on knowing what class a household occupies. Without this, no transitions, no dynamics, no bifurcation analysis.

**Independent Test**: Provide known household wealth + precarity data, verify classification matches expected position. Verify that the accounting criterion (V_produced vs V_reproduction) and the wealth percentile produce the same classification for calibration test cases.

**Acceptance Scenarios**:

1. **Given** a household with wealth at the 75th percentile nationally, **When** classifying, **Then** the system returns LABOR_ARISTOCRACY regardless of income level or Φ_hour value.

2. **Given** a household with wealth at the 25th percentile and PrecarityStatus.STABLE (regular W-2 employment), **When** classifying, **Then** the system returns PROLETARIAT.

3. **Given** a household with wealth at the 10th percentile and PrecarityStatus.EXCLUDED (incarcerated primary earner), **When** classifying, **Then** the system returns LUMPENPROLETARIAT.

4. **Given** a household with wealth at the 95th percentile, **When** classifying, **Then** the system returns PETIT_BOURGEOISIE.

5. **Given** calibration test data where V_produced and V_reproduction are known, **When** comparing accounting-criterion classification to wealth-percentile classification, **Then** they agree for ≥90% of test cases. Disagreements are logged with explanatory context.

6. **Given** a household with a non-working spouse and total household wealth at the 70th percentile, **When** classifying, **Then** the system returns LABOR_ARISTOCRACY (household-level, not individual).

______________________________________________________________________

### User Story 2 — Apply Hypergraph Filtration to Class Metrics (Priority: P1)

A simulation researcher needs community hyperedge memberships to modify how economic relationships are interpreted for each household, so that the INDIGENOUS filtration (and others) correctly adjusts class determination.

**Why this priority**: Without filtration, the model produces false positives (Indigenous homeowners classified as settler-LA) and false negatives (undocumented households classified as proletariat when they're functionally lumpen due to severed state transfer access).

**Independent Test**: Classify two households with identical wealth but different hyperedge memberships. Verify filtration produces different effective class positions or different V_reproduction calculations.

**Acceptance Scenarios**:

1. **Given** an INDIGENOUS household on reservation trust land with nominal home value of $45,000, **When** computing effective wealth position, **Then** the INDIGENOUS filtration adjusts the home equity contribution downward (trust land discount factor) such that the household does NOT classify as LA solely from home ownership.

2. **Given** an UNDOCUMENTED household with PrecarityStatus.PRECARIOUS, **When** computing V_reproduction, **Then** state transfer sources (SNAP, Medicaid, unemployment insurance) are filtered out, increasing the effective V_reproduction gap and pushing toward LUMPENPROLETARIAT.

3. **Given** an INCARCERATED household member, **When** computing household labor market status, **Then** that member contributes zero to household V_produced AND the incarceration costs increase V_reproduction (legal fees, commissary, lost income).

4. **Given** a DISABLED household with wealth at the 55th percentile, **When** computing V_reproduction, **Then** disability-related costs (accommodation, healthcare, transport) increase V_reproduction, potentially pushing the household below effective LA threshold despite nominal wealth.

5. **Given** two households with identical wealth percentiles but one SETTLER and one NEW_AFRIKAN, **When** computing Φ_hour, **Then** the NEW_AFRIKAN household has lower Φ_hour (measurable via racial wage gap within same NAICS codes in the county).

6. **Given** a SETTLER household with no filtration overrides, **When** classifying, **Then** the standard wealth-percentile classification applies without modification.

______________________________________________________________________

### User Story 3 — Compute Solidarity Potential via Hypergraph Overlap (Priority: P2)

A simulation researcher needs to compute solidarity potential between two households (or household-aggregates/class blocks) based on shared community hyperedge memberships and imperial rent differential.

**Why this priority**: Solidarity potential feeds directly into the George Jackson bifurcation — whether crisis produces fascism or revolution depends on whether solidarity edges cross the colonial divide. This requires knowing which households *can* form solidarity based on shared community membership.

**Independent Test**: Provide two agents with known community memberships and rent differentials. Verify solidarity potential formula produces expected values. Verify that cross-colonial-divide solidarity (e.g., DISABLED connecting SETTLER and NEW_AFRIKAN agents) is correctly computed.

**Acceptance Scenarios**:

1. **Given** Agent A (SETTLER, DISABLED, QUEER) and Agent B (NEW_AFRIKAN, DISABLED, QUEER) with moderate Φ differential, **When** computing solidarity_potential, **Then** the community overlap bonus (2 shared memberships) partially offsets the rent differential penalty, producing positive solidarity potential.

2. **Given** Agent A (SETTLER) and Agent B (NEW_AFRIKAN) with no shared community memberships and high Φ differential, **When** computing solidarity_potential, **Then** potential is near zero or negative (no cross-divide pathway).

3. **Given** a community hyperedge (e.g., TRANS) that has been degraded by state repression (reduced infrastructure attribute), **When** computing solidarity transmission through that hyperedge, **Then** transmission is attenuated proportional to infrastructure degradation.

4. **Given** the George Jackson bifurcation test, **When** solidarity edges cross the SETTLER/NEW_AFRIKAN divide, **Then** agitation routes to class_consciousness. **When** solidarity edges do NOT cross that divide, **Then** agitation routes to national_identity (fascist potential).

______________________________________________________________________

### User Story 4 — Track Home Ownership as Class Ascendancy Metric (Priority: P2)

A simulation researcher needs to use home ownership rate (with equity) as the primary county-level proxy for LA share, with the INDIGENOUS filtration correctly excluding reservation trust land.

**Why this priority**: Home ownership is the most available and theoretically grounded county-level proxy for the 50th percentile wealth threshold. It directly operationalizes the settler colonial property relation.

**Independent Test**: Compute LA share proxy for Wayne County and Oakland County using ACS home ownership data. Verify Oakland > Wayne. Verify reservation counties are correctly filtered.

**Acceptance Scenarios**:

1. **Given** ACS home ownership data for Oakland County (26125), **When** computing LA share proxy, **Then** `la_share_proxy = homeownership_rate × equity_factor` where equity_factor is calibrated from SCF (~0.6). Expected: Oakland LA proxy > Wayne LA proxy.

2. **Given** ACS home ownership data for Wayne County (26163), **When** computing LA share proxy, **Then** the lower homeownership rate produces a lower LA share, consistent with higher internal colonization / lower wealth accumulation.

3. **Given** a reservation county (e.g., Shannon County SD / Oglala Lakota, FIPS 46102), **When** computing LA share proxy, **Then** the INDIGENOUS filtration applies a trust_land_discount to home equity, producing a lower effective LA share than raw homeownership rate would suggest.

4. **Given** historical ACS data for Wayne County 2006-2012, **When** tracking homeownership rate over the foreclosure crisis, **Then** the decline in homeownership maps to LA → Proletariat transitions in the class dynamics engine.

5. **Given** gentrification indicators (rising home prices, demographic change) in a county, **When** tracking homeownership composition, **Then** incoming households (higher wealth) replace displaced households (lower wealth), and aggregate LA share may rise even as original residents are dispossessed.

______________________________________________________________________

### User Story 5 — Integrate DPD' Lifecycle with Household Class Reproduction (Priority: P3)

A simulation researcher needs to model how the DPD' (dependency-production-dependency') lifecycle circuit operates at the household level, connecting inheritance, class reproduction, and generational dynamics.

**Why this priority**: DPD' is the mechanism by which class position reproduces across generations. Without it, the simulation can model within-generation dynamics but not intergenerational persistence or disruption of class structure. Lower priority because it operates on a generational timescale and the within-generation dynamics must work first.

**Independent Test**: Run a multi-generational simulation (3+ DPD' cycles) and verify that class position persistence matches empirical intergenerational mobility data (Chetty Opportunity Atlas).

**Acceptance Scenarios**:

1. **Given** an LA household at DPD' phase transition (P → D'), **When** computing inheritance flow, **Then** accumulated household wealth (primarily home equity) transfers to the next-generation household, maintaining class position.

2. **Given** a Proletariat household where the primary earner is incarcerated (forced DPD' interruption), **When** computing inheritance, **Then** wealth transfer is severed — legal costs + lost income + asset seizure produce negative inheritance, pushing next generation deeper into precarity.

3. **Given** a Bourgeoisie household at D' transition, **When** computing inheritance, **Then** capital preservation mechanisms (trusts, estate planning) ensure next generation enters P phase as Bourgeoisie. Inheritance inequality (InheritanceGini) should exceed income inequality.

4. **Given** historical conditions from the 2008 crisis, **When** running multi-year simulation for Wayne County, **Then** the foreclosure wave severs DPD' inheritance for affected households, and the class composition of the *next generation* shows downward shift relative to the pre-crisis trajectory.

5. **Given** class-differentiated DPD' circuits, **When** computing LA lifecycle, **Then** P-phase accumulation (W - V_reproduction > 0 due to Φ) converts to D'-phase wealth, which transfers via inheritance. The LA reproduces itself across generations *through property*.

______________________________________________________________________

### Edge Cases

**Mixed-nation households**: A SETTLER/NEW_AFRIKAN household has members in different national hyperedges. Resolution: household inherits the *most disadvantaged* national membership for filtration purposes (conservative estimate — the system treats mixed households as subject to racialized barriers).

**Household dissolution**: Divorce, death, incarceration split households. The wealth is divided (often unequally, gendered). Each resulting sub-household is reclassified independently. Divorce can be a dispossession event if one party loses the home.

**Multigenerational households**: Common on reservations and in immigrant communities. The DPD' phases overlap — D, P, and D' members coexist. V_reproduction is shared/pooled. Class position reflects the aggregate.

**Zero-wealth-but-high-income**: A new tech worker earning $150k with student debt (negative net worth). Wealth percentile says Proletariat; income says potential LA. Resolution: class is determined by wealth (stock). They are Proletariat who are *accumulating toward* LA. The income determines the *rate* of transition, not the current position.

**Homeowner with negative equity**: Underwater mortgage. Nominal homeowner but effective wealth ≤ 0. They are NOT LA despite owning a home — the equity_factor in the proxy calculation handles this (SCF calibration accounts for underwater mortgages).

---

## Functional Requirements

### FR-001: Household-Level Classification

The system must classify households (not individuals) into one of five class positions based on household-level wealth percentile and household-level precarity assessment.

### FR-002: Dual-Criteria Validation

The system must compute both the accounting criterion (V_produced vs V_reproduction) and the wealth percentile, and log disagreements between the two for calibration purposes.

### FR-003: Hypergraph Filtration

The system must apply community hyperedge memberships as filtration predicates that modify which economic relationships are operative for each household. Filtration rules must be explicitly defined per hyperedge type (INDIGENOUS, UNDOCUMENTED, INCARCERATED, DISABLED, SETTLER as default).

### FR-004: Solidarity Potential Computation

The system must compute solidarity potential between agent-pairs using the formula:

```
solidarity_potential(A, B) = base_class_solidarity
    + community_bonus × |communities(A) ∩ communities(B)|
    - rent_differential_penalty × |Φ_A - Φ_B|
```

### FR-005: Home Ownership LA Proxy

The system must compute county-level LA share proxy from ACS home ownership data with equity factor calibration and INDIGENOUS trust land discount.

### FR-006: DPD' Lifecycle Tracking

The system must track household DPD' phase (D, P, D') and compute inheritance flows at phase transitions, class-differentiated by position.

### FR-007: Filtration Override Hierarchy

When a household has multiple community memberships that produce conflicting filtrations, the system must apply the most restrictive (most disadvantaged) filtration. INDIGENOUS always overrides SETTLER interpretation of property.

### FR-008: National Rent Differential

The system must compute nation-specific Φ_hour differentials using racial wage gap data within same NAICS codes at county level (ACS earnings by race × industry).

### FR-009: Fractal Consistency

When the simulation zooms into Core Non-Bourgeoisie, the expanded class taxonomy must replicate the four-node pattern internally: Settler Nation (PB, LA, Settler Lumpen) and Internal Semi-Colonies (Comprador B, National PB, LA subset, Lumpen). The same ClassPosition enum and classification logic must apply at both zoom levels.

---

## Success Criteria

### SC-001: Accounting-Wealth Agreement

For the Detroit test case (Wayne + Oakland, 2010-2024), the accounting criterion and wealth percentile classifications agree for ≥90% of household-equivalents (county-level class share comparison).

### SC-002: Pareto Emergence

Running the accounting dynamics forward from initial conditions, the simulation produces a wealth distribution approximating the empirical Pareto pattern (1%/9%/40%/50% ± 5 percentage points per bracket).

### SC-003: Oakland > Wayne LA Share

The home ownership proxy produces higher LA share for Oakland County (26125) than Wayne County (26163) for every year 2010-2024.

### SC-004: Crisis Dispossession

The 2008-2012 period shows accelerated LA → Proletariat transitions in Wayne County, with homeownership decline correlating (r > 0.6) with class share shifts.

### SC-005: Indigenous Filtration Correctness

For reservation counties, the INDIGENOUS filtration produces LA share proxies at least 15% lower than raw homeownership rate would suggest (trust land discount is material, not token).

### SC-006: Solidarity Bifurcation

In the George Jackson bifurcation test: when solidarity edges cross the SETTLER/NEW_AFRIKAN divide (computed via hypergraph overlap), crisis routes to class_consciousness. When they don't, crisis routes to national_identity. The bifurcation outcome is determined by topology, not parameters.

### SC-007: Household Consistency

Classification of a non-working spouse in a homeowning household always matches the household classification (LA), never individual classification (would be Lumpen).

### SC-008: Racial Wage Gap Differential

For Wayne County, within the same NAICS sector, NEW_AFRIKAN Φ_hour < SETTLER Φ_hour, computed from ACS earnings by race data.

---

## Data Requirements

### Required Data Sources

| Source | Resolution | Used For | Status |
|--------|------------|----------|--------|
| Fed SCF | National, triennial | Wealth percentile thresholds, Pareto calibration | Available |
| ACS B25003 | County, annual | Home ownership rate | Have |
| ACS B25077 | County, annual | Median home value | Have |
| ACS B25077 by race | County, annual | Racial homeownership gap | Need |
| ACS earnings by race × NAICS | County, annual | National Φ differential | Need |
| IRS SOI | County, annual | Investment income (PB proxy) | Available |
| BLS LAUS (U-6 equivalent) | County, monthly | Precarity assessment | Have |
| ACS B23023 | County, annual | PTER rate | Need |
| ACS B23005 | County, annual | Discouraged workers | Need |
| BJS / Vera Institute | County, annual | Incarceration rate | Available |
| ACS C18120 | County, annual | Disability employment gap | Need |
| BIA / Census AIAN | Reservation, annual | Trust land homeownership | Need |
| Chetty Opportunity Atlas | Tract, cohort | Intergenerational mobility (DPD' validation) | Available |

### MVP Data Strategy

For MVP, use hardcoded national SCF thresholds + ACS homeownership as LA proxy. INDIGENOUS filtration uses reservation county FIPS list with flat trust_land_discount = 0.5 (calibrate later from BIA data). Precarity assessment uses U-6 only. Racial differential uses ACS median earnings by race at county level.

---

## Assumptions

- A-001: The Pareto wealth distribution (1%/9%/40%/50%) is sufficiently stable across 2010-2024 that national SCF thresholds can be applied to county-level proxies without annual recalibration.
- A-002: Home ownership with positive equity is a valid proxy for the 50th percentile wealth threshold at county level. Calibration factor from SCF (~0.6) accounts for underwater mortgages and minimal equity.
- A-003: Reservation counties can be identified by FIPS code cross-referenced with BIA tribal land boundaries. Imperfect but sufficient for MVP.
- A-004: The racial wage gap within same NAICS codes is a valid proxy for differential Φ distribution by nation. Assumes the gap reflects structural position, not individual productivity differences (consistent with MLM-TW theory).
- A-005: XGI hypergraph library is computationally adequate for community membership operations at Babylon's current scale (metro Detroit, ~100-1000 household agents). If performance becomes an issue, migrate to node-attribute approach with manual set intersection.
- A-006: Mixed-nation households are sufficiently rare in the simulation's current resolution (county-level class blocks, not individual households) that the "most disadvantaged membership" rule is adequate. At finer resolution, this may need revisiting.

---

## Dependencies

- **014-wealth-based-class-position**: ClassPosition enum, wealth percentile thresholds, PrecarityStatus
- **016-class-dynamics-engine**: Class transition mechanics (accumulation, dispossession, crisis amplification)
- **013-melt-imperial-rent**: τ, γ_basket, Φ_hour computation
- **020-organization-base-model**: Organization-as-agent architecture (organizations act on class blocks)
- **023-bifurcation-topology**: George Jackson bifurcation uses solidarity potential from this spec

---

## What This Spec Does NOT Include

- Full XGI hypergraph implementation (just the interface this spec requires — community membership, overlap computation, filtration predicates)
- Organization-level dynamics (handled by 020-025 org topology specs)
- GUI/visualization of class distribution or hypergraph structure
- International class dynamics (periphery proletariat, comprador bourgeoisie outside US borders)
- Climate modeling interactions with class dynamics
- Religious institution capture dynamics (separate spec)
