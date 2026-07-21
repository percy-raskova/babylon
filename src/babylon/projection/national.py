"""The national read-model — ``project_national``, the nation-tier dossier.

Assembles a :class:`~babylon.projection.view_models.NationalView` from the
post-tick world: population-weighted rollups of the same per-territory tick
attributes and per-county aggregators :mod:`babylon.projection.county` reads,
one tier up, plus the ``v_national_value_aggregate`` declared-view row
(Constitution II.11) injected explicitly by the caller. Transport-neutral by
construction — no Django, no engine imports, no database connection; callers
hand in the graph and world they already hold, and (optionally) a
Postgres-sourced :class:`~babylon.persistence.postgres_aggregation.
NationalValueAggregate` row they already fetched.

**One producer per field** (mirrors the WO-3 ruling
:mod:`babylon.projection.county` records, extended one tier up):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``population``
     - Σ ``SocialClass.population`` over every entity nationwide with an
       attributed ``county_fips`` and positive population — the same
       spec-065 attribution sum :mod:`babylon.projection.county` uses,
       simply unfiltered by FIPS.
   * - ``class_composition``
     - Population-weighted mean of every territory node's own
       ``tick_class_distribution`` attribute, weighted by that territory's
       attributed county population.
   * - ``median_wage``
     - Population-weighted mean of every territory's ``tick_median_wage``.
   * - ``imperial_rent_pool``
     - ``WorldState.economy.imperial_rent_pool`` — the nationwide "Gas Tank"
       stock. NOT a rollup of the per-county ``tick_phi_hour`` Φ
       (:attr:`~babylon.projection.view_models.CountyView.imperial_rent_phi`);
       county.py's own docstring flags this as the field the county page
       deliberately does *not* use — this is where it belongs instead.
   * - ``consciousness``
     - Population-weighted combination of
       :func:`~babylon.persistence.county_aggregation.aggregate_consciousness_for_county`
       across every attributed county — reused verbatim, not re-derived.
   * - ``legitimacy``
     - Population-weighted mean of every territory's ``legitimation_index``.
   * - ``p_acquiescence`` / ``p_revolution``
     - Population-weighted combination of
       :func:`~babylon.persistence.county_aggregation.aggregate_survival_for_county`
       across every attributed county.
   * - ``bifurcation_score``
     - Population-weighted mean of every territory's
       ``tick_bifurcation_score``.
   * - ``sovereign_id``
     - The single sovereign holding a CLAIMS edge over *every* claimed
       territory nationwide; ``None`` for zero claims (unclaimed) or more
       than one distinct claimant anywhere (a balkanized/contested nation
       has no single sovereign).
   * - ``c_sum`` / ``v_sum`` / ``s_sum`` / ``k_sum`` / ``biocapacity_sum`` /
       ``hex_count``
     - The ``v_national_value_aggregate`` declared-view row
       (:class:`~babylon.persistence.postgres_aggregation.NationalValueAggregate`),
       injected via the ``national_aggregate`` parameter. This data is
       Postgres-only (spec-089: hex state is persisted, not graph-resident)
       and cannot be derived from ``graph``/``world`` at all — unlike every
       other field above, there is no in-memory path to it, so a caller with
       no Postgres session to read from passes ``None`` and gets honest
       absence, never a fabricated sum.

Absence discipline (Constitution III.11): a nation with no attributed county
anywhere projects every population-weighted field as ``None``, exactly like
an unattributed county. A present-but-malformed source value (e.g. a
territory's ``tick_class_distribution`` missing a class share) fails loud
through the same :class:`~babylon.projection.view_models.ClassComposition`
validation :mod:`babylon.projection.county` relies on — only a *missing*
value is absence.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Final

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.aggregation import (
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
)
from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    NationalView,
)

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState
    from babylon.persistence.postgres_aggregation import NationalValueAggregate

__all__ = ["national_statblocks", "project_national"]

#: Statblock row/provider shapes re-declared locally rather than imported
#: from ``babylon.tui.directives`` — the projection layer must not import
#: the client layer (layering is one-directional: tui depends on
#: projection, never the reverse), so this module stays structurally, not
#: nominally, compatible with ``babylon.tui.directives.StatblockProvider``.
_StatblockRow = tuple[str, str]
_StatblockProvider = Callable[[str], Sequence[_StatblockRow] | None]

#: NationalView fields that are always present (identity/provenance, plus
#: the always-materialized ``imperial_rent_pool`` — see its docstring on
#: :class:`~babylon.projection.view_models.NationalView`) — every other
#: declared field is walked for statblock resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"kind", "national_id", "verified_tick", "imperial_rent_pool"}
)


def _population_by_fips(world: WorldState) -> dict[str, int]:
    """Sum attributed population per county FIPS, nationwide, in one pass.

    :param world: The post-tick world state.
    :returns: A mapping of ``county_fips`` to summed population, over every
        entity with a non-``None`` ``county_fips`` and positive population.
        A county absent from ``world.entities`` entirely is simply absent
        from this mapping (weight zero) rather than a zero-valued entry.
    """
    totals: dict[str, int] = {}
    for entity in world.entities.values():
        if entity.county_fips is None:
            continue
        population = int(entity.population)
        if population <= 0:
            continue
        totals[entity.county_fips] = totals.get(entity.county_fips, 0) + population
    return totals


def _national_survival(
    world: WorldState,
    population_by_fips: Mapping[str, int],
) -> tuple[float | None, float | None]:
    """Population-weighted P(S|A)/P(S|R), combined across every attributed county.

    Reuses :func:`~babylon.persistence.county_aggregation.
    aggregate_survival_for_county` per county rather than re-deriving the
    per-entity weighting math.

    :param world: The post-tick world state.
    :param population_by_fips: The nationwide population-by-county mapping
        from :func:`_population_by_fips`.
    :returns: ``(mean_p_acquiescence, mean_p_revolution)``, or ``(None,
        None)`` if no county anywhere is attributed.
    """
    total_population = sum(population_by_fips.values())
    if total_population == 0:
        return (None, None)
    sum_acquiescence = 0.0
    sum_revolution = 0.0
    for fips, population in population_by_fips.items():
        p_acquiescence, p_revolution, _ = aggregate_survival_for_county(world, fips)
        sum_acquiescence += p_acquiescence * population
        sum_revolution += p_revolution * population
    return (sum_acquiescence / total_population, sum_revolution / total_population)


def _national_consciousness(
    world: WorldState,
    population_by_fips: Mapping[str, int],
) -> ConsciousnessSimplex | None:
    """Population-weighted consciousness simplex, combined across every attributed county.

    Reuses :func:`~babylon.persistence.county_aggregation.
    aggregate_consciousness_for_county` per county rather than re-deriving
    the ideology-to-ternary bridge mapping.

    :param world: The post-tick world state.
    :param population_by_fips: The nationwide population-by-county mapping
        from :func:`_population_by_fips`.
    :returns: The nationwide ternary simplex, or ``None`` if no county
        anywhere is attributed.
    """
    total_population = sum(population_by_fips.values())
    if total_population == 0:
        return None
    sum_r = 0.0
    sum_l = 0.0
    sum_f = 0.0
    for fips, population in population_by_fips.items():
        ternary = aggregate_consciousness_for_county(world, fips)
        sum_r += ternary.r * population
        sum_l += ternary.l * population
        sum_f += ternary.f * population
    return ConsciousnessSimplex(
        revolutionary=sum_r / total_population,
        liberal=sum_l / total_population,
        fascist=sum_f / total_population,
    )


def _weighted_mean(pairs: Sequence[tuple[float, int]]) -> float | None:
    """The population-weighted mean of a ``(value, weight)`` series.

    :param pairs: ``(value, weight)`` pairs; each weight is a whole-county
        population, always non-negative.
    :returns: The weighted mean, or ``None`` if the series is empty or every
        weight is zero.
    """
    total_weight = sum(weight for _, weight in pairs)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in pairs) / total_weight


def _territory_rollup(
    graph: GraphProtocol,
    population_by_fips: Mapping[str, int],
) -> tuple[ClassComposition | None, float | None, float | None, float | None]:
    """Population-weighted rollup of every territory's own tick attributes.

    Each territory is weighted by its own county's attributed population
    (``0`` — and so excluded — for a territory with no ``county_fips`` or
    one no entity is attributed to). A present ``tick_class_distribution``
    is validated through :class:`ClassComposition` per-territory before
    being folded into the rollup, so a malformed distribution on any one
    territory fails loud exactly as it would projecting that county alone
    (:mod:`babylon.projection.county`'s ``TestLoudFailure`` contract).

    :param graph: The post-tick graph.
    :param population_by_fips: The nationwide population-by-county mapping
        from :func:`_population_by_fips`.
    :returns: ``(class_composition, median_wage, legitimacy,
        bifurcation_score)``, each ``None`` if no territory contributes a
        weighted value for it.
    :raises pydantic.ValidationError: if a territory's
        ``tick_class_distribution`` is present but malformed.
    """
    wage_pairs: list[tuple[float, int]] = []
    legitimacy_pairs: list[tuple[float, int]] = []
    bifurcation_pairs: list[tuple[float, int]] = []
    composition_pairs: list[tuple[ClassComposition, int]] = []

    for territory in graph.query_nodes(node_type=NodeType.TERRITORY):
        fips = territory.attributes.get("county_fips")
        weight = population_by_fips.get(fips, 0) if fips is not None else 0
        if weight <= 0:
            continue

        distribution = territory.attributes.get("tick_class_distribution")
        if distribution:
            composition_pairs.append((ClassComposition(**distribution), weight))

        wage = territory.attributes.get("tick_median_wage")
        if wage is not None:
            wage_pairs.append((float(wage), weight))

        legitimacy = territory.attributes.get("legitimation_index")
        if legitimacy is not None:
            legitimacy_pairs.append((float(legitimacy), weight))

        bifurcation = territory.attributes.get("tick_bifurcation_score")
        if bifurcation is not None:
            bifurcation_pairs.append((float(bifurcation), weight))

    class_composition: ClassComposition | None = None
    composition_weight = sum(weight for _, weight in composition_pairs)
    if composition_weight > 0:
        shares = {
            name: sum(
                getattr(composition, name) * weight for composition, weight in composition_pairs
            )
            / composition_weight
            for name in ClassComposition.model_fields
        }
        class_composition = ClassComposition(**shares)

    return (
        class_composition,
        _weighted_mean(wage_pairs),
        _weighted_mean(legitimacy_pairs),
        _weighted_mean(bifurcation_pairs),
    )


def _national_sovereign(graph: GraphProtocol) -> str | None:
    """The single sovereign claiming every territory nationwide, or ``None``.

    :param graph: The post-tick graph.
    :returns: The claiming sovereign's node id when every CLAIMS edge
        targeting a territory node comes from the same sovereign; ``None``
        for zero claims nationwide (unclaimed) or claims from more than one
        distinct sovereign (a balkanized/contested nation has no single
        ruler, and projecting one silently would erase the fragmentation).
    """
    territory_ids = {node.id for node in graph.query_nodes(node_type=NodeType.TERRITORY)}
    claimants = sorted(
        {
            edge.source_id
            for edge in graph.query_edges(edge_type=EdgeType.CLAIMS)
            if edge.target_id in territory_ids
        }
    )
    if len(claimants) == 1:
        return claimants[0]
    return None


def project_national(
    national_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
    national_aggregate: NationalValueAggregate | None = None,
) -> NationalView:
    """Project the whole nation's post-tick state into a :class:`NationalView`.

    Read strictly *post-tick*, exactly like :func:`~babylon.projection.
    county.project_county`.

    :param national_id: The nation's identity (``"USA"`` today).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state.
    :param tick: The committed tick this dossier is projected from.
    :param national_aggregate: The ``v_national_value_aggregate`` row for
        this ``(national_id, tick)``, already fetched by the caller from
        Postgres — this module never queries a database itself (dependency
        injection, not runtime discovery). ``None`` when the caller has no
        Postgres session (e.g. a fixture-fed harvest run); every
        value-composition field then projects as honest absence.
    :returns: The frozen, validated national dossier.
    :raises ValueError: if ``national_aggregate`` is given but its
        ``national_id`` or ``tick`` does not match the arguments — a
        present-but-mismatched producer is a caller bug, surfaced loud
        rather than silently attributed to the wrong nation/tick.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    if national_aggregate is not None:
        if national_aggregate.national_id != national_id:
            msg = (
                f"national_aggregate.national_id {national_aggregate.national_id!r} "
                f"does not match projected national_id {national_id!r}"
            )
            raise ValueError(msg)
        if national_aggregate.tick != tick:
            msg = (
                f"national_aggregate.tick {national_aggregate.tick!r} "
                f"does not match projected tick {tick!r}"
            )
            raise ValueError(msg)

    population_by_fips = _population_by_fips(world)
    total_population = sum(population_by_fips.values())
    class_composition, median_wage, legitimacy, bifurcation_score = _territory_rollup(
        graph, population_by_fips
    )
    consciousness = _national_consciousness(world, population_by_fips)
    p_acquiescence, p_revolution = _national_survival(world, population_by_fips)

    return NationalView(
        national_id=national_id,
        verified_tick=tick,
        population=total_population if total_population > 0 else None,
        class_composition=class_composition,
        median_wage=median_wage,
        imperial_rent_pool=world.economy.imperial_rent_pool,
        consciousness=consciousness,
        legitimacy=legitimacy,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        bifurcation_score=bifurcation_score,
        sovereign_id=_national_sovereign(graph),
        c_sum=national_aggregate.c_sum if national_aggregate is not None else None,
        v_sum=national_aggregate.v_sum if national_aggregate is not None else None,
        s_sum=national_aggregate.s_sum if national_aggregate is not None else None,
        k_sum=national_aggregate.k_sum if national_aggregate is not None else None,
        biocapacity_sum=(
            national_aggregate.biocapacity_sum if national_aggregate is not None else None
        ),
        hex_count=national_aggregate.hex_count if national_aggregate is not None else None,
    )


def _optional_field_names() -> tuple[str, ...]:
    """NationalView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        NationalView` declaration order, excluding :data:`_IDENTITY_FIELDS`.
    """
    return tuple(name for name in NationalView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: NationalView) -> tuple[_StatblockRow, ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Mirrors :func:`babylon.projection.vault.render._statblock_rows`'s
    formatting convention (six-decimal floats) so a national statblock reads
    identically to a county one.

    :param view: the national projection to walk.
    :returns: ``(label, value)`` pairs in NationalView declaration order.
    """
    rows: list[_StatblockRow] = []
    for name in _optional_field_names():
        value = getattr(view, name)
        if value is None:
            continue
        if name == "class_composition":
            for field_name in ClassComposition.model_fields:
                share = getattr(value, field_name)
                rows.append((f"class_composition.{field_name}", f"{share:.6f}"))
        elif name == "consciousness":
            for field_name in ConsciousnessSimplex.model_fields:
                pole = getattr(value, field_name)
                rows.append((f"consciousness.{field_name}", f"{pole:.6f}"))
        elif isinstance(value, float):
            rows.append((name, f"{value:.6f}"))
        else:
            rows.append((name, str(value)))
    return tuple(rows)


def national_statblocks(views: Mapping[str, NationalView]) -> _StatblockProvider:
    """Build a live statblock provider over a fixed set of national dossiers.

    The per-kind provider function Wave-1 delivers alongside its page
    projection (shared-file discipline: ``app.py`` composition is Wave-2's
    WO-45, not this WO's job). Structurally matches
    ``babylon.tui.directives.StatblockProvider`` — a callable from subject
    id to statblock rows or ``None`` — without importing that module (the
    projection layer never imports the client layer).

    :param views: A mapping of subject id (``"national/<national_id>"``) to
        the :class:`NationalView` it resolves to — injected explicitly by
        the caller, never discovered at runtime.
    :returns: A callable ``subject -> rows | None``: ``None`` for any
        subject not in ``views`` (Constitution III.11 — no projection is
        honest absence, not a fabricated empty statblock).
    """

    def provider(subject: str) -> Sequence[_StatblockRow] | None:
        view = views.get(subject)
        if view is None:
            return None
        return _statblock_rows(view)

    return provider
