"""Tests for TerritorySystem - Layer 0 Territorial Dynamics.

Sprint 3.5.4: The Territorial Substrate.

TDD Red Phase: These tests define the contract for the TerritorySystem.

Test Intent:
- Heat dynamics: HIGH_PROFILE gains heat, LOW_PROFILE decays heat
- Heat cap at 1.0
- Eviction trigger when heat >= threshold
- Rent spike during eviction
- Population displacement during eviction
- Heat spillover via ADJACENCY edges
"""

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.territory import TerritorySystem
from babylon.models.config import SimulationConfig
from babylon.models.enums import EdgeType, OperationalProfile, SectorType

# =============================================================================
# BASIC SYSTEM TESTS
# =============================================================================


@pytest.mark.unit
class TestTerritorySystemBasic:
    """Test basic TerritorySystem behavior."""

    def test_system_has_name(self) -> None:
        """TerritorySystem should have a descriptive name."""
        system = TerritorySystem()
        assert system.name == "Territory"

    def test_ignores_non_territory_nodes(self) -> None:
        """System should only process nodes with _node_type='territory'."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # Social class node (should be ignored)
        graph.add_node(
            "C001",
            _node_type="social_class",
            wealth=10.0,
            ideology=0.0,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: No changes to social class node
        assert graph.nodes["C001"]["wealth"] == 10.0


# =============================================================================
# HEAT DYNAMICS TESTS
# =============================================================================


@pytest.mark.unit
class TestTerritoryHeatDynamics:
    """Test heat accumulation and decay based on operational profile."""

    def test_high_profile_gains_heat(self) -> None:
        """HIGH_PROFILE territories gain heat each tick.

        Formula: heat = min(1.0, heat + high_profile_heat_gain)
        Default gain = 0.15
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.2,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: heat increased by 0.15 (default)
        assert graph.nodes["T001"]["heat"] == pytest.approx(0.35, abs=0.01)

    def test_low_profile_decays_heat(self) -> None:
        """LOW_PROFILE territories decay heat each tick.

        Formula: heat = max(0.0, heat * (1 - heat_decay_rate))
        Default decay rate = 0.1, so heat * 0.9
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Docks",
            sector_type=SectorType.DOCKS,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.5,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: heat decayed by 10% (multiplied by 0.9)
        assert graph.nodes["T001"]["heat"] == pytest.approx(0.45, abs=0.01)

    def test_heat_capped_at_one(self) -> None:
        """Heat cannot exceed 1.0."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.95,  # Near cap
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: heat capped at 1.0
        assert graph.nodes["T001"]["heat"] == 1.0

    def test_heat_cannot_go_negative(self) -> None:
        """Heat cannot go below 0.0."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.01,  # Very low
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: heat stays non-negative
        assert graph.nodes["T001"]["heat"] >= 0.0


# =============================================================================
# EVICTION PIPELINE TESTS
# =============================================================================


@pytest.mark.unit
class TestTerritoryEvictionPipeline:
    """Test eviction trigger and effects."""

    def test_eviction_triggered_at_threshold(self) -> None:
        """Eviction triggered when heat >= eviction_heat_threshold.

        Default threshold = 0.8
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.85,  # Above threshold
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: eviction started
        assert graph.nodes["T001"]["under_eviction"] is True

    def test_no_eviction_below_threshold(self) -> None:
        """No eviction if heat < eviction_heat_threshold."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Docks",
            sector_type=SectorType.DOCKS,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.5,  # Below threshold
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: no eviction
        assert graph.nodes["T001"]["under_eviction"] is False

    def test_rent_spike_during_eviction(self) -> None:
        """Rent spikes during eviction.

        Formula: rent_level *= rent_spike_multiplier
        Default multiplier = 1.5
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=True,  # Already under eviction
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: rent spiked by 1.5x
        assert graph.nodes["T001"]["rent_level"] == pytest.approx(1.5, abs=0.01)

    def test_population_displacement_during_eviction(self) -> None:
        """Population displaced during eviction.

        Formula: population = floor(population * (1 - displacement_rate))
        Default rate = 0.1, so population * 0.9
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=True,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: population reduced by 10%
        assert graph.nodes["T001"]["population"] == 900


# =============================================================================
# HEAT SPILLOVER TESTS
# =============================================================================


@pytest.mark.unit
class TestTerritoryHeatSpillover:
    """Test heat spillover via ADJACENCY edges."""

    def test_heat_spills_to_adjacent_territories(self) -> None:
        """Heat spills to adjacent territories.

        Formula: adjacent.heat += source.heat * heat_spillover_rate
        Default rate = 0.05
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # Source territory with high heat
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.6,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )
        # Adjacent territory with low heat
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.1,
            rent_level=1.0,
            population=2000,
            under_eviction=False,
        )
        # ADJACENCY edge
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: T002 heat increased by spillover
        # Spillover = 0.6 * 0.05 = 0.03
        # But also T002 heat decays (LOW_PROFILE): 0.1 * 0.9 = 0.09
        # Final = 0.09 + 0.03 = 0.12
        # Note: Spillover is applied after heat dynamics
        expected_base = 0.1 * 0.9  # decay
        expected_spillover = 0.6 * 0.05  # spillover from T001
        expected_total = expected_base + expected_spillover
        assert graph.nodes["T002"]["heat"] == pytest.approx(expected_total, abs=0.02)

    def test_no_spillover_from_non_adjacent(self) -> None:
        """Heat does not spill to non-adjacent territories."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Docks",
            sector_type=SectorType.DOCKS,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.1,
            rent_level=1.0,
            population=2000,
            under_eviction=False,
        )
        # No ADJACENCY edge between them

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: T002 heat only decayed, no spillover
        assert graph.nodes["T002"]["heat"] == pytest.approx(0.09, abs=0.01)

    def test_spillover_capped_at_one(self) -> None:
        """Heat from spillover cannot exceed 1.0."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=1.0,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.99,  # Near cap
            rent_level=1.0,
            population=2000,
            under_eviction=False,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: T002 heat capped at 1.0
        assert graph.nodes["T002"]["heat"] <= 1.0


# =============================================================================
# CONFIG PARAMETER TESTS
# =============================================================================


@pytest.mark.unit
class TestTerritorySystemConfig:
    """Test that TerritorySystem respects configuration parameters."""

    def test_custom_heat_gain(self) -> None:
        """System uses config's high_profile_heat_gain."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="University",
            sector_type=SectorType.UNIVERSITY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.2,
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        config = SimulationConfig(high_profile_heat_gain=0.25)
        services = ServiceContainer.create(config)
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: heat increased by custom 0.25
        assert graph.nodes["T001"]["heat"] == pytest.approx(0.45, abs=0.01)

    def test_custom_eviction_threshold(self) -> None:
        """System uses config's eviction_heat_threshold."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Residential",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.65,  # Above custom threshold, below default
            rent_level=1.0,
            population=1000,
            under_eviction=False,
        )

        config = SimulationConfig(eviction_heat_threshold=0.6)
        services = ServiceContainer.create(config)
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: eviction triggered with custom threshold
        assert graph.nodes["T001"]["under_eviction"] is True

    def test_custom_rent_spike_multiplier(self) -> None:
        """System uses config's rent_spike_multiplier."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Commercial",
            sector_type=SectorType.COMMERCIAL,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=True,
        )

        config = SimulationConfig(rent_spike_multiplier=2.0)
        services = ServiceContainer.create(config)
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: rent spiked by custom 2.0x
        assert graph.nodes["T001"]["rent_level"] == pytest.approx(2.0, abs=0.01)
