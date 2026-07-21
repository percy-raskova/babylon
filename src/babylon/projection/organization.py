"""The organization read-model — ``project_organization`` (Program 24 P2 WO-18).

Assembles a :class:`~babylon.projection.view_models.OrganizationView` dossier
from the post-tick world: the ``organization`` graph node's attributes
(written once, wholesale, by ``WorldState.to_graph()`` — ``G.add_node(org_id,
_node_type=NodeType.ORGANIZATION, **org.model_dump())``). Mirrors
:mod:`babylon.projection.county` exactly: transport-neutral by construction —
no Django, no engine imports, no database connection; callers hand in the
graph and world they already hold.

**One producer per field.** Every declared field below reads the Organization
node's OWN attribute of the same name — there is only one producer because
``Organization`` (``babylon.models.entities.organization``) is written to the
graph wholesale via ``model_dump()`` at ``to_graph()`` time, not assembled
piecemeal the way a Territory's ``tick_*`` attrs are. As of this WO, no
:mod:`~babylon.engine.systems` module mutates any of these twelve fields
after construction (:mod:`~babylon.engine.systems.doctrine` mutates a
*different* set — ``acquired_doctrine_ids``/``theoretical_labor``/
``doctrine_tags``/``congress_tag_snapshot``/``study_target_id``, the Doctrine
Tree accumulator, out of scope for this dossier) — but the projection still
reads strictly post-tick, so a future write-back is picked up automatically
with no change here.

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``name``
     - ``Organization.name`` graph attribute.
   * - ``org_type``
     - ``Organization.org_type`` graph attribute (the subtype discriminator).
   * - ``class_character``
     - ``Organization.class_character`` graph attribute.
   * - ``legal_standing``
     - ``Organization.legal_standing`` graph attribute.
   * - ``budget``
     - ``Organization.budget`` graph attribute.
   * - ``territory_ids``
     - ``Organization.territory_ids`` graph attribute (a tuple, possibly
       empty — an org with zero territories is a real fact, not absence).
   * - ``headquarters_id``
     - ``Organization.headquarters_id`` graph attribute (``None`` is a
       legitimate model value, not just a missing-key sentinel).
   * - ``is_institution``
     - ``Organization.is_institution`` graph attribute.
   * - ``heat``
     - ``Organization.heat`` graph attribute.
   * - ``consciousness_tendency``
     - ``Organization.consciousness_tendency`` graph attribute.
   * - ``cohesion``
     - ``Organization.cohesion`` graph attribute.
   * - ``cadre_level``
     - ``Organization.cadre_level`` graph attribute.

**Fog field split (documented here, NOT wired — Lane E WO-41's job).** Track 1
/ Task 5 §B ruled an organization's *existence*, public activity, and
territorial presence are MATERIAL (public record, never gated), while its
*internal state* is POLITICAL for every non-player org — gated the same way
:data:`~babylon.projection.fog.filter.ORG_POLITICAL_FIELDS` gates the legacy
web bridge's org payload. :data:`POLITICAL_VIEW_FIELDS` names the four
declared fields that are members of that set (``heat``,
``consciousness_tendency``, ``cohesion``, ``cadre_level`` — the rest of
``ORG_POLITICAL_FIELDS`` belongs to territory/faction payload shapes this view
has no field for); :data:`MATERIAL_VIEW_FIELDS` names the remainder. This
module never calls :func:`~babylon.projection.fog.filter.apply_fog` — a live
caller gates the graph attributes (or the assembled view) before/after this
function runs; this WO's fixture ships already-gated (pre-gated) data,
exactly as WO-18 requires.

Absence discipline (Constitution III.11): an ``org_id`` that does not resolve
to a real ``organization`` node in *both* the graph and ``world.organizations``
projects every field ``None`` except identity/provenance — never a fabricated
default. **The ``single_county`` scenario seeds zero organizations** (its
``WorldState`` never populates ``organizations``), so the WO-18 committed
fixture (``tests/fixtures/projection/organization_org_rwp.json``) is the
honest-absence path end to end, exactly as the WO's no-producer contingency
anticipates — flagged here rather than silently shipping a fabricated
producer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from babylon.models.enums.topology import NodeType
from babylon.projection.view_models import OrganizationView

if TYPE_CHECKING:
    from collections.abc import Callable

    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode
    from babylon.models.world_state import WorldState
    from babylon.tui.directives import StatblockRow

__all__ = [
    "MATERIAL_VIEW_FIELDS",
    "POLITICAL_VIEW_FIELDS",
    "org_statblocks",
    "project_organization",
]

#: The declared :class:`OrganizationView` fields gated as political for every
#: non-player org (Track 1 / Task 5 §B) — a subset of
#: :data:`~babylon.projection.fog.filter.ORG_POLITICAL_FIELDS`. Documentation
#: only; see the module docstring's fog-field-split note. Not wired to
#: :func:`~babylon.projection.fog.filter.apply_fog` in this module.
POLITICAL_VIEW_FIELDS: Final[tuple[str, ...]] = (
    "heat",
    "consciousness_tendency",
    "cohesion",
    "cadre_level",
)

#: The declared :class:`OrganizationView` fields that stay material — never
#: gated — under the same ruling: existence, public activity, territorial
#: presence.
MATERIAL_VIEW_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "org_type",
    "class_character",
    "legal_standing",
    "budget",
    "territory_ids",
    "headquarters_id",
    "is_institution",
)


def _resolve_organization(graph: GraphProtocol, world: WorldState, org_id: str) -> GraphNode | None:
    """Find the ``organization`` node carrying ``org_id``, deterministically.

    Existence is cross-checked against *both* the graph and
    ``world.organizations`` — the committed
    :class:`~babylon.models.world_state.WorldState` is the run's entity
    roster (``WorldState.organizations``), while the graph carries the
    (currently graph-static, see the module docstring) attribute values.
    Callers always hand in a matched ``(graph, world)`` pair (``world``
    reconstructed from the same graph via ``WorldState.from_graph``), so this
    never masks a real node; it refuses to fabricate a dossier for a stray
    same-id node the world doesn't know about.

    :param graph: The post-tick graph.
    :param world: The committed post-tick world state.
    :param org_id: The organization's node/entity id.
    :returns: The matching graph node, or ``None`` when ``org_id`` is not a
        known organization in this run.
    """
    if org_id not in world.organizations:
        return None
    node = graph.get_node(org_id)
    if node is None or node.node_type != NodeType.ORGANIZATION.value:
        return None
    return node


def project_organization(
    org_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> OrganizationView:
    """Project one organization's post-tick state into an :class:`OrganizationView`.

    Read strictly *post-tick*: systems mutate the shared graph in-place in
    strict order, so a mid-tick read would see a partially-applied world.

    :param org_id: The organization's node/entity id (e.g. ``"org_rwp"``).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state (entity collection).
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated organization dossier. Every field is
        ``None`` when ``org_id`` names no known organization this run.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    node = _resolve_organization(graph, world, org_id)
    attrs: dict[str, Any] = dict(node.attributes) if node else {}

    territory_ids_raw = attrs.get("territory_ids")
    territory_ids: tuple[str, ...] | None = (
        tuple(territory_ids_raw) if territory_ids_raw is not None else None
    )

    return OrganizationView(
        org_id=org_id,
        verified_tick=tick,
        name=attrs.get("name"),
        org_type=attrs.get("org_type"),
        class_character=attrs.get("class_character"),
        legal_standing=attrs.get("legal_standing"),
        budget=attrs.get("budget"),
        territory_ids=territory_ids,
        headquarters_id=attrs.get("headquarters_id"),
        is_institution=attrs.get("is_institution"),
        heat=attrs.get("heat"),
        consciousness_tendency=attrs.get("consciousness_tendency"),
        cohesion=attrs.get("cohesion"),
        cadre_level=attrs.get("cadre_level"),
    )


def org_statblocks(view: OrganizationView) -> Callable[[str], list[StatblockRow] | None]:
    """Build a per-kind :data:`~babylon.tui.directives.StatblockProvider` closure.

    Shared-file discipline (Program 24 P2, WO-18): Wave-1 page WOs deliver a
    per-kind statblock provider *function inside their own module* and
    register nothing in ``tui/app.py`` — the single serial WO-45 composes
    every kind's provider into one dispatch table. This closure answers only
    for ``"organization/{view.org_id}"``; any other subject id is "no
    projection here" (``None``), which the fenced-directive dispatcher
    renders as an absence block rather than fabricating rows.

    :param view: The organization dossier this provider serves.
    :returns: A callable matching
        :data:`~babylon.tui.directives.StatblockProvider`.
    """
    subject = f"organization/{view.org_id}"

    def _provider(queried_subject: str) -> list[StatblockRow] | None:
        if queried_subject != subject:
            return None
        from babylon.projection.vault.render_organization import _statblock_rows

        return list(_statblock_rows(view))

    return _provider
