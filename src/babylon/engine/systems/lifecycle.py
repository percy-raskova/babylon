"""LifecycleSystem for D-P-D' population dynamics (Feature 030).

Positioned between CommunitySystem and SolidaritySystem per ADR032
materialist causality order. Computes population transitions, legitimation,
inheritance, dual-circuit interference, and ideology transmission for
each county territory node.

See Also:
    :mod:`babylon.economics.lifecycle`: Calculator implementations.
    ``specs/030-dpd-lifecycle-circuit/contracts/lifecycle-system-contract.md``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.economics.lifecycle.cohort_dynamics import DefaultCohortDynamicsCalculator
from babylon.economics.lifecycle.legitimation import DefaultLegitimationCalculator
from babylon.economics.lifecycle.types import DPDState, LegitimationState
from babylon.engine.event_bus import Event
from babylon.models.enums import EventType, LegitimationClassification

if TYPE_CHECKING:
    import networkx as nx

    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType

logger = logging.getLogger(__name__)


class LifecycleSystem:
    """D-P-D' lifecycle circuit system (Feature 030).

    Tracks population cohorts across three lifecycle phases per county,
    computes legitimation indices, models inheritance flows, transmits
    ideology, and detects dual-circuit interference.

    Turn position: After CommunitySystem, before SolidaritySystem.
    """

    name = "Lifecycle Circuit"

    def __init__(self) -> None:
        self._cohort_calc = DefaultCohortDynamicsCalculator()
        self._legit_calc = DefaultLegitimationCalculator()

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Execute lifecycle circuit for one tick.

        Args:
            graph: Mutable simulation graph.
            services: Service container with defines, event_bus.
            context: Tick context.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        defines = services.defines.lifecycle
        tick = context.tick if hasattr(context, "tick") else context.get("tick", 0)

        for node in graph.query_nodes(node_type="territory"):
            attrs = node.attributes
            territory_id = node.id

            # Read or initialize DPDState
            dpd_data = attrs.get("dpd_state")
            if dpd_data is not None and isinstance(dpd_data, dict):
                dpd_state = DPDState(**dpd_data)
            elif isinstance(dpd_data, DPDState):
                dpd_state = dpd_data
            else:
                # Initialize from defines defaults
                total_pop = float(attrs.get("population", 10000.0))
                dpd_state = DPDState(
                    pop_d=total_pop * defines.initial_pop_d_frac,
                    pop_p=total_pop * defines.initial_pop_p_frac,
                    pop_d_prime=total_pop * defines.initial_pop_d_prime_frac,
                    rate_d_to_p=defines.rate_d_to_p,
                    rate_p_to_d_prime=defines.rate_p_to_d_prime,
                    rate_d_prime_to_death=defines.rate_d_prime_to_death,
                    birth_rate=defines.birth_rate,
                    wealth_d_prime=float(attrs.get("wealth_d_prime", 0.0)),
                )

            # Step 1: Compute population transitions
            new_state = self._cohort_calc.compute_transitions(dpd_state, defines)

            # Step 2: Verify conservation
            if not self._cohort_calc.verify_conservation(dpd_state, new_state):
                logger.warning(
                    "Population conservation violation at tick %d, territory %s",
                    tick,
                    territory_id,
                )

            # Step 3: Compute legitimation index
            legit_state = self._read_legitimation_state(attrs, defines)
            legitimation_index = self._legit_calc.compute_index(legit_state, defines)
            crisis_class = self._legit_calc.classify_crisis(legitimation_index, defines)

            # Write updated state to graph
            graph.update_node(
                territory_id,
                dpd_state=new_state.model_dump(),
                dependency_ratio=new_state.dependency_ratio,
                legitimation_index=legitimation_index,
                legitimation_crisis=crisis_class.value,
            )

            # Emit transition event
            services.event_bus.publish(
                Event(
                    type=EventType.LIFECYCLE_TRANSITION,
                    tick=tick,
                    payload={
                        "territory_id": territory_id,
                        "pop_d": new_state.pop_d,
                        "pop_p": new_state.pop_p,
                        "pop_d_prime": new_state.pop_d_prime,
                        "dependency_ratio": new_state.dependency_ratio,
                    },
                )
            )

            # Emit crisis/recovery events
            prev_crisis = attrs.get("legitimation_crisis")
            if crisis_class == LegitimationClassification.CRISIS and prev_crisis != "CRISIS":
                services.event_bus.publish(
                    Event(
                        type=EventType.LEGITIMATION_CRISIS,
                        tick=tick,
                        payload={
                            "territory_id": territory_id,
                            "legitimation_index": legitimation_index,
                        },
                    )
                )
            elif crisis_class == LegitimationClassification.STABLE and prev_crisis == "CRISIS":
                services.event_bus.publish(
                    Event(
                        type=EventType.LEGITIMATION_RECOVERY,
                        tick=tick,
                        payload={
                            "territory_id": territory_id,
                            "legitimation_index": legitimation_index,
                        },
                    )
                )

    @staticmethod
    def _read_legitimation_state(
        attrs: dict[str, object],
        defines: object,
    ) -> LegitimationState:
        """Read or initialize LegitimationState from territory attributes.

        Args:
            attrs: Node attributes dict.
            defines: LifecycleDefines with default component values.

        Returns:
            LegitimationState for this territory.
        """
        legit_data = attrs.get("legitimation_state")
        if legit_data is not None and isinstance(legit_data, dict):
            return LegitimationState(**legit_data)
        if isinstance(legit_data, LegitimationState):
            return legit_data

        # Initialize from defines defaults
        from babylon.config.defines import LifecycleDefines

        if isinstance(defines, LifecycleDefines):
            return LegitimationState(
                pension_coverage=defines.pension_coverage_rate,
                ss_replacement_rate=defines.ss_replacement_rate,
                healthcare_security=defines.healthcare_security,
                home_ownership_rate=defines.home_ownership_rate,
                retirement_confidence=defines.retirement_confidence,
            )
        # Fallback to moderate values
        return LegitimationState(
            pension_coverage=0.5,
            ss_replacement_rate=0.4,
            healthcare_security=0.6,
            home_ownership_rate=0.64,
            retirement_confidence=0.5,
        )


__all__ = ["LifecycleSystem"]
