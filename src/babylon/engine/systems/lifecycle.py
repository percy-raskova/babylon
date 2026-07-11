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
from typing import TYPE_CHECKING, ClassVar

from babylon.economics.lifecycle.cohort_dynamics import DefaultCohortDynamicsCalculator
from babylon.economics.lifecycle.inheritance import DefaultInheritanceCalculator
from babylon.economics.lifecycle.legitimation import DefaultLegitimationCalculator
from babylon.economics.lifecycle.mobility import DefaultClassMobilityCalculator
from babylon.economics.lifecycle.types import ClassMobilityParams, DPDState, LegitimationState
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import EventType, LegitimationClassification

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

logger = logging.getLogger(__name__)


class LifecycleSystem(SystemBase):
    """D-P-D' lifecycle circuit system (Feature 030).

    Tracks population cohorts across three lifecycle phases per county,
    computes legitimation indices, models inheritance flows, transmits
    ideology, and detects dual-circuit interference.

    Turn position: After CommunitySystem, before SolidaritySystem.
    """

    name: ClassVar[str] = "Lifecycle Circuit"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def __init__(self) -> None:
        self._cohort_calc = DefaultCohortDynamicsCalculator()
        self._legit_calc = DefaultLegitimationCalculator()
        self._inherit_calc = DefaultInheritanceCalculator()
        self._mobility_calc = DefaultClassMobilityCalculator()

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Execute lifecycle circuit for one tick.

        Args:
            graph: Mutable simulation graph.
            services: Service container with defines, event_bus.
            context: Tick context.
        """

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

            # Step 4: Compute inheritance flow when deaths > 0
            inheritance_flow = self._inherit_calc.compute_inheritance_flow(
                dpd_state=new_state,
                pareto_alpha=defines.pareto_alpha,
                care_cost_fraction=defines.care_cost_fraction,
            )
            if inheritance_flow is not None:
                services.event_bus.publish(
                    Event(
                        type=EventType.INHERITANCE_TRANSFER,
                        tick=tick,
                        payload={
                            "territory_id": territory_id,
                            "total_transferred": float(inheritance_flow.total_transferred),
                            "care_consumed": float(inheritance_flow.care_consumed),
                            "net_inheritance": float(inheritance_flow.net_inheritance),
                            "inheritance_gini": float(inheritance_flow.inheritance_gini),
                        },
                    )
                )

            # Step 5: Compute ideology transmission for D→P cohort
            caregiver_ideology = float(attrs.get("caregiver_ideology", 0.5))
            institutional_hegemony = float(attrs.get("institutional_hegemony", 0.5))
            community_tendency_raw = attrs.get("community_tendency")
            community_tendency = (
                float(community_tendency_raw) if community_tendency_raw is not None else None
            )
            transmitted_ideology = self._cohort_calc.compute_ideology_transmission(
                caregiver_ideology=caregiver_ideology,
                institutional_hegemony=institutional_hegemony,
                defines=defines,
                community_tendency=community_tendency,
            )
            graph.update_node(
                territory_id,
                transmitted_ideology=transmitted_ideology,
            )

            # Step 6: Apply class mobility parameters
            mobility_data = attrs.get("mobility_params")
            if mobility_data is not None and isinstance(mobility_data, dict):
                mobility_params = ClassMobilityParams(**mobility_data)
            elif isinstance(mobility_data, ClassMobilityParams):
                mobility_params = mobility_data
            else:
                mobility_params = ClassMobilityParams(
                    mobility_base_rate=defines.mobility_base_rate,
                    mobility_base_rate_p75=defines.mobility_base_rate_p75,
                    mobility_racial_gap=defines.mobility_racial_gap,
                    carceral_modifier=defines.carceral_transition_modifier,
                    early_mortality_modifier=defines.early_mortality_modifier,
                    baseline_gini=defines.baseline_gini,
                    poverty_share=defines.poverty_share,
                    employment_rate=defines.employment_rate,
                    single_parent_fraction=defines.single_parent_fraction,
                    college_rate=defines.college_rate,
                )
            # Store mobility-adjusted P→D' rate on graph for downstream use
            adjusted_p_to_d_prime = self._mobility_calc.compute_premature_exit_rate(
                base_rate=new_state.rate_p_to_d_prime,
                mortality_modifier=mobility_params.early_mortality_modifier,
                carceral_modifier=1.0,  # Carceral applied per-subpopulation, not aggregate
            )
            graph.update_node(
                territory_id,
                mobility_params=mobility_params.model_dump(),
                adjusted_p_to_d_prime=adjusted_p_to_d_prime,
            )

            # Step 7: Apply differential rates for structural inequality
            differential_state = self._cohort_calc.apply_differential_rates(
                new_state,
                defines,
                early_mortality_modifier=mobility_params.early_mortality_modifier,
                carceral_modifier=mobility_params.carceral_modifier,
            )
            # Write differential-adjusted rate for downstream use
            graph.update_node(
                territory_id,
                differential_p_to_d_prime=differential_state.rate_p_to_d_prime,
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
