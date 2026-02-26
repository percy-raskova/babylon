"""Graph bridge for TickDynamicsSystem <-> NetworkX graph integration.

Feature: 017-simulation-tick-dynamics

Maps between SimulationTickState and NetworkX graph attributes so that
downstream engine Systems can consume tick dynamics outputs.

Territory nodes carry county-level state as ``tick_``-prefixed attributes.
National-level state is stored in ``graph.graph["tick_dynamics"]``.

See Also:
    :mod:`babylon.economics.tick.types`: Data models
    :mod:`babylon.models.world_state`: WorldState graph serialization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import networkx as nx

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol

from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.derived_rates import DerivedRateCalculator
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    DerivedRates,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
    TickSummary,
)

# Graph metadata key
TICK_DYNAMICS_KEY: str = "tick_dynamics"


def write_tick_state_to_graph(  # pragma: no mutate — data serialization
    graph: nx.DiGraph[str] | GraphProtocol,
    state: SimulationTickState,
) -> None:
    """Write SimulationTickState to the shared NetworkX graph.

    Territory nodes with matching FIPS codes receive county-level
    attributes with ``tick_`` prefix. National-level parameters are
    stored in ``graph.graph["tick_dynamics"]``.

    Args:
        graph: Mutable NetworkX graph or GraphProtocol (modified in-place).
        state: Simulation tick state to write.
    """
    from babylon.engine.graph_protocol import GraphProtocol

    if not isinstance(graph, GraphProtocol):
        from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

        graph = NetworkXAdapter.wrap(graph)

    # Write national-level metadata (includes county_states for persistence
    # through the WorldState round-trip when territory nodes don't exist)
    graph.set_graph_attr(
        TICK_DYNAMICS_KEY,
        {  # pragma: no mutate
            "year": state.year,  # pragma: no mutate
            "national_params": state.national_params,  # pragma: no mutate
            "coefficients": state.coefficients,  # pragma: no mutate
            "tick_summary": state.tick_summary,  # pragma: no mutate
            "is_year_boundary": True,  # pragma: no mutate
            "county_states": state.county_states,  # pragma: no mutate
            "credit_cycle_phase": "expansion",  # pragma: no mutate  # Feature 024
        },
    )  # pragma: no mutate

    # Pre-compute per-county derived rates for graph persistence
    rate_calc = DerivedRateCalculator()  # pragma: no mutate
    county_rates: dict[str, DerivedRates] = {}  # pragma: no mutate
    for fips, county in state.county_states.items():  # pragma: no mutate
        county_rates[fips] = rate_calc.compute_county_rates(  # pragma: no mutate
            county,
            state.national_params,  # pragma: no mutate
        )  # pragma: no mutate

    # Write county-level state to Territory nodes
    for fips, county in state.county_states.items():  # pragma: no mutate
        node = graph.get_node(fips)  # pragma: no mutate
        if node is None:  # pragma: no mutate
            continue  # pragma: no mutate
        # Only write to territory nodes
        if node.node_type != "territory":  # pragma: no mutate
            continue  # pragma: no mutate

        rates = county_rates[fips]  # pragma: no mutate
        graph.update_node(  # pragma: no mutate
            fips,  # pragma: no mutate
            tick_capital_stock=county.capital_stock,  # pragma: no mutate
            tick_throughput_position=county.throughput_position,  # pragma: no mutate
            tick_supply_chain_depth=county.supply_chain_depth,  # pragma: no mutate
            tick_phi_hour=county.phi_hour,  # pragma: no mutate
            tick_crisis_phase=county.crisis_state.phase.value,  # pragma: no mutate
            tick_crisis_duration=county.crisis_state.crisis_duration,  # pragma: no mutate
            tick_bifurcation_score=county.bifurcation_risk.score,  # pragma: no mutate
            tick_wage_compression=county.crisis_state.cumulative_wage_compression,  # pragma: no mutate
            tick_class_distribution={  # pragma: no mutate
                "bourgeoisie": county.class_distribution.bourgeoisie_share,  # pragma: no mutate
                "petit_bourgeoisie": county.class_distribution.petit_bourgeoisie_share,  # pragma: no mutate
                "labor_aristocracy": county.class_distribution.labor_aristocracy_share,  # pragma: no mutate
                "proletariat": county.class_distribution.proletariat_share,  # pragma: no mutate
                "lumpenproletariat": county.class_distribution.lumpenproletariat_share,  # pragma: no mutate
            },  # pragma: no mutate
            tick_unemployment_rate=county.unemployment_rate,  # pragma: no mutate
            tick_median_wage=county.median_wage,  # pragma: no mutate
            # Derived rates (computed per-county)
            tick_profit_rate=rates.profit_rate,  # pragma: no mutate
            tick_occ=rates.organic_composition,  # pragma: no mutate
            tick_exploitation_rate=rates.exploitation_rate,  # pragma: no mutate
            # Circulation state (Feature 023)
            tick_liquidity_ratio=county.circulation_state.circuit_state.liquidity_ratio,  # pragma: no mutate
            tick_commodity_overhang=county.circulation_state.circuit_state.commodity_overhang,  # pragma: no mutate
            tick_replacement_cycle=(  # pragma: no mutate
                county.circulation_state.depreciation_fund.replacement_cycle_position.value  # pragma: no mutate
            ),  # pragma: no mutate
            tick_inventory_diagnosis=(  # pragma: no mutate
                county.circulation_state.inventory_state.inventory_problem.value  # pragma: no mutate
            ),  # pragma: no mutate
            tick_realization_crisis=(  # pragma: no mutate
                county.circulation_state.latest_assessment.realization_crisis  # pragma: no mutate
                if county.circulation_state.latest_assessment is not None  # pragma: no mutate
                else False  # pragma: no mutate
            ),  # pragma: no mutate
            tick_turnover_crisis=(  # pragma: no mutate
                county.circulation_state.latest_assessment.turnover_crisis  # pragma: no mutate
                if county.circulation_state.latest_assessment is not None  # pragma: no mutate
                else False  # pragma: no mutate
            ),  # pragma: no mutate
            tick_reproduction_crisis=(  # pragma: no mutate
                county.circulation_state.latest_assessment.reproduction_crisis  # pragma: no mutate
                if county.circulation_state.latest_assessment is not None  # pragma: no mutate
                else False  # pragma: no mutate
            ),  # pragma: no mutate
            # Financial distribution state (Feature 024)
            tick_interest_burden=(  # pragma: no mutate
                county.surplus_distribution.interest_payments  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_ground_rent=(  # pragma: no mutate
                county.rent_extraction.total_rent  # pragma: no mutate
                if county.rent_extraction is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_rentier_share=(  # pragma: no mutate
                county.surplus_distribution.rentier_share  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_profit_of_enterprise=(  # pragma: no mutate
                county.surplus_distribution.profit_of_enterprise  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_financialization_share=(  # pragma: no mutate
                county.surplus_distribution.financialization_share  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_accumulated_debt=(  # pragma: no mutate
                county.debt_accumulation.accumulated_debt  # pragma: no mutate
                if county.debt_accumulation is not None  # pragma: no mutate
                else 0.0  # pragma: no mutate
            ),  # pragma: no mutate
            tick_claims_exceed_surplus=(  # pragma: no mutate
                county.surplus_distribution.claims_exceed_surplus  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
                else False  # pragma: no mutate
            ),  # pragma: no mutate
            tick_housing_fictitious_fraction=(  # pragma: no mutate
                county.housing_decomposition.fictitious_fraction  # pragma: no mutate
                if county.housing_decomposition is not None  # pragma: no mutate
                else None  # pragma: no mutate
            ),  # pragma: no mutate
            tick_financial_crisis_signals=(  # pragma: no mutate
                county.financial_crisis.active_signals  # pragma: no mutate
                if county.financial_crisis is not None  # pragma: no mutate
                else 0  # pragma: no mutate
            ),  # pragma: no mutate
        )  # pragma: no mutate


def read_tick_state_from_graph(  # pragma: no mutate — data serialization
    graph: nx.DiGraph[str] | GraphProtocol,
) -> SimulationTickState | None:
    """Read SimulationTickState from the shared NetworkX graph.

    Reconstructs SimulationTickState from graph attributes written by
    ``write_tick_state_to_graph()``.

    Args:
        graph: NetworkX graph or GraphProtocol containing tick dynamics attributes.

    Returns:
        Reconstructed SimulationTickState, or None if no tick dynamics
        data is present in the graph.
    """
    from babylon.engine.graph_protocol import GraphProtocol

    if not isinstance(graph, GraphProtocol):
        from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

        graph = NetworkXAdapter.wrap(graph)

    tick_data: dict[str, Any] | None = graph.get_graph_attr(TICK_DYNAMICS_KEY)  # pragma: no mutate
    if tick_data is None:  # pragma: no mutate
        return None  # pragma: no mutate

    national_params: NationalTickParameters = tick_data["national_params"]  # pragma: no mutate
    coefficients: SmoothedCoefficients = tick_data["coefficients"]  # pragma: no mutate
    tick_summary: TickSummary | None = tick_data.get("tick_summary")  # pragma: no mutate
    year: int = tick_data["year"]  # pragma: no mutate

    # Reconstruct county states from territory nodes (preferred) or from
    # the tick_data dict (fallback for when graph has no territory nodes,
    # e.g. Feature 020 from_sqlite path)
    county_states: dict[str, CountyEconomicState] = {}  # pragma: no mutate
    for node in graph.query_nodes():  # pragma: no mutate
        if node.node_type != "territory":  # pragma: no mutate
            continue  # pragma: no mutate
        node_data = node.attributes  # pragma: no mutate
        if "tick_capital_stock" not in node_data:  # pragma: no mutate
            continue  # pragma: no mutate

        fips = str(node.id)  # pragma: no mutate
        dist_dict = node_data.get("tick_class_distribution", {})  # pragma: no mutate
        class_dist = ClassDistribution(  # pragma: no mutate
            fips=fips,  # pragma: no mutate
            year=year,  # pragma: no mutate
            bourgeoisie_share=dist_dict.get("bourgeoisie", 0.01),  # pragma: no mutate
            petit_bourgeoisie_share=dist_dict.get("petit_bourgeoisie", 0.09),  # pragma: no mutate
            labor_aristocracy_share=dist_dict.get("labor_aristocracy", 0.40),  # pragma: no mutate
            proletariat_share=dist_dict.get("proletariat", 0.35),  # pragma: no mutate
            lumpenproletariat_share=dist_dict.get("lumpenproletariat", 0.15),  # pragma: no mutate
        )  # pragma: no mutate

        county_states[fips] = CountyEconomicState(  # pragma: no mutate
            fips=fips,  # pragma: no mutate
            year=year,  # pragma: no mutate
            capital_stock=node_data["tick_capital_stock"],  # pragma: no mutate
            throughput_position=node_data["tick_throughput_position"],  # pragma: no mutate
            supply_chain_depth=node_data["tick_supply_chain_depth"],  # pragma: no mutate
            unemployment_rate=node_data.get("tick_unemployment_rate", 0.05),  # pragma: no mutate
            u6_rate=node_data.get("tick_u6_rate", 0.10),  # pragma: no mutate
            pter_rate=node_data.get("tick_pter_rate", 0.04),  # pragma: no mutate
            nilf_rate=node_data.get("tick_nilf_rate", 0.06),  # pragma: no mutate
            median_wage=node_data.get("tick_median_wage", 21.0),  # pragma: no mutate
            employment=node_data.get("tick_employment", 100000.0),  # pragma: no mutate
            class_distribution=class_dist,  # pragma: no mutate
            phi_hour=node_data.get("tick_phi_hour", 0.0),  # pragma: no mutate
            crisis_state=CrisisState(  # pragma: no mutate
                phase=CrisisPhase(
                    node_data.get("tick_crisis_phase", "normal")
                ),  # pragma: no mutate
                crisis_duration=node_data.get("tick_crisis_duration", 0),  # pragma: no mutate
                cumulative_wage_compression=node_data.get(
                    "tick_wage_compression", 0.0
                ),  # pragma: no mutate
            ),  # pragma: no mutate
            bifurcation_risk=BifurcationRiskMetric(  # pragma: no mutate
                score=node_data.get("tick_bifurcation_score", 0.0),  # pragma: no mutate
            ),  # pragma: no mutate
        )  # pragma: no mutate

    # Fallback: use county_states stored directly in tick_data dict
    if not county_states and "county_states" in tick_data:  # pragma: no mutate
        county_states = tick_data["county_states"]  # pragma: no mutate

    return SimulationTickState(  # pragma: no mutate
        year=year,  # pragma: no mutate
        national_params=national_params,  # pragma: no mutate
        county_states=county_states,  # pragma: no mutate
        coefficients=coefficients,  # pragma: no mutate
        tick_summary=tick_summary,  # pragma: no mutate
    )  # pragma: no mutate


def _reconstruct_tick_state(  # pragma: no mutate — data deserialization
    tick_data: dict[str, Any],
) -> SimulationTickState | None:
    """Reconstruct SimulationTickState from a snapshot dict.

    Used by Simulation.get_time_series() to read accumulated snapshots
    stored in persistent_context. Unlike read_tick_state_from_graph(),
    this reads county_states directly from the dict (no graph nodes needed).

    Args:
        tick_data: Dict with keys: year, national_params, coefficients,
            tick_summary, county_states.

    Returns:
        Reconstructed SimulationTickState, or None if data is invalid.
    """
    if not tick_data:  # pragma: no mutate
        return None  # pragma: no mutate

    county_states: dict[str, CountyEconomicState] = tick_data.get(
        "county_states", {}
    )  # pragma: no mutate

    return SimulationTickState(  # pragma: no mutate
        year=tick_data["year"],  # pragma: no mutate
        national_params=tick_data["national_params"],  # pragma: no mutate
        county_states=county_states,  # pragma: no mutate
        coefficients=tick_data["coefficients"],  # pragma: no mutate
        tick_summary=tick_data.get("tick_summary"),  # pragma: no mutate
    )  # pragma: no mutate


__all__ = [
    "TICK_DYNAMICS_KEY",
    "_reconstruct_tick_state",
    "read_tick_state_from_graph",
    "write_tick_state_to_graph",
]
