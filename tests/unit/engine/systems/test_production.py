"""Unit tests for ProductionSystem - The Soil.

TDD tests for the Material Reality Refactor.
Workers generate wealth from labor × biocapacity.
Only active workers in territories can produce.

Feature 020: Tests for tensor-aware production (T010).

These tests are written BEFORE implementation (RED phase of TDD).
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import networkx as nx
import pytest

from babylon.economics.tensor import DepartmentRow, NoDataSentinel, ValueTensor4x3
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
    population: int = 1,
) -> None:
    """Add a worker node to the graph."""
    graph.add_node(
        node_id,
        role=role,
        wealth=wealth,
        active=active,
        population=population,
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
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # base_labor_power is annual, converted to weekly
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_worker_in_half_biocapacity_territory_gains_half_labor_power(
        self, services: ServiceContainer
    ) -> None:
        """Worker in territory with 50% biocapacity gains half production.

        production = (1.0 / 52) * (50 / 100) = 0.0096
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=50.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 0.5
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_worker_in_depleted_territory_gains_nothing(self, services: ServiceContainer) -> None:
        """Worker in territory with 0 biocapacity gains nothing.

        production = 1.0 * (0 / 100) = 0.0
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=5.0)
        _create_territory_node(graph, "T001", biocapacity=0.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (no production)
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(5.0)

    def test_worker_without_territory_gains_nothing(self, services: ServiceContainer) -> None:
        """Worker with no TENANCY edge gains nothing (no territory to work)."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=5.0)
        # No territory, no tenancy edge

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(5.0)

    def test_inactive_worker_does_not_produce(self, services: ServiceContainer) -> None:
        """Dead workers (active=False) do not produce."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0, active=False)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (dead worker can't work)
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(0.0)

    def test_bourgeoisie_does_not_produce(self, services: ServiceContainer) -> None:
        """Bourgeoisie extracts but does not produce value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(
            graph, "PERIPHERY_WORKER_ID", role=SocialRole.CORE_BOURGEOISIE, wealth=100.0
        )
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (bourgeoisie doesn't produce)
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(100.0)

    def test_comprador_does_not_produce(self, services: ServiceContainer) -> None:
        """Comprador bourgeoisie extracts but does not produce."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(
            graph, "PERIPHERY_WORKER_ID", role=SocialRole.COMPRADOR_BOURGEOISIE, wealth=50.0
        )
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(50.0)

    def test_labor_aristocracy_produces(self, services: ServiceContainer) -> None:
        """Labor aristocracy is a worker class and produces value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(
            graph, "PERIPHERY_WORKER_ID", role=SocialRole.LABOR_ARISTOCRACY, wealth=0.0
        )
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_periphery_proletariat_produces(self, services: ServiceContainer) -> None:
        """Periphery proletariat produces value."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(
            graph, "PERIPHERY_WORKER_ID", role=SocialRole.PERIPHERY_PROLETARIAT, wealth=0.0
        )
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_production_accumulates_with_existing_wealth(self, services: ServiceContainer) -> None:
        """Production adds to existing wealth, not replaces it."""
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=10.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_wealth = 10.0 + (annual_labor_power / weeks_per_year)
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_wealth)

    def test_production_system_name(self) -> None:
        """ProductionSystem should have correct name property."""
        system = ProductionSystem()
        assert system.name == "production"


@pytest.mark.unit
class TestProductionPopulationScaling:
    """Tests for Mass Line population scaling in ProductionSystem."""

    def test_population_scales_production(self, services: ServiceContainer) -> None:
        """Production scales linearly with population.

        A block of 100 workers produces 100× what a single worker produces.
        production = (base_labor_power * population) * bio_ratio
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0, population=100)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Expected: (base_labor_power / weeks_per_year) * population * bio_ratio
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 100 * 1.0
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_population_one_backward_compatible(self, services: ServiceContainer) -> None:
        """Population=1 produces same as original implementation.

        This ensures backward compatibility for existing scenarios.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0, population=1)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year
        expected_production = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(expected_production)

    def test_population_zero_no_production(self, services: ServiceContainer) -> None:
        """Population=0 produces nothing (extinct block).

        Zero workers means zero production, regardless of territory health.
        """
        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=5.0, population=0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Wealth unchanged (0 population = 0 production)
        assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == pytest.approx(5.0)


def _make_tensor(
    fips: str = "26163", year: int = 2022, total_v: float = 520000.0
) -> ValueTensor4x3:
    """Create a ValueTensor4x3 with a given total_v (split across 4 departments)."""
    v_per_dept = total_v / 4.0
    dept = DepartmentRow(c=100.0, v=v_per_dept, s=50.0)
    return ValueTensor4x3(
        fips_code=fips,
        year=year,
        dept_I=dept,
        dept_IIa=dept,
        dept_IIb=dept,
        dept_III=dept,
        naics_granularity=0.85,
        excluded_wages=0.0,
    )


@pytest.mark.unit
class TestTensorAwareProduction:
    """Tests for tensor-driven production in ProductionSystem (Feature 020, T010)."""

    def test_tensor_lookup_uses_total_v(self) -> None:
        """When tensor_registry provides data, production uses total_v."""
        total_v = 520000.0  # annual variable capital in labor-hours
        tensor = _make_tensor(total_v=total_v)

        mock_registry = MagicMock()
        mock_registry.get.return_value = tensor

        services = ServiceContainer.create(tensor_registry=mock_registry)
        weeks_per_year = services.defines.timescale.weeks_per_year

        graph: nx.DiGraph = nx.DiGraph()
        graph.graph["base_year"] = 2022
        _create_worker_node(graph, "W1", wealth=0.0, population=1)
        _create_territory_node(graph, "T1", biocapacity=100.0, max_biocapacity=100.0)
        graph.nodes["T1"]["fips_code"] = "26163"
        _create_tenancy_edge(graph, "W1", "T1")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 0})

        expected = (total_v / weeks_per_year) * 1.0  # population=1, bio_ratio=1.0
        assert graph.nodes["W1"]["wealth"] == pytest.approx(expected)
        services.database.close()

    def test_no_data_sentinel_falls_back_to_base_labor_power(self) -> None:
        """When tensor_registry returns NoDataSentinel, use base_labor_power."""
        mock_registry = MagicMock()
        mock_registry.get.return_value = NoDataSentinel("26163", 2022, "no data")

        services = ServiceContainer.create(tensor_registry=mock_registry)
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year

        graph: nx.DiGraph = nx.DiGraph()
        graph.graph["base_year"] = 2022
        _create_worker_node(graph, "W1", wealth=0.0)
        _create_territory_node(graph, "T1", biocapacity=100.0, max_biocapacity=100.0)
        graph.nodes["T1"]["fips_code"] = "26163"
        _create_tenancy_edge(graph, "W1", "T1")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 0})

        expected = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["W1"]["wealth"] == pytest.approx(expected)
        services.database.close()

    def test_no_tensor_registry_falls_back_to_base_labor_power(self) -> None:
        """When tensor_registry is None, use base_labor_power (backward compat)."""
        services = ServiceContainer.create()  # tensor_registry=None
        annual_labor_power = services.defines.economy.base_labor_power
        weeks_per_year = services.defines.timescale.weeks_per_year

        graph: nx.DiGraph = nx.DiGraph()
        _create_worker_node(graph, "W1", wealth=0.0)
        _create_territory_node(graph, "T1", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "W1", "T1")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 0})

        expected = (annual_labor_power / weeks_per_year) * 1.0
        assert graph.nodes["W1"]["wealth"] == pytest.approx(expected)
        services.database.close()

    def test_two_fips_different_tensors(self) -> None:
        """Two territories with different tensors produce different values."""
        tensor_wayne = _make_tensor(fips="26163", total_v=520000.0)
        tensor_oakland = _make_tensor(fips="26125", total_v=260000.0)

        mock_registry = MagicMock()

        def get_tensor(fips: str, year: int) -> ValueTensor4x3:
            if fips == "26163":
                return tensor_wayne
            return tensor_oakland

        mock_registry.get.side_effect = get_tensor

        services = ServiceContainer.create(tensor_registry=mock_registry)
        weeks_per_year = services.defines.timescale.weeks_per_year

        graph: nx.DiGraph = nx.DiGraph()
        graph.graph["base_year"] = 2022

        _create_worker_node(graph, "W1", wealth=0.0)
        _create_territory_node(graph, "T1", biocapacity=100.0, max_biocapacity=100.0)
        graph.nodes["T1"]["fips_code"] = "26163"
        _create_tenancy_edge(graph, "W1", "T1")

        _create_worker_node(graph, "W2", wealth=0.0)
        _create_territory_node(graph, "T2", biocapacity=100.0, max_biocapacity=100.0)
        graph.nodes["T2"]["fips_code"] = "26125"
        _create_tenancy_edge(graph, "W2", "T2")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 0})

        assert graph.nodes["W1"]["wealth"] == pytest.approx(520000.0 / weeks_per_year)
        assert graph.nodes["W2"]["wealth"] == pytest.approx(260000.0 / weeks_per_year)
        # Wayne should produce 2x Oakland
        assert graph.nodes["W1"]["wealth"] == pytest.approx(2.0 * graph.nodes["W2"]["wealth"])
        services.database.close()
