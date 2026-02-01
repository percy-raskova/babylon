# Quickstart: Infrastructure Hardening Patterns

**Feature**: 008-infrastructure-hardening
**Date**: 2026-01-31

This guide covers the new patterns introduced by the Infrastructure Hardening spec.

## 1. Accessing Metrics via ServiceContainer

### Before (Singleton - DEPRECATED)
```python
from babylon.metrics.collector import MetricsCollector

# DON'T DO THIS - singleton pattern removed
collector = MetricsCollector()
collector.record("my_metric", 42.0)
```

### After (Dependency Injection)
```python
from babylon.engine.services import ServiceContainer

# Create container with metrics
container = ServiceContainer.create()

# Access metrics through container
container.metrics.record("my_metric", 42.0)
container.metrics.increment("event_count")
with container.metrics.time("operation"):
    # ... timed operation ...
```

### In Tests (Mock Injection)
```python
from unittest.mock import MagicMock
from babylon.metrics.interfaces import MetricsCollectorProtocol

def test_with_mock_metrics():
    mock_metrics = MagicMock(spec=MetricsCollectorProtocol)
    container = ServiceContainer.create(metrics=mock_metrics)

    # Run code that uses metrics
    some_function(container)

    # Verify metrics were recorded
    mock_metrics.record.assert_called_with("expected_metric", 100.0)
```

## 2. Tick-Context Logging

All log messages within `SimulationEngine.run_tick()` automatically include:
- `tick`: Current simulation tick number
- `correlation_id`: Unique UUID for this tick

### Viewing Context in Logs
```json
{
    "ts": "2026-01-31T15:30:00.000Z",
    "level": "INFO",
    "logger": "babylon.engine.systems.economic",
    "msg": "Extracted 42.5 imperial rent",
    "tick": 5,
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Filtering by Tick
```bash
# Find all logs for tick 5
cat simulation.log | jq 'select(.tick == 5)'

# Find all logs for a specific correlation
cat simulation.log | jq 'select(.correlation_id == "550e8400-...")'
```

### Adding Custom Context
```python
from babylon.utils.log import log_context_scope

# Add additional context within your code
with log_context_scope(system="economic", phase="extraction"):
    logger.info("Processing extraction")  # Includes tick + correlation_id + custom fields
```

## 3. MetricsCollector API

The `MetricsCollectorProtocol` defines the standard interface:

```python
from babylon.metrics.interfaces import MetricsCollectorProtocol

class MetricsCollectorProtocol(Protocol):
    def record(self, name: str, value: float,
               tags: dict[str, str] | None = None,
               metadata: dict[str, Any] | None = None) -> None:
        """Record a metric value."""

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""

    def time(self, name: str) -> AbstractContextManager[Any]:
        """Context manager for timing operations."""

    def summary(self) -> dict[str, Any]:
        """Get aggregated summary of all metrics."""

    def clear(self) -> None:
        """Clear all recorded metrics."""
```

## 4. Refactoring Legacy Code

If you have code that uses `MetricsCollector()` directly:

### Step 1: Update Constructor
```python
# Before
class MyService:
    def __init__(self):
        self.metrics = MetricsCollector()

# After
from babylon.metrics.interfaces import MetricsCollectorProtocol

class MyService:
    def __init__(self, metrics: MetricsCollectorProtocol | None = None):
        from babylon.metrics.collector import MetricsCollector
        self.metrics = metrics if metrics is not None else MetricsCollector()
```

### Step 2: Pass Metrics from Container
```python
# When instantiating
container = ServiceContainer.create()
service = MyService(metrics=container.metrics)
```

## 5. Creating a Test Spy

For tests that need to inspect recorded metrics:

```python
from babylon.metrics.interfaces import MetricsCollectorProtocol
from contextlib import contextmanager
from typing import Any

class MetricsSpy:
    """Test spy that records all metric calls."""

    def __init__(self):
        self.records: list[tuple[str, float, dict]] = []
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        self.timings: list[tuple[str, float]] = []

    def record(self, name: str, value: float,
               tags: dict[str, str] | None = None,
               metadata: dict[str, Any] | None = None) -> None:
        self.records.append((name, value, tags or {}))

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    @contextmanager
    def time(self, name: str):
        import time
        start = time.perf_counter()
        yield
        self.timings.append((name, time.perf_counter() - start))

    def summary(self) -> dict[str, Any]:
        return {"records": len(self.records), "counters": self.counters}

    def clear(self) -> None:
        self.records.clear()
        self.counters.clear()
        self.gauges.clear()
        self.timings.clear()

# Usage
def test_something():
    spy = MetricsSpy()
    container = ServiceContainer.create(metrics=spy)

    run_simulation(container)

    assert spy.counters["ticks_completed"] == 10
    assert any(name == "imperial_rent" for name, _, _ in spy.records)
```

## Summary

| Pattern | Old Way | New Way |
|---------|---------|---------|
| Get metrics | `MetricsCollector()` | `container.metrics` |
| Inject in tests | Not possible | `ServiceContainer.create(metrics=mock)` |
| Log tick context | Manual | Automatic in `run_tick()` |
| Debug by tick | Grep timestamps | Filter by `tick` field |
