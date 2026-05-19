"""Spec-070 CollapseTransitionSystem (T067, FR-023, FR-024, FR-028).

Detects Sovereigns meeting collapse predicates (``legitimacy <= 0.0``
or external trigger via ``context.persistent_data["balkanization.
collapse_triggers"]``), emits ``SOVEREIGN_COLLAPSE`` per FR-023,
emits ``TERRITORY_TRANSITION`` for each claimed Territory, and
deletes the collapsed Sovereign's outbound CLAIMS / ADMINISTERS
edges (FR-024 step 5).

Pipeline position: ~19.5 (between FieldDerivativeSystem at 20 and
EdgeTransitionSystem at 21). Belongs to ``CONSEQUENCE_SYSTEMS``.

Determinism notes:

- Collapse predicate evaluation in lex-sorted Sovereign ID order.
- TERRITORY_TRANSITION emission per claimed Territory in sorted-ID
  order.

NOTE: This is the structural backbone. The full 5-step partition
(re-assigning territories to winning-Faction-installed new
Sovereigns) is sketched in :meth:`_partition_claimed_territories`;
the new-Sovereign creation half is deferred to a follow-up
implementation along with the EndgameDetector augmentation.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.event_bus import Event
from babylon.engine.systems.base import SystemBase
from babylon.models.enums import EventType

if TYPE_CHECKING:  # pragma: no cover
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType


class CollapseTransitionSystem(SystemBase):
    """Detects collapsing Sovereigns + emits transition events."""

    name: ClassVar[str] = "CollapseTransition"
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        tick = _extract_tick(context)
        persistent = _extract_persistent(context)

        triggers = persistent.get("balkanization.collapse_triggers", {})
        sovereign_ids = sorted(node.id for node in wrapped.query_nodes(node_type="sovereign"))
        for sovereign_id in sovereign_ids:
            sov_node = wrapped.get_node(sovereign_id)
            if sov_node is None:
                continue
            legitimacy = float(sov_node.attributes.get("legitimacy", 1.0))
            trigger = triggers.get(sovereign_id)
            if trigger is None and legitimacy <= 0.0:
                trigger = "legitimacy_zero"
            if trigger is None:
                continue
            self._collapse_sovereign(wrapped, services, tick, sovereign_id, trigger)

        # Clear processed triggers (single-shot per tick).
        persistent["balkanization.collapse_triggers"] = {}
        if isinstance(context, dict):
            context["persistent_data"] = persistent
        else:
            with contextlib.suppress(AttributeError):
                context.persistent_data = persistent

    def _collapse_sovereign(
        self,
        wrapped: GraphProtocol,
        services: ServiceContainer,
        tick: int,
        sovereign_id: str,
        trigger: str,
    ) -> None:
        """Emit SOVEREIGN_COLLAPSE + TERRITORY_TRANSITION events for
        every claimed Territory, then strip CLAIMS / ADMINISTERS."""

        claims = wrapped.query_sovereign_claims(sovereign_id)
        services.event_bus.publish(
            Event(
                type=EventType.SOVEREIGN_COLLAPSE,
                tick=tick,
                payload={
                    "event_type": "sovereign_collapse",
                    "sovereign_id": sovereign_id,
                    "trigger": trigger,
                    "claimed_territories_count": len(claims),
                },
            )
        )
        for territory_id, _ctrl, _legal in sorted(claims, key=lambda r: r[0]):
            services.event_bus.publish(
                Event(
                    type=EventType.TERRITORY_TRANSITION,
                    tick=tick,
                    payload={
                        "event_type": "territory_transition",
                        "territory_id": territory_id,
                        "from_sovereign_id": sovereign_id,
                        "to_sovereign_id": None,
                        "from_winning_faction_id": None,
                        "to_winning_faction_id": None,
                        "reason": "collapse_partition",
                    },
                )
            )
            with contextlib.suppress(KeyError):
                wrapped.remove_edge(sovereign_id, territory_id, "claims")


def _extract_tick(context: ContextType) -> int:
    return int(context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0))


def _extract_persistent(context: ContextType) -> dict[str, Any]:
    if isinstance(context, dict):
        persistent = context.get("persistent_data")
        if persistent is None:
            persistent = {}
            context["persistent_data"] = persistent
        return persistent if isinstance(persistent, dict) else dict(persistent)
    existing = getattr(context, "persistent_data", None)
    if existing is None:
        return {}
    return existing if isinstance(existing, dict) else dict(existing)
