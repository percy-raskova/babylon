"""The social-class read-model — ``project_social_class``.

Assembles a :class:`~babylon.projection.view_models.SocialClassView` dossier
for one social-class graph node (``NodeType.SOCIAL_CLASS``) from the
post-tick world. Transport-neutral by construction — no Django, no engine
imports, no database connection; callers hand in the graph and world they
already hold (mirrors :func:`babylon.projection.county.project_county`
exactly, per the Program 24 P2 Lane P extension recipe).

**One producer per field** (the WO-3 ruling the charter requires):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``role``
     - ``SocialClass.role`` node attribute (stamped by ``WorldState.to_graph``
       via ``entity.model_dump()``) — this class's fixed position in the
       world system.
   * - ``county_fips``
     - ``SocialClass.county_fips`` node attribute (spec-065 attribution key).
       ``None`` (unset) and ``""`` (explicitly unattributed) both hydrate
       through as the source stores them; both are treated as "no county to
       nest under" for :attr:`~babylon.projection.view_models.
       SocialClassView.county_class_composition` resolution.
   * - ``population``
     - ``SocialClass.population`` node attribute — this class's own block
       size, NOT a county-wide aggregate (contrast
       ``CountyView.population``, the pop-weighted county sum).
   * - ``wealth``
     - ``SocialClass.wealth`` node attribute (post-tick, mutated in-place by
       Production/Struggle/MarketScissors — read the graph, not a stale
       pre-tick model instance, per the "systems mutate the shared graph"
       gotcha).
   * - ``organization``
     - ``SocialClass.organization`` node attribute.
   * - ``repression_faced``
     - ``SocialClass.repression_faced`` node attribute.
   * - ``p_acquiescence`` / ``p_revolution``
     - ``SocialClass.p_acquiescence`` / ``p_revolution`` node attributes —
       this class's own survival-calculus outputs, NOT the pop-weighted
       county mean ``aggregate_survival_for_county`` produces.
   * - ``consciousness``
     - This class's own ``IdeologicalProfile`` (``class_consciousness``,
       ``national_identity``) mapped through the spec-065 bridge
       (:func:`~babylon.persistence.county_aggregation._ideology_to_ternary`)
       — the same mapping ``aggregate_consciousness_for_county``
       population-weights across many entities, applied here to one.
   * - ``county_class_composition``
     - The containing county's ``tick_class_distribution`` territory
       attribute (nesting context — the same producer
       :attr:`CountyView.class_composition` uses), resolved via this
       class's own ``county_fips``. Deliberately duplicated resolution logic
       (not a cross-module import of ``county.py``'s private helper) so this
       module and ``county.py`` stay independently evolvable — both are
       small, single-purpose lookups over the same territory shape.

Absence discipline (Constitution III.11): a ``class_id`` absent from the
committed :class:`~babylon.models.world_state.WorldState` — the authoritative
registry of which entities currently exist, preferred here over trusting a
graph node's mere presence, which can outlive an entity's removal from
``world.entities`` — projects every non-identity field as ``None``, never a
default.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import NodeType
from babylon.persistence.county_aggregation import _ideology_to_ternary
from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    SocialClassView,
)

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState

__all__ = ["project_social_class", "social_class_statblocks"]


def _resolve_class_node(graph: GraphProtocol, class_id: str) -> GraphNode | None:
    """Find the social-class node carrying ``class_id``, if it exists.

    :param graph: The post-tick graph.
    :param class_id: The social-class node id (e.g. ``"C004"``).
    :returns: The matching node, or ``None`` when absent or when a node of
        that id exists but carries a different ``_node_type`` (a shape
        mismatch this projection refuses to read through).
    """
    node = graph.get_node(class_id)
    if node is None or node.node_type != NodeType.SOCIAL_CLASS:
        return None
    return node


def _resolve_county_composition(graph: GraphProtocol, county_fips: str) -> ClassComposition | None:
    """The containing county's class-share breakdown, for nesting context.

    :param graph: The post-tick graph.
    :param county_fips: Five-digit county FIPS code to resolve a territory for.
    :returns: The territory's :class:`ClassComposition`, or ``None`` when no
        territory carries ``county_fips`` or it has no
        ``tick_class_distribution`` attribute yet. Several territories
        sharing a FIPS (a documented deterministic tie-break, mirroring
        ``county.py``) resolve to the lexicographically-first node id.
    """
    matches = [
        node
        for node in graph.query_nodes(node_type=NodeType.TERRITORY)
        if node.attributes.get("county_fips") == county_fips
    ]
    if not matches:
        return None
    territory = min(matches, key=lambda node: node.id)
    distribution = territory.attributes.get("tick_class_distribution")
    if not distribution:
        return None
    return ClassComposition(**distribution)


def project_social_class(
    class_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> SocialClassView:
    """Project one social class's post-tick state into a :class:`SocialClassView`.

    Read strictly *post-tick*, like :func:`~babylon.projection.county.
    project_county`: systems mutate the shared graph in-place in strict
    order, so a mid-tick read would see a partially-applied world.

    :param class_id: The social-class node id (e.g. ``"C004"``).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state — consulted as the
        authoritative existence registry (see module docstring); this
        class's own field values are read from the graph node, not from a
        ``world.entities`` model instance, so a ``from_graph`` reconstruction
        gap can never silently mask an absent field with a defaulted one.
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated social-class dossier. Every unattributed
        or absent quantity is ``None``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type, or a present ``tick_class_distribution`` is
        malformed — a wrong value fails loud, only a *missing* one is
        absence.
    """
    node = _resolve_class_node(graph, class_id) if class_id in world.entities else None
    attrs: dict[str, Any] = dict(node.attributes) if node is not None else {}

    ideology = attrs.get("ideology")
    consciousness: ConsciousnessSimplex | None
    if ideology:
        r, l_, f = _ideology_to_ternary(
            float(ideology["class_consciousness"]),
            float(ideology["national_identity"]),
        )
        consciousness = ConsciousnessSimplex(revolutionary=r, liberal=l_, fascist=f)
    else:
        consciousness = None

    county_fips = attrs.get("county_fips")
    county_class_composition = (
        _resolve_county_composition(graph, county_fips) if county_fips else None
    )

    return SocialClassView(
        class_id=class_id,
        verified_tick=tick,
        role=attrs.get("role"),
        county_fips=county_fips,
        population=attrs.get("population"),
        wealth=attrs.get("wealth"),
        organization=attrs.get("organization"),
        repression_faced=attrs.get("repression_faced"),
        p_acquiescence=attrs.get("p_acquiescence"),
        p_revolution=attrs.get("p_revolution"),
        consciousness=consciousness,
        county_class_composition=county_class_composition,
    )


def social_class_statblocks(
    view: SocialClassView,
) -> Callable[[str], list[tuple[str, str]] | None]:
    """Build the per-kind statblock provider for one social-class dossier.

    Returns a closure matching ``babylon.tui.directives.StatblockProvider``'s
    exact shape (``Callable[[str], Sequence[tuple[str, str]] | None]``)
    without this module importing ``babylon.tui`` — this package reads
    strictly downward (``babylon/projection/__init__.py``). Mirrors
    ``babylon.tui.app._sample_statblocks``'s "known subject -> fixed rows,
    else None" contract; the single WO-45 integrator composes every Lane P
    kind's provider (built from its live per-tick view, once Lane E wires
    that) into one kind-dispatch registry — nothing here is registered in
    ``app.py`` (Wave-1 WOs never touch it).

    :param view: The projected social-class dossier this provider serves.
    :returns: A callable resolving rows for the one subject
        ``f"social_class/{view.class_id}"`` and ``None`` for anything else.
    """
    subject = f"social_class/{view.class_id}"

    def _provider(candidate: str) -> list[tuple[str, str]] | None:
        if candidate != subject:
            return None
        rows: list[tuple[str, str]] = []
        if view.role is not None:
            rows.append(("role", view.role.value))
        if view.county_fips:
            rows.append(("county_fips", view.county_fips))
        if view.population is not None:
            rows.append(("population", str(view.population)))
        if view.wealth is not None:
            rows.append(("wealth", f"{view.wealth:.6f}"))
        if view.p_acquiescence is not None:
            rows.append(("p_acquiescence", f"{view.p_acquiescence:.6f}"))
        if view.p_revolution is not None:
            rows.append(("p_revolution", f"{view.p_revolution:.6f}"))
        return rows

    return _provider
