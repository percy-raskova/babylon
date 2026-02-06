# Implementation Plan: Crisis and Devaluation Mechanics

**Branch**: `018-crisis-devaluation-mechanics` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-crisis-devaluation-mechanics/spec.md`

## Summary

Replace binary crisis detection (`ThresholdCrisisDetector`) with a multi-period lifecycle system driven by the flow-based profit rate `s/(c+v)` from `ValueTensor4x3`. Crisis progresses through five phases (NORMAL, ONSET, EARLY, DEEP, RECOVERY) with phase-dependent amplification of class transition rates, wage compression feedback loops in deep crisis, and a George Jackson bifurcation risk metric synthesizing solidarity topology, legitimation, and class burden distribution. Integration via batch-within-step design in the existing TickDynamicsSystem pipeline (Step 5 crisis detection, Step 6 phased amplification).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models), NetworkX 3.x (solidarity graph), existing economics module (Features 011-017)
**Storage**: In-memory computation; no new database tables. CrisisState persists via CountyEconomicState in the graph bridge.
**Testing**: pytest (TDD Red-Green-Refactor). Unit tests for detector, amplifier, bifurcation calculator. Integration tests for full lifecycle.
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project (extends existing economics subsystem)
**Performance Goals**: No measurable per-tick degradation on 50-county, 20-year simulation (SC-008)
**Constraints**: No pipeline restructuring (C-001). Backward-compatible CrisisAmplifier protocol (C-002). All state serializable in CountyEconomicState (C-003).
**Scale/Scope**: ~8 new/modified source files, ~5 new test files, ~15 modified test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.3 TRPF with Counter-Tendencies | PASS | Crisis detects when net r falls below threshold. Counter-tendencies (imperial rent) can prevent crisis. Rate emerges from ValueTensor4x3 interaction, not assumed. |
| I.4 George Jackson Bifurcation | PASS | Bifurcation risk metric (FR-011) directly implements this. Solidarity topology determines revolutionary vs fascist outcome. |
| I.7 Quantitative → Qualitative | PASS | Crisis phases are discrete (enum), not continuous. Profit rate accumulates quantitatively; phase transitions are qualitative events. |
| II.2 Primitives vs Derived | JUSTIFIED | CrisisState and BifurcationRiskMetric are persisted despite II.2 "never store derived quantities." Justified: they are accumulated temporal state (like SmoothedCoefficients), not derivable from current-tick primitives. See R4, R6 in research.md. |
| II.4 Quantities vs Coefficients | PASS | Crisis is modeled as "discontinuous coefficient reset when r < threshold" per the constitution's own crisis definition. Amplification multipliers are coefficients selected by phase. |
| III.1 No Magic Constants | PASS | r_threshold=0.05 derives from WID/Piketty analysis. Amplification multipliers from 2008-2012 crisis data ratios. All configurable in GameDefines. |
| III.4 Data Source Traceability | PASS | Profit rate from QCEW/BEA via ValueTensor4x3. Threshold from WID (Piketty). Class burden from QCEW employment data. |
| V.1 Material Base First | PASS | Economic crisis (TRPF) drives class transitions, which then feed bifurcation assessment. Material base → class formation → political outcome. |

## Project Structure

### Documentation (this feature)

```text
specs/018-crisis-devaluation-mechanics/
├── plan.md              # This file
├── research.md          # Phase 0: 9 research items (R1-R9)
├── data-model.md        # Phase 1: Entity definitions, ER diagram, state machine
├── quickstart.md        # Phase 1: Module map, usage patterns
├── checklists/
│   └── comprehensive.md # 33-item requirements quality checklist (12/33 resolved)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/babylon/economics/tick/
├── types.py              # MODIFY: Add CrisisState, CrisisPhase, BifurcationRiskMetric
│                         #         Replace crisis:bool on CountyEconomicState
├── crisis_detector.py    # REPLACE: MultiPeriodCrisisDetector (was ThresholdCrisisDetector)
├── system.py             # MODIFY: Step 5 batch quarterly eval, Step 6 phased amplification
└── graph_bridge.py       # MODIFY: Serialize CrisisState, bifurcation score to graph

src/babylon/economics/dynamics/
├── crisis.py             # REPLACE: PhasedCrisisAmplifier (was DefaultCrisisAmplifier)
└── data_sources.py       # UNCHANGED: CrisisAmplifier protocol preserved

src/babylon/economics/crisis/
├── __init__.py           # NEW: Public API
└── bifurcation.py        # NEW: BifurcationRiskCalculator

src/babylon/config/
└── defines.py            # MODIFY: Add CrisisDefines category to GameDefines

src/babylon/models/
└── enums.py              # MODIFY: Add 3 EventType values

tests/unit/economics/tick/
├── test_multi_period_detector.py  # NEW: US1 acceptance scenarios
├── test_crisis.py                 # MODIFY: Update for new detector

tests/unit/economics/dynamics/
├── test_phased_amplifier.py       # NEW: US2 acceptance scenarios
├── test_crisis.py                 # MODIFY: Update for phased amplification

tests/unit/economics/crisis/
├── conftest.py                    # NEW: Crisis test fixtures
├── test_bifurcation_risk.py       # NEW: US3 acceptance scenarios
├── test_crisis_lifecycle.py       # NEW: US4 full lifecycle integration
└── test_wage_compression.py       # NEW: US5 wage compression + crisis trap
```

**Structure Decision**: Extends existing `economics/tick/` and `economics/dynamics/` packages. New `economics/crisis/` package for bifurcation risk (separates the political-trajectory concern from economic-state concern). This follows the existing pattern where each economic subsystem has its own package.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|-----------|--------------------------------------|
| Persist CrisisState (II.2) | Consecutive-period counter is temporal accumulation, not derivable from current tick | Cannot recompute "how many consecutive quarters was r below threshold" from a single profit rate value |
| Persist BifurcationRiskMetric (II.2) | Computed quarterly, consumed weekly. Inputs change between evaluation points | Recomputing at consumption time would use stale inputs and violate the "recorded measurement" semantic |
