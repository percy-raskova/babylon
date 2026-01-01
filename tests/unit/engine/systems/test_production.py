"""Unit tests for ProductionSystem - The Soil.

TDD tests for the Material Reality Refactor.
Workers generate wealth from labor × biocapacity.
Only active workers in territories can produce.

These tests are written BEFORE implementation (RED phase of TDD).
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.production import ProductionSystem
from babylon.models.enums import EdgeType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_worker_node(
    graph: nx.DiGraph,
    node_id: str,
    role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
    wealth: float = 0.0,
    active: bool = True,
) -> None:
    """Add a worker node to the graph."""
    graph.add_node(
        node_id,
        role=role,
        wealth=wealth,
        active=active,
        _node_type="social_class",
    )


def _create_territory_node(
    graph: nx.DiGraph,
    node_id: str,
    biocapacity: float = 100.0,
    max_biocapacity: float = 100.0,
) -> None:
    """Add a territory node to the graph."""
    graph.add_node(
        node_id,
        biocapacity=biocapacity,
        max_biocapacity=max_biocapacity,
        _node_type="territory",
    )


def _create_tenancy_edge(
    graph: nx.DiGraph,
    worker_id: str,
    territory_id: str,
) -> None:
    """Add a TENANCY edge from worker to territory."""
    graph.add_edge(
        worker_id,
        territory_id,
        edge_type=EdgeType.TENANCY,
    )


@pytest.mark.unit
class TestProductionSystem:
    """Tests for ProductionSystem value creation mechanics."""

    def test_worker_in_full_biocapacity_territory_gains_full_labor_power(
        self, services: ServiceContainer
    ) -> None:
        """Worker in territory with 100% biocapacity gains weekly labor power.

        production = (base_labor_power / weeks_per_year) * (biocapacity / max_biocapacity)
        production = (1.0 / 52) * (100 / 100) = 0.0192
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # base_labor_power is annual, converted to weekly
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_production)

    def test_worker_in_half_biocapacity_territory_gains_half_labor_power(
        self, services: ServiceContainer
    ) -> None:
        """Worker in territory with 50% biocapacity gains half production.

        production = (1.0 / 52) * (50 / 100) = 0.0096
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=50.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 0.5
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_production)

    def test_worker_in_depleted_territory_gains_nothing(self, services: ServiceContainer) -> None:
        """Worker in territory with 0 biocapacity gains nothing.

        production = 1.0 * (0 / 100) = 0.0
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=5.0)
        _create_territory_node(graph, "T001", biocapacity=0.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (no production)
        assert graph.nodes["C001"]["wealth"] == pytest.approx(5.0)

    def test_worker_without_territory_gains_nothing(self, services: ServiceContainer) -> None:
        """Worker with no TENANCY edge gains nothing (no territory to work)."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=5.0)
        # No territory, no tenancy edge

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged
        assert graph.nodes["C001"]["wealth"] == pytest.approx(5.0)

    def test_inactive_worker_does_not_produce(self, services: ServiceContainer) -> None:
        """Dead workers (active=False) do not produce."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=0.0, active=False)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (dead worker can't work)
        assert graph.nodes["C001"]["wealth"] == pytest.approx(0.0)

    def test_bourgeoisie_does_not_produce(self, services: ServiceContainer) -> None:
        """Bourgeoisie extracts but does not produce value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", role=SocialRole.CORE_BOURGEOISIE, wealth=100.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (bourgeoisie doesn't produce)
        assert graph.nodes["C001"]["wealth"] == pytest.approx(100.0)

    def test_comprador_does_not_produce(self, services: ServiceContainer) -> None:
        """Comprador bourgeoisie extracts but does not produce."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", role=SocialRole.COMPRADOR_BOURGEOISIE, wealth=50.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged
        assert graph.nodes["C001"]["wealth"] == pytest.approx(50.0)

    def test_labor_aristocracy_produces(self, services: ServiceContainer) -> None:
        """Labor aristocracy is a worker class and produces value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", role=SocialRole.LABOR_ARISTOCRACY, wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_production)

    def test_periphery_proletariat_produces(self, services: ServiceContainer) -> None:
        """Periphery proletariat produces value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", role=SocialRole.PERIPHERY_PROLETARIAT, wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_production)

    def test_production_accumulates_with_existing_wealth(self, services: ServiceContainer) -> None:
        """Production adds to existing wealth, not replaces it."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "C001", wealth=10.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "C001", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_wealth = 10.0 + (annual_labor_power / weeks_per_year)
        assert graph.nodes["C001"]["wealth"] == pytest.approx(expected_wealth)

    def test_production_system_name(self) -> None:
        """ProductionSystem should have correct name property."""
        system = ProductionSystem()
        assert system.name == "production"
