# Feature Specification: Capital Volume I Production Dynamics

**Feature Branch**: `021-capital-volume-i`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Capital Volume I Integration brainstorm — Reserve Army of Labor, Primitive Accumulation/Dispossession, Working Day, Subsumption of Labor, Concentration and Centralization of Capital

---

## Overview

Marx's *Capital Volume I* analyzes the **production** of surplus value — the extraction of unpaid labor at the point of production. Babylon currently models the **composition** of value (c, v, s in the tensor) and the **distribution** of surplus (Volume III's TRPF), but lacks the *dynamics* that generate those values. This feature fills five critical gaps:

1. **Reserve Army of Labor** — How capital accumulation produces unemployment that disciplines wages
2. **Primitive Accumulation / Ongoing Dispossession** — How wealth is forcibly transferred through extra-economic means
3. **The Working Day** — How surplus value is extracted via absolute vs. relative methods
4. **Subsumption of Labor** — How capital reorganizes the labor process itself
5. **Concentration and Centralization** — How capital consolidates toward monopoly

These mechanisms are the **causal engine** behind the tensor values. Without them, the simulation describes *what* value looks like but not *why* it changes.

---

## User Scenarios & Testing

### User Story 1 — Reserve Army of Labor (Priority: P1)

The simulation computes the composition and dynamics of the industrial reserve army for each territory, using labor market data to model three forms of surplus population (floating, latent, stagnant) plus a pauperized layer. The reserve army's size and composition exert measurable downward pressure on wages, directly affecting variable capital (v) in the value tensor.

**Why this priority**: The reserve army is the single most important missing mechanism. It explains *why* wages move — the core question for all downstream calculations. The existing tensor models what wages are but not what forces shape them.

**Independent Test**: Can be fully tested by computing reserve army state from labor market inputs and verifying that higher reserve ratios produce lower wage pressure coefficients. Delivers immediate value by connecting unemployment data to the tensor's v component.

**Acceptance Scenarios**:

1. **Given** a territory with BLS labor data (U-3, U-6, PTER, discouraged workers), **When** the reserve army state is computed, **Then** the system produces a decomposition into floating, latent, stagnant, and pauperized categories with a total reserve ratio.
2. **Given** a territory with reserve_ratio of 0.15, **When** wage pressure is calculated, **Then** the downward pressure on v is measurably stronger than for a territory with reserve_ratio of 0.05.
3. **Given** a tick where mechanization displaces workers, **When** reserve army dynamics flow, **Then** the floating reserve increases by the displaced count and subsequent wage pressure increases.
4. **Given** an economic expansion absorbing workers, **When** reserve army dynamics flow, **Then** the floating reserve decreases and wage pressure decreases proportionally.

______________________________________________________________________

### User Story 2 — Primitive Accumulation / Dispossession Events (Priority: P1)

The simulation tracks discrete acts of ongoing primitive accumulation — foreclosure, eviction, tax sale, eminent domain, wage theft, incarceration-related seizure, pension default, and gentrification displacement. Each event records the value transferred, the parties involved, and the class-position consequences. Aggregate dispossession metrics drive territorial dynamics and class decomposition.

**Why this priority**: Dispossession is the mechanism behind gentrification — Babylon's core case study. The existing dispossession calculator (Feature 016) computes *rates* for class transitions but does not model dispossession as discrete, trackable events with value transfer between territories. This story provides the event infrastructure that makes the Wayne County to Oakland County value transfer visible and quantifiable.

**Independent Test**: Can be tested by emitting dispossession events in a simulation run and verifying they produce correct value transfers between territories, trigger class position changes, and aggregate to territory-level dispossession intensity metrics.

**Acceptance Scenarios**:

1. **Given** a foreclosure event with a known property value, **When** the event is processed, **Then** the system records the value transferred from the dispossessed household to the appropriating entity and adjusts the territory's accumulated wealth accordingly.
2. **Given** a territory experiencing high foreclosure and eviction rates, **When** aggregate dispossession intensity is computed, **Then** the intensity reflects weighted contributions from all dispossession types.
3. **Given** a series of dispossession events in Wayne County, **When** the territorial value transfer is computed, **Then** the cumulative value lost by Wayne County matches the cumulative value gained by receiving territories (minus deadweight loss).
4. **Given** a Labor Aristocracy household that loses housing equity via foreclosure, **When** class position is re-evaluated, **Then** the household transitions toward Proletariat status.

______________________________________________________________________

### User Story 3 — Working Day Characterization (Priority: P2)

The simulation classifies each territory-sector combination by its dominant mode of surplus value extraction: absolute (lengthening the working day), relative (increasing productivity during a fixed day), or mixed. This distinction affects consciousness dynamics because absolute exploitation is *visible* to workers while relative exploitation is *invisible*.

**Why this priority**: The absolute/relative distinction determines *how* surplus is extracted, which directly shapes worker consciousness and organizing capacity. Detroit's gig economy growth represents a return to absolute surplus value extraction — long hours, multiple jobs — which should produce different consciousness dynamics than manufacturing automation (relative extraction).

**Independent Test**: Can be tested by providing sector-level hours and productivity data and verifying that the exploitation mode classification matches expected outcomes (e.g., warehouse work = ABSOLUTE_DOMINANT, software = RELATIVE_DOMINANT).

**Acceptance Scenarios**:

1. **Given** a sector with average weekly hours above 45 and low productivity growth, **When** exploitation mode is classified, **Then** the result is ABSOLUTE_DOMINANT.
2. **Given** a sector with average weekly hours at or below 40 and high productivity growth, **When** exploitation mode is classified, **Then** the result is RELATIVE_DOMINANT.
3. **Given** a MIXED exploitation mode sector, **When** consciousness dynamics are computed, **Then** the visibility modifier reflects the blend of absolute (visible) and relative (invisible) extraction.
4. **Given** working day data over multiple ticks, **When** the trend is analyzed, **Then** the system detects shifts between exploitation modes (e.g., manufacturing sector shifting from ABSOLUTE_DOMINANT to RELATIVE_DOMINANT as automation increases).

______________________________________________________________________

### User Story 4 — Subsumption of Labor Classification (Priority: P3)

The simulation classifies sectors by their mode of labor's subordination to capital: formal subsumption (worker retains craft knowledge but sells labor power), real subsumption (capital controls the labor process, worker is deskilled), or hybrid. This classification affects worker replaceability, wage levels, and consciousness.

**Why this priority**: Subsumption determines whether workers retain the *capacity* for independent production. Under formal subsumption, workers can potentially organize and withdraw labor effectively. Under real subsumption, workers are interchangeable — the reserve army's disciplinary effect is strongest. This creates differential organizing capacity across sectors.

**Independent Test**: Can be tested by classifying sectors using skill level and automation exposure data, then verifying that formal subsumption sectors show different consciousness dynamics than real subsumption sectors.

**Acceptance Scenarios**:

1. **Given** a sector with high average skill level and low automation exposure, **When** subsumption is classified, **Then** the result is FORMAL (or high formal_share).
2. **Given** a sector with low average skill level and high automation exposure, **When** subsumption is classified, **Then** the result is REAL (or high real_share).
3. **Given** a sector under real subsumption with high automation exposure, **When** deskilling pressure is computed, **Then** the pressure value is higher than for formal subsumption sectors.
4. **Given** a sector transitioning from formal to real subsumption over multiple ticks, **When** the labor value is recomputed, **Then** v decreases (deskilled labor is cheaper to reproduce).

______________________________________________________________________

### User Story 5 — Capital Concentration and Centralization (Priority: P3)

The simulation tracks market structure metrics for each territory-sector combination, distinguishing between concentration (individual capitals growing through accumulation) and centralization (existing capitals combining through M&A). The system classifies sectors as COMPETITIVE, OLIGOPOLY, or MONOPOLY based on market concentration indices.

**Why this priority**: Concentration and centralization are the mechanism through which competitive capitalism tends toward monopoly. Lenin's extension (monopoly capital leads to imperialism) connects directly to Babylon's imperial rent framework. This story completes the chain from production (Volume I) through monopoly pricing (Volume III's transformation problem) to imperial rent extraction.

**Independent Test**: Can be tested by providing market structure data (firm sizes, M&A activity) and verifying correct classification of monopoly tendency and accurate computation of concentration metrics.

**Acceptance Scenarios**:

1. **Given** a sector with Herfindahl index above 0.25, **When** monopoly tendency is assessed, **Then** the classification is MONOPOLY.
2. **Given** a sector with Herfindahl index between 0.15 and 0.25, **When** monopoly tendency is assessed, **Then** the classification is OLIGOPOLY.
3. **Given** a sector experiencing high M&A volume (centralization), **When** concentration metrics are updated, **Then** the Herfindahl index increases faster than from organic growth alone.
4. **Given** a sector classified as MONOPOLY, **When** pricing dynamics are computed, **Then** the sector's surplus extraction rate exceeds the economy-wide average (monopoly rent).

______________________________________________________________________

### User Story 6 — Cross-System Integration (Priority: P2)

The five Volume I mechanisms feed into existing simulation systems to create a complete causal chain: reserve army disciplines v in the tensor; dispossession transfers value between territories and triggers class transitions; working day mode shapes consciousness visibility; subsumption determines deskilling pressure that feeds back into the reserve army; concentration drives monopoly rent that augments imperial rent.

**Why this priority**: Without integration, each mechanism operates in isolation. The theoretical power of Volume I is that these mechanisms form a self-reinforcing cycle: accumulation leads to mechanization leads to reserve army leads to wage suppression leads to higher s/v leads to more accumulation. This story ensures the causal chain is closed.

**Independent Test**: Can be tested by running a multi-tick simulation with all five mechanisms active and verifying that the feedback loops produce the expected dynamics (e.g., mechanization leads to rising reserve army leads to falling wages leads to rising exploitation rate).

**Acceptance Scenarios**:

1. **Given** a territory with a high reserve ratio, **When** the tensor is hydrated, **Then** variable capital (v) reflects the wage-suppression effect of the reserve army.
2. **Given** a dispossession event, **When** the class transition engine runs, **Then** the event triggers the appropriate class position change (LA to Proletariat for foreclosure).
3. **Given** a sector under real subsumption experiencing mechanization, **When** reserve army dynamics flow, **Then** displaced workers enter the floating reserve at a rate proportional to automation exposure.
4. **Given** a MONOPOLY-classified sector with high concentration, **When** imperial rent is computed, **Then** monopoly rent is included as a component of total rent extraction.

______________________________________________________________________

### User Story 7 — Data Loaders for Production Dynamics (Priority: P1)

The simulation ingests real-world labor market, housing, and productivity data from federal statistical sources to populate the Reserve Army, Dispossession, and Working Day mechanisms. Without empirical data, these mechanisms can only operate on synthetic inputs and cannot be calibrated or falsified against the Detroit case study.

**Why this priority**: The success criteria (SC-001, SC-002, SC-003, SC-007) all require calibration against empirical data. The Reserve Army requires BLS unemployment decompositions. Dispossession requires Eviction Lab filings and foreclosure rates. The Working Day requires BLS hours and productivity indices. The existing data loader infrastructure (DataLoader ABC, LoaderConfig, checkpoint system) provides a proven pattern to follow.

**Independent Test**: Can be tested by running each loader against its source API or bulk files and verifying that the ingested data matches expected row counts, covers the target geographic scope (Wayne, Oakland, Macomb counties), and passes schema validation against the 3NF reference database.

**Acceptance Scenarios**:

1. **Given** BLS bulk data files for unemployment categories (U-3, U-6, PTER, discouraged workers, marginally attached), **When** the BLS unemployment loader runs, **Then** the system ingests county-level unemployment decompositions for Wayne, Oakland, and Macomb counties across the target year range (2005-2020) into the reference database.
2. **Given** Eviction Lab data files with eviction filings and executions by county, **When** the Eviction Lab loader runs, **Then** the system ingests county-level eviction rates for the target counties and years, with each record linked to the appropriate FIPS code and time period.
3. **Given** CoreLogic/ATTOM foreclosure data, **When** the foreclosure loader runs, **Then** the system ingests county-level foreclosure rates with the 2008-2012 crisis period fully covered for the Detroit metro area.
4. **Given** Census ACS data for housing tenure, migration, and institutional ownership, **When** the Census housing loader runs, **Then** the system captures tenure changes, net migration by income bracket, and institutional investor ownership shares at the county level.
5. **Given** BLS data for average weekly hours and productivity indices by industry, **When** the BLS hours/productivity loader runs, **Then** the system ingests sector-level working day metrics linked to NAICS codes for the target counties and years.

______________________________________________________________________

### Edge Cases

- What happens when reserve_ratio approaches 1.0 (near-total unemployment)? Wage pressure should saturate at a ceiling rather than diverge.
- What happens when all dispossession types have zero rates? The dispossession intensity should be exactly zero with no spurious events emitted.
- What happens when a sector has zero employees (abandoned industry)? Working day and subsumption metrics should not be computed; the system should return a sentinel/skip value.
- What happens when Herfindahl index is exactly at classification boundaries (0.15, 0.25)? Boundary behavior must be deterministic and documented.
- What happens when reserve army inflows exceed the total labor force? Flows must be clamped to prevent negative employed population.
- What happens when a dispossession event's value exceeds the territory's total wealth? The transfer should be clamped to available wealth, not create negative wealth.
- What happens when a data source API is unavailable or rate-limited? Loaders should respect rate limits, retry with backoff, and abort cleanly with a descriptive error after max retries.
- What happens when BLS unemployment categories don't sum to expected totals for a county-year? The loader should flag the discrepancy and use the raw values with a data quality warning.
- What happens when Eviction Lab data has gaps for certain years or counties? The system should record the gap as a NoDataSentinel with a descriptive reason, not silently fill with zeros.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST compute reserve army state from labor market data, decomposing the surplus population into floating (between jobs), latent (underemployed/discouraged), stagnant (chronic irregular employment), and pauperized (unable to work) categories.
- **FR-002**: System MUST compute a reserve ratio (total reserve as fraction of labor force) and derive a wage pressure coefficient that quantifies downward pressure on variable capital.
- **FR-003**: System MUST model reserve army flow dynamics: inflows from mechanization displacement, firm failures, and deskilling redundancy; outflows from expansion absorption, new sector absorption, and emigration.
- **FR-004**: System MUST record discrete dispossession events with type classification (foreclosure, eviction, tax sale, eminent domain, wage theft, incarceration seizure, pension default, gentrification displacement), value transferred, dispossessed party, and appropriating party.
- **FR-005**: System MUST compute aggregate territory-level dispossession intensity from weighted individual event types.
- **FR-006**: System MUST track value transfers between territories resulting from dispossession events, maintaining a balanced accounting (value lost = value gained + deadweight loss).
- **FR-007**: System MUST classify each territory-sector pair by exploitation mode: ABSOLUTE_DOMINANT (long hours, low productivity growth), RELATIVE_DOMINANT (standard hours, high productivity growth), or MIXED.
- **FR-008**: System MUST compute working day characteristics: average weekly hours, necessary labor hours, surplus labor hours, and labor intensity index.
- **FR-009**: System MUST classify sectors by subsumption mode: FORMAL (worker retains craft control), REAL (capital controls labor process), or HYBRID, based on skill level and automation exposure data.
- **FR-010**: System MUST compute deskilling pressure as a function of automation exposure and skill degradation, feeding into reserve army formation dynamics.
- **FR-011**: System MUST compute market concentration metrics (Herfindahl index, CR4, average establishment size) and classify sectors as COMPETITIVE, OLIGOPOLY, or MONOPOLY.
- **FR-012**: System MUST track centralization dynamics (M&A activity, private equity ownership share) separately from organic concentration.
- **FR-013**: System MUST integrate reserve army wage pressure into the tensor's variable capital (v) computation, such that higher reserve ratios produce measurably lower v.
- **FR-014**: System MUST integrate dispossession events with the class transition engine (Feature 016), triggering appropriate class position changes when dispossession occurs.
- **FR-015**: System MUST provide exploitation mode visibility modifiers to consciousness dynamics, where absolute extraction has higher visibility than relative extraction.
- **FR-016**: System MUST provide all five mechanisms' state data to the simulation engine's event bus for observation and narrative generation.
- **FR-017**: System MUST provide falsification criteria that can be tested against empirical data: (a) higher U-6 predicts lower subsequent wage growth, (b) dispossession events predict downward class mobility, (c) absolute exploitation sectors show different consciousness patterns than relative exploitation sectors, (d) formal subsumption correlates with higher organizing capacity.
- **FR-018**: System MUST ingest BLS unemployment data (U-3, U-6, PTER, discouraged workers, marginally attached) at the county level for the Detroit metro area (Wayne, Oakland, Macomb counties) covering 2005-2020, following the existing DataLoader/LoaderConfig pattern with idempotent loads and checkpoint support.
- **FR-019**: System MUST ingest Eviction Lab data (eviction filings and executions by county) for the target counties and year range, storing records in the 3NF reference database linked to FIPS codes and time periods.
- **FR-020**: System MUST ingest foreclosure rate data (CoreLogic/ATTOM or equivalent public source) at the county level, with complete coverage of the 2008-2012 crisis period for the Detroit metro area.
- **FR-021**: System MUST ingest Census ACS housing data (tenure changes, migration patterns, institutional ownership rates) at the county level for the target geographic scope and years.
- **FR-022**: System MUST ingest BLS hours and productivity data (average weekly hours by industry, output per hour, unit labor costs) at the sector level for the target counties and years, linked to NAICS codes.
- **FR-023**: All data loaders MUST implement the existing VerificationProtocol for preflight validation, reporting data availability and completeness before simulation runs.
- **FR-024**: All data loaders MUST support incremental loading via the existing checkpoint system, allowing interrupted loads to resume without re-processing already-ingested data.

### Key Entities

- **Reserve Army State**: The composition and size of the relative surplus population for a territory in a given period. Key attributes: floating reserve (workers between jobs), latent reserve (underemployed/discouraged), stagnant reserve (chronically irregular employment), pauperized layer (unable to work), total reserve ratio, wage pressure coefficient.
- **Reserve Army Dynamics**: Flow rates governing formation and absorption of the reserve army. Key attributes: mechanization displacement, firm failure displacement, deskilling redundancy (inflows); expansion absorption, new sector absorption, emigration (outflows).
- **Dispossession Event**: A discrete act of primitive accumulation transferring accumulated wealth. Key attributes: event type (8 categories), dispossessed entity, appropriating entity, asset type, value transferred, labor-time equivalent.
- **Territory Dispossession State**: Aggregate dispossession metrics for a territory. Key attributes: foreclosure rate, eviction rate, displacement rate, concentrated ownership share, absentee landlord share, composite dispossession intensity.
- **Working Day State**: Characteristics of the working day for a territory-sector. Key attributes: average weekly hours, necessary labor hours, surplus labor hours, labor intensity index, legal limit, physical limit, exploitation mode classification.
- **Sector Subsumption**: Classification of labor's subordination to capital. Key attributes: formal share, real share, average skill level, automation exposure, deskilling pressure.
- **Capital Concentration State**: Market structure metrics for a territory-sector. Key attributes: Herfindahl index, CR4 (top-4 share), average establishment size, M&A volume, private equity share, monopoly tendency classification.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Reserve army wage pressure produces a statistically significant negative correlation with subsequent wage growth when tested against historical BLS data for the Detroit metro area (Wayne, Oakland, Macomb counties, 2005-2020).
- **SC-002**: Dispossession events in Wayne County during 2008-2012 produce class position transitions (LA to Proletariat) at rates that match observed foreclosure-driven wealth loss patterns within 20% of empirical estimates.
- **SC-003**: The simulation correctly classifies at least 80% of NAICS sectors by exploitation mode when compared against BLS hours and productivity data (using 2019 pre-pandemic baseline).
- **SC-004**: Multi-tick simulations demonstrate the accumulation to mechanization to reserve army to wage suppression to higher s/v feedback loop, with exploitation rate (s/v) trending upward over 10+ ticks when mechanization is active.
- **SC-005**: All five mechanisms produce events consumable by the existing observation and narrative systems, enabling narrative generation that references reserve army, dispossession, working day, subsumption, and concentration dynamics.
- **SC-006**: Reserve army formation from mechanization displacement and reabsorption during expansion phases produces counter-cyclical employment patterns consistent with Marx's analysis of the business cycle.
- **SC-007**: Territory-level dispossession intensity for Wayne County exceeds Oakland County by at least 3x during the 2008-2012 crisis period when calibrated against Eviction Lab and CoreLogic data.

---

## Assumptions

1. **Data availability**: BLS unemployment categories (U-3, U-6, PTER, discouraged workers) are sufficient to decompose the reserve army into Marx's four categories. The mapping is: U-3 approximates floating, (U-6 minus U-3) approximates latent, part-time for economic reasons approximates stagnant. Pauperized requires supplementary Census data. Note: The existing FRED loader already ingests state-level unemployment data (`FactFredStateUnemployment`, `FactFredIndustryUnemployment`); the new BLS loader provides the finer-grained county-level decomposition needed for reserve army composition.
2. **Existing dispossession calculator**: Feature 016's `DefaultDispossessionCalculator` provides dispossession *rates* for class transitions. This feature adds discrete *events* and *value tracking* on top of that foundation rather than replacing it.
3. **Phillips curve approximation**: Wage pressure from the reserve army can be empirically calibrated using Phillips curve literature as a starting approximation, with Marx's insight that the relationship is structurally determined (not a policy tradeoff) guiding the functional form.
4. **Sector classification stability**: Subsumption mode and exploitation mode classifications change slowly relative to simulation tick frequency. They can be treated as quasi-static within a single tick and updated periodically.
5. **Gentrification as primitive accumulation**: The theoretical claim that gentrification *is* primitive accumulation operating within the imperial core is treated as an axiom of the simulation, not a hypothesis to be tested. The simulation tests the *consequences* of this claim, not the claim itself.
6. **Concentration data granularity**: Census Business Dynamics Statistics provide sufficient granularity for Herfindahl and CR4 computation at the county-sector level. Where granularity is insufficient, the system should use state-level data with appropriate uncertainty markers.

---

## Dependencies

- **Feature 016 (Class Dynamics Engine)**: Dispossession events trigger class position transitions via the existing `TransitionRates` and `ClassTransitionEngine`.
- **Feature 011 (Value Tensor)**: Reserve army wage pressure modifies variable capital (v) in `ValueTensor4x3`.
- **Feature 013 (MELT/Basket)**: Working day and subsumption affect the monetary expression of labor time and basket composition.
- **Feature 002 (Dialectical Field Topology)**: Concentration/centralization metrics may inform contradiction field intensities in future integration.
- **Existing Simulation Engine**: All five mechanisms must register as Systems or integrate with existing Systems in the simulation engine's tick pipeline.
- **Existing Data Infrastructure**: Data loaders extend the `DataLoader` ABC, `LoaderConfig`, and `VerificationProtocol` from `src/babylon/data/`. The 3NF reference database schema must accommodate new fact tables for unemployment decomposition, eviction rates, foreclosure rates, housing tenure, and productivity indices.

---

## Scope Boundaries

### In Scope

- Reserve army composition, dynamics, and wage pressure computation
- Discrete dispossession event tracking with value transfer accounting
- Working day characterization and exploitation mode classification
- Subsumption classification and deskilling pressure computation
- Capital concentration/centralization metrics and monopoly tendency classification
- Integration with tensor (v), class transition engine, consciousness dynamics, and event bus
- Detroit metro case study calibration (Wayne, Oakland, Macomb counties)
- Data loaders for P1/P2 mechanisms:
  - BLS unemployment loader (U-3, U-6, PTER, discouraged workers) — Reserve Army
  - BLS hours and productivity loader (average weekly hours, output per hour, unit labor costs) — Working Day
  - Eviction Lab loader (eviction filings and executions by county) — Dispossession
  - CoreLogic/ATTOM foreclosure loader (foreclosure rates by county) — Dispossession
  - Census housing loader (tenure changes, migration patterns, institutional ownership) — Dispossession

### Out of Scope

- Commodity fetishism modeling (deferred — requires consciousness model extensions beyond current architecture)
- Data loaders for P3 mechanisms (separate feature): O*NET skill data (Subsumption), Census Business Dynamics Statistics (Concentration), SEC M&A filings (Concentration), Pitchbook/Preqin PE ownership (Concentration)
- UI/dashboard visualization of Volume I metrics — separate feature
- Historical time-series data ingestion pipeline — separate feature
- International reserve army dynamics (cross-border labor migration at scale)
