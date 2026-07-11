"""Integration tests for tick-context logging correlation.

RED Phase: These tests verify that logs within run_tick() include
tick number and correlation_id as required by Spec 008.

Test Intent:
- T019: Logs within run_tick() contain tick number
- T020: Logs within run_tick() contain correlation_id (UUID)
- T021: Each tick has a unique correlation_id
- T022: Nested function calls inherit tick context
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import SimulationEngine
from babylon.kernel.system_protocol import ContextType, System


class LogCapturingHandler(logging.Handler):
    """Custom handler to capture log records for testing."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def clear(self) -> None:
        self.records.clear()


class LoggingSystem(System):
    """A test system that emits log messages."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Emit a log message during step execution."""
        self._logger.info("LoggingSystem step executed")


class NestedLoggingSystem(System):
    """A test system that emits logs from nested function calls."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Emit logs from nested calls."""
        self._outer_call()

    def _outer_call(self) -> None:
        self._logger.info("Outer function log")
        self._inner_call()

    def _inner_call(self) -> None:
        self._logger.info("Inner function log")


class TestLogContextInRunTick:
    """Test that run_tick() wraps execution with log context."""

    @pytest.fixture
    def test_logger(self) -> logging.Logger:
        """Create a logger for testing."""
        logger = logging.getLogger("test.log_context")
        logger.setLevel(logging.DEBUG)
        # Add ContextAwareFilter to inject context fields
        from babylon.utils.log import ContextAwareFilter

        logger.addFilter(ContextAwareFilter())
        return logger

    @pytest.fixture
    def handler(self, test_logger: logging.Logger) -> LogCapturingHandler:
        """Create and attach a capturing handler."""
        handler = LogCapturingHandler()
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)
        yield handler
        test_logger.removeHandler(handler)

    @pytest.fixture
    def services(self) -> ServiceContainer:
        """Create a ServiceContainer for testing."""
        container = ServiceContainer.create()
        yield container
        container.database.close()

    def test_logs_contain_tick_number(
        self, test_logger: logging.Logger, handler: LogCapturingHandler, services: ServiceContainer
    ) -> None:
        """T019: Logs within run_tick() contain tick number.

        SC-003: Logs within run_tick() have tick + correlation_id.
        """
        engine = SimulationEngine([LoggingSystem(test_logger)])
        graph = BabylonGraph()

        # Run tick with tick=5
        context: dict[str, Any] = {"tick": 5}
        engine.run_tick(graph, services, context)

        # Verify log records have tick attribute
        assert len(handler.records) >= 1
        for record in handler.records:
            assert hasattr(record, "tick"), "Log record missing 'tick' attribute"
            assert record.tick == 5, f"Expected tick=5, got tick={record.tick}"

    def test_logs_contain_correlation_id(
        self, test_logger: logging.Logger, handler: LogCapturingHandler, services: ServiceContainer
    ) -> None:
        """T020: Logs within run_tick() contain correlation_id.

        SC-003: Each log within run_tick() must have a correlation_id UUID.
        """
        engine = SimulationEngine([LoggingSystem(test_logger)])
        graph = BabylonGraph()

        context: dict[str, Any] = {"tick": 1}
        engine.run_tick(graph, services, context)

        assert len(handler.records) >= 1
        for record in handler.records:
            assert hasattr(record, "correlation_id"), "Log record missing 'correlation_id'"
            # Verify it's a valid UUID
            correlation_id = record.correlation_id
            try:
                uuid.UUID(correlation_id)
            except (ValueError, AttributeError):
                pytest.fail(f"correlation_id '{correlation_id}' is not a valid UUID")

    def test_each_tick_has_unique_correlation_id(
        self, test_logger: logging.Logger, handler: LogCapturingHandler, services: ServiceContainer
    ) -> None:
        """T021: Each tick has a unique correlation_id.

        SC-003: Running multiple ticks should produce different correlation_ids.
        """
        engine = SimulationEngine([LoggingSystem(test_logger)])
        graph = BabylonGraph()

        # Run two ticks
        context1: dict[str, Any] = {"tick": 1}
        engine.run_tick(graph, services, context1)
        tick1_records = list(handler.records)
        handler.clear()

        context2: dict[str, Any] = {"tick": 2}
        engine.run_tick(graph, services, context2)
        tick2_records = list(handler.records)

        # Extract correlation_ids
        assert len(tick1_records) >= 1
        assert len(tick2_records) >= 1

        correlation_id_1 = tick1_records[0].correlation_id
        correlation_id_2 = tick2_records[0].correlation_id

        assert correlation_id_1 != correlation_id_2, (
            f"Tick 1 and Tick 2 should have different correlation_ids, "
            f"but both have {correlation_id_1}"
        )

    def test_nested_calls_inherit_tick_context(
        self, test_logger: logging.Logger, handler: LogCapturingHandler, services: ServiceContainer
    ) -> None:
        """T022: Nested function calls inherit tick context.

        SC-003: All logs within the run_tick scope should have the same
        tick and correlation_id, even from nested function calls.
        """
        engine = SimulationEngine([NestedLoggingSystem(test_logger)])
        graph = BabylonGraph()

        context: dict[str, Any] = {"tick": 10}
        engine.run_tick(graph, services, context)

        # Should have 2 log records (outer and inner)
        assert len(handler.records) >= 2

        # All records should have same tick and correlation_id
        ticks = {record.tick for record in handler.records}
        correlation_ids = {record.correlation_id for record in handler.records}

        assert ticks == {10}, f"All logs should have tick=10, got {ticks}"
        assert len(correlation_ids) == 1, (
            f"All logs within same tick should share correlation_id, "
            f"got {len(correlation_ids)} different IDs"
        )
