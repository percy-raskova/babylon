# Feature Specification: Crisis and Devaluation Mechanics

**Feature Branch**: `018-crisis-devaluation-mechanics`
**Created**: 2026-02-06
**Status**: Draft
**Input**: User description: "Create a specification for Crisis and Devaluation Mechanics. TRPF creates pressure toward crisis as profit rates decline. Crisis triggers accelerated class transitions (dispossession, precaritization). This is where the George Jackson bifurcation becomes relevant."

## Clarifications

### Session 2026-02-06

- Q: Should unemployment remain as a crisis trigger alongside profit rate, or is profit rate the sole trigger? → A: Profit rate only. Unemployment is a lagging indicator — a downstream symptom of crisis (manifesting via the dispossession cascade) rather than a cause. The existing unemployment-based trigger in ThresholdCrisisDetector is removed; crisis detection is driven purely by TRPF dynamics.
- Q: How is the legitimation index derived for bifurcation risk? → A: Inverse of aggregate agitation: `legitimation = 1 - mean(agitation)` across county nodes. Uses the existing `agitation` field from IdeologicalProfile. As material conditions worsen, agitation rises, legitimation drops, and bifurcation unlocks.
- Q: How long does the recovery phase last before returning to normal? → A: Proportional to crisis duration with a cap: `recovery_duration = min(crisis_duration, R_cap)` where R_cap is configurable (default: 8 periods). Longer crises leave deeper structural scars requiring proportionally longer recovery.
- Q: What timescale do crisis "periods" operate on? → A: Configurable as a multiple of ticks. Default: quarterly (13 ticks; 52 weeks / 4 = 13, and 13 is prime — its indivisibility prevents aliasing with other periodic cycles, producing more realistic desynchronization). The crisis evaluation interval (`crisis_period_ticks`, default 13) defines how often the detector evaluates profit rates and advances phase counters. All period-based parameters (N consecutive periods, M recovery periods, R_cap, phase durations) are measured in these crisis periods, not raw ticks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crisis Detection from Declining Profit Rates (Priority: P1)

As a simulation researcher, I need the system to detect when a capitalist economy enters crisis by monitoring the rate of profit over consecutive periods, so that crisis-driven dynamics (accelerated dispossession, wage compression, political bifurcation) activate at historically appropriate moments rather than arbitrarily.

The existing `ThresholdCrisisDetector` checks single-period unemployment and profit decline. This feature replaces that with a multi-period detector that tracks the *tendency* of the rate of profit to fall across N consecutive periods, matching the Marxist theoretical foundation where crisis emerges from sustained structural decline rather than single-period shocks.

**Why this priority**: Crisis detection is the foundational trigger for all downstream mechanics. Without accurate detection, the dispossession cascade and bifurcation risk assessment have no activation signal. This is the MVP slice that enables the entire feature.

**Independent Test**: Can be fully tested by feeding a synthetic profit rate time series into the detector and verifying that crisis onset, duration, and resolution are correctly identified. Delivers value by replacing the existing single-period detector with a theoretically grounded multi-period mechanism.

**Acceptance Scenarios**:

1. **Given** a county with profit rates `[0.12, 0.11, 0.10, 0.09, 0.08]` over 5 consecutive periods and `r_threshold = 0.10` and `N = 3`, **When** the crisis detector evaluates period 5, **Then** crisis is detected because `r[t] < r_threshold` for 3 consecutive periods (periods 3, 4, 5).
2. **Given** a county with profit rates `[0.12, 0.09, 0.11, 0.09, 0.08]` (non-consecutive dips below threshold), **When** the crisis detector evaluates period 5, **Then** crisis is NOT detected because the consecutive-period requirement resets when `r[t]` rises above `r_threshold` at period 3.
3. **Given** a county currently in crisis (crisis active for 6 periods), **When** profit rates recover above `r_threshold` for M consecutive periods (recovery window), **Then** crisis status transitions to "recovery" phase with hysteresis effects (dampened transition rates, not immediate return to normal).
4. **Given** a county where profit rate data is unavailable (None) for some periods, **When** the crisis detector evaluates, **Then** unavailable periods do not count toward the consecutive-period accumulator but do not reset it either.

______________________________________________________________________

### User Story 2 - Dispossession Cascade During Crisis (Priority: P1)

As a simulation researcher, I need crisis periods to trigger accelerated downward class transitions that model the real-world dispossession cascade (foreclosures driving labor aristocracy into proletariat, layoffs driving proletariat into lumpenproletariat), so that the simulation reproduces observed class composition shifts during economic crises like 2008-2012.

The existing `DefaultCrisisAmplifier` applies flat multipliers (2.5x dispossession, 0.3x accumulation). This feature extends it to model phased crisis effects: early crisis primarily increases precaritization (layoffs), deep crisis additionally increases dispossession (foreclosures), and recovery exhibits hysteresis (class composition does not fully restore).

**Why this priority**: Equal to P1 because the dispossession cascade is the primary observable effect of crisis. Without it, crisis detection has no downstream impact on class dynamics. This story and US1 together form the minimum viable crisis mechanic.

**Independent Test**: Can be tested by simulating class transitions under crisis conditions at different crisis depths (early, deep, recovery) and verifying that transition rate amplification follows the phased model. Delivers value by producing historically plausible class composition trajectories during crisis periods.

**Acceptance Scenarios**:

1. **Given** a county entering early crisis (crisis active for 1-4 periods) with initial class distribution `{LA: 0.35, Prol: 0.45, Lumpen: 0.15}`, **When** class transitions are computed, **Then** precaritization rate is amplified (Proletariat to Lumpenproletariat increases) while dispossession rate amplification is minimal (LA share remains relatively stable).
2. **Given** a county in deep crisis (crisis active for 5+ periods), **When** class transitions are computed, **Then** both dispossession (LA to Proletariat) AND precaritization (Proletariat to Lumpenproletariat) rates are amplified, producing a visible decline in LA share and increase in Lumpenproletariat share.
3. **Given** a county transitioning from crisis to recovery (profit rates above threshold for M consecutive periods), **When** class transitions are computed, **Then** upward transition rates (accumulation, stabilization) recover slowly with a hysteresis coefficient, meaning class composition does not return to pre-crisis levels within the same number of periods it took to reach crisis composition.
4. **Given** a county in deep crisis where wage compression has reduced the accumulation rate to near zero, **When** class transitions are computed, **Then** the dispossession cascade reaches a natural floor (bourgeoisie and petit-bourgeoisie shares are not affected by crisis-driven transitions, only LA/Proletariat/Lumpen redistribute).

______________________________________________________________________

### User Story 3 - Bifurcation Risk Assessment (Priority: P2)

As a simulation researcher, I need the system to assess whether crisis conditions are driving a population toward revolutionary solidarity or fascist reaction (the George Jackson Bifurcation), so that the simulation can model the historically observed phenomenon where identical material crises produce opposite political outcomes depending on organizational infrastructure and legitimation dynamics.

The existing `ConsciousnessSystem` already routes agitation energy based on solidarity network presence. This feature adds a *crisis-specific* bifurcation risk metric that synthesizes solidarity topology, legitimation index, and class burden distribution into a single directional indicator that downstream systems can consume.

**Why this priority**: P2 because bifurcation risk assessment is a derived analytical metric that depends on both crisis detection (US1) and class composition changes (US2). It adds interpretive depth but the simulation can run without it.

**Independent Test**: Can be tested by constructing scenarios with varying solidarity densities and class burden distributions under crisis, then verifying the bifurcation risk metric correctly indicates revolutionary vs. fascist trajectory. Delivers value by providing a legible summary indicator of political direction during crisis.

**Acceptance Scenarios**:

1. **Given** a population in crisis where solidarity edges connect more than 60% of worker nodes across class lines (high cross-class solidarity), **When** bifurcation risk is computed, **Then** the metric indicates "revolutionary trajectory" (class consciousness accumulates faster than national identity).
2. **Given** a population in crisis where solidarity edges are sparse or confined within class boundaries (atomized/siloed solidarity), **When** bifurcation risk is computed, **Then** the metric indicates "fascist trajectory" (national identity accumulates faster than class consciousness).
3. **Given** a population in crisis where the labor aristocracy bears disproportionate losses (LA share declining faster than other classes), **When** bifurcation risk is computed, **Then** the fascist trajectory indicator is amplified (LA losing status gravitates toward reactionary politics to restore hierarchy).
4. **Given** a population where legitimation index is high (population believes the system can recover), **When** bifurcation risk is computed during early crisis, **Then** both revolutionary and fascist indicators are suppressed (faith in system recovery dampens political radicalization).

______________________________________________________________________

### User Story 4 - Crisis Phase Lifecycle Management (Priority: P2)

As a simulation researcher, I need crisis to follow a lifecycle with distinct phases (onset, early, deep, recovery, post-crisis) rather than being a binary flag, so that the simulation can model the qualitatively different dynamics that characterize each phase of a real economic crisis.

**Why this priority**: P2 because the phased lifecycle enriches the existing binary crisis flag but the system can function with binary detection (US1) alone. Phase tracking enables the phased amplification required by US2.

**Independent Test**: Can be tested by driving a county through a complete crisis lifecycle via synthetic profit rate inputs and verifying correct phase transitions, duration tracking, and phase-appropriate behavior at each stage.

**Acceptance Scenarios**:

1. **Given** a county with no active crisis, **When** profit rate falls below `r_threshold` for fewer than N consecutive periods, **Then** crisis phase remains "normal" (no crisis).
2. **Given** a county where profit rate has been below `r_threshold` for exactly N consecutive periods, **When** the crisis detector evaluates, **Then** crisis phase transitions to "onset" and an onset event is emitted.
3. **Given** a county in "onset" phase, **When** crisis persists for additional periods beyond N, **Then** phase transitions through "early" (periods N+1 to N+4) and then "deep" (period N+5 onward), with each transition emitting a phase-change event.
4. **Given** a county in "deep" crisis, **When** profit rates recover above `r_threshold` for M consecutive periods, **Then** phase transitions to "recovery" (not immediately to "normal"), and recovery phase persists for a hysteresis window before returning to "normal".

______________________________________________________________________

### User Story 5 - Wage Compression and Accumulation Halt (Priority: P3)

As a simulation researcher, I need deep crisis to produce wage compression effects that halt capital accumulation, so that the simulation models the self-reinforcing feedback loop where crisis destroys the conditions for recovery (the "crisis trap").

**Why this priority**: P3 because this captures an important secondary effect (the crisis feedback loop) but the core crisis mechanics (detection, cascade, bifurcation) work without it. This adds realism to prolonged crisis scenarios.

**Independent Test**: Can be tested by running a county through deep crisis and measuring whether wage rates compress, accumulation rates approach zero, and the crisis becomes self-sustaining absent external intervention.

**Acceptance Scenarios**:

1. **Given** a county in deep crisis (5+ periods), **When** wages are computed for the next period, **Then** wage rates decline proportionally to crisis duration (wage compression effect).
2. **Given** a county where wage compression has reduced the accumulation rate below a minimum threshold, **When** class transitions are computed, **Then** upward mobility effectively halts (accumulation rate clamped to zero or near-zero).
3. **Given** a county in the crisis trap (wages compressed, accumulation halted), **When** no external shock restores profit rates, **Then** crisis persists indefinitely (stable crisis equilibrium) until an exogenous factor changes conditions.

______________________________________________________________________

### Edge Cases

- What happens when ALL counties in the simulation enter crisis simultaneously (systemic crisis)? The national-level class distribution must still sum to 1.0 and individual county distributions must maintain their sum-to-one invariant.
- How does the system handle a county that oscillates rapidly around `r_threshold` (profit rate hovering at the boundary)? The consecutive-period accumulator prevents rapid on/off cycling.
- What happens when crisis duration exceeds the simulation time horizon? Crisis phase must be serializable in the tick state for persistence across simulation runs.
- How does the system handle a county with zero employment (fully lumpenproletariat)? Profit rate is undefined; crisis detection skips such counties.
- What happens when recovery begins but a new profit rate decline interrupts it? The recovery phase resets and crisis resumes from the current depth.

## Requirements *(mandatory)*

### Functional Requirements

#### Crisis Detection

- **FR-001**: System MUST detect crisis onset when the stock-based profit rate `r[t]` falls below a configurable threshold `r_threshold` (default: 0.05, i.e. 5%) for N consecutive crisis periods, where N is configurable (default: 3 periods). A crisis period is defined as `crisis_period_ticks` ticks (default: 13 ticks = 1 quarter). The detector evaluates once per crisis period, not every tick. The default `r_threshold` of 5% is derived from Piketty's rate of return framework (`r = capital_share / wealth_income_ratio`) applied to World Inequality Database data for the US (1970-2024): every significant recession since 2000 occurred when the computed `r` fell to or below 5.1%, with the P10 of the full historical distribution at 5.09%.
- **FR-002**: System MUST track crisis duration as the number of consecutive crisis periods where `r[t] < r_threshold`, persisted across ticks in the county economic state.
- **FR-003**: System MUST classify crisis into phases based on duration: "normal" (no crisis), "onset" (period N), "early" (periods N+1 through N+4), "deep" (period N+5 onward), and "recovery" (profit rate above threshold for M consecutive periods, default M=2). Recovery phase duration is proportional to crisis duration: `recovery_duration = min(crisis_duration, R_cap)` where R_cap is configurable (default: 8 periods). After recovery_duration periods, phase transitions to "normal".
- **FR-004**: System MUST emit a crisis phase-change event whenever a county transitions between phases, including the county identifier, previous phase, new phase, current profit rate, and crisis duration.
- **FR-005**: System MUST handle missing profit rate data (None values from division-by-zero in derived rates) by neither counting toward nor resetting the consecutive-period accumulator.

#### Dispossession Cascade

- **FR-006**: System MUST apply phase-dependent amplification to class transition rates during crisis, with amplification factors that increase with crisis depth:

  | Phase    | Dispossession Multiplier | Precaritization Multiplier | Accumulation Multiplier | Stabilization Multiplier |
  |----------|--------------------------|---------------------------|------------------------|-------------------------|
  | Normal   | 1.0                      | 1.0                       | 1.0                    | 1.0                     |
  | Onset    | 1.2                      | 1.5                       | 0.8                    | 0.7                     |
  | Early    | 1.8                      | 2.5                       | 0.4                    | 0.4                     |
  | Deep     | 3.0                      | 3.5                       | 0.1                    | 0.2                     |
  | Recovery | 1.3                      | 1.2                       | 0.6                    | 0.5                     |

- **FR-007**: System MUST enforce that crisis-amplified transition rates remain clamped to `[0, 1]` after multiplication.
- **FR-008**: System MUST preserve the sum-to-one invariant for class distributions after crisis-amplified transitions (`abs(total - 1.0) <= 0.001`).
- **FR-009**: System MUST implement hysteresis in recovery: when transitioning from crisis to recovery phase, upward transition rates (accumulation, stabilization) recover according to a hysteresis coefficient `h` (default: 0.5) such that the effective recovery multiplier at recovery period `k` is `normal_rate * (1 - h^k)`, approaching but not immediately reaching normal rates.
- **FR-010**: System MUST confine crisis-driven class transitions to the three dynamic classes (labor aristocracy, proletariat, lumpenproletariat). Bourgeoisie and petit-bourgeoisie shares are not modified by crisis amplification.

#### Bifurcation Risk

- **FR-011**: System MUST compute a bifurcation risk metric during active crisis periods that indicates the trajectory toward revolutionary solidarity versus fascist reaction, expressed as a value in `[-1, +1]` where -1 is fully revolutionary and +1 is fully fascist. During non-crisis periods, the bifurcation risk metric is 0 (neutral). The combination formula is:

  ```
  raw_score = -w_s * solidarity_density + w_b * class_burden_ratio
  dampened_score = raw_score * (1 - legitimation)
  bifurcation = clamp(dampened_score, -1, +1)
  ```

  Where `w_s` (solidarity weight, default: 1.0) and `w_b` (burden weight, default: 1.0) are configurable in GameDefines, `solidarity_density` is [0, 1] (FR-012), `legitimation` is [0, 1] (FR-013), and `class_burden_ratio` is [0, +inf) normalized to [0, 1] via `min(ratio, 1.0)` (FR-014). High solidarity pushes revolutionary (negative), high LA burden pushes fascist (positive), and high legitimation dampens both toward zero. The additive structure ensures each input has independent, interpretable influence.
- **FR-012**: System MUST incorporate cross-class solidarity density into the bifurcation risk calculation, defined as the fraction of possible SOLIDARITY edges between nodes of different ClassPosition that actually exist (range [0, 1]). Higher cross-class solidarity edge density pushes the metric toward the revolutionary end (-1). When the county has fewer than 2 distinct ClassPosition categories present, solidarity density is 0.
- **FR-013**: System MUST incorporate legitimation index into the bifurcation risk calculation, computed as `legitimation = 1 - mean(agitation)` across nodes in the county (range [0, 1]), where higher legitimation dampens both extremes toward the center (0). Uses the existing `agitation` field from IdeologicalProfile.
- **FR-014**: System MUST incorporate class burden distribution into the bifurcation risk calculation, where disproportionate labor aristocracy losses (LA share declining faster than proletariat share) push the metric toward the fascist end (+1). The class burden ratio is defined as `|delta_LA| / max(|delta_Prol|, epsilon)` where delta is the per-period share change and epsilon is a small constant (default: 0.001) to prevent division by zero. The ratio is clamped to [0, 1] via `min(ratio, 1.0)` before use in the combination formula.
- **FR-015**: System MUST persist the bifurcation risk metric in the county economic state so that it is available to downstream systems (ConsciousnessSystem, StruggleSystem) in subsequent ticks.

#### Wage Compression

- **FR-016**: System MUST apply wage compression during deep crisis phases, reducing the effective wage rate by a configurable fraction per crisis period (default: 2% per period of deep crisis).
- **FR-017**: System MUST halt upward class transitions (accumulation rate clamped to zero) when wage compression reduces wages below a configurable floor relative to subsistence cost.
- **FR-018**: System MUST model the crisis trap: when wage compression and accumulation halt co-occur, crisis persists as a stable equilibrium until an exogenous shock restores profit rates above threshold.

#### Integration

- **FR-019**: System MUST integrate with the existing `TickDynamicsSystem` pipeline, replacing the current Step 5 (crisis detection) and modifying Step 6 (class transitions) to use phase-dependent amplification. The TickDynamicsSystem pipeline runs annually (every 52 ticks). Within each annual pipeline invocation, Step 5 processes all quarterly crisis evaluations that fall within that annual cycle (4 evaluations at the default 13-tick crisis period). This batch-within-step design confines crisis logic to Step 5 while respecting the quarterly evaluation cadence: Step 5 iterates over each crisis period boundary that occurred since the last pipeline run, evaluating profit rates and advancing phase counters for each.
- **FR-020**: System MUST replace the existing `ThresholdCrisisDetector` with the new multi-period `CrisisDetector`. The new detector removes unemployment rate as a crisis trigger (unemployment is a lagging indicator, a symptom of crisis rather than a cause). Required inputs: current profit rate, crisis history (CrisisState), and profit rate time series. Unemployment-based detection logic is removed, not preserved.
- **FR-021**: System MUST replace or extend the existing `DefaultCrisisAmplifier` with a `PhasedCrisisAmplifier` that consumes crisis phase information to select appropriate amplification multipliers.
- **FR-022**: System MUST emit events of type `ECONOMIC_CRISIS` (existing) for crisis onset and new event types for phase transitions, dispossession cascade milestones, and bifurcation risk threshold crossings.
- **FR-023**: All configurable parameters MUST be defined in `GameDefines` under a new `crisis` category: `crisis_period_ticks` (default: 13), `r_threshold` (default: 0.05), `N` (default: 3), `M` (default: 2), `R_cap` (default: 8), amplification multipliers (per FR-006 table), hysteresis coefficient `h` (default: 0.5), wage compression rate (default: 0.02), wage compression floor ratio (default: 0.8, i.e. 80% of subsistence cost), bifurcation solidarity weight `w_s` (default: 1.0), bifurcation burden weight `w_b` (default: 1.0), and class burden epsilon (default: 0.001).

### Key Entities

- **CrisisState**: Represents the crisis status of a single county. Attributes: current phase (enum: NORMAL, ONSET, EARLY, DEEP, RECOVERY), consecutive periods below threshold, consecutive recovery periods, crisis start period, peak severity (lowest profit rate during crisis), cumulative wage compression applied.
- **CrisisPhase**: Enumeration of crisis lifecycle phases with associated amplification profiles.
- **BifurcationRiskMetric**: Represents the political trajectory indicator for a county under crisis. Attributes: bifurcation score (-1 to +1), cross-class solidarity density, legitimation index, class burden ratio (LA loss rate / proletariat loss rate), contributing factors breakdown.
- **PhasedAmplificationProfile**: Maps crisis phases to transition rate multipliers. Configurable via GameDefines.
- **CrisisEvent**: Extension of existing Event model for crisis-specific payloads including phase transition details, cascade metrics, and bifurcation risk snapshots.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a synthetic profit rate time series that dips below threshold for exactly N periods, crisis detection activates within 1 tick of the Nth period and deactivates after M recovery periods, with zero false positives or false negatives.
- **SC-002**: During simulated 2008-2012 conditions (sustained profit rate decline of 15-25% from baseline), the LA share declines by at least 5 percentage points and the lumpenproletariat share increases by at least 5 percentage points, matching the observed direction and approximate magnitude of class composition shifts.
- **SC-003**: During simulated recovery (2013-2016 conditions), class composition does not fully restore to pre-crisis levels within 4 recovery periods, demonstrating hysteresis (at least 2 percentage points of permanent shift remaining).
- **SC-004**: In a scenario with high cross-class solidarity (>60% edge density), the bifurcation risk metric is below -0.3 (revolutionary trajectory). In a scenario with atomized solidarity (<20% edge density), the metric is above +0.3 (fascist trajectory).
- **SC-005**: All county-level class distributions maintain the sum-to-one invariant (`abs(total - 1.0) <= 0.001`) throughout the crisis lifecycle, including during phase transitions.
- **SC-006**: Deep crisis (5+ periods) produces wage compression that reduces the accumulation rate to near zero (below 0.01), demonstrating the crisis trap feedback loop.
- **SC-007**: Crisis phase transitions emit events that can be consumed by the observer system, enabling crisis lifecycle visualization and narrative generation.
- **SC-008**: The crisis detection, dispossession cascade, and bifurcation risk calculations each complete within the existing per-tick time budget (no measurable performance degradation on a standard simulation of 50 counties over 20 simulated years).

## Assumptions

- **A-001**: The stock-based profit rate (`r = s / (K + v)`) from the DerivedRateCalculator is the primary crisis indicator. Flow-based profit rate is not used for crisis detection.
- **A-002**: Crisis operates at a configurable period timescale (`crisis_period_ticks`, default: 13 ticks = quarterly), not the weekly engine tick timescale. The TickDynamicsSystem pipeline runs annually (every 52 ticks); Step 5 of the pipeline batch-processes all quarterly crisis evaluations within each annual cycle (see FR-019). This preserves the constraint that all crisis logic lives within the pipeline (C-001) while respecting the quarterly cadence. All period-based parameters (N, M, R_cap, phase durations) are measured in crisis periods.
- **A-003**: The existing George Jackson Bifurcation implementation in ConsciousnessSystem continues to handle per-tick ideological routing. The bifurcation risk metric introduced here is a crisis-period summary indicator, not a replacement for per-tick routing.
- **A-004**: Bourgeoisie and petit-bourgeoisie class shares are structurally fixed during crisis (their dynamics are governed by different mechanisms outside this feature's scope).
- **A-005**: The phased amplification multipliers in FR-006 are initial defaults subject to calibration. The specification defines the mechanism, not the final tuned values.
- **A-006**: Legitimation index is derived as `legitimation = 1 - mean(agitation)` across county nodes, using the existing `agitation` field from IdeologicalProfile. No new external data sources required.

## Constraints

- **C-001**: Must integrate with the existing 8-step TickDynamicsSystem pipeline without restructuring the pipeline itself. Changes are confined to Step 5 (crisis detection, including batch quarterly evaluation) and Step 6 (class transitions) plus new derived outputs. Step 5 may internally iterate over multiple crisis periods per annual pipeline invocation, but this is an implementation detail within the step, not a structural change to the pipeline.
- **C-002**: Must maintain backward compatibility with existing `CrisisAmplifier` protocol. The new `PhasedCrisisAmplifier` must satisfy the existing protocol interface while adding phase-awareness.
- **C-003**: All new state (CrisisState, BifurcationRiskMetric) must be serializable in the `CountyEconomicState` or `SimulationTickState` for cross-tick persistence.
- **C-004**: Must not introduce new external data source dependencies. All inputs come from existing calculators and the simulation's own state history.

## Dependencies

- **Requires Feature 017** (Simulation Tick Dynamics): Provides the TickDynamicsSystem pipeline, CountyEconomicState, DerivedRateCalculator, and ThresholdCrisisDetector that this feature extends.
- **Requires Feature 016** (Class Dynamics Engine): Provides the ClassTransitionEngine, TransitionRates, CrisisAmplifier protocol, and DefaultCrisisAmplifier that this feature replaces/extends.
- **Requires Feature 012** (Capital Stock Dynamics): Provides capital stock K used in stock-based profit rate calculation.
- **Consumed by**: ConsciousnessSystem (bifurcation risk metric influences ideological routing), StruggleSystem (crisis phase affects struggle intensity), Observer/Narrative systems (crisis events for storytelling).

## Future Enhancements

- **FE-001**: Sector-specific crisis detection using industry-level OCC and profit rates (requires Epoch 2 TRPF implementation with real OCC data).
- **FE-002**: Inter-county crisis contagion via supply chain linkages (crisis in one county raises crisis probability in economically connected counties).
- **FE-003**: Policy response modeling: bourgeoisie policy choices (stimulus, austerity, war) as crisis responses that alter the crisis trajectory.
- **FE-004**: Historical scenario calibration against specific crises (1929, 1973, 2008) with empirical validation targets.
- **FE-005**: Integration with MetabolismSystem for ecological crisis triggers (biocapacity collapse as crisis catalyst).
