# Research: Crisis and Devaluation Mechanics (Feature 018)

**Date**: 2026-02-06
**Feature**: 018-crisis-devaluation-mechanics

## R1. Profit Rate Source for Crisis Detection

**Decision**: Use the flow-based profit rate `s/(c+v)` from `ValueTensor4x3.profit_rate` rather than the stock-based rate `s/(K+v)` from `DerivedRateCalculator`.

**Rationale**:
- The flow-based rate is dimensionally consistent (all labor-hours).
- It validates against Piketty's 3-8% empirical bounds (Piketty guardrails pass in CI).
- The `r_threshold = 0.05` (5%) was derived from WID data in this same range.
- The stock-based rate has a dimensional bug (dollars + labor-hours in denominator, GitHub #97) and produces ~0.5% values even when fixed, making the 5% threshold permanently unreachable.

**Alternatives considered**:
- Stock-based rate `s/(K+v)` from DerivedRateCalculator. Rejected: dimensional inconsistency (s,v in dollars, K in labor-hours). Even corrected, the rate is ~0.5%, requiring completely different threshold calibration.
- Dynamic per-tick flow-based rate with evolving c,v,s. Rejected as premature: the tensor provides year-to-year variation as QCEW data evolves, which is sufficient for crisis detection at quarterly evaluation cadence.

See `docs/concepts/piketty-profit-rate.rst` for full dimensional analysis and calibration epistemology.

## R2. Pipeline Integration: Profit Rate Availability

**Decision**: The new `MultiPeriodCrisisDetector` accesses `ValueTensor4x3.profit_rate` via the `TensorRegistry` in `ServiceContainer`, NOT from `DerivedRateCalculator` (Step 8).

**Rationale**: The current pipeline has a sequencing gap: Step 5 (crisis detection) runs before Step 8 (derived rate computation), so `ThresholdCrisisDetector` receives `current_profit_rate=None`. The tensor profit rate is available from hydration time (before the pipeline runs), so the new detector can access it directly without pipeline reordering.

**Implementation**:
- `ServiceContainer` already provides access to calculators. The `TensorRegistry` (or a reference to the county's tensor) must be accessible from Step 5.
- The detector queries `tensor_registry.get(fips, year)` to obtain the profit rate.
- If the tensor returns `NoDataSentinel`, the profit rate is treated as missing (FR-005: neither counts toward nor resets the consecutive-period accumulator).

**Alternatives considered**:
- Reorder pipeline steps (move Step 8 before Step 5). Rejected: violates C-001 constraint to not restructure the pipeline. Also, Step 8 computes the stock-based rate, not the flow-based rate.
- Cache previous tick's DerivedRates.profit_rate. Rejected: this uses the stock-based rate with the dimensional bug.

## R3. CrisisAmplifier Protocol Backward Compatibility

**Decision**: `PhasedCrisisAmplifier` satisfies the existing `CrisisAmplifier` protocol (`amplify(rates, crisis: bool) -> TransitionRates`) while also exposing a phase-aware `amplify_phased(rates, phase: CrisisPhase) -> TransitionRates` method. The pipeline calls `amplify_phased()` directly.

**Rationale**: C-002 requires backward compatibility. The protocol method `amplify(rates, crisis=True)` maps to DEEP phase multipliers (worst case), preserving the existing behavior for any code that uses the boolean interface.

**Implementation**:
```python
class PhasedCrisisAmplifier:
    def amplify(self, rates: TransitionRates, crisis: bool) -> TransitionRates:
        """Protocol-compatible: maps crisis=True to DEEP phase."""
        phase = CrisisPhase.DEEP if crisis else CrisisPhase.NORMAL
        return self.amplify_phased(rates, phase)

    def amplify_phased(self, rates: TransitionRates, phase: CrisisPhase) -> TransitionRates:
        """Phase-aware amplification using FR-006 multiplier table."""
        profile = self._profiles[phase]
        return TransitionRates(...)
```

**Alternatives considered**:
- Extend protocol signature to add optional `phase` parameter. Rejected: changing the protocol breaks any existing implementations or mocks.
- Create entirely new protocol `PhasedAmplifier`. Rejected: unnecessary fragmentation when the existing protocol can be satisfied with a simple mapping.

## R4. CrisisState Storage and Persistence

**Decision**: Add a `crisis_state: CrisisState` field to `CountyEconomicState` replacing the current `crisis: bool` field. `CrisisState` is a frozen Pydantic model containing phase, duration, and recovery tracking.

**Rationale**: The current `crisis: bool` is insufficient for phased crisis mechanics. `CrisisState` needs to persist across ticks to track consecutive-period counters and phase progression. Storing it in `CountyEconomicState` follows the existing pattern (all county-level state lives here) and ensures it flows through the graph bridge for tick-to-tick persistence.

**Backward Compatibility**: Code that reads `county.crisis` (boolean) must be updated to read `county.crisis_state.phase != CrisisPhase.NORMAL`. The `EconomicConditions.crisis` field remains boolean (derived from `crisis_state`).

**Constitution II.2 Consideration**: `CrisisState` contains accumulated state (crisis duration counter) that depends on temporal history, not a derived quantity that can be recomputed from current primitives. The consecutive-period counter is analogous to `SmoothedCoefficients` (also accumulated/persisted). This is not a violation of "NEVER store derived quantities."

## R5. Batch-Within-Step Design for Quarterly Evaluation

**Decision**: Step 5 internally iterates over quarterly boundaries within each annual pipeline invocation (4 evaluations per annual tick at default `crisis_period_ticks=13`).

**Rationale**: The TickDynamicsSystem pipeline runs annually (every 52 ticks). Crisis evaluation is quarterly (every 13 ticks). Rather than restructuring the pipeline to run quarterly, Step 5 batch-processes all quarterly evaluations that occurred since the last annual run.

**Implementation**:
```python
def _check_crisis_triggers(self, county_states, ...):
    quarterly_evaluations = 52 // crisis_period_ticks  # 4 at default
    for q in range(quarterly_evaluations):
        for fips, county in county_states.items():
            profit_rate = self._get_profit_rate(fips, year)
            crisis_state = self._crisis_detector.evaluate(
                profit_rate=profit_rate,
                current_state=county.crisis_state,
            )
            county_states[fips] = county.model_copy(update={"crisis_state": crisis_state})
```

**Note**: Within a single year, the tensor profit rate is constant. So 4 quarterly evaluations see the same rate. If below threshold, the counter advances by 4. If above, 4 recovery evaluations occur. This is intentional: intra-year variation would require sub-annual economic modeling beyond current scope.

## R6. BifurcationRiskMetric Persistence

**Decision**: Persist `BifurcationRiskMetric` in `CountyEconomicState` (FR-015) as a justified exception to Constitution II.2.

**Rationale**: The metric is computed at crisis evaluation time (quarterly) but consumed by downstream systems (ConsciousnessSystem, StruggleSystem) at weekly tick resolution. The inputs (solidarity density, legitimation, class burden) may change between evaluation points, so the metric cannot be recomputed from "current" primitives at consumption time -- it's a **recorded measurement**, not a derivation. Analogous to how `SmoothedCoefficients` records temporal state.

## R7. Existing Test Infrastructure

**Decision**: New tests follow existing patterns in `tests/unit/economics/tick/` and `tests/unit/economics/dynamics/`.

**Key test files to extend or parallel**:
- `test_crisis.py` (tick): ThresholdCrisisDetector tests -- replace with MultiPeriodCrisisDetector tests
- `test_crisis.py` (dynamics): DefaultCrisisAmplifier tests -- extend with PhasedCrisisAmplifier tests
- `test_system.py` (tick): TickDynamicsSystem pipeline tests -- extend Step 5/6 tests
- `test_transition_engine.py` (dynamics): transition engine tests -- verify phased amplification integration

**New test files**:
- `test_multi_period_detector.py`: MultiPeriodCrisisDetector with all US1 acceptance scenarios
- `test_phased_amplifier.py`: PhasedCrisisAmplifier with all US2 acceptance scenarios
- `test_bifurcation_risk.py`: BifurcationRiskCalculator with all US3 acceptance scenarios
- `test_crisis_lifecycle.py`: Full lifecycle integration (US4 scenarios)
- `test_wage_compression.py`: Wage compression and crisis trap (US5 scenarios)

## R8. Event Types for Crisis Phase Transitions

**Decision**: Add new `EventType` enum values for crisis-specific events (FR-022). Reuse existing `ECONOMIC_CRISIS` for crisis onset; add new types for phase transitions and bifurcation thresholds.

**New EventType values**:
- `CRISIS_PHASE_TRANSITION`: Emitted when a county transitions between crisis phases
- `DISPOSSESSION_CASCADE`: Emitted when cumulative crisis-driven class displacement exceeds milestone thresholds
- `BIFURCATION_THRESHOLD`: Emitted when bifurcation risk crosses configurable thresholds (e.g., |score| > 0.5)

**Rationale**: The existing `ECONOMIC_CRISIS` type is appropriate for onset notification. Phase transitions need distinct types because they carry different payloads (previous phase, new phase, duration) and downstream systems (Observer, Narrative) consume them differently.

## R9. Profit Rate Temporal Evolution

**Decision**: The flow-based profit rate from ValueTensor4x3 changes year-to-year as the simulation advances through QCEW data snapshots. Within a year, the rate is constant.

**Rationale**: The TensorRegistry hydrates tensors from QCEW/BEA data for specific county-years. As the simulation year advances, new tensors provide updated profit rates reflecting real economic changes. The TRPF (tendency of rate of profit to fall) manifests through this empirical time series, not through per-tick formula computation.

**Implications for crisis detection**: If a county's profit rate falls below `r_threshold` for a given year, all 4 quarterly evaluations within that year see the same below-threshold rate. The consecutive-period counter advances by 4 in one pipeline run. This means:
- N=3 (default) crisis onset can trigger within a single year
- Recovery requires the NEXT year's tensor to show profit rate above threshold
- The minimum crisis resolution is 1 year (the pipeline's temporal resolution for rate changes)

This is appropriate for the simulation's annual economic modeling granularity.
