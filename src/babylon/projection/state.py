"""The state read-model — ``project_state``, Program 24 P2's first nesting rollup.

Assembles a :class:`~babylon.projection.view_models.StateView` dossier by
rolling up every county within a US state — its territory nodes' tick
attributes plus the spec-065 county-attributed entity aggregates
(:mod:`babylon.persistence.county_aggregation`) — into one population-weighted
composite. Transport-neutral by construction, exactly like
:func:`babylon.projection.county.project_county`: no Django, no engine
imports, no database connection; callers hand in the graph and world they
already hold. State membership is derived structurally: a county belongs to a
state when its five-digit FIPS code's two-digit prefix equals the state's
FIPS code — there is no separate ``state`` graph node type (Constitution
II.11's spatial substrate is county/territory-grained); ``state`` is a
*projection-time* aggregation tier, R7's Victoria-3 nesting made concrete.

**One producer per field**, generalizing the WO-3 ruling ``project_county``
already discharges — where several counties each carry a value, exactly one
combination rule is projected and recorded here:

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``population``
     - SUM, over every county FIPS in the state, of the spec-065 attribution
       population :func:`~babylon.persistence.county_aggregation.
       aggregate_survival_for_county` returns per county — the same
       per-county producer ``project_county`` uses, added across counties.
   * - ``consciousness`` / ``p_acquiescence`` / ``p_revolution``
     - Population-weighted mean, across every *attributed* county in the
       state, of that county's own aggregate
       (:func:`~babylon.persistence.county_aggregation.
       aggregate_consciousness_for_county` /
       :func:`~babylon.persistence.county_aggregation.
       aggregate_survival_for_county`) — weighted by that county's
       attribution population.
   * - ``class_composition`` / ``median_wage`` / ``legitimacy`` /
       ``bifurcation_score``
     - Population-weighted mean, across every territory in the state
       carrying the underlying tick attribute (``tick_class_distribution``
       / ``tick_median_wage`` / ``legitimation_index`` /
       ``tick_bifurcation_score``), weighted by **the same spec-065
       attribution population** used for ``population``/``consciousness``.
       A WO-16 ruling: a territory intensity has no population signal
       independent of the human-shield ``Territory.population`` the county
       dossier already deliberately avoids (see ``project_county``'s own
       docstring) — reusing the attribution weight keeps the state rollup
       internally consistent with the county tier it nests.
   * - ``imperial_rent_phi``
     - SUM, over every territory in the state carrying ``tick_phi_hour``, of
       that value — an extensive labor-hours flow, summed unconditional on
       attribution (mirrors ``project_county``'s own unconditional read of
       the same attribute).
   * - ``sovereign_id``
     - The single sovereign iff *every* territory in the state resolves
       (:func:`babylon.projection.county._single_claimant`, reused) to the
       identical non-``None`` claimant; any disagreement, any
       unclaimed/contested territory, or a state with no territory at all
       projects ``None`` — the state-level generalization of county's own
       "zero or contested claims -> None" rule.

Absence discipline (Constitution III.11) generalizes identically: a state
with no attributed county projects ``population``/``consciousness``/survival
as ``None``; a state whose territories carry none of a given tick attribute
projects that field as ``None`` too — never a defaulted zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, cast

from babylon.models.enums.topology import NodeType
from babylon.persistence.county_aggregation import (
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
)
from babylon.projection.county import _single_claimant
from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    StateView,
)

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState

__all__ = ["project_state", "state_statblocks"]

#: The state this Wave-1 demo statblock table is fixture-derived for —
#: Michigan, the ``single_county`` scenario's sole territory's state (Wayne
#: County, FIPS ``26163``).
_DEMO_STATE_SUBJECT: Final[str] = "state/26"


def _in_state(county_fips: str | None, state_fips: str) -> bool:
    """Whether a county FIPS code's 2-digit state prefix matches ``state_fips``.

    :param county_fips: a 5-digit county FIPS, or ``None`` (unattributed).
    :param state_fips: the 2-digit state FIPS being projected.
    :returns: ``True`` iff ``county_fips`` is present and its prefix matches.
    """
    return county_fips is not None and county_fips[:2] == state_fips


def _territories_by_county_fips(graph: GraphProtocol, state_fips: str) -> dict[str, GraphNode]:
    """Every territory node under ``state_fips``, keyed by its own county FIPS.

    :param graph: the post-tick graph.
    :param state_fips: the 2-digit state FIPS to match.
    :returns: a mapping from county FIPS to the territory node claiming it,
        for every territory whose ``county_fips`` falls under this state.
    """
    result: dict[str, GraphNode] = {}
    for node in graph.query_nodes(node_type=NodeType.TERRITORY):
        county_fips = node.attributes.get("county_fips")
        if not _in_state(county_fips, state_fips):
            continue
        result[cast(str, county_fips)] = node
    return result


def _counties_in_state(graph: GraphProtocol, world: WorldState, state_fips: str) -> tuple[str, ...]:
    """Every county FIPS attributable to ``state_fips``, deterministically ordered.

    Unions the territory-node source with the world-entity source, mirroring
    ``project_county``'s own honesty that entity-sourced fields survive a
    county with no territory node yet.

    :param graph: the post-tick graph.
    :param world: the post-tick world state.
    :param state_fips: the 2-digit state FIPS to match.
    :returns: county FIPS codes, sorted for deterministic iteration.
    """
    from_territories: set[str] = set(_territories_by_county_fips(graph, state_fips))
    from_entities: set[str] = set()
    for entity in world.entities.values():
        county_fips = entity.county_fips
        if not _in_state(county_fips, state_fips):
            continue
        from_entities.add(cast(str, county_fips))
    return tuple(sorted(from_territories | from_entities))


def _rollup_survival_and_consciousness(
    world: WorldState,
    county_fips_codes: tuple[str, ...],
    survival_by_county: dict[str, tuple[float, float, int]],
) -> tuple[int | None, float | None, float | None, ConsciousnessSimplex | None]:
    """Population-weighted survival + consciousness across every county.

    :param world: the post-tick world state.
    :param county_fips_codes: every county FIPS in the state.
    :param survival_by_county: each county's precomputed
        ``(p_acquiescence, p_revolution, population)`` triple.
    :returns: ``(population, p_acquiescence, p_revolution, consciousness)``,
        all ``None`` if no county in the state is attributed.
    """
    total_population = 0
    p_acq_weighted = 0.0
    p_rev_weighted = 0.0
    r_weighted = l_weighted = f_weighted = 0.0
    for county_fips in county_fips_codes:
        p_acq, p_rev, pop = survival_by_county[county_fips]
        if pop <= 0:
            continue
        total_population += pop
        p_acq_weighted += p_acq * pop
        p_rev_weighted += p_rev * pop
        ternary = aggregate_consciousness_for_county(world, county_fips)
        r_weighted += ternary.r * pop
        l_weighted += ternary.l * pop
        f_weighted += ternary.f * pop
    if total_population == 0:
        return None, None, None, None
    return (
        total_population,
        p_acq_weighted / total_population,
        p_rev_weighted / total_population,
        ConsciousnessSimplex(
            revolutionary=r_weighted / total_population,
            liberal=l_weighted / total_population,
            fascist=f_weighted / total_population,
        ),
    )


def _pop_weighted_territory_mean(
    territories: dict[str, GraphNode],
    county_fips_codes: tuple[str, ...],
    survival_by_county: dict[str, tuple[float, float, int]],
    attribute: str,
) -> float | None:
    """Population-weighted mean of one scalar territory tick attribute.

    Weight is each county's spec-065 attribution population (the WO-16
    weight ruling — see this module's docstring). Used for
    ``tick_median_wage``, ``legitimation_index``, and
    ``tick_bifurcation_score`` — all three follow this identical shape.

    :param territories: county FIPS -> territory node, for this state.
    :param county_fips_codes: every county FIPS in the state.
    :param survival_by_county: each county's precomputed survival triple
        (only the population element is used here).
    :param attribute: the territory attribute name to average.
    :returns: the weighted mean, or ``None`` if no positively-weighted
        territory carries ``attribute``.
    """
    weight_total = 0
    weighted_sum = 0.0
    for county_fips in county_fips_codes:
        pop = survival_by_county[county_fips][2]
        if pop <= 0:
            continue
        territory = territories.get(county_fips)
        if territory is None:
            continue
        value = territory.attributes.get(attribute)
        if value is None:
            continue
        weight_total += pop
        weighted_sum += value * pop
    return weighted_sum / weight_total if weight_total > 0 else None


def _rollup_class_composition(
    territories: dict[str, GraphNode],
    county_fips_codes: tuple[str, ...],
    survival_by_county: dict[str, tuple[float, float, int]],
) -> ClassComposition | None:
    """Population-weighted five-class composite across every territory.

    Each contributing county's own ``tick_class_distribution`` is validated
    through :class:`ClassComposition` first (a malformed per-county
    distribution fails loud, exactly as ``project_county`` does), then
    combined by the same attribution-population weight as
    :func:`_pop_weighted_territory_mean`.

    :param territories: county FIPS -> territory node, for this state.
    :param county_fips_codes: every county FIPS in the state.
    :param survival_by_county: each county's precomputed survival triple.
    :returns: the weighted composite, or ``None`` if no positively-weighted
        territory carries a distribution.
    :raises pydantic.ValidationError: if a present distribution is malformed.
    """
    weight_total = 0
    weighted_shares: dict[str, float] = dict.fromkeys(ClassComposition.model_fields, 0.0)
    for county_fips in county_fips_codes:
        pop = survival_by_county[county_fips][2]
        if pop <= 0:
            continue
        territory = territories.get(county_fips)
        if territory is None:
            continue
        distribution = territory.attributes.get("tick_class_distribution")
        if distribution is None:
            continue
        composition = ClassComposition(**distribution)
        weight_total += pop
        for field_name in ClassComposition.model_fields:
            weighted_shares[field_name] += getattr(composition, field_name) * pop
    if weight_total == 0:
        return None
    return ClassComposition(
        **{name: weighted_shares[name] / weight_total for name in ClassComposition.model_fields}
    )


def _sum_territory_attribute(territories: dict[str, GraphNode], attribute: str) -> float | None:
    """SUM a scalar territory tick attribute across every territory in the state.

    An extensive flow quantity (imperial rent Φ), summed unconditional on
    entity attribution — mirrors ``project_county``'s own unconditional read
    of the same attribute at county scope.

    :param territories: county FIPS -> territory node, for this state.
    :param attribute: the territory attribute name to sum.
    :returns: the sum, or ``None`` if no territory in the state carries it.
    """
    values = [
        territory.attributes[attribute]
        for territory in territories.values()
        if attribute in territory.attributes
    ]
    return sum(values) if values else None


def _rollup_sovereign(graph: GraphProtocol, territories: dict[str, GraphNode]) -> str | None:
    """The single sovereign iff every territory in the state agrees.

    :param graph: the post-tick graph.
    :param territories: county FIPS -> territory node, for this state.
    :returns: the shared claimant id, or ``None`` if the state has no
        territory, or its territories disagree, or any is unclaimed/contested.
    """
    if not territories:
        return None
    claimants = {_single_claimant(graph, territory.id) for territory in territories.values()}
    if len(claimants) == 1:
        (only,) = claimants
        return only
    return None


def project_state(
    state_fips: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> StateView:
    """Project every county under ``state_fips`` into one :class:`StateView`.

    Read strictly *post-tick*, exactly like
    :func:`~babylon.projection.county.project_county` (systems mutate the
    shared graph in-place in strict order, so a mid-tick read would see a
    partially-applied world).

    :param state_fips: Two-digit state FIPS code (e.g. ``"26"`` for Michigan).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state (entity collection).
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated state dossier. Every unattributed or
        withheld quantity is ``None``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type, or a present ``tick_class_distribution`` on
        any territory in the state is malformed — a wrong value fails loud,
        only a *missing* one is absence.
    """
    territories = _territories_by_county_fips(graph, state_fips)
    county_fips_codes = _counties_in_state(graph, world, state_fips)
    survival_by_county = {
        county_fips: aggregate_survival_for_county(world, county_fips)
        for county_fips in county_fips_codes
    }

    population, p_acquiescence, p_revolution, consciousness = _rollup_survival_and_consciousness(
        world, county_fips_codes, survival_by_county
    )

    return StateView(
        state_fips=state_fips,
        verified_tick=tick,
        population=population,
        class_composition=_rollup_class_composition(
            territories, county_fips_codes, survival_by_county
        ),
        median_wage=_pop_weighted_territory_mean(
            territories, county_fips_codes, survival_by_county, "tick_median_wage"
        ),
        imperial_rent_phi=_sum_territory_attribute(territories, "tick_phi_hour"),
        consciousness=consciousness,
        legitimacy=_pop_weighted_territory_mean(
            territories, county_fips_codes, survival_by_county, "legitimation_index"
        ),
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        bifurcation_score=_pop_weighted_territory_mean(
            territories, county_fips_codes, survival_by_county, "tick_bifurcation_score"
        ),
        sovereign_id=_rollup_sovereign(graph, territories),
    )


def state_statblocks(subject: str) -> list[tuple[str, str]] | None:
    """The state page's Wave-1 demo statblock rows for ``state/<fips>``.

    Structurally conforms to ``babylon.tui.directives.StatblockProvider``
    (``Callable[[str], Sequence[tuple[str, str]] | None]``) *without
    importing* ``babylon.tui`` — ``babylon.projection`` sits below
    ``babylon.tui`` in the layering (this package's own docstring: clients
    consume projections, never the reverse), so the dependency direction
    stays correct and the callable shape is satisfied structurally rather
    than by import.

    Wave-1 scope (WO-16): mirrors the keel demo's own shape
    (``babylon.tui.app._sample_statblocks``) — a small, real-data-derived
    table for exactly one subject, hardcoded here rather than read from
    ``tests/fixtures/`` at runtime (production code must never depend on the
    tests tree). The numbers below are this WO's harvester's actual output
    for Michigan (committed at ``tests/fixtures/projection/state_26.json`` —
    regenerate both via ``uv run python tools/record_state_fixture.py`` if
    the ``single_county`` scenario changes). WO-45 replaces every Lane-P
    demo provider with one live/baked kind-dispatch registry.

    :param subject: the statblock subject id.
    :returns: demo rows for ``"state/26"``, else ``None``.
    """
    if subject != _DEMO_STATE_SUBJECT:
        return None
    return [
        ("population", "2"),
        ("median_wage", "21.00"),
        ("imperial_rent_phi", "0.00"),
        ("bifurcation_score", "0.00"),
    ]
