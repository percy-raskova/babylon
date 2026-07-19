"""Graph bridge for TickDynamicsSystem <-> NetworkX graph integration.

Feature: 017-simulation-tick-dynamics

Maps between SimulationTickState and NetworkX graph attributes so that
downstream engine Systems can consume tick dynamics outputs.

Territory nodes carry county-level state as ``tick_``-prefixed attributes.
National-level state is stored in ``graph.graph["tick_dynamics"]``.

See Also:
    :mod:`babylon.domain.economics.tick.types`: Data models
    :mod:`babylon.models.world_state`: WorldState graph serialization
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol

from babylon.config.defines import GameDefines
from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tick.derived_rates import DerivedRateCalculator
from babylon.domain.economics.tick.types import (
    BifurcationRiskMetric,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    DerivedRates,
    NationalFinancialParameters,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
    TickSummary,
)

# Graph metadata key
TICK_DYNAMICS_KEY: str = "tick_dynamics"


def resolve_county_identity(node: Any) -> str | None:
    """Resolve a territory node's REAL county identity, or ``None``.

    The county identity of a territory lives in its ``county_fips`` attribute
    and nowhere else. A graph node id is a graph-local label, NOT a county FIPS
    code: ``Territory.id`` is constrained to ``^(T[0-9]{3,}|[0-9a-f]{15})$``, so
    a production territory id is either a bridge-minted ``'T001'`` or a 15-char
    H3 cell — never a valid 5-char FIPS.

    The former ``county_fips or node.id`` fallback therefore could not succeed.
    It had exactly two possible outcomes, both wrong:

    1. a pydantic ``ValidationError`` downstream, because
       ``ClassDistribution.fips`` / ``CountyEconomicState.fips`` are
       ``min_length=5, max_length=5`` (``'T001'`` is 4 chars, an H3 id is 15);
    2. a pseudo-county that misses every real-FIPS-keyed data source.

    Fabricating an identifier is no better than fabricating a zero — both are
    Constitution III.11 violations. A territory with no ``county_fips`` has no
    county economic identity; that is an EMPTY DOMAIN and callers skip it. The
    NATIONAL layer is unaffected — it does not key on counties.

    Args:
        node: A graph node exposing ``attributes`` (only territories carry a
            county identity).

    Returns:
        The real county FIPS, or ``None`` when the territory carries none.
    """
    county_fips = node.attributes.get("county_fips")
    if county_fips is None:
        return None
    identity = str(county_fips)
    return identity if identity else None


def write_tick_state_to_graph(  # pragma: no mutate — data serialization
    graph: GraphProtocol,
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

    # county_states are keyed by real 5-digit FIPS, but territory node ids may be
    # graph-local labels (bridge-minted 'T001', owner item 25). Map FIPS -> node id
    # so the writeback lands on the right node; abstract territories key by their id.
    fips_to_node: dict[str, str] = {}  # pragma: no mutate
    for territory_node in graph.query_nodes():  # pragma: no mutate
        if territory_node.node_type != "territory":  # pragma: no mutate
            continue  # pragma: no mutate
        # Real county FIPS only (owner item 25). A territory with no
        # county_fips has no county identity — an empty domain, not a
        # pseudo-county named after its node label (see
        # :func:`resolve_county_identity`). The miss path below
        # (`fips_to_node.get(fips, fips)`) already covers abstract
        # territories keyed by their own id, so skipping here does not
        # change lookup semantics for real-FIPS territories.
        territory_fips = resolve_county_identity(territory_node)  # pragma: no mutate
        if territory_fips is None:  # pragma: no mutate
            continue  # pragma: no mutate
        fips_to_node[territory_fips] = str(territory_node.id)  # pragma: no mutate

    # Write county-level state to Territory nodes
    for fips, county in state.county_states.items():  # pragma: no mutate
        node_id = fips_to_node.get(fips, fips)  # pragma: no mutate
        node = graph.get_node(node_id)  # pragma: no mutate
        if node is None:  # pragma: no mutate
            continue  # pragma: no mutate
        # Only write to territory nodes
        if node.node_type != "territory":  # pragma: no mutate
            continue  # pragma: no mutate

        rates = county_rates[fips]  # pragma: no mutate
        graph.update_node(  # pragma: no mutate
            node_id,  # pragma: no mutate
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
            tick_renter_share=county.renter_share,  # pragma: no mutate
            tick_median_wage=county.median_wage,  # pragma: no mutate
            tick_bracket_ratio=county.bracket_ratio,  # pragma: no mutate
            tick_real_wage_deflator=county.real_wage_deflator,  # pragma: no mutate
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
                county.surplus_distribution.ground_rent  # pragma: no mutate
                if county.surplus_distribution is not None  # pragma: no mutate
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
    graph: GraphProtocol,
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

        # Real county FIPS (owner item 25). A territory with no county_fips has
        # no county identity to read back — an empty domain, not a pseudo-county
        # named after its node label (see :func:`resolve_county_identity`).
        fips = resolve_county_identity(node)  # pragma: no mutate
        if fips is None:  # pragma: no mutate
            continue  # pragma: no mutate
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
            renter_share=node_data.get("tick_renter_share", 0.0),  # pragma: no mutate
            u6_rate=node_data.get("tick_u6_rate", 0.10),  # pragma: no mutate
            pter_rate=node_data.get("tick_pter_rate", 0.04),  # pragma: no mutate
            nilf_rate=node_data.get("tick_nilf_rate", 0.06),  # pragma: no mutate
            median_wage=node_data.get("tick_median_wage", 21.0),  # pragma: no mutate
            employment=node_data.get("tick_employment", 100000.0),  # pragma: no mutate
            real_wage_deflator=node_data.get("tick_real_wage_deflator", 1.0),  # pragma: no mutate
            class_distribution=class_dist,  # pragma: no mutate
            phi_hour=node_data.get("tick_phi_hour", 0.0),  # pragma: no mutate
            bracket_ratio=node_data.get("tick_bracket_ratio", 0.0),  # pragma: no mutate
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


# Graph metadata key — Feature 024/vol3-money-scissors U3: the national
# financial state (interest rate environment + fictitious capital stock)
# published once per tick so CONSEQUENCE-phase Systems can read it. Kept
# separate from TICK_DYNAMICS_KEY / NationalTickParameters (the MELT/gamma
# carrier) — different lifecycle (see NationalFinancialParameters docstring).
NATIONAL_FINANCIAL_ATTR: Final[str] = "national_financial"


def write_national_financial_state_to_graph(  # pragma: no mutate — data serialization
    graph: GraphProtocol,
    params: NationalFinancialParameters,
) -> None:
    """Write NationalFinancialParameters to the shared graph.

    Feature: 024-capital-volume-iii / vol3-money-scissors U3

    Stores ``params.model_dump()`` (a plain dict, not the Pydantic object
    itself) under ``graph.graph[NATIONAL_FINANCIAL_ATTR]`` so any System
    later in the same tick can read it via
    :func:`read_national_financial_state_from_graph`.

    Args:
        graph: Mutable NetworkX graph or GraphProtocol (modified in-place).
        params: National financial state to publish.
    """
    graph.set_graph_attr(NATIONAL_FINANCIAL_ATTR, params.model_dump())  # pragma: no mutate


def read_national_financial_state_from_graph(  # pragma: no mutate — data serialization
    graph: GraphProtocol,
) -> NationalFinancialParameters | None:
    """Read NationalFinancialParameters from the shared graph.

    Feature: 024-capital-volume-iii / vol3-money-scissors U3

    Args:
        graph: NetworkX graph or GraphProtocol possibly containing the
            published financial state.

    Returns:
        Reconstructed NationalFinancialParameters, or None if nothing has
        been published this tick.
    """
    data: dict[str, Any] | None = graph.get_graph_attr(  # pragma: no mutate
        NATIONAL_FINANCIAL_ATTR
    )
    if data is None:  # pragma: no mutate
        return None  # pragma: no mutate
    return NationalFinancialParameters.model_validate(data)  # pragma: no mutate


def _employment_weighted_unemployment(
    county_states: dict[str, CountyEconomicState],
) -> float | None:
    """Aggregate U-3 unemployment ``rho_bar`` over the tick's county states.

    ``Sum(u3_i * employment_i) / Sum(employment_i)`` — the total-unemployed /
    total-labor-force aggregate, which is the materially-correct extensive
    weighting for an unemployment RATE (never the unweighted mean of the
    per-county rates, which is the intensive-aggregation defect class: a
    100k-worker county would swing the national reading as hard as Wayne).

    Employment is the natural weight (the labor force the rate is a fraction
    of), and unlike ``tick_capital_stock`` it is populated for every county
    (the capital calculator returns 0 for many county-years, so a
    capital-weighted reserve reading collapses to a structural zero). Read in
    scope from ``county_states`` — never from ``tick_``-prefixed graph attrs,
    which ``state.to_graph()`` strips at the top of every tick.

    Sorted-FIPS float accumulation (Constitution III.7). ``None`` — never a
    fabricated zero (III.11) — when no county carries positive employment.
    """
    weighted = 0.0
    weight = 0.0
    for fips in sorted(county_states):
        county = county_states[fips]
        employment = county.employment
        if employment <= 0.0:
            continue
        weighted += county.unemployment_rate * employment
        weight += employment
    if weight <= 0.0:
        return None
    return weighted / weight


def reserve_army_signal(
    county_states: dict[str, CountyEconomicState],
    defines: GameDefines,
) -> float:
    """Reserve-army downturn signal ``s_r`` in [0, 1] (loan-capital demand).

    ``clamp((rho_bar - rho_ref) / (1 - rho_ref), 0, 1)`` where ``rho_bar`` is
    the employment-weighted mean county U-3 unemployment rate
    (:func:`_employment_weighted_unemployment`) and ``rho_ref`` is
    ``capital_vol3.interest_reserve_reference`` — a threshold whose 0.08 value
    is calibrated against BLS UNRATE (U-3), so U-3 is the consistent
    county-native reserve measure (``CountyEconomicState`` carries no
    ``reserve_ratio``; U-3 is its labor-slack field). The rising reserve army
    is the material signature of the crisis that ignites the scramble for
    means of payment (Capital Vol. III ch. 25); below the reference there is
    no liquidity-demand pressure. Zero (not absent) when no county carries
    labor-force data.

    Reads ``county_states`` in scope (the freshly-computed current-tick
    states), never ``tick_``-prefixed graph attrs — those are stripped by
    ``state.to_graph()`` each tick and re-stamped only AFTER this financial
    layer runs, which structurally zeroed the prior graph-attr reading.
    """
    rho_bar = _employment_weighted_unemployment(county_states)
    if rho_bar is None:
        return 0.0
    rho_ref = defines.capital_vol3.interest_reserve_reference
    denom = 1.0 - rho_ref
    if denom <= 0.0:
        return 1.0 if rho_bar > rho_ref else 0.0
    raw = (rho_bar - rho_ref) / denom
    return 0.0 if raw < 0.0 else (1.0 if raw > 1.0 else raw)


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
    "NATIONAL_FINANCIAL_ATTR",
    "TICK_DYNAMICS_KEY",
    "_reconstruct_tick_state",
    "read_national_financial_state_from_graph",
    "read_tick_state_from_graph",
    "reserve_army_signal",
    "write_national_financial_state_to_graph",
    "write_tick_state_to_graph",
]
