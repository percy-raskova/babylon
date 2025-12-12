"""Mock metrics collector for testing - implements pure spy pattern.

This is a "Dumb Spy" that only records what methods were called and with
what arguments. It does NOT calculate statistics - that logic belongs
in the production MetricsCollector only.

The spy pattern ensures:
1. Tests verify what was recorded, not derived calculations
2. No duplication of business logic in test doubles
3. Clear separation between recording and analysis
"""

from __future__ import annotations

import warnings
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


class MockMetricsCollector:
    """Mock metrics collector for testing - pure spy implementation.

    This spy records all metric calls without performing any calculations.
    Use get_recorded_data() to inspect what was recorded during a test.

    Note:
        This class intentionally does NOT implement MetricsCollectorProtocol
        because it provides additional test-specific methods (record_object_access,
        record_query_latency, etc.) that are not part of the protocol.

    Example:
        >>> collector = MockMetricsCollector()
        >>> collector.record_cache_event("L1", hit=True)
        >>> collector.record_cache_event("L1", hit=False)
        >>> data = collector.get_recorded_data()
        >>> assert data["cache_hits"]["L1"] == 1
        >>> assert data["cache_misses"]["L1"] == 1
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        """Initialize the spy collector.

        Args:
            log_dir: Optional log directory (kept for API compatibility).
        """
        self.log_dir = log_dir
        self.current_session: dict[str, Any] = {
            "start_time": datetime.now(),
            "total_objects": 0,
            "active_objects": 0,
            "cached_objects": 0,
        }
        self.metrics: dict[str, Any] = {
            "object_access": Counter(),
            "token_usage": [],
            "cache_performance": {"hits": Counter(), "misses": Counter()},
            "latency": {"db_queries": [], "context_switches": []},
            "memory_usage": [],
            "errors": Counter(),
            "failed_operations": [],
            "contradiction_tracking": {"total": 0, "active": 0},
        }

        # Initialize default cache levels
        self.metrics["cache_performance"]["hits"]["L1"] = 0
        self.metrics["cache_performance"]["hits"]["L2"] = 0
        self.metrics["cache_performance"]["misses"]["L1"] = 0
        self.metrics["cache_performance"]["misses"]["L2"] = 0

        # Track protocol-compatible calls for inspection
        self._recorded_calls: list[dict[str, Any]] = []

    def record_object_access(self, object_id: str, context: str) -> None:
        """Record an object access.

        Args:
            object_id: Identifier of the accessed object.
            context: Context of the access (e.g., "contradiction_system").
        """
        self.metrics["object_access"][object_id] += 1
        self.current_session["total_objects"] += 1
        if context == "contradiction_system":
            self.metrics["contradiction_tracking"]["total"] += 1

    def record_metric(
        self,
        name: str,
        value: float,
        context: str = "",
        object_id: str | None = None,
        context_level: str | None = None,
    ) -> None:
        """Record a metric.

        Args:
            name: Metric name.
            value: Metric value (recorded but not used for calculations).
            context: Optional context string.
            object_id: Optional object identifier.
            context_level: Optional context level.
        """
        # Track the call for inspection
        self._recorded_calls.append(
            {
                "method": "record_metric",
                "name": name,
                "value": value,
                "context": context,
                "object_id": object_id,
                "context_level": context_level,
            }
        )

        if name.startswith("error:") or name == "error":
            self.metrics["errors"][context] += 1
            self.metrics["failed_operations"].append(context)
        if object_id:
            self.record_object_access(object_id, context_level or "")

    def record_cache_event(self, level: str, hit: bool) -> None:
        """Record a cache hit or miss.

        Args:
            level: Cache level (e.g., "L1", "L2").
            hit: True for cache hit, False for cache miss.
        """
        if hit:
            self.metrics["cache_performance"]["hits"][level] += 1
        else:
            self.metrics["cache_performance"]["misses"][level] += 1

    def record_token_usage(self, tokens: int) -> None:
        """Record token usage.

        Args:
            tokens: Number of tokens used.
        """
        self.metrics["token_usage"].append(tokens)

    def record_query_latency(self, latency: float) -> None:
        """Record query latency.

        Args:
            latency: Query latency in seconds.
        """
        self.metrics["latency"]["db_queries"].append(latency)

    def record_context_switch(self, latency: float) -> None:
        """Record context switch latency.

        Args:
            latency: Context switch latency in seconds.
        """
        self.metrics["latency"]["context_switches"].append(latency)

    def record_memory_usage(self, memory_mb: float) -> None:
        """Record memory usage.

        Args:
            memory_mb: Memory usage in megabytes.
        """
        self.metrics["memory_usage"].append(memory_mb)

    # -------------------------------------------------------------------------
    # Protocol-compatible methods (for drop-in replacement scenarios)
    # -------------------------------------------------------------------------

    def record(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value (protocol-compatible).

        Args:
            name: Metric name.
            value: Numeric value.
            tags: Optional key-value pairs.
            metadata: Optional additional context.
        """
        self._recorded_calls.append(
            {
                "method": "record",
                "name": name,
                "value": value,
                "tags": tags,
                "metadata": metadata,
            }
        )

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter (protocol-compatible).

        Args:
            name: Counter name.
            value: Amount to increment.
        """
        self._recorded_calls.append({"method": "increment", "name": name, "value": value})

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge value (protocol-compatible).

        Args:
            name: Gauge name.
            value: Current value.
        """
        self._recorded_calls.append({"method": "gauge", "name": name, "value": value})

    @contextmanager
    def time(self, name: str) -> Iterator[None]:
        """Context manager for timing operations (protocol-compatible).

        Note: This spy does NOT actually time anything - it just records
        that the timing context was entered and exited.

        Args:
            name: Timer name.

        Yields:
            None
        """
        self._recorded_calls.append({"method": "time_enter", "name": name})
        try:
            yield
        finally:
            self._recorded_calls.append({"method": "time_exit", "name": name})

    def summary(self) -> dict[str, Any]:
        """Get summary of recorded data (protocol-compatible).

        Returns:
            Raw recorded data without calculations.
        """
        return self.get_recorded_data()

    def clear(self) -> None:
        """Clear all recorded metrics (protocol-compatible)."""
        self.metrics = {
            "object_access": Counter(),
            "token_usage": [],
            "cache_performance": {"hits": Counter(), "misses": Counter()},
            "latency": {"db_queries": [], "context_switches": []},
            "memory_usage": [],
            "errors": Counter(),
            "failed_operations": [],
            "contradiction_tracking": {"total": 0, "active": 0},
        }
        self._recorded_calls.clear()
        self.current_session["total_objects"] = 0
        self.current_session["active_objects"] = 0
        self.current_session["cached_objects"] = 0

    # -------------------------------------------------------------------------
    # Spy-specific methods for test assertions
    # -------------------------------------------------------------------------

    def get_recorded_data(self) -> dict[str, Any]:
        """Return raw recorded data without calculations.

        This is the spy pattern - we only record what was called,
        we don't calculate statistics. Calculation logic belongs
        in the production MetricsCollector, not in test doubles.

        Returns:
            Dictionary with raw recorded values:
            - object_access: Counter of object accesses by ID
            - token_usage: List of token usage values
            - cache_hits: Counter of cache hits by level
            - cache_misses: Counter of cache misses by level
            - memory_usage: List of memory usage values
            - latency_db_queries: List of query latencies
            - latency_context_switches: List of context switch latencies
            - errors: Counter of errors by type
            - failed_operations: List of failed operation contexts
            - contradiction_tracking: Dict with total and active counts
        """
        return {
            "object_access": dict(self.metrics["object_access"]),
            "token_usage": list(self.metrics["token_usage"]),
            "cache_hits": dict(self.metrics["cache_performance"]["hits"]),
            "cache_misses": dict(self.metrics["cache_performance"]["misses"]),
            "memory_usage": list(self.metrics["memory_usage"]),
            "latency_db_queries": list(self.metrics["latency"]["db_queries"]),
            "latency_context_switches": list(self.metrics["latency"]["context_switches"]),
            "errors": dict(self.metrics["errors"]),
            "failed_operations": list(self.metrics["failed_operations"]),
            "contradiction_tracking": dict(self.metrics["contradiction_tracking"]),
        }

    def get_protocol_calls(self) -> list[dict[str, Any]]:
        """Return list of all protocol-compatible method calls.

        Useful for verifying the exact sequence of calls made.

        Returns:
            List of call records with method name and arguments.
        """
        return list(self._recorded_calls)

    def analyze_performance(self) -> dict[str, Any]:
        """DEPRECATED: Use get_recorded_data() instead.

        This method previously calculated statistics but now returns raw data.
        Tests should check recorded values directly rather than derived stats.

        Returns:
            Raw recorded data (same as get_recorded_data()).
        """
        warnings.warn(
            "analyze_performance() is deprecated, use get_recorded_data() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_recorded_data()


# =============================================================================
# Self-contained tests (run with: pytest tests/mocks/metrics_collector.py -v)
# =============================================================================


def test_mock_metrics_collector_initialization() -> None:
    """Test that the collector initializes with correct default state."""
    collector = MockMetricsCollector()
    assert isinstance(collector.metrics["object_access"], Counter)
    assert isinstance(collector.metrics["token_usage"], list)
    assert collector.metrics["cache_performance"]["hits"]["L1"] == 0
    assert collector.metrics["cache_performance"]["hits"]["L2"] == 0
    assert collector.metrics["cache_performance"]["misses"]["L1"] == 0
    assert collector.metrics["cache_performance"]["misses"]["L2"] == 0


def test_record_object_access() -> None:
    """Test that object accesses are recorded correctly."""
    collector = MockMetricsCollector()
    collector.record_object_access("obj1", "test")
    collector.record_object_access("obj1", "test")
    collector.record_object_access("obj2", "test")

    assert collector.metrics["object_access"]["obj1"] == 2
    assert collector.metrics["object_access"]["obj2"] == 1


def test_record_cache_events() -> None:
    """Test that cache events are recorded correctly."""
    collector = MockMetricsCollector()
    collector.record_cache_event("L1", hit=True)
    collector.record_cache_event("L1", hit=False)
    collector.record_cache_event("L2", hit=True)

    assert collector.metrics["cache_performance"]["hits"]["L1"] == 1
    assert collector.metrics["cache_performance"]["misses"]["L1"] == 1
    assert collector.metrics["cache_performance"]["hits"]["L2"] == 1
    assert collector.metrics["cache_performance"]["misses"]["L2"] == 0


def test_get_recorded_data() -> None:
    """Test the spy returns raw recorded data without calculations."""
    collector = MockMetricsCollector()

    # Record various metrics
    collector.record_object_access("OBJ001", "contradiction_system")
    collector.record_object_access("OBJ001", "regular")
    collector.record_cache_event("L1", hit=True)
    collector.record_cache_event("L1", hit=False)
    collector.record_token_usage(100)
    collector.record_token_usage(200)
    collector.record_query_latency(0.1)
    collector.record_query_latency(0.3)
    collector.record_memory_usage(50.0)
    collector.record_memory_usage(70.0)
    collector.record_metric("error", 1.0, context="network")

    # Get raw data (spy pattern)
    data = collector.get_recorded_data()

    # Check raw recorded values - NO CALCULATIONS
    assert data["object_access"]["OBJ001"] == 2
    assert data["cache_hits"]["L1"] == 1
    assert data["cache_misses"]["L1"] == 1
    assert 100 in data["token_usage"]
    assert 200 in data["token_usage"]
    assert 0.1 in data["latency_db_queries"]
    assert 0.3 in data["latency_db_queries"]
    assert 50.0 in data["memory_usage"]
    assert 70.0 in data["memory_usage"]
    assert data["errors"]["network"] == 1
    assert data["contradiction_tracking"]["total"] == 1


def test_protocol_compatible_methods() -> None:
    """Test that protocol-compatible methods record calls correctly."""
    collector = MockMetricsCollector()

    # Use protocol methods
    collector.record("test_metric", 42.0, tags={"env": "test"})
    collector.increment("counter_name", value=5)
    collector.gauge("gauge_name", value=3.14)
    with collector.time("operation_name"):
        pass  # Simulated work

    # Verify calls were recorded
    calls = collector.get_protocol_calls()
    assert len(calls) == 5  # record, increment, gauge, time_enter, time_exit

    assert calls[0]["method"] == "record"
    assert calls[0]["name"] == "test_metric"
    assert calls[0]["value"] == 42.0

    assert calls[1]["method"] == "increment"
    assert calls[1]["name"] == "counter_name"
    assert calls[1]["value"] == 5

    assert calls[2]["method"] == "gauge"
    assert calls[2]["name"] == "gauge_name"

    assert calls[3]["method"] == "time_enter"
    assert calls[4]["method"] == "time_exit"


def test_clear_resets_all_data() -> None:
    """Test that clear() resets all recorded data."""
    collector = MockMetricsCollector()

    # Record some data
    collector.record_object_access("obj1", "test")
    collector.record_token_usage(100)
    collector.record("metric", 1.0)

    # Clear
    collector.clear()

    # Verify reset
    data = collector.get_recorded_data()
    assert len(data["object_access"]) == 0
    assert len(data["token_usage"]) == 0
    assert len(collector.get_protocol_calls()) == 0


def test_analyze_performance_deprecation_warning() -> None:
    """Test that analyze_performance() emits deprecation warning."""
    collector = MockMetricsCollector()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        collector.analyze_performance()
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
