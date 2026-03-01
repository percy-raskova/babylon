# Implementation Plan: Bifurcation Topology Analysis

**Branch**: `033-bifurcation-topology` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/033-bifurcation-topology/spec.md`

## Summary

Extend TopologyMonitor with consciousness-weighted bifurcation analysis that predicts whether crisis produces fascism or revolution. Core innovation: solidarity edges are weighted by a nonlinear sigmoid of community collective_identity, so assimilationist solidarity (the Democratic Party coalition pattern) correctly classifies as fragile/fascist despite high edge density. Uses weakest-link combination across contradiction axes, two-pass topology (raw + consciousness-filtered Betti numbers), community bridge detection, and DPD legitimation amplification. Read-only observer emitting events on tendency change.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: NetworkX 3.x (graph analysis), XGI 0.10 (hypergraph), Pydantic 2.x (frozen models)
**Storage**: In-memory via GraphProtocol. No new database tables. BifurcationSnapshot stored in monitor history list.
**Testing**: pytest with `@pytest.mark.unit` and `@pytest.mark.topology` markers
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project — analysis package + monitor extension
**Performance Goals**: Full bifurcation computation adds no more than 10% overhead to average tick (SC-007)
**Constraints**: Pure NetworkX for Betti numbers (no giotto-tda). Standard `math.exp` sigmoid (no numpy/scipy).
**Scale/Scope**: ~7 analysis functions, 1 monitor class, 1 defines model, 1 event type, ~7 test modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.4 George Jackson Bifurcation | ALIGNED | This feature IS the George Jackson bifurcation, extended with consciousness weighting |
| I.6 Solidarity as Edge Mode | ALIGNED | Nonlinear sigmoid transform prevents solidarity-as-scalar; qualitative filter, not `+= x` |
| I.7 Quantitative → Qualitative | ALIGNED | collective_identity accumulates (float); tendency transforms discretely (enum: revolutionary/fascist/indeterminate) |
| I.12 Catastrophe Surface | ALIGNED | Bifurcation is the fold crossing; consciousness threshold is the cusp |
| I.18 Material-Ideological Distinction | ALIGNED | Gap between material position and ideological consciousness IS the consciousness weighting |
| II.5 AI Observes, Never Controls | ALIGNED | BifurcationMonitor is read-only observer, no graph writes |
| II.7 Edges vs Hyperedges | ALIGNED | Uses NetworkX (solidarity edges) + XGI (community hyperedges) as separate layers |
| III.1 No Magic Constants | MUST VERIFY | All thresholds in BifurcationDefines with documented sources |
| VIII.1 Solidarity as Scalar | ALIGNED | Nonlinear sigmoid explicitly prevents scalar multiplication |
| VIII.9 Community as Pairwise Edge | ALIGNED | Communities accessed via XGI hyperedges, not combinatorial pairs |

**Result**: All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/033-bifurcation-topology/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── analysis.md      # Function signatures
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/bifurcation/             # NEW analysis package
├── __init__.py                      # Public API exports
├── types.py                         # BifurcationResult, BifurcationSnapshot, AxisTendency, BridgeInfo
├── consciousness.py                 # consciousness_weighted_solidarity(), sigmoid transform
├── axis.py                          # crosses_contradiction_axis(), compute_axis_tendency()
├── bridges.py                       # detect_bridges()
├── resilience.py                    # compute_betti_numbers(), equivalence_classes(), critical nodes
├── ceiling.py                       # compute_solidarity_ceiling()
├── legitimation.py                  # compute_legitimation_amplifier()
└── analysis.py                      # bifurcation_tendency() — orchestrator

src/babylon/engine/
├── bifurcation_monitor.py           # BifurcationMonitor(TopologyMonitor) — observer extension
└── community_state_store.py         # CommunityStateStore protocol + InMemoryCommunityStateStore

src/babylon/config/defines.py        # BifurcationDefines added to GameDefines
src/babylon/models/enums.py          # BIFURCATION_TENDENCY_CHANGE EventType
src/babylon/models/events.py         # BifurcationTendencyEvent model

tests/unit/bifurcation/              # Unit tests
├── conftest.py                      # Shared fixtures (graphs, hypergraphs, community states)
├── test_consciousness.py            # US1: consciousness-weighted solidarity
├── test_axis.py                     # US2: per-axis contradiction analysis
├── test_bridges.py                  # US3: community bridge detection
├── test_resilience.py               # US4: Betti numbers, equivalence classes, purge
├── test_analysis.py                 # US5: full bifurcation computation
├── test_ceiling.py                  # US6: material solidarity ceiling
└── test_legitimation.py             # US7: legitimation crisis amplifier

tests/integration/topology/
└── test_bifurcation_integration.py  # Integration with TopologyMonitor + engine
```

**Structure Decision**: New `src/babylon/bifurcation/` package following the `src/babylon/organizations/` pattern — analysis functions in a domain package, consumed by an engine observer. BifurcationMonitor lives in `engine/` alongside `topology_monitor.py` because it extends TopologyMonitor and implements SimulationObserver.
