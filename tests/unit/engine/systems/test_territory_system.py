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
from babylon.models.enums import EdgeType, OperationalProfile, SectorType, TerritoryType

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


# =============================================================================
# SINK NODE TESTS (Sprint 3.7: The Carceral Geography)
# =============================================================================


@pytest.mark.unit
class TestFindSinkNode:
    """Tests for _find_sink_node method.

    Sprint 3.7: The Carceral Geography - Necropolitical Triad.
    The sink node finder locates connected containment/elimination zones
    for displaced populations to flow into.

    Priority order: CONCENTRATION_CAMP > PENAL_COLONY > RESERVATION
    """

    def test_find_sink_node_returns_concentration_camp_priority(self) -> None:
        """CONCENTRATION_CAMP takes priority over other sink types.

        When multiple sink nodes are adjacent, the most severe
        (elimination > extraction > containment) takes priority.
        This models the escalation logic of carceral geography.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # Source territory (under eviction)
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            heat=0.9,
            population=1000,
            under_eviction=True,
        )
        # Reservation (lowest priority)
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Pine Ridge",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.RESERVATION,
            population=500,
        )
        # Penal Colony (medium priority)
        graph.add_node(
            "T003",
            _node_type="territory",
            id="T003",
            name="Angola",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PENAL_COLONY,
            population=200,
        )
        # Concentration Camp (highest priority)
        graph.add_node(
            "T004",
            _node_type="territory",
            id="T004",
            name="Internment Zone",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.CONCENTRATION_CAMP,
            population=100,
        )
        # Add adjacency edges
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)
        graph.add_edge("T001", "T003", edge_type=EdgeType.ADJACENCY)
        graph.add_edge("T001", "T004", edge_type=EdgeType.ADJACENCY)

        system = TerritorySystem()

        # Act
        result = system._find_sink_node("T001", graph)

        # Assert: concentration camp has highest priority
        assert result == "T004"

    def test_find_sink_node_returns_penal_colony_when_no_camp(self) -> None:
        """PENAL_COLONY is chosen when no CONCENTRATION_CAMP is adjacent."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            heat=0.9,
            population=1000,
            under_eviction=True,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Reservation",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.RESERVATION,
            population=500,
        )
        graph.add_node(
            "T003",
            _node_type="territory",
            id="T003",
            name="Prison",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PENAL_COLONY,
            population=200,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)
        graph.add_edge("T001", "T003", edge_type=EdgeType.ADJACENCY)

        system = TerritorySystem()

        # Act
        result = system._find_sink_node("T001", graph)

        # Assert: penal colony is chosen (no camp available)
        assert result == "T003"

    def test_find_sink_node_returns_reservation_when_no_higher_priority(self) -> None:
        """RESERVATION is chosen when no PENAL_COLONY or CONCENTRATION_CAMP."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            population=1000,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Reservation",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.RESERVATION,
            population=500,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        system = TerritorySystem()

        # Act
        result = system._find_sink_node("T001", graph)

        # Assert: reservation is chosen
        assert result == "T002"

    def test_find_sink_node_returns_none_when_no_sinks(self) -> None:
        """Returns None when no sink nodes are adjacent.

        This triggers fallback to the original "disappear" behavior.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            population=1000,
        )
        # Adjacent territory is CORE (not a sink)
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Suburbs",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.CORE,
            population=2000,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        system = TerritorySystem()

        # Act
        result = system._find_sink_node("T001", graph)

        # Assert: no sink found
        assert result is None


# =============================================================================
# POPULATION TRANSFER TESTS (Sprint 3.7)
# =============================================================================


@pytest.mark.unit
class TestEvictionPopulationTransfer:
    """Tests for population transfer during eviction.

    Sprint 3.7: The Carceral Geography.
    Instead of "disappearing" displaced populations, they are
    transferred to connected sink nodes.
    """

    def test_eviction_transfers_population_to_sink(self) -> None:
        """Population displaced during eviction flows to sink node.

        Formula: displaced = current_pop * displacement_rate
        Target sink receives: sink_pop + displaced
        Source loses: source_pop - displaced
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=True,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Prison",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PENAL_COLONY,
            heat=0.0,
            population=200,
            under_eviction=False,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        services = ServiceContainer.create()  # Default displacement_rate=0.1
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: population transferred
        # Displaced = 1000 * 0.1 = 100
        # T001: 1000 - 100 = 900
        # T002: 200 + 100 = 300
        assert graph.nodes["T001"]["population"] == 900
        assert graph.nodes["T002"]["population"] == 300

    def test_eviction_deletes_population_when_no_sink(self) -> None:
        """Population disappears if no sink node connected (fallback).

        This preserves the original behavior when no carceral
        infrastructure is present.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Ghetto",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.PERIPHERY,
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.9,
            rent_level=1.0,
            population=1000,
            under_eviction=True,
        )
        # Only adjacent to CORE territory (not a sink)
        graph.add_node(
            "T002",
            _node_type="territory",
            id="T002",
            name="Suburbs",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=TerritoryType.CORE,
            population=2000,
            under_eviction=False,
        )
        graph.add_edge("T001", "T002", edge_type=EdgeType.ADJACENCY)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: population just disappeared (original behavior)
        # T001: 1000 * (1 - 0.1) = 900
        # T002: unchanged at 2000 (not a sink)
        assert graph.nodes["T001"]["population"] == 900
        assert graph.nodes["T002"]["population"] == 2000


# =============================================================================
# NECROPOLITICS TESTS (Sprint 3.7)
# =============================================================================


@pytest.mark.unit
class TestNecropolitics:
    """Tests for necropolitical processing of sink nodes.

    Sprint 3.7: The Carceral Geography - Necropolitical Triad.
    Sink nodes apply special effects each tick:
    - CONCENTRATION_CAMP: population *= (1 - decay_rate) [elimination]
    - PENAL_COLONY: connected SocialClass.organization = 0.0 [suppression]
    """

    def test_concentration_camp_eliminates_population(self) -> None:
        """CONCENTRATION_CAMP territories decay population each tick.

        Formula: population *= (1 - concentration_camp_decay_rate)
        Default decay_rate = 0.2, so population * 0.8

        This models the elimination function of carceral geography.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Internment Zone",
            sector_type=SectorType.GOVERNMENT,
            territory_type=TerritoryType.CONCENTRATION_CAMP,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.0,
            population=1000,
            under_eviction=False,
        )

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: population decayed by 20%
        # 1000 * 0.8 = 800
        assert graph.nodes["T001"]["population"] == 800

    def test_penal_colony_suppresses_connected_class_organization(self) -> None:
        """PENAL_COLONY suppresses organization of connected SocialClass.

        Classes connected via TENANCY edge to a penal colony
        have their organization set to 0.0 each tick.

        This models the atomization effect of mass incarceration.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        # Penal colony territory
        graph.add_node(
            "T001",
            _node_type="territory",
            id="T001",
            name="Angola Prison",
            sector_type=SectorType.INDUSTRIAL,
            territory_type=TerritoryType.PENAL_COLONY,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.0,
            population=500,
            under_eviction=False,
        )
        # Social class with high organization
        graph.add_node(
            "C001",
            _node_type="social_class",
            id="C001",
            name="Prisoners",
            organization=0.8,  # High organization
            wealth=1.0,
        )
        # TENANCY edge from class to territory
        graph.add_edge("C001", "T001", edge_type=EdgeType.TENANCY)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = TerritorySystem()

        # Act
        system.step(graph, services, context)

        # Assert: organization suppressed to 0.0
        assert graph.nodes["C001"]["organization"] == pytest.approx(0.0, abs=0.01)
