"""Service container for dependency injection.

This module provides a ServiceContainer dataclass that aggregates all
dependencies needed by the simulation engine, enabling clean injection
for testing and configuration.

Sprint 3: Central Committee (Dependency Injection)
Paradox Refactor: Added GameDefines for centralized coefficients.
Spec 008: Added metrics field for dependency-injected telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from babylon.config.defines import GameDefines
from babylon.engine.database import DatabaseConnection
from babylon.engine.event_bus import EventBus
from babylon.engine.formula_registry import FormulaRegistry
from babylon.models.config import SimulationConfig

if TYPE_CHECKING:
    from babylon.metrics.interfaces import MetricsCollectorProtocol


@dataclass
class ServiceContainer:
    """Container for all simulation services.

    Aggregates the six core services needed by the simulation:
    - config: Immutable simulation parameters
    - database: Database connection for persistence
    - event_bus: Publish/subscribe communication
    - formulas: Registry of mathematical formulas
    - defines: Centralized game coefficients (Paradox Refactor)
    - metrics: Telemetry collector for observability (Spec 008)

    Example:
        >>> container = ServiceContainer.create()
        >>> rent = container.formulas.get("imperial_rent")
        >>> container.event_bus.publish(Event(...))
        >>> with container.database.session() as session:
        ...     # do database work
        >>> container.database.close()
        >>> default_org = container.defines.DEFAULT_ORGANIZATION
        >>> container.metrics.increment("ticks_processed")
    """

    config: SimulationConfig
    database: DatabaseConnection
    event_bus: EventBus
    formulas: FormulaRegistry
    defines: GameDefines
    metrics: MetricsCollectorProtocol

    @classmethod
    def create(
        cls,
        config: SimulationConfig | None = None,
        defines: GameDefines | None = None,
        metrics: MetricsCollectorProtocol | None = None,
    ) -> ServiceContainer:
        """Factory method to create a fully-initialized container.

        Creates all services with sensible defaults. Uses in-memory
        SQLite for database isolation in tests.

        Args:
            config: Optional custom config. If None, uses default SimulationConfig.
            defines: Optional custom defines. If None, uses default GameDefines.
            metrics: Optional custom metrics collector. If None, creates a new
                MetricsCollector instance. Pass a mock for testing.

        Returns:
            ServiceContainer with all services initialized
        """
        # Lazy import to avoid circular imports (T017)
        if metrics is None:
            from babylon.metrics.collector import MetricsCollector

            metrics = MetricsCollector()

        return cls(
            config=config if config is not None else SimulationConfig(),
            database=DatabaseConnection(url="sqlite:///:memory:"),
            event_bus=EventBus(),
            formulas=FormulaRegistry.default(),
            defines=defines if defines is not None else GameDefines(),
            metrics=metrics,
        )
