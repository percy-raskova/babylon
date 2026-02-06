# Integration & Pipeline Checklist: Simulation Tick Dynamics

**Purpose**: Validate that the 8-step pipeline orchestration, 6-feature dependency chain, and dual-mode architecture requirements are complete, clear, and consistent
**Created**: 2026-02-06
**Feature**: [spec.md](../spec.md)
**Depth**: Standard (PR Review)
**Audience**: Reviewer validating spec readiness before implementation
**Reviewed**: 2026-02-06

## Pipeline Step Completeness

- [ ] CHK001 - Does FR-003 enumerate all 8 pipeline steps with matching names in the acceptance scenario (US3-4)? US3 scenario 4 lists 7 steps while FR-003 lists 8 -- the "update class distribution" step (step 7) is absent from the acceptance scenario [Consistency, Spec FR-003 vs US3-4]
- [x] CHK002 - Is the role of Step 1 ("load new economic data") defined for simulation ticks where the engine produces all values? FR-003 does not distinguish initialization-only steps from simulation-mode steps, though the Clarifications section and data-model DAG indicate Step 1 is initialization-only [Clarity, Spec FR-003]. **Defined across Clarifications (line 12), Edge Cases (line 122), FR-010, and data-model DAG. Consistent and unambiguous when read together.**
- [ ] CHK003 - Are the inputs, outputs, and dependencies of each pipeline step explicitly defined in the spec, or only implied by the step ordering? [Completeness, Gap]. **Implied by step ordering and entity definitions, but no explicit I/O mapping per step exists in the spec.**
- [ ] CHK004 - Is the distinction between Step 6 (simulate class transitions) and Step 7 (update class distribution) clearly defined? What does Step 7 do that Step 6 does not? [Clarity, Spec FR-003]. **Data-model DAG labels Step 7 as "validate sum-to-one invariant" and FR-009 says validate after transitions, but the spec doesn't explicitly state that Step 6 = compute, Step 7 = validate+commit.**
- [ ] CHK005 - Are parallelization boundaries specified for within-step parallelism? The constraint mentions "independent steps at the same dependency level" but does not identify which steps qualify [Clarity, Spec Constraints]. **Only one example given ("step 3 county-level computations"). Steps 3a/3b parallelism shown in DAG but not in spec constraints.**

## Dependency Chain Specification

- [ ] CHK006 - Are the specific calculator methods called per pipeline step documented in the spec (e.g., which MELTCalculator method for Step 2, which CapitalStockCalculator method for Step 3)? [Completeness, Gap]. **Method names appear in Assumptions ("get_melt, compute_metrics, simulate_transitions") but not in FRs. FR-022 names the Protocol types but not their methods.**
- [ ] CHK007 - Does the spec define what happens if a required upstream calculator (Features 011-016) raises an exception during a simulation tick, as distinct from returning NoDataSentinel during initialization? [Coverage, Gap]. **FR-010 handles NoDataSentinel during initialization. No FR or edge case addresses runtime exceptions from calculators during simulation ticks.**
- [x] CHK008 - Is the version/interface contract with each dependency feature specified or referenced? The spec references "existing Feature 013 and Feature 015 calculators" but does not name the specific protocol methods [Clarity, Spec FR-001, FR-002]. **FR-022 explicitly names all 7 Protocol types. Dependencies section maps features to their provided types. Interface contracts are identified by type name.**
- [x] CHK009 - Is the relationship between NationalTickParameters (Feature 017) and the existing NationalParameters (Feature 013) clearly defined? Does NationalTickParameters extend, wrap, or replace NationalParameters? [Clarity, Spec Key Entities]. **Data-model explicitly states: "Extends existing NationalParameters (Feature 013) with smoothed variants and gamma_III".**

## Dual-Mode Architecture Consistency

- [x] CHK010 - Is the dual-mode distinction (initialization vs simulation) applied consistently across all FRs? FR-010, FR-014, FR-016, FR-020 explicitly scope to initialization, but FR-003 Step 1 ("load new economic data") does not [Consistency, Spec FR-003 vs FR-010]. **The dual-mode distinction is established across Clarifications, Assumptions, FR-010, FR-014, FR-016, FR-020, FR-024, and edge cases. FR-003's Step 1 is clarified by the data-model DAG as "only during initialization". Consistent overall.**
- [ ] CHK011 - Are the precarity derivation formulas (U-6, PTER, NILF from class distribution) specified in the spec, or only referenced as "derived from class distribution and transition rates"? FR-014 describes the concept but not the formulas [Completeness, Spec FR-014]. **FR-014 says "derived from class distribution and transition rates (e.g., lumpen share and precaritization rate inform U-6)". Full formulas exist only in plan D5 and research R3, not in the spec itself.**
- [x] CHK012 - Is the transition between modes defined? How does the system know whether it is in initialization mode or simulation mode? Is this implicit (first tick vs subsequent) or explicit (constructor parameter, state flag)? [Clarity, Gap]. **Architecturally separated: TickInitializer handles initialization, TickDynamicsSystem handles simulation ticks (plan D4). These are different components, not a runtime mode flag. The separation is defined in the plan and spec (FR-012 for initial state acceptance, FR-021 for System execution).**
- [ ] CHK013 - Does the spec define how initial precarity indicators (seeded from FRED/BLS) relate to simulation-derived precarity? If initialization seeds U-6 at 8% and the first simulation tick derives U-6 at 12% from class distribution, which value is used? [Clarity, Spec FR-014]. **FR-014 describes init seeding and simulation derivation as separate modes, but does not define the handoff: does the first simulation tick overwrite initialized values, blend them, or use init values as calibration targets?**

## State Model Requirements

- [ ] CHK014 - Is the immutability requirement for SimulationTickState explicitly stated in the spec? The plan (D3) specifies frozen Pydantic models, but the spec only implies it through "forward-only transformation" language [Completeness, Spec Constraints]. **Spec constraints say "pure function" (line 199) and "MUST NOT modify prior ticks" (line 198), which imply but do not explicitly require immutability/frozen models. Plan D3 is explicit about `ConfigDict(frozen=True)` but the spec is not.**
- [x] CHK015 - Are all fields of CountyEconomicState traceable to a specific pipeline step that produces them? The entity definition lists fields but does not map each to its producing step [Traceability, Spec Key Entities]. **Data-model Graph Integration section maps each Territory node attribute to its "Source Step" (Step 3a, 4, 5, 7, 8). Full traceability exists in data-model.md.**
- [x] CHK016 - Is the SmoothedCoefficients.is_initialized flag behavior defined in the spec? FR-018 says "first tick uses raw values" but does not specify how the system detects "first tick" [Clarity, Spec FR-018]. **Data-model defines is_initialized as "False until first tick completes" with update rule: "First tick: value[0] = raw[0] (no smoothing applied)". Detection is via the is_initialized flag. FR-018 + data-model together define the behavior.**
- [ ] CHK017 - Does the spec define whether the county set is fixed for an entire simulation run or can change between ticks? [Completeness, Gap]. **Assumptions say "configurable as part of the initial state" but no FR addresses county set mutability across ticks. Unclear if counties can be added/removed between ticks.**

## Formula & Threshold Specification

- [ ] CHK018 - Are crisis detection thresholds specified in the FRs or only in Assumptions? FR-015 says "based on economic indicators" without specifying thresholds; Assumptions mention 8% unemployment and 15% profit rate decline as defaults [Clarity, Spec FR-015 vs Assumptions]. **FR-015 is vague: "based on economic indicators (profit rate decline, unemployment spike)". Specific thresholds (8% unemployment, 15% profit rate decline) and their configurability are only in Assumptions (line 193) and Research R6, not in any FR.**
- [ ] CHK019 - Is the annualization of phi_hour (imperial rent per hour) to produce Phi_aggregate (annual total) specified? FR-007 says "sum of all county-level imperial rent flows" but phi_hour is a per-hour rate, not an annual flow [Ambiguity, Spec FR-007]. **FR-007 says "sum of all county-level imperial rent flows" but the stored county value is phi_hour (per-hour rate). The conversion from per-hour to annual flow (hours worked per year) is not specified.**
- [ ] CHK020 - Are the boundaries of coefficient vs quantity classification exhaustive? FR-005 lists examples but does not claim the lists are complete. What about gamma_import, median_wage, or supply_chain_depth? [Completeness, Spec FR-005]. **FR-005 lists example quantities and coefficients but uses implicit "etc." Several fields are unclassified: median_wage, supply_chain_depth, gamma_import (appears in SmoothedCoefficients but not in FR-005). Research R5 has a more complete listing.**
- [x] CHK021 - Is the alpha-smoothing formula's behavior at alpha=1 (no smoothing) defined as a valid operating mode or just a mathematical limit? The constraint says alpha in (0, 1] but no acceptance scenario tests alpha=1 [Coverage, Spec FR-006]. **Edge Cases (line 125) explicitly states: "Alpha=1 means no smoothing (coefficient tracks raw data exactly)". The constraint includes 1 in the valid range (0, 1]. Behavior is defined even though no acceptance scenario tests it.**

## Cross-Artifact Consistency

- [x] CHK022 - Does the spec's Constraint about integrating "with the existing System protocol" conflict with the plan's Design Decision D1 (standalone service, NOT a System)? [Conflict, Spec Constraints vs Plan D1] **RESOLVED**: Plan D1 rewritten to TickDynamicsSystem conforming to System protocol. Spec constraint strengthened with FR-021 through FR-024. All documents aligned.
- [ ] CHK023 - Are the 8 pipeline steps in FR-003 consistent with the pipeline DAG in data-model.md? The DAG shows Step 3 split into 3a (county state) and 3b (coefficient smoothing) as parallel branches, which FR-003 does not specify [Consistency, Spec FR-003 vs data-model.md]. **FR-003 lists "compute county-level state" as one step (Step 3). The DAG refines this into 3a (county state) and 3b (coefficient smoothing) as parallel branches feeding into Step 4. This refinement is not reflected in FR-003.**
- [x] CHK024 - Does the spec's SC-002 expected range for class distributions (bourgeoisie 0.5-2%, LA 30-50%) align with the plan's validation expectations and Feature 016's defaults (bourgeoisie 1%, LA 40%)? [Consistency, Spec SC-002]. **Feature 016 defaults (B: 1%, PB: 9%, LA: 40%, P: 35%, L: 15%) all fall within SC-002 ranges (B: 0.5-2%, PB: 5-15%, LA: 30-50%, P: 25-45%, L: 10-25%). Ranges are wide enough to accommodate multi-year drift.**

## Edge Case & Scenario Coverage

- [ ] CHK025 - Are requirements defined for what happens when a county's derived rates produce mathematically undefined results (e.g., division by zero when K=0 and v=0 for profit rate r = s/(K+v))? [Edge Case, Spec FR-008]. **US6-4 handles missing/unavailable K but not K=0 with v=0 (division by zero). DerivedRates data-model says "None if K unavailable" but doesn't address K=0.**
- [ ] CHK026 - Is the minimum viable county count for a simulation run specified? FR-020 says halt at zero, SC-008 says 90% success, but no FR defines the minimum for proceeding [Gap, Spec FR-020 vs SC-008]. **FR-020 halts at 0 counties. SC-008 measures success at 90%. Gap exists between halt condition (0) and success criterion (90%): no requirement defines behavior when 1-89% of counties initialize.**
- [ ] CHK027 - Are requirements specified for handling year-boundary edge cases in multi-tick runs (e.g., tick at year 2040 which is the upper bound of the year constraint)? [Edge Case, Spec FR-011]. **Data-model defines year constraint as ge=2007, le=2040. No edge case or FR addresses what happens when a multi-tick run reaches 2040 and attempts to produce year 2041.**
- [ ] CHK028 - Is the expected behavior defined when consecutive ticks produce identical state (economic equilibrium/convergence)? [Coverage, Gap]. **No requirement or edge case addresses economic equilibrium/convergence where class transitions net to zero change across consecutive ticks.**

## Summary

| Category | Pass | Fail | Total |
|----------|------|------|-------|
| Pipeline Step Completeness | 1 | 4 | 5 |
| Dependency Chain Specification | 2 | 2 | 4 |
| Dual-Mode Architecture Consistency | 2 | 2 | 4 |
| State Model Requirements | 2 | 2 | 4 |
| Formula & Threshold Specification | 1 | 3 | 4 |
| Cross-Artifact Consistency | 2 | 1 | 3 |
| Edge Case & Scenario Coverage | 0 | 4 | 4 |
| **Total** | **10** | **18** | **28** |

## Notes

- Check items off as completed: `[x]`
- Items referencing `[Gap]` indicate requirements that may need to be added to the spec
- Items referencing `[Conflict]` indicate contradictions between spec sections or between spec and plan
- Items referencing `[Ambiguity]` indicate requirements that need more precise language
- CHK022 (System protocol conflict) has been RESOLVED: spec strengthened with FR-021-024, plan D1/D2/D3 rewritten, research R2/R7/R8 updated, data-model and quickstart fully updated for System integration architecture
- **Highest-impact open items**: CHK001 (US3 step count mismatch), CHK007 (no error handling for calculator exceptions), CHK018 (crisis thresholds not in FRs), CHK019 (phi_hour annualization ambiguous), CHK025 (division by zero unaddressed)
