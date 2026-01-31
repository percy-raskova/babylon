# Implementation Plan: GUI Protocol Extension (Phase 0)

**Branch**: `006-gui-protocol-extension` | **Date**: 2026-01-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-gui-protocol-extension/spec.md`

## Summary

Extend the existing SimulationControl and SimulationState protocols to support GUI integration:

1. Add `register_observer`/`unregister_observer` to SimulationControl for callback-based notifications
1. Add `get_node_by_spatial_index(h3_index)` to SimulationState for H3→Territory lookup
1. Create ProtocolObserverAdapter for thread-safe state delivery to PyQt6 GUI

This enables GUI layers to receive simulation state updates without coupling to implementation details.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models), NetworkX 3.x (graph), h3 4.2 (spatial indexing)
**Storage**: N/A (in-memory protocols, no persistence changes)
**Testing**: pytest with hypothesis for property-based testing
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: Single project (extending existing engine)
**Performance Goals**: Observer notification < 1ms overhead per tick; spatial query O(1) via index
**Constraints**: Thread-safe delivery to GUI event loop; backward compatible protocol extension
**Scale/Scope**: Typical simulation: 10-100 territories, 1-10 observers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                                    | Status  | Notes                                                                               |
| -------------------------------------------- | ------- | ----------------------------------------------------------------------------------- |
| II.5 AI Observes, Never Controls             | ✅ PASS | Observer pattern is read-only; GUI receives snapshots, cannot modify state          |
| II.6 State is Data, Engine is Transformation | ✅ PASS | Protocol extensions return immutable snapshots (frozen Pydantic)                    |
| II.3 NetworkX as Discretized Manifold        | ✅ PASS | Spatial query bridges H3 index to graph topology                                    |
| III.2 Falsifiability Required                | ✅ PASS | Acceptance scenarios are testable with concrete inputs/outputs                      |
| VI.3 Determinism from Material Conditions    | ✅ PASS | Observer registration is deterministic; callbacks are invoked in registration order |

**Gate Result**: PASS - No constitution violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-gui-protocol-extension/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output (protocol definitions)
```

### Source Code (repository root)

```text
src/babylon/
├── protocols/
│   ├── __init__.py              # Export protocols
│   ├── simulation_control.py    # MODIFY: Add register/unregister_observer
│   └── simulation_state.py      # MODIFY: Add get_node_by_spatial_index
├── engine/
│   ├── simulation.py            # MODIFY: Implement new protocol methods
│   └── observer_adapter.py      # NEW: ProtocolObserverAdapter class
└── models/
    └── snapshots.py             # EXISTING: TerritoryState (return type)

tests/
├── unit/
│   └── protocols/
│       ├── test_simulation_control.py  # NEW: Observer registration tests
│       └── test_simulation_state.py    # NEW: Spatial query tests
└── integration/
    └── engine/
        └── test_observer_adapter.py    # NEW: Thread-safety tests
```

**Structure Decision**: Extending existing `src/babylon/protocols/` and `src/babylon/engine/` directories. Single new file for ProtocolObserverAdapter.

## Complexity Tracking

No constitution violations requiring justification. Feature is a minimal protocol extension.

______________________________________________________________________

## Phase 0: Research

### Research Tasks

1. **PyQt6 Thread Communication**: Best practices for cross-thread signal/slot patterns
1. **H3 Validation**: Python h3 library validation functions
1. **Existing Observer Pattern**: Current SimulationObserver implementation details

### Research Findings

See [research.md](research.md) for detailed findings.

**Summary of Key Decisions**:

| Topic                  | Decision                                 | Rationale                                                                        |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------------------------------- |
| Thread Safety          | Deep copy + frozen Pydantic models       | Compatible with Qt QueuedConnection; immutability guarantees no races            |
| H3 Validation          | Use `h3.is_valid_cell()`                 | Library function more robust than regex for edge cases                           |
| Callback Signature     | `Callable[[int, SimulationState], None]` | Tick number enables delta tracking; SimulationState provides full read interface |
| Duplicate Registration | Idempotent (single invocation)           | Simplest behavior; matches edge case spec                                        |

______________________________________________________________________

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for entity definitions.

**Key Entities**:

| Entity                  | Type      | Description                                 |
| ----------------------- | --------- | ------------------------------------------- |
| SimulationControl       | Protocol  | Extended with observer registration methods |
| SimulationState         | Protocol  | Extended with spatial query method          |
| ProtocolObserverAdapter | Class     | Thread-safe bridge to GUI callbacks         |
| ObserverCallback        | TypeAlias | `Callable[[int, SimulationState], None]`    |

### Contracts

See [contracts/](contracts/) for protocol definitions.

**Protocol Extensions**:

```python
# SimulationControl additions
def register_observer(self, callback: Callable[[int, SimulationState], None]) -> None: ...
def unregister_observer(self, callback: Callable[[int, SimulationState], None]) -> None: ...

# SimulationState additions
def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None: ...
```

### Quickstart

See [quickstart.md](quickstart.md) for usage examples.

______________________________________________________________________

## Per-Tick Update Rule

Observer callbacks are invoked at the end of each `step()` call:

```
step(n=1):
    for _ in range(n):
        new_state = engine.run_tick(graph, services, context)
        self._current_state = WorldState.from_graph(graph)
        self._notify_gui_observers()  # NEW: Invoke registered callbacks
```

The notification occurs AFTER state reconstruction, ensuring observers receive consistent state.

______________________________________________________________________

## Implementation Phases

### Phase 1: Protocol Extension (Tasks 1-2)

1. Extend SimulationControl protocol with observer methods
1. Extend SimulationState protocol with spatial query

### Phase 2: Simulation Implementation (Tasks 3-4)

3. Implement observer registration in Simulation class
1. Implement spatial query with H3 index lookup

### Phase 3: ProtocolObserverAdapter (Task 5)

5. Create ProtocolObserverAdapter with thread-safe snapshot delivery

### Phase 4: Testing & Integration (Tasks 6-7)

6. Unit tests for protocol methods
1. Integration tests for thread safety

______________________________________________________________________

## Risk Assessment

| Risk                                                     | Likelihood | Impact | Mitigation                                      |
| -------------------------------------------------------- | ---------- | ------ | ----------------------------------------------- |
| H3 index collision (multiple territories claim same hex) | Low        | Medium | First-match lookup; document behavior           |
| Callback exception halts simulation                      | Low        | High   | Wrap in try/except per ADR003                   |
| Thread race in adapter                                   | Medium     | High   | Deep copy snapshots; use frozen models          |
| Backward compatibility break                             | Low        | High   | Protocol extension (additive), not modification |

______________________________________________________________________

## Success Criteria Verification

| Criterion                              | Verification Method                                        |
| -------------------------------------- | ---------------------------------------------------------- |
| SC-001: Callbacks within tick boundary | Unit test: mock callback, verify invocation count per step |
| SC-002: H3 query correctness           | Unit test: known hex→territory mapping, 100% accuracy      |
| SC-003: Thread-safe snapshots          | Integration test: concurrent step + read, no corruption    |
| SC-004: Graceful callback failure      | Unit test: callback raises exception, simulation continues |
| SC-005: Backward compatibility         | Existing tests pass without modification                   |
