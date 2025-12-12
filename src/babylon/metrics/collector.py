"""Metrics collection system for Babylon/Babylon.

The MetricsCollector observes the simulation without interfering.
It is the Party's Central Statistical Bureau - recording material
conditions for analysis by the planning committee.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.config.base import BaseConfig

if TYPE_CHECKING:
    from babylon.metrics.interfaces import MetricsCollectorProtocol

logger = logging.getLogger(__name__)


class MetricEvent(BaseModel):
    """A single metric measurement.

    Immutable record of a moment in the simulation's history.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    """Centralized metrics collection and aggregation.

    This class implements the Singleton pattern to ensure a single
    source of truth for all metrics across the simulation.

    The collector is thread-safe for concurrent metric recording.

    Metrics Categories:
    - performance: Timing, throughput, latency
    - simulation: Game state metrics (P(S|A), P(S|R), Rent flow)
    - cache: Hit rates, evictions, memory usage
    - embedding: Generation times, batch sizes, errors
    """

    _instance: MetricsCollector | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> MetricsCollector:
        """Implement singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        if getattr(self, "_initialized", False):
            return

        self._metrics: dict[str, list[MetricEvent]] = {}
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, list[float]] = {}
        self._enabled: bool = BaseConfig.METRICS_ENABLED
        self._data_lock = threading.Lock()
        self._initialized = True

        logger.debug("MetricsCollector initialized (enabled=%s)", self._enabled)

    @property
    def enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self._enabled

    def record(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value.

        Args:
            name: Metric name (e.g., "simulation.p_revolution")
            value: Numeric value
            tags: Key-value pairs for filtering/grouping
            metadata: Additional context
        """
        if not self._enabled:
            return

        event = MetricEvent(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {},
        )

        with self._data_lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(event)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name
            value: Amount to increment
        """
        if not self._enabled:
            return

        with self._data_lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge metric to a specific value.

        Args:
            name: Gauge name
            value: Current value
        """
        if not self._enabled:
            return

        with self._data_lock:
            self._gauges[name] = value

    def time(self, name: str) -> TimerContext:
        """Context manager for timing operations.

        Args:
            name: Timer name

        Returns:
            TimerContext that records duration on exit

        Example:
            with collector.time("embedding.generation"):
                embeddings = generate_embeddings(texts)
        """
        return TimerContext(self, name)

    def record_timing(self, name: str, duration: float) -> None:
        """Record a timing measurement directly.

        Args:
            name: Timer name
            duration: Duration in seconds
        """
        if not self._enabled:
            return

        with self._data_lock:
            if name not in self._timers:
                self._timers[name] = []
            self._timers[name].append(duration)

    def record_metric(
        self,
        name: str,
        value: float,
        context: str = "",
        object_id: str | None = None,
        context_level: str | None = None,
    ) -> None:
        """Record a named metric with context.

        Args:
            name: Metric name
            value: Metric value
            context: Optional context string
            object_id: Optional object identifier
            context_level: Optional context level
        """
        tags: dict[str, str] = {}
        if context:
            tags["context"] = context
        if object_id:
            tags["object_id"] = object_id
        if context_level:
            tags["context_level"] = context_level
        self.record(name, value, tags=tags)

    def record_cache_event(self, level: str, hit: bool) -> None:
        """Record a cache hit or miss event.

        Args:
            level: Cache level (e.g., "L1", "L2", "embedding")
            hit: Whether this was a cache hit (True) or miss (False)
        """
        event_name = f"cache.{level}.{'hit' if hit else 'miss'}"
        self.increment(event_name)

    def record_token_usage(self, tokens: int) -> None:
        """Record token usage.

        Args:
            tokens: Number of tokens used
        """
        self.record("token_usage", float(tokens))

    def record_memory_usage(self, memory_bytes: float) -> None:
        """Record memory usage.

        Args:
            memory_bytes: Memory usage in bytes
        """
        self.record("memory_usage", memory_bytes)

    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        with self._data_lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float | None:
        """Get current gauge value."""
        with self._data_lock:
            return self._gauges.get(name)

    def get_timer_stats(self, name: str) -> dict[str, float]:
        """Get statistics for a timer.

        Returns:
            Dict with count, sum, mean, min, max
        """
        with self._data_lock:
            timings = self._timers.get(name, [])

        if not timings:
            return {"count": 0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

        return {
            "count": len(timings),
            "sum": sum(timings),
            "mean": sum(timings) / len(timings),
            "min": min(timings),
            "max": max(timings),
        }

    def get_metrics(self, name: str, limit: int = 100) -> list[MetricEvent]:
        """Get recent metric events.

        Args:
            name: Metric name
            limit: Maximum number of events to return

        Returns:
            List of recent MetricEvent objects
        """
        with self._data_lock:
            events = self._metrics.get(name, [])
            return events[-limit:]

    def clear(self) -> None:
        """Clear all collected metrics.

        Used primarily for testing or resetting between game sessions.
        """
        with self._data_lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()

        logger.debug("MetricsCollector cleared")

    def summary(self) -> dict[str, Any]:
        """Get a summary of all collected metrics.

        Returns:
            Dict with counters, gauges, and timer statistics
        """
        with self._data_lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers": {name: self.get_timer_stats(name) for name in self._timers},
                "metric_series_count": len(self._metrics),
                "total_events": sum(len(events) for events in self._metrics.values()),
            }


class TimerContext:
    """Context manager for timing code blocks."""

    def __init__(self, collector: MetricsCollector, name: str) -> None:
        self.collector = collector
        self.name = name
        self.start_time: float = 0.0

    def __enter__(self) -> TimerContext:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        duration = time.perf_counter() - self.start_time
        self.collector.record_timing(self.name, duration)


# Type check: verify MetricsCollector implements the protocol
def _verify_protocol_conformance() -> MetricsCollectorProtocol:
    """Verify MetricsCollector implements MetricsCollectorProtocol.

    This function is never called at runtime - it exists purely for
    static type checking to ensure the class conforms to the protocol.

    Returns:
        A MetricsCollector instance typed as the protocol.
    """
    from babylon.metrics.interfaces import (
        MetricsCollectorProtocol as Protocol,
    )

    collector: Protocol = MetricsCollector()
    return collector
