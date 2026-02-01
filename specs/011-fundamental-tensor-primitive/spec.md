# Feature Specification: Fundamental Tensor Primitive

**Feature Branch**: `011-fundamental-tensor-primitive`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "Fundamental Tensor Primitive - ValueTensor4x3 as the foundation for all economic data, measured in labor-hours not monetary wages. The simulation and hexagons pull data from the primitive, which pulls from SQLite. Hexagons DO NOT touch the database."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulation Engine Consumes Tensor Data (Priority: P1)

The simulation engine needs to access economic data for each county/FIPS and time period. Instead of querying the database directly or using monetary values, the engine requests data from the ValueTensor4x3 primitive, which provides labor-hour measurements across the four Marxian departments (I, IIa, IIb, III) and three value components (c, v, s).

**Why this priority**: This is the foundational data flow that all other systems depend on. Without the tensor primitive serving the simulation, no economic calculations can occur.

**Independent Test**: Can be fully tested by loading tensor data for a single FIPS/year combination and verifying the simulation can read c/v/s values in labor-hours for all four departments.

**Acceptance Scenarios**:

1. **Given** the tensor primitive has loaded data from SQLite for FIPS "06037" (LA County) and year 2020, **When** the simulation engine requests economic data for that location/time, **Then** it receives a ValueTensor4x3 containing labor-hour values for all 12 cells (4 departments × 3 components).

2. **Given** the tensor primitive contains data for multiple FIPS codes, **When** the simulation requests data for a specific territory, **Then** only that territory's tensor slice is returned without database access.

3. **Given** the tensor primitive has been initialized, **When** the simulation queries for c, v, s values, **Then** all values are in labor-hours (not currency) and can be summed correctly across departments.

______________________________________________________________________

### User Story 2 - Hexagon Visualization Receives Tensor Data (Priority: P2)

The hexagon visualization layer needs to display economic data on the map. Hexagons must receive their data exclusively from the tensor primitive (or derived tensors/calculated values), never touching the database directly.

**Why this priority**: Visualization is essential for user interaction, but depends on the tensor primitive being functional first.

**Independent Test**: Can be tested by populating a tensor with known values and verifying hexagons display correct labor-hour data without any database connections.

**Acceptance Scenarios**:

1. **Given** a hexagon representing FIPS "36061" (Manhattan), **When** it requests economic data for display, **Then** it receives data from the tensor primitive, not from a database query.

2. **Given** the tensor primitive has calculated a derived value (e.g., imperial rent), **When** a hexagon needs to display that value, **Then** it reads from the derived tensor, which was computed from the primitive.

3. **Given** magic constants (SNLT conversion factor, etc.) are defined, **When** hexagons need to display converted values, **Then** they receive pre-computed values from the tensor layer, not raw database values.

______________________________________________________________________

### User Story 3 - Tensor Loads from SQLite Database (Priority: P3)

The ValueTensor4x3 primitive must be able to hydrate itself from the SQLite database containing QCEW and BEA ratio data. This is the only layer that touches the database for economic data.

**Why this priority**: Data loading is foundational but runs once at initialization; the runtime pattern (P1, P2) is more critical for correctness.

**Independent Test**: Can be tested by initializing a tensor from a test SQLite database and verifying correct data mapping.

**Acceptance Scenarios**:

1. **Given** a SQLite database with QCEW wage data and BEA ratios, **When** the tensor primitive initializes, **Then** it loads and converts monetary wages to labor-hours using the Socially Necessary Labor Time (SNLT) conversion factor.

2. **Given** the database contains data for years 2010-2025, **When** the tensor requests year 2015, **Then** it returns only that year's data slice without loading the entire dataset into memory.

3. **Given** the database is missing data for a specific FIPS/year, **When** the tensor is queried for that combination, **Then** it returns a clearly-defined "no data available" state (not zeros, which could be valid values).

______________________________________________________________________

### User Story 4 - Derived Tensors Compute from Primitive (Priority: P3)

Higher-level tensors (Imperial Rent Field, Visibility Metric, etc.) must derive their values from the primitive ValueTensor4x3, not from raw database queries.

**Why this priority**: Derived tensors depend on the primitive being correct; they extend rather than replace it.

**Independent Test**: Can be tested by computing a derived tensor from a known primitive and verifying the derivation formula.

**Acceptance Scenarios**:

1. **Given** a ValueTensor4x3 with department values, **When** the Imperial Rent Field is requested, **Then** it computes Φ = Σ(wages - value) from the primitive tensor, not from database queries.

2. **Given** the primitive tensor is updated (e.g., new year loaded), **When** derived tensors are accessed, **Then** they recompute from the updated primitive.

______________________________________________________________________

### Edge Cases

- When QCEW data exists but BEA ratios are missing for a FIPS/year: **Use nearest available year's BEA ratio** (temporal interpolation).
- SNLT varies by year: **Use year-specific SNLT values** (each year has its own conversion factor reflecting contemporary productivity).
- Hexagon requests data for FIPS code not in tensor: **Return a sentinel "no data" object** (distinct from zero values, per FR-014).
- Aggregation from county → state → nation: **Compute on-demand when requested, cache results** (lazy aggregation strategy).
- Derived tensor produces negative values: **Allow negative values in derived tensors** (they have economic meaning, e.g., negative imperial rent indicates periphery status). Primitive tensor cells must remain non-negative.
- **Year outside 2010-2025 range**: Return NoDataSentinel with reason "Year outside available data range (2010-2025)".
- **State aggregate with no loaded counties**: Return NoDataSentinel with reason "No county data loaded for state".

## Requirements *(mandatory)*

### Functional Requirements

#### Data Layer Architecture

- **FR-001**: The ValueTensor4x3 primitive MUST be the single source of truth for all economic data in the simulation.
- **FR-002**: The primitive tensor MUST store values in labor-hours, not monetary units.
- **FR-003**: The tensor layer MUST be the only component that queries the SQLite database for economic data.
- **FR-004**: Hexagon visualization components MUST NOT have direct database access for economic data. "Direct database access" is defined as: any import from `babylon.data.*` or `sqlalchemy.orm.*` or `sqlite3` modules, or direct SQLAlchemy session usage. Prohibited import paths include: `babylon.data.*`, `sqlalchemy.orm.*`, `sqlite3`.
- **FR-005**: All derived economic values (imperial rent, exploitation rate, etc.) MUST be computed from the primitive tensor, not from database queries.

#### Tensor Structure

- **FR-006**: The primitive tensor MUST have the index structure T^μ_ν[fips, year] where μ ∈ {I, IIa, IIb, III} (departments) and ν ∈ {c, v, s} (value components).
- **FR-007**: The tensor MUST support geographic indices using 5-digit FIPS codes (3,143 US counties).
- **FR-008**: The tensor MUST support temporal indices for years available in QCEW data (1975-present).
- **FR-009**: Each cell in the primitive tensor MUST represent non-negative labor-hours, with the ability to aggregate correctly across geographic and temporal dimensions.
- **FR-010**: Derived tensors MAY contain negative values when economically meaningful (e.g., negative imperial rent indicates periphery status).

#### Data Loading

- **FR-011**: The tensor MUST load from SQLite containing QCEW wage data and BEA ratios.
- **FR-012**: Monetary values from QCEW MUST be converted to labor-hours using year-specific Socially Necessary Labor Time (SNLT) conversion factors (each year has its own factor reflecting contemporary productivity).
- **FR-013**: The tensor MUST support lazy loading (load data on demand) to handle the full county × year dataset.
- **FR-014**: The tensor MUST provide a clear distinction between "no data available" and "zero value."
- **FR-015**: When BEA ratios are missing for a FIPS/year but QCEW data exists, the tensor MUST use the nearest available year's BEA ratio (temporal interpolation).

#### Transformation Properties

- **FR-016**: The tensor MUST aggregate correctly under geographic transformation (county → state → nation) using lazy computation with caching (compute on-demand, cache results).
- **FR-017**: The tensor MUST aggregate correctly under temporal transformation (quarterly → annual).
- **FR-018**: The tensor MUST support currency-to-labor conversion via SNLT scaling (for future transformation problem implementation).

#### Consumer Access

- **FR-019**: The simulation engine MUST access economic data exclusively through the tensor primitive or its derivatives.
- **FR-020**: Hexagons MUST receive data from: the primitive tensor, derived tensors, calculated values, or magic constants—never direct database access.
- **FR-021**: Magic constants MUST be defined in the tensor configuration, accessible to consumers. These include:
  - **SNLT factors**: Year-specific labor-time conversion factors (default 1.0)
  - **BEA ratio defaults**: Industry-level c/v and s/v ratios (loaded from YAML)
  - **max_delta**: Maximum years for BEA ratio temporal interpolation (default 5 years)

### Key Entities

- **ValueTensor4x3**: The fundamental tensor with shape [fips, year, department, component] where department ∈ {I, IIa, IIb, III} and component ∈ {c, v, s}. All values in labor-hours.
- **Department**: Marxian production departments—I (means of production), IIa (wage goods), IIb (luxury goods), III (reproductive labor).
- **ValueComponent**: The three components of value—c (constant capital/dead labor), v (variable capital/living labor), s (surplus value).
- **SNLT Conversion Factor**: Socially Necessary Labor Time factor for converting monetary values to labor-hours.
- **Derived Tensor**: Any tensor computed from the primitive (e.g., Imperial Rent Field, Visibility Metric).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All economic calculations in the simulation use labor-hour values from the tensor, with zero direct database queries after initialization.
- **SC-002**: Hexagon visualization layer has no import dependencies on database modules for economic data. Verified via static import analysis.
- **SC-003**: Geographic aggregation (sum of county values) equals state/national totals within 0.01% **relative** tolerance.
- **SC-004**: Temporal aggregation (sum of quarterly values) equals annual totals within 0.01% **relative** tolerance.
- **SC-005**: The tensor can load data for 100 counties × 10 years within 5 seconds **p95 latency** on standard hardware (4-core CPU, 16GB RAM, SSD).
- **SC-006**: **Peak RSS** memory footprint for loaded tensor data stays under 500MB for full US county dataset.
- **SC-007**: All formula tests pass with labor-hour inputs (no monetary unit assumptions in test assertions).
- **SC-008**: Derived tensors (imperial rent, exploitation rate) produce identical results whether computed from tensor or from equivalent manual calculations, within **1e-9 floating-point tolerance**.
- **SC-015**: When BEA ratios are missing for a FIPS/year, temporal interpolation uses nearest available year within max_delta (default 5 years) or falls back to YAML defaults. Verified via unit tests.

### Performance Requirements

- **SC-009**: `TensorRegistry.get()` method latency MUST be < 1ms p95 (cache hit, no computation).
- **SC-010**: `TensorRegistry.get_aggregate()` latency: cold cache < 100ms p95, warm cache < 1ms p95.
- **SC-011**: LRU cache eviction triggers at 500MB peak RSS; eviction events are logged at INFO level.

### Observability Requirements

- **SC-012**: Tensor hydration operations logged at INFO level with county count and duration.
- **SC-013**: Cache hits/misses logged at DEBUG level.
- **SC-014**: `NoDataSentinel.reason` format: "{context}: {specific_reason}" (e.g., "get(26163, 2022): FIPS code not in database").

## Clarifications

### Session 2026-02-01

- Q: What happens when QCEW data exists but BEA ratios are missing for a FIPS/year? → A: Use nearest available year's BEA ratio (interpolation)
- Q: How does the system handle SNLT conversion when SNLT varies by year? → A: Use year-specific SNLT values (each year has its own conversion factor)
- Q: What happens when a hexagon requests data for a FIPS code not in the tensor? → A: Return a sentinel "no data" object (distinct from zero values)
- Q: How does the system handle aggregation from county → state → nation level? → A: Compute on-demand when requested, cache results (lazy aggregation)
- Q: What happens if derived tensor computation produces invalid values (negative labor-hours)? → A: Allow negative values in derived tensors (they have economic meaning, e.g., negative imperial rent = periphery)
- Note: Until SNLT conversion is fully implemented, tensor values represent wage-proportional labor-time proxies. Derived ratios (r, e, OCC) are exact; absolute magnitudes require SNLT calibration.

## Assumptions

1. **SNLT Conversion**: The SNLT conversion factor will be provided as a configuration value, with the transformation problem (prices → labor-values) deferred to a future specification. **Until SNLT conversion is fully implemented, tensor values represent wage-proportional labor-time proxies. Derived ratios (r, e, OCC) are exact; absolute magnitudes require SNLT calibration.**
2. **BEA Ratio Availability**: BEA c/v and s/v ratios are available at the industry level and can be applied to QCEW county data.
3. **Existing Tensor Implementation**: The existing `src/babylon/economics/tensor.py` provides a starting point but may need refactoring to meet these requirements.
4. **QCEW Data Structure**: QCEW data is already loaded into SQLite with the schema documented in the data infrastructure.
5. **Department Mapping**: Industry-to-department mappings exist or can be derived from BEA input-output tables.

## Out of Scope

1. **Transformation Problem**: Converting labor-values to prices of production (future specification).
2. **Inter-Industry Flow Matrix**: BEA I-O table integration (Level 1 tensor per hierarchy doc).
3. **Geographic Flow Tensor**: BTS Freight Analysis Framework integration (Level 1 tensor).
4. **Class Transition Matrix**: PSID panel data integration (Level 1 tensor).
5. **ATUS Time Use Data**: American Time Use Survey for visibility metric (separate spec 005).
6. **GUI Implementation**: The hexagon rendering itself; this spec covers only the data flow contract.
