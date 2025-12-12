"""Metrics collector interfaces and protocols.

This module defines the contract that all metrics collectors must implement,
enabling dependency injection and testability throughout the codebase.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol


class MetricsCollectorProtocol(Protocol):
    """Protocol defining the contract for metrics collectors.

    This protocol ensures both the real MetricsCollector and any test
    doubles (spies, mocks) implement the same interface.

    The protocol follows the "Dumb Spy" pattern for test doubles:
    implementations should record what was called, not calculate statistics.
    Statistical analysis belongs in the production MetricsCollector only.

    Example:
        .. code-block:: python

            def process_data(collector: MetricsCollectorProtocol) -> None:
                collector.increment("items_processed")
                with collector.time("processing_duration"):
                    # ... do work ...
                    pass
    """

    def record(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric value.

        Args:
            name: Metric name (e.g., "simulation.p_revolution").
            value: Numeric value to record.
            tags: Key-value pairs for filtering/grouping.
            metadata: Additional context.
        """
        ...

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter.

        Args:
            name: Counter name.
            value: Amount to increment (default 1).
        """
        ...

    def gauge(self, name: str, value: float) -> None:
        """Set a gauge value.

        Gauges represent point-in-time values that can go up or down.

        Args:
            name: Gauge name.
            value: Current value.
        """
        ...

    def time(self, name: str) -> AbstractContextManager[Any]:
        """Context manager for timing operations.

        Args:
            name: Timer name.

        Returns:
            Context manager that records duration on exit.

        Example:
            .. code-block:: python

                with collector.time("embedding.generation"):
                    embeddings = generate_embeddings(texts)
        """
        ...

    def summary(self) -> dict[str, Any]:
        """Get aggregated summary of all metrics.

        Returns:
            Dict containing counters, gauges, timer statistics, etc.
        """
        ...

    def clear(self) -> None:
        """Clear all recorded metrics.

        Used primarily for testing or resetting between game sessions.
        """
        ...
