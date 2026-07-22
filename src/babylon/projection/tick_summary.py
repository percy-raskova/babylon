"""The ``tick_summary`` kwargs builder — ``build_tick_summary_kwargs`` (T5 Unit U2).

Port of ``web/game/engine_bridge.py::_build_tick_summary`` (lines ~9341-9420)
and its ``_county_tick_series_aggregates`` helper (lines ~8660-8737) into a
pure projection helper — same read logic, no redesign. The web bridge's
``persist_tick_summary`` caller (``_persist_snapshots_safe``,
``web/game/engine_bridge.py:9486-9495``) is the only production caller of
:meth:`~babylon.persistence.postgres_runtime.PostgresRuntime.
persist_tick_summary` before this unit — a real Archive campaign
(:class:`~babylon.game.session.GameSession`) wrote nothing to ``tick_summary``
at all, so every trend read over it was empty (the same dormant-construct
pattern T3 closed for field-state). This module supplies the SAME kwargs
shape from :class:`~babylon.game.session.GameSession`'s own commit boundary,
with no Django, no engine imports, and no database connection — the caller
hands in the graph and world it already holds.

Only values the engine actually computes are aggregated; everything else
stays ``None`` — NULL columns over invented zeros (Constitution III.11),
exactly matching the ported ``_build_tick_summary``'s own contract:

* ``year`` / ``total_c`` / ``total_v`` / ``total_s`` / ``exploitation_rate``
  / ``profit_rate`` / ``co_optive_edge_count`` / ``conservation_check`` are
  ALWAYS ``None`` in the ported source too — no engine system computes them
  yet, so this helper does not invent values for them either.
* ``imperial_rent`` from :class:`~babylon.models.entities.economy.GlobalEconomy`'s
  ``imperial_rent_pool``; ``avg_consciousness`` over
  ``SocialClass.ideology.class_consciousness``; ``price_log``/
  ``fictitious_log``/``market_corrections`` from the Program 23 Market
  Scissors shadow axis (:class:`~babylon.models.market.MarketState`) — each
  ``None`` when its own axis is absent this tick.
* ``solidarity_edge_count``/``antagonistic_edge_count`` count
  :class:`~babylon.models.entities.relationship.Relationship` rows by
  ``edge_type`` (direct :class:`~babylon.models.enums.topology.EdgeType`
  comparison — the SAME counting rule as the ported source's own
  ``_enum_val``-string match, since ``Relationship.edge_type`` is a
  strictly-typed enum field in this module's Pydantic boundary, unlike the
  web bridge's own dict-serialized payloads).
* ``uprising_count`` counts this tick's raw kernel
  :class:`~babylon.kernel.event_bus.Event` history (the ``events=`` param)
  by ``.type`` against :class:`~babylon.models.enums.events.EventType`;
  ``repression_count`` is ALWAYS ``None`` — no production bus publisher
  for STATE_REPRESSION exists (see the assignment-site comment)
  (REVIEW FIX, T5 U2: the first cut counted ``WorldState.events`` instead,
  which is ALWAYS empty on the Archive path —
  ``WorldState.from_graph()`` reconstructs ``.events`` from
  ``graph.graph['events']``, a key only
  :meth:`~babylon.models.world_state.WorldState.to_graph` ever writes
  (once, at tick-0 boot); no engine system restamps it per tick, so every
  ``advance_tick`` call was silently persisting a fabricated ``0`` instead
  of the real count — exactly the invented-zero Constitution III.11
  forbids. :meth:`~babylon.game.session.GameSession.advance_tick` already
  collects the tick's real bus history via ``bus.get_history()`` for the
  Chronicle adapter; this module reuses that SAME tuple rather than
  inventing a second event source). ``events=None`` (no history threaded)
  keeps both columns honestly ``None`` — a caller with no history is a
  different state from "zero events happened this tick", so it is never
  collapsed to the same ``0``.
* ``org_count``/``player_org_count`` read ``WorldState.organizations``/
  ``player_org_id`` directly rather than the ported source's own
  already-``_serialize_organization``-ed ``organizations`` list — the same
  ``_is_player_org`` single-source-of-truth comparison
  (``org_id == player_org_id``, never a heuristic), since this module never
  needs the fog-gated presentation fields ``_serialize_organization``
  computes for a UI, only the two counts.

Playability Spine Task 19 (spec-116 4d.5): when ``graph`` is supplied (the
committed post-tick graph), five county-deduped year-boundary aggregates
ride the row via :func:`_county_tick_series_aggregates`; without a graph they
are honest ``None`` — tick-0 has no TickDynamics output.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

from babylon.models.enums.events import EventType
from babylon.models.enums.topology import EdgeType, NodeType

if TYPE_CHECKING:
    from babylon.kernel.event_bus import Event
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState

__all__ = ["build_tick_summary_kwargs"]

#: The three ``tick_crisis_phase`` values counted as "in crisis" by
#: ``crisis_pop_share`` — verbatim from the ported
#: ``_county_tick_series_aggregates``.
_CRISIS_ACTIVE_PHASES: Final[frozenset[str]] = frozenset({"onset", "early", "deep"})

#: The five ``tick_*`` territory attrs the county-dedup pass reads, in the
#: order the ported source visits them.
_TICK_SERIES_KEYS: Final[tuple[str, ...]] = (
    "tick_crisis_phase",
    "tick_bifurcation_score",
    "tick_wage_compression",
    "tick_capital_stock",
    "tick_unemployment_rate",
)

#: The five aggregate columns' honest-absent shape when no graph is supplied
#: (tick-0 bootstrap call sites) — verbatim from the ported
#: ``_build_tick_summary``'s own no-graph branch.
_EMPTY_TICK_SERIES: Final[dict[str, float | None]] = {
    "crisis_pop_share": None,
    "bifurcation_score_mean": None,
    "wage_compression_mean": None,
    "capital_stock_total": None,
    "unemployment_rate_mean": None,
}


def _county_weighted_mean(rows: list[tuple[float, float]]) -> float | None:
    """Population-weighted mean, falling back to a plain mean at zero weight.

    Deliberately distinct from :func:`babylon.projection.national._weighted_mean`
    (which returns ``None`` at zero total weight): the ported
    ``_county_tick_series_aggregates`` instead falls back to an unweighted
    mean across the counties present, so this helper preserves that EXACT
    fallback rather than the different national.py contract.

    :param rows: ``(value, population_weight)`` pairs, one per county that
        carries the attr being averaged.
    :returns: The weighted mean, or the plain mean when every weight is
        zero, or ``None`` for an empty series.
    """
    if not rows:
        return None
    total_weight = sum(weight for _value, weight in rows)
    if total_weight > 0:
        return sum(value * weight for value, weight in rows) / total_weight
    return sum(value for value, _weight in rows) / len(rows)


def _county_tick_series_aggregates(graph: GraphProtocol) -> dict[str, float | None]:
    """County-deduped aggregates of the year-boundary ``tick_*`` attrs.

    Port of ``web/game/engine_bridge.py::_county_tick_series_aggregates``
    (lines ~8660-8737): every territory in a county carries the SAME
    county-level ``tick_*`` stamps, so aggregating per TERRITORY would
    inflate every county quantity N-fold. This dedupes to one representative
    value per ``county_fips`` (first non-``None`` seen per attr), weights
    the intensive means by summed county population
    (:func:`_county_weighted_mean`), and sums the extensive capital stock.

    Honest-sparse by construction (Constitution III.11): ``tick_*`` attrs
    stamp at year boundaries only and carry forward between them, so every
    aggregate is ``None`` before the first boundary this session and a step
    function after — never a fabricated 0.0, never smoothed.

    :param graph: The committed post-tick graph whose territory nodes may
        carry the ``tick_*`` attrs.
    :returns: Dict with ``crisis_pop_share`` / ``bifurcation_score_mean`` /
        ``wage_compression_mean`` / ``capital_stock_total`` /
        ``unemployment_rate_mean``, each ``float | None``.
    """
    pops: dict[str, float] = {}
    reps: dict[str, dict[str, Any]] = {}
    for node in graph.query_nodes(node_type=NodeType.TERRITORY):
        attrs = node.attributes
        fips = attrs.get("county_fips")
        if not fips:
            continue
        pops[fips] = pops.get(fips, 0.0) + max(0.0, float(attrs.get("population") or 0))
        rep = reps.setdefault(fips, {})
        for key in _TICK_SERIES_KEYS:
            if rep.get(key) is None and attrs.get(key) is not None:
                rep[key] = attrs[key]

    def weighted_mean(key: str) -> float | None:
        rows = [
            (float(rep[key]), pops[fips]) for fips, rep in reps.items() if rep.get(key) is not None
        ]
        return _county_weighted_mean(rows)

    phased = [
        (rep["tick_crisis_phase"], pops[fips])
        for fips, rep in reps.items()
        if rep.get("tick_crisis_phase") is not None
    ]
    crisis_pop_share: float | None = None
    if phased:
        total = sum(weight for _phase, weight in phased)
        if total > 0:
            crisis_pop_share = (
                sum(weight for phase, weight in phased if phase in _CRISIS_ACTIVE_PHASES) / total
            )
        else:
            crisis_pop_share = sum(
                1 for phase, _weight in phased if phase in _CRISIS_ACTIVE_PHASES
            ) / len(phased)

    capitals = [
        float(rep["tick_capital_stock"])
        for rep in reps.values()
        if rep.get("tick_capital_stock") is not None
    ]
    return {
        "crisis_pop_share": crisis_pop_share,
        "bifurcation_score_mean": weighted_mean("tick_bifurcation_score"),
        "wage_compression_mean": weighted_mean("tick_wage_compression"),
        "capital_stock_total": sum(capitals) if capitals else None,
        "unemployment_rate_mean": weighted_mean("tick_unemployment_rate"),
    }


def build_tick_summary_kwargs(
    world: WorldState,
    *,
    graph: GraphProtocol | None = None,
    events: Sequence[Event] | None = None,
) -> dict[str, Any]:
    """Aggregate one committed tick's ``tick_summary`` row from live state.

    Port of ``web/game/engine_bridge.py::_build_tick_summary`` (lines
    ~9341-9420) — same field semantics, no redesign (see this module's own
    docstring for the field-by-field ruling and the deliberate mechanical
    simplifications: direct enum comparison in place of ``_enum_val``-string
    matching, and reading ``org_count``/``player_org_count`` straight off
    ``WorldState`` rather than an already-``_serialize_organization``-ed
    list).

    :param world: The committed, post-tick ``WorldState``
        (``WorldState.from_graph(graph, tick=...)`` — never a bootstrap
        ``WorldState`` with a stale ``events`` list, since ``events`` is
        per-tick, not cumulative). NOTE: ``world.events`` is NOT read for
        ``uprising_count``/``repression_count`` (see ``events=`` below) —
        ``WorldState.from_graph()`` never restamps it per tick, so it would
        always be empty on this path.
    :param graph: The SAME committed post-tick graph ``world`` was built
        from, when the caller has one — unlocks the five county-deduped
        year-boundary aggregates via :func:`_county_tick_series_aggregates`.
        ``None`` (tick-0 bootstrap call sites) keeps those five honestly
        ``None`` rather than fabricating a step-function head.
    :param events: This tick's raw kernel bus history (typically
        ``tuple(bus.get_history())`` — the SAME tuple
        :meth:`~babylon.game.session.GameSession.advance_tick` already
        collects for the Chronicle adapter), used to count
        ``uprising_count`` by ``.type``. ``None`` (no history threaded)
        keeps it honestly ``None`` rather than a fabricated ``0``
        (Constitution III.11). ``repression_count`` is ALWAYS ``None``
        regardless — no production bus publisher for STATE_REPRESSION
        exists (see the inline comment at its assignment).
    :returns: Kwargs dict for
        :meth:`~babylon.persistence.postgres_runtime.PostgresRuntime.
        persist_tick_summary`.
    """
    consciousness_values = [
        float(sc.ideology.class_consciousness) for sc in world.entities.values()
    ]
    avg_consciousness = (
        sum(consciousness_values) / len(consciousness_values) if consciousness_values else None
    )

    solidarity_edge_count = sum(
        1 for rel in world.relationships if rel.edge_type == EdgeType.SOLIDARITY
    )
    antagonistic_edge_count = sum(
        1 for rel in world.relationships if rel.edge_type == EdgeType.EXPLOITATION
    )
    uprising_count: int | None
    if events is None:
        uprising_count = None
    else:
        uprising_count = sum(1 for event in events if event.type == EventType.UPRISING)
    # repression_count is honestly NULL, never a bus count: NO production
    # code publishes STATE_REPRESSION to the kernel bus (the OODA
    # first-class-action gate covers only POGROM/LOCKOUT/VIGILANTISM; the
    # type otherwise lives only as a string inside ActionResult.
    # events_generated), so counting it over bus history is a structural
    # fabricated 0 (Constitution III.11). The web-bridge reference is
    # latently 0 for the same reason. Flip this to a real count only when
    # an engine unit adds a STATE_REPRESSION bus publisher on the REPRESS
    # path (declared drift ceremony).
    repression_count: int | None = None
    player_org_count = sum(
        1 for org in world.organizations.values() if org.id == world.player_org_id
    )

    return {
        "year": None,
        "total_c": None,
        "total_v": None,
        "total_s": None,
        "exploitation_rate": None,
        "profit_rate": None,
        "imperial_rent": float(world.economy.imperial_rent_pool) if world.economy else None,
        "avg_consciousness": avg_consciousness,
        "solidarity_edge_count": solidarity_edge_count,
        "antagonistic_edge_count": antagonistic_edge_count,
        "co_optive_edge_count": None,
        "org_count": len(world.organizations),
        "player_org_count": player_org_count,
        "uprising_count": uprising_count,
        "repression_count": repression_count,
        "conservation_check": None,
        # Program 23 (ADR077): the Market Scissors shadow axis. NULL when the
        # axis is absent this tick (no value substrate yet) — honest
        # absence.
        "price_log": float(world.market.price_log) if world.market else None,
        "fictitious_log": float(world.market.fictitious_log) if world.market else None,
        # ADR078: cumulative correction-snap count, same NULL contract.
        "market_corrections": int(world.market.corrections) if world.market else None,
        # Playability Spine Task 19 (spec-116 4d.5): county-deduped crisis/
        # bifurcation history. NULL without a graph or before the first year
        # boundary — honest sparse (step function), never smoothed.
        **(_county_tick_series_aggregates(graph) if graph is not None else _EMPTY_TICK_SERIES),
    }
