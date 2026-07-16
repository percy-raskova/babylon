"""Ideology systems for the Babylon simulation - The Superstructure.

Sprint 3.4.2b: Extended with Fascist Bifurcation mechanic.
Sprint 3.4.3: George Jackson Refactor - Multi-dimensional consciousness model.

When wages FALL, crisis creates "agitation energy" that channels into:
- Class Consciousness (if solidarity_pressure > 0) - Revolutionary Path
- National Identity (if solidarity_pressure = 0) - Fascist Path via loss aversion
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.formulas.consciousness_routing import (
    compute_agitation_delta,
    compute_exploitation_visibility,
    compute_reification_buffer,
    route_agitation_to_ternary,
)
from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType

# Context keys for storing previous values between ticks
PREVIOUS_WAGES_KEY = "previous_wages"
PREVIOUS_WEALTH_KEY = "previous_wealth"


def _get_ideology_profile_from_node(
    node_data: dict[str, Any],
) -> dict[str, float]:  # pragma: no mutate — graph accessor
    """Extract IdeologicalProfile values from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Dict with class_consciousness, national_identity, agitation keys
    """
    ideology = node_data.get("ideology")  # pragma: no mutate

    if ideology is None:  # pragma: no mutate
        # No ideology data - return defaults
        return {  # pragma: no mutate
            "class_consciousness": 0.0,  # pragma: no mutate
            "national_identity": 0.5,  # pragma: no mutate
            "agitation": 0.0,  # pragma: no mutate
        }  # pragma: no mutate

    if isinstance(ideology, dict):  # pragma: no mutate
        # IdeologicalProfile format
        return {  # pragma: no mutate
            "class_consciousness": ideology.get("class_consciousness", 0.0),  # pragma: no mutate
            "national_identity": ideology.get("national_identity", 0.5),  # pragma: no mutate
            "agitation": ideology.get("agitation", 0.0),  # pragma: no mutate
        }  # pragma: no mutate

    # Unknown format - return defaults
    return {  # pragma: no mutate
        "class_consciousness": 0.0,  # pragma: no mutate
        "national_identity": 0.5,  # pragma: no mutate
        "agitation": 0.0,  # pragma: no mutate
    }  # pragma: no mutate


class ConsciousnessSystem(SystemBase):
    """Phase 2: Consciousness Drift based on material conditions.

    Sprint 3.4.3 (George Jackson Refactor): Uses multi-dimensional IdeologicalProfile.
    - class_consciousness: Relationship to Capital [0=False, 1=Revolutionary]
    - national_identity: Relationship to State/Tribe [0=Internationalist, 1=Fascist]
    - agitation: Raw political energy from crisis (falling wages)

    Extended with Fascist Bifurcation mechanic:
    - Reads incoming SOLIDARITY edges to calculate solidarity_pressure
    - Tracks wage changes between ticks to detect crisis conditions
    - Routes agitation to either class_consciousness or national_identity
    """

    name: ClassVar[str] = "Consciousness Drift"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Apply consciousness drift to all entities with bifurcation routing."""

        # Handle both TickContext (with persistent_data) and raw dict
        # TickContext stores persistent data in .persistent_data attribute
        # Raw dict stores persistent data directly
        if hasattr(context, "persistent_data"):
            persistent: dict[str, Any] = context.persistent_data
        else:
            persistent = context

        # Lawverian wage-opposition deterioration (C1.5, signed in the Phase D
        # review). ContradictionSystem (position 18) stashes the registry
        # snapshot on the graph attr ``opposition_states``; this system
        # (position 17) reads LAST tick's wage state. Under the Phase D
        # measure the wage opposition is the true (W, V) defect and
        # ``gap == |balance|`` with balance > 0 == wage above value (the
        # bribe). Deterioration is therefore the relation SHARPENING
        # (rate > 0) while labor is on the LOSING side (balance < 0 — wage
        # sinking below value). A growing bribe (balance > 0, rate > 0) is
        # pacification and contributes ZERO agitation — Cope's crisis-gating:
        # flat during a growing bribe is CORRECT. Nominal wage cuts are the
        # separate per-worker ``wage_change`` channel below. Absent snapshot
        # (tick 1 / non-bridged tests) -> 0.
        opposition_states = graph.get_graph_attr("opposition_states", {}) or {}
        wage_state = opposition_states.get("wage", {})
        _wage_rate = float(wage_state.get("rate", 0.0))
        _wage_balance = float(wage_state.get("balance", 0.0))
        wage_deterioration = max(0.0, _wage_rate) if _wage_balance < 0.0 else 0.0

        # Initialize or retrieve previous wages tracking from persistent storage
        if PREVIOUS_WAGES_KEY not in persistent:
            persistent[PREVIOUS_WAGES_KEY] = {}
        previous_wages: dict[str, float] = persistent[PREVIOUS_WAGES_KEY]

        # Initialize or retrieve previous wealth tracking from persistent storage
        # Periphery Dynamics Extension: Track wealth extraction between ticks
        if PREVIOUS_WEALTH_KEY not in persistent:
            persistent[PREVIOUS_WEALTH_KEY] = {}
        previous_wealth: dict[str, float] = persistent[PREVIOUS_WEALTH_KEY]

        # Track current wages and wealth for next tick comparison
        current_wages: dict[str, float] = {}
        current_wealth_map: dict[str, float] = {}

        for node in graph.query_nodes(node_type="social_class"):
            attrs = node.attributes

            # Skip inactive (dead) entities - dead can't develop consciousness
            if not attrs.get("active", True):
                continue

            # Calculate wages received (sum of incoming WAGES edges)
            core_wages = 0.0
            for edge in graph.query_edges(edge_type=EdgeType.WAGES):
                if edge.target_id == node.id:
                    core_wages += edge.attributes.get("value_flow", 0.0)

            # Store current wages for next tick
            current_wages[node.id] = core_wages

            # Calculate wage_change for bifurcation mechanic
            prev_wage = previous_wages.get(node.id, core_wages)
            wage_change = core_wages - prev_wage

            # Periphery Dynamics Extension: Calculate wealth_change for extraction detection
            # Periphery workers have wealth extracted via EXPLOITATION edges, not wage cuts
            current_wealth = float(attrs.get("wealth", 0.0))
            # Default to current wealth if first tick (no previous baseline)
            prev_wealth = previous_wealth.get(node.id, current_wealth)
            wealth_change = current_wealth - prev_wealth
            current_wealth_map[node.id] = current_wealth

            # Calculate solidarity_pressure from incoming SOLIDARITY edges
            # Sum of solidarity_strength from all incoming SOLIDARITY edges
            solidarity_pressure = 0.0
            activation_threshold = services.defines.solidarity.activation_threshold

            for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
                if edge.target_id == node.id:
                    # Get solidarity_strength from edge
                    strength = edge.attributes.get("solidarity_strength", 0.0)
                    if strength > 0:
                        src_node = graph.get_node(edge.source_id)
                        src_attrs = src_node.attributes if src_node else {}
                        # GraphNode strips _node_type OUT of .attributes (the
                        # known round-trip gotcha) — read .node_type instead.
                        src_type = str(src_node.node_type) if src_node else ""
                        if src_type == "organization":
                            # DoctrineSystem Unit 6b (ADR073): an organization
                            # transmits solidarity through its MASS LINK — the
                            # corpus's "connection to the broad masses". An
                            # isolated org (MASS_LINK == 0) transmits nothing
                            # ("Low: Isolated, actions seen as terrorism"). The
                            # consciousness gate below is a class-node concept
                            # and does not apply to org sources. StrEnum keys:
                            # "mass_link" finds both enum- and str-keyed dicts.
                            doctrine_tags = src_attrs.get("doctrine_tags") or {}
                            mass_link = float(doctrine_tags.get("mass_link", 0.0))
                            if mass_link > 0:
                                bonus = services.defines.doctrine.mass_link_solidarity_bonus
                                solidarity_pressure += strength * (
                                    1.0 + bonus * min(mass_link, 10.0)
                                )
                            continue
                        # Only count if source has revolutionary consciousness
                        source_profile = _get_ideology_profile_from_node(src_attrs)
                        source_consciousness = source_profile["class_consciousness"]
                        if source_consciousness > activation_threshold:
                            solidarity_pressure += strength

            # Get current ideological profile
            current_profile = _get_ideology_profile_from_node(attrs)

            # Apply consciousness routing (Spec 043 - Value Transparency)
            # Convert wage/wealth changes to agitation via tensor pipeline
            agitation_increment = compute_agitation_delta(
                exploitation_rate_delta=abs(wage_change) if wage_change < 0 else 0.0,
                imperial_rent_delta=wealth_change,  # Wealth decline ~ rent decline
                visibility_delta=0.0,  # g₃₃ changes handled in community system
            )
            new_agitation = current_profile["agitation"] + agitation_increment + wage_deterioration

            # Route agitation through solidarity → class/nation split.
            # The ternary router (Spec 043) returns shifts in (revolutionary,
            # liberal, fascist). The legacy two-axis IdeologicalProfile maps
            #   class_consciousness  ← revolutionary (delta_r)
            #   national_identity    ← fascist       (delta_f)
            # liberal drain (delta_l) is the *backpressure* on the liberal
            # tendency and intentionally has no projection onto either
            # legacy axis. Until the Spec 043 refactor was completed, this
            # block discarded delta_f and added abs(delta_l) to
            # national_identity, which made every wage cut grow
            # national_identity by the same amount as class_consciousness
            # under any solidarity level — defeating the bifurcation.
            delta_r, _delta_l, delta_f = route_agitation_to_ternary(
                agitation=new_agitation,
                solidarity_factor=min(1.0, solidarity_pressure),
                education_pressure=0.0,  # Education pressure handled in community system
            )
            new_class = min(1.0, current_profile["class_consciousness"] + delta_r)
            new_nation = min(1.0, current_profile["national_identity"] + delta_f)
            # Decay agitation after routing
            decay_rate = services.defines.consciousness.agitation_decay_rate
            new_agitation = max(0.0, new_agitation * (1.0 - decay_rate))

            # Update the ideology in the graph as a dict (IdeologicalProfile format)
            # Also write MaterialConditionsBuffer for downstream systems
            graph.update_node(
                node.id,
                ideology={
                    "class_consciousness": new_class,
                    "national_identity": new_nation,
                    "agitation": new_agitation,
                },
                material_conditions={
                    "agitation": new_agitation,
                    "exploitation_visibility": compute_exploitation_visibility(
                        exploitation_rate=abs(wage_change) if wage_change < 0 else 0.0,
                        imperial_rent=max(0.0, wealth_change),
                    ),
                    "reification_buffer": compute_reification_buffer(
                        imperial_rent=max(0.0, wealth_change),
                        total_v=max(1.0, core_wages),
                    ),
                },
            )

        # Update previous wages and wealth for next tick in persistent storage
        persistent[PREVIOUS_WAGES_KEY] = current_wages
        persistent[PREVIOUS_WEALTH_KEY] = current_wealth_map
