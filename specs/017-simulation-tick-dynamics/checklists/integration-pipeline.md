# Integration & Pipeline Checklist: Simulation Tick Dynamics

**Purpose**: Validate that the 8-step pipeline orchestration, 6-feature dependency chain, and dual-mode architecture requirements are complete, clear, and consistent
**Created**: 2026-02-06
**Feature**: [spec.md](../spec.md)
**Depth**: Standard (PR Review)
**Audience**: Reviewer validating spec readiness before implementation

## Pipeline Step Completeness

- [ ] CHK001 - Does FR-003 enumerate all 8 pipeline steps with matching names in the acceptance scenario (US3-4)? US3 scenario 4 lists 7 steps while FR-003 lists 8 -- the "update class distribution" step (step 7) is absent from the acceptance scenario [Consistency, Spec FR-003 vs US3-4]
- [ ] CHK002 - Is the role of Step 1 ("load new economic data") defined for simulation ticks where the engine produces all values? FR-003 does not distinguish initialization-only steps from simulation-mode steps, though the Clarifications section and data-model DAG indicate Step 1 is initialization-only [Clarity, Spec FR-003]
- [ ] CHK003 - Are the inputs, outputs, and dependencies of each pipeline step explicitly defined in the spec, or only implied by the step ordering? [Completeness, Gap]
- [ ] CHK004 - Is the distinction between Step 6 (simulate class transitions) and Step 7 (update class distribution) clearly defined? What does Step 7 do that Step 6 does not? [Clarity, Spec FR-003]
- [ ] CHK005 - Are parallelization boundaries specified for within-step parallelism? The constraint mentions "independent steps at the same dependency level" but does not identify which steps qualify [Clarity, Spec Constraints]

## Dependency Chain Specification

- [ ] CHK006 - Are the specific calculator methods called per pipeline step documented in the spec (e.g., which MELTCalculator method for Step 2, which CapitalStockCalculator method for Step 3)? [Completeness, Gap]
- [ ] CHK007 - Does the spec define what happens if a required upstream calculator (Features 011-016) raises an exception during a simulation tick, as distinct from returning NoDataSentinel during initialization? [Coverage, Gap]
- [ ] CHK008 - Is the version/interface contract with each dependency feature specified or referenced? The spec references "existing Feature 013 and Feature 015 calculators" but does not name the specific protocol methods [Clarity, Spec FR-001, FR-002]
- [ ] CHK009 - Is the relationship between NationalTickParameters (Feature 017) and the existing NationalParameters (Feature 013) clearly defined? Does NationalTickParameters extend, wrap, or replace NationalParameters? [Clarity, Spec Key Entities]

## Dual-Mode Architecture Consistency

- [ ] CHK010 - Is the dual-mode distinction (initialization vs simulation) applied consistently across all FRs? FR-010, FR-014, FR-016, FR-020 explicitly scope to initialization, but FR-003 Step 1 ("load new economic data") does not [Consistency, Spec FR-003 vs FR-010]
- [ ] CHK011 - Are the precarity derivation formulas (U-6, PTER, NILF from class distribution) specified in the spec, or only referenced as "derived from class distribution and transition rates"? FR-014 describes the concept but not the formulas [Completeness, Spec FR-014]
- [ ] CHK012 - Is the transition between modes defined? How does the system know whether it is in initialization mode or simulation mode? Is this implicit (first tick vs subsequent) or explicit (constructor parameter, state flag)? [Clarity, Gap]
- [ ] CHK013 - Does the spec define how initial precarity indicators (seeded from FRED/BLS) relate to simulation-derived precarity? If initialization seeds U-6 at 8% and the first simulation tick derives U-6 at 12% from class distribution, which value is used? [Clarity, Spec FR-014]

## State Model Requirements

- [ ] CHK014 - Is the immutability requirement for SimulationTickState explicitly stated in the spec? The plan (D3) specifies frozen Pydantic models, but the spec only implies it through "forward-only transformation" language [Completeness, Spec Constraints]
- [ ] CHK015 - Are all fields of CountyEconomicState traceable to a specific pipeline step that produces them? The entity definition lists fields but does not map each to its producing step [Traceability, Spec Key Entities]
- [ ] CHK016 - Is the SmoothedCoefficients.is_initialized flag behavior defined in the spec? FR-018 says "first tick uses raw values" but does not specify how the system detects "first tick" [Clarity, Spec FR-018]
- [ ] CHK017 - Does the spec define whether the county set is fixed for an entire simulation run or can change between ticks? [Completeness, Gap]

## Formula & Threshold Specification

- [ ] CHK018 - Are crisis detection thresholds specified in the FRs or only in Assumptions? FR-015 says "based on economic indicators" without specifying thresholds; Assumptions mention 8% unemployment and 15% profit rate decline as defaults [Clarity, Spec FR-015 vs Assumptions]
- [ ] CHK019 - Is the annualization of phi_hour (imperial rent per hour) to produce Phi_aggregate (annual total) specified? FR-007 says "sum of all county-level imperial rent flows" but phi_hour is a per-hour rate, not an annual flow [Ambiguity, Spec FR-007]
- [ ] CHK020 - Are the boundaries of coefficient vs quantity classification exhaustive? FR-005 lists examples but does not claim the lists are complete. What about gamma_import, median_wage, or supply_chain_depth? [Completeness, Spec FR-005]
- [ ] CHK021 - Is the alpha-smoothing formula's behavior at alpha=1 (no smoothing) defined as a valid operating mode or just a mathematical limit? The constraint says alpha in (0, 1] but no acceptance scenario tests alpha=1 [Coverage, Spec FR-006]

## Cross-Artifact Consistency

- [ ] CHK022 - Does the spec's Constraint about integrating "with the existing System protocol" conflict with the plan's Design Decision D1 (standalone service, NOT a System)? [Conflict, Spec Constraints vs Plan D1]
- [ ] CHK023 - Are the 8 pipeline steps in FR-003 consistent with the pipeline DAG in data-model.md? The DAG shows Step 3 split into 3a (county state) and 3b (coefficient smoothing) as parallel branches, which FR-003 does not specify [Consistency, Spec FR-003 vs data-model.md]
- [ ] CHK024 - Does the spec's SC-002 expected range for class distributions (bourgeoisie 0.5-2%, LA 30-50%) align with the plan's validation expectations and Feature 016's defaults (bourgeoisie 1%, LA 40%)? [Consistency, Spec SC-002]

## Edge Case & Scenario Coverage

- [ ] CHK025 - Are requirements defined for what happens when a county's derived rates produce mathematically undefined results (e.g., division by zero when K=0 and v=0 for profit rate r = s/(K+v))? [Edge Case, Spec FR-008]
- [ ] CHK026 - Is the minimum viable county count for a simulation run specified? FR-020 says halt at zero, SC-008 says 90% success, but no FR defines the minimum for proceeding [Gap, Spec FR-020 vs SC-008]
- [ ] CHK027 - Are requirements specified for handling year-boundary edge cases in multi-tick runs (e.g., tick at year 2040 which is the upper bound of the year constraint)? [Edge Case, Spec FR-011]
- [ ] CHK028 - Is the expected behavior defined when consecutive ticks produce identical state (economic equilibrium/convergence)? [Coverage, Gap]

## Notes

- Check items off as completed: `[x]`
- Items referencing `[Gap]` indicate requirements that may need to be added to the spec
- Items referencing `[Conflict]` indicate contradictions between spec sections or between spec and plan
- Items referencing `[Ambiguity]` indicate requirements that need more precise language
- CHK022 (System protocol conflict) is the highest-priority item as it represents a direct contradiction between the spec and the implementation plan
