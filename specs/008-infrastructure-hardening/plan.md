# Implementation Plan: Infrastructure Hardening & Metrics Convergence

**Branch**: `008-infrastructure-hardening` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-infrastructure-hardening/spec.md`

## Summary

Eliminate the singleton pattern from `MetricsCollector`, integrate metrics into the `ServiceContainer` for dependency injection, add tick-context logging correlation to `SimulationEngine.run_tick()`, and delete confirmed dead code (`metrics/models.py`). This is infrastructure debt payment before Epoch 2 complexity.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x, NetworkX 3.x, SQLAlchemy 2.x (existing stack)
**Storage**: In-memory (MetricsCollector stores data in dicts, no persistence layer used currently)
**Testing**: pytest with existing 150+ tests
**Target Platform**: Linux (development), cross-platform Python
**Project Type**: Single project (monorepo structure)
**Performance Goals**: <5% degradation from logging context injection (SC-006)
**Constraints**: Hard removal of singleton (no deprecation period per clarification)
**Scale/Scope**: 5 legacy call sites to refactor (RAG module)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| II.5 AI Observes, Never Controls | ✅ PASS | Metrics/logging are observation infrastructure - they observe without controlling |
| II.6 State is Data, Engine is Transformation | ✅ PASS | ServiceContainer holds services (including metrics), not state. Metrics are infrastructure, not WorldState |
| III.1 No Magic Constants | ✅ PASS | No new constants introduced |
| VI.1 UI Observes, Never Controls | N/A | No UI changes in this spec |

**Gate Result**: PASS - proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/008-infrastructure-hardening/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal - no new data models)
├── quickstart.md        # Phase 1 output
├── checklists/          # Validation checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/babylon/
├── engine/
│   ├── services.py          # ADD: metrics field to ServiceContainer
│   └── simulation_engine.py # MODIFY: wrap run_tick() with log_context_scope
├── metrics/
│   ├── __init__.py          # MODIFY: update exports
│   ├── collector.py         # MODIFY: remove singleton pattern
│   ├── interfaces.py        # KEEP: already well-designed protocol
│   └── models.py            # DELETE: confirmed dead code
├── utils/
│   └── log.py               # KEEP: already has log_context_scope
└── rag/
    ├── embeddings.py                    # REFACTOR: accept collector via DI
    └── pre_embeddings/
        ├── manager.py                   # REFACTOR: accept collector via DI
        ├── cache_manager.py             # REFACTOR: accept collector via DI
        ├── preprocessor.py              # REFACTOR: accept collector via DI
        └── chunking.py                  # REFACTOR: accept collector via DI

tests/
├── unit/
│   ├── engine/
│   │   └── test_services.py  # ADD: tests for ServiceContainer.metrics
│   └── metrics/
│       └── test_collector.py # MODIFY: update for non-singleton behavior
└── integration/
    └── test_log_context.py   # ADD: verify tick correlation in logs
```

**Structure Decision**: Single project structure (Option 1). All changes are within existing `src/babylon/` hierarchy. No new directories needed.

## Complexity Tracking

> No violations to justify - design is simple DI refactoring.

## Phase 0: Research Findings

### R-001: Singleton Removal Strategy

**Decision**: Remove `__new__` override and `_instance` class variable entirely. No deprecation.

**Rationale**:
- Per clarification, hard removal is required (no deprecation period)
- 5 legacy call sites exist in RAG module - all must be refactored
- `_verify_protocol_conformance()` function in collector.py uses `MetricsCollector()` - this is a type-check helper, not production code

**Alternatives Considered**:
- DeprecationWarning fallback: Rejected per user clarification
- Gradual migration: Rejected per user clarification

### R-002: ServiceContainer Integration Pattern

**Decision**: Add `metrics: MetricsCollectorProtocol` field to ServiceContainer dataclass. Factory method `create()` instantiates real collector.

**Rationale**:
- Matches existing pattern for `config`, `database`, `event_bus`, `formulas`, `defines`
- Protocol type allows mock injection in tests
- Factory method encapsulates default construction

**Implementation**:
```python
@dataclass
class ServiceContainer:
    config: SimulationConfig
    database: DatabaseConnection
    event_bus: EventBus
    formulas: FormulaRegistry
    defines: GameDefines
    metrics: MetricsCollectorProtocol  # NEW
```

### R-003: Log Context Scope Integration

**Decision**: Wrap `run_tick()` body with `log_context_scope(tick=current_tick, correlation_id=uuid4())`.

**Rationale**:
- `log_context_scope` already exists in `src/babylon/utils/log.py`
- Uses `ContextVar` for thread-local storage - safe for async
- `ContextAwareFilter` already injects context into log records
- Per clarification, generate UUID per-tick

**Implementation Location**: `SimulationEngine.run_tick()` at lines 115-129

**Challenge**: `run_tick()` doesn't have direct access to tick number. Need to extract from context parameter or pass explicitly.

### R-004: RAG Module Refactoring

**Decision**: All 5 RAG classes that use `MetricsCollector()` must accept `MetricsCollectorProtocol` via constructor injection.

**Files to Modify**:
1. `src/babylon/rag/embeddings.py:114` - EmbeddingsManager class
2. `src/babylon/rag/pre_embeddings/manager.py:67` - PreEmbeddingsManager
3. `src/babylon/rag/pre_embeddings/cache_manager.py:51` - CacheManager
4. `src/babylon/rag/pre_embeddings/preprocessor.py:52` - Preprocessor
5. `src/babylon/rag/pre_embeddings/chunking.py:51` - ChunkingManager

**Pattern**: Add `metrics: MetricsCollectorProtocol | None = None` parameter, create real instance only if None.

### R-005: Dead Code Verification

**Decision**: Delete `src/babylon/metrics/models.py` entirely.

**Verification**:
- File defines `MetricsBase`, `Metric`, `Counter`, `TimeSeries` SQLAlchemy models
- Grep confirms no imports of `from babylon.metrics.models` anywhere in codebase
- Models were for planned database persistence that was never implemented
- No tests reference these models

**Risk**: None - confirmed unused

## Phase 1: Design & Contracts

### Data Model Changes

**No new data models required.**

The only changes are:
1. Adding a field to existing `ServiceContainer` dataclass
2. Removing singleton pattern from existing `MetricsCollector` class
3. Deleting unused `models.py`

### API/Contract Changes

**ServiceContainer.create() Signature Change**:

```python
# Before
@classmethod
def create(
    cls,
    config: SimulationConfig | None = None,
    defines: GameDefines | None = None,
) -> "ServiceContainer":

# After
@classmethod
def create(
    cls,
    config: SimulationConfig | None = None,
    defines: GameDefines | None = None,
    metrics: MetricsCollectorProtocol | None = None,  # NEW
) -> "ServiceContainer":
```

**MetricsCollector Class Change**:

```python
# Before: Singleton pattern
class MetricsCollector:
    _instance: MetricsCollector | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

# After: Normal instantiation
class MetricsCollector:
    # Remove _instance, _lock, __new__
    # Keep _initialized guard in __init__ for defensive re-init protection
```

**SimulationEngine.run_tick() Change**:

```python
# Before
def run_tick(
    self,
    graph: nx.DiGraph[str],
    services: ServiceContainer,
    context: ContextType,
) -> None:
    for system in self._systems:
        system.step(graph, services, context)

# After
def run_tick(
    self,
    graph: nx.DiGraph[str],
    services: ServiceContainer,
    context: ContextType,
) -> None:
    from uuid import uuid4
    from babylon.utils.log import log_context_scope

    tick = context.tick if hasattr(context, 'tick') else context.get('tick', 0)
    correlation_id = str(uuid4())

    with log_context_scope(tick=tick, correlation_id=correlation_id):
        for system in self._systems:
            system.step(graph, services, context)
```

### Quickstart

See `quickstart.md` for developer onboarding with the new patterns.

## Implementation Phases

### Phase A: Core Infrastructure (P1 - DI Metrics)

1. **Remove singleton from MetricsCollector** (`collector.py`)
   - Delete `_instance`, `_lock`, `__new__`
   - Keep `_initialized` guard in `__init__` for safety
   - Update `_verify_protocol_conformance()` - may need adjustment

2. **Add metrics to ServiceContainer** (`services.py`)
   - Add `metrics: MetricsCollectorProtocol` field
   - Update `create()` factory to accept and instantiate metrics
   - Import MetricsCollector in create() to avoid circular imports

3. **Write tests for new ServiceContainer behavior** (`test_services.py`)
   - Test: `container.metrics` returns valid collector
   - Test: Two containers have independent collectors
   - Test: Mock injection works

### Phase B: Logging Context (P2 - Tick Correlation)

4. **Integrate log_context_scope in run_tick()** (`simulation_engine.py`)
   - Add imports for `uuid4` and `log_context_scope`
   - Extract tick number from context
   - Generate per-tick UUID
   - Wrap system execution in context scope

5. **Write integration tests for log context** (`test_log_context.py`)
   - Test: Logs within run_tick contain tick number
   - Test: Logs within run_tick contain correlation_id
   - Test: Each tick has unique correlation_id

### Phase C: RAG Module Refactoring (P1 continuation)

6. **Refactor RAG classes for DI** (5 files)
   - Add `metrics: MetricsCollectorProtocol | None = None` to constructors
   - Default to creating MetricsCollector() if None (for backward compat during transition)
   - Update any places that instantiate these classes

7. **Update RAG tests** (if any exist)
   - Verify tests can inject mock collectors

### Phase D: Cleanup (P3 - Dead Code)

8. **Delete dead code**
   - Delete `src/babylon/metrics/models.py`
   - Update `metrics/__init__.py` if needed
   - Verify no broken imports

9. **Analyze unused getter methods in MetricsCollector**
   - Check if `get_counter`, `get_gauge`, `get_timer_stats`, `get_metrics` are used
   - Remove if unused, document if kept

### Phase E: Verification

10. **Run full test suite**
    - All 150+ tests must pass
    - No regression in existing functionality

11. **Performance benchmark** (required for SC-006)
    - **Baseline measurement**: Run `mise run sim:profile` with 100-tick simulation BEFORE adding log context
    - **Post-change measurement**: Run same benchmark AFTER adding log_context_scope to run_tick()
    - **Calculation**: degradation = (post_time - baseline_time) / baseline_time × 100%
    - **Pass criterion**: degradation < 5%

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run tests after each phase |
| Circular imports | Import MetricsCollector lazily in ServiceContainer.create() |
| Missing tick in context | Add fallback to 0, log warning |
| RAG module not actively tested | Careful refactoring, preserve backward compat |

## Success Verification Checklist

- [ ] `ServiceContainer.create().metrics` returns valid collector (SC-001)
- [ ] Two containers have independent metrics (SC-002)
- [ ] Logs within run_tick() have tick + correlation_id (SC-003)
- [ ] `src/babylon/metrics/models.py` deleted (SC-004)
- [ ] All tests pass (SC-005)
- [ ] Performance <5% degradation via `mise run sim:profile` baseline comparison (SC-006)
- [ ] MetricsCollectorProtocol defines all required methods (SC-007)
- [ ] No direct `MetricsCollector()` calls remain in RAG module (SC-008)
- [ ] Unused getter methods removed or documented as required (SC-009)
