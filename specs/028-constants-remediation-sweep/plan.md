# Implementation Plan: Constants Remediation Sweep

**Branch**: `028-constants-remediation-sweep` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/028-constants-remediation-sweep/spec.md`

## Summary

Execute the 5-phase remediation identified in the 027 Constants Provenance Audit. Wire 12 pipeline-ready Tier A constants to federal data sources via existing SQLite adapters, eliminate 34 Tier B dead code constants, centralize 28 inline Tier C constants into GameDefines for parameter sweep, and document/triage 138 remaining Tier D/E/gated-A constants. All changes gated by Detroit regression baselines (FR-005). Zero new adapters (FR-006), zero schema changes (FR-007).

## Technical Context

**Language/Version**: Python 3.12+ (existing stack)
**Primary Dependencies**: Pydantic 2.x (GameDefines frozen models), SQLAlchemy 2.x (hydrator ORM), NetworkX 3.x (graph bridge)
**Storage**: SQLite (`marxist-data-3NF.sqlite` read-only for data hydration; in-memory for simulation)
**Testing**: pytest (unit + integration + regression via `tools/regression_test.py`)
**Target Platform**: Linux (local simulation engine)
**Project Type**: Single project — modification of existing `src/babylon/config/defines.py` + formula/engine modules
**Performance Goals**: No measurable initialization slowdown (SQLite queries are sub-second)
**Constraints**: Frozen Pydantic models — all GameDefines mutations via `model_copy(update={})`. No new external dependencies.
**Scale/Scope**: 247 constants across ~20 source files; ~19 new GameDefines fields; ~34 deleted constants; ~28 inline constants centralized

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| III.1 | No Magic Constants | PASS | This feature's explicit goal — replaces magic numbers with data-derived or documented values |
| III.2 | Falsifiability Required | PASS | FR-004 mandates falsifiability statement for each newly wired constant |
| III.3 | Physics Cosplay Prohibition | PASS | No new tensor notation introduced |
| III.4 | Data Source Traceability | PASS | FR-002 restricts to existing approved data sources; FR-006 forbids new ones |
| III.5 | Empirical vs Strategic Separation | PASS | Tier A wiring provides material conditions from data; Tier E game design knobs remain strategic |
| IV | Detroit Testable | PASS | FR-005 regression gate on Wayne/Oakland County baseline after each cluster |
| VI.1 | Material Base First | PASS | Fixes economic foundation (extraction_efficiency, class shares, wage rates) before superstructure |
| VI.3 | Flag Scope Creep | PASS | FR-006 (no new sources), FR-007 (no schema changes) bound scope explicitly |
| II.6 | State is Data, Engine is Transformation | PASS | GameDefines remains frozen Pydantic; hydration at init, not during tick |
| VIII.6 | Constants Without Data Sources | PASS | This feature remediates the anti-pattern; remaining unfalsifiable constants triaged per FR-003 |

**Gate Result**: ALL PASS — no violations. Proceed to implementation.

**Post-Phase 1 Re-check**: Constitution compliance confirmed. No new violations introduced by design decisions:
- New GameDefines fields follow existing `Field(ge=, le=, description=)` pattern (II.4)
- Data hydration at initialization, not during tick (II.6)
- Edge transition thresholds centralized to GameDefines maintain Constitution I.15 edge mode transition rules

## Project Structure

### Documentation (this feature)

```text
specs/028-constants-remediation-sweep/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: codebase research findings
├── data-model.md        # Phase 1: GameDefines modifications + artifact schemas
├── quickstart.md        # Phase 1: execution guide
├── checklists/
│   └── requirements.md  # Spec quality validation
├── contracts/
│   └── disposition-schema.yaml  # JSON Schema for constant disposition tracking
├── reports/             # Phase 2 output (generated during implementation)
│   ├── triage-report.md         # FR-003: all 247 dispositions
│   └── deviation-log.md         # FR-005: data-derived value deviations
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/
├── config/
│   └── defines.py                    # PRIMARY TARGET: ~19 new fields, ~113 updated descriptions
├── formulas/
│   ├── constants.py                  # Tier B: redirect LOSS_AVERSION_COEFFICIENT, EPSILON
│   ├── dynamic_balance.py            # Tier B: remove 10 function param defaults
│   ├── solidarity.py                 # Tier B: remove activation_threshold default
│   ├── metabolic_rift.py             # Tier B: remove entropy_factor, max_ratio defaults
│   ├── curvature.py                  # Tier B: remove alpha default
│   ├── trpf.py                       # Tier B: remove floor default
│   ├── ideological_routing.py        # Tier C: centralize _ROUTING_SCALE, agitation_decay
│   ├── vitality.py                   # Tier C: centralize attrition base
│   ├── class_dynamics.py             # Tier C: centralize ODE coefficients
│   └── community.py                  # Tier C: centralize overlap_bonus, rent_penalty, maintenance
├── engine/
│   ├── observers/
│   │   ├── endgame_detector.py       # Tier B: delete 5 deprecated module constants
│   │   └── metrics.py                # Tier B: extract DEATH_THRESHOLD to GameDefines
│   ├── topology_monitor.py           # Tier B: delete 2 + extract 5 module constants
│   └── systems/
│       ├── struggle.py               # Tier C: centralize consciousness boost multiplier
│       ├── edge_transition.py        # Tier C: centralize 16 threshold values
│       └── dispossession_events.py   # Tier C: centralize transfer scale
├── economics/
│   ├── tick/
│   │   └── system.py                 # Tier A: wire 8 class share constants (lines 320-342)
│   ├── hydrator.py                   # Reference: MarxianHydrator pattern
│   ├── adapters.py                   # Reference: SQLiteQCEWSource, InterpolatingBEASource
│   └── credit/
│       └── types.py                  # Tier C: centralize STAGNATION_CREDIT_GROWTH
├── data/
│   ├── reference/
│   │   └── hydrator.py               # Tier A: extend with new hydration functions
│   ├── census/
│   │   └── loader_3nf.py             # Reference: CensusLoader
│   ├── atus/
│   │   └── db_loader.py              # Reference: ATUSDBLoader
│   └── fred/
│       └── api_client.py             # Reference: FredAPIClient
tests/
├── baselines/                        # Regression baselines (regenerated during remediation)
└── unit/
    └── config/
        └── test_constants_sync.py    # Existing sync tests (update after Tier B changes)
tools/
├── regression_test.py                # Regression gate infrastructure
└── shared.py                         # DEATH_THRESHOLD duplicate to remove
```

**Structure Decision**: Single project, modifying existing modules in-place. No new packages or directories created (except `specs/028-*/reports/` for documentation artifacts). All changes follow existing patterns in `src/babylon/`.

## Complexity Tracking

No constitution violations to justify. All gates pass.

## Implementation Phases

### Phase A: Baseline Establishment (Pre-work)
Generate fresh regression baselines from current codebase state before any modifications.

### Phase B: Tier B Elimination (US2 — P2)
Three sub-phases:
1. **B.1 Pure Delete** — Remove 7 deprecated module constants (EndgameDetector, TopologyMonitor GASEOUS/CONDENSATION)
2. **B.2 Extract + Delete** — Add ~19 fields to GameDefines, update callers to use GameDefines path, then delete inline defaults
3. **B.3 Redirect** — Update FormulaConstant importers to use GameDefines directly
4. **B.4 Regenerate baselines** — New GameDefines hash from added fields

### Phase C: Tier A Wiring (US1 — P1)
Wire 12 constants to data sources:
1. **C.1 Tick Initializer** — 8 class share constants from Census/QCEW (highest impact)
2. **C.2 Economy** — extraction_efficiency, shadow_wage_hourly, base_subsistence, wage rates
3. **C.3 Reserve Army** — sigmoid_r0 from FRED
4. **C.4 Document deviations** — Each changed value logged with falsifiability statement

### Phase D: Tier C Centralization (US3 — P3)
1. **D.1 Formula module constants** — 12 non-edge-transition inline constants → GameDefines
2. **D.2 Edge transition thresholds** — 16 threshold values → GameDefines (new or existing subsection)
3. **D.3 Verify sweep space** — Run Morris sensitivity to confirm all 63+ Tier C constants visible

### Phase E: Triage & Documentation (US4 — P4)
1. **E.1 Tier D documentation** — 14 engineering constants: add constraint rationale to `description=`
2. **E.2 Tier E documentation** — 99 game design constants: add "Game design: [rationale]" to `description=`
3. **E.3 Gated Tier A triage** — 25 constants: document blocking feature + required adapter
4. **E.4 Final triage report** — Verify 247 dispositions sum correctly

### Phase F: Final Verification
Full regression suite + test suite + lint/typecheck. Verify SC-001 through SC-007.
