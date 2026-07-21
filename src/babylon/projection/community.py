"""The community/hyperedge read-model — ``project_community`` (WO-24).

Assembles a :class:`~babylon.projection.view_models.CommunityView` dossier
for one fixed :class:`~babylon.models.enums.CommunityType` from the post-tick
world. Transport-neutral by construction — no Django, no engine imports, no
database connection; callers hand in the world they already hold.

**Community is never a graph node** (Constitution II.7; MEMORY
hex/community Lawverian disposition — the live-armed invariant
``NoCommunityFanOut`` INV-010, ``src/babylon/engine/invariants.py``, fails
the tick if a MEMBERSHIP edge's source is a ``community`` node). A community
is instead an XGI hyperedge whose members are ``SocialClass`` entities each
carrying a ``community_memberships`` list (``models/entities/social_class.py``,
Feature 022) — this module reads that entity-level data directly, mirroring
the shape (not the code — ``babylon.engine.systems.community`` is an engine
module and the projection layer does not import the engine) of the engine's
own ``CommunitySystem._collect_memberships``.

**Signature note (departs from the county+nesting recipe):** every other
Lane P WO's ``project_<kind>`` accepts ``(id, *, graph, world, tick)``; this
one accepts only ``(community_id, *, world, tick)``. There is no graph-sourced
field to read — community truly has no graph-node representation, so a
``graph`` parameter would be dead weight (and an unused-argument lint
failure, ``ARG001`` is enabled repo-wide). This is the literal expression of
"community is never a graph node," not an oversight.

**No producer exists today (documented, not a bug):** no scenario builder in
this codebase ever populates ``SocialClass.community_memberships`` —
``CommunitySystem.step`` (``engine/systems/community.py``) is a structural
no-op every tick because ``services.community_hypergraph`` is never wired by
any scenario, and the seam registry
(``src/babylon/sentinels/seam/registry.py:1969-1991``) marks the
``community_memberships`` payload ``STRUCTURALLY_IMPOSSIBLE`` for exactly
this reason. ``ooda/initiative.py::compute_community_embeddedness`` documents
the same fact and reads the real substrate shape anyway "so the score becomes
live the moment a producer exists" — this module follows the same discipline:
the code below is the real, correct read of the declared field, honestly
returning ``None`` today because the field is honestly always empty today,
never a fabricated placeholder roster.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``roster``
     - Sorted ``SocialClass.id`` values (``models/entities/social_class.py``)
       for every **active** entity whose ``community_memberships`` contains
       an entry matching the queried ``community_id``. ``None`` when no
       entity is currently attributed — never an empty tuple (an empty
       tuple is reserved for :attr:`~babylon.projection.view_models.
       CommunityView.overlaps`' distinct "computed, found none" case).
   * - ``formation_tick``
     - **No producer of any kind.** Neither
       :class:`~babylon.models.entities.community.CommunityState` nor
       :class:`~babylon.models.entities.community.CommunityMembership`
       declares a timestamp field — a ``CommunityType`` is one of 14 fixed
       members assigned a category at import time
       (``COMMUNITY_CATEGORY_MAP``), not a hyperedge instantiated at a
       tick. Always ``None``.
   * - ``overlaps``
     - Derived from the same ``community_memberships`` read as ``roster``:
       for every roster member, every *other* ``CommunityType`` they also
       belong to, counted and sorted by that other type. ``None`` exactly
       when ``roster`` is ``None``; an attributed roster with zero
       cross-community members projects an empty tuple.

Absence discipline (Constitution III.11): an unattributed community projects
``roster``/``overlaps`` as ``None`` — never a fabricated empty-looking-active
roster. A ``community_id`` that is not a real
:class:`~babylon.models.enums.CommunityType` member is a *caller* error
(loud ``pydantic.ValidationError`` via :class:`CommunityType`'s own
construction), never absence — absence is about missing *data*, not an
unrecognized *identity*.

Amendment D (read-only, Constitution II.7 transition state): this module
only reads and projects hyperedge membership; it defines no mutation
affordance, and the vault page/template built from its output carries none
either (design-canon S9: "hyperedge rendering is read-only presentation and
safe").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.entities.community import CommunityMembership
from babylon.models.enums import CommunityType
from babylon.projection.view_models import CommunityOverlap, CommunityView

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState

__all__ = ["project_community"]


def _memberships_of(entity: Any) -> tuple[CommunityMembership, ...]:
    """Normalize one entity's ``community_memberships`` into typed objects.

    ``SocialClass.community_memberships`` is declared ``list[Any]`` (Feature
    022) because it holds either already-hydrated
    :class:`~babylon.models.entities.community.CommunityMembership`
    instances (a directly-constructed ``SocialClass``, as in this module's
    own tests) or plain dicts (whenever the entity round-tripped through a
    graph — ``WorldState.to_graph()``/``from_graph()`` carries entity fields
    through ``model_dump()``, which flattens nested Pydantic models to
    dicts). Both shapes must be accepted for the field to mean anything.

    :param entity: A ``SocialClass``-shaped object (structurally typed here
        as ``Any`` rather than imported, to avoid a hard dependency this
        module does not otherwise need).
    :returns: The entity's memberships as a tuple of
        :class:`~babylon.models.entities.community.CommunityMembership`.
    :raises pydantic.ValidationError: if a dict-shaped entry does not hydrate
        to a valid ``CommunityMembership`` — a malformed entry is a loud
        failure, never silently skipped.
    """
    raw = getattr(entity, "community_memberships", None) or ()
    result: list[CommunityMembership] = []
    for item in raw:
        if isinstance(item, CommunityMembership):
            result.append(item)
        else:
            result.append(CommunityMembership(**item))
    return tuple(result)


def project_community(
    community_id: str,
    *,
    world: WorldState,
    tick: int,
) -> CommunityView:
    """Project one community's post-tick membership into a :class:`CommunityView`.

    :param community_id: The :class:`~babylon.models.enums.CommunityType`
        value identifying the community (e.g. ``"settler"``).
    :param world: The committed post-tick world state (entity collection).
    :param tick: The committed tick this dossier is projected from — becomes
        the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated community dossier.
    :raises pydantic.ValidationError: if ``community_id`` is not a real
        :class:`~babylon.models.enums.CommunityType` member (a caller error,
        not absence), or if a present-but-malformed membership entry fails
        to hydrate.
    """
    target = CommunityType(community_id)

    agent_communities: dict[str, set[CommunityType]] = {}
    for entity in world.entities.values():
        if not getattr(entity, "active", True):
            continue
        memberships = _memberships_of(entity)
        if not memberships:
            continue
        agent_communities[entity.id] = {membership.community_type for membership in memberships}

    members = sorted(agent_id for agent_id, types in agent_communities.items() if target in types)
    if not members:
        return CommunityView(community_id=target, verified_tick=tick)

    overlap_counts: dict[CommunityType, int] = {}
    for agent_id in members:
        for other in agent_communities[agent_id]:
            if other == target:
                continue
            overlap_counts[other] = overlap_counts.get(other, 0) + 1

    overlaps = tuple(
        CommunityOverlap(community_id=other, shared_member_count=count)
        for other, count in sorted(overlap_counts.items())
    )

    return CommunityView(
        community_id=target,
        verified_tick=tick,
        roster=tuple(members),
        overlaps=overlaps,
    )
