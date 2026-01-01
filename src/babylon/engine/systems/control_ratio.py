"""Control ratio system for tracking guard:prisoner dynamics.

This system monitors the balance between carceral enforcers and the
prisoner population (INTERNAL_PROLETARIAT + LUMPENPROLETARIAT). When
prisoners exceed the control capacity, a CONTROL_RATIO_CRISIS occurs.

User specification: 1:20 ratio (1 guard can control 20 prisoners).

The terminal decision bifurcation:
- If average organization >= 0.5: prisoners + guards unite in REVOLUTION
- If average organization < 0.5: system turns GENOCIDAL to eliminate surplus

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

from babylon.engine.systems.protocol import ContextType

# Control capacity: 1 guard can control 20 prisoners
CONTROL_CAPACITY = 20

# Organization threshold for revolution (vs genocide)
REVOLUTION_THRESHOLD = 0.5

# Prisoner classes (internal proletariat + lumpen)
_PRISONER_ROLES: frozenset[SocialRole] = frozenset(
    {
        SocialRole.INTERNAL_PROLETARIAT,
        SocialRole.LUMPENPROLETARIAT,
    }
)


def _get_role(data: dict[str, Any]) -> SocialRole | None:
    """Extract SocialRole from node data, returning None if invalid."""
    role = data.get("role")
    if isinstance(role, str):
        try:
            return SocialRole(role)
        except ValueError:
            return None
    if isinstance(role, SocialRole):
        return role
    return None


def _count_enforcer_population(graph: nx.DiGraph[str]) -> int:
    """Count total population of active CARCERAL_ENFORCER entities."""
    total = 0
    for _node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "territory":
            continue
        if not data.get("active", True):
            continue
        if _get_role(data) == SocialRole.CARCERAL_ENFORCER:
            total += data.get("population", 0)
    return total


def _count_prisoner_population_and_org(
    graph: nx.DiGraph[str],
) -> tuple[int, float]:
    """Count prisoner population and weighted organization sum.

    Returns:
        Tuple of (total_population, org_weighted_sum) where
        org_weighted_sum = sum(population * organization) for averaging.
    """
    total_pop = 0
    org_sum = 0.0
    for _node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "territory":
            continue
        if not data.get("active", True):
            continue
        if _get_role(data) in _PRISONER_ROLES:
            pop = data.get("population", 0)
            org = data.get("organization", 0.0)
            total_pop += pop
            org_sum += pop * org
    return total_pop, org_sum


class ControlRatioSystem:
    """Track guard:prisoner ratio and trigger terminal decision.

    When enforcers × CONTROL_CAPACITY < prisoners, a control ratio
    crisis occurs. The outcome depends on prisoner organization:
    - High org (>= 0.5): Revolution - prisoners and guards unite
    - Low org (< 0.5): Genocide - system eliminates surplus population
    """

    name = "ControlRatio"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Check control ratio and emit crisis/terminal decision events."""
        tick = context.get("tick", 0)

        enforcer_pop = _count_enforcer_population(graph)
        prisoner_pop, prisoner_org_sum = _count_prisoner_population_and_org(graph)

        # No prisoners = no crisis
        if prisoner_pop == 0:
            return

        # Calculate control capacity
        max_controllable = enforcer_pop * CONTROL_CAPACITY

        # Check if control ratio is exceeded
        if prisoner_pop <= max_controllable:
            return  # Within capacity, no crisis

        # CONTROL_RATIO_CRISIS!
        self._emit_crisis(services, tick, enforcer_pop, prisoner_pop, max_controllable)

        # Terminal decision based on prisoner organization
        avg_organization = prisoner_org_sum / prisoner_pop if prisoner_pop > 0 else 0.0
        self._emit_terminal_decision(services, tick, avg_organization, prisoner_pop, enforcer_pop)

    def _emit_crisis(
        self,
        services: ServiceContainer,
        tick: int,
        enforcer_pop: int,
        prisoner_pop: int,
        max_controllable: int,
    ) -> None:
        """Emit CONTROL_RATIO_CRISIS event."""
        actual_ratio = prisoner_pop / enforcer_pop if enforcer_pop > 0 else float("inf")
        over_capacity_by = prisoner_pop - max_controllable

        services.event_bus.publish(
            Event(
                type=EventType.CONTROL_RATIO_CRISIS,
                tick=tick,
                payload={
                    "enforcer_population": enforcer_pop,
                    "prisoner_population": prisoner_pop,
                    "control_capacity": CONTROL_CAPACITY,
                    "max_controllable": max_controllable,
                    "actual_ratio": actual_ratio,
                    "over_capacity_by": over_capacity_by,
                    "narrative_hint": (
                        f"CONTROL RATIO CRISIS: {prisoner_pop} prisoners exceed "
                        f"{max_controllable} control capacity. "
                        f"The carceral state cannot contain the surplus."
                    ),
                },
            )
        )

    def _emit_terminal_decision(
        self,
        services: ServiceContainer,
        tick: int,
        avg_organization: float,
        prisoner_pop: int,
        enforcer_pop: int,
    ) -> None:
        """Emit TERMINAL_DECISION event based on organization level."""
        if avg_organization >= REVOLUTION_THRESHOLD:
            outcome = "revolution"
            narrative = (
                "REVOLUTION: Organized prisoners and radicalized guards unite. "
                "The carceral apparatus turns against capital."
            )
        else:
            outcome = "genocide"
            narrative = (
                "GENOCIDE: Atomized surplus population cannot resist. "
                "The system eliminates what it cannot exploit or control."
            )

        services.event_bus.publish(
            Event(
                type=EventType.TERMINAL_DECISION,
                tick=tick,
                payload={
                    "outcome": outcome,
                    "avg_organization": avg_organization,
                    "revolution_threshold": REVOLUTION_THRESHOLD,
                    "prisoner_population": prisoner_pop,
                    "enforcer_population": enforcer_pop,
                    "narrative_hint": narrative,
                },
            )
        )
