# Feature Specification: Tensor Hierarchy

**Feature Branch**: `025-tensor-hierarchy`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "Implement multi-level tensor hierarchy from primitive ValueTensor4x3 through derived tensors using federal statistical data sources (see ai-docs/brainstorms/tensor/tensor_hierarchy.md)"

## Clarifications

### Session 2026-02-26

- Q: Should User Story 2 (Visibility Metric) reimplement or integrate the existing Feature 015 gamma module? → A: Integrate existing gamma module into tensor hierarchy (wrap, don't rewrite).
- Q: Should tensor data loaders follow a uniform acquisition pattern? → A: Protocol-based loader interface reading from the SQLite 3NF database. Data ingestion into SQLite (from APIs, files, etc.) is a separate concern handled by existing infrastructure.
- Q: What geographic resolution for BTS FAF flows, and what if needed data is missing from the database? → A: Use data at its native resolution (CFS Areas ~130 for FAF). If data required by a tensor is not yet in the database, build an ingestion loader for it as part of this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inter-Industry Flow Matrix from BEA Input-Output Tables (Priority: P1)

A simulation operator loads the BEA Input-Output coefficient matrix (~70 industries x ~70 industries) so that the engine can model inter-industry dependencies. The operator can aggregate the ~70 BEA industries down to Babylon's 4 Marxian departments (I, IIa, IIb, III) and compute total requirements via the Leontief inverse. This enables supply-chain disruption modeling and total labor embodiment calculations.

**Why this priority**: The inter-industry flow matrix is the highest value-to-effort tensor in the hierarchy. It unlocks supply chain analysis and total labor embodiment — both critical for modeling capitalist production structure. BEA publishes annual flat CSV files that are straightforward to ingest.

**Independent Test**: Can be fully tested by loading a BEA I-O table for a given year, aggregating to 4 departments, computing the Leontief inverse, and verifying output multipliers against BEA-published multiplier benchmarks.

**Acceptance Scenarios**:

1. **Given** a BEA I-O summary table CSV for year 2019, **When** the loader ingests it, **Then** the system stores a square coefficient matrix A where A[i,j] represents dollars of industry i output required per $1 of industry j output.
2. **Given** a loaded I-O matrix and a department mapping (BEA industry -> Marxian department), **When** the operator requests department-level aggregation, **Then** the system produces a 4x4 matrix with correct weighted sums.
3. **Given** an aggregated 4x4 matrix, **When** the Leontief inverse L = (I - A)^{-1} is computed, **Then** L correctly represents total (direct + indirect) requirements and element-wise values are non-negative.
4. **Given** the Leontief inverse and direct labor coefficients per industry, **When** total labor coefficients are computed, **Then** the results represent total labor (direct + indirect) per dollar of final demand.

______________________________________________________________________

### User Story 2 - Visibility Metric from ATUS and QCEW (Priority: P2)

A simulation operator exposes the existing Feature 015 gamma visibility computations (`src/babylon/economics/gamma/`) through the tensor hierarchy interface. The gamma module already computes visibility metrics (gamma_III, gamma_import, gamma_basket, Phi_III, Phi_imperial) with 101 tests. This story wraps that existing infrastructure into a VisibilityMetric tensor conforming to the hierarchy's transformation and registry patterns, and adds the shadow subsidy derivation (Level 2).

**Why this priority**: The gamma module is complete and tested. Wrapping it into the tensor hierarchy is low effort and demonstrates the integration pattern for existing computations. No reimplementation — only adapter/interface work.

**Independent Test**: Can be fully tested by providing paid hours (QCEW) and unpaid hours (ATUS) per department, computing visibility = paid / (paid + unpaid), and verifying that Department III has significantly lower visibility than Departments I/IIa/IIb.

**Acceptance Scenarios**:

1. **Given** QCEW paid hours by department and ATUS unpaid hours by department for a given year, **When** the visibility metric is computed, **Then** the result is a 4x4 diagonal matrix where each diagonal entry is paid/(paid+unpaid) for that department.
2. **Given** a visibility metric and the ValueTensor4x3, **When** the shadow subsidy is calculated, **Then** it equals Department III total value multiplied by (1 - g_33), representing uncompensated reproductive labor.
3. **Given** zero unpaid hours for a department, **When** visibility is computed, **Then** that department's visibility is 1.0 (fully visible).
4. **Given** zero total hours (paid + unpaid) for a department, **When** visibility is computed, **Then** that department's visibility defaults to 1.0 (no division by zero).

______________________________________________________________________

### User Story 3 - Geographic Flow Tensor from BTS Freight Analysis (Priority: P3)

A simulation operator loads origin-destination commodity flow data from the Bureau of Transportation Statistics Freight Analysis Framework. The system computes the imperial rent field Phi — the net value extraction by county — from the antisymmetric part of the flow matrix. Counties with Phi > 0 are net recipients (core behavior), Phi < 0 are net donors (periphery behavior).

**Why this priority**: Geographic flows provide the empirical foundation for imperial rent at the county level. However, the data is large (~10M potential entries for 3,143 x 3,143 counties) and requires sparse matrix handling, making it higher effort than the first two stories.

**Independent Test**: Can be fully tested by loading a subset of FAF commodity flow data, computing inflow/outflow per county, and verifying that the sum of all net rents across all counties approximates zero (closed-system conservation).

**Acceptance Scenarios**:

1. **Given** BTS FAF commodity flow records with origin FIPS, destination FIPS, commodity code, and value, **When** the loader ingests them, **Then** the system stores a sparse county-to-county flow matrix.
2. **Given** a loaded flow matrix F, **When** imperial rent is computed as inflow - outflow per county, **Then** net recipients (core counties) have positive values and net donors (periphery counties) have negative values.
3. **Given** a complete flow matrix, **When** the sum of all county imperial rents is computed, **Then** the result approximates zero (value conservation in a closed system).
4. **Given** the flow matrix, **When** geographic aggregation is requested (county to state), **Then** the aggregated matrix preserves total flow magnitudes.

______________________________________________________________________

### User Story 4 - Reproduction Requirements from CEX and ATUS (Priority: P4)

A simulation operator loads consumption requirements (from the Consumer Expenditure Survey) and reproductive labor requirements (from ATUS) by social class. The system computes total reproduction cost per class in labor-time units, enabling the contradiction between production output and reproduction needs to be quantified.

**Why this priority**: Refines the variable capital (V) component of the value decomposition by grounding it in actual household expenditure data. Lower priority because the existing V estimates from QCEW wages provide a reasonable approximation.

**Independent Test**: Can be fully tested by providing consumption quantities by class/department and reproductive labor hours by class, computing total reproduction cost via SNLT conversion, and verifying the result matches hand-calculated values.

**Acceptance Scenarios**:

1. **Given** CEX spending data by category and income quintile, **When** mapped to Babylon social roles and departments, **Then** the system produces consumption requirements C[class, department, use_value].
2. **Given** ATUS time-use data by activity and demographic, **When** mapped to reproductive labor categories, **Then** the system produces labor requirements L[reproduced_class, laborer_class, labor_type].
3. **Given** consumption and labor requirements for a class, **When** total reproduction cost is calculated with a given SNLT rate, **Then** the result equals consumption cost (via SNLT) plus reproductive labor hours.

______________________________________________________________________

### User Story 5 - Class Transition Matrix from PSID (Priority: P5)

A simulation operator loads class mobility data from the Panel Study of Income Dynamics to estimate transition probabilities between social positions. The system computes stationary distributions (long-run class composition) and specific metrics like lumpenization rate.

**Why this priority**: Lowest priority because PSID data is restricted (requires registration), the panel structure is complex to process, and existing class dynamics already function with model-internal transition rules.

**Independent Test**: Can be fully tested by providing a stochastic transition matrix, verifying rows sum to 1.0, computing the dominant eigenvector, and checking that the stationary distribution converges under matrix self-multiplication.

**Acceptance Scenarios**:

1. **Given** PSID income/occupation panel data across waves, **When** class transitions are estimated, **Then** the system produces a stochastic matrix P where P[c, c'] = probability of transitioning from class c to c'.
2. **Given** a transition matrix P, **When** the stationary distribution is computed, **Then** it equals the dominant eigenvector of P^T normalized to sum to 1.0.
3. **Given** a transition matrix, **When** lumpenization rate is queried, **Then** it returns P[Labor_Aristocracy, Lumpen] — the per-period probability of downward mobility.
4. **Given** a transition matrix, **When** class aggregation is applied (e.g., 6-class to 4-class), **Then** block-sum preserves stochasticity (rows still sum to 1.0).

______________________________________________________________________

### Edge Cases

- What happens when BEA I-O table has missing or zero-valued industries? System must handle gracefully without producing NaN in the Leontief inverse.
- How does the system handle a singular matrix (I - A) when computing the Leontief inverse? Must detect and report the singularity rather than producing garbage values.
- What happens when geographic flow data has counties not present in the FIPS reference? System must log warnings and exclude unknown FIPS codes without crashing.
- How does the system handle ATUS data years that don't align with QCEW data years? Must use nearest-year matching or interpolation with clear documentation of the gap.
- What happens when a class transition matrix has absorbing states (a row with 1.0 on the diagonal)? The stationary distribution calculation must handle this correctly.
- What happens when the flow matrix is entirely zero for a county? Imperial rent must be 0.0, not NaN or undefined.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load BEA Input-Output coefficient tables from the SQLite 3NF database and construct square matrices indexed by industry code and year.
- **FR-002**: System MUST aggregate I-O matrices from ~70 BEA industries to 4 Marxian departments using a configurable industry-to-department mapping.
- **FR-003**: System MUST compute the Leontief inverse L = (I - A)^{-1} from an I-O coefficient matrix and detect singular matrices.
- **FR-004**: System MUST compute total labor coefficients from the Leontief inverse and direct labor inputs.
- **FR-005**: System MUST compute a visibility metric g_uv as a diagonal 4x4 matrix from paid hours (QCEW) and unpaid hours (ATUS) per department.
- **FR-006**: System MUST compute shadow subsidy as Department III total value multiplied by (1 - g_33).
- **FR-007**: System MUST load BTS Freight Analysis Framework origin-destination commodity flows from the SQLite 3NF database and construct a sparse area-to-area flow matrix at the data's native resolution (CFS Areas, ~130 geographic units). A CFS-to-county lookup MUST be available for downstream mapping.
- **FR-008**: System MUST compute imperial rent field Phi per county as net inflow minus net outflow from the geographic flow matrix.
- **FR-009**: System MUST support geographic aggregation of flow matrices (county to state to nation) preserving total flow magnitudes.
- **FR-010**: System MUST load Consumer Expenditure Survey data from the SQLite 3NF database by category and income group and map it to Babylon social roles and departments.
- **FR-011**: System MUST load ATUS time-use data from the SQLite 3NF database and map activities to reproductive labor categories by social class.
- **FR-012**: System MUST compute total reproduction cost per class in labor-time units via SNLT conversion.
- **FR-013**: System MUST load class transition matrices from the SQLite 3NF database or accept them programmatically, and verify stochasticity (rows sum to 1.0).
- **FR-014**: System MUST compute stationary class distributions from transition matrices via eigenvector decomposition.
- **FR-015**: System MUST support class aggregation on transition matrices preserving stochasticity.
- **FR-016**: All tensors MUST satisfy defined transformation properties — geographic aggregation sums correctly, temporal aggregation sums correctly, and currency-to-labor-time scales uniformly.
- **FR-017**: System MUST validate that each tensor meets the three-part test: specified index space, defined transformation rule, verified consistency (aggregation commutes with transformation).
- **FR-018**: All new tensors MUST integrate with the existing TensorRegistry and follow the NoDataSentinel pattern for missing data.
- **FR-019**: For any data source required by a tensor that is not yet present in the SQLite 3NF database, an ingestion loader MUST be built as part of this feature to populate the database from the upstream source.

### Key Entities

- **InterIndustryFlow**: Square coefficient matrix A[i,j] representing dollars of industry i output per $1 of industry j output. Indexed by year and ~70 BEA industry codes. Aggregatable to 4 Marxian departments.
- **GeographicFlow**: Sparse area-to-area matrix F[a,b] representing annual value flow from CFS Area a to CFS Area b (~130 geographic units at native BTS FAF resolution). Indexed by year. Decomposes into symmetric (exchange) and antisymmetric (net extraction) parts. Includes CFS-to-county lookup for downstream mapping.
- **VisibilityMetric**: Diagonal 4x4 matrix g[mu,nu] representing what fraction of each department's labor registers in the monetary economy. Derived from QCEW paid hours and ATUS unpaid hours.
- **ReproductionRequirements**: Multi-indexed tensor C[class, department, use_value] for consumption and L[class, class, labor_type] for reproductive labor. Derived from CEX and ATUS data.
- **ClassTransitionMatrix**: Stochastic matrix P[c,c'] representing per-period probability of transitioning between social classes. Derived from PSID panel data.
- **LeontiefInverse**: Derived matrix L = (I-A)^{-1} representing total (direct + indirect) production requirements. Level 2 tensor computed from InterIndustryFlow.
- **ImperialRentField**: Scalar field Phi[county] representing net value extraction by geography. Level 2 tensor computed from antisymmetric part of GeographicFlow.
- **ShadowSubsidy**: Scalar quantity representing uncompensated reproductive labor value. Level 2 tensor computed from ValueTensor4x3 and VisibilityMetric.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Inter-industry flow aggregation from ~70 industries to 4 departments produces output multipliers within 5% of BEA-published multiplier benchmarks for at least 3 test years.
- **SC-002**: Visibility metric computation for Department III yields values significantly below 1.0 (empirically expected g_33 < 0.5), confirming the shadow labor formalization works correctly.
- **SC-003**: Imperial rent field sums to approximately zero across all counties (|sum| < 0.1% of total flow), validating closed-system value conservation.
- **SC-004**: Class transition matrix stationary distributions converge within 100 matrix self-multiplications, and the stationary distribution matches the dominant eigenvector to within numerical precision (< 1e-6).
- **SC-005**: All Level 1 tensors pass the commutativity test: aggregating then transforming produces results identical (within numerical tolerance) to transforming then aggregating.
- **SC-006**: Geographic flow matrix handles the full CFS Area space (~130 areas) using sparse storage efficiently for a single year's data.
- **SC-007**: Each tensor type includes at least one validation test comparing computed values against independently published federal statistical benchmarks.
- **SC-008**: All tensor loaders gracefully handle missing data years by returning NoDataSentinel objects with descriptive reason fields, rather than crashing or returning silent defaults.

## Assumptions

- BEA Input-Output "summary" level (~70 industries) is sufficient; the "detailed" level (~400 industries) is not required for initial implementation.
- BTS FAF data uses CFS Areas (~130 geographic units) as its native resolution, not individual counties. A CFS-to-county mapping is needed for integration with county-level simulation data.
- ATUS data can be mapped to the 4 Marxian departments using activity codes without requiring custom survey weighting.
- CEX data is available in public-use microdata form with income quintile stratification.
- PSID public-use files (free with registration) are sufficient; geocoded restricted versions are not required.
- The existing ValueTensor4x3 (Level 0) and TensorRegistry infrastructure remain stable and do not require modification.
- Level 3 tensors (Jacobian, Bifurcation Surface) are computed from model dynamics at runtime and do not require new data loaders; they are out of scope for this feature's data ingestion focus.
- Sparse matrix storage (e.g., compressed sparse row format) is acceptable for geographic flow data.
- Data sources not yet in the SQLite 3NF database (e.g., BEA I-O tables, BTS FAF, CEX, PSID) will require new ingestion loaders as part of this feature.
