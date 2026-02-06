"""TickDynamicsSystem: per-tick state evolution engine System.

Feature: 017-simulation-tick-dynamics

Integrates Features 012-016 economics calculators into a unified per-tick
pipeline conforming to the engine's System protocol.

Pipeline Steps:
    1. (Init only) Load economic data
    2. Compute national parameters (tau, gamma_basket, gamma_III)
    3a. Compute county-level state (K, pi, D per county)
    3b. Apply coefficient smoothing
    4. Compute imperial rent flows (phi_hour per county)
    5. Check crisis triggers
    6. Simulate class transitions (Feature 016)
    7. Validate class distribution (sum-to-one invariant)
    8. Compute derived rates and assemble TickSummary

See Also:
    :mod:`babylon.engine.systems.protocol`: System protocol
    :mod:`babylon.economics.tick.types`: Data models
    :mod:`babylon.economics.tick.graph_bridge`: Graph serialization
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import networkx as nx

from babylon.economics.dynamics.types import ClassDistribution, EconomicConditions
from babylon.economics.tick.graph_bridge import (
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.economics.tick.types import (
    CountyEconomicState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType

logger = logging.getLogger(__name__)

# Year boundary: 52 weeks per year (FR-024)
WEEKS_PER_YEAR: int = 52

# Default subsistence cost ($/hour) for MVP
DEFAULT_V_REPRODUCTION: float = 12.0

# Default dispossession rates (MVP: hardcoded national averages)
DEFAULT_FORECLOSURE_RATE: float = 0.006
DEFAULT_BANKRUPTCY_RATE: float = 0.006
DEFAULT_EVICTION_RATE: float = 0.063


class TickDynamicsSystem:
    """Engine System for per-tick economic state evolution.

    Conforms to the System protocol (name + step). Executes the 8-step
    pipeline on year boundaries, writing results to the shared graph.

    Example:
        >>> system = TickDynamicsSystem()
        >>> system.step(graph, services, context)
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "tick_dynamics"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Execute tick dynamics pipeline on year boundaries.

        Args:
            graph: Mutable NetworkX graph (modified in-place).
            services: ServiceContainer with calculator services.
            context: TickContext or dict with tick number.
        """
        # Extract tick number
        tick: int
        if hasattr(context, "tick"):
            tick = context.tick
        elif isinstance(context, dict):
            tick = context.get("tick", 0)
        else:
            tick = 0

        # Gate: only execute on year boundaries (FR-024)
        if tick % WEEKS_PER_YEAR != 0:
            return

        # Check for required calculators
        if services.melt_calculator is None:
            logger.debug("TickDynamicsSystem: no calculators configured, skipping")
            return

        # Read existing state from graph (if any)
        existing_state = read_tick_state_from_graph(graph)

        # Determine current year
        if existing_state is not None:
            year = existing_state.year + 1
            prev_coefficients = existing_state.coefficients
            prev_county_states = existing_state.county_states
        else:
            year = self._determine_year(tick)
            prev_coefficients = None
            prev_county_states = self._bootstrap_county_states(graph, year)

        # Step 2: Compute national parameters
        national_params = self._compute_national_params(year, services, prev_coefficients)
        if national_params is None:
            return

        # Step 3a: Compute county-level state
        county_fips = (
            list(prev_county_states.keys())
            if prev_county_states
            else self._get_territory_fips(graph)
        )
        county_states = self._compute_county_states(year, county_fips, services, prev_county_states)

        # Step 3b: Update smoothed coefficients
        coefficients = self._update_coefficients(national_params, prev_coefficients)

        # Step 4: Compute imperial rent flows
        county_states = self._compute_imperial_rent(county_states, national_params, services)

        # Step 5: Check crisis triggers
        county_states = self._check_crisis_triggers(county_states)

        # Step 6: Simulate class transitions
        county_states = self._simulate_transitions(county_states, national_params, services)

        # Step 7: Validate class distribution invariant
        self._validate_distributions(county_states)

        # Assemble state (tick_summary added in Phase 8)
        new_state = SimulationTickState(
            year=year,
            national_params=national_params,
            county_states=county_states,
            coefficients=coefficients,
        )

        # Write to graph
        write_tick_state_to_graph(graph, new_state)

    def _determine_year(self, tick: int) -> int:
        """Determine simulation year from tick number.

        Args:
            tick: Current tick number.

        Returns:
            Estimated year (2010 + tick // WEEKS_PER_YEAR).
        """
        return 2010 + tick // WEEKS_PER_YEAR

    def _get_territory_fips(self, graph: nx.DiGraph[str]) -> list[str]:
        """Extract FIPS codes from territory nodes in graph.

        Args:
            graph: NetworkX graph.

        Returns:
            List of FIPS codes for territory nodes.
        """
        fips_list: list[str] = []
        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") == "territory":
                fips_list.append(str(node_id))
        return fips_list

    def _bootstrap_county_states(
        self,
        graph: nx.DiGraph[str],
        year: int,
    ) -> dict[str, CountyEconomicState]:
        """Bootstrap county states from graph territory nodes.

        Args:
            graph: NetworkX graph with territory nodes.
            year: Current year.

        Returns:
            Dict of FIPS -> CountyEconomicState with defaults.
        """
        states: dict[str, CountyEconomicState] = {}
        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") != "territory":
                continue
            fips = str(node_id)

            # Read existing tick_ attributes if present
            if "tick_capital_stock" in data:
                dist_dict = data.get("tick_class_distribution", {})
                clamped_year = min(max(year, 2007), 2030)
                dist = ClassDistribution(
                    fips=fips,
                    year=clamped_year,
                    bourgeoisie_share=dist_dict.get("bourgeoisie", 0.01),
                    petit_bourgeoisie_share=dist_dict.get("petit_bourgeoisie", 0.09),
                    labor_aristocracy_share=dist_dict.get("labor_aristocracy", 0.40),
                    proletariat_share=dist_dict.get("proletariat", 0.35),
                    lumpenproletariat_share=dist_dict.get("lumpenproletariat", 0.15),
                )
                states[fips] = CountyEconomicState(
                    fips=fips,
                    year=min(max(year, 2007), 2040),
                    capital_stock=data["tick_capital_stock"],
                    throughput_position=data.get("tick_throughput_position", 1.0),
                    supply_chain_depth=data.get("tick_supply_chain_depth", 2.0),
                    unemployment_rate=data.get("tick_unemployment_rate", 0.05),
                    u6_rate=data.get("tick_u6_rate", 0.10),
                    pter_rate=data.get("tick_pter_rate", 0.04),
                    nilf_rate=data.get("tick_nilf_rate", 0.06),
                    median_wage=data.get("tick_median_wage", 21.0),
                    employment=data.get("tick_employment", 100_000.0),
                    class_distribution=dist,
                    phi_hour=data.get("tick_phi_hour", 0.0),
                    crisis=data.get("tick_crisis", False),
                )
        return states

    def _compute_national_params(
        self,
        year: int,
        services: ServiceContainer,
        prev_coefficients: SmoothedCoefficients | None,
    ) -> NationalTickParameters | None:
        """Step 2: Compute national parameters.

        Args:
            year: Current year.
            services: ServiceContainer with calculators.
            prev_coefficients: Previous smoothed coefficients (None on first tick).

        Returns:
            NationalTickParameters, or None if critical data unavailable.
        """
        # Get tau from MELTCalculator
        tau_result = services.melt_calculator.get_melt(year)
        if not tau_result and not isinstance(tau_result, (int, float)):
            logger.warning("TickDynamics Step 2: MELT unavailable for year %d", year)
            return None
        tau = float(tau_result)

        # Get gamma_basket from BasketVisibilityCalculator
        gamma_basket_raw: float = 0.68
        estimated: bool = True
        if services.basket_calculator is not None:
            gb_result = services.basket_calculator.get_gamma_basket(year)
            gamma_basket_raw = gb_result[0]
            estimated = gb_result[1]

        # Get gamma_III from GammaIIICalculator
        gamma_III_raw: float = 0.33
        if services.gamma_calculator is not None:
            g3_result = services.gamma_calculator.compute(year)
            if g3_result and not isinstance(g3_result, type(None)):
                gamma_III_raw = g3_result.gamma_iii

        # Apply smoothing if previous coefficients exist
        gamma_basket = gamma_basket_raw
        gamma_III = gamma_III_raw
        if prev_coefficients is not None and prev_coefficients.is_initialized:
            alpha = prev_coefficients.alpha
            gamma_basket = prev_coefficients.gamma_basket + alpha * (
                gamma_basket_raw - prev_coefficients.gamma_basket
            )
            gamma_III = prev_coefficients.gamma_III + alpha * (
                gamma_III_raw - prev_coefficients.gamma_III
            )

        tau_effective = tau * gamma_basket

        clamped_year = min(max(year, 2007), 2040)
        return NationalTickParameters(
            year=clamped_year,
            tau=tau,
            gamma_basket=gamma_basket,
            gamma_basket_raw=gamma_basket_raw,
            gamma_III=gamma_III,
            gamma_III_raw=gamma_III_raw,
            tau_effective=tau_effective,
            v_reproduction=DEFAULT_V_REPRODUCTION,
            estimated=estimated,
        )

    def _compute_county_states(
        self,
        year: int,
        county_fips: list[str],
        services: ServiceContainer,
        prev_county_states: dict[str, CountyEconomicState] | None,
    ) -> dict[str, CountyEconomicState]:
        """Step 3a: Compute county-level state.

        Args:
            year: Current year.
            county_fips: List of FIPS codes to process.
            services: ServiceContainer with calculators.
            prev_county_states: Previous county states.

        Returns:
            Dict of FIPS -> updated CountyEconomicState.
        """
        states: dict[str, CountyEconomicState] = {}
        clamped_year = min(max(year, 2007), 2040)

        for fips in county_fips:
            prev = prev_county_states.get(fips) if prev_county_states else None

            # Get capital stock K from calculator
            capital_stock: float = prev.capital_stock if prev else 0.0
            if services.capital_calculator is not None:
                k_result = services.capital_calculator.get_K(fips, year)
                if k_result and isinstance(k_result, (int, float)):
                    capital_stock = float(k_result)

            # Get throughput metrics from calculator
            throughput_position: float = prev.throughput_position if prev else 1.0
            supply_chain_depth: float = prev.supply_chain_depth if prev else 2.0
            if services.throughput_calculator is not None:
                tp_result = services.throughput_calculator.compute_metrics(fips, year)
                if tp_result and hasattr(tp_result, "pi") and tp_result.pi is not None:
                    throughput_position = tp_result.pi
                    supply_chain_depth = tp_result.supply_chain_depth

            # Preserve previous precarity/labor indicators
            unemployment_rate = prev.unemployment_rate if prev else 0.05
            u6_rate = prev.u6_rate if prev else 0.10
            pter_rate = prev.pter_rate if prev else 0.04
            nilf_rate = prev.nilf_rate if prev else 0.06
            median_wage = prev.median_wage if prev else 21.0
            employment = prev.employment if prev else 100_000.0
            phi_hour = prev.phi_hour if prev else 0.0
            crisis = prev.crisis if prev else False

            # Preserve class distribution
            if prev is not None:
                class_dist = prev.class_distribution
                # Update year if different
                if class_dist.year != clamped_year:
                    clamped_dist_year = min(max(clamped_year, 2007), 2030)
                    class_dist = ClassDistribution(
                        fips=fips,
                        year=clamped_dist_year,
                        bourgeoisie_share=class_dist.bourgeoisie_share,
                        petit_bourgeoisie_share=class_dist.petit_bourgeoisie_share,
                        labor_aristocracy_share=class_dist.labor_aristocracy_share,
                        proletariat_share=class_dist.proletariat_share,
                        lumpenproletariat_share=class_dist.lumpenproletariat_share,
                    )
            else:
                class_dist = ClassDistribution(
                    fips=fips,
                    year=min(max(clamped_year, 2007), 2030),
                    bourgeoisie_share=0.01,
                    petit_bourgeoisie_share=0.09,
                    labor_aristocracy_share=0.40,
                    proletariat_share=0.35,
                    lumpenproletariat_share=0.15,
                )

            states[fips] = CountyEconomicState(
                fips=fips,
                year=clamped_year,
                capital_stock=capital_stock,
                throughput_position=throughput_position,
                supply_chain_depth=supply_chain_depth,
                unemployment_rate=unemployment_rate,
                u6_rate=u6_rate,
                pter_rate=pter_rate,
                nilf_rate=nilf_rate,
                median_wage=median_wage,
                employment=employment,
                class_distribution=class_dist,
                phi_hour=phi_hour,
                crisis=crisis,
            )

        return states

    def _update_coefficients(
        self,
        national_params: NationalTickParameters,
        prev_coefficients: SmoothedCoefficients | None,
    ) -> SmoothedCoefficients:
        """Step 3b: Update smoothed coefficients.

        Args:
            national_params: Current national parameters.
            prev_coefficients: Previous coefficients (None on first tick).

        Returns:
            Updated SmoothedCoefficients.
        """
        if prev_coefficients is None or not prev_coefficients.is_initialized:
            # First tick: use raw values, mark as initialized
            return SmoothedCoefficients(
                alpha=prev_coefficients.alpha if prev_coefficients else 0.3,
                gamma_basket=national_params.gamma_basket,
                gamma_III=national_params.gamma_III,
                gamma_import=0.35,  # MVP default
                is_initialized=True,
            )

        return SmoothedCoefficients(
            alpha=prev_coefficients.alpha,
            gamma_basket=national_params.gamma_basket,
            gamma_III=national_params.gamma_III,
            gamma_import=prev_coefficients.gamma_import,
            is_initialized=True,
        )

    def _compute_imperial_rent(
        self,
        county_states: dict[str, CountyEconomicState],
        national_params: NationalTickParameters,
        services: ServiceContainer,
    ) -> dict[str, CountyEconomicState]:
        """Step 4: Compute imperial rent flows.

        Args:
            county_states: Current county states.
            national_params: National parameters.
            services: ServiceContainer with imperial rent calculator.

        Returns:
            Updated county states with phi_hour.
        """
        if services.imperial_rent_calculator is None:
            return county_states

        # Build NationalParameters for the imperial rent calculator
        from babylon.economics.melt.parameters import NationalParameters

        nat_params = NationalParameters(
            year=min(max(national_params.year, 2010), 2030),
            tau=national_params.tau,
            alpha=0.25,  # MVP default
            gamma_import=0.35,  # MVP default
            gamma_basket=national_params.gamma_basket,
            tau_effective=national_params.tau_effective,
            v_reproduction=national_params.v_reproduction,
            estimated=national_params.estimated,
        )

        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            phi_hour = services.imperial_rent_calculator.compute_phi_hour(
                county.median_wage, nat_params
            )
            # Phi_hour can be negative (net exploited), but we store as ge=0
            phi_hour_clamped = max(phi_hour, 0.0)
            updated[fips] = county.model_copy(update={"phi_hour": phi_hour_clamped})
        return updated

    def _check_crisis_triggers(
        self,
        county_states: dict[str, CountyEconomicState],
    ) -> dict[str, CountyEconomicState]:
        """Step 5: Check crisis triggers.

        Default thresholds: unemployment > 0.08.

        Args:
            county_states: Current county states.

        Returns:
            Updated county states with crisis flags.
        """
        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            crisis = county.unemployment_rate > 0.08
            updated[fips] = county.model_copy(update={"crisis": crisis})
        return updated

    def _simulate_transitions(
        self,
        county_states: dict[str, CountyEconomicState],
        national_params: NationalTickParameters,
        services: ServiceContainer,
    ) -> dict[str, CountyEconomicState]:
        """Step 6: Simulate class transitions using Feature 016 engine.

        Args:
            county_states: Current county states.
            national_params: National parameters.
            services: ServiceContainer with transition engine.

        Returns:
            Updated county states with new class distributions.
        """
        if services.transition_engine is None:
            return county_states

        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            # Synthesize EconomicConditions
            clamped_year = min(max(county.year, 2007), 2030)
            conditions = EconomicConditions(
                fips=fips,
                year=clamped_year,
                unemployment_rate=county.unemployment_rate,
                median_wage=county.median_wage * 2080,  # hourly -> annual
                melt=national_params.tau,
                phi_hour=county.phi_hour,
                foreclosure_rate=DEFAULT_FORECLOSURE_RATE,
                bankruptcy_rate=DEFAULT_BANKRUPTCY_RATE,
                eviction_rate=DEFAULT_EVICTION_RATE,
                crisis=county.crisis,
            )

            # Clamp distribution year for transition engine
            dist = county.class_distribution
            if dist.year != clamped_year:
                dist = ClassDistribution(
                    fips=dist.fips,
                    year=clamped_year,
                    bourgeoisie_share=dist.bourgeoisie_share,
                    petit_bourgeoisie_share=dist.petit_bourgeoisie_share,
                    labor_aristocracy_share=dist.labor_aristocracy_share,
                    proletariat_share=dist.proletariat_share,
                    lumpenproletariat_share=dist.lumpenproletariat_share,
                )

            result = services.transition_engine.simulate_transitions(dist, conditions)

            if result and isinstance(result, ClassDistribution):
                # Clamp the result year
                result_year = min(max(result.year, 2007), 2030)
                if result.year != result_year:
                    result = ClassDistribution(
                        fips=result.fips,
                        year=result_year,
                        bourgeoisie_share=result.bourgeoisie_share,
                        petit_bourgeoisie_share=result.petit_bourgeoisie_share,
                        labor_aristocracy_share=result.labor_aristocracy_share,
                        proletariat_share=result.proletariat_share,
                        lumpenproletariat_share=result.lumpenproletariat_share,
                    )
                updated[fips] = county.model_copy(update={"class_distribution": result})
            else:
                updated[fips] = county

        return updated

    def _validate_distributions(
        self,
        county_states: dict[str, CountyEconomicState],
    ) -> None:
        """Step 7: Validate class distribution sum-to-one invariant (FR-009).

        Args:
            county_states: County states to validate.

        Raises:
            ValueError: If any distribution violates the invariant.
        """
        for fips, county in county_states.items():
            dist = county.class_distribution
            total = (
                dist.bourgeoisie_share
                + dist.petit_bourgeoisie_share
                + dist.labor_aristocracy_share
                + dist.proletariat_share
                + dist.lumpenproletariat_share
            )
            if abs(total - 1.0) > 0.001:
                msg = (
                    f"Step 7 validation failed for FIPS {fips}: "
                    f"class shares sum to {total:.6f}, expected 1.0"
                )
                raise ValueError(msg)


__all__ = ["TickDynamicsSystem"]
