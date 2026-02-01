# Data Model: Infrastructure Hardening & Metrics Convergence

**Feature**: 008-infrastructure-hardening
**Date**: 2026-01-31

## Summary

This feature introduces **no new data models**. It modifies existing infrastructure:

1. **ServiceContainer** - Add `metrics` field
2. **MetricsCollector** - Remove singleton pattern
3. **models.py** - Delete (dead code)

## Entity Changes

### ServiceContainer (Modified)

**Location**: `src/babylon/engine/services.py`

**Change**: Add `metrics` field

```python
@dataclass
class ServiceContainer:
    config: SimulationConfig
    database: DatabaseConnection
    event_bus: EventBus
    formulas: FormulaRegistry
    defines: GameDefines
    metrics: MetricsCollectorProtocol  # NEW FIELD
```

**Relationships**:
- Used by: `SimulationEngine`, all Systems, RAG components
- Contains: All simulation services including new metrics field

### MetricsCollector (Modified)

**Location**: `src/babylon/metrics/collector.py`

**Change**: Remove singleton pattern

**Before**:
```python
class MetricsCollector:
    _instance: MetricsCollector | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> MetricsCollector:
        # Singleton enforcement
```

**After**:
```python
class MetricsCollector:
    # Normal class - no singleton
    def __init__(self) -> None:
        # Standard initialization
```

**Relationships**:
- Implements: `MetricsCollectorProtocol`
- Used by: `ServiceContainer.create()` (default instantiation)

### models.py (Deleted)

**Location**: `src/babylon/metrics/models.py`

**Status**: DELETE ENTIRELY

**Contents** (for reference):
- `MetricsBase` - SQLAlchemy declarative base
- `Metric` - ORM model for metric records
- `Counter` - ORM model for counters
- `TimeSeries` - ORM model for time-series data

**Reason**: Unused dead code. No imports found in codebase.

## No New Entities

This is an infrastructure refactoring spec. The goal is to:
1. Improve testability via DI
2. Add logging context correlation
3. Remove dead code

No new domain entities are introduced.

## State Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ServiceContainer                          │
├─────────────────────────────────────────────────────────────┤
│  config: SimulationConfig                                    │
│  database: DatabaseConnection                                │
│  event_bus: EventBus                                         │
│  formulas: FormulaRegistry                                   │
│  defines: GameDefines                                        │
│  metrics: MetricsCollectorProtocol  ◄── NEW                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ create()
                          ▼
              ┌───────────────────────┐
              │   MetricsCollector    │
              │   (no longer singleton)│
              └───────────────────────┘
```

## Migration Notes

### For Existing Code

Replace:
```python
from babylon.metrics.collector import MetricsCollector
collector = MetricsCollector()  # Singleton access
```

With:
```python
# If you have access to ServiceContainer
container.metrics.record(...)

# If you need standalone collector (tests)
from babylon.metrics.collector import MetricsCollector
collector = MetricsCollector()  # Creates NEW instance
```

### For Tests

```python
from unittest.mock import MagicMock
mock_metrics = MagicMock(spec=MetricsCollectorProtocol)
container = ServiceContainer.create(metrics=mock_metrics)
```
