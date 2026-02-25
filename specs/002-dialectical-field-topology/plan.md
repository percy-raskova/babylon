# Implementation Plan: Dialectical Field Topology

**Branch**: `002-dialectical-field-topology` | **Date**: 2026-02-25 | **Spec**: `specs/002-dialectical-field-topology/spec.md`
**Input**: Feature specification from `/specs/002-dialectical-field-topology/spec.md`

## Summary

Implement a field-theoretic layer on the NetworkX graph that computes named contradiction fields (exploitation, immiseration, imperial rent, displacement) at every social-class node per tick, derives spatial operators (gradient, Laplacian) and temporal operators (df/dt, d2f/dt2) from those fields, computes Ollivier-Ricci curvature as a cached structural property, identifies the principal contradiction per tick, performs continuity accounting, and governs discrete edge mode transitions via declarative compound predicates. The system adds CO-OPTIVE as a 5th edge mode with derivative suppression, latent contradiction tracking, and George Jackson bifurcation dynamics.

Three new systems slot into the existing execution order after the current 13 systems: ContradictionFieldSystem (position 14), FieldDerivativeSystem (position 15), and EdgeTransitionSystem (position 16). All use the existing GraphProtocol with auto-wrap guard pattern.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: NetworkX 3.x (graph), Pydantic 2.x (models), scipy (Wasserstein-1 LP for curvature)
**Storage**: In-memory via GraphProtocol (`update_node`, `update_edge`) + `context.persistent_data` for cross-tick history
**Testing**: pytest (markers: `@pytest.mark.unit`, `@pytest.mark.math`, `@pytest.mark.topology`)
**Target Platform**: Linux (local simulation engine)
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Per-tick overhead < 10ms for 50-node graph (field + derivative + transition computation)
**Constraints**: Must use GraphProtocol exclusively (no direct NetworkX access). No new persistence mechanism. scipy is the only new dependency.
**Scale/Scope**: Detroit metro graph (~20 social-class nodes, ~40 edges). 4 contradiction fields initially, extensible.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.1 Settler-Colonial Frame | PASS | Detroit metro validation uses settler-colonial geography |
| I.2 Imperial Rent (Φ) | PASS | Imperial rent is one of the four contradiction fields |
| I.3 TRPF with Counter-Tendencies | PASS | Exploitation field derived from s/v captures TRPF |
| I.4 George Jackson Bifurcation | PASS | CO-OPTIVE breakdown → solidarity topology → bifurcation direction. Directly implements I.4. |
| I.5 Department III | N/A | Reproductive labor not in initial field set (future extension) |
| I.6 Solidarity as Edge Mode | AMENDMENT NEEDED | Constitution defines 4 modes. This feature adds CO-OPTIVE as 5th mode. Research R-008 documents the theoretical justification. |
| I.7 Quantitative→Qualitative | PASS | Core principle: continuous field values → discrete edge mode transitions via compound predicates |
| I.12 Catastrophe Surface Dynamics | PASS | Compound predicates define the fold geometry; field derivatives are the control parameters |
| I.13 Principal Contradiction | PASS | FR-008 directly implements this constitutional requirement |
| I.14 Contradiction Internals | PASS | Temporal derivatives (trajectory), edge-level contradiction character. Aspect via directed edges. |
| I.15 Edge Mode Transition Topology | PASS + EXTENSION | Implements the state machine with compound predicate conditions. Extends with CO-OPTIVE transitions. |
| II.2 Primitives vs Derived | PASS | Contradiction fields are derived from economic outputs, never stored as primitives |
| II.3 NetworkX as Discretized Manifold | PASS | This feature is the literal implementation of "fields propagate on the manifold" |
| II.5 AI Observes, Never Controls | PASS | All computation is deterministic. Events emitted for observer consumption. |
| II.6 State is Data, Engine is Transformation | PASS | Systems are stateless transformations. Cross-tick state uses persistent_data. |
| III.1 No Magic Constants | PASS | Normalization bounds from QCEW data. Thresholds in GameDefines. |
| III.4 Data Sources | PASS | QCEW for exploitation/immiseration, PWT for imperial rent, Census for displacement |

**Gate Result**: PASS with one constitutional amendment (I.6 → add CO-OPTIVE mode, I.15 → extend transition topology). Amendment is justified by systematic literature review documented in `edge-mode-completeness-analysis.md`.

## Project Structure

### Documentation (this feature)

```text
specs/002-dialectical-field-topology/
├── plan.md              # This file
├── research.md          # Phase 0: 8 research decisions (R-001 through R-008)
├── data-model.md        # Phase 1: 11 entity definitions
├── quickstart.md        # Phase 1: Developer quickstart
├── contracts/           # Phase 1: Python protocol contracts
│   ├── contradiction_field_system.py
│   ├── field_derivative_system.py
│   ├── edge_transition_system.py
│   └── field_registry.py
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   └── enums.py                          # MODIFY: Add EdgeMode enum (5 values)
├── engine/
│   ├── systems/
│   │   ├── contradiction_field.py        # NEW: ContradictionFieldSystem
│   │   ├── field_derivative.py           # NEW: FieldDerivativeSystem
│   │   ├── edge_transition.py            # NEW: EdgeTransitionSystem
│   │   └── __init__.py                   # MODIFY: Register new systems
│   ├── simulation_engine.py              # MODIFY: Add systems to execution order
│   └── field_registry.py                 # NEW: Open field registry
├── formulas/
│   └── curvature.py                      # NEW: Ollivier-Ricci via scipy LP
└── config/
    └── defines.py                        # MODIFY: Add field normalization bounds, transition thresholds

tests/
├── unit/engine/
│   ├── test_contradiction_field_system.py # NEW: Field computation tests
│   ├── test_field_derivative_system.py    # NEW: Derivative computation tests
│   ├── test_edge_transition_system.py     # NEW: Transition predicate tests
│   └── test_field_registry.py             # NEW: Registry extensibility tests
├── unit/formulas/
│   └── test_curvature.py                  # NEW: Ollivier-Ricci tests
└── integration/
    └── test_field_topology_integration.py # NEW: Multi-tick field evolution tests
```

**Structure Decision**: Single project extension. All new code follows existing `src/babylon/engine/systems/` pattern. No new packages or sub-projects. The `formulas/curvature.py` follows the existing `formulas/` module pattern for pure mathematical functions.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| scipy dependency (new) | Wasserstein-1 optimal transport for Ollivier-Ricci curvature requires LP solver | Pure Python solver would be slower and harder to verify. scipy.optimize.linprog is stable, well-tested, and already available in the dependency tree via numpy. |
| CO-OPTIVE constitutional amendment | Feature adds 5th edge mode not in constitution v1.5.0 | Cannot model co-optation dynamics (labor aristocracy, welfare state) without it. Theoretical justification from systematic literature review (Mao, Lenin, Dimitrov, Jackson). |
