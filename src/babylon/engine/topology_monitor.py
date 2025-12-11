"""Topology Monitor for phase transition detection (Sprint 3.1).

The TopologyMonitor is a SimulationObserver that tracks the "condensation"
of revolutionary consciousness through the social graph using percolation
theory. It detects phase transitions from "atomized" (gaseous) to
"condensed" (liquid) movement states.

Theoretical Model:
    - Gaseous State: Many small, disconnected components. Vulnerable to purge.
    - Liquid State: Giant Component (L_max) spans >50% of network. Resilient.
    - Phase Shift: The tick where the graph crosses percolation threshold.

Key Metrics:
    - num_components: Number of disconnected solidarity cells
    - max_component_size (L_max): Largest connected component
    - percolation_ratio: L_max / N (giant component dominance)
    - potential_liquidity: SOLIDARITY edges > 0.1 (sympathizers)
    - actual_liquidity: SOLIDARITY edges > 0.5 (cadre)

Narrative States:
    - "Gaseous": percolation < 0.1 (atomized, vulnerable)
    - "Condensation": percolation crosses 0.5 (vanguard formed)
    - "Brittle": potential >> actual (broad but lacks discipline)
    - "Sword of Damocles": resilience test fails (purge would destroy)
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import networkx as nx

from babylon.models.enums import EdgeType
from babylon.models.topology_metrics import ResilienceResult, TopologySnapshot

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# =============================================================================
# CONSTANTS
# =============================================================================

# Thresholds for narrative detection
GASEOUS_THRESHOLD = 0.1  # percolation_ratio below this = atomized
CONDENSATION_THRESHOLD = 0.5  # percolation_ratio crossing this = phase shift
BRITTLE_MULTIPLIER = 2  # potential > actual * this = brittle

# Thresholds for liquidity classification
POTENTIAL_MIN_STRENGTH = 0.1  # Sympathizer threshold
ACTUAL_MIN_STRENGTH = 0.5  # Cadre threshold

# Default resilience test parameters
DEFAULT_REMOVAL_RATE = 0.2  # Remove 20% of nodes
DEFAULT_SURVIVAL_THRESHOLD = 0.4  # L_max must survive at 40% of original


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def extract_solidarity_subgraph(
    G: nx.DiGraph[str],
    min_strength: float = 0.0,
) -> nx.Graph[str]:
    """Extract undirected solidarity network from WorldState graph.

    Creates an undirected graph containing only social_class nodes and
    SOLIDARITY edges above the minimum strength threshold. Used for
    connected component analysis.

    Args:
        G: Directed graph from WorldState.to_graph()
        min_strength: Minimum solidarity_strength to include edge (default 0)

    Returns:
        Undirected Graph containing only solidarity connections.
        Isolated social_class nodes are included.

    Note:
        Territory nodes are excluded as they represent spatial substrate,
        not class positions in the solidarity network.
    """
    # Create undirected graph for component analysis
    solidarity_graph: nx.Graph[str] = nx.Graph()

    # Add all social_class nodes (even if isolated)
    for node_id, data in G.nodes(data=True):
        if data.get("_node_type") == "social_class":
            solidarity_graph.add_node(node_id)

    # Add SOLIDARITY edges above threshold
    for u, v, data in G.edges(data=True):
        if (
            data.get("edge_type") == EdgeType.SOLIDARITY
            and data.get("solidarity_strength", 0.0) > min_strength
            and G.nodes[u].get("_node_type") == "social_class"
            and G.nodes[v].get("_node_type") == "social_class"
        ):
            solidarity_graph.add_edge(u, v)

    return solidarity_graph


def calculate_component_metrics(
    solidarity_graph: nx.Graph[str],
    total_social_classes: int,
) -> tuple[int, int, float]:
    """Calculate connected component metrics for solidarity network.

    Args:
        solidarity_graph: Undirected graph of solidarity connections
        total_social_classes: Total number of social_class nodes in system

    Returns:
        Tuple of (num_components, max_component_size, percolation_ratio)
        - num_components: Number of disconnected subgraphs
        - max_component_size: Size of largest component (L_max)
        - percolation_ratio: L_max / N (clamped to [0, 1])
    """
    if total_social_classes == 0:
        return (0, 0, 0.0)

    # Get connected components
    components = list(nx.connected_components(solidarity_graph))
    num_components = len(components)
    max_component_size = 0 if num_components == 0 else max(len(c) for c in components)

    # Calculate percolation ratio
    percolation_ratio = max_component_size / total_social_classes
    # Clamp to [0, 1] for Probability type
    percolation_ratio = max(0.0, min(1.0, percolation_ratio))

    return (num_components, max_component_size, percolation_ratio)


def calculate_liquidity(G: nx.DiGraph[str]) -> tuple[int, int]:
    """Calculate liquidity metrics (potential vs actual solidarity).

    Measures the strength of the solidarity network by counting edges
    at different thresholds:
    - Potential (sympathizers): edges > 0.1 strength
    - Actual (cadre): edges > 0.5 strength

    Args:
        G: Directed graph from WorldState.to_graph()

    Returns:
        Tuple of (potential_liquidity, actual_liquidity)
    """
    potential = 0
    actual = 0

    for _, _, data in G.edges(data=True):
        if data.get("edge_type") == EdgeType.SOLIDARITY:
            strength = data.get("solidarity_strength", 0.0)
            if strength > POTENTIAL_MIN_STRENGTH:
                potential += 1
            if strength > ACTUAL_MIN_STRENGTH:
                actual += 1

    return (potential, actual)


def test_resilience(
    G: nx.DiGraph[str],
    removal_rate: float = DEFAULT_REMOVAL_RATE,
    survival_threshold: float = DEFAULT_SURVIVAL_THRESHOLD,
    seed: int | None = None,
) -> ResilienceResult:
    """Test if solidarity network survives targeted node removal.

    Simulates a "purge" by removing a percentage of nodes and checking
    if the giant component survives. This is the "Sword of Damocles"
    test - a fragile network can be destroyed by targeting key members.

    Args:
        G: Directed graph from WorldState.to_graph()
        removal_rate: Fraction of nodes to remove (default 0.2 = 20%)
        survival_threshold: Required fraction of original L_max to survive
        seed: RNG seed for reproducibility (None = random)

    Returns:
        ResilienceResult with is_resilient flag and metrics.

    Note:
        The original graph is NOT modified. Test operates on a copy.
    """
    # Set up RNG
    rng = random.Random(seed)

    # Extract solidarity subgraph
    solidarity_graph = extract_solidarity_subgraph(G)
    nodes = list(solidarity_graph.nodes())
    total_nodes = len(nodes)

    if total_nodes == 0:
        return ResilienceResult(
            is_resilient=True,  # Vacuously true
            original_max_component=0,
            post_purge_max_component=0,
            removal_rate=removal_rate,
            survival_threshold=survival_threshold,
            seed=seed,
        )

    # Calculate original L_max
    original_components = list(nx.connected_components(solidarity_graph))
    original_max = max(len(c) for c in original_components) if original_components else 0

    # Create copy and remove nodes
    purged_graph = solidarity_graph.copy()
    num_to_remove = max(1, int(total_nodes * removal_rate))
    nodes_to_remove = rng.sample(nodes, min(num_to_remove, total_nodes))
    purged_graph.remove_nodes_from(nodes_to_remove)

    # Calculate post-purge L_max
    post_components = list(nx.connected_components(purged_graph))
    post_max = max(len(c) for c in post_components) if post_components else 0

    # Check resilience
    is_resilient = post_max >= (original_max * survival_threshold)

    return ResilienceResult(
        is_resilient=is_resilient,
        original_max_component=original_max,
        post_purge_max_component=post_max,
        removal_rate=removal_rate,
        survival_threshold=survival_threshold,
        seed=seed,
    )


# =============================================================================
# TOPOLOGY MONITOR OBSERVER
# =============================================================================


class TopologyMonitor:
    """Observer tracking solidarity network condensation.

    Implements SimulationObserver protocol to receive state change
    notifications and analyze the topology of SOLIDARITY edges.

    Monitors:
        - Connected components (atomization vs. condensation)
        - Percolation ratio (L_max / N)
        - Liquidity metrics (potential vs. actual solidarity)
        - Resilience (survives targeted node removal)

    Narrative states logged:
        - Gaseous: percolation < 0.1 (atomized)
        - Liquid: percolation crosses 0.5 (condensation detected)
        - Brittle: potential >> actual (broad but fragile)
        - Fragile: resilience = False (Sword of Damocles)

    Attributes:
        name: Observer identifier ("TopologyMonitor")
        history: List of TopologySnapshot for each tick
    """

    def __init__(
        self,
        resilience_test_interval: int = 5,
        resilience_removal_rate: float = DEFAULT_REMOVAL_RATE,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize TopologyMonitor.

        Args:
            resilience_test_interval: Run resilience test every N ticks
                (0 = disabled). Default 5.
            resilience_removal_rate: Fraction of nodes to remove in test.
                Default 0.2 (20%).
            logger: Logger instance (default: module logger)
        """
        self._history: list[TopologySnapshot] = []
        self._previous_percolation: float = 0.0
        self._resilience_interval: int = resilience_test_interval
        self._removal_rate: float = resilience_removal_rate
        self._logger: logging.Logger = logger or logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return "TopologyMonitor"

    @property
    def history(self) -> list[TopologySnapshot]:
        """Return copy of snapshot history."""
        return list(self._history)

    def on_simulation_start(
        self,
        initial_state: WorldState,
        _config: SimulationConfig,
    ) -> None:
        """Called when simulation begins.

        Initializes history and records initial topology snapshot.

        Args:
            initial_state: WorldState at tick 0
            _config: SimulationConfig for this run (unused)
        """
        self._history.clear()
        self._previous_percolation = 0.0
        self._record_snapshot(initial_state, is_start=True)

    def on_tick(
        self,
        _previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes.

        Records topology snapshot and detects phase transitions.

        Args:
            _previous_state: WorldState before the tick (unused)
            new_state: WorldState after the tick
        """
        self._record_snapshot(new_state, is_start=False)

    def on_simulation_end(self, _final_state: WorldState) -> None:
        """Called when simulation ends.

        Logs summary of topology metrics.

        Args:
            _final_state: Final WorldState when simulation ends (unused)
        """
        self._log_summary()

    def _record_snapshot(self, state: WorldState, is_start: bool = False) -> None:
        """Calculate metrics and record snapshot.

        Args:
            state: Current WorldState to analyze
            is_start: Whether this is the initial snapshot
        """
        # Convert to graph
        graph = state.to_graph()

        # Count social_class nodes
        total_nodes = sum(
            1 for _, data in graph.nodes(data=True) if data.get("_node_type") == "social_class"
        )

        # Extract solidarity subgraph and calculate metrics
        solidarity_graph = extract_solidarity_subgraph(graph)
        num_components, max_component_size, percolation_ratio = calculate_component_metrics(
            solidarity_graph, total_nodes
        )

        # Calculate liquidity
        potential, actual = calculate_liquidity(graph)

        # Run resilience test if interval reached
        is_resilient: bool | None = None
        if self._resilience_interval > 0:
            tick = state.tick
            if is_start or (tick > 0 and tick % self._resilience_interval == 0):
                result = test_resilience(graph, removal_rate=self._removal_rate)
                is_resilient = result.is_resilient

        # Create snapshot
        snapshot = TopologySnapshot(
            tick=state.tick,
            num_components=num_components,
            max_component_size=max_component_size,
            total_nodes=total_nodes,
            percolation_ratio=percolation_ratio,
            potential_liquidity=potential,
            actual_liquidity=actual,
            is_resilient=is_resilient,
        )

        # Log narratives
        self._log_narratives(snapshot)

        # Update state
        self._previous_percolation = percolation_ratio
        self._history.append(snapshot)

    def _log_narratives(self, snapshot: TopologySnapshot) -> None:
        """Generate and log narrative descriptions.

        Args:
            snapshot: Current TopologySnapshot to analyze
        """
        # Gaseous state detection
        if snapshot.percolation_ratio < GASEOUS_THRESHOLD:
            self._logger.info(
                "STATE: Gaseous. Movement is atomized. "
                f"(percolation={snapshot.percolation_ratio:.2f}, "
                f"components={snapshot.num_components})"
            )

        # Phase shift detection (crossing condensation threshold)
        if (
            self._previous_percolation < CONDENSATION_THRESHOLD
            and snapshot.percolation_ratio >= CONDENSATION_THRESHOLD
        ):
            self._logger.info(
                "PHASE SHIFT: Condensation detected. A Vanguard Party has formed. "
                f"(percolation={snapshot.percolation_ratio:.2f}, "
                f"L_max={snapshot.max_component_size})"
            )

        # Brittle movement warning
        if (
            snapshot.potential_liquidity > snapshot.actual_liquidity * BRITTLE_MULTIPLIER
            and snapshot.actual_liquidity > 0
        ):
            self._logger.info(
                "WARNING: Movement is broad but brittle. Lacks cadre discipline. "
                f"(potential={snapshot.potential_liquidity}, "
                f"actual={snapshot.actual_liquidity})"
            )
        elif snapshot.potential_liquidity > 0 and snapshot.actual_liquidity == 0:
            self._logger.info(
                "WARNING: Movement is broad but brittle. Lacks cadre discipline. "
                f"(potential={snapshot.potential_liquidity}, actual=0)"
            )

        # Sword of Damocles alert
        if snapshot.is_resilient is False:
            self._logger.warning(
                "ALERT: Sword of Damocles active. A purge would destroy the movement. "
                f"(percolation={snapshot.percolation_ratio:.2f})"
            )

    def _log_summary(self) -> None:
        """Log summary of topology metrics at simulation end."""
        if not self._history:
            self._logger.info("TopologyMonitor: No snapshots recorded.")
            return

        final = self._history[-1]
        initial = self._history[0]

        self._logger.info(
            f"TopologyMonitor Summary (ticks={len(self._history)}): "
            f"percolation {initial.percolation_ratio:.2f} -> {final.percolation_ratio:.2f}, "
            f"components {initial.num_components} -> {final.num_components}, "
            f"L_max {initial.max_component_size} -> {final.max_component_size}"
        )
