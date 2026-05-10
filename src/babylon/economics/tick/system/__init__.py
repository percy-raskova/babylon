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
from typing import TYPE_CHECKING, ClassVar

import networkx as nx

from babylon.economics.circulation.circuit import initialize_circuit_state
from babylon.economics.circulation.crisis import assess_circulation_crisis
from babylon.economics.circulation.defaults import FALLBACK_PROFILE
from babylon.economics.circulation.types import (
    CirculationCrisisState,
    DepreciationFundState,
    InventoryState,
    ReproductionAnalysis,
    ReproductionBalance,
)
from babylon.economics.credit.types import FictitiousCapitalStock
from babylon.economics.crisis.bifurcation import BifurcationRiskCalculator
from babylon.economics.crisis.wage_compression import should_halt_accumulation
from babylon.economics.dynamics.types import ClassDistribution, EconomicConditions
from babylon.economics.reserve_army.calculator import DefaultWagePressureCalculator
from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tick.crisis_detector import (
    MultiPeriodCrisisDetector,
    ThresholdCrisisDetector,
)
from babylon.economics.tick.derived_rates import DerivedRateCalculator
from babylon.economics.tick.graph_bridge import (
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.economics.tick.precarity import PrecarityDeriver
from babylon.economics.tick.smoothing import CoefficientSmoother
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
    TickSummary,
)
from babylon.engine.systems.base import SystemBase

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
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


class TickDynamicsSystem(SystemBase):
    """Engine System for per-tick economic state evolution.

    Conforms to the System protocol (name + step). Executes the 8-step
    pipeline on year boundaries, writing results to the shared graph.

    Example:
        >>> system = TickDynamicsSystem()
        >>> system.step(graph, services, context)
    """

    name: ClassVar[str] = "tick_dynamics"

    def __init__(self) -> None:
        self._legacy_crisis_detector = ThresholdCrisisDetector()
        self._crisis_detector: MultiPeriodCrisisDetector | None = None
        self._bifurcation_calculator: BifurcationRiskCalculator | None = None
        self._precarity_deriver = PrecarityDeriver()
        self._smoother = CoefficientSmoother(alpha=0.3)
        self._rate_calculator = DerivedRateCalculator()

    def step(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Execute tick dynamics pipeline on year boundaries.

        Args:
            graph: Mutable NetworkX graph or GraphProtocol (modified in-place).
            services: ServiceContainer with calculator services.
            context: TickContext or dict with tick number.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

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
            year = self._determine_year(tick, graph)
            prev_coefficients = None
            prev_county_states = self._bootstrap_county_states(graph, year)

        # Step 2: Compute national parameters
        national_params = self._compute_national_params(year, services, prev_coefficients)
        if national_params is None:
            return

        # Step 3a: Compute county-level state
        # Try: previous state keys > graph territory nodes > tensor_registry FIPS
        if prev_county_states:
            county_fips = list(prev_county_states.keys())
        else:
            county_fips = self._get_territory_fips(graph)
            # Feature 020: Fall back to tensor_registry when graph has no territories
            if not county_fips:
                tensor_registry = getattr(services, "tensor_registry", None)
                if tensor_registry is not None:
                    county_fips = list(tensor_registry.all_fips())
        county_states = self._compute_county_states(year, county_fips, services, prev_county_states)

        # Step 3a+: Derive precarity indicators from class distribution
        county_states = self._derive_precarity(county_states)

        # Step 3b: Update smoothed coefficients
        coefficients = self._update_coefficients(national_params, prev_coefficients)

        # Step 3.5: Compute Vol I production layer — wage pressure (Feature 021)
        county_states = self._compute_vol1_layer(county_states, services, year)

        # Step 4: Compute imperial rent flows
        county_states = self._compute_imperial_rent(county_states, national_params, services)

        # Step 4.5: Compute circulation layer (Feature 023)
        county_states = self._compute_circulation_layer(county_states, services, year)

        # Step 5: Check crisis triggers (batch-within-step quarterly evaluation)
        county_states = self._check_crisis_triggers(county_states, services, tick)

        # Step 5.5: Compute financial layer (Feature 024)
        county_states = self._compute_financial_layer(
            county_states,
            national_params,
            services,
            year,
        )

        # Step 6: Simulate class transitions (with cascade tracking)
        county_states = self._simulate_transitions(
            county_states,
            national_params,
            services,
            prev_county_states,
            tick,
        )

        # Step 5b: Compute bifurcation risk (FR-011, uses prev + curr distributions)
        county_states = self._compute_bifurcation_risk(
            county_states,
            prev_county_states,
            graph,
            services,
            tick,
        )

        # Step 7: Validate class distribution invariant
        self._validate_distributions(county_states)

        # Step 8: Compute derived rates and assemble TickSummary
        tick_summary = self._compute_tick_summary(year, county_states, national_params)

        # Assemble final state
        new_state = SimulationTickState(
            year=year,
            national_params=national_params,
            county_states=county_states,
            coefficients=coefficients,
            tick_summary=tick_summary,
        )

        # Write to graph
        write_tick_state_to_graph(graph, new_state)

        # Step 9: Write hex substrate state to graph (Feature 026)
        # Aggregates R7 economic substrate → R6 territory nodes
        self._write_hex_substrate(graph, services)

    def _write_hex_substrate(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
    ) -> None:
        """Step 9: Write hex substrate economic state to graph territory nodes.

        Aggregates R7 hex economic data to R6 resolution and writes
        ``hex_``-prefixed attributes to territory nodes. This enables
        organizational dynamics and player verbs to consume spatialized
        economic metrics.

        No-op if ``services.hex_grid`` is None.

        Args:
            graph: Mutable GraphProtocol (already wrapped).
            services: ServiceContainer with optional hex_grid.
        """
        hex_grid = getattr(services, "hex_grid", None)
        if hex_grid is None:
            return

        from babylon.economics.substrate.hex_graph_bridge import (
            aggregate_r7_to_r6,
            write_hex_state_to_graph,
        )
        from babylon.economics.substrate.types import HexGrid

        if not isinstance(hex_grid, HexGrid):
            logger.warning("TickDynamicsSystem: hex_grid is not a HexGrid instance, skipping")
            return

        r6_states = aggregate_r7_to_r6(hex_grid)
        write_hex_state_to_graph(graph, r6_states)

    def _determine_year(
        self, tick: int, graph: nx.DiGraph[str] | GraphProtocol | None = None
    ) -> int:
        """Determine simulation year from tick number and graph metadata.

        Args:
            tick: Current tick number.
            graph: Optional graph to read base_year from metadata.

        Returns:
            Estimated year (base_year + tick // WEEKS_PER_YEAR).
            Default base_year is 2010 if not set in graph metadata.
        """
        base_year = 2010
        if graph is not None:
            from babylon.engine.graph_protocol import GraphProtocol

            if not isinstance(graph, GraphProtocol):
                from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

                graph = NetworkXAdapter.wrap(graph)
            base_year = graph.get_graph_attr("base_year", 2010)
        return base_year + tick // WEEKS_PER_YEAR

    def _get_territory_fips(self, graph: nx.DiGraph[str] | GraphProtocol) -> list[str]:
        """Extract FIPS codes from territory nodes in graph.

        Args:
            graph: NetworkX graph or GraphProtocol.

        Returns:
            List of FIPS codes for territory nodes.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        fips_list: list[str] = []
        for node in graph.query_nodes():
            if node.node_type == "territory":
                fips_list.append(str(node.id))
        return fips_list

    def _bootstrap_county_states(
        self,
        graph: nx.DiGraph[str] | GraphProtocol,
        year: int,
    ) -> dict[str, CountyEconomicState]:
        """Bootstrap county states from graph territory nodes.

        Args:
            graph: NetworkX graph or GraphProtocol with territory nodes.
            year: Current year.

        Returns:
            Dict of FIPS -> CountyEconomicState with defaults.
        """
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

        states: dict[str, CountyEconomicState] = {}
        for node in graph.query_nodes():
            if node.node_type != "territory":
                continue
            fips = str(node.id)
            data = node.attributes

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

        # Apply smoothing via CoefficientSmoother
        is_init = prev_coefficients is not None and prev_coefficients.is_initialized
        gamma_basket = self._smoother.smooth(
            raw=gamma_basket_raw,
            previous=prev_coefficients.gamma_basket if prev_coefficients else gamma_basket_raw,
            is_initialized=is_init,
        )
        gamma_III = self._smoother.smooth(
            raw=gamma_III_raw,
            previous=prev_coefficients.gamma_III if prev_coefficients else gamma_III_raw,
            is_initialized=is_init,
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
            crisis_state = prev.crisis_state if prev else CrisisState.normal()

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
                crisis_state=crisis_state,
            )

        return states

    def _derive_precarity(
        self,
        county_states: dict[str, CountyEconomicState],
    ) -> dict[str, CountyEconomicState]:
        """Derive precarity indicators (U-6, PTER, NILF) from class shares.

        Uses lumpenproletariat share as the precaritization rate.

        Args:
            county_states: Current county states.

        Returns:
            Updated county states with derived precarity indicators.
        """
        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            precaritization_rate = county.class_distribution.lumpenproletariat_share
            u6, pter, nilf = self._precarity_deriver.derive(
                unemployment_rate=county.unemployment_rate,
                precaritization_rate=precaritization_rate,
            )
            updated[fips] = county.model_copy(
                update={"u6_rate": u6, "pter_rate": pter, "nilf_rate": nilf}
            )
        return updated

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

        Per Spec 057 / FR-001: thin delegation to the
        :func:`babylon.economics.tick.system.imperial_rent.compute` orchestration
        module (≤400 LOC, completing Spec 058's deferred US2 decomposition).
        Behavioral fence preserved per Spec 058 / FR-007 (return-type class,
        exception class hierarchy, event-bus emission ordering).

        Args:
            county_states: Current county states.
            national_params: National parameters (provides tick year).
            services: ServiceContainer with the 4 Spec 057 fields wired
                (graceful degradation to stub behavior if not).

        Returns:
            Updated county states with phi_hour set from the Leontief pipeline,
            or unchanged county states if the pipeline isn't wired (graceful
            degradation per data-model.md).
        """
        from babylon.economics.tick.system.imperial_rent import compute

        return compute(county_states, national_params, services)

    def _check_crisis_triggers(
        self,
        county_states: dict[str, CountyEconomicState],
        services: ServiceContainer,
        tick: int,
    ) -> dict[str, CountyEconomicState]:
        """Step 5: Check crisis triggers using MultiPeriodCrisisDetector.

        Batch-within-step quarterly evaluation (FR-019): the annual pipeline
        evaluates 4 quarterly crisis periods per run. For each county, the
        detector is invoked 4 times with the current profit rate.

        Args:
            county_states: Current county states.
            services: ServiceContainer with event_bus, defines, tensor_registry.
            tick: Current tick number.

        Returns:
            Updated county states with crisis state.
        """
        # Lazily initialize detector from GameDefines
        if self._crisis_detector is None:
            crisis_cfg = services.defines.crisis
            self._crisis_detector = MultiPeriodCrisisDetector(
                r_threshold=crisis_cfg.r_threshold,
                n_consecutive=crisis_cfg.n_consecutive,
                m_recovery=crisis_cfg.m_recovery,
                r_cap=crisis_cfg.r_cap,
            )

        # Number of quarterly evaluations per annual pipeline run
        quarterly_evals = 4

        wage_compression_rate = services.defines.crisis.wage_compression_rate

        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            profit_rate = self._get_profit_rate(fips, county.year, services)
            crisis_state = county.crisis_state
            median_wage = county.median_wage

            for _ in range(quarterly_evals):
                prev_phase = crisis_state.phase
                crisis_state = self._crisis_detector.evaluate(profit_rate, crisis_state)
                new_phase = crisis_state.phase

                # FR-016: Apply wage compression per DEEP quarter
                if new_phase == CrisisPhase.DEEP:
                    median_wage = median_wage * (1.0 - wage_compression_rate)
                    prev_cumulative = crisis_state.cumulative_wage_compression
                    new_cumulative = min(
                        1.0 - (1.0 - prev_cumulative) * (1.0 - wage_compression_rate),
                        1.0,
                    )
                    crisis_state = crisis_state.model_copy(
                        update={"cumulative_wage_compression": new_cumulative}
                    )

                # Emit events on phase transitions (FR-004, FR-022)
                if new_phase != prev_phase:
                    self._emit_crisis_event(
                        services,
                        tick,
                        fips,
                        prev_phase,
                        new_phase,
                        profit_rate,
                        crisis_state.crisis_duration,
                    )

            updated[fips] = county.model_copy(
                update={
                    "crisis_state": crisis_state,
                    "median_wage": median_wage,
                }
            )
        return updated

    def _get_profit_rate(
        self,
        fips: str,
        year: int,
        services: ServiceContainer,
    ) -> float | None:
        """Retrieve profit rate for a county from TensorRegistry.

        Uses carry-forward logic: if data is unavailable for the requested
        year, falls back to the most recent available year (T014).

        Args:
            fips: County FIPS code.
            year: Target year for lookup.
            services: ServiceContainer with optional tensor_registry.

        Returns:
            Profit rate or None if unavailable.
        """
        tensor_registry = getattr(services, "tensor_registry", None)
        if tensor_registry is None:
            return None

        tensor = tensor_registry.get(fips, year)
        # Carry-forward: if current year unavailable, use most recent (T014)
        if isinstance(tensor, NoDataSentinel) and hasattr(tensor_registry, "available_years"):
            available = tensor_registry.available_years(fips)
            candidates = [y for y in available if y <= year]
            if candidates:
                carry_year = max(candidates)
                logger.info(
                    "FIPS %s: using %d tensor data for year %d",
                    fips,
                    carry_year,
                    year,
                )
                tensor = tensor_registry.get(fips, carry_year)

        if isinstance(tensor, NoDataSentinel):
            return None
        return getattr(tensor, "profit_rate", None)

    @staticmethod
    def _emit_crisis_event(
        services: ServiceContainer,
        tick: int,
        fips: str,
        prev_phase: CrisisPhase,
        new_phase: CrisisPhase,
        profit_rate: float | None,
        crisis_duration: int,
    ) -> None:
        """Emit crisis phase-change events (FR-004, FR-022).

        Args:
            services: ServiceContainer with event_bus.
            tick: Current simulation tick.
            fips: County FIPS code.
            prev_phase: Previous crisis phase.
            new_phase: New crisis phase.
            profit_rate: Current profit rate.
            crisis_duration: Current crisis duration.
        """
        # Lazy imports to avoid circular dependency (engine -> economics -> engine)
        from babylon.engine.event_bus import Event
        from babylon.models.enums import EventType

        # CRISIS_PHASE_TRANSITION on every phase change
        services.event_bus.publish(
            Event(
                type=EventType.CRISIS_PHASE_TRANSITION.value,
                tick=tick,
                payload={
                    "fips": fips,
                    "previous_phase": prev_phase.value,
                    "new_phase": new_phase.value,
                    "profit_rate": profit_rate,
                    "crisis_duration": crisis_duration,
                },
            )
        )

        # ECONOMIC_CRISIS at crisis onset (NORMAL -> ONSET)
        if prev_phase == CrisisPhase.NORMAL and new_phase == CrisisPhase.ONSET:
            services.event_bus.publish(
                Event(
                    type=EventType.ECONOMIC_CRISIS.value,
                    tick=tick,
                    payload={
                        "fips": fips,
                        "phase": new_phase.value,
                        "profit_rate": profit_rate,
                    },
                )
            )

    @staticmethod
    def _check_dispossession_cascade(
        fips: str,
        new_dist: ClassDistribution,
        prev_county_states: dict[str, CountyEconomicState],
        services: ServiceContainer,
        tick: int,
    ) -> None:
        """Emit DISPOSSESSION_CASCADE at LA share decline milestones (FR-022).

        Compares current LA share to the previous tick's LA share (baseline)
        and emits an event for the highest milestone crossed by the decline.
        Default milestones: 5, 10, 15 percentage points.

        Args:
            fips: County FIPS code.
            new_dist: New class distribution after transitions.
            prev_county_states: Previous tick's county states (baseline).
            services: ServiceContainer with event_bus and defines.
            tick: Current simulation tick.
        """
        prev_county = prev_county_states.get(fips)
        if prev_county is None:
            return

        baseline_la = prev_county.class_distribution.labor_aristocracy_share
        current_la = new_dist.labor_aristocracy_share
        decline = baseline_la - current_la

        if decline <= 0:
            return

        milestones: list[float] = services.defines.crisis.dispossession_cascade_milestones
        crossed: float | None = None
        for milestone in sorted(milestones):
            if decline >= milestone:
                crossed = milestone

        if crossed is not None:
            # Lazy imports to avoid circular dependency
            from babylon.engine.event_bus import Event
            from babylon.models.enums import EventType

            services.event_bus.publish(
                Event(
                    type=EventType.DISPOSSESSION_CASCADE.value,
                    tick=tick,
                    payload={
                        "fips": fips,
                        "cumulative_la_decline": round(decline, 6),
                        "milestone_crossed": crossed,
                        "current_la_share": round(current_la, 6),
                        "baseline_la_share": round(baseline_la, 6),
                    },
                )
            )

    def _compute_vol1_layer(
        self,
        county_states: dict[str, CountyEconomicState],
        services: ServiceContainer,
        year: int,
    ) -> dict[str, CountyEconomicState]:
        """Compute Volume I production layer — reserve army wage pressure.

        Feature: 021-capital-volume-i
        Derives reserve army state from FRED UNRATE + NROU, computes sigmoid
        wage pressure, and applies it to county median_wage. Runs before
        imperial rent (Step 4) so adjusted wages propagate through phi_hour.

        Args:
            county_states: Current county snapshots.
            services: ServiceContainer with reserve_army_data_source.
            year: Current simulation year.

        Returns:
            Updated county states with median_wage adjusted for wage pressure.
        """
        if services.reserve_army_data_source is None:
            return county_states

        wage_calc = DefaultWagePressureCalculator(getattr(services.defines, "reserve_army", None))

        updated: dict[str, CountyEconomicState] = {}
        max_counties = 3300
        for idx, (fips, county) in enumerate(county_states.items()):
            if idx >= max_counties:
                logger.warning("County count exceeds %d, truncating Vol I layer", max_counties)
                break
            updated[fips] = self._compute_vol1_county_state(fips, county, services, year, wage_calc)

        for fips, county in county_states.items():
            if fips not in updated:
                updated[fips] = county

        return updated

    def _compute_vol1_county_state(
        self,
        fips: str,
        county: CountyEconomicState,
        services: ServiceContainer,
        year: int,
        wage_calc: DefaultWagePressureCalculator,
    ) -> CountyEconomicState:
        """Apply Vol I wage pressure to a single county.

        Args:
            fips: 5-digit county FIPS code.
            county: Current county economic state.
            services: ServiceContainer with reserve_army_data_source.
            year: Current simulation year.
            wage_calc: Pre-built wage pressure calculator.

        Returns:
            Updated CountyEconomicState with adjusted median_wage.
        """
        state = services.reserve_army_data_source.get_unemployment_decomposition(fips, year)
        if state is None:
            return county

        pressure = wage_calc.compute_wage_pressure(state.reserve_ratio)
        adjusted_wage = county.median_wage * (1.0 - pressure)
        return county.model_copy(update={"median_wage": adjusted_wage})

    def _compute_circulation_layer(
        self,
        county_states: dict[str, CountyEconomicState],
        services: ServiceContainer,
        year: int,
    ) -> dict[str, CountyEconomicState]:
        """Compute Volume II circulation state per county.

        Feature: 023-capital-volume-ii
        Computes national circulation parameters once from FRED data, then
        applies per-county circuit/inventory/depreciation state and crisis assessment.

        Args:
            county_states: Current county snapshots.
            services: ServiceContainer with circulation data sources.
            year: Current simulation year.

        Returns:
            Updated county states with circulation_state populated.
        """
        if services.turnover_profile_source is None:
            return county_states

        national = self._compute_national_circulation_state(services, year)
        days_raw, days_finished, national_inventory, annual_depr, gross_inv = national

        updated: dict[str, CountyEconomicState] = {}
        max_counties = 3300
        for idx, (fips, county) in enumerate(county_states.items()):
            if idx >= max_counties:
                logger.warning(
                    "County count exceeds %d, truncating circulation layer", max_counties
                )
                break
            updated[fips] = self._compute_county_circulation_state(
                fips,
                county,
                services,
                year,
                days_raw,
                days_finished,
                national_inventory,
                annual_depr,
                gross_inv,
            )

        for fips, county in county_states.items():
            if fips not in updated:
                updated[fips] = county

        return updated

    def _compute_national_circulation_state(
        self,
        services: ServiceContainer,
        year: int,
    ) -> tuple[float | None, float | None, float | None, float | None, float | None]:
        """Extract national circulation parameters from data sources.

        Returns:
            Tuple of (days_raw, days_finished, national_inventory,
            annual_depreciation, gross_investment). Each may be None if
            data unavailable.
        """
        inv_src = services.inventory_data_source
        depr_src = services.depreciation_data_source

        days_raw: float | None = None
        days_finished: float | None = None
        national_inventory: float | None = None
        annual_depr: float | None = None
        gross_inv: float | None = None

        if inv_src is not None:
            days_raw = getattr(inv_src, "get_days_inventory_raw", lambda _: None)(year)
            days_finished = getattr(inv_src, "get_days_inventory_finished", lambda _: None)(year)
            national_inventory = getattr(inv_src, "get_national_inventory", lambda _: None)(year)

        if depr_src is not None:
            annual_depr = getattr(depr_src, "get_annual_depreciation", lambda _: None)(year)
            gross_inv = getattr(depr_src, "get_gross_investment", lambda _: None)(year)

        return days_raw, days_finished, national_inventory, annual_depr, gross_inv

    def _compute_county_circulation_state(
        self,
        fips: str,
        county: CountyEconomicState,
        services: ServiceContainer,
        year: int,
        days_raw: float | None,
        days_finished: float | None,
        national_inventory: float | None,
        annual_depr_national: float | None,
        gross_inv_national: float | None,
    ) -> CountyEconomicState:
        """Compute circulation state for a single county.

        Args:
            fips: 5-digit county FIPS code.
            county: Current county economic state.
            services: ServiceContainer with circulation sources.
            year: Current simulation year.
            days_raw: National raw-materials days-of-inventory (or None).
            days_finished: National finished-goods days-of-inventory (or None).
            national_inventory: National manufacturer inventory in dollars (or None).
            annual_depr_national: National annual depreciation in dollars (or None).
            gross_inv_national: National gross private investment in dollars (or None).

        Returns:
            Updated CountyEconomicState with circulation_state populated.
        """
        capital_stock = county.capital_stock
        if capital_stock <= 0:
            return county

        # Resolve turnover profile via NAICS (fallback to generic)
        profile = FALLBACK_PROFILE
        if services.turnover_profile_source is not None:
            resolved = services.turnover_profile_source.get_turnover_profile(fips[:2])
            if resolved is not None:
                profile = resolved

        # National employment share for county scaling
        national_employment = 155_000_000.0
        county_share = county.employment / national_employment if county.employment > 0 else 0.0

        # Build CircuitState from capital_stock + turnover profile
        from babylon.models.types import Currency

        circuit = initialize_circuit_state(
            fips_code=fips,
            year=year,
            total_capital=Currency(capital_stock),
            turnover=profile,
        )

        # Build InventoryState: scale national inventory to county
        county_inventory = (national_inventory * county_share) if national_inventory else 0.0
        county_raw = county_inventory * profile.fixed_capital_ratio
        county_finished = county_inventory * (1.0 - profile.fixed_capital_ratio)
        inventory = InventoryState(
            fips_code=fips,
            year=year,
            raw_materials=county_raw,
            work_in_progress=0.0,
            finished_goods=county_finished,
            days_inventory_raw=days_raw if days_raw is not None else 30.0,
            days_inventory_finished=days_finished if days_finished is not None else 30.0,
        )

        # Build DepreciationFundState: scale national depreciation to county
        county_depr = (annual_depr_national * county_share) if annual_depr_national else 0.0
        county_repl = (gross_inv_national * county_share) if gross_inv_national else 0.0
        # Ensure annual_depreciation_flow > 0 (required by model)
        safe_depr = max(county_depr, 1.0)
        depreciation = DepreciationFundState(
            fips_code=fips,
            year=year,
            total_fixed_capital=circuit.fixed_capital,
            accumulated_depreciation=safe_depr,
            annual_depreciation_flow=safe_depr,
            replacement_expenditure=county_repl,
        )

        # Reproduction defaults: assume balanced reproduction
        repro_balance = ReproductionBalance(
            condition_met=True,
            gap=0.0,
            interpretation="Default reproduction balance",
        )
        repro_analysis = ReproductionAnalysis(
            labor_power_demand=county.employment,
            reproduction_capacity=county.employment,
            gap=0.0,
            sustainability=True,
        )

        assessment = assess_circulation_crisis(
            circuit_state=circuit,
            turnover=profile,
            inventory=inventory,
            reproduction_balance=repro_balance,
            reproduction_analysis=repro_analysis,
        )

        new_circ_state = CirculationCrisisState(
            circuit_state=circuit,
            inventory_state=inventory,
            depreciation_fund=depreciation,
            latest_assessment=assessment,
        )

        return county.model_copy(update={"circulation_state": new_circ_state})

    def _compute_financial_layer(
        self,
        county_states: dict[str, CountyEconomicState],
        _national_params: NationalTickParameters,
        services: ServiceContainer,
        year: int,
    ) -> dict[str, CountyEconomicState]:
        """Compute Volume III financial distribution layer.

        Feature: 024-capital-volume-iii
        Computes national financial parameters once, then distributes
        surplus value and assesses financial crisis per county.

        Args:
            county_states: Current county snapshots.
            _national_params: National economic context (reserved for future use).
            services: ServiceContainer with financial calculators.
            year: Current simulation year.

        Returns:
            Updated county states with financial fields populated.
        """
        # Graceful skip if financial calculators not configured
        if services.interest_calculator is None:
            return county_states

        national_rate, fictitious = self._compute_national_financial_state(services, year)

        # County-level computation
        updated: dict[str, CountyEconomicState] = {}
        max_counties = 3300
        for idx, (fips, county) in enumerate(county_states.items()):
            if idx >= max_counties:
                logger.warning("County count exceeds %d, truncating financial layer", max_counties)
                break
            updated[fips] = self._compute_county_financial_state(
                fips,
                county,
                services,
                year,
                national_rate,
                fictitious,
            )

        # Preserve any remaining counties not processed (if truncated)
        for fips, county in county_states.items():
            if fips not in updated:
                updated[fips] = county

        return updated

    def _compute_national_financial_state(
        self,
        services: ServiceContainer,
        year: int,
    ) -> tuple[float, FictitiousCapitalStock | None]:
        """Compute national-level financial parameters once per tick.

        Returns:
            Tuple of (national_interest_rate, fictitious_capital_or_none).
        """
        interest_state = services.interest_calculator.compute_interest_rate_state(year)
        if isinstance(interest_state, NoDataSentinel):
            interest_state = None
        national_rate = interest_state.effective_rate if interest_state is not None else 0.0

        fictitious = None
        if services.fictitious_capital_calculator is not None:
            fict_result = services.fictitious_capital_calculator.compute_fictitious_capital(year)
            if not isinstance(fict_result, NoDataSentinel):
                fictitious = fict_result

        return national_rate, fictitious

    def _compute_county_financial_state(
        self,
        fips: str,
        county: CountyEconomicState,
        services: ServiceContainer,
        year: int,
        national_rate: float,
        fictitious: FictitiousCapitalStock | None,
    ) -> CountyEconomicState:
        """Compute financial fields for a single county.

        Args:
            fips: County FIPS code.
            county: Current county state.
            services: ServiceContainer with financial calculators.
            year: Current simulation year.
            national_rate: National effective interest rate.
            fictitious: FictitiousCapitalStock or None.

        Returns:
            Updated CountyEconomicState with financial fields.
        """
        updates: dict[str, object] = {}
        total_surplus: float | None = None

        # Use nearest available tensor year to handle year+1 advancement
        tensor_year = self._get_best_tensor_year(fips, year, services)

        # Surplus distribution (s = p + i + r + t)
        if services.distribution_calculator is not None:
            profit_rate = self._get_county_profit_rate(fips, tensor_year, services)
            total_surplus = self._get_county_surplus(fips, tensor_year, services)
            if total_surplus is not None and total_surplus > 0:
                dist = services.distribution_calculator.compute_distribution(
                    fips=fips,
                    year=year,
                    total_surplus=total_surplus,
                    county_profit_rate=profit_rate if profit_rate is not None else 0.05,
                    national_interest_rate=national_rate,
                    county_employment=county.employment,
                )
                if not isinstance(dist, NoDataSentinel):
                    updates["surplus_distribution"] = dist
                    if county.debt_accumulation is not None:
                        from babylon.economics.distribution.types import DebtAccumulation

                        updates["debt_accumulation"] = DebtAccumulation.update(
                            county.debt_accumulation,
                            dist.profit_of_enterprise,
                            year,
                        )

        # Rent extraction
        if services.rent_calculator is not None:
            rent_result = services.rent_calculator.compute_rent_extraction(fips, year)
            if not isinstance(rent_result, NoDataSentinel):
                updates["rent_extraction"] = rent_result

        # Housing decomposition
        if services.housing_calculator is not None:
            housing_result = services.housing_calculator.decompose_housing_value(fips, year)
            if not isinstance(housing_result, NoDataSentinel):
                updates["housing_decomposition"] = housing_result

        # Financial crisis assessment
        if services.financial_crisis_assessor is not None and "surplus_distribution" in updates:
            assessment = self._assess_county_financial_crisis(
                fips,
                year,
                updates,
                services,
                national_rate,
                fictitious,
                total_surplus,
            )
            if assessment is not None:
                updates["financial_crisis"] = assessment

        if updates:
            return county.model_copy(update=updates)
        return county

    def _assess_county_financial_crisis(
        self,
        fips: str,
        year: int,
        updates: dict[str, object],
        services: ServiceContainer,
        national_rate: float,
        fictitious: FictitiousCapitalStock | None,
        total_surplus: float | None,
    ) -> object | None:
        """Assess financial crisis for a single county."""
        surplus_dist = updates["surplus_distribution"]
        fin_share = getattr(surplus_dist, "financialization_share", 0.0)
        claims_exceed = getattr(surplus_dist, "claims_exceed_surplus", False)
        fin_ratio = 0.0
        max_counties = 3300
        if fictitious is not None and total_surplus is not None and total_surplus > 0:
            fin_ratio = fictitious.ratio_to_real(total_surplus * max_counties)

        result: object | None = services.financial_crisis_assessor.assess(
            fips=fips,
            year=year,
            interest_burden_ratio=float(fin_share),
            financialization_ratio=fin_ratio,
            default_rate=0.02,  # Placeholder
            credit_spread=national_rate,
            claims_exceed_surplus=bool(claims_exceed),
        )
        return result

    def _get_best_tensor_year(
        self,
        fips: str,
        year: int,
        services: ServiceContainer,
    ) -> int:
        """Return nearest tensor-populated year for a county.

        The simulation advances year by +1 each tick, but tensors are
        hydrated only for the initial years. This method falls back to
        the most recently available tensor year (up to 2 years back)
        so the financial layer always draws real data, not None.

        Args:
            fips: 5-digit county FIPS code.
            year: Requested simulation year.
            services: ServiceContainer with tensor_registry.

        Returns:
            Best available year: current, current-1, or current-2.
        """
        tensor_registry = getattr(services, "tensor_registry", None)
        if tensor_registry is None:
            return year
        for candidate in [year, year - 1, year - 2]:
            tensor = tensor_registry.get(fips, candidate)
            if not isinstance(tensor, NoDataSentinel):
                return candidate
        return year

    def _get_county_profit_rate(
        self,
        fips: str,
        year: int,
        services: ServiceContainer,
    ) -> float | None:
        """Get county profit rate from tensor registry.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.
            services: ServiceContainer with tensor_registry.

        Returns:
            Profit rate if available, None otherwise.
        """
        tensor_registry = getattr(services, "tensor_registry", None)
        if tensor_registry is None:
            return None
        tensor = tensor_registry.get(fips, year)
        if isinstance(tensor, NoDataSentinel):
            return None
        profit_rate = getattr(tensor, "profit_rate", None)
        if profit_rate is not None:
            return float(profit_rate)
        return None

    def _get_county_surplus(
        self,
        fips: str,
        year: int,
        services: ServiceContainer,
    ) -> float | None:
        """Get county total surplus from tensor registry.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.
            services: ServiceContainer with tensor_registry.

        Returns:
            Total surplus if available, None otherwise.
        """
        tensor_registry = getattr(services, "tensor_registry", None)
        if tensor_registry is None:
            return None
        tensor = tensor_registry.get(fips, year)
        if isinstance(tensor, NoDataSentinel):
            return None
        total_s = getattr(tensor, "total_s", None)
        if total_s is not None:
            return float(total_s)
        return None

    def _compute_bifurcation_risk(
        self,
        county_states: dict[str, CountyEconomicState],
        prev_county_states: dict[str, CountyEconomicState] | None,
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        tick: int,
    ) -> dict[str, CountyEconomicState]:
        """Step 5b: Compute bifurcation risk for each county (FR-011).

        Uses solidarity density from graph topology, legitimation from
        agitation levels, and class burden ratio from distribution deltas
        to assess political trajectory during active crisis.

        Args:
            county_states: Current county states (after transitions).
            prev_county_states: Previous county states (before transitions).
            graph: Simulation graph with social class nodes and edges.
            services: ServiceContainer with event_bus and defines.
            tick: Current simulation tick.

        Returns:
            Updated county states with bifurcation risk metrics.
        """
        if prev_county_states is None:
            return county_states

        # Lazily initialize calculator from GameDefines
        if self._bifurcation_calculator is None:
            crisis_cfg = services.defines.crisis
            self._bifurcation_calculator = BifurcationRiskCalculator(
                solidarity_weight=crisis_cfg.bifurcation_solidarity_weight,
                burden_weight=crisis_cfg.bifurcation_burden_weight,
                epsilon=crisis_cfg.class_burden_epsilon,
            )

        threshold = services.defines.crisis.bifurcation_event_threshold

        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            prev_county = prev_county_states.get(fips)
            if prev_county is None:
                updated[fips] = county
                continue

            metric = self._bifurcation_calculator.compute(
                graph,
                fips,
                county.crisis_state,
                prev_county.class_distribution,
                county.class_distribution,
            )

            # FR-022: Emit BIFURCATION_THRESHOLD when |score| exceeds threshold
            if abs(metric.score) >= threshold:
                self._emit_bifurcation_event(
                    services,
                    tick,
                    fips,
                    metric,
                    threshold,
                )

            updated[fips] = county.model_copy(update={"bifurcation_risk": metric})

        return updated

    @staticmethod
    def _emit_bifurcation_event(
        services: ServiceContainer,
        tick: int,
        fips: str,
        metric: BifurcationRiskMetric,
        threshold: float,
    ) -> None:
        """Emit BIFURCATION_THRESHOLD event (FR-022).

        Args:
            services: ServiceContainer with event_bus.
            tick: Current simulation tick.
            fips: County FIPS code.
            metric: Computed bifurcation risk metric.
            threshold: |score| threshold that was exceeded.
        """
        # Lazy imports to avoid circular dependency (engine -> economics -> engine)
        from babylon.engine.event_bus import Event
        from babylon.models.enums import EventType

        direction = "revolutionary" if metric.score < 0 else "fascist"
        services.event_bus.publish(
            Event(
                type=EventType.BIFURCATION_THRESHOLD.value,
                tick=tick,
                payload={
                    "fips": fips,
                    "score": round(metric.score, 6),
                    "direction": direction,
                    "solidarity_density": round(metric.solidarity_density, 6),
                    "legitimation": round(metric.legitimation, 6),
                    "class_burden_ratio": round(metric.class_burden_ratio, 6),
                    "threshold": threshold,
                },
            )
        )

    def _simulate_transitions(
        self,
        county_states: dict[str, CountyEconomicState],
        national_params: NationalTickParameters,
        services: ServiceContainer,
        prev_county_states: dict[str, CountyEconomicState] | None = None,
        tick: int = 0,
    ) -> dict[str, CountyEconomicState]:
        """Step 6: Simulate class transitions using Feature 016 engine.

        Args:
            county_states: Current county states.
            national_params: National parameters.
            services: ServiceContainer with transition engine.
            prev_county_states: Previous county states (for cascade tracking).
            tick: Current tick number (for event emission).

        Returns:
            Updated county states with new class distributions.
        """
        if services.transition_engine is None:
            return county_states

        floor_ratio = services.defines.crisis.wage_compression_floor_ratio

        updated: dict[str, CountyEconomicState] = {}
        for fips, county in county_states.items():
            # Synthesize EconomicConditions with phase-aware amplification
            clamped_year = min(max(county.year, 2007), 2030)
            crisis_phase = county.crisis_state.phase

            # FR-017: Halt accumulation when wages below subsistence floor
            effective_wage = county.median_wage * 2080  # hourly -> annual
            if should_halt_accumulation(county.median_wage, DEFAULT_V_REPRODUCTION, floor_ratio):
                effective_wage = 0.0  # Zero wage -> zero accumulation

            # Use real dispossession rates if available (Feature 021)
            foreclosure_rate = DEFAULT_FORECLOSURE_RATE
            bankruptcy_rate = DEFAULT_BANKRUPTCY_RATE
            eviction_rate = DEFAULT_EVICTION_RATE
            if services.dispossession_data_source is not None:
                disp = services.dispossession_data_source
                fc = disp.get_foreclosure_rate(fips, clamped_year)
                if fc is not None:
                    foreclosure_rate = fc
                bk = disp.get_bankruptcy_rate(fips, clamped_year)
                if bk is not None:
                    bankruptcy_rate = bk
                ev = disp.get_eviction_rate(fips, clamped_year)
                if ev is not None:
                    eviction_rate = ev

            conditions = EconomicConditions(
                fips=fips,
                year=clamped_year,
                unemployment_rate=county.unemployment_rate,
                median_wage=effective_wage,
                melt=national_params.tau,
                phi_hour=county.phi_hour,
                foreclosure_rate=foreclosure_rate,
                bankruptcy_rate=bankruptcy_rate,
                eviction_rate=eviction_rate,
                crisis=crisis_phase != CrisisPhase.NORMAL,
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

            result = services.transition_engine.simulate_transitions(
                dist,
                conditions,
                crisis_phase=crisis_phase,
            )

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

                # FR-022: Emit DISPOSSESSION_CASCADE at milestone thresholds
                if crisis_phase != CrisisPhase.NORMAL and prev_county_states:
                    self._check_dispossession_cascade(
                        fips,
                        result,
                        prev_county_states,
                        services,
                        tick,
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

    def _compute_tick_summary(
        self,
        year: int,
        county_states: dict[str, CountyEconomicState],
        national_params: NationalTickParameters,
    ) -> TickSummary:
        """Step 8: Compute derived rates and assemble TickSummary.

        Args:
            year: Current year.
            county_states: County states after transitions.
            national_params: National parameters.

        Returns:
            TickSummary with aggregate statistics.
        """
        # Compute per-county derived rates
        profit_rates: list[float] = []
        occ_values: list[float] = []
        exploitation_values: list[float] = []

        for county in county_states.values():
            rates = self._rate_calculator.compute_county_rates(county, national_params)
            if rates.profit_rate is not None:
                profit_rates.append(rates.profit_rate)
            if rates.organic_composition is not None:
                occ_values.append(rates.organic_composition)
            if rates.exploitation_rate is not None:
                exploitation_values.append(rates.exploitation_rate)

        # Aggregate phi
        phi_aggregate = self._rate_calculator.compute_phi_aggregate(county_states)

        # Weighted-average class distribution
        total_employment = sum(c.employment for c in county_states.values())
        national_dist: dict[str, float] = {
            "bourgeoisie": 0.0,
            "petit_bourgeoisie": 0.0,
            "labor_aristocracy": 0.0,
            "proletariat": 0.0,
            "lumpenproletariat": 0.0,
        }
        if total_employment > 0:
            for county in county_states.values():
                weight = county.employment / total_employment
                d = county.class_distribution
                national_dist["bourgeoisie"] += d.bourgeoisie_share * weight
                national_dist["petit_bourgeoisie"] += d.petit_bourgeoisie_share * weight
                national_dist["labor_aristocracy"] += d.labor_aristocracy_share * weight
                national_dist["proletariat"] += d.proletariat_share * weight
                national_dist["lumpenproletariat"] += d.lumpenproletariat_share * weight

        clamped_year = min(max(year, 2007), 2040)
        return TickSummary(
            year=clamped_year,
            counties_processed=len(county_states),
            phi_aggregate=phi_aggregate,
            national_melt=national_params.tau,
            mean_profit_rate=sum(profit_rates) / len(profit_rates) if profit_rates else 0.0,
            mean_occ=sum(occ_values) / len(occ_values) if occ_values else 0.0,
            mean_exploitation_rate=(
                sum(exploitation_values) / len(exploitation_values) if exploitation_values else 0.0
            ),
            national_class_distribution=national_dist,
        )


__all__ = ["TickDynamicsSystem"]
