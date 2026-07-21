"""The institution read-model — ``project_institution`` (Program 24 P2 WO-19).

Assembles a :class:`~babylon.projection.view_models.InstitutionView` dossier
from the post-tick graph. Transport-neutral by construction — no Django, no
engine imports, no database connection; the caller hands in the graph it
already holds. Unlike :func:`~babylon.projection.county.project_county`
(which aggregates several declared sources into one dossier), an institution
is a *single graph node*: ``WorldState.to_graph()`` stamps every
``Institution`` Pydantic model field (Feature 040) whole-cloth onto its node,
so this projection has exactly one producer per field and needs no
``WorldState`` at all — it reads the graph directly, sidestepping the
``from_graph()`` computed-field-drop gotcha the same way ``project_county``
does for territory attributes.

**One producer per field** (the WO-3 ruling the charter requires):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``name``, ``apparatus_type``, ``social_function``, ``class_inscription``,
       ``legitimacy``, ``budget``, ``housed_org_ids``, ``territory_ids``
     - The institution's own graph node attribute of the same name — written
       whole-cloth by ``WorldState.to_graph()`` from the ``Institution``
       model (``inst.model_dump()``, ``models/world_state.py``).
   * - ``factional_composition``
     - The node's ``internal_balance`` attribute, projecting only the three
       named ruling-class-fraction weights (``liberal_technocratic``,
       ``revanchist_fascist``, ``institutionalist_bonapartist``) — mirrors
       the legacy ``_institution_factional_control``/``InstitutionSerializer.
       factional_composition`` contract (``web/game/engine_bridge.py``,
       ``web/game/serializers.py``). The computed ``hegemonic_fraction`` and
       the ``internal_contestation`` weight are NOT projected (see
       :class:`~babylon.projection.view_models.FactionalComposition`).

Absence discipline (Constitution III.11): when no institution node carries
the requested id, every field beyond identity/provenance projects as
``None`` — never a fabricated default (in particular, never the legacy
web bridge's "all-zero factional weights" fallback, which is itself a
disclosed anti-pattern this projection deliberately does not reproduce).
When a node IS found, every ``Institution`` field is present by
construction (the model has no field the engine can omit); a present-but-
malformed ``internal_balance`` (e.g. a dict missing a named weight) is a
shape bug that fails loud via :class:`~babylon.projection.view_models.
FactionalComposition`'s own validation — never silently defaulted.

**Honest producer-absence note (vocabulary sentinel discipline):** ``
_node_type="institution"`` IS a real, production-stamped graph vocabulary
member (``models/enums/topology.py``, ``WorldState.to_graph()`` /
``from_graph()`` both handle it, Feature 040 tests construct real
``Institution`` instances) — this is NOT an invented type. What is
genuinely absent today is a *scenario* that populates ``WorldState.
institutions``: neither ``create_single_county_scenario`` nor any other
``src/babylon/engine/scenarios/*.py`` builder, nor any ``_DEFAULT_SYSTEMS``
system, ever constructs an ``Institution`` or writes an institution node
(confirmed by grep: zero ``Institution(`` call sites under
``src/babylon/engine/``). ``tools/record_institution_fixture.py`` drives the
real ``single_county`` scenario exactly like the WO-6 county harvester and
records the *honest result*: an all-absent dossier, because that scenario
seeds zero institutions. This module's unit tests instead construct a
graph directly (mirroring ``test_county.py``'s own in-test
``BabylonGraph()`` fixtures) to exercise the full-dossier and loud-failure
paths no current scenario can produce.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from babylon.models.enums.topology import NodeType
from babylon.projection.vault.render_institution import _statblock_rows
from babylon.projection.view_models import FactionalComposition, InstitutionView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.tui.directives import StatblockProvider, StatblockRow

__all__ = ["project_institution", "institution_statblocks"]


def _resolve_institution(graph: GraphProtocol, institution_id: str) -> GraphNode | None:
    """Find the institution node carrying ``institution_id``, if any.

    :param graph: The post-tick graph.
    :param institution_id: The institution's graph node id.
    :returns: The matching node, or ``None`` when no institution node carries
        that id (either the id is entirely unknown, or it names a
        differently-typed node — both are honest absence, never a crash).
    """
    node = graph.get_node(institution_id)
    if node is None or node.node_type != NodeType.INSTITUTION:
        return None
    return node


def _factional_composition(attrs: Mapping[str, Any]) -> FactionalComposition | None:
    """Project the node's ``internal_balance`` attribute to a composition.

    :param attrs: The institution node's attribute mapping.
    :returns: The three-weight :class:`FactionalComposition`, or ``None`` if
        the node carries no ``internal_balance`` attribute at all.
    :raises pydantic.ValidationError: if ``internal_balance`` is present but
        missing one of the three named weights, or a weight is out of
        ``[0, 1]`` range, or the three weights do not sum to one within
        tolerance — a present-but-malformed value fails loud (never
        defaulted to zero, unlike the legacy web-bridge fallback this
        deliberately does not reproduce).
    """
    balance = attrs.get("internal_balance")
    if balance is None:
        return None
    return FactionalComposition(
        liberal_technocratic=balance.get("liberal_technocratic"),
        revanchist_fascist=balance.get("revanchist_fascist"),
        institutionalist_bonapartist=balance.get("institutionalist_bonapartist"),
    )


def _as_id_tuple(value: Any) -> tuple[str, ...] | None:
    """Project a node's id-list attribute to an immutable tuple, or ``None``.

    :param value: The raw attribute value (a list of ids, or absent).
    :returns: A tuple of the ids in their stored order, or ``None`` if the
        attribute is entirely absent from the node. An empty list projects
        to an empty tuple — a real "houses/operates in nothing" value,
        distinct from absence.
    """
    if value is None:
        return None
    return tuple(value)


def project_institution(
    institution_id: str,
    *,
    graph: GraphProtocol,
    tick: int,
) -> InstitutionView:
    """Project one institution's post-tick state into an :class:`InstitutionView`.

    Read strictly *post-tick*, matching :func:`~babylon.projection.county.
    project_county`'s discipline: systems mutate the shared graph in-place in
    strict order, so a mid-tick read would see a partially-applied world.

    :param institution_id: The institution's graph node id.
    :param graph: The committed post-tick graph.
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated institution dossier. Every field is
        ``None`` when no institution node carries ``institution_id``.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    node = _resolve_institution(graph, institution_id)
    if node is None:
        return InstitutionView(institution_id=institution_id, verified_tick=tick)

    attrs = node.attributes
    return InstitutionView(
        institution_id=institution_id,
        verified_tick=tick,
        name=attrs.get("name"),
        apparatus_type=attrs.get("apparatus_type"),
        social_function=attrs.get("social_function"),
        class_inscription=attrs.get("class_inscription"),
        legitimacy=attrs.get("legitimacy"),
        budget=attrs.get("budget"),
        housed_org_ids=_as_id_tuple(attrs.get("housed_org_ids")),
        territory_ids=_as_id_tuple(attrs.get("territory_ids")),
        factional_composition=_factional_composition(attrs),
    )


def institution_statblocks(views: Mapping[str, InstitutionView]) -> StatblockProvider:
    """Build a live :data:`~babylon.tui.directives.StatblockProvider` for institutions.

    The Wave-1 "per-kind statblock provider function inside their own
    module" the shared-file discipline requires (``specs/24-archive/
    work-orders-p2-p4.md``): registers nothing in ``tui/app.py`` (that
    composition is Wave-2 WO-45's job). Reuses the exact same row-formatting
    logic :func:`~babylon.projection.vault.render_institution.render_institution`
    bakes into a page, so a live statblock and a baked one never drift.

    :param views: A mapping of subject id (``"institution/<id>"``) to its
        already-projected :class:`~babylon.projection.view_models.
        InstitutionView` — fixture-backed until a live wiring lands.
    :returns: A provider resolving a known subject to its statblock rows
        (possibly an empty sequence, for an honestly all-absent view) and
        ``None`` for any subject not in ``views``.
    """

    def provider(subject: str) -> Sequence[StatblockRow] | None:
        view = views.get(subject)
        if view is None:
            return None
        return _statblock_rows(view)

    return provider
