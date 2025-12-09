"""Tests for ServiceContainer dependency injection.

RED Phase: These tests define the contract for the service container.
The ServiceContainer aggregates all dependencies for the simulation.

Test Intent:
- ServiceContainer is a dataclass holding all services
- create() factory builds a container with default or custom config
- All services are accessible as attributes
"""

from dataclasses import is_dataclass


class TestServiceContainer:
    """Test ServiceContainer behavior."""

    def test_is_dataclass(self) -> None:
        """ServiceContainer is a dataclass."""
        from babylon.engine.services import ServiceContainer

        assert is_dataclass(ServiceContainer)

    def test_create_with_no_args_uses_default_config(self) -> None:
        """create() with no arguments uses default SimulationConfig."""
        from babylon.engine.services import ServiceContainer
        from babylon.models.config import SimulationConfig

        container = ServiceContainer.create()

        try:
            # Should have a config with default values
            assert container.config is not None
            assert isinstance(container.config, SimulationConfig)
            # Check a default value
            assert container.config.extraction_efficiency == 0.8
        finally:
            container.database.close()

    def test_create_with_custom_config_uses_it(self) -> None:
        """create() with custom config uses the provided config."""
        from babylon.engine.services import ServiceContainer
        from babylon.models.config import SimulationConfig

        custom_config = SimulationConfig(extraction_efficiency=0.5)
        container = ServiceContainer.create(config=custom_config)

        try:
            assert container.config is custom_config
            assert container.config.extraction_efficiency == 0.5
        finally:
            container.database.close()

    def test_all_services_accessible_as_attributes(self) -> None:
        """All services are accessible as named attributes."""
        from babylon.engine.database import DatabaseConnection
        from babylon.engine.event_bus import EventBus
        from babylon.engine.formula_registry import FormulaRegistry
        from babylon.engine.services import ServiceContainer
        from babylon.models.config import SimulationConfig

        container = ServiceContainer.create()

        try:
            # All four services should be accessible
            assert isinstance(container.config, SimulationConfig)
            assert isinstance(container.database, DatabaseConnection)
            assert isinstance(container.event_bus, EventBus)
            assert isinstance(container.formulas, FormulaRegistry)
        finally:
            container.database.close()

    def test_event_bus_is_functional(self) -> None:
        """The event bus in the container is fully functional."""
        from babylon.engine.event_bus import Event
        from babylon.engine.services import ServiceContainer

        container = ServiceContainer.create()
        received: list[Event] = []

        try:
            container.event_bus.subscribe("test", lambda e: received.append(e))
            container.event_bus.publish(Event(type="test", tick=0, payload={}))

            assert len(received) == 1
        finally:
            container.database.close()

    def test_database_is_functional(self) -> None:
        """The database in the container is fully functional."""
        from sqlalchemy import text

        from babylon.engine.services import ServiceContainer

        container = ServiceContainer.create()

        try:
            with container.database.session() as session:
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            container.database.close()

    def test_formulas_has_all_defaults(self) -> None:
        """The formula registry has all default formulas registered."""
        from babylon.engine.services import ServiceContainer

        container = ServiceContainer.create()

        try:
            formulas = container.formulas.list_formulas()
            assert len(formulas) == 13  # 12 original + solidarity_transmission
            assert "imperial_rent" in formulas
            assert "revolution_probability" in formulas
            assert "solidarity_transmission" in formulas  # Sprint 3.4.2
        finally:
            container.database.close()

    def test_container_can_be_created_multiple_times(self) -> None:
        """Multiple containers can be created independently."""
        from babylon.engine.services import ServiceContainer
        from babylon.models.config import SimulationConfig

        config1 = SimulationConfig(extraction_efficiency=0.1)
        config2 = SimulationConfig(extraction_efficiency=0.9)

        container1 = ServiceContainer.create(config=config1)
        container2 = ServiceContainer.create(config=config2)

        try:
            assert container1.config.extraction_efficiency == 0.1
            assert container2.config.extraction_efficiency == 0.9

            # They should have independent event buses
            container1.event_bus.publish(
                __import__("babylon.engine.event_bus", fromlist=["Event"]).Event(
                    type="test", tick=0, payload={}
                )
            )
            assert len(container1.event_bus.get_history()) == 1
            assert len(container2.event_bus.get_history()) == 0
        finally:
            container1.database.close()
            container2.database.close()

    def test_create_uses_memory_database_by_default(self) -> None:
        """create() uses in-memory SQLite for isolation."""
        from babylon.engine.services import ServiceContainer

        container = ServiceContainer.create()

        try:
            # Should be using in-memory database
            assert "memory" in str(container.database._engine.url)
        finally:
            container.database.close()
