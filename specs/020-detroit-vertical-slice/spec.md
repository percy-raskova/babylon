# Feature Specification: Detroit Vertical Slice Integration

**Feature Branch**: `020-detroit-vertical-slice`
**Created**: 2026-02-23
**Status**: Draft
**Input**: Wire existing data layer, economics calculators, and game engine into a single pipeline producing validatable Detroit 2010-2025 time series output.

## Clarifications

### Session 2026-02-23

- Q: When a year boundary occurs but tensor data for the next year is missing, what should the system do? → A: Carry forward the most recent available year's tensor data and log a warning (Option A).

## Problem Statement

Babylon has three functional but disconnected layers:

1. **Data layer** (34k LOC): Ingests QCEW/BEA/Census data into 3NF SQLite, hydrates ValueTensor4x3 models, caches them in TensorRegistry. Works.
2. **Economics layer** (19k LOC): Computes MELT, imperial rent, class position, throughput, crisis detection via 7 standalone calculators. Works in isolation.
3. **Game engine** (12-system tick loop): Runs simulation ticks producing events. Works with hardcoded GameDefines constants.

The gap: `Simulation.from_sqlite()` already creates a TensorRegistry hydrated from QCEW/BEA data, but never wires the economics calculators into ServiceContainer. TickDynamicsSystem checks `services.melt_calculator is None` and returns early on every tick. ProductionSystem reads a flat `base_labor_power` constant instead of real tensor data. The economics layer and data layer sit unused during actual simulation runs.

This feature closes the loop: **real data -> real economics -> real game ticks -> observable output** for Detroit (Wayne + Oakland counties) 2010-2025.

## User Scenarios & Testing

### User Story 1 - Calculator Factory Wiring (Priority: P0)

As a simulation developer, I want economics calculators to be automatically instantiated and injected into ServiceContainer when I create a simulation from the database, so that the full TickDynamicsSystem pipeline executes instead of returning early.

**Why this priority**: Without this, no economics calculations run. Every other story depends on calculators being wired. This is the fundamental integration gap.

**Independent Test**: Create a simulation via `from_sqlite()` for any valid FIPS codes and year, inspect ServiceContainer fields, and verify TickDynamicsSystem executes its full 8-step pipeline on the first year-boundary tick.

**Acceptance Scenarios**:

1. **Given** a simulation created from the database for Wayne and Oakland counties (year 2022), **When** I inspect the service container's calculator fields, **Then** all 7 calculator fields are non-None (melt, basket, gamma, capital, throughput, transition, imperial_rent)
2. **Given** the same simulation, **When** TickDynamicsSystem.step() runs on the first year-boundary tick, **Then** it executes all 8 pipeline steps (does not return early at the calculator guard)
3. **Given** the same simulation after one year-boundary tick, **When** I read national parameters from the graph, **Then** tau (MELT) is a positive value derived from actual QCEW data
4. **Given** a simulation created without database access (existing path), **When** I inspect the service container, **Then** calculator fields remain None (backward compatible, no regression)

______________________________________________________________________

### User Story 2 - Production from Tensor Data (Priority: P0)

As a simulation developer, I want ProductionSystem to derive production values from the territory's hydrated ValueTensor4x3 (variable capital component) instead of a flat GameDefines constant, so that different counties produce different amounts based on their actual QCEW labor data.

**Why this priority**: Without this, all counties are economically identical regardless of real-world data. Wayne County (deindustrializing Detroit) and Oakland County (affluent suburb) would produce the same values, making the simulation meaningless for validation.

**Independent Test**: Run one tick of a two-county simulation and compare the production values assigned to each territory. They must differ because the underlying QCEW data differs.

**Acceptance Scenarios**:

1. **Given** Wayne County (26163) and Oakland County (26125) in a simulation, **When** ProductionSystem runs, **Then** their produced values differ (reflecting different QCEW wage structures)
2. **Given** Wayne County's tensor has a specific variable capital total, **When** production runs, **Then** the produced value is derivable from that variable capital (not from `base_labor_power`)
3. **Given** a county with no tensor data in the registry (missing QCEW coverage), **When** ProductionSystem runs, **Then** it falls back gracefully to `base_labor_power` from GameDefines (no crash)
4. **Given** the TensorRegistry is accessible during production, **When** a territory node has a FIPS code attribute, **Then** ProductionSystem looks up the corresponding tensor for the current simulation year

______________________________________________________________________

### User Story 3 - Multi-Year Time Series (Priority: P1)

As a simulation developer, I want to run the simulation across the 2010-2025 QCEW time series for Wayne and Oakland counties, so that I can observe class composition shifts over 15 years and validate against Census data.

**Why this priority**: Single-year snapshots cannot reveal trends. The value of the Detroit vertical slice is longitudinal: seeing deindustrialization, crisis recovery, and class restructuring unfold over time. This transforms the simulation from a static calculator into a dynamic model.

**Independent Test**: Run a 780-tick simulation (15 years x 52 weeks/year) and verify that TickDynamicsSystem performs year-boundary updates using different tensor data for each year.

**Acceptance Scenarios**:

1. **Given** a simulation created for FIPS 26163 and 26125 spanning years 2010-2024, **When** the simulation runs 780 ticks, **Then** TickDynamicsSystem executes year-boundary updates pulling fresh tensor data for each year
2. **Given** the TensorRegistry is hydrated for all requested years at simulation creation, **When** the simulation crosses a year boundary, **Then** economic calculations use that year's tensor data (not the previous year's)
3. **Given** a completed multi-year run, **When** I extract time series data, **Then** I get records of (year, fips, class_distribution, profit_rate, imperial_rent_per_hour, throughput_position) for each year-county combination
4. **Given** the time series for Wayne County, **When** I compare early vs late year class distributions, **Then** the labor aristocracy share has shifted (reflecting deindustrialization trends visible in QCEW data)

______________________________________________________________________

### User Story 4 - Validation Harness (Priority: P2)

As a simulation developer, I want a script that runs the Detroit time series and outputs a comparison table against Census/ACS ground truth, so that I can quantitatively assess where the model diverges from reality.

**Why this priority**: Without validation against external data, the simulation output is unfalsifiable. This story provides the quantitative gate that distinguishes "model works" from "model needs calibration." Depends on US1-US3 being complete.

**Independent Test**: Run the validation script and verify it produces a structured comparison table with divergence metrics.

**Acceptance Scenarios**:

1. **Given** I run the validation script for Wayne and Oakland counties, **Then** I get a table with columns: year, fips, model_LA_share, census_proxy_LA_share, divergence
2. **Given** the output table, **When** I scan the divergence column, **Then** I can identify which years and counties diverge most from Census proxies
3. **Given** a divergence metric between model and Census class distributions, **Then** I have a single number per county-year that quantifies model accuracy
4. **Given** Census/ACS data is unavailable for some years, **Then** the script clearly reports which years lack ground truth and skips them without crashing

______________________________________________________________________

### Edge Cases

- What happens when QCEW data is missing for a specific FIPS/year combination? TensorRegistry returns NoDataSentinel; all systems consuming tensor data must handle this gracefully without crashing.
- What happens when BEA GDP data is unavailable for MELT calculation? The current StubBEASource returns None, causing DepartmentMapper YAML defaults to provide fallback s/v and c/v ratios. This behavior must be preserved.
- What happens when a year boundary occurs but the next year's tensor data doesn't exist in the registry? The system MUST carry forward the most recent available year's tensor data and log a warning indicating which year's data is being reused. This ensures a gap-free time series.
- What happens when all ticks complete but one county had no data for the entire span? Time series output should include the county with sentinel/missing markers, not omit it silently.
- What happens when the database file is missing or inaccessible? Simulation creation should fail fast with a clear error message.
- What happens when the existing non-database simulation path is used? All calculator fields should remain None (backward compatibility), and the engine should run exactly as before.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a mechanism to instantiate all 7 economics calculators from a database session and TensorRegistry in a single operation
- **FR-002**: System MUST inject instantiated calculators into ServiceContainer so that all 7 calculator fields are non-None when simulation is created from the database
- **FR-003**: TickDynamicsSystem MUST execute its full 8-step pipeline (not return early) when calculators are present in ServiceContainer
- **FR-004**: ProductionSystem MUST read the territory's FIPS code and look up its ValueTensor4x3 from TensorRegistry to derive production values
- **FR-005**: ProductionSystem MUST use the variable capital (v) component of the tensor to compute production instead of a flat constant
- **FR-006**: ProductionSystem MUST fall back to `base_labor_power` from GameDefines when no tensor data exists for a territory
- **FR-007**: Simulation creation from the database MUST hydrate the TensorRegistry for ALL requested years (not just a single year)
- **FR-008**: TickDynamicsSystem MUST use fresh tensor data from the registry when crossing a year boundary
- **FR-015**: When tensor data is missing for a year boundary, the system MUST carry forward the most recent available year's tensor data and log a warning (no gaps in time series output)
- **FR-009**: System MUST provide a method to extract time series data from a completed multi-year simulation run
- **FR-010**: Time series records MUST contain: year, FIPS code, class distribution, profit rate, imperial rent per hour, and throughput position
- **FR-011**: A validation script MUST run the Detroit time series and compare model output against Census/ACS income distribution data
- **FR-012**: The validation script MUST compute a quantitative divergence metric between model and ground truth distributions
- **FR-013**: The validation script MUST clearly report missing ground truth data rather than silently skipping or crashing
- **FR-014**: The existing non-database simulation creation path MUST continue to work unchanged (backward compatibility)

### Key Entities

- **Calculator Factory**: A creation mechanism that takes a database session + TensorRegistry and produces all 7 instantiated economics calculators ready for ServiceContainer injection
- **TensorRegistry** (existing): Cache of ValueTensor4x3 models keyed by (FIPS, year), already supports multi-year hydration via `hydrate_counties(hydrator, fips_codes, years)`
- **ServiceContainer** (existing): Dependency injection container with 7 typed calculator slots, currently all None when created from database
- **Time Series Record**: A per-county, per-year snapshot containing class distribution, profit rate, imperial rent, and throughput position
- **Validation Report**: A comparison table of model predictions vs Census/ACS ground truth with divergence metrics per county-year

## Data Requirements

- **QCEW data for Wayne (26163) and Oakland (26125)**: Must already exist in marxist-data-3NF.sqlite. The existing QCEW loader ingests years 2013-2025 by default; years 2010-2012 availability must be verified during planning.
- **BEA GDP national**: Required for MELT (tau) calculation. Currently using StubBEASource which falls back to DepartmentMapper YAML defaults. Actual BEA data availability must be verified.
- **Census/ACS income distribution, 2010-2020**: Required only for US4 (validation harness). If unavailable, US4 must document exactly what data needs to be ingested.

## Scope Boundaries

**In Scope**:
- Wire existing calculator classes into ServiceContainer via a factory mechanism
- Modify simulation creation to use the factory and pass calculators
- Make ProductionSystem tensor-aware (read FIPS, look up tensor, use variable capital)
- Add multi-year hydration to simulation creation path
- Add time series extraction capability to completed simulation runs
- Create a validation script comparing model output to Census/ACS data

**Out of Scope**:
- Adding new data sources or data loaders
- Refactoring the 12-system engine ordering
- Changing the ValueTensor4x3 schema
- Building new UI or dashboard
- Adding new economics calculators
- Modifying existing calculator internals

## Dependencies

- marxist-data-3NF.sqlite must be populated with QCEW data for FIPS 26163 and 26125
- All existing economics calculator unit tests must be passing
- Existing `Simulation.from_sqlite()` must work for single-year case
- TensorRegistry.hydrate_counties() must successfully hydrate from the database

## Assumptions

- **Year range**: The QCEW loader covers years 2013-2025 by default. If years 2010-2012 are unavailable, the time series will start from 2013, reducing the span from 15 to 12 years. This is acceptable for the vertical slice.
- **BEA fallback**: StubBEASource provides None for all BEA queries, causing DepartmentMapper YAML defaults to be used for s/v and c/v ratios. This is acceptable for the vertical slice; real BEA data integration is a separate concern.
- **Calculator sub-dependencies**: Some calculators (throughput, class transitions) require sub-dependencies (SupplyChainAnalyzer, AccumulationCalculator, etc.) that may need stub or default implementations. The factory must handle this.
- **Census/ACS availability**: For US4, Census income distribution data may need manual preparation. If not available, US4 documents the requirements for future ingestion.
- **Tick-to-year mapping**: TickDynamicsSystem uses `2010 + tick // 52` to determine year. Multi-year simulations must align tick counts with the requested year range.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A simulation created from the database has all 7 ServiceContainer calculator fields populated (verified by inspection after creation)
- **SC-002**: TickDynamicsSystem executes all 8 pipeline steps on the first year-boundary tick (verified by logging or step count, not returning early)
- **SC-003**: Wayne County and Oakland County produce different production values in the same tick (verified by comparing territory attributes after one production step)
- **SC-004**: A multi-year simulation (780 ticks for 15 years, or 624 ticks for 12 years) completes without error and produces year-boundary economic updates for each year
- **SC-005**: Time series output contains at least one record per county per year for the full simulation span
- **SC-006**: Profit rates for Wayne County show variation across years (not constant), reflecting changing QCEW data
- **SC-007**: The validation harness produces a comparison table with divergence metrics for each county-year pair where both model and Census data are available
- **SC-008**: All existing unit tests continue to pass after integration changes (zero regressions)
