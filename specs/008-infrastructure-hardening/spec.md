# Feature Specification: Infrastructure Hardening & Metrics Convergence

**Feature Branch**: `008-infrastructure-hardening`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Eliminate MetricsCollector singleton pattern, clean up dead code in metrics module, enforce strict tick-context logging correlation across the simulation engine. Pay down technical debt before Epoch 2 complexity."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dependency-Injected Metrics (Priority: P1)

As a simulation developer, I want to access the metrics collector via the ServiceContainer, so that I can easily mock telemetry in tests and avoid global state side-effects.

**Why this priority**: The singleton pattern currently violates our DI architecture and makes testing difficult. This is the core architectural fix that unblocks all other improvements.

**Independent Test**: Can be fully tested by creating a ServiceContainer instance and verifying `container.metrics` returns a valid collector that can record metrics without any global state.

**Acceptance Scenarios**:

1. **Given** a fresh ServiceContainer created via `ServiceContainer.create()`, **When** I access `container.metrics`, **Then** I receive a valid MetricsCollectorProtocol implementation that can record metrics.
2. **Given** two separate ServiceContainer instances, **When** I record metrics to each, **Then** the metrics remain isolated between containers (no shared state).
3. **Given** a test environment, **When** I create a ServiceContainer with a mock metrics collector, **Then** the mock is used instead of the real implementation.

______________________________________________________________________

### User Story 2 - Context-Aware Logging (Priority: P2)

As a debugger, I need every log message generated during a simulation tick to include `tick=N` and a correlation_id, so that I can trace the exact sequence of events across multiple systems without guessing.

**Why this priority**: Once metrics are properly injected, the logging context becomes essential for debugging multi-system interactions. This builds on the P1 infrastructure.

**Independent Test**: Can be fully tested by running a simulation tick and capturing log output, then verifying every log line contains the expected tick number.

**Acceptance Scenarios**:

1. **Given** a simulation at tick 5, **When** any system emits a log message during `run_tick()`, **Then** the log message includes `"tick": 5` in its context.
2. **Given** a simulation spanning multiple ticks, **When** I filter logs by tick number, **Then** I see only events from that specific tick.
3. **Given** nested function calls during a tick, **When** each function logs, **Then** all logs inherit the tick context automatically.

______________________________________________________________________

### User Story 3 - Dead Code Elimination (Priority: P3)

As a maintainer, I want unused ORM models and legacy methods removed, so that the codebase remains lean and less confusing for new contributors.

**Why this priority**: This is cleanup work that reduces cognitive overhead but doesn't affect runtime behavior. Can be done after core functionality is fixed.

**Independent Test**: Can be fully tested by verifying the deleted files no longer exist and all tests still pass.

**Acceptance Scenarios**:

1. **Given** the file `src/babylon/metrics/models.py`, **When** the cleanup is complete, **Then** the file no longer exists.
2. **Given** unused getter methods in MetricsCollector, **When** the cleanup is complete, **Then** only actively-used methods remain.
3. **Given** the cleaned codebase, **When** I run the full test suite, **Then** all tests pass without import errors.

______________________________________________________________________

### Edge Cases

- **Legacy global usage**: Existing code (especially in RAG module) that imports `MetricsCollector()` directly MUST be refactored to accept the container or a collector instance as part of this spec. No deprecation period.
- **Performance impact**: High-frequency logging with context injection must not degrade simulation speed by more than 5%.
- **Incomplete tick context**: Log messages emitted outside of `run_tick()` (e.g., during initialization) should still function normally, just without tick context.
- **Thread safety**: MetricsCollector is NOT thread-safe after singleton removal. Each ServiceContainer instance MUST have its own MetricsCollector instance. Concurrent access from multiple threads to the same collector instance is not supported and not required (simulation runs single-threaded).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `ServiceContainer` (src/babylon/engine/services.py) MUST include a `metrics` field of type `MetricsCollectorProtocol`.
- **FR-002**: The `MetricsCollector` class MUST be instantiable without singleton behavior, allowing normal construction via `ServiceContainer.create()`.
- **FR-003**: The `MetricsCollectorProtocol` (src/babylon/metrics/interfaces.py) MUST define a minimal interface that the implementation satisfies, preferring generic `record(name, value, tags={...})` over specialized methods.
- **FR-004**: The `SimulationEngine.run_tick()` method MUST wrap its execution in `log_context_scope(tick=current_tick, correlation_id=uuid)` from `src/babylon/utils/log.py`, generating a new UUID for each tick.
- **FR-005**: All log messages emitted within the `log_context_scope` MUST automatically include both the tick number and correlation_id (UUID) in structured log output.
- **FR-006**: The file `src/babylon/metrics/models.py` MUST be deleted (confirmed dead code).
- **FR-007**: Unused getter methods in `MetricsCollector` (`get_counter`, `get_gauge`, etc.) MUST be removed unless proven necessary for the Dashboard.
- **FR-008**: All legacy code that uses `MetricsCollector()` directly MUST be refactored to use ServiceContainer injection as part of this spec (no deprecation period).

### Key Entities

- **ServiceContainer**: The central dependency injection container that provides access to all simulation services including the new metrics field.
- **MetricsCollectorProtocol**: The interface defining metrics recording capabilities, simplified to use generic recording methods.
- **MetricsCollector**: The concrete implementation of the protocol, now instantiable without singleton constraints.
- **log_context_scope**: A context manager that injects tick number and a per-tick UUID correlation_id into all logs within its scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `ServiceContainer.create().metrics` returns a valid collector (verified via unit test).
- **SC-002**: Creating two ServiceContainer instances results in two independent metrics collectors (no shared state).
- **SC-003**: Running a simulation generates logs where 100% of messages within `run_tick()` contain both `"tick": N` and a unique `"correlation_id": <UUID>` per tick.
- **SC-004**: The file `src/babylon/metrics/models.py` does not exist after cleanup.
- **SC-005**: All 150+ existing tests pass with the refactored container.
- **SC-006**: Simulation performance degradation from logging context injection is less than 5% (measured via `mise run sim:profile` with 100-tick baseline).
- **SC-007**: `MetricsCollectorProtocol` defines all methods required by `MetricsCollector` implementation (verified via T006-T007).
- **SC-008**: No direct `MetricsCollector()` calls remain in `src/babylon/rag/` after refactoring (verified via grep).
- **SC-009**: Unused getter methods are removed OR documented as required for Dashboard (verified via T039 analysis).

## Clarifications

### Session 2026-01-31

- Q: What is the deprecation timeline for legacy singleton usage? → A: Hard removal now (break legacy callers immediately)
- Q: How is correlation_id generated for tick logging? → A: Generate UUID per-tick (unique per run_tick call)

## Out of Scope

- Building a new Dashboard UI for these metrics (this spec fixes the backend pipe only).
- Altering `TickStateRecorder` logic (that is for game state history, separate from system telemetry).
- Changing the fundamental metrics storage or export format.

## Assumptions

- The `log_context_scope` utility already exists in `src/babylon/utils/log.py` and provides the necessary context injection mechanism.
- The Dashboard (if it uses getter methods) can be updated in a follow-up spec if needed.
- RAG module refactoring for DI compliance will be completed as part of this spec (hard removal, no deprecation period).
