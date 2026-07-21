"""The county read-model — ``project_county``, the Hoist's first projection.

Assembles a :class:`~babylon.projection.view_models.CountyView` dossier from
the post-tick world: the territory node's tick attributes plus the spec-065
county-attributed entity aggregates. Transport-neutral by construction — no
Django, no engine imports, no database connection; callers hand in the graph
and world they already hold.

**One producer per field** (the WO-3 ruling the charter requires — where the
tree offers several sources for a quantity, exactly one is projected and the
choice is recorded here):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``population``
     - spec-065 attribution sum — ``Σ SocialClass.population`` where
       ``county_fips`` matches (the same weights the survival and
       consciousness aggregates use, keeping the dossier internally
       consistent; NOT ``Territory.population``, the human-shield count).
   * - ``class_composition``
     - ``tick_class_distribution`` territory attribute (TickDynamicsSystem
       via ``graph_bridge.write_tick_state_to_graph``).
   * - ``median_wage``
     - ``tick_median_wage`` territory attribute.
   * - ``imperial_rent_phi``
     - ``tick_phi_hour`` territory attribute (per-county Leontief Φ — NOT
       the national ``economy.imperial_rent_pool``).
   * - ``consciousness``
     - ``aggregate_consciousness_for_county`` pop-weighted ``(r, l, f)``
       simplex — NOT the owner-gated always-default
       ``class_consciousness`` scalar.
   * - ``legitimacy``
     - ``legitimation_index`` territory attribute (LifecycleSystem, written
       every tick).
   * - ``p_acquiescence`` / ``p_revolution``
     - ``aggregate_survival_for_county`` pop-weighted means.
   * - ``bifurcation_score``
     - ``tick_bifurcation_score`` territory attribute.
   * - ``sovereign_id``
     - The single incoming CLAIMS edge on the county's territory node
       (spec-070); zero or contested (>1) claims project as ``None``.

Absence discipline (Constitution III.11): a missing territory attribute, an
unattributed county, or a contested claim projects as ``None`` — never a
default. In particular the aggregators' no-attribution sentinels — survival's
``(0.0, 0.0, 0)`` and consciousness's substrate default ``(0.3, 0.6, 0.1)``
— are detected *before* the call and converted to honest ``None``: a county
nobody has attributed has no consciousness reading, not a liberal-leaning one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.aggregation import (
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
)
from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    CountyView,
)

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState

__all__ = ["project_county"]


def _resolve_territory(graph: GraphProtocol, county_fips: str) -> GraphNode | None:
    """Find the territory node carrying ``county_fips``, deterministically.

    :param graph: The post-tick graph.
    :param county_fips: Five-digit county FIPS code.
    :returns: The matching territory node, or ``None`` when no territory
        carries the code. When several match (a county spanning bridge-minted
        territories), the lexicographically-first node id wins — a documented
        deterministic tie-break, revisited when multi-territory counties
        become real.
    """
    matches = [
        node
        for node in graph.query_nodes(node_type=NodeType.TERRITORY)
        if node.attributes.get("county_fips") == county_fips
    ]
    if not matches:
        return None
    return min(matches, key=lambda node: node.id)


def _single_claimant(graph: GraphProtocol, territory_id: str) -> str | None:
    """The sovereign claiming a territory, or ``None`` if unclaimed/contested.

    :param graph: The post-tick graph.
    :param territory_id: The territory node id.
    :returns: The claiming sovereign's node id when exactly one CLAIMS edge
        targets the territory; ``None`` for zero claims (unclaimed) or more
        than one (contested — a contested county has no *single* sovereign,
        and projecting one silently would erase the contest).
    """
    claimants = sorted(
        {
            edge.source_id
            for edge in graph.query_edges(edge_type=EdgeType.CLAIMS)
            if edge.target_id == territory_id
        }
    )
    if len(claimants) == 1:
        return claimants[0]
    return None


def project_county(
    county_fips: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> CountyView:
    """Project one county's post-tick state into a :class:`CountyView`.

    Read strictly *post-tick*: systems mutate the shared graph in-place in
    strict order, so a mid-tick read would see a partially-applied world.

    :param county_fips: Five-digit county FIPS code (e.g. ``"26163"``).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state (entity collection).
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated county dossier. Every unattributed or
        withheld quantity is ``None``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type, or a present ``tick_class_distribution`` is
        malformed — a wrong value fails loud, only a *missing* one is absence.
    """
    territory = _resolve_territory(graph, county_fips)
    attrs: dict[str, Any] = dict(territory.attributes) if territory else {}

    attributed = any(
        entity.county_fips == county_fips and int(entity.population) > 0
        for entity in world.entities.values()
    )
    if attributed:
        p_acq, p_rev, population = aggregate_survival_for_county(world, county_fips)
        ternary = aggregate_consciousness_for_county(world, county_fips)
        consciousness: ConsciousnessSimplex | None = ConsciousnessSimplex(
            revolutionary=ternary.r,
            liberal=ternary.l,
            fascist=ternary.f,
        )
        survival: tuple[float | None, float | None, int | None] = (
            p_acq,
            p_rev,
            population,
        )
    else:
        consciousness = None
        survival = (None, None, None)

    distribution = attrs.get("tick_class_distribution")
    composition = ClassComposition(**distribution) if distribution else None

    return CountyView(
        county_fips=county_fips,
        verified_tick=tick,
        population=survival[2],
        class_composition=composition,
        median_wage=attrs.get("tick_median_wage"),
        imperial_rent_phi=attrs.get("tick_phi_hour"),
        consciousness=consciousness,
        legitimacy=attrs.get("legitimation_index"),
        p_acquiescence=survival[0],
        p_revolution=survival[1],
        bifurcation_score=attrs.get("tick_bifurcation_score"),
        sovereign_id=_single_claimant(graph, territory.id) if territory else None,
    )
