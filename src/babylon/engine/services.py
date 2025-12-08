"""Service container for dependency injection.

This module provides a ServiceContainer dataclass that aggregates all
dependencies needed by the simulation engine, enabling clean injection
for testing and configuration.

Sprint 3: Central Committee (Dependency Injection)
"""

from dataclasses import dataclass

from babylon.engine.database import DatabaseConnection
from babylon.engine.event_bus import EventBus
from babylon.engine.formula_registry import FormulaRegistry
from babylon.models.config import SimulationConfig


@dataclass
class ServiceContainer:
    """Container for all simulation services.

    Aggregates the four core services needed by the simulation:
    - config: Immutable simulation parameters
    - database: Database connection for persistence
    - event_bus: Publish/subscribe communication
    - formulas: Registry of mathematical formulas

    Example:
        >>> container = ServiceContainer.create()
        >>> rent = container.formulas.get("imperial_rent")
        >>> container.event_bus.publish(Event(...))
        >>> with container.database.session() as session:
        ...     # do database work
        >>> container.database.close()
    """

    config: SimulationConfig
    database: DatabaseConnection
    event_bus: EventBus
    formulas: FormulaRegistry

    @classmethod
    def create(cls, config: SimulationConfig | None = None) -> "ServiceContainer":
        """Factory method to create a fully-initialized container.

        Creates all services with sensible defaults. Uses in-memory
        SQLite for database isolation in tests.

        Args:
            config: Optional custom config. If None, uses default SimulationConfig.

        Returns:
            ServiceContainer with all services initialized
        """
        return cls(
            config=config if config is not None else SimulationConfig(),
            database=DatabaseConnection(url="sqlite:///:memory:"),
            event_bus=EventBus(),
            formulas=FormulaRegistry.default(),
        )
