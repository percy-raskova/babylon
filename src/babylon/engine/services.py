"""Service container for dependency injection.

This module provides a ServiceContainer dataclass that aggregates all
dependencies needed by the simulation engine, enabling clean injection
for testing and configuration.

Sprint 3: Central Committee (Dependency Injection)
Paradox Refactor: Added GameDefines for centralized coefficients.
Spec 008: Added metrics field for dependency-injected telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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

    Aggregates the six core services needed by the simulation, plus
    optional economics calculator services for tick dynamics (Feature 017):

    Core:
        - config: Immutable simulation parameters
        - database: Database connection for persistence
        - event_bus: Publish/subscribe communication
        - formulas: Registry of mathematical formulas
        - defines: Centralized game coefficients (Paradox Refactor)
        - metrics: Telemetry collector for observability (Spec 008)

    Field Topology (Feature 002, optional for backward compatibility):
        - field_registry: Contradiction field computation registry

    Economics (Feature 017, all optional for backward compatibility):
        - melt_calculator: National MELT computation (Feature 013)
        - basket_calculator: Basket visibility computation (Feature 013)
        - gamma_calculator: Reproductive visibility computation (Feature 015)
        - capital_calculator: Capital stock computation (Feature 012)
        - throughput_calculator: Throughput position computation (Feature 014)
        - transition_engine: Class transition engine (Feature 016)
        - imperial_rent_calculator: Imperial rent computation (Feature 013)
        - tensor_registry: Cached economic tensor data (Feature 011)

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

    # Field topology services (Feature 002 - optional, default None)
    field_registry: Any = field(default=None)

    # Economics calculator services (Feature 017 - all optional, default None)
    melt_calculator: Any = field(default=None)
    basket_calculator: Any = field(default=None)
    gamma_calculator: Any = field(default=None)
    capital_calculator: Any = field(default=None)
    throughput_calculator: Any = field(default=None)
    transition_engine: Any = field(default=None)
    imperial_rent_calculator: Any = field(default=None)
    tensor_registry: Any = field(default=None)

    @classmethod
    def create(
        cls,
        config: SimulationConfig | None = None,
        defines: GameDefines | None = None,
        metrics: MetricsCollectorProtocol | None = None,
        *,
        field_registry: Any = None,
        melt_calculator: Any = None,
        basket_calculator: Any = None,
        gamma_calculator: Any = None,
        capital_calculator: Any = None,
        throughput_calculator: Any = None,
        transition_engine: Any = None,
        imperial_rent_calculator: Any = None,
        tensor_registry: Any = None,
    ) -> ServiceContainer:
        """Factory method to create a fully-initialized container.

        Creates all services with sensible defaults. Uses in-memory
        SQLite for database isolation in tests.

        Args:
            config: Optional custom config. If None, uses default SimulationConfig.
            defines: Optional custom defines. If None, uses default GameDefines.
            metrics: Optional custom metrics collector. If None, creates a new
                MetricsCollector instance. Pass a mock for testing.
            field_registry: Optional FieldRegistry for contradiction fields (Feature 002).
            melt_calculator: Optional MELTCalculator (Feature 013).
            basket_calculator: Optional BasketVisibilityCalculator (Feature 013).
            gamma_calculator: Optional GammaIIICalculator (Feature 015).
            capital_calculator: Optional CapitalStockCalculator (Feature 012).
            throughput_calculator: Optional ThroughputCalculator (Feature 014).
            transition_engine: Optional ClassTransitionEngine (Feature 016).
            imperial_rent_calculator: Optional ImperialRentCalculator (Feature 013).
            tensor_registry: Optional TensorRegistry for cached tensor data (Feature 011).

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
            field_registry=field_registry,
            melt_calculator=melt_calculator,
            basket_calculator=basket_calculator,
            gamma_calculator=gamma_calculator,
            capital_calculator=capital_calculator,
            throughput_calculator=throughput_calculator,
            transition_engine=transition_engine,
            imperial_rent_calculator=imperial_rent_calculator,
            tensor_registry=tensor_registry,
        )
