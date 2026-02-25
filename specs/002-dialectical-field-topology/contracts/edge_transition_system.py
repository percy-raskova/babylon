"""Contract: EdgeTransitionSystem (System #16).

Evaluates compound predicates against field values, derivatives, and
structural properties. Fires edge mode transitions per the state machine.
Handles CO-OPTIVE suppression, latent contradiction, and bifurcation.

Reference: FR-007 (compound predicates), FR-010 (transition topology)
Reference: FR-014-017 (CO-OPTIVE field dynamics)
Reference: R-002 (EdgeMode vs EdgeType), R-005 (predicate design)
Reference: R-006 (system ordering — position 16)

System Protocol: step(graph, services, context) -> None
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType


class EdgeTransitionSystemContract:
    """Contract for EdgeTransitionSystem.

    Execution Order: 16 (after FieldDerivativeSystem)

    Inputs (read from graph):
        - Node: contradiction_fields: dict[str, float]
        - Node: field_derivatives: dict[str, dict]
        - Edge: field_gradients: dict[str, float]
        - Edge: ricci_curvature: float
        - Edge: edge_mode: str (EdgeMode enum value)
        - Edge: co_optive_suppressed_fields: list[str] (for CO-OPTIVE edges)
        - persistent_data["latent_contradictions"]: accumulated suppression

    Outputs (written to graph):
        - Edge: edge_mode: str (updated if transition fires)
        - Node: contradiction_fields: dict[str, float]
            (modified if CO-OPTIVE suppression active or latent release)
        - Events emitted via event_bus for transitions

    Invariants:
        - Only transitions defined in the state machine (FR-010) are permitted
        - Prohibited transitions raise errors
        - Multiple eligible transitions resolved by priority (EC-003)
        - CO-OPTIVE edges with zero material flow must transition (EC-010)
        - Latent contradiction from broken CO-OPTIVE edges releases as
          df/dt spike, accounted for in continuity (EC-008)
        - Multiple CO-OPTIVE edges at one node: independent suppression
          and independent release (EC-009)
        - Bifurcation direction: solidarity magnitude comparison (SC-011)
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "edge_transition"

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Evaluate predicates and fire edge mode transitions.

        Algorithm:
            1. Auto-wrap graph if not GraphProtocol
            2. CO-OPTIVE suppression phase:
                a. For each CO-OPTIVE edge:
                    - Suppress df/dt at co-opted node for declared fields
                    - Accumulate suppressed amount in latent_contradictions
                    - Validate material flow > 0 (EC-010)
            3. Predicate evaluation phase:
                a. For each edge with an edge_mode:
                    - Collect all eligible transitions from current mode
                    - Evaluate compound predicates for each transition
                    - If multiple fire, select by priority (EC-003)
                    - Apply the highest-priority transition
            4. CO-OPTIVE breakdown handling:
                a. If a CO-OPTIVE edge transitioned away:
                    - Release latent contradiction as df/dt spike
                    - Determine bifurcation direction:
                      cross-divide solidarity > within-group → revolutionary
                      within-group > cross-divide → fascist
                    - Emit appropriate event (REVOLUTIONARY_OFFENSIVE
                      or FASCIST_REVANCHISM)
            5. Emit transition events for all mode changes
        """
        ...
