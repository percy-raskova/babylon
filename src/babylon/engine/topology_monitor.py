"""Topology Monitor for phase transition detection (Sprint 3.1, 3.3).

The TopologyMonitor is a SimulationObserver that tracks the "condensation"
of revolutionary consciousness through the social graph using percolation
theory. It detects phase transitions between 4 phases of movement organization.

Theoretical Model (4-Phase):
    - Gaseous State: percolation < 0.1 (atomized, no coordination)
    - Transitional State: 0.1 <= percolation < 0.5 (emerging structure)
    - Liquid State: percolation >= 0.5, cadre_density < 0.5 (mass movement)
    - Solid State: percolation >= 0.5, cadre_density >= 0.5 (vanguard party)

Key Metrics:
    - num_components: Number of disconnected solidarity cells
    - max_component_size (L_max): Largest connected component
    - percolation_ratio: L_max / N (giant component dominance)
    - potential_liquidity: SOLIDARITY edges > 0.1 (sympathizers)
    - actual_liquidity: SOLIDARITY edges > 0.5 (cadre)
    - cadre_density: actual_liquidity / max(1, potential_liquidity)

Narrative States:
    - "Gaseous": percolation < 0.1 (atomized, vulnerable)
    - "Transitional": 0.1 <= percolation < 0.5 (emerging structure)
    - "Liquid": percolation >= 0.5 (mass movement with weak ties)
    - "Solid": percolation >= 0.5 AND cadre_density >= 0.5 (vanguard party)
    - "Brittle": potential >> actual (broad but lacks discipline)
    - "Sword of Damocles": resilience test fails (purge would destroy)
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from babylon.dialectics.instances.connectivity import pieces
from babylon.engine.graph import BabylonUGraph
from babylon.models.enums import EdgeType
from babylon.models.events import PhaseTransitionEvent, SimulationEvent
from babylon.models.topology_metrics import ResilienceResult, TopologySnapshot

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def extract_solidarity_subgraph(
    G: GraphProtocol,
    min_strength: float = 0.0,
) -> BabylonUGraph:
    """Extract undirected solidarity network from WorldState graph.

    Creates an undirected graph containing only social_class nodes and
    SOLIDARITY edges above the minimum strength threshold. Used for
    connected component analysis via the connectivity cylinder's
    :math:`\\Pi_0` (rustworkx-native since Amendment L).

    Args:
        G: Graph from WorldState.to_graph() (raw or protocol-wrapped)
        min_strength: Minimum solidarity_strength to include edge (default 0)

    Returns:
        Undirected :class:`BabylonUGraph` containing only solidarity
        connections. Isolated social_class nodes are included.

    Note:
        Territory nodes are excluded as they represent spatial substrate,
        not class positions in the solidarity network.
    """

    # Undirected analytics graph for component analysis (Amendment L)
    solidarity_graph = BabylonUGraph()

    # Add all social_class nodes (even if isolated)
    for node in G.query_nodes(node_type="social_class"):
        solidarity_graph.add_node(node.id)

    # Collect social_class node IDs for edge filtering
    social_nodes = set(solidarity_graph.nodes())

    # Add SOLIDARITY edges above threshold
    for edge in G.query_edges(edge_type=EdgeType.SOLIDARITY):
        strength = edge.attributes.get("solidarity_strength", 0.0)
        if (
            strength > min_strength
            and edge.source_id in social_nodes
            and edge.target_id in social_nodes
        ):
            solidarity_graph.add_edge(edge.source_id, edge.target_id)

    return solidarity_graph


def calculate_component_metrics(
    solidarity_graph: BabylonUGraph,
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

    Note:
        Component counting is grounded in the connectivity cylinder's
        :math:`\\Pi_0` (:func:`babylon.dialectics.instances.connectivity.pieces`)
        — the same connected-components computation, re-exposed as the
        Phase-B instance (``project/06-lawverian-dialectics.md`` §4).
    """
    if total_social_classes == 0:
        return (0, 0, 0.0)

    # Get connected components (Pi_0 of the connectivity cylinder instance)
    components = pieces(solidarity_graph)
    num_components = len(components)
    max_component_size = 0 if num_components == 0 else max(len(c) for c in components)

    # Calculate percolation ratio
    percolation_ratio = max_component_size / total_social_classes
    # Clamp to [0, 1] for Probability type
    percolation_ratio = max(0.0, min(1.0, percolation_ratio))

    return (num_components, max_component_size, percolation_ratio)


def calculate_liquidity(
    G: GraphProtocol,
    sympathizer_threshold: float | None = None,
    cadre_threshold: float | None = None,
) -> tuple[int, int]:
    """Calculate liquidity metrics (potential vs actual solidarity).

    Measures the strength of the solidarity network by counting edges
    at different thresholds:
    - Potential (sympathizers): edges > sympathizer_threshold strength
    - Actual (cadre): edges > cadre_threshold strength

    Args:
        G: Graph from WorldState.to_graph() (raw or protocol-wrapped)
        sympathizer_threshold: Minimum strength for sympathizer. Defaults to
            GameDefines.topology.solidarity_sympathizer_threshold.
        cadre_threshold: Minimum strength for cadre. Defaults to
            GameDefines.topology.solidarity_cadre_threshold.

    Returns:
        Tuple of (potential_liquidity, actual_liquidity)
    """
    from babylon.config.defines import GameDefines

    if sympathizer_threshold is None or cadre_threshold is None:
        defaults = GameDefines()
        if sympathizer_threshold is None:
            sympathizer_threshold = defaults.topology.solidarity_sympathizer_threshold
        if cadre_threshold is None:
            cadre_threshold = defaults.topology.solidarity_cadre_threshold

    potential = 0
    actual = 0

    for edge in G.query_edges(edge_type=EdgeType.SOLIDARITY):
        strength = edge.attributes.get("solidarity_strength", 0.0)
        if strength > sympathizer_threshold:
            potential += 1
        if strength > cadre_threshold:
            actual += 1

    return (potential, actual)


def check_resilience(
    G: GraphProtocol,
    removal_rate: float | None = None,
    survival_threshold: float | None = None,
    seed: int | None = None,
) -> ResilienceResult:
    """Test if solidarity network survives targeted node removal.

    Simulates a "purge" by removing a percentage of nodes and checking
    if the giant component survives. This is the "Sword of Damocles"
    test - a fragile network can be destroyed by targeting key members.

    Args:
        G: Directed graph from WorldState.to_graph()
        removal_rate: Fraction of nodes to remove. Defaults to
            GameDefines.topology.resilience_removal_rate.
        survival_threshold: Required fraction of original L_max to survive.
            Defaults to GameDefines.topology.resilience_survival_threshold.
        seed: RNG seed for reproducibility (None = random)

    Returns:
        ResilienceResult with is_resilient flag and metrics.

    Note:
        The original graph is NOT modified. Test operates on a copy.
    """
    from babylon.config.defines import GameDefines

    if removal_rate is None or survival_threshold is None:
        defaults = GameDefines()
        if removal_rate is None:
            removal_rate = defaults.topology.resilience_removal_rate
        if survival_threshold is None:
            survival_threshold = defaults.topology.resilience_survival_threshold

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

    # Calculate original L_max (Pi_0 of the connectivity cylinder)
    original_components = pieces(solidarity_graph)
    original_max = max(len(c) for c in original_components) if original_components else 0

    # Create copy and remove nodes
    purged_graph = solidarity_graph.copy()
    num_to_remove = max(1, int(total_nodes * removal_rate))
    nodes_to_remove = rng.sample(nodes, min(num_to_remove, total_nodes))
    purged_graph.remove_nodes_from(nodes_to_remove)

    # Calculate post-purge L_max
    post_components = pieces(purged_graph)
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
        resilience_removal_rate: float | None = None,
        logger: logging.Logger | None = None,
        gaseous_threshold: float | None = None,
        condensation_threshold: float | None = None,
        vanguard_threshold: float | None = None,
    ) -> None:
        """Initialize TopologyMonitor.

        Args:
            resilience_test_interval: Run resilience test every N ticks
                (0 = disabled). Default 5.
            resilience_removal_rate: Fraction of nodes to remove in test.
                Defaults to GameDefines.topology.resilience_removal_rate.
            logger: Logger instance (default: module logger)
            gaseous_threshold: Percolation ratio below this = atomized.
                Defaults to GameDefines.topology.gaseous_threshold.
            condensation_threshold: Percolation ratio for phase transition.
                Defaults to GameDefines.topology.condensation_threshold.
            vanguard_threshold: Cadre density threshold for solid phase.
                Defaults to GameDefines.topology.vanguard_density_threshold.
        """
        # Import here to avoid circular dependency
        from babylon.config.defines import GameDefines

        defaults = GameDefines()
        topo = defaults.topology

        self._history: list[TopologySnapshot] = []
        self._previous_percolation: float = 0.0
        self._resilience_interval: int = resilience_test_interval
        self._removal_rate: float = (
            resilience_removal_rate
            if resilience_removal_rate is not None
            else topo.resilience_removal_rate
        )
        self._logger: logging.Logger = logger or logging.getLogger(__name__)
        # Sprint 3.3: Phase transition event emission
        self._previous_phase: str | None = None
        self._pending_events: list[SimulationEvent] = []
        # Brittle multiplier from GameDefines
        self._brittle_multiplier: float = topo.brittle_multiplier

        # Configurable thresholds (defaults from GameDefines)
        self._gaseous_threshold: float = (
            gaseous_threshold if gaseous_threshold is not None else topo.gaseous_threshold
        )
        self._condensation_threshold: float = (
            condensation_threshold
            if condensation_threshold is not None
            else topo.condensation_threshold
        )
        self._vanguard_threshold: float = (
            vanguard_threshold
            if vanguard_threshold is not None
            else defaults.topology.vanguard_density_threshold
        )

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return "TopologyMonitor"

    @property
    def history(self) -> list[TopologySnapshot]:
        """Return copy of snapshot history."""
        return list(self._history)

    def _classify_phase(self, percolation_ratio: float, cadre_density: float = 0.0) -> str:
        """Classify network state based on percolation ratio and cadre density.

        Uses a 4-phase model based on percolation theory:

        - Gaseous: percolation < gaseous_threshold (atomized, no coordination)
        - Transitional: gaseous <= percolation < condensation (emerging structure)
        - Liquid: percolation >= condensation, cadre < vanguard (mass movement)
        - Solid: percolation >= condensation, cadre >= vanguard (vanguard party)

        Thresholds are configurable via constructor or GameDefines.topology.

        Args:
            percolation_ratio: L_max / N ratio from topology analysis.
            cadre_density: Ratio of cadre to sympathizers (actual/potential).
                Defaults to 0.0 for backward compatibility.

        Returns:
            Phase classification: "gaseous", "transitional", "liquid", or "solid".
        """
        if percolation_ratio < self._gaseous_threshold:
            return "gaseous"
        if percolation_ratio < self._condensation_threshold:
            return "transitional"
        # percolation >= condensation: distinguish liquid vs solid by cadre density
        if cadre_density >= self._vanguard_threshold:
            return "solid"
        return "liquid"

    def get_pending_events(self) -> list[SimulationEvent]:
        """Return and clear pending events for collection by Simulation facade.

        Observer events cannot be emitted directly to WorldState because
        observers run AFTER WorldState is frozen. Instead, pending events
        are collected by the Simulation facade and injected into the
        NEXT tick's WorldState.

        Returns:
            List of pending SimulationEvent objects (cleared after return).
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

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
        self._previous_phase = None  # Reset phase tracking
        self._pending_events.clear()  # Clear any stale events
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
        # Amendment L: to_graph() returns BabylonGraph, which IS the
        # protocol — no wrap needed.
        graph: GraphProtocol = state.to_graph()

        # Count social_class nodes
        total_nodes = sum(1 for _ in graph.query_nodes(node_type="social_class"))

        # Extract solidarity subgraph and calculate metrics
        solidarity_graph = extract_solidarity_subgraph(graph)
        num_components, max_component_size, percolation_ratio = calculate_component_metrics(
            solidarity_graph, total_nodes
        )

        # Calculate liquidity
        potential, actual = calculate_liquidity(graph)

        # Calculate cadre_density: actual / potential (with division-by-zero protection)
        cadre_density = actual / max(1, potential)
        # Clamp to [0, 1] for safety
        cadre_density = max(0.0, min(1.0, cadre_density))

        # Run resilience test if interval reached
        is_resilient: bool | None = None
        if self._resilience_interval > 0:
            tick = state.tick
            if is_start or (tick > 0 and tick % self._resilience_interval == 0):
                result = check_resilience(graph, removal_rate=self._removal_rate)
                is_resilient = result.is_resilient

        # Create snapshot (now includes cadre_density)
        snapshot = TopologySnapshot(
            tick=state.tick,
            num_components=num_components,
            max_component_size=max_component_size,
            total_nodes=total_nodes,
            percolation_ratio=percolation_ratio,
            potential_liquidity=potential,
            actual_liquidity=actual,
            cadre_density=cadre_density,
            is_resilient=is_resilient,
        )

        # Log narratives
        self._log_narratives(snapshot)

        # Sprint 3.3: Phase transition detection and event emission (4-phase model)
        current_phase = self._classify_phase(percolation_ratio, cadre_density)

        if self._previous_phase is not None and current_phase != self._previous_phase:
            # Phase transition detected - emit event
            event = PhaseTransitionEvent(
                tick=state.tick,
                previous_state=self._previous_phase,
                new_state=current_phase,
                percolation_ratio=percolation_ratio,
                num_components=num_components,
                largest_component_size=max_component_size,
                cadre_density=cadre_density,
                is_resilient=is_resilient,
            )
            self._pending_events.append(event)

        self._previous_phase = current_phase

        # Update state
        self._previous_percolation = percolation_ratio
        self._history.append(snapshot)

    def _log_narratives(self, snapshot: TopologySnapshot) -> None:
        """Generate and log narrative descriptions.

        Args:
            snapshot: Current TopologySnapshot to analyze
        """
        # Gaseous state detection
        if snapshot.percolation_ratio < self._gaseous_threshold:
            self._logger.info(
                "STATE: Gaseous. Movement is atomized. "
                f"(percolation={snapshot.percolation_ratio:.2f}, "
                f"components={snapshot.num_components})"
            )

        # Phase shift detection (crossing condensation threshold)
        if (
            self._previous_percolation < self._condensation_threshold
            and snapshot.percolation_ratio >= self._condensation_threshold
        ):
            self._logger.info(
                "PHASE SHIFT: Condensation detected. A Vanguard Party has formed. "
                f"(percolation={snapshot.percolation_ratio:.2f}, "
                f"L_max={snapshot.max_component_size})"
            )

        # Brittle movement warning
        if (
            snapshot.potential_liquidity > snapshot.actual_liquidity * self._brittle_multiplier
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
