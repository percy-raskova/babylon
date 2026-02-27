# Feature Specification: Multi-Resolution Economic Tensor Substrate (Vols I-III Integration)

**Feature Branch**: `026-tri-county-economic-substrate`
**Created**: 2026-02-26
**Status**: Draft
**Depends On**: `021-capital-volume-i`, `023-capital-volume-ii`, `024-capital-volume-iii`, `025-tensor-hierarchy`, `014-throughput-position`
**Input**: User description: "Multi-Resolution Economic Tensor Substrate integrating Capital Volumes I, II, and III across a tri-county H3 spatial mesh"

## Motivation

The electoral/institutional layer is deferred per Constitution V.1 (Material Base First). Before any superstructural logic can be implemented, the unified economic logic of Capital Volumes I (Production), II (Circulation), and III (Equalization) must be fully operational across a multi-resolution spatial substrate.

The test geography extends to the Detroit tri-county area:
- **Wayne County (26163)**: Black internal colony, deindustrializing core
- **Oakland County (26125)**: White settler suburb, financialized economy
- **Macomb County (26099)**: White working-class bellwether, Department II manufacturing concentration

The spatial substrate operates at H3 resolution 7 (~5.16 km², roughly Census tract scale) for granular production/reproduction dynamics, aggregating up to resolution 6 and resolution 5 for regional realization and equalization. The overarching goal is to prove that value, mathematically conserved in the tensor hierarchy, circulates geographically and equalizes correctly across these resolutions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Spatial Substrate Generation (Priority: P1)

As a simulation developer, I need H3 resolution 7 hexes to form the base graph for Wayne, Oakland, and Macomb counties so that economic tensors have a granular spatial execution context.

**Why this priority**: Without a spatial substrate, no economic computation can be placed in geographic space. This is the foundational layer upon which all subsequent stories depend.

**Independent Test**: Can be fully tested by generating the hex mesh from county boundaries and verifying hex counts, parent mappings, and spatial continuity. Delivers a working spatial graph independent of economic logic.

**Acceptance Scenarios**:

1. **Given** TIGER/Line county boundaries for FIPS 26163 (Wayne), 26125 (Oakland), and 26099 (Macomb), **When** the spatial initializer runs, **Then** it generates a continuous mesh of resolution 7 hexes (expected ~1,500-2,500 hexes) covering the entire tri-county area.
2. **Given** a generated resolution 7 hex mesh, **When** parent resolution mappings are computed, **Then** every resolution 7 hex maps to exactly one resolution 6 parent and exactly one resolution 5 parent via H3 hierarchical indexing.
3. **Given** the generated hex mesh, **When** county assignments are computed, **Then** every resolution 7 hex is assigned to exactly one of the three counties, and no hex is orphaned or duplicated.
4. **Given** the hex mesh, **When** boundary hexes are identified, **Then** hexes whose centroid falls within a county boundary polygon are assigned to that county, with no gaps between adjacent county coverages.

______________________________________________________________________

### User Story 2 - Demographic Allocation and Tensor Hydration (Priority: P2)

As an economist, I need county-level macroeconomic data allocated to resolution 7 hexes using Census tract weights, so the base graph reflects historical spatial inequality within each county.

**Why this priority**: Raw hex geometry without economic data is inert. Allocation transforms the spatial substrate into a working economic landscape that reflects real-world inequality. This must precede any Volume I-III computation.

**Independent Test**: Can be tested by allocating known county totals to hexes and verifying that hex-level sums exactly reconstitute county totals (Conservation of Value). Delivers spatially-distributed economic data independent of simulation dynamics.

**Acceptance Scenarios**:

1. **Given** county-level QCEW wage and employment data and tract-level Census ACS demographic data, **When** the Hydrator allocates data to resolution 7 hexes, **Then** economic values are distributed proportionally based on tract demographics (population, employment, income).
2. **Given** allocated hex-level data for any single county, **When** the sum of all resolution 7 hex values within that county is computed, **Then** it equals the original county-level QCEW total within floating-point tolerance (abs(diff) < 1e-10) (Conservation of Value invariant).
3. **Given** tract-level demographic weights, **When** allocation runs for Wayne County, **Then** hexes covering high-poverty Census tracts (e.g., Detroit core) receive proportionally lower wage allocations and higher unemployment weights than suburban tract hexes.
4. **Given** a hex that spans multiple Census tracts, **When** allocation weights are computed, **Then** the hex receives a population-weighted blend of the overlapping tracts' economic data.

______________________________________________________________________

### User Story 3 - Volume I Production at Resolution 7 (Priority: P3)

As a theorist, I need surplus value generation and exploitation rates calculated at the resolution 7 hex level, so that local points of production are accurately modeled without value leakage.

**Why this priority**: Production (Volume I) is the origin of all value in the Marxian circuit. Without local surplus value extraction, Volumes II and III have nothing to circulate or equalize. Depends on hydrated hex data from Story 2.

**Independent Test**: Can be tested by running production calculations on hydrated hexes and verifying that local exploitation rates (s/v) are computed correctly, and that total value across all hexes is conserved before and after production. Delivers per-hex surplus value independent of circulation.

**Acceptance Scenarios**:

1. **Given** a hydrated resolution 7 hex with allocated Department I/II/III employment and wage data, **When** the Volume I production logic executes for that hex, **Then** it calculates the local rate of exploitation (s/v) based on the hex's economic composition.
2. **Given** all resolution 7 hexes after production execution, **When** total capital (C = c + v + s) is summed across all hexes, **Then** it equals the total capital before production plus any net value added during the tick (no value leaks outside any hex during production).
3. **Given** a hex with zero employment (e.g., parkland, water), **When** production executes, **Then** it produces zero surplus value and does not distort neighboring hex calculations.
4. **Given** Macomb County hexes with high Department II (manufacturing) concentration, **When** production executes, **Then** they exhibit higher organic composition of capital (c/v) than service-sector-dominated Wayne County core hexes.

______________________________________________________________________

### User Story 4 - Volume II Circulation via Commute Flows (Priority: P4)

As a theorist, I need variable capital (v) to circulate from the hex of production to the hex of reproduction based on empirical commute patterns, so that the consumption fund is distributed according to where workers live, not where they work.

**Why this priority**: Circulation (Volume II) redistributes wages spatially. Without this, value remains frozen at production sites and cannot drive consumption-driven reproduction dynamics. This is the largest and most complex story due to the origin-destination matrix operations across 1,600+ nodes.

**Independent Test**: Can be tested by flowing wages from production hexes to residence hexes using commute data and verifying that total variable capital (v) is perfectly conserved during transit. Delivers spatially-redistributed consumption fund independent of equalization.

**Acceptance Scenarios**:

1. **Given** surplus value extracted at a resolution 7 production hex and LODES origin-destination commute flow data, **When** the Volume II circulation logic executes, **Then** wages (v) flow from the workplace hex to the residence hexes proportionally based on commute shares.
2. **Given** all circulation flows across the tri-county area, **When** total variable capital (v) is summed before and after circulation, **Then** the totals differ by less than floating-point tolerance (abs(diff) < 1e-10) (conservation during transit).
3. **Given** a Wayne County production hex where workers predominantly reside in Macomb County, **When** circulation executes, **Then** the corresponding wage share flows from the Wayne hex to the relevant Macomb residence hexes.
4. **Given** cross-county commute flows, **When** circulation aggregates to county level, **Then** Oakland County receives net wage inflows (bedroom community pattern) while Wayne County core shows net wage outflows (workers commute out to suburbs).

______________________________________________________________________

### User Story 5 - Volume III Equalization Across Resolutions (Priority: P5)

As a theorist, I need capital to flow between hexes seeking higher profit rates, demonstrating the tendency toward equalization of the rate of profit across the spatial economy.

**Why this priority**: Equalization (Volume III) is the capstone that produces the average rate of profit. Without it, the simulation cannot demonstrate capital's spatial mobility or deindustrialization dynamics. Depends on all prior stories.

**Independent Test**: Can be tested by running equalization over multiple ticks and verifying that capital measurably migrates from low-profit hexes to high-profit hexes, and that resolution 7 values aggregate correctly to resolution 5 for metro-wide profit rate computation. Delivers observable spatial capital dynamics.

**Acceptance Scenarios**:

1. **Given** post-circulation surplus value distributed across resolution 7 hexes with varying local profit rates, **When** the Volume III equalization logic executes, **Then** capital migrates from low-profit hexes toward high-profit hexes.
2. **Given** resolution 7 hex-level profit rates, **When** aggregation computes resolution 5 metro-wide averages, **Then** the metro-wide average profit rate (r) is a properly weighted average of all constituent resolution 7 hex profit rates.
3. **Given** 260 simulation ticks (5 years), **When** equalization runs repeatedly, **Then** Wayne County's share of total tri-county capital decreases AND Oakland County's share increases (directional shift), reflecting real-world capital flight dynamics.
4. **Given** resolution 7 hex data, **When** intermediate resolution 6 aggregation is computed, **Then** resolution 6 values equal the sums of their child resolution 7 hexes within floating-point tolerance, and resolution 5 values equal the sums of their child resolution 6 hexes within floating-point tolerance (hierarchical conservation).

______________________________________________________________________

### User Story 6 - Full Tick Performance Gate (Priority: P6)

As a simulation developer, I need the complete economic tick (Volumes I through III) to execute within a strict time budget, so that the simulation can scale to the full tri-county mesh without becoming impractical.

**Why this priority**: Performance is a cross-cutting concern. If the economic pipeline is correct but too slow, it cannot be used for multi-tick scenario analysis. This story validates the entire pipeline end-to-end.

**Independent Test**: Can be tested by profiling a complete simulation tick across all resolution 7 hexes and measuring wall-clock time. Delivers a performance baseline and identifies bottlenecks.

**Acceptance Scenarios**:

1. **Given** the full tri-county resolution 7 hex mesh (~1,500-2,500 hexes) with hydrated economic data, **When** a single complete simulation tick executes (Volume I production, Volume II circulation, Volume III equalization), **Then** the tick resolves in under 5.0 seconds wall-clock time on standard hardware.
2. **Given** the performance profiling results, **When** bottlenecks are identified, **Then** the LODES origin-destination matrix multiplication (Volume II) is the dominant cost, and no single Volume exceeds 3.0 seconds individually.

______________________________________________________________________

### Edge Cases

- What happens when a resolution 7 hex has zero population and zero employment (water bodies, parks, industrial wasteland)? Expected: produces zero surplus value, assigned zero allocation weight, does not participate in commute flows.
- How does the system handle hexes at the boundary of the tri-county area that partially extend beyond county borders? Expected: assigned to county containing the hex centroid; partial-area hexes are treated as fully belonging to one county.
- What happens when LODES commute data shows flows to/from hexes outside the tri-county area (commuters to/from Ann Arbor, Toledo, etc.)? Expected: external flows are captured in a boundary flow register for conservation accounting, not modeled at individual hex resolution.
- How does circulation handle a hex that is a production site but has zero resident workers (e.g., an isolated industrial park)? Expected: all produced wages flow outward to residence hexes via commute data; no wages remain at the production hex.
- What happens when equalization produces negative capital stock at a severely depleted hex? Expected: capital stock is floored at zero; the deficit is recorded as disinvestment for accounting purposes.
- How does multi-resolution aggregation handle hexes that span resolution parent boundaries due to H3 grid alignment? Expected: H3 natively guarantees each child hex has exactly one parent at every resolution; no boundary splitting occurs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a continuous mesh of H3 resolution 7 hexes covering Wayne (26163), Oakland (26125), and Macomb (26099) counties from TIGER/Line boundary data.
- **FR-002**: System MUST map every resolution 7 hex to its resolution 6 and resolution 5 parent hexes via H3 hierarchical indexing.
- **FR-003**: System MUST assign every resolution 7 hex to exactly one county based on centroid containment within county boundary polygons.
- **FR-004**: System MUST allocate county-level QCEW wage and employment data to resolution 7 hexes using Census ACS tract-level demographic weights (population, employment, income).
- **FR-005**: System MUST enforce Conservation of Value: the sum of allocated values across all resolution 7 hexes within a county MUST equal the county-level source total within floating-point tolerance (abs(diff) < 1e-10).
- **FR-006**: System MUST compute per-hex surplus value (s), variable capital (v), and constant capital (c) at resolution 7 for Volume I production.
- **FR-007**: System MUST compute the local rate of exploitation (s/v) for each resolution 7 hex based on its allocated economic composition.
- **FR-008**: System MUST redistribute variable capital (v) from production hexes to residence hexes using LODES origin-destination commute flow data.
- **FR-009**: System MUST conserve total variable capital (v) during Volume II circulation within floating-point tolerance (abs(diff) < 1e-10; no value created or destroyed in transit).
- **FR-010**: System MUST compute local profit rates at resolution 7 and enable capital migration toward higher-profit hexes during Volume III equalization.
- **FR-011**: System MUST aggregate resolution 7 economic values to resolution 6 and resolution 5, preserving sums within floating-point tolerance (abs(diff) < 1e-10) at each level of the hierarchy (hierarchical conservation).
- **FR-012**: System MUST handle zero-population/zero-employment hexes gracefully, producing zero surplus value without distorting neighboring calculations.
- **FR-013**: System MUST handle external commute flows (to/from hexes outside the tri-county area) by accounting for them in a boundary flow register without violating conservation.
- **FR-014**: System MUST complete a full simulation tick (all three Volumes) for the entire resolution 7 hex mesh in under 5.0 seconds on standard hardware.
- **FR-015**: System MUST check conservation invariants (total capital, variable capital, hierarchical sums) at the end of each tick and log warnings if any invariant exceeds floating-point tolerance, without halting the simulation.

### Key Entities

- **H3 Hex (Resolution 7)**: The fundamental spatial unit (~5.16 km²). Each hex holds economic state (c, v, s), demographic weights, and county assignment. ~1,500-2,500 hexes cover the tri-county area.
- **County**: One of three tri-county entities (Wayne, Oakland, Macomb). Source of macroeconomic totals from QCEW. Contains a set of resolution 7 hexes.
- **Economic Tensor**: Per-hex economic state vector containing constant capital (c), variable capital (v), surplus value (s), employment, wages, and derived rates (s/v, profit rate).
- **Commute Flow**: Origin-destination pair with flow weight, derived from LODES data. Maps workplace hexes to residence hexes for wage redistribution.
- **Resolution Hierarchy**: Parent-child relationships linking resolution 7 hexes to resolution 6 and resolution 5 parents. Enables multi-scale aggregation with exact conservation.
- **Boundary Flow Register**: Accounting mechanism for commute flows crossing the tri-county boundary, ensuring conservation without modeling external geography.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The sum of total capital (C = c + v + s) across all resolution 7 hexes at the end of any tick equals the macroeconomic calculation for the entire tri-county system within floating-point tolerance (abs(diff) < 1e-10) (Conservation of Value).
- **SC-002**: Macomb County resolution 7 hexes reflect a measurably higher concentration of Department II (manufacturing) employment than Oakland County hexes, matching known industrial composition ratios from QCEW data.
- **SC-003**: Over 260 simulation ticks (5 years), Wayne County's share of total tri-county capital decreases AND Oakland County's share increases (directional shift, no minimum magnitude required), demonstrating capital flight from deindustrializing core to financialized suburbs.
- **SC-004**: A single complete simulation tick processing all resolution 7 hexes across Volumes I, II, and III resolves in under 5.0 seconds wall-clock time.
- **SC-005**: Resolution 7 hex values aggregate to resolution 6 and resolution 5 within floating-point tolerance (abs(diff) < 1e-10), verified by sum comparison at each hierarchical level.
- **SC-006**: Total variable capital (v) before and after Volume II circulation differs by less than floating-point tolerance (abs(diff) < 1e-10) (conservation during wage redistribution across commute flows).

## Scope Boundaries

### In Scope
- H3 resolution 5/6/7 hex generation for the tri-county area
- Census/QCEW/LODES demographic and economic allocation to resolution 7 hexes
- Wiring of Volume I (production), Volume II (circulation), and Volume III (equalization) logic into tensor objects on the spatial graph
- Multi-resolution aggregation (r7 to r6 to r5)
- Performance verification for the full tick pipeline

### Deferred
- Electoral mechanics, institutional nodes, governmental budgets, and political campaigns
- Geography beyond the tri-county area (state-level, national-level)
- Real-time visualization of spatial economic dynamics
- Historical time-series comparison against actual BEA/BLS data

## Clarifications

### Session 2026-02-26

- Q: What does "exactly equals" mean for Conservation of Value checks? → A: Floating-point tolerance (`abs(diff) < 1e-10`), standard scientific computing practice.
- Q: What minimum capital shift constitutes "measurably" for SC-003? → A: Directional only — Wayne County's capital share decreases AND Oakland County's share increases, no minimum magnitude required.
- Q: Should conservation violations be enforced at runtime or only in tests? → A: Runtime logging — conservation check runs each tick and logs warnings if violated, but does not halt the simulation.

## Assumptions

- TIGER/Line boundary data uses the most recent available vintage (2023 or later).
- Census ACS data uses the latest 5-year estimates available for the tri-county area.
- LODES data uses the most recent available year with workplace-residence flow tables.
- QCEW data uses the most recent complete annual dataset.
- "Standard hardware" for the 5.0-second performance target means a modern development workstation (8+ cores, 16+ GB RAM).
- County boundary polygons are pre-loaded or downloadable from Census TIGER/Line shapefiles.
- External commute flows (beyond tri-county boundary) are captured in aggregate rather than modeled at hex resolution.
- H3 hierarchical indexing natively guarantees each child hex maps to exactly one parent at any coarser resolution, eliminating boundary-splitting concerns.
