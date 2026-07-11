"""Spec-070 FactionInfluenceSystem (T054, FR-021, FR-022, FR-026,
FR-029a/b/c, FR-034).

Reads INFLUENCES + ADJACENCY edges, computes per-Territory winning
Faction (FR-021), emits TERRITORY_TRANSITION on flips (FR-022),
FACTION_VICTORY on supermajority (FR-026), RED_SETTLER_TRAP_DETECTED
diagnostic (FR-034), and queues secession-eligible (faction, sovereign)
pairs after a hysteresis window (FR-029a/b/c).

Pipeline position: ~14.5 (between OODASystem at 14 and SurvivalSystem
at 15). Belongs to ``CONSEQUENCE_SYSTEMS`` per spec-056 + spec-070
research.md R-003.

Determinism notes (III.7):

- Winning-Faction ``argmax`` uses incumbent-priority tiebreaker first,
  then seed-deterministic RNG over sorted-ID tied set.
- Hysteresis counters keyed by ``(faction_id, sovereign_id)``.
- Iteration is in lex-sorted Territory ID order.
"""

from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.formulas.balkanization import (
    contiguous_influence_majority_subregion,
    detect_red_settler_trap,
    winning_faction_for_territory,
)
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.models.enums import ColonialStance, EventType

if TYPE_CHECKING:  # pragma: no cover
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType


_PREV_WINNING = "balkanization.previous_winning_faction_by_territory"
_HYSTERESIS = "balkanization.hysteresis_buffer"


class FactionInfluenceSystem(SystemBase):
    """Resolve per-Territory winning Faction + secession eligibility."""

    name: ClassVar[str] = "FactionInfluence"
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        tick = _extract_tick(context)
        persistent = _extract_persistent(context)
        defines = _resolve_defines(services)
        rng = resolve_rng(services, tick)

        winning = self._resolve_winning_factions(wrapped, persistent, rng)
        persistent["balkanization.winning_faction_by_territory"] = winning

        self._emit_territory_transitions(persistent, winning, tick, services)
        persistent[_PREV_WINNING] = dict(winning)

        self._emit_faction_victory(winning, defines, tick, services)
        self._emit_red_settler_trap_events(wrapped, defines, tick, services)
        self._update_secession_eligibility(wrapped, persistent, defines, tick, services)

        if isinstance(context, dict):
            context["persistent_data"] = persistent
        else:
            with contextlib.suppress(AttributeError):
                context.persistent_data = persistent

    def _resolve_winning_factions(
        self,
        wrapped: GraphProtocol,
        persistent: dict[str, Any],
        rng: random.Random,
    ) -> dict[str, str]:
        previous: dict[str, str] = persistent.get(_PREV_WINNING, {})
        winning: dict[str, str] = {}
        territory_ids = sorted(node.id for node in wrapped.query_nodes(node_type="territory"))
        for territory_id in territory_ids:
            incumbent = previous.get(territory_id)
            winner = winning_faction_for_territory(wrapped, territory_id, incumbent, rng)
            if winner is not None:
                winning[territory_id] = winner
        return winning

    @staticmethod
    def _emit_territory_transitions(
        persistent: dict[str, Any],
        winning: dict[str, str],
        tick: int,
        services: ServicesProtocol,
    ) -> None:
        previous: dict[str, str] = persistent.get(_PREV_WINNING, {})
        for territory_id in sorted(winning):
            old = previous.get(territory_id)
            new = winning[territory_id]
            if old == new:
                continue
            services.event_bus.publish(
                Event(
                    type=EventType.TERRITORY_TRANSITION,
                    tick=tick,
                    payload={
                        "territory_id": territory_id,
                        "from_sovereign_id": None,
                        "to_sovereign_id": None,
                        "from_winning_faction_id": old,
                        "to_winning_faction_id": new,
                        "reason": "influence_flip",
                    },
                )
            )

    @staticmethod
    def _emit_faction_victory(
        winning: dict[str, str],
        defines: BalkanizationDefines,
        tick: int,
        services: ServicesProtocol,
    ) -> None:
        if not winning:
            return
        threshold = defines.faction_victory_supermajority_threshold
        counts: dict[str, int] = {}
        for faction_id in winning.values():
            counts[faction_id] = counts.get(faction_id, 0) + 1
        total = sum(counts.values())
        if total == 0:
            return
        for faction_id in sorted(counts):
            share = counts[faction_id] / total
            if share >= threshold:
                services.event_bus.publish(
                    Event(
                        type=EventType.FACTION_VICTORY,
                        tick=tick,
                        payload={
                            "faction_id": faction_id,
                            "aggregate_influence_share": share,
                        },
                    )
                )

    @staticmethod
    def _emit_red_settler_trap_events(
        wrapped: GraphProtocol,
        defines: BalkanizationDefines,
        tick: int,
        services: ServicesProtocol,
    ) -> None:
        for node in sorted(
            wrapped.query_nodes(node_type="balkanization_faction"),
            key=lambda n: n.id,
        ):
            attrs = node.attributes
            stance_raw = attrs.get("colonial_stance")
            if not isinstance(stance_raw, str):
                continue
            try:
                stance = ColonialStance(stance_raw)
            except ValueError:
                continue
            class_reduction = float(attrs.get("class_reduction", 0.0))
            if detect_red_settler_trap(class_reduction, stance, defines):
                services.event_bus.publish(
                    Event(
                        type=EventType.RED_SETTLER_TRAP_DETECTED,
                        tick=tick,
                        payload={
                            "faction_id": node.id,
                            "class_reduction": class_reduction,
                            "colonial_stance": stance.value,
                        },
                    )
                )

    @staticmethod
    def _update_secession_eligibility(
        wrapped: GraphProtocol,
        persistent: dict[str, Any],
        defines: BalkanizationDefines,
        tick: int,
        services: ServicesProtocol,
    ) -> None:
        hysteresis: dict[str, int] = persistent.get(_HYSTERESIS, {})
        eligible: list[dict[str, Any]] = []
        faction_ids = sorted(
            node.id for node in wrapped.query_nodes(node_type="balkanization_faction")
        )
        sovereign_ids = sorted(node.id for node in wrapped.query_nodes(node_type="sovereign"))
        seen: set[str] = set()
        for sovereign_id in sovereign_ids:
            sov_node = wrapped.get_node(sovereign_id)
            if sov_node is None:
                continue
            incumbent = sov_node.attributes.get("ruling_faction_id")
            for faction_id in faction_ids:
                if faction_id == incumbent:
                    continue
                region = contiguous_influence_majority_subregion(
                    wrapped, faction_id, sovereign_id, defines
                )
                key = f"{faction_id}::{sovereign_id}"
                seen.add(key)
                if not region:
                    hysteresis[key] = 0
                    continue
                hysteresis[key] = hysteresis.get(key, 0) + 1
                if hysteresis[key] >= defines.secession_hysteresis_ticks:
                    eligible.append(
                        {
                            "secessionist_faction_id": faction_id,
                            "parent_sovereign_id": sovereign_id,
                            "contiguous_territory_ids": tuple(sorted(region)),
                        }
                    )
                    services.event_bus.publish(
                        Event(
                            type=EventType.SECESSION_DECLARED,
                            tick=tick,
                            payload={
                                "secessionist_faction_id": faction_id,
                                "parent_sovereign_id": sovereign_id,
                                "contiguous_territory_ids": tuple(sorted(region)),
                                "observer_triggered": False,
                            },
                        )
                    )
                    hysteresis[key] = 0
        # Reset hysteresis for (faction, sovereign) pairs that no longer
        # have any active count (cleanup).
        for stale_key in list(hysteresis):
            if stale_key not in seen:
                del hysteresis[stale_key]
        persistent[_HYSTERESIS] = hysteresis
        persistent["balkanization.secession_eligible"] = eligible


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


def _resolve_defines(services: ServicesProtocol) -> BalkanizationDefines:
    bk = getattr(services.defines, "balkanization", None)
    return bk if isinstance(bk, BalkanizationDefines) else BalkanizationDefines()
