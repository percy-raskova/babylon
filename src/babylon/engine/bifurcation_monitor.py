"""Bifurcation topology monitor (T032, Phase 10, Feature 033).

Standalone monitor that tracks consciousness-weighted bifurcation
analysis results across simulation ticks and emits tendency change
events. Accepts a CommunityStateStore for consciousness data access.

Unlike TopologyMonitor (which tracks percolation phase transitions),
BifurcationMonitor tracks the George Jackson model: whether crisis
routes toward fascism or revolution based on cross-line solidarity
weighted by community consciousness.

See Also:
    :mod:`babylon.domain.bifurcation.analysis`: Core analysis function.
    :mod:`babylon.engine.topology_monitor`: Percolation-based monitor.
    :mod:`babylon.engine.community_state_store`: State store protocol.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.config.defines import BifurcationDefines
from babylon.domain.bifurcation.analysis import bifurcation_tendency
from babylon.domain.bifurcation.types import BifurcationSnapshot
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType
from babylon.models.events import BifurcationTendencyEvent, SimulationEvent

if TYPE_CHECKING:
    from babylon.engine.community_state_store import CommunityStateStore
    from babylon.topology.graph import BabylonGraph


class BifurcationMonitor:
    """Monitor tracking bifurcation tendency across simulation ticks.

    Records BifurcationSnapshot per tick and emits BifurcationTendencyEvent
    when the overall tendency changes (revolutionary/fascist/indeterminate).

    Args:
        community_state_store: Protocol-based access to community states.
        defines: Configurable bifurcation parameters.
        logger: Logger instance (default: module logger).

    Attributes:
        bifurcation_history: List of BifurcationSnapshot objects.
    """

    def __init__(
        self,
        community_state_store: CommunityStateStore,
        defines: BifurcationDefines | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._store = community_state_store
        self._defines = defines or BifurcationDefines()
        self._logger = logger or logging.getLogger(__name__)
        self._bifurcation_history: list[BifurcationSnapshot] = []
        self._previous_tendency: str | None = None
        self._pending_events: list[SimulationEvent] = []

    @property
    def bifurcation_history(self) -> list[BifurcationSnapshot]:
        """Return list of recorded bifurcation snapshots."""
        return list(self._bifurcation_history)

    def record_bifurcation(
        self,
        graph: BabylonGraph,
        H: xgi.Hypergraph,
        agent_memberships: dict[str, set[CommunityType]],
        contradictions: list[Contradiction],
        tick: int,
    ) -> None:
        """Run bifurcation analysis and record snapshot.

        Args:
            graph: Simulation DiGraph with social_class and territory nodes.
            H: XGI hypergraph for community membership lookup.
            agent_memberships: Agent ID to community memberships mapping.
            contradictions: List of current contradictions in this scope.
            tick: Current simulation tick.
        """
        community_states = self._store.get_all()

        result = bifurcation_tendency(
            graph=graph,
            H=H,
            community_states=community_states,
            contradictions=contradictions,
            agent_memberships=agent_memberships,
            defines=self._defines,
        )

        snapshot = BifurcationSnapshot(tick=tick, result=result)
        self._bifurcation_history.append(snapshot)

        # Emit event on tendency change
        current = result.overall_tendency
        if self._previous_tendency is not None and current != self._previous_tendency:
            event = BifurcationTendencyEvent(
                tick=tick,
                percolation_ratio=0.0,  # Not tracked by bifurcation (see TopologyMonitor)
                num_components=result.filtered_beta_0,
                previous_tendency=self._previous_tendency,
                new_tendency=current,
                consciousness_weighted_cross_solidarity=result.consciousness_weighted_cross_solidarity,
                mean_collective_identity_marginalized=result.mean_collective_identity_marginalized,
                bridge_potential_weighted=result.bridge_potential_weighted,
                legitimation_index=result.legitimation_index,
            )
            self._pending_events.append(event)
            self._logger.info(
                "BIFURCATION: Tendency changed %s → %s (tick %d)",
                self._previous_tendency,
                current,
                tick,
            )

        self._previous_tendency = current

    def get_pending_events(self) -> list[SimulationEvent]:
        """Return and clear pending events.

        Same pattern as TopologyMonitor: observer events cannot be
        emitted directly to frozen WorldState. Pending events are
        collected by the Simulation facade.

        Returns:
            List of pending events (cleared after return).
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events
