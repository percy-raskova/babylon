"""Spec-070 CollapseTransitionSystem (T067 + T084-T087, FR-023, FR-024,
FR-027, FR-028).

Handles two distinct collapse / fracture paths:

1. **Collapse-driven** (FR-023, FR-024): Sovereign legitimacy ≤ 0.0 or
   external trigger via ``context.persistent_data["balkanization.
   collapse_triggers"]``. Emits ``SOVEREIGN_COLLAPSE``, partitions claimed
   Territories among winning Factions (creates new Sovereigns at
   ``control_level = initial_post_collapse_control_level``), emits
   ``TERRITORY_TRANSITION`` per claimed Territory, deletes the collapsed
   Sovereign node + outbound edges.

2. **Active-secession** (FR-027, FR-028, FR-029a): Reads
   ``persistent_data["balkanization.secession_eligible"]`` (populated by
   FactionInfluenceSystem when the hysteresis window elapses), emits
   ``CIVIL_WAR_DECLARED``, rewires the contiguous sub-region's CLAIMS
   from the parent Sovereign to a new secessionist Sovereign via the
   ``bulk_partition_claims`` O(K) protocol method (FR-018 / SC-004).

Pipeline position: 20.5 (between FieldDerivativeSystem at 20 and
EdgeTransitionSystem at 21). Belongs to ``CONSEQUENCE_SYSTEMS``.

Determinism notes:

- Collapse predicate evaluation in lex-sorted Sovereign ID order.
- TERRITORY_TRANSITION emission per claimed Territory in sorted-ID
  order.
- New Sovereign IDs follow ``SOV_AUTO_T{tick}_F{faction_id}_{counter}``.
- Orphaned Sovereign nodes (zero CLAIMS) are deleted at the END of
  every tick.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.event_bus import Event
from babylon.engine.systems.base import SystemBase
from babylon.models.enums import EventType

if TYPE_CHECKING:  # pragma: no cover
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType


class CollapseTransitionSystem(SystemBase):
    """Detects collapsing Sovereigns + emits transition events."""

    name: ClassVar[str] = "CollapseTransition"
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        tick = _extract_tick(context)
        persistent = _extract_persistent(context)

        # Phase 1: Collapse-driven path (FR-023, FR-024).
        triggers = persistent.get("balkanization.collapse_triggers", {})
        winning = persistent.get("balkanization.winning_faction_by_territory", {})
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
            self._collapse_sovereign(wrapped, services, tick, sovereign_id, trigger, winning)

        # Phase 2: Active-secession path (FR-027, FR-028).
        eligible = persistent.get("balkanization.secession_eligible", [])
        for entry in eligible:
            self._execute_secession(wrapped, services, tick, entry)

        # Phase 3: Orphaned-Sovereign cleanup.
        self._cleanup_orphaned_sovereigns(wrapped)

        # Clear processed inputs (single-shot per tick).
        persistent["balkanization.collapse_triggers"] = {}
        persistent["balkanization.secession_eligible"] = []
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
        winning: dict[str, str],
    ) -> None:
        """Emit SOVEREIGN_COLLAPSE + per-Territory TERRITORY_TRANSITION,
        partition claimed Territories among winning Factions (creating
        new Sovereigns per FR-024 step 4), then strip the collapsed
        Sovereign's CLAIMS / ADMINISTERS edges (step 5)."""

        from babylon.config.defines.balkanization import BalkanizationDefines

        defines = BalkanizationDefines()
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

        # FR-024 step 4: partition Territories among winning Factions.
        # Each Faction inherits its share with control_level =
        # initial_post_collapse_control_level (default 0.8) and
        # legal_status=DE_FACTO.
        by_faction: dict[str, list[str]] = {}
        for territory_id, _ctrl, _legal in claims:
            faction = winning.get(territory_id)
            if faction is None:
                # No winning Faction ⇒ territory becomes unclaimed (Edge
                # case "Unclaimed Territory" — would be picked up by
                # SOV_EXTERIOR_NULL fallback per FR-040b).
                continue
            by_faction.setdefault(faction, []).append(territory_id)

        new_sovereign_ids: dict[str, str] = {}
        for counter, (faction_id, territory_ids) in enumerate(sorted(by_faction.items()), start=1):
            new_sov_id = f"SOV_AUTO_T{tick}_F{faction_id.removeprefix('FAC_')}_{counter}"
            # Slight ID length cap so it satisfies the SOV_ pattern.
            new_sov_id = new_sov_id[:64]
            new_sovereign_ids[faction_id] = new_sov_id
            wrapped.add_node(
                new_sov_id,
                "sovereign",
                name=f"Successor of {sovereign_id}",
                sovereignty_type="provisional",
                legitimacy=0.5,
                color_hex="#7f7f7f",
                ruling_faction_id=faction_id,
                extraction_policy=_extraction_policy_for_faction(wrapped, faction_id),
                founded_tick=tick,
            )
            for territory_id in sorted(territory_ids):
                wrapped.add_edge(
                    new_sov_id,
                    territory_id,
                    "claims",
                    control_level=defines.initial_post_collapse_control_level,
                    legal_status="de_facto",
                    fiscal_status="taxed",
                    recognition_level=0.5,
                    claimed_since_tick=tick,
                )

        # Emit TERRITORY_TRANSITION per claimed Territory (sorted).
        for territory_id, _ctrl, _legal in sorted(claims, key=lambda r: r[0]):
            faction = winning.get(territory_id)
            to_sov = new_sovereign_ids.get(faction) if faction is not None else None
            services.event_bus.publish(
                Event(
                    type=EventType.TERRITORY_TRANSITION,
                    tick=tick,
                    payload={
                        "event_type": "territory_transition",
                        "territory_id": territory_id,
                        "from_sovereign_id": sovereign_id,
                        "to_sovereign_id": to_sov,
                        "from_winning_faction_id": None,
                        "to_winning_faction_id": faction,
                        "reason": "collapse_partition",
                    },
                )
            )
            with contextlib.suppress(KeyError):
                wrapped.remove_edge(sovereign_id, territory_id, "claims")

    def _execute_secession(
        self,
        wrapped: GraphProtocol,
        services: ServiceContainer,
        tick: int,
        entry: dict[str, Any],
    ) -> None:
        """Spec-070 FR-027 / FR-028 fracture execution.

        Creates a new secessionist Sovereign for the seceding Faction,
        rewires the contiguous Territory sub-region's CLAIMS from parent
        → new via ``bulk_partition_claims`` (O(K) per FR-018), emits
        ``CIVIL_WAR_DECLARED`` per FR-028.
        """

        from babylon.config.defines.balkanization import BalkanizationDefines

        defines = BalkanizationDefines()
        faction_id = str(entry["secessionist_faction_id"])
        parent_id = str(entry["parent_sovereign_id"])
        territories = {str(tid) for tid in entry["contiguous_territory_ids"]}
        if not territories:
            return

        new_sov_id = f"SOV_BREAK_T{tick}_F{faction_id.removeprefix('FAC_')}"
        new_sov_id = new_sov_id[:64]
        wrapped.add_node(
            new_sov_id,
            "sovereign",
            name=f"Breakaway from {parent_id}",
            sovereignty_type="secessionist",
            legitimacy=0.5,
            color_hex="#ff7f00",
            ruling_faction_id=faction_id,
            extraction_policy=_extraction_policy_for_faction(wrapped, faction_id),
            founded_tick=tick,
        )

        # O(K) rewire via the protocol-level batch operation (FR-018 /
        # SC-004). The benchmark test asserts this stays flat in N.
        moved = wrapped.bulk_partition_claims(
            from_sovereign_id=parent_id,
            to_sovereign_id=new_sov_id,
            territories=territories,
        )

        services.event_bus.publish(
            Event(
                type=EventType.CIVIL_WAR_DECLARED,
                tick=tick,
                payload={
                    "event_type": "civil_war_declared",
                    "parent_sovereign_id": parent_id,
                    "secessionist_faction_id": faction_id,
                    "contested_territory_count": moved,
                },
            )
        )
        # Promote the new edges' legal_status to disputed for FR-028's
        # contested-boundary semantics. Reflect control_level =
        # initial_post_collapse_control_level.
        for territory_id in sorted(territories):
            with contextlib.suppress(KeyError):
                wrapped.update_edge(
                    new_sov_id,
                    territory_id,
                    "claims",
                    legal_status="de_facto",
                    control_level=defines.initial_post_collapse_control_level,
                )

    @staticmethod
    def _cleanup_orphaned_sovereigns(wrapped: GraphProtocol) -> None:
        """Delete any Sovereign with zero remaining CLAIMS edges, plus
        the corresponding ADMINISTERS edges."""

        sovereign_ids = [node.id for node in wrapped.query_nodes(node_type="sovereign")]
        for sovereign_id in sovereign_ids:
            claims = wrapped.query_sovereign_claims(sovereign_id)
            if claims:
                continue
            # The SOV_EXTERIOR_NULL is the documented exterior fallback
            # — never orphan-prune it.
            if sovereign_id == "SOV_EXTERIOR_NULL":
                continue
            with contextlib.suppress(KeyError):
                wrapped.remove_node(sovereign_id)


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


def _extraction_policy_for_faction(wrapped: GraphProtocol, faction_id: str) -> str:
    """Resolve a Faction's :class:`ExtractionPolicy` via stance lookup.

    Falls back to ``"continue"`` (the safe default) when the Faction
    or its stance is missing from the graph.
    """

    from babylon.formulas.balkanization import derive_extraction_policy_from_stance
    from babylon.models.enums import ColonialStance

    node = wrapped.get_node(faction_id)
    if node is None:
        return "continue"
    stance_raw = node.attributes.get("colonial_stance")
    if not isinstance(stance_raw, str):
        return "continue"
    try:
        stance = ColonialStance(stance_raw)
    except ValueError:
        return "continue"
    return derive_extraction_policy_from_stance(stance).value
