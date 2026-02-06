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

from typing import Any

import networkx as nx

from babylon.economics.dynamics.types import ClassDistribution
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

# Graph metadata key
TICK_DYNAMICS_KEY: str = "tick_dynamics"


def write_tick_state_to_graph(
    graph: nx.DiGraph[str],
    state: SimulationTickState,
) -> None:
    """Write SimulationTickState to the shared NetworkX graph.

    Territory nodes with matching FIPS codes receive county-level
    attributes with ``tick_`` prefix. National-level parameters are
    stored in ``graph.graph["tick_dynamics"]``.

    Args:
        graph: Mutable NetworkX graph (modified in-place).
        state: Simulation tick state to write.
    """
    # Write national-level metadata
    graph.graph[TICK_DYNAMICS_KEY] = {
        "year": state.year,
        "national_params": state.national_params,
        "coefficients": state.coefficients,
        "tick_summary": state.tick_summary,
        "is_year_boundary": True,
    }

    # Write county-level state to Territory nodes
    for fips, county in state.county_states.items():
        if fips not in graph.nodes:
            continue
        node_data = graph.nodes[fips]
        # Only write to territory nodes
        if node_data.get("_node_type") != "territory":
            continue

        node_data["tick_capital_stock"] = county.capital_stock
        node_data["tick_throughput_position"] = county.throughput_position
        node_data["tick_supply_chain_depth"] = county.supply_chain_depth
        node_data["tick_phi_hour"] = county.phi_hour
        node_data["tick_crisis_phase"] = county.crisis_state.phase.value
        node_data["tick_crisis_duration"] = county.crisis_state.crisis_duration
        node_data["tick_bifurcation_score"] = county.bifurcation_risk.score
        node_data["tick_wage_compression"] = county.crisis_state.cumulative_wage_compression
        node_data["tick_class_distribution"] = {
            "bourgeoisie": county.class_distribution.bourgeoisie_share,
            "petit_bourgeoisie": county.class_distribution.petit_bourgeoisie_share,
            "labor_aristocracy": county.class_distribution.labor_aristocracy_share,
            "proletariat": county.class_distribution.proletariat_share,
            "lumpenproletariat": county.class_distribution.lumpenproletariat_share,
        }
        node_data["tick_unemployment_rate"] = county.unemployment_rate
        node_data["tick_median_wage"] = county.median_wage
        # Derived rates (from DerivedRates if available)
        node_data["tick_profit_rate"] = None
        node_data["tick_occ"] = None
        node_data["tick_exploitation_rate"] = None


def read_tick_state_from_graph(
    graph: nx.DiGraph[str],
) -> SimulationTickState | None:
    """Read SimulationTickState from the shared NetworkX graph.

    Reconstructs SimulationTickState from graph attributes written by
    ``write_tick_state_to_graph()``.

    Args:
        graph: NetworkX graph containing tick dynamics attributes.

    Returns:
        Reconstructed SimulationTickState, or None if no tick dynamics
        data is present in the graph.
    """
    tick_data: dict[str, Any] | None = graph.graph.get(TICK_DYNAMICS_KEY)
    if tick_data is None:
        return None

    national_params: NationalTickParameters = tick_data["national_params"]
    coefficients: SmoothedCoefficients = tick_data["coefficients"]
    tick_summary: TickSummary | None = tick_data.get("tick_summary")
    year: int = tick_data["year"]

    # Reconstruct county states from territory nodes
    county_states: dict[str, CountyEconomicState] = {}
    for node_id, node_data in graph.nodes(data=True):
        if node_data.get("_node_type") != "territory":
            continue
        if "tick_capital_stock" not in node_data:
            continue

        fips = str(node_id)
        dist_dict = node_data.get("tick_class_distribution", {})
        class_dist = ClassDistribution(
            fips=fips,
            year=year,
            bourgeoisie_share=dist_dict.get("bourgeoisie", 0.01),
            petit_bourgeoisie_share=dist_dict.get("petit_bourgeoisie", 0.09),
            labor_aristocracy_share=dist_dict.get("labor_aristocracy", 0.40),
            proletariat_share=dist_dict.get("proletariat", 0.35),
            lumpenproletariat_share=dist_dict.get("lumpenproletariat", 0.15),
        )

        county_states[fips] = CountyEconomicState(
            fips=fips,
            year=year,
            capital_stock=node_data["tick_capital_stock"],
            throughput_position=node_data["tick_throughput_position"],
            supply_chain_depth=node_data["tick_supply_chain_depth"],
            unemployment_rate=node_data.get("tick_unemployment_rate", 0.05),
            u6_rate=node_data.get("tick_u6_rate", 0.10),
            pter_rate=node_data.get("tick_pter_rate", 0.04),
            nilf_rate=node_data.get("tick_nilf_rate", 0.06),
            median_wage=node_data.get("tick_median_wage", 21.0),
            employment=node_data.get("tick_employment", 100000.0),
            class_distribution=class_dist,
            phi_hour=node_data.get("tick_phi_hour", 0.0),
            crisis_state=CrisisState(
                phase=CrisisPhase(node_data.get("tick_crisis_phase", "normal")),
                crisis_duration=node_data.get("tick_crisis_duration", 0),
                cumulative_wage_compression=node_data.get("tick_wage_compression", 0.0),
            ),
            bifurcation_risk=BifurcationRiskMetric(
                score=node_data.get("tick_bifurcation_score", 0.0),
            ),
        )

    return SimulationTickState(
        year=year,
        national_params=national_params,
        county_states=county_states,
        coefficients=coefficients,
        tick_summary=tick_summary,
    )


__all__ = [
    "TICK_DYNAMICS_KEY",
    "read_tick_state_from_graph",
    "write_tick_state_to_graph",
]
