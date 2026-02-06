# Integration & Pipeline Checklist: Simulation Tick Dynamics

**Purpose**: Validate that the 8-step pipeline orchestration, 6-feature dependency chain, and dual-mode architecture requirements are complete, clear, and consistent
**Created**: 2026-02-06
**Feature**: [spec.md](../spec.md)
**Depth**: Standard (PR Review)
**Audience**: Reviewer validating spec readiness before implementation
**Reviewed**: 2026-02-06

## Pipeline Step Completeness

- [x] CHK001 - Does FR-003 enumerate all 8 pipeline steps with matching names in the acceptance scenario (US3-4)? **RESOLVED**: US3-4 updated to 8-step list with 3a/3b split. FR-003 rewritten with full step descriptions including 3a/3b parallel split, Step 6 = simulate_transitions, Step 7 = validate+commit. [Consistency, Spec FR-003 vs US3-4]
- [x] CHK002 - Is the role of Step 1 ("load new economic data") defined for simulation ticks where the engine produces all values? FR-003 does not distinguish initialization-only steps from simulation-mode steps, though the Clarifications section and data-model DAG indicate Step 1 is initialization-only [Clarity, Spec FR-003]. **Defined across Clarifications (line 12), Edge Cases (line 122), FR-010, and data-model DAG. Consistent and unambiguous when read together.**
- [x] CHK003 - Are the inputs, outputs, and dependencies of each pipeline step explicitly defined in the spec, or only implied by the step ordering? **RESOLVED**: Pipeline Step I/O Mapping table added after FR-003 with explicit inputs, outputs, and calculator method for each step. [Completeness, Gap]
- [x] CHK004 - Is the distinction between Step 6 (simulate class transitions) and Step 7 (update class distribution) clearly defined? **RESOLVED**: FR-003 now explicitly states Step 6 = "simulate class transitions via ClassTransitionEngine.simulate_transitions() producing updated ClassDistribution" and Step 7 = "validate sum-to-one invariant and commit updated class distribution shares". [Clarity, Spec FR-003]
- [x] CHK005 - Are parallelization boundaries specified for within-step parallelism? **RESOLVED**: Constraints section now explicitly specifies: Steps 3a and 3b MAY execute in parallel after Step 2; within Step 3a, counties MAY parallelize; all other steps (1, 2, 4, 5, 6, 7, 8) MUST execute sequentially. [Clarity, Spec Constraints]

## Dependency Chain Specification

- [x] CHK006 - Are the specific calculator methods called per pipeline step documented in the spec? **RESOLVED**: Required Calculator Protocol Methods table added after FR-006 with all 7 calculators, method names, full signatures, and return types verified against codebase. Pipeline I/O table also references calculator methods per step. [Completeness, Gap]
- [x] CHK007 - Does the spec define what happens if a required upstream calculator raises an exception during a simulation tick? **RESOLVED**: FR-025 added: calculator exceptions during simulation ticks halt the pipeline with enhanced context (step number, calculator name, FIPS). Never silently convert to NoDataSentinel during simulation. [Coverage, Gap]
- [x] CHK008 - Is the version/interface contract with each dependency feature specified or referenced? The spec references "existing Feature 013 and Feature 015 calculators" but does not name the specific protocol methods [Clarity, Spec FR-001, FR-002]. **FR-022 explicitly names all 7 Protocol types. Dependencies section maps features to their provided types. Interface contracts are identified by type name.**
- [x] CHK009 - Is the relationship between NationalTickParameters (Feature 017) and the existing NationalParameters (Feature 013) clearly defined? Does NationalTickParameters extend, wrap, or replace NationalParameters? [Clarity, Spec Key Entities]. **Data-model explicitly states: "Extends existing NationalParameters (Feature 013) with smoothed variants and gamma_III".**

## Dual-Mode Architecture Consistency

- [x] CHK010 - Is the dual-mode distinction (initialization vs simulation) applied consistently across all FRs? FR-010, FR-014, FR-016, FR-020 explicitly scope to initialization, but FR-003 Step 1 ("load new economic data") does not [Consistency, Spec FR-003 vs FR-010]. **The dual-mode distinction is established across Clarifications, Assumptions, FR-010, FR-014, FR-016, FR-020, FR-024, and edge cases. FR-003's Step 1 is clarified by the data-model DAG as "only during initialization". Consistent overall.**
- [x] CHK011 - Are the precarity derivation formulas (U-6, PTER, NILF from class distribution) specified in the spec? **RESOLVED**: FR-014 now includes explicit formulas: U-6 ≈ lumpen_share + precaritization_rate x proletariat_share, PTER ≈ precaritization_rate x proletariat_share x pter_fraction (default 0.4), NILF ≈ lumpen_share x nilf_fraction (default 0.6). Coefficients are configurable and traceable to BLS. [Completeness, Spec FR-014]
- [x] CHK012 - Is the transition between modes defined? How does the system know whether it is in initialization mode or simulation mode? Is this implicit (first tick vs subsequent) or explicit (constructor parameter, state flag)? [Clarity, Gap]. **Architecturally separated: TickInitializer handles initialization, TickDynamicsSystem handles simulation ticks (plan D4). These are different components, not a runtime mode flag. The separation is defined in the plan and spec (FR-012 for initial state acceptance, FR-021 for System execution).**
- [x] CHK013 - Does the spec define how initial precarity indicators relate to simulation-derived precarity? **RESOLVED**: FR-014 now includes explicit handoff rule: "The first simulation tick overwrites initialized FRED/BLS precarity values with derived values (no blending); from that point forward, precarity is entirely endogenous." Plan D6 documents the rationale. [Clarity, Spec FR-014]

## State Model Requirements

- [x] CHK014 - Is the immutability requirement for SimulationTickState explicitly stated in the spec? **RESOLVED**: Constraints section now explicitly states: "SimulationTickState MUST be immutable (frozen Pydantic model with ConfigDict(frozen=True)). All state updates MUST produce new instances via model_copy(update={...}); in-place mutation is prohibited." [Completeness, Spec Constraints]
- [x] CHK015 - Are all fields of CountyEconomicState traceable to a specific pipeline step that produces them? The entity definition lists fields but does not map each to its producing step [Traceability, Spec Key Entities]. **Data-model Graph Integration section maps each Territory node attribute to its "Source Step" (Step 3a, 4, 5, 7, 8). Full traceability exists in data-model.md.**
- [x] CHK016 - Is the SmoothedCoefficients.is_initialized flag behavior defined in the spec? FR-018 says "first tick uses raw values" but does not specify how the system detects "first tick" [Clarity, Spec FR-018]. **Data-model defines is_initialized as "False until first tick completes" with update rule: "First tick: value[0] = raw[0] (no smoothing applied)". Detection is via the is_initialized flag. FR-018 + data-model together define the behavior.**
- [x] CHK017 - Does the spec define whether the county set is fixed for an entire simulation run or can change between ticks? **RESOLVED**: FR-026 added: county set fixed for duration of simulation run, defined at initialization, immutable between ticks. [Completeness, Gap]

## Formula & Threshold Specification

- [x] CHK018 - Are crisis detection thresholds specified in the FRs or only in Assumptions? **RESOLVED**: FR-015 now explicitly specifies: unemployment_rate > unemployment_threshold (default 0.08/8%), YoY profit rate decline > profit_rate_decline_threshold (default 0.15/15%). Both configurable. Assumptions updated to reference FR-015. [Clarity, Spec FR-015]
- [x] CHK019 - Is the annualization of phi_hour to produce Phi_aggregate specified? **RESOLVED**: FR-007 now includes explicit formula: Phi_aggregate = sum over all counties of (phi_hour x county_employment x 2080), where 2080 = 52 weeks x 40 hours/week. [Ambiguity, Spec FR-007]
- [x] CHK020 - Are the boundaries of coefficient vs quantity classification exhaustive? **RESOLVED**: FR-005 now provides exhaustive classification. Quantities: T, K, unemployment_rate, u6_rate, pter_rate, nilf_rate, median_wage, employment, foreclosure_rate, bankruptcy_rate, eviction_rate, supply_chain_depth. Coefficients: gamma_basket, gamma_III, gamma_import. Classification explicitly declared exhaustive. [Completeness, Spec FR-005]
- [x] CHK021 - Is the alpha-smoothing formula's behavior at alpha=1 (no smoothing) defined as a valid operating mode or just a mathematical limit? The constraint says alpha in (0, 1] but no acceptance scenario tests alpha=1 [Coverage, Spec FR-006]. **Edge Cases (line 125) explicitly states: "Alpha=1 means no smoothing (coefficient tracks raw data exactly)". The constraint includes 1 in the valid range (0, 1]. Behavior is defined even though no acceptance scenario tests it.**

## Cross-Artifact Consistency

- [x] CHK022 - Does the spec's Constraint about integrating "with the existing System protocol" conflict with the plan's Design Decision D1 (standalone service, NOT a System)? [Conflict, Spec Constraints vs Plan D1] **RESOLVED**: Plan D1 rewritten to TickDynamicsSystem conforming to System protocol. Spec constraint strengthened with FR-021 through FR-024. All documents aligned.
- [x] CHK023 - Are the 8 pipeline steps in FR-003 consistent with the pipeline DAG in data-model.md? **RESOLVED**: FR-003 now explicitly specifies the 3a/3b parallel split matching the data-model DAG. US3-4 acceptance scenario also updated to match. All three locations (FR-003, US3-4, DAG) are now consistent. [Consistency, Spec FR-003 vs data-model.md]
- [x] CHK024 - Does the spec's SC-002 expected range for class distributions (bourgeoisie 0.5-2%, LA 30-50%) align with the plan's validation expectations and Feature 016's defaults (bourgeoisie 1%, LA 40%)? [Consistency, Spec SC-002]. **Feature 016 defaults (B: 1%, PB: 9%, LA: 40%, P: 35%, L: 15%) all fall within SC-002 ranges (B: 0.5-2%, PB: 5-15%, LA: 30-50%, P: 25-45%, L: 10-25%). Ranges are wide enough to accommodate multi-year drift.**

## Edge Case & Scenario Coverage

- [x] CHK025 - Are requirements defined for division by zero in derived rates? **RESOLVED**: New edge case added to spec: r = s/(K+v) if K=0 and v=0 → None; OCC = c/v and e = s/v if v=0 → None. DerivedRates uses Optional[float]; None = mathematically undefined (distinct from NoDataSentinel). Data-model.md DerivedRates table and handling note also updated. [Edge Case, Spec FR-008]
- [x] CHK026 - Is the minimum viable county count for a simulation run specified? **RESOLVED**: FR-027 added: 0% = halt with diagnostic; 1-89% = proceed with warning listing failures; >=90% = proceed normally. All thresholds relative to configured county set size. [Gap, Spec FR-020 vs SC-008]
- [x] CHK027 - Are requirements specified for year-boundary edge cases in multi-tick runs? **RESOLVED**: FR-028 added: when next tick would exceed year 2040, halt and return final valid state with diagnostic. Expected termination, not error. [Edge Case, Spec FR-011]
- [x] CHK028 - Is the expected behavior defined for economic equilibrium/convergence? **RESOLVED**: FR-029 added: near-identical consecutive states (all share changes < 0.001) continue normally. Equilibrium is an observable outcome, not an error or halt trigger. TickSummary SHOULD note convergence for analysis. [Coverage, Gap]

## Summary

| Category | Pass | Fail | Total |
|----------|------|------|-------|
| Pipeline Step Completeness | 5 | 0 | 5 |
| Dependency Chain Specification | 4 | 0 | 4 |
| Dual-Mode Architecture Consistency | 4 | 0 | 4 |
| State Model Requirements | 4 | 0 | 4 |
| Formula & Threshold Specification | 4 | 0 | 4 |
| Cross-Artifact Consistency | 3 | 0 | 3 |
| Edge Case & Scenario Coverage | 4 | 0 | 4 |
| **Total** | **28** | **0** | **28** |

## Notes

- Check items off as completed: `[x]`
- Items referencing `[Gap]` indicate requirements that may need to be added to the spec
- Items referencing `[Conflict]` indicate contradictions between spec sections or between spec and plan
- Items referencing `[Ambiguity]` indicate requirements that need more precise language
- CHK022 (System protocol conflict) was RESOLVED in prior session: spec strengthened with FR-021-024, plan D1/D2/D3 rewritten
- **All 28 items now passing.** The 18 previously failing items were resolved by: updating US3-4 and FR-003 with 3a/3b split (CHK001/004/023), adding I/O mapping table (CHK003), explicit parallelization boundaries (CHK005), calculator method signatures (CHK006), FR-025 through FR-029 for gap coverage (CHK007/017/026/027/028), precarity formulas and handoff rule in FR-014 (CHK011/013), immutability constraint (CHK014), crisis thresholds in FR-015 (CHK018), annualization formula in FR-007 (CHK019), exhaustive quantity/coefficient classification in FR-005 (CHK020), and division-by-zero edge case (CHK025)
