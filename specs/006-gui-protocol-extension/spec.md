# Feature Specification: GUI Protocol Extension (Phase 0)

**Feature Branch**: `006-gui-protocol-extension`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Phase 0 Protocol Extension tasks for GUI implementation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - GUI Observer Registration (Priority: P1)

A GUI developer wants to register their PyQt6-based visualization layer as an observer of the simulation engine so the map display updates automatically after each simulation tick.

**Why this priority**: Without observer registration, the GUI cannot receive state updates. This is the foundational capability that enables all GUI-simulation communication.

**Independent Test**: Can be fully tested by registering a mock callback and verifying it receives notifications with tick number and state reference after calling `step()`.

**Acceptance Scenarios**:

1. **Given** a SimulationControl instance and a callback function, **When** `register_observer(callback)` is called and then `step()` is called, **Then** the callback receives the current tick number and a reference to the SimulationState.
1. **Given** a registered observer callback, **When** `unregister_observer(callback)` is called, **Then** the callback no longer receives notifications on subsequent `step()` calls.
1. **Given** multiple registered observers, **When** `step()` is called, **Then** all observers receive notifications in registration order.

______________________________________________________________________

### User Story 2 - Spatial Query by H3 Index (Priority: P2)

A map visualization component (pydeck) receives click events containing H3 hex indices. The developer needs to retrieve the underlying node/territory state for that spatial location to display detailed information in a sidebar.

**Why this priority**: This bridges the gap between the GUI's spatial representation (H3 hexes used by pydeck) and the simulation's internal node identifiers. Essential for interactive map features.

**Independent Test**: Can be fully tested by querying a known H3 index from a hydrated simulation state and verifying the returned NodeState contains expected territory data.

**Acceptance Scenarios**:

1. **Given** a SimulationState with hydrated territories, **When** `get_node_by_spatial_index(h3_index)` is called with a valid claimed H3 index, **Then** the method returns the TerritoryState that claims that hex.
1. **Given** a SimulationState, **When** `get_node_by_spatial_index(h3_index)` is called with an H3 index not claimed by any territory, **Then** the method returns None.
1. **Given** a SimulationState, **When** `get_node_by_spatial_index(h3_index)` is called with an invalid H3 format, **Then** the method raises ValueError with a descriptive message.

______________________________________________________________________

### User Story 3 - Thread-Safe State Snapshot for GUI (Priority: P3)

The GUI (PyQt6 event loop) runs in a different thread than the simulation engine. A developer needs to safely access simulation state for rendering without race conditions that could cause display corruption or crashes.

**Why this priority**: Thread safety is required before the GUI can reliably render state. Without this, the GUI risks reading partially-updated state during engine execution.

**Independent Test**: Can be fully tested by simulating concurrent access from two threads (engine stepping, GUI reading) and verifying no data races occur via thread sanitizer or explicit interleaving tests.

**Acceptance Scenarios**:

1. **Given** a registered observer callback, **When** the engine triggers the callback, **Then** the callback receives an immutable snapshot of the state that cannot be modified by subsequent engine operations.
1. **Given** a simulation running in one thread, **When** the GUI requests a state snapshot from another thread, **Then** the snapshot is consistent (no partial updates visible).
1. **Given** a ProtocolObserverAdapter instance, **When** the engine completes a step, **Then** the adapter delivers a deep-copied, frozen snapshot to registered GUI callbacks.

______________________________________________________________________

### Edge Cases

- What happens when an observer callback raises an exception during notification?
  - Callback exceptions are logged but do not halt the simulation (consistent with existing ADR003 policy).
- What happens when `unregister_observer` is called with a callback that was never registered?
  - This is a no-op (no exception raised).
- What happens when `register_observer` is called with the same callback twice?
  - Treated as idempotent: callback is only invoked once per tick.
- What happens when spatial query is called during a step() operation from another thread?
  - ProtocolObserverAdapter handles synchronization; direct queries document thread-safety requirements.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: SimulationControl protocol MUST include a `register_observer(callback: Callable[[int, SimulationState], None])` method to register callbacks for state change notifications.
- **FR-002**: SimulationControl protocol MUST include an `unregister_observer(callback: Callable)` method to remove previously registered callbacks.
- **FR-003**: The simulation engine MUST invoke all registered observer callbacks at the end of every `step()` call, passing the current tick number and a reference to the SimulationState.
- **FR-004**: SimulationState protocol MUST include a `get_node_by_spatial_index(h3_index: str) -> TerritoryState | None` method to retrieve territory state by H3 hex index.
- **FR-005**: The `get_node_by_spatial_index` method MUST validate H3 index format and raise ValueError for invalid formats.
- **FR-006**: A ProtocolObserverAdapter class MUST be provided that implements the observer side of the protocol for GUI integration.
- **FR-007**: ProtocolObserverAdapter MUST deliver immutable, deep-copied state snapshots to registered GUI callbacks to prevent race conditions.
- **FR-008**: Observer callback exceptions MUST be logged but not propagate to halt simulation execution (consistent with ADR003).

### Key Entities

- **SimulationControl (Protocol)**: Extended protocol defining the write interface for simulation control, including observer registration.
- **SimulationState (Protocol)**: Extended protocol defining the read interface with spatial query capability.
- **ProtocolObserverAdapter**: New class that bridges the engine's observer notifications to thread-safe GUI callbacks.
- **TerritoryState (existing)**: The return type for spatial queries - represents a territory's state at a specific tick.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All registered observer callbacks receive notifications within the same tick boundary (before next `step()` begins).
- **SC-002**: 100% of valid H3 indices return the correct owning territory within a single method call.
- **SC-003**: GUI thread can safely read state snapshots while engine thread executes steps without data corruption or exceptions.
- **SC-004**: No simulation-halting exceptions occur when observer callbacks fail (graceful degradation).
- **SC-005**: Protocol extensions maintain backward compatibility - existing code using SimulationControl and SimulationState continues to work without modification.

## Assumptions

- **A1**: The GUI will use PyQt6, which has its own event loop that runs in the main thread or a dedicated GUI thread.
- **A2**: The existing `SimulationObserver` protocol (on_tick, on_simulation_start, on_simulation_end) will remain for AI/narrative observers, while the new callback-based registration is for GUI-specific lightweight notifications.
- **A3**: H3 indices use resolution 5 (15-character hex strings) as established in the existing HexState model.
- **A4**: The ProtocolObserverAdapter will use deep copy with frozen Pydantic models to ensure thread safety, leveraging the existing `frozen=True` configuration on snapshot types.
- **A5**: Duplicate callback registration is treated as idempotent (no error, callback only invoked once per tick).
