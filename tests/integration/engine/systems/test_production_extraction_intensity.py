"""Integration tests for extraction_intensity hump shape decay dynamics.

Tests that verify the decay phase in long simulations where
ProductionSystem sets extraction_intensity, causing MetabolismSystem
to degrade biocapacity over many ticks.

Extracted from tests/unit/engine/systems/test_production_extraction_intensity.py
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.engine.systems.production import ProductionSystem
from babylon.models.enums import EdgeType, SocialRole
from tests.constants import TestConstants

TC = TestConstants


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
    extraction_intensity: float = 0.0,
    regeneration_rate: float = 0.02,
) -> None:
    """Add a territory node to the graph."""
    graph.add_node(
        node_id,
        biocapacity=biocapacity,
        max_biocapacity=max_biocapacity,
        extraction_intensity=extraction_intensity,
        regeneration_rate=regeneration_rate,
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


@pytest.mark.integration
class TestHumpShapeDecay:
    """Verify decay phase in long simulations."""

    def test_biocapacity_declines_over_100_ticks(self, services: ServiceContainer) -> None:
        """Multi-tick simulation shows progressive biocapacity decline.

        With sufficient workers, biocapacity should steadily decline
        over 100 ticks, demonstrating the metabolic rift dynamics.
        """
        graph: nx.DiGraph = BabylonGraph()

        # Create enough workers for intensity > breakeven
        # Need ~87 workers for breakeven (0.0167 * 100 / 0.0192 ~ 87)
        # Use 150 for clear depletion signal
        for i in range(150):
            _create_worker_node(graph, f"C{i:03d}", wealth=0.0)
            _create_tenancy_edge(graph, f"C{i:03d}", "T001")

        _create_territory_node(
            graph,
            "T001",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
        )

        initial_biocapacity = graph.nodes["T001"]["biocapacity"]
        production = ProductionSystem()
        metabolism = MetabolismSystem()

        for tick in range(100):
            production.step(graph, services, {"tick": tick})
            metabolism.step(graph, services, {"tick": tick})

        final_biocapacity = graph.nodes["T001"]["biocapacity"]

        assert final_biocapacity < initial_biocapacity * 0.8, (
            f"Biocapacity should decline by at least 20% over 100 ticks: "
            f"initial={initial_biocapacity:.2f}, final={final_biocapacity:.2f}, "
            f"decline={(1 - final_biocapacity / initial_biocapacity) * 100:.1f}%"
        )

    def test_production_declines_with_biocapacity(self, services: ServiceContainer) -> None:
        """Wealth accumulation slows as biocapacity depletes.

        The first 50 ticks should accumulate more wealth than
        the second 50 ticks due to biocapacity depletion.
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)

        # Use high extraction to accelerate depletion for test
        _create_territory_node(
            graph,
            "T001",
            biocapacity=100.0,
            max_biocapacity=100.0,
            regeneration_rate=0.02,
            extraction_intensity=0.5,  # High initial extraction
        )
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        production = ProductionSystem()
        metabolism = MetabolismSystem()

        # Run first 50 ticks and record wealth gained
        wealth_at_start = graph.nodes["PERIPHERY_WORKER_ID"]["wealth"]
        for tick in range(50):
            production.step(graph, services, {"tick": tick})
            metabolism.step(graph, services, {"tick": tick})
        wealth_at_50 = graph.nodes["PERIPHERY_WORKER_ID"]["wealth"]
        first_half_gain = wealth_at_50 - wealth_at_start

        # Run next 50 ticks
        for tick in range(50, 100):
            production.step(graph, services, {"tick": tick})
            metabolism.step(graph, services, {"tick": tick})
        wealth_at_100 = graph.nodes["PERIPHERY_WORKER_ID"]["wealth"]
        second_half_gain = wealth_at_100 - wealth_at_50

        # Second half should produce less due to depleted biocapacity
        assert second_half_gain < first_half_gain, (
            f"Wealth gain should slow as biocapacity depletes: "
            f"first_half={first_half_gain:.4f}, second_half={second_half_gain:.4f}"
        )
