"""``TopologyInvariantHarness`` runner for spec-055 topology-invariant tests.

Mirrors the ``BoundInvariantHarness`` shape from spec-054 with one
namespace difference: the opt-out marker class attribute is
``bypasses_topology_invariant`` (not ``bypasses_bound_invariant``).

Also exposes the single-source-of-truth community-node detector
``is_community_node(graph, node_id)`` and its sibling injection helper
``_inject_community_markers(graph, community_node_ids)`` used by the
US2 strategy / linter (per data-model.md §3.3 and research §3).

At import time, validates SC-006: every System with a
``bypasses_topology_invariant`` marker MUST carry a non-empty
justification string for every entry. Empty justifications fail
collection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from babylon.engine.context import TickContext
from babylon.engine.invariants import Invariant, InvariantResult
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.protocol import System
from babylon.models.world_state import WorldState

from .bound_harness import HarnessResult
from .system_registry import all_systems

if TYPE_CHECKING:
    import networkx as nx

# Re-export HarnessResult so tests have a single import surface.
__all__ = [
    "HarnessResult",
    "TopologyInvariantHarness",
    "_inject_community_markers",
    "is_community_node",
]

SystemRunner = Callable[..., None]


def is_community_node(graph: nx.DiGraph[str], node_id: str) -> bool:
    """Return True iff the node is marked as a community node.

    Single source of truth for spec-055 US2's hyperedges-not-pairwise
    linter (per Q1 clarification + research §3). The detection rule is
    ``graph.nodes[node_id].get("_node_type") == "community"``.

    For node IDs absent from the graph, returns False (does not raise).

    Args:
        graph: NetworkX directed graph (typically from ``WorldState.to_graph()``).
        node_id: Node ID to check.

    Returns:
        True iff the node carries ``_node_type == "community"``.
    """
    if node_id not in graph.nodes:
        return False
    return graph.nodes[node_id].get("_node_type") == "community"


def _inject_community_markers(graph: nx.DiGraph[str], community_node_ids: frozenset[str]) -> None:
    """Tag the named nodes with ``_node_type='community'`` on the live graph.

    Paired with ``is_community_node`` so injection and detection share a
    file. Used by US2 strategies/tests after calling ``state.to_graph()``
    to mark which nodes the test wants treated as communities.

    Nodes not present in the graph are silently skipped (the strategy
    may produce IDs that the post-build graph doesn't contain).

    Args:
        graph: Live mutable graph to patch in place.
        community_node_ids: Set of node IDs to mark.
    """
    for node_id in community_node_ids:
        if node_id in graph.nodes:
            graph.nodes[node_id]["_node_type"] = "community"


@dataclass(frozen=True)
class TopologyInvariantHarness:
    """Runs a System (or pipeline) and applies topology invariants to (pre, post).

    Mirrors ``BoundInvariantHarness`` exactly except for the
    ``bypass_marker_attr`` default.

    Args:
        system: Either a System class (instantiated fresh per call) or a
            ``SystemRunner`` callable wrapping the full pipeline.
        invariants: Sequence of ``Invariant`` instances to check.
        bypass_marker_attr: Class attribute carrying the opt-out marker.
            Defaults to ``"bypasses_topology_invariant"``.
    """

    system: type[System] | SystemRunner
    invariants: Sequence[Invariant]
    bypass_marker_attr: str = "bypasses_topology_invariant"

    def run(self, pre: WorldState, services: ServiceContainer, ctx: TickContext) -> HarnessResult:
        """Run the System once and check each invariant against (pre, post)."""
        if isinstance(self.system, type):
            system_instance = self.system()
            system_name = self.system.__name__
            marker = self._read_marker(self.system)
            runner: SystemRunner = system_instance.step
        else:
            system_name = "<pipeline>"
            marker = {}
            runner = self.system

        graph = pre.to_graph()
        runner(graph, services, ctx)
        post = WorldState.from_graph(graph, tick=pre.tick + 1)

        outcomes: dict[str, InvariantResult | Literal["SKIPPED"]] = {}
        skip_reasons: dict[str, str] = {}
        for invariant in self.invariants:
            if invariant.name in marker:
                outcomes[invariant.name] = "SKIPPED"
                skip_reasons[invariant.name] = marker[invariant.name]
                continue
            outcomes[invariant.name] = invariant.check(pre, post)

        return HarnessResult(system_name=system_name, outcomes=outcomes, skip_reasons=skip_reasons)

    def _read_marker(self, system_cls: type[System]) -> dict[str, str]:
        """Read the configured opt-out marker ClassVar if present."""
        marker = getattr(system_cls, self.bypass_marker_attr, None)
        if marker is None:
            return {}
        if not isinstance(marker, dict):
            msg = (
                f"{system_cls.__name__}.{self.bypass_marker_attr} must be a "
                f"dict[str, str]; got {type(marker).__name__}"
            )
            raise TypeError(msg)
        return marker


def _validate_all_markers() -> None:
    """At import time, machine-enforce SC-006 for topology markers across Systems."""
    for cls in all_systems():
        marker = getattr(cls, "bypasses_topology_invariant", None)
        if marker is None:
            continue
        if not isinstance(marker, dict):
            msg = (
                f"{cls.__name__}.bypasses_topology_invariant must be a "
                f"dict[str, str]; got {type(marker).__name__}"
            )
            raise TypeError(msg)
        for predicate, justification in marker.items():
            if not isinstance(justification, str) or not justification.strip():
                msg = (
                    f"{cls.__name__}.bypasses_topology_invariant[{predicate!r}] "
                    f"has empty justification; SC-006 requires every marker "
                    f"entry to carry a non-empty explanation."
                )
                raise ValueError(msg)


_validate_all_markers()
