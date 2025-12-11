"""Integration tests for TopologyMonitor (Sprint 3.1).

These tests verify TopologyMonitor integration with the Simulation facade,
testing real multi-tick simulation runs with various network topologies.

Test Scenarios:
    A. Full Simulation Lifecycle - Observer receives notifications, history populated
    B. Fragile Star Network - Hub removal fragments network (Sword of Damocles)
    C. Resilient Mesh Network - 20% removal does NOT destroy giant component
    D. Gaseous State Detection - Isolated nodes have percolation_ratio < 0.1

Key Integration Points:
    - Simulation.run() triggers observer lifecycle hooks
    - TopologyMonitor.history captures snapshots each tick
    - test_resilience() correctly identifies fragile vs. resilient networks
"""

from __future__ import annotations

import pytest

from babylon.engine.factories import create_proletariat
from babylon.engine.simulation import Simulation
from babylon.engine.topology_monitor import (
    TopologyMonitor,
    test_resilience,
)
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.world_state import WorldState

# =============================================================================
# HELPER FUNCTIONS: WorldState Factories for Topology Tests
# =============================================================================


def create_star_topology_state(num_spokes: int = 10) -> WorldState:
    """Create a WorldState with star topology (fragile - hub is single point of failure).

    The hub node (C000) connects to all spoke nodes (C001, C002, ...).
    Spokes have no connections to each other.

    Args:
        num_spokes: Number of spoke nodes around the hub (default 10).

    Returns:
        WorldState with hub + spoke entities and SOLIDARITY edges from hub to spokes.
    """
    entities: dict[str, SocialClass] = {}
    relationships: list[Relationship] = []

    # Hub node
    hub = SocialClass(
        id="C000",
        name="Hub Leader",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=0.9,  # Highly organized (central figure)
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )
    entities["C000"] = hub

    # Spoke nodes connected only to hub
    for i in range(1, num_spokes + 1):
        spoke_id = f"C{i:03d}"
        spoke = SocialClass(
            id=spoke_id,
            name=f"Spoke Worker {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=0.0,  # type: ignore[arg-type]  # Validator converts float
            organization=0.1,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        entities[spoke_id] = spoke

        # SOLIDARITY edge from hub to spoke
        solidarity_edge = Relationship(
            source_id="C000",
            target_id=spoke_id,
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,  # Strong solidarity
        )
        relationships.append(solidarity_edge)

    return WorldState(tick=0, entities=entities, relationships=relationships)


def create_mesh_topology_state(num_nodes: int = 10) -> WorldState:
    """Create a WorldState with mesh topology (resilient - no single point of failure).

    Each node connects to multiple neighbors in a circular mesh pattern.
    Node i connects to nodes i-1, i+1, i-2, i+2 (wrapping at boundaries).

    Args:
        num_nodes: Number of nodes in the mesh (default 10).

    Returns:
        WorldState with mesh-connected entities and SOLIDARITY edges.
    """
    entities: dict[str, SocialClass] = {}
    relationships: list[Relationship] = []

    # Create nodes
    for i in range(num_nodes):
        node_id = f"C{i:03d}"
        node = SocialClass(
            id=node_id,
            name=f"Mesh Worker {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=0.0,  # type: ignore[arg-type]  # Validator converts float
            organization=0.3,
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        entities[node_id] = node

    # Create mesh connections (each node connects to 4 neighbors)
    # Use a set to avoid duplicate edges
    edge_pairs: set[tuple[str, str]] = set()
    for i in range(num_nodes):
        source_id = f"C{i:03d}"
        # Connect to neighbors at distance 1 and 2 (wrapping)
        for offset in [1, 2]:
            neighbor_idx = (i + offset) % num_nodes
            target_id = f"C{neighbor_idx:03d}"
            # Normalize edge direction to avoid duplicates
            pair = tuple(sorted([source_id, target_id]))
            if pair not in edge_pairs:
                edge_pairs.add(pair)  # type: ignore[arg-type]
                solidarity_edge = Relationship(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,
                )
                relationships.append(solidarity_edge)

    return WorldState(tick=0, entities=entities, relationships=relationships)


def create_gaseous_state(num_nodes: int = 20) -> WorldState:
    """Create a WorldState with completely isolated nodes (gaseous/atomized state).

    All nodes are social_class entities with no SOLIDARITY edges between them.
    Each node is its own connected component.

    Args:
        num_nodes: Number of isolated nodes (default 20 for percolation < 0.1).

    Returns:
        WorldState with isolated entities and no SOLIDARITY relationships.
    """
    entities: dict[str, SocialClass] = {}

    for i in range(num_nodes):
        node_id = f"C{i:03d}"
        node = SocialClass(
            id=node_id,
            name=f"Isolated Worker {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=0.5,
            ideology=0.0,  # type: ignore[arg-type]  # Validator converts float
            organization=0.05,  # Very low organization (atomized)
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )
        entities[node_id] = node

    # No SOLIDARITY relationships - fully atomized
    return WorldState(tick=0, entities=entities, relationships=[])


# =============================================================================
# SCENARIO A: Full Simulation Lifecycle
# =============================================================================


@pytest.mark.integration
class TestFullSimulationLifecycle:
    """Test TopologyMonitor integration with Simulation lifecycle."""

    def test_observer_receives_start_notification(self) -> None:
        """TopologyMonitor.on_simulation_start is called on first step."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])

        # Before any steps, history should be empty
        assert len(monitor.history) == 0

        # First step triggers on_simulation_start
        sim.step()

        # Initial snapshot + first tick snapshot
        assert len(monitor.history) == 2
        assert monitor.history[0].tick == 0  # Initial
        assert monitor.history[1].tick == 1  # After first step

    def test_history_accumulates_over_multiple_ticks(self) -> None:
        """TopologyMonitor.history has one snapshot per tick plus initial."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])

        num_ticks = 7
        sim.run(num_ticks)

        # History: initial (tick 0) + 7 tick snapshots
        expected_snapshots = num_ticks + 1
        assert len(monitor.history) == expected_snapshots

        # Verify tick sequence
        for i, snapshot in enumerate(monitor.history):
            assert snapshot.tick == i

    def test_snapshots_have_valid_metrics(self) -> None:
        """All snapshots have non-negative metrics and ratio in [0, 1]."""
        state = create_mesh_topology_state(num_nodes=10)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.run(5)

        for snapshot in monitor.history:
            # Non-negative counts
            assert snapshot.num_components >= 0
            assert snapshot.max_component_size >= 0
            assert snapshot.total_nodes >= 0
            assert snapshot.potential_liquidity >= 0
            assert snapshot.actual_liquidity >= 0

            # Ratio must be in [0, 1]
            assert 0.0 <= snapshot.percolation_ratio <= 1.0

            # L_max cannot exceed total nodes
            assert snapshot.max_component_size <= snapshot.total_nodes

    def test_simulation_end_notifies_observer(self) -> None:
        """Calling sim.end() triggers on_simulation_end notification."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.run(3)

        # Verify history exists before end
        assert len(monitor.history) == 4  # Initial + 3 ticks

        # Calling end() should not add more snapshots (just logs summary)
        sim.end()
        assert len(monitor.history) == 4  # Still 4 snapshots

    def test_multiple_observers_all_notified(self) -> None:
        """Multiple TopologyMonitors each receive notifications."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()
        monitor1 = TopologyMonitor()
        monitor2 = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor1, monitor2])
        sim.run(3)

        # Both monitors should have same history length
        assert len(monitor1.history) == len(monitor2.history)
        assert len(monitor1.history) == 4

        # Snapshots should be equivalent
        for s1, s2 in zip(monitor1.history, monitor2.history, strict=True):
            assert s1.tick == s2.tick
            assert s1.percolation_ratio == s2.percolation_ratio


# =============================================================================
# SCENARIO B: Fragile Star Network (Sword of Damocles)
# =============================================================================


@pytest.mark.integration
class TestFragileStarNetwork:
    """Test that star topology is detected as fragile (Sword of Damocles)."""

    def test_star_topology_has_single_giant_component(self) -> None:
        """Star topology with hub has all nodes in one component."""
        state = create_star_topology_state(num_spokes=10)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]
        # All 11 nodes (1 hub + 10 spokes) in one component
        assert initial_snapshot.total_nodes == 11
        assert initial_snapshot.num_components == 1
        assert initial_snapshot.max_component_size == 11
        assert initial_snapshot.percolation_ratio == pytest.approx(1.0)

    def test_hub_removal_fragments_network(self) -> None:
        """Removing the hub node from star topology destroys giant component."""
        state = create_star_topology_state(num_spokes=10)
        graph = state.to_graph()

        # Seed that removes the hub (node C000) deterministically
        # We'll test with seed=0 and check if hub is removed
        # If not, we'll find a seed that does remove the hub
        result = test_resilience(graph, removal_rate=0.2, seed=0)

        # Original L_max = 11 (all connected via hub)
        assert result.original_max_component == 11

        # With 20% removal (2 nodes), if hub is removed:
        # - Post-purge components are isolated spokes (L_max = 1)
        # - Network is NOT resilient
        # If hub is not removed, L_max drops by 2 at most (9)
        # Either way, let's verify the structure
        if result.post_purge_max_component <= 1:
            # Hub was removed - network fragmented
            assert result.is_resilient is False
        else:
            # Hub survived this seed - try another
            result_seed_1 = test_resilience(graph, removal_rate=0.2, seed=1)
            result_seed_2 = test_resilience(graph, removal_rate=0.2, seed=2)
            result_seed_3 = test_resilience(graph, removal_rate=0.2, seed=3)

            # At least one seed should remove the hub
            results = [result, result_seed_1, result_seed_2, result_seed_3]
            fragile_results = [r for r in results if r.post_purge_max_component <= 1]

            # Star topology should be fragile for at least one seed
            assert len(fragile_results) > 0, "Star topology should be fragile under some seed"

    def test_star_topology_resilience_false_on_hub_removal(self) -> None:
        """test_resilience returns is_resilient=False when hub removed."""
        state = create_star_topology_state(num_spokes=5)
        graph = state.to_graph()

        # With 6 nodes and 20% removal, we remove 1 node
        # Try multiple seeds to find one that removes the hub
        max_post_purge = 0
        min_post_purge = 6
        fragile_seed = None

        for seed in range(20):
            result = test_resilience(graph, removal_rate=0.2, seed=seed)
            max_post_purge = max(max_post_purge, result.post_purge_max_component)
            min_post_purge = min(min_post_purge, result.post_purge_max_component)
            if not result.is_resilient:
                fragile_seed = seed

        # Star topology should be fragile for at least some seeds
        # When hub is removed, L_max drops to 1 (isolated spokes)
        assert min_post_purge <= 1, "Hub removal should fragment network to isolated nodes"
        assert fragile_seed is not None, "Should find at least one fragile seed"


# =============================================================================
# SCENARIO C: Resilient Mesh Network
# =============================================================================


@pytest.mark.integration
class TestResilientMeshNetwork:
    """Test that mesh topology is detected as resilient."""

    def test_mesh_topology_has_single_component(self) -> None:
        """Mesh topology has all nodes connected in one component."""
        state = create_mesh_topology_state(num_nodes=10)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]
        # All 10 nodes in one component
        assert initial_snapshot.total_nodes == 10
        assert initial_snapshot.num_components == 1
        assert initial_snapshot.max_component_size == 10
        assert initial_snapshot.percolation_ratio == pytest.approx(1.0)

    def test_mesh_survives_20_percent_removal(self) -> None:
        """Mesh topology maintains giant component after 20% node removal."""
        state = create_mesh_topology_state(num_nodes=10)
        graph = state.to_graph()

        # Test with fixed seed for reproducibility
        result = test_resilience(graph, removal_rate=0.2, seed=42)

        # Original L_max = 10 (all connected)
        assert result.original_max_component == 10

        # After 20% removal (2 nodes), mesh should remain connected
        # Survival threshold is 40%, so need L_max >= 4
        # Mesh with 4 connections per node should easily survive
        assert result.is_resilient is True
        assert result.post_purge_max_component >= 4  # 40% of original

    def test_mesh_resilient_across_multiple_seeds(self) -> None:
        """Mesh topology is resilient across various RNG seeds."""
        state = create_mesh_topology_state(num_nodes=10)
        graph = state.to_graph()

        # Test multiple seeds - mesh should be resilient for all
        resilient_count = 0
        for seed in range(10):
            result = test_resilience(graph, removal_rate=0.2, seed=seed)
            if result.is_resilient:
                resilient_count += 1

        # Mesh should be resilient for most/all seeds
        assert resilient_count >= 8, "Mesh should be resilient for at least 80% of seeds"

    def test_mesh_high_potential_and_actual_liquidity(self) -> None:
        """Mesh topology has high liquidity (both potential and actual)."""
        state = create_mesh_topology_state(num_nodes=10)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        # All edges are strong (0.8) so potential == actual
        assert initial_snapshot.potential_liquidity > 0
        assert initial_snapshot.actual_liquidity > 0
        # With all edges at 0.8, potential and actual should be equal
        assert initial_snapshot.potential_liquidity == initial_snapshot.actual_liquidity


# =============================================================================
# SCENARIO D: Gaseous State Detection
# =============================================================================


@pytest.mark.integration
class TestGaseousStateDetection:
    """Test detection of gaseous (atomized) movement state."""

    def test_isolated_nodes_have_low_percolation(self) -> None:
        """WorldState with isolated nodes has percolation_ratio < 0.1."""
        state = create_gaseous_state(num_nodes=20)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        # With 20 isolated nodes, L_max = 1, percolation = 1/20 = 0.05
        assert initial_snapshot.total_nodes == 20
        assert initial_snapshot.max_component_size == 1
        assert initial_snapshot.percolation_ratio == pytest.approx(0.05)
        assert initial_snapshot.percolation_ratio < 0.1  # Gaseous threshold

    def test_num_components_equals_num_nodes_when_isolated(self) -> None:
        """Each isolated node is its own component."""
        state = create_gaseous_state(num_nodes=15)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        # Each node is its own component
        assert initial_snapshot.num_components == initial_snapshot.total_nodes
        assert initial_snapshot.num_components == 15

    def test_gaseous_state_has_zero_liquidity(self) -> None:
        """Gaseous state with no SOLIDARITY edges has zero liquidity."""
        state = create_gaseous_state(num_nodes=20)
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        # No SOLIDARITY edges means no liquidity
        assert initial_snapshot.potential_liquidity == 0
        assert initial_snapshot.actual_liquidity == 0

    def test_gaseous_state_is_vacuously_resilient(self) -> None:
        """Isolated nodes are 'resilient' because there's nothing to fragment."""
        state = create_gaseous_state(num_nodes=10)
        graph = state.to_graph()

        result = test_resilience(graph, removal_rate=0.2, seed=42)

        # Original L_max = 1 (each node is its own component)
        assert result.original_max_component == 1

        # After removal, remaining nodes are still isolated, L_max still 1
        # 1 >= 1 * 0.4 = 0.4, so "resilient" by the math
        # But this is vacuous resilience - there's no structure to destroy
        assert result.is_resilient is True


# =============================================================================
# EDGE CASES AND BOUNDARY CONDITIONS
# =============================================================================


@pytest.mark.integration
class TestTopologyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_state_produces_valid_snapshot(self) -> None:
        """WorldState with no entities produces valid (zeroed) snapshot."""
        state = WorldState(tick=0, entities={}, relationships=[])
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        assert initial_snapshot.total_nodes == 0
        assert initial_snapshot.num_components == 0
        assert initial_snapshot.max_component_size == 0
        assert initial_snapshot.percolation_ratio == 0.0
        assert initial_snapshot.potential_liquidity == 0
        assert initial_snapshot.actual_liquidity == 0

    def test_single_node_state(self) -> None:
        """WorldState with single node produces correct metrics."""
        worker = create_proletariat(id="C001")
        state = WorldState(tick=0, entities={"C001": worker}, relationships=[])
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        assert initial_snapshot.total_nodes == 1
        assert initial_snapshot.num_components == 1
        assert initial_snapshot.max_component_size == 1
        assert initial_snapshot.percolation_ratio == pytest.approx(1.0)

    def test_resilience_test_interval_configuration(self) -> None:
        """TopologyMonitor respects resilience_test_interval setting."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()

        # Test interval of 3: resilience tested at tick 0, 3, 6, ...
        monitor = TopologyMonitor(resilience_test_interval=3)

        sim = Simulation(state, config, observers=[monitor])
        sim.run(6)

        # Check which snapshots have resilience results
        # Initial (tick 0) should have resilience tested
        assert monitor.history[0].is_resilient is not None

        # Tick 1, 2 should NOT have resilience tested
        assert monitor.history[1].is_resilient is None
        assert monitor.history[2].is_resilient is None

        # Tick 3 should have resilience tested
        assert monitor.history[3].is_resilient is not None

        # Tick 4, 5 should NOT have resilience tested
        assert monitor.history[4].is_resilient is None
        assert monitor.history[5].is_resilient is None

        # Tick 6 should have resilience tested
        assert monitor.history[6].is_resilient is not None

    def test_resilience_interval_zero_disables_testing(self) -> None:
        """resilience_test_interval=0 disables all resilience testing."""
        state = create_mesh_topology_state(num_nodes=5)
        config = SimulationConfig()

        monitor = TopologyMonitor(resilience_test_interval=0)

        sim = Simulation(state, config, observers=[monitor])
        sim.run(5)

        # All snapshots should have is_resilient=None
        for snapshot in monitor.history:
            assert snapshot.is_resilient is None

    def test_two_node_connected_pair(self) -> None:
        """Two nodes with SOLIDARITY edge form single component."""
        worker1 = create_proletariat(id="C001", name="Worker 1")
        worker2 = create_proletariat(id="C002", name="Worker 2")
        solidarity = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.8,
        )

        state = WorldState(
            tick=0,
            entities={"C001": worker1, "C002": worker2},
            relationships=[solidarity],
        )
        config = SimulationConfig()
        monitor = TopologyMonitor()

        sim = Simulation(state, config, observers=[monitor])
        sim.step()

        initial_snapshot = monitor.history[0]

        assert initial_snapshot.total_nodes == 2
        assert initial_snapshot.num_components == 1
        assert initial_snapshot.max_component_size == 2
        assert initial_snapshot.percolation_ratio == pytest.approx(1.0)
        assert initial_snapshot.potential_liquidity == 1  # One edge > 0.1
        assert initial_snapshot.actual_liquidity == 1  # One edge > 0.5
