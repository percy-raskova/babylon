# Comprehensive Requirements Quality Checklist: Crisis and Devaluation Mechanics

**Purpose**: Full requirements quality audit of spec.md — testing whether the requirements are complete, clear, consistent, and measurable before proceeding to implementation planning.
**Created**: 2026-02-06
**Feature**: [spec.md](../spec.md)
**Depth**: Standard (comprehensive, all domains)
**Audience**: Author & reviewer (pre-plan gate)

## Requirement Completeness

- [x] CHK001 - Is a default value specified for `r_threshold` (the profit rate crisis trigger)? **RESOLVED**: FR-001 now specifies `r_threshold` default of 0.05 (5%) derived from WID/Piketty empirical analysis. FR-023 also lists the default.
- [x] CHK002 - Is a default value specified for the wage compression floor ratio in FR-017? **RESOLVED**: FR-023 now specifies `wage_compression_floor_ratio` default of 0.8 (80% of subsistence cost).
- [ ] CHK003 - Are the new EventType enum values enumerated for FR-022? The spec says "new event types for phase transitions, dispossession cascade milestones, and bifurcation risk threshold crossings" but does not name or count them. [Gap, Spec §FR-022]
- [x] CHK004 - Is the behavior of the bifurcation risk metric during non-crisis periods specified? **RESOLVED**: FR-011 now states "During non-crisis periods, the bifurcation risk metric is 0 (neutral)."
- [x] CHK005 - Is the combination formula for bifurcation risk specified? **RESOLVED**: FR-011 now contains the full additive combination formula: `raw_score = -w_s * solidarity_density + w_b * class_burden_ratio; dampened_score = raw_score * (1 - legitimation); bifurcation = clamp(dampened_score, -1, +1)` with configurable weights.
- [ ] CHK006 - Is the consecutive-period counter reset behavior explicitly specified when a county exits crisis (enters recovery) and later re-enters crisis? Implicitly the counter resets, but no FR states this. [Gap, Spec §FR-002]
- [ ] CHK007 - Does the CrisisState entity include a field for the profit rate time series (or rolling window) needed by the multi-period detector? FR-020 lists "profit rate time series" as a required input, but the CrisisState attributes in Key Entities do not include it. [Gap, Spec §Key Entities]
- [ ] CHK008 - Is the "contributing factors breakdown" attribute of BifurcationRiskMetric defined with specific structure (dict, list, named fields)? [Clarity, Spec §Key Entities]

## Requirement Clarity

- [ ] CHK009 - Is the hysteresis recovery period index `k` in FR-009 defined with its starting value? If k=0 at recovery start, `(1 - h^0) = 0` means zero recovery in the first period. If k=1, half recovery immediately. This materially affects behavior. [Clarity, Spec §FR-009]
- [x] CHK010 - Is "cross-class solidarity edge density" in FR-012 defined precisely? **RESOLVED**: FR-012 now defines it as "the fraction of possible SOLIDARITY edges between nodes of different ClassPosition that actually exist" with zero-edge handling.
- [x] CHK011 - Is the "class burden ratio" in FR-014 defined as rate of change or absolute level difference? **RESOLVED**: FR-014 now defines it as `|delta_LA| / max(|delta_Prol|, epsilon)` where delta is per-period share change, with epsilon default 0.001.
- [ ] CHK012 - Is wage compression in FR-016 compounding or linear? "Reducing the effective wage rate by 2% per period" could mean `wage * (1 - 0.02)^k` (compounding) or `wage * (1 - 0.02*k)` (linear). These diverge significantly over many periods. [Clarity, Spec §FR-016]
- [ ] CHK013 - Are "simulated 2008-2012 conditions" in SC-002 defined with specific input parameters (profit rate trajectory, initial class distribution)? Without concrete inputs, SC-002 is not reproducibly testable. [Clarity, Spec §SC-002]

## Requirement Consistency

- [ ] CHK014 - Do the crisis phase names in US2 acceptance scenarios align with the phase definitions in FR-003? US2 AS1 says "early crisis (crisis active for 1-4 periods)" but FR-003 defines "onset" at period N and "early" at N+1 through N+4 — if N=3, "crisis active for 1-4 periods" spans both onset and early phases. [Consistency, Spec §US2 vs §FR-003]
- [ ] CHK015 - Does SC-001 use the correct timescale unit? SC-001 says "activates within 1 tick of the Nth period" but the clarification establishes that the detector evaluates per crisis period (13 ticks), not per tick. Should this say "within 1 crisis period"? [Consistency, Spec §SC-001 vs §Clarifications]
- [x] CHK016 - Is the crisis evaluation frequency consistent between FR-001 and FR-019? **RESOLVED**: FR-019 now specifies batch-within-step design: Step 5 processes all quarterly crisis evaluations within each annual pipeline run. A-002 and C-001 updated to align.
- [ ] CHK017 - Is the relationship between US4 phase "post-crisis" (mentioned in US4 header) and FR-003 phase list (which has "normal" but no "post-crisis") consistent? US4 mentions 5 phases including "post-crisis" but FR-003 defines only NORMAL, ONSET, EARLY, DEEP, RECOVERY. [Consistency, Spec §US4 vs §FR-003]

## Acceptance Criteria Quality

- [ ] CHK018 - Can SC-008 ("no measurable performance degradation") be objectively verified? What is the baseline measurement, what constitutes "measurable", and what tool/method is used? [Measurability, Spec §SC-008]
- [ ] CHK019 - Are the acceptance scenario thresholds in US2 quantified? US2 AS1 says "precaritization rate is amplified" and "dispossession rate amplification is minimal" — are these measurable against the FR-006 multiplier table? [Measurability, Spec §US2]
- [ ] CHK020 - Is SC-004's solidarity density threshold (60%, 20%) traceable to a requirement? No FR specifies these threshold values — they appear only in success criteria. [Traceability, Spec §SC-004]

## Scenario Coverage

- [x] CHK021 - Is the scenario of a county with zero solidarity edges addressed? **RESOLVED**: FR-012 now specifies "When the county has fewer than 2 distinct ClassPosition categories present, solidarity density is 0."
- [ ] CHK022 - Is the scenario of `crisis_period_ticks` not evenly dividing the annual cycle addressed? Default 13 divides evenly (52/13=4), but if configured differently (e.g., 10), there is a tick alignment issue. Should configuration validation enforce divisibility? [Edge Case, Gap]
- [ ] CHK023 - Is the scenario of a county entering crisis for the first time (no prior CrisisState) specified? How is CrisisState initialized — all zeros, or a sentinel? [Edge Case, Gap]
- [ ] CHK024 - Is the interaction between wage compression (FR-016) and the ImperialRentSystem's wage modifications specified? Both systems modify wage rates; which takes precedence, and are they additive or sequential? [Coverage, Gap]
- [ ] CHK025 - Is the scenario where crisis deepens while bifurcation risk is near a threshold crossing addressed? Does the system emit a bifurcation threshold event, and if so, at what threshold(s)? FR-022 mentions "bifurcation risk threshold crossings" but no thresholds are defined. [Gap, Spec §FR-022]

## State Machine Completeness

- [ ] CHK026 - Are all valid phase transitions enumerated? The spec implies NORMAL->ONSET->EARLY->DEEP->RECOVERY->NORMAL, but are other transitions possible (e.g., EARLY->RECOVERY if profit rates recover before reaching DEEP)? [Completeness, Spec §FR-003]
- [ ] CHK027 - Is the phase transition from ONSET directly to RECOVERY specified? If crisis onset is detected (period N) but profit rates recover at period N+1, does the county skip EARLY and go to RECOVERY, or revert to NORMAL? [Completeness, Spec §FR-003]
- [ ] CHK028 - Is the interrupted recovery scenario (edge case #5) specified with enough precision to determine which phase the county returns to? "Crisis resumes from the current depth" — does this mean it returns to DEEP, or to the phase corresponding to total accumulated crisis duration? [Clarity, Spec §Edge Cases]

## Dependencies & Assumptions

- [x] CHK029 - Is assumption A-002 reconciled with constraint C-001? **RESOLVED**: A-002 and C-001 both updated to describe batch-within-step design. Step 5 internally iterates over quarterly boundaries within the annual pipeline run, keeping all crisis logic within the pipeline.
- [ ] CHK030 - Is the dependency on IdeologicalProfile's `agitation` field (used for legitimation index) documented in the Dependencies section? Currently only Features 012, 016, 017 are listed; the ConsciousnessSystem dependency for reading agitation is listed as "consumed by" but should also be "reads from". [Completeness, Spec §Dependencies]

## Dimensional Consistency (added 2026-02-06, post-checklist)

- [ ] CHK031 - Which profit rate formula does the crisis detector consume — flow-based `s/(c+v)` from ValueTensor4x3 or stock-based `s/(K+v)` from DerivedRateCalculator? The spec (FR-001, A-001) says "stock-based profit rate" but the DerivedRateCalculator has a dimensional inconsistency: `s` and `v` are computed in dollars while `K` is in labor-hours. Must be reconciled before implementation. [Conflict, Code §derived_rates.py vs §capital_stock.py]
- [ ] CHK032 - If the stock-based rate `s/(K+v)` is used (where `K ≈ 14.3 × c` at δ=0.07), the rate will be an order of magnitude lower than the flow-based rate. The `r_threshold` default of 0.05 (5%) was derived from Piketty data which aligns with the flow-based range (3-8%), not the stock-based range (~0.5%). If stock-based is chosen, `r_threshold` must be recalibrated. [Calibration, Spec §FR-001 vs Code §tensor.py]
- [ ] CHK033 - Does the spec need to specify that all components of the profit rate formula (s, K or c, v) must be in the same unit system (either all labor-hours or all dollars)? Currently A-001 references "stock-based profit rate" without specifying dimensional requirements. [Clarity, Spec §A-001]

## Notes

- ~~CHK016 and CHK029 both flag the same fundamental issue: the crisis evaluation frequency (quarterly) conflicts with the TickDynamicsSystem pipeline frequency (annual). This is the highest-priority item to resolve before planning.~~ **RESOLVED** via batch-within-step design in FR-019, A-002, C-001.
- ~~CHK005 (bifurcation combination formula) is the second highest priority — without it, the metric cannot be implemented or tested.~~ **RESOLVED** with full additive formula in FR-011.
- ~~CHK001 (r_threshold default) was the third priority.~~ **RESOLVED** with 0.05 (5%) default derived from WID/Piketty empirical analysis.
- Items are numbered CHK001-CHK033 sequentially for cross-referencing.
- 9 of 33 items resolved (CHK001, CHK002, CHK004, CHK005, CHK010, CHK011, CHK016, CHK021, CHK029). 24 items remain open for planning-phase resolution.
- **CHK031-CHK033 are high priority**: The dimensional mismatch in the tick pipeline profit rate formula must be resolved before r_threshold can be implemented. See `docs/concepts/piketty-profit-rate.rst` §Dimensional Analysis for the full investigation and resolution options.
