"""TDD tests for extraction_intensity linkage in ProductionSystem.

RED phase tests that verify ProductionSystem sets extraction_intensity on
territory nodes based on worker production. This linkage is critical for
the Hump Shape dynamics - without it, MetabolismSystem cannot degrade
biocapacity and the simulation shows infinite growth instead of decay.

Mathematical Context:
    MetabolismSystem uses: ΔB = R - (E × η)
    Where:
        R = regeneration_rate × max_biocapacity
        E = extraction_intensity × current_biocapacity
        η = entropy_factor (default 1.2)

    When extraction_intensity = 0.0, ΔB = R (only regeneration, no depletion).
    ProductionSystem must set extraction_intensity based on worker production.

    Formula: extraction_intensity = min(1.0, total_production / max_biocapacity)

    Breakeven threshold (where R = E × η):
        R = 0.02 × 100 = 2.0
        E × 1.2 × 100 = 2.0
        E = 2.0 / 120 = 0.0167

    When intensity > 0.0167, biocapacity depletes.
    When intensity < 0.0167, biocapacity regenerates.
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

# Use centralized breakeven constant from tests/constants.py
BREAKEVEN_INTENSITY = TC.MetabolicRift.BREAKEVEN_INTENSITY


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


@pytest.mark.unit
class TestProductionSetsExtractionIntensity:
    """Verify ProductionSystem sets extraction_intensity on territories."""

    def test_single_worker_sets_intensity(self, services: ServiceContainer) -> None:
        """Worker production creates extraction pressure on territory.

        A single worker produces wealth from biocapacity. This production
        should translate to extraction_intensity on the territory.

        Formula: intensity = min(1.0, production / max_biocapacity)

        With defaults:
            base_labor_power = 1.0/52 per tick (weekly)
            max_biocapacity = 100.0
            production = 1.0/52 * 1.0 (full biocapacity ratio)
            intensity = (1.0/52) / 100.0 = 0.000192
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        # Calculate expected intensity
        weekly_labor_power = services.defines.economy.base_labor_power / 52
        expected_intensity = weekly_labor_power / 100.0  # ~0.000192

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity == pytest.approx(expected_intensity, rel=0.01), (
            f"Single worker should set extraction_intensity: "
            f"expected={expected_intensity:.6f}, got={intensity:.6f}"
        )

    def test_multiple_workers_aggregate_intensity(self, services: ServiceContainer) -> None:
        """Multiple workers on same territory sum their extraction.

        Two workers on the same territory should produce combined
        extraction_intensity equal to sum of individual productions.
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_worker_node(graph, "COMPRADOR_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")
        _create_tenancy_edge(graph, "COMPRADOR_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        weekly_labor_power = services.defines.economy.base_labor_power / 52
        expected_intensity = (2 * weekly_labor_power) / 100.0  # ~0.000385

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity == pytest.approx(expected_intensity, rel=0.01), (
            f"Two workers should double extraction_intensity: "
            f"expected={expected_intensity:.6f}, got={intensity:.6f}"
        )

    def test_intensity_capped_at_one(self, services: ServiceContainer) -> None:
        """extraction_intensity cannot exceed 1.0.

        Even with massive production, intensity is capped to prevent
        numerical instability in MetabolismSystem.

        Uses a tiny max_biocapacity so few workers exceed the cap:
            production_per_worker = base_labor_power/52 * (biocapacity/max_biocapacity)
            With max_biocapacity=0.01, biocapacity=0.01:
                production_per_worker = 1.0/52 * 1.0 ≈ 0.0192
            total_production = 6 * 0.0192 ≈ 0.1154
            intensity = min(1.0, 0.1154 / 0.01) = min(1.0, 11.54) = 1.0
        """
        graph: nx.DiGraph = BabylonGraph()

        # 6 workers with tiny max_biocapacity to exceed cap without 6000 nodes
        for i in range(6):
            _create_worker_node(graph, f"C{i:04d}", wealth=0.0)
            _create_tenancy_edge(graph, f"C{i:04d}", "T001")

        _create_territory_node(graph, "T001", biocapacity=0.01, max_biocapacity=0.01)

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity <= 1.0, f"Intensity must be capped at 1.0, got {intensity:.4f}"
        assert intensity == pytest.approx(1.0, rel=0.01), (
            f"With 6 workers on tiny territory, intensity should hit cap: got {intensity:.4f}"
        )

    def test_no_workers_resets_intensity_to_zero(self, services: ServiceContainer) -> None:
        """Territory with no production has intensity = 0.0.

        If no workers produce on a territory in a given tick,
        extraction_intensity should be 0.0 (or reset to 0.0).
        """
        graph: nx.DiGraph = BabylonGraph()
        # Territory with pre-existing intensity (from previous tick)
        _create_territory_node(
            graph, "T001", biocapacity=100.0, max_biocapacity=100.0, extraction_intensity=0.5
        )
        # No workers

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity == 0.0, (
            f"Territory without workers should have intensity=0.0, got {intensity:.4f}"
        )

    def test_dead_workers_do_not_contribute(self, services: ServiceContainer) -> None:
        """Inactive workers don't contribute to extraction.

        Dead workers (active=False) should not produce or contribute
        to extraction_intensity.
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0, active=False)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity == 0.0, f"Dead worker should not contribute: got {intensity:.4f}"

    def test_depleted_territory_has_lower_intensity(self, services: ServiceContainer) -> None:
        """Low biocapacity reduces production, thus extraction.

        Production = base_labor_power * (biocapacity / max_biocapacity)
        At 50% biocapacity, production is halved, so intensity is halved.
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=50.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        weekly_labor_power = services.defines.economy.base_labor_power / 52
        expected_production = weekly_labor_power * 0.5  # Half biocapacity ratio
        expected_intensity = expected_production / 100.0

        intensity = graph.nodes["T001"].get("extraction_intensity", 0.0)
        assert intensity == pytest.approx(expected_intensity, rel=0.01), (
            f"Depleted territory should have lower intensity: "
            f"expected={expected_intensity:.6f}, got={intensity:.6f}"
        )

    def test_workers_on_different_territories_set_independent_intensities(
        self, services: ServiceContainer
    ) -> None:
        """Workers on separate territories affect only their territory."""
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_worker_node(graph, "COMPRADOR_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_territory_node(graph, "T002", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")
        _create_tenancy_edge(graph, "COMPRADOR_ID", "T002")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})

        weekly_labor_power = services.defines.economy.base_labor_power / 52
        expected_intensity = weekly_labor_power / 100.0

        intensity_t1 = graph.nodes["T001"].get("extraction_intensity", 0.0)
        intensity_t2 = graph.nodes["T002"].get("extraction_intensity", 0.0)

        assert intensity_t1 == pytest.approx(expected_intensity, rel=0.01)
        assert intensity_t2 == pytest.approx(expected_intensity, rel=0.01)


@pytest.mark.unit
class TestExtractionIntensityCausesDepletion:
    """Integration: Production → extraction_intensity → Metabolism → depletion."""

    def test_production_causes_biocapacity_decline(self, services: ServiceContainer) -> None:
        """Worker production degrades territory biocapacity.

        When ProductionSystem sets extraction_intensity > breakeven,
        MetabolismSystem should reduce biocapacity.

        With 50 workers at full biocapacity:
            production_per_worker = 1.0/52 = 0.0192
            total_production = 50 * 0.0192 = 0.96
            intensity = 0.96 / 100 = 0.0096

        This is below breakeven (0.0167), so we need MORE workers.
        With 100 workers:
            total_production = 100 * 0.0192 = 1.92
            intensity = 1.92 / 100 = 0.0192 > 0.0167

        Biocapacity delta at max capacity (no regeneration):
            extraction = 0.0192 * 100 * 1.2 = 2.304
            regeneration = 0 (at max capacity)
            delta = 0 - 2.304 = -2.304

        But actually regeneration happens below max:
            regeneration = 0.02 * 100 = 2.0
            extraction = 0.0192 * 100 * 1.2 = 2.304
            delta = 2.0 - 2.304 = -0.304
        """
        graph: nx.DiGraph = BabylonGraph()

        # Create 100 workers for intensity > breakeven
        for i in range(100):
            _create_worker_node(graph, f"C{i:03d}", wealth=0.0)
            _create_tenancy_edge(graph, f"C{i:03d}", "T001")

        _create_territory_node(
            graph,
            "T001",
            biocapacity=99.0,  # Slightly below max to enable regeneration
            max_biocapacity=100.0,
            regeneration_rate=0.02,
        )

        initial_biocapacity = graph.nodes["T001"]["biocapacity"]

        # Run Production to set extraction_intensity
        production = ProductionSystem()
        production.step(graph, services, {"tick": 1})

        # Run Metabolism to apply biocapacity change
        metabolism = MetabolismSystem()
        metabolism.step(graph, services, {"tick": 1})

        final_biocapacity = graph.nodes["T001"]["biocapacity"]

        assert final_biocapacity < initial_biocapacity, (
            f"Biocapacity should decline with high extraction: "
            f"initial={initial_biocapacity:.2f}, final={final_biocapacity:.2f}"
        )

    def test_biocapacity_decline_reduces_production(self, services: ServiceContainer) -> None:
        """Lower biocapacity → lower production (feedback loop).

        This verifies the negative feedback: as biocapacity depletes,
        production decreases, which eventually slows depletion.
        """
        graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(graph, "T001", biocapacity=50.0, max_biocapacity=100.0)
        _create_tenancy_edge(graph, "PERIPHERY_WORKER_ID", "T001")

        # Full biocapacity production
        full_graph: nx.DiGraph = BabylonGraph()
        _create_worker_node(full_graph, "PERIPHERY_WORKER_ID", wealth=0.0)
        _create_territory_node(full_graph, "T001", biocapacity=100.0, max_biocapacity=100.0)
        _create_tenancy_edge(full_graph, "PERIPHERY_WORKER_ID", "T001")

        system = ProductionSystem()
        system.step(graph, services, {"tick": 1})
        system.step(full_graph, services, {"tick": 1})

        depleted_production = graph.nodes["PERIPHERY_WORKER_ID"]["wealth"]
        full_production = full_graph.nodes["PERIPHERY_WORKER_ID"]["wealth"]

        assert depleted_production < full_production, (
            f"Depleted territory should produce less: "
            f"depleted={depleted_production:.4f}, full={full_production:.4f}"
        )
        assert depleted_production == pytest.approx(full_production * 0.5, rel=0.01), (
            f"At 50% biocapacity, production should be 50%: "
            f"depleted={depleted_production:.4f}, expected={full_production * 0.5:.4f}"
        )
