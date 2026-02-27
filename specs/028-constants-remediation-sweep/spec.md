# Feature Specification: Constants Remediation Sweep

**Feature Branch**: `028-constants-remediation-sweep`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Execute remediations from 027 Constants Provenance Audit; trace core mechanics to federal data primitives; falsifiable against Metro Detroit test case.
**Prerequisite**: Feature 027 (Constants Provenance Audit) — completed. 7 reports, 247 constants catalogued.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Wire Pipeline-Ready Constants to Federal Data (Priority: P1)

As the Architect, I need the 12 constants identified as "pipeline-ready" in the 027 audit to be derived programmatically from the SQLite reference database at simulation initialization, so that the simulation's foundational parameters trace to QCEW, BEA, Census, FRED, and ATUS data rather than hardcoded scalars.

**Why this priority**: These 12 constants have fully implemented data adapters (MarxianHydrator, SQLiteQCEWSource, CensusLoader, FredAPIClient, ATUSDBLoader). Zero infrastructure gaps exist — only the wiring is missing. These constants flow into the highest-consumer system (ImperialRentSystem, 31 constants) and directly affect the simulation's economic core.

**Independent Test**: Can be verified by initializing the simulation engine with the Detroit FIPS codes (Wayne 26163, Oakland 26125) and asserting that the 12 previously-hardcoded constants now hold values derived from SQLite queries, not GameDefines scalar defaults.

**Acceptance Scenarios**:

1. **Given** the simulation engine initializes with Wayne County FIPS 26163, **When** `extraction_efficiency` is read, **Then** its value is computed from QCEW wage data and BEA value-added data via MarxianHydrator, not the hardcoded 0.8 default.
2. **Given** the 8 Tick Initializer class share constants (bourgeoisie=0.01, petit_b=0.09, labor_aristocracy=0.40, proletariat=0.35, lumpen=0.15, unemployment=0.05, median_wage=21.0, MELT tau=62.0), **When** simulation initializes, **Then** each is derived from Census/QCEW data for the target county.
3. **Given** `economy.shadow_wage_hourly` (currently 15.43), **When** simulation initializes, **Then** the value is loaded from BLS OES data via ATUSDBLoader.
4. **Given** `reserve_army.sigmoid_r0` (currently 0.08), **When** simulation initializes, **Then** the value is derived from FRED UNRATE series.

______________________________________________________________________

### User Story 2 — Eliminate Tier B Dead Code (Priority: P2)

As the Architect, I need all 34 Tier B constants (duplicates, deprecated fallbacks, dead code) removed from the codebase, so that the constant surface area shrinks by 14% and dependency analysis is unambiguous for future remediation phases.

**Why this priority**: Tier B removal has zero behavioral impact — these constants are either never consumed or duplicate values already in GameDefines. Removing them first eliminates noise from consumer-count analysis and unblocks accurate cascade risk assessment for US1.

**Independent Test**: After removing all 34 constants, the full test suite passes with identical outcomes. No runtime behavior changes.

**Acceptance Scenarios**:

1. **Given** the 2 FormulaConstant re-exports (LOSS_AVERSION_COEFFICIENT, EPSILON), **When** removed, **Then** all callers reference the canonical GameDefines path and tests pass.
2. **Given** 10 DynamicBalance function parameter defaults that shadow GameDefines, **When** the default parameters are removed from function signatures, **Then** callers continue to pass explicit GameDefines values and tests pass.
3. **Given** 5 EndgameDetector module-level constants already mirrored in GameDefines, **When** deleted, **Then** the class reads from GameDefines directly and tests pass.
4. **Given** 7 TopologyMonitor module constants, **When** 2 move to GameDefines (GASEOUS, CONDENSATION thresholds) and 5 become constructor parameters, **Then** tests pass.
5. **Given** 5 Metrics observer fallbacks and 5 Formula module defaults, **When** removed in favor of explicit GameDefines injection, **Then** tests pass.

______________________________________________________________________

### User Story 3 — Centralize and Sweep Tier C Calibration Constants (Priority: P3)

As the Architect, I need all 63 Tier C constants validated as tunable (with explicit upper and lower bounds in GameDefines) and the 16 currently-inline Tier C constants centralized into GameDefines, so that a systematic parameter sweep can optimize them against the Detroit baseline.

**Why this priority**: Tier C constants have no direct data source but can be calibrated via parameter optimization against observed Detroit outcomes. This is the primary mechanism for constants that cannot be data-derived. Must follow US2 (dead code removal) to avoid sweeping deprecated constants.

**Independent Test**: After centralization, running a Morris sensitivity analysis produces importance rankings for all 63 Tier C constants, and no Tier C constant is missing from the sweep search space.

**Acceptance Scenarios**:

1. **Given** 16 inline Tier C constants scattered across formula modules, **When** centralized into GameDefines with sweep bounds, **Then** each constant is accessible via the standard GameDefines path and has explicit upper/lower constraints.
2. **Given** 10 coupled constant clusters (e.g., Bourgeoisie policy: critical < low < high), **When** the sweep runs, **Then** ordering constraints are enforced and invalid combinations are rejected before simulation execution.
3. **Given** the full 63-constant search space, **When** Bayesian optimization completes, **Then** the optimized parameter set produces Detroit baseline regression results within tolerance.

______________________________________________________________________

### User Story 4 — Triage Feature-Gated and Document Design Constants (Priority: P4)

As the Architect, I need a formal triage report for all constants NOT addressed in US1-US3 (25 feature-gated Tier A, 14 Tier D engineering, 99 Tier E game design), so that each constant has a documented disposition: quarantine, proxy derivation, deletion, or explicit game-design labeling.

**Why this priority**: These constants cannot be remediated in this feature either because upstream features haven't landed (Tier A gated by features 002, 013, 021, 024) or because they are intentional design/engineering choices (Tier D/E). Documenting their disposition closes the audit loop and prevents future re-investigation.

**Independent Test**: A triage report exists for every constant in the 027 inventory. The sum of dispositions (wired + eliminated + centralized + triaged) equals 247 (total constants inventoried).

**Acceptance Scenarios**:

1. **Given** 25 Tier A constants gated by features 002, 013, 021, 024, **When** triaged, **Then** each has a documented blocking feature, required adapter, and estimated unblock condition.
2. **Given** 14 Tier D engineering constants (epsilon guards, overflow clamps, calendar values), **When** documented, **Then** each has an explicit constraint rationale in its GameDefines field description.
3. **Given** 99 Tier E game design constants, **When** documented, **Then** each has description text explicitly stating it is a game design choice, not data-derived, with brief rationale.
4. **Given** the complete triage, **When** dispositions are summed, **Then** wired (12) + eliminated (34) + centralized (63) + triaged (138) = 247.

______________________________________________________________________

### Edge Cases

- What happens when a pipeline-ready constant's data source returns no data for the target FIPS code? The system falls back to the GameDefines default value and logs a warning. The fallback value must match the current hardcoded value to maintain behavioral equivalence.
- What happens when removing a Tier B constant reveals that a caller was silently depending on the default parameter? The test suite catches this as a missing-argument error. The fix is to pass the GameDefines value explicitly at the call site.
- What happens when a coupled cluster constraint is violated during parameter sweep? The sweep runner must reject invalid parameter combinations before simulation execution, not during.
- What happens when Tier A data-derived values differ significantly from current hardcoded defaults? The regression test flags the deviation. Each deviation must be documented with the data source value, the previous hardcoded value, and a brief justification for accepting or rejecting the new value.
- How does phased execution maintain engine stability between clusters? Each cluster is committed independently. After each cluster commit, the full test suite must pass before proceeding to the next cluster.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Phased Execution)**: The remediation MUST be executed in strictly isolated clusters (Tier B elimination, then Tier A wiring by system, then Tier C centralization by subsection) to maintain engine stability. Each cluster MUST pass the full test suite before the next begins.
- **FR-002 (Data Hydration Bridge)**: Pipeline-ready constants MUST be replaced with values derived from the SQLite reference database using existing adapter infrastructure (MarxianHydrator, SQLiteQCEWSource, CensusLoader, FredAPIClient, ATUSDBLoader). No new adapters may be created.
- **FR-003 (Leftover Triage Protocol)**: For every constant lacking data provenance, the implementer MUST halt implementation and produce a triage record: [Parameter] -> [Why it lacks data] -> [Proposed disposition]. Valid dispositions: quarantine in tuning standard, derive via proxy equation, delete feature, or label as intentional game design.
- **FR-004 (Falsifiability Enforcement)**: Any newly derived equation connecting a data source to a constant MUST document what real-world observation in Wayne County (26163) or Oakland County (26125) would prove the derivation wrong.
- **FR-005 (Regression Gate)**: After each remediation cluster, the Detroit baseline regression tests MUST pass. Deliberate deviations require explicit documentation: old value, new value, data source, and theoretical justification.
- **FR-006 (No New Data Sources)**: The remediation MUST use only data sources already mapped in the 027 audit and approved in Constitution Article III.4. No new data source adapters may be introduced.
- **FR-007 (No Schema Changes)**: The SQLite reference schema MUST NOT be modified. All hydration uses existing tables and the existing Hydrator query pattern.
- **FR-008 (Constant Count Accountability)**: The total disposition count (wired + eliminated + centralized + triaged) MUST equal 247, matching the 027 inventory total. No constant may be left unaccounted.

### Key Entities

- **Constant**: A numerical value used in simulation mechanics, identified by source (GameDefines field, FormulaConstant, inline literal), tier (A-E), and consumer count. 247 total from 027 inventory.
- **Tier Classification**: 5-tier taxonomy from 027 audit — A (tensor-derivable, 37), B (eliminable, 34), C (calibration, 63), D (engineering, 14), E (game design, 99).
- **Coupled Cluster**: A group of constants with ordering or co-dependency constraints that must be remediated as a bundle (13 clusters identified in 027 audit).
- **Data Adapter**: Existing infrastructure that loads federal data from SQLite — bridges raw statistical data to simulation-ready parameter values.
- **Triage Record**: A structured disposition for each constant not directly remediated, containing: parameter path, reason for non-remediation, proposed constitutional fix.
- **Regression Baseline**: Expected simulation output values for the Detroit test case that gate each remediation cluster.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 12 pipeline-ready constants are derived from federal data at initialization — zero hardcoded scalar defaults remain for these parameters.
- **SC-002**: 34 Tier B constants are deleted from the codebase — constant surface area reduces by 14%.
- **SC-003**: All 63 Tier C constants are present in the parameter sweep search space with explicit upper and lower bounds.
- **SC-004**: 100% of the 247 inventoried constants have a documented disposition (wired, eliminated, centralized, or triaged) — no orphans.
- **SC-005**: The Detroit baseline regression test suite passes after each remediation cluster, or deviations are explicitly documented with data source evidence.
- **SC-006**: Each newly wired constant has a falsifiability statement identifying what Wayne/Oakland County observation would disprove its derivation.
- **SC-007**: Zero new data source adapters are introduced — only existing Constitution III.4 infrastructure is used.

## Assumptions

- The 027 Constants Provenance Audit inventory (247 constants) is complete and accurate. No significant undiscovered constants exist.
- The 12 "pipeline-ready" data adapters are functional and return correct values for Wayne/Oakland County FIPS codes.
- The Detroit regression baseline exists or can be generated before remediation begins.
- Existing coupled-cluster ordering constraints (identified in 027 audit) are correct and sufficient.
- GameDefines field bounds are appropriate for the calibration sweep and do not need widening.

## Dependencies

- **Feature 027** (Constants Provenance Audit): Completed. Provides the 247-constant inventory, 5-tier classification, coupled cluster analysis, data source mappings, and 5-phase remediation plan.
- **Existing data adapters**: MarxianHydrator, SQLiteQCEWSource, CensusLoader, FredAPIClient, ATUSDBLoader must be functional.
- **SQLite reference database**: Must contain current data for Wayne (26163) and Oakland (26125) counties.
- **Regression infrastructure**: Regression generation and comparison tooling must be operational.
- **Features 002, 013, 021, 024**: NOT dependencies — their absence defines the 25 feature-gated constants handled by FR-003 triage, not by direct wiring.
