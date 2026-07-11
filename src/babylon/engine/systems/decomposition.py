"""Decomposition system for class breakdown during terminal crisis.

Implements LA decomposition during SUPERWAGE_CRISIS:
- 30% of Labor Aristocracy becomes CARCERAL_ENFORCER (guards, cops)
- 70% falls into INTERNAL_PROLETARIAT (precariat, unemployed)

This models the shift from productive jobs to carceral jobs as the imperial
economy contracts. The carceral state expands to manage the surplus population.

See ai/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.kernel.event_bus import Event
from babylon.models.entity_registry import CORE_BOURGEOISIE_ID
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType

# Spec-071 create-on-demand id offsets (keep clear of bridge ids: workers
# C000-C082, bourgeois C500-C582). Enforcers land in the C7xx band, internal
# proletariat in the C8xx band.
_ENFORCER_ID_OFFSET = 700
_INTERNAL_PROLETARIAT_ID_OFFSET = 800


def _derive_entity_id(graph: GraphProtocol, base_id: str, offset: int) -> str:
    """Deterministically derive a free, pattern-valid (``^C[0-9]{3}$``) node id.

    The numeric part of ``base_id`` plus ``offset`` (mod 1000), advanced past
    any collision. Deterministic (no ``hash()`` — III.7): the same graph +
    inputs always yield the same id. Falls back to the offset alone when
    ``base_id`` carries no digits (e.g. test ids like ``C_w``).
    """
    digits = "".join(c for c in base_id if c.isdigit())
    seed = (int(digits) % 1000) if digits else 0
    for i in range(1000):
        candidate = f"C{(seed + offset + i) % 1000:03d}"
        if graph.get_node(candidate) is None:
            return candidate
    return f"C{(seed + offset) % 1000:03d}"  # pragma: no cover - 1000 ids exhausted


def _find_entity_by_role(
    graph: GraphProtocol,
    role: SocialRole,
    *,
    include_inactive: bool = False,
) -> tuple[str, dict[str, Any]] | None:
    """Find the first entity with the specified social role.

    Args:
        graph: The simulation graph (protocol or raw)
        role: The SocialRole to search for
        include_inactive: If True, include inactive entities

    Returns:
        Tuple of (node_id, node_data) or None if not found
    """
    for node in graph.query_nodes(node_type="social_class"):
        attrs = node.attributes

        # Skip inactive unless explicitly requested
        if not include_inactive and not attrs.get("active", True):
            continue

        node_role = attrs.get("role")
        if isinstance(node_role, str):
            try:
                node_role = SocialRole(node_role)
            except ValueError:
                continue

        if node_role == role:
            return (node.id, attrs)

    return None


class DecompositionSystem(SystemBase):
    """Handles class decomposition during terminal crisis.

    The Labor Aristocracy decomposes when super-wages can't be paid:
    - Checks event bus history for SUPERWAGE_CRISIS events
    - Splits LA population: 30% enforcer / 70% internal proletariat
    - Transfers wealth proportionally
    - Emits CLASS_DECOMPOSITION event

    Must run AFTER ImperialRentSystem (which emits SUPERWAGE_CRISIS).
    """

    name: ClassVar[str] = "Decomposition"
    # Spec 053 INV-001: DecompositionSystem transfers wealth proportionally
    # during LA decomposition. Default-deny while audit pending; flip to
    # False once internal redistribution is proven sum-preserving.
    creates_value: ClassVar[bool] = True

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Check for SUPERWAGE_CRISIS and execute LA decomposition with delay.

        Uses persistent_data to track when SUPERWAGE_CRISIS was detected
        and delays CLASS_DECOMPOSITION by the configured number of ticks.
        This ensures phase staggering (temporal separation between phases).
        """

        tick = context.get("tick", 0)
        # Handle both TickContext (with persistent_data) and raw dict
        if hasattr(context, "persistent_data"):
            persistent: dict[str, Any] = context.persistent_data
        else:
            persistent = context

        # Check if already decomposed (one-time event)
        if persistent.get("_decomposition_complete"):
            return

        # Check trigger conditions:
        # 1. SUPERWAGE_CRISIS has been detected + delay elapsed
        # 2. LA is about to die (wealth below subsistence) - fallback trigger
        #
        # The fallback ensures decomposition happens before LA dies naturally,
        # which would prevent the carceral phase from executing properly.

        # Check for LA about to die (fallback trigger)
        # We use two thresholds:
        # - "approaching subsistence": emit SUPERWAGE_CRISIS early
        # - "below subsistence": execute CLASS_DECOMPOSITION
        # This ensures at least 1 tick gap between the events
        la = _find_entity_by_role(graph, SocialRole.LABOR_ARISTOCRACY)
        la_approaching_death = False
        la_about_to_die = False
        la_id = None
        if la is not None:
            la_id, la_data = la
            la_wealth = la_data.get("wealth", 0.0)
            subsistence = la_data.get("subsistence_threshold", 0.0)
            la_pop = la_data.get("population", 0)
            # Estimate per-tick consumption (s_bio + s_class)
            consumption = la_data.get("s_bio", 0.0) + la_data.get("s_class", 0.0)
            # "Approaching": within 2 ticks of subsistence
            if la_wealth < subsistence + (2 * consumption) and la_pop > 0:
                la_approaching_death = True
            # "About to die": below subsistence
            if la_wealth < subsistence and la_pop > 0:
                la_about_to_die = True

        # Check if SUPERWAGE_CRISIS has been detected
        superwage_tick = persistent.get("_superwage_crisis_tick")

        if superwage_tick is None:
            # Look for SUPERWAGE_CRISIS events in history
            # Use explicit .value for robust string comparison
            crisis_events = [
                e
                for e in services.event_bus.get_history()
                if e.type == EventType.SUPERWAGE_CRISIS.value
            ]
            if crisis_events:
                # Record the tick when crisis was first detected
                superwage_tick = min(e.tick for e in crisis_events)
                persistent["_superwage_crisis_tick"] = superwage_tick

        # Early warning: emit SUPERWAGE_CRISIS when LA is approaching death
        # This ensures at least 1 tick gap before CLASS_DECOMPOSITION
        if la_approaching_death and superwage_tick is None and la_id is not None:
            services.event_bus.publish(
                Event(
                    type=EventType.SUPERWAGE_CRISIS,
                    tick=tick,
                    payload={
                        "payer_id": CORE_BOURGEOISIE_ID,  # Core bourgeoisie
                        "receiver_id": la_id,
                        "desired_wages": 0.0,
                        "available_pool": 0.0,
                        "narrative_hint": (
                            "SUPERWAGE CRISIS: Labor aristocracy wealth collapsing. "
                            "Super-wages cannot sustain the privileged stratum."
                        ),
                    },
                )
            )
            persistent["_superwage_crisis_tick"] = tick
            superwage_tick = tick  # Update local variable for delay check

        # Determine if we should decompose now
        should_decompose = False
        if la_about_to_die:
            # Fallback: LA is dying, decompose immediately to prevent loss
            should_decompose = True
        elif superwage_tick is not None:
            # Normal path: check if delay has elapsed
            delay = services.defines.carceral.decomposition_delay
            if tick >= superwage_tick + delay:
                should_decompose = True

        if not should_decompose:
            return

        # Execute decomposition
        # Note: We don't re-fetch the crisis event from EventBus because
        # EventBus is recreated each tick (ephemeral). The trigger event
        # type is always SUPERWAGE_CRISIS when this code path executes.
        success = self._execute_decomposition(graph, services, tick)

        # Mark as complete and record tick for ControlRatioSystem
        # Only mark complete if decomposition actually happened
        if success:
            persistent["_decomposition_complete"] = True
            persistent["_class_decomposition_tick"] = tick

    @staticmethod
    def _create_target_entity(
        graph: GraphProtocol,
        role: SocialRole,
        la_id: str,
        la_data: dict[str, Any],
        offset: int,
    ) -> tuple[str, dict[str, Any]]:
        """Create an inactive decomposition target node on demand (spec-071).

        Seeds a minimal ``social_class`` node (population/wealth 0, ``active``
        False until the transfer flips it on) inheriting the LA's county so it
        participates in per-county aggregation. Returns ``(id, attributes)``
        matching the :func:`_find_entity_by_role` shape.
        """
        new_id = _derive_entity_id(graph, la_id, offset)
        graph.add_node(
            new_id,
            "social_class",
            # Model-complete payload (Design B): SocialClass requires id AND
            # name — from_graph-side id injection alone cannot supply name
            # (min_length=1), so the writer must. Deterministic (no hash()
            # — Constitution III.7).
            id=new_id,
            name=f"{role.value} (decomposed from {la_id})",
            role=role.value,
            active=False,
            population=0,
            wealth=0.0,
            county_fips=la_data.get("county_fips"),
            subsistence_threshold=la_data.get("subsistence_threshold", 0.0),
            s_bio=la_data.get("s_bio", 0.01),
            s_class=la_data.get("s_class", 0.0),
            inequality=la_data.get("inequality", 0.0),
        )
        created = graph.get_node(new_id)
        return (new_id, created.attributes if created is not None else {})

    def _execute_decomposition(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
    ) -> bool:
        """Execute LA decomposition based on carceral defines.

        Args:
            graph: The simulation graph (protocol or raw)
            services: Service container
            tick: Current simulation tick

        Returns:
            True if decomposition happened, False otherwise.
        """
        # Find Labor Aristocracy
        la = _find_entity_by_role(graph, SocialRole.LABOR_ARISTOCRACY)
        if la is None:
            return False  # No LA to decompose (or already decomposed)

        la_id, la_data = la

        # Get LA population and wealth
        la_population = la_data.get("population", 0)
        la_wealth = la_data.get("wealth", 0.0)

        if la_population <= 0:
            return False  # Nothing to decompose

        # Get decomposition fractions from defines (tunable parameters)
        enforcer_fraction = services.defines.carceral.enforcer_fraction
        proletariat_fraction = services.defines.carceral.proletariat_fraction

        # Calculate splits
        enforcer_pop_gain = int(la_population * enforcer_fraction)
        proletariat_pop = int(la_population * proletariat_fraction)
        enforcer_wealth_gain = la_wealth * enforcer_fraction
        proletariat_wealth = la_wealth * proletariat_fraction

        # Find (or, spec-071, create on demand) target entities. The bridged
        # canonical world seeds no CARCERAL_ENFORCER / INTERNAL_PROLETARIAT
        # entity, so without this the enforcer branch no-ops (project/02 §5b).
        enforcer = _find_entity_by_role(graph, SocialRole.CARCERAL_ENFORCER, include_inactive=True)
        if enforcer is None:
            enforcer = self._create_target_entity(
                graph, SocialRole.CARCERAL_ENFORCER, la_id, la_data, _ENFORCER_ID_OFFSET
            )
        internal_proletariat = _find_entity_by_role(
            graph, SocialRole.INTERNAL_PROLETARIAT, include_inactive=True
        )
        if internal_proletariat is None:
            internal_proletariat = self._create_target_entity(
                graph,
                SocialRole.INTERNAL_PROLETARIAT,
                la_id,
                la_data,
                _INTERNAL_PROLETARIAT_ID_OFFSET,
            )

        # Transfer to CARCERAL_ENFORCER
        enforcer_id, enforcer_data = enforcer
        current_pop = enforcer_data.get("population", 0)
        current_wealth = enforcer_data.get("wealth", 0.0)
        graph.update_node(
            enforcer_id,
            population=current_pop + enforcer_pop_gain,
            wealth=current_wealth + enforcer_wealth_gain,
            active=True,
        )

        # Transfer to INTERNAL_PROLETARIAT
        ip_id, _ = internal_proletariat
        graph.update_node(ip_id, population=proletariat_pop, wealth=proletariat_wealth, active=True)

        # Deactivate Labor Aristocracy (decomposed)
        graph.update_node(la_id, active=False)

        # Emit CLASS_DECOMPOSITION event
        services.event_bus.publish(
            Event(
                type=EventType.CLASS_DECOMPOSITION,
                tick=tick,
                payload={
                    "source_class": la_id,
                    "source_population": la_population,
                    "source_wealth": la_wealth,
                    "enforcer_fraction": enforcer_fraction,
                    "proletariat_fraction": proletariat_fraction,
                    "population_transferred": {
                        "to_enforcer": enforcer_pop_gain,
                        "to_proletariat": proletariat_pop,
                    },
                    "wealth_transferred": {
                        "to_enforcer": enforcer_wealth_gain,
                        "to_proletariat": proletariat_wealth,
                    },
                    "trigger_event": EventType.SUPERWAGE_CRISIS.value,
                    "narrative_hint": (
                        "CLASS DECOMPOSITION: Labor aristocracy collapses. "
                        f"{enforcer_pop_gain} become guards/cops. "
                        f"{proletariat_pop} fall into the precariat."
                    ),
                },
            )
        )
        return True
