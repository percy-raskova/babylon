"""The Levi/bipartite ego-tree ordering provider (WO-31, Lane T).

Design canon R8 ("hypergraph shapes must render in the terminal ... the
structures from the planned xgi Rust port (``hypergraph-rs``) need
terminal-native visual idioms") and S9 ("Levi/bipartite ego-trees — matching
hypergraph-rs's internal bipartite representation — the visualization walks
the storage structure"). A Levi graph represents a hypergraph as an ordinary
bipartite graph: one node class for the hypergraph's original nodes, a
second node class for its hyperedges, with an edge wherever a node belongs to
an edge. Here the two classes are concrete: **member** ids (``SocialClass``
agents, e.g. ``"C001"``) on one side, **community** ids
(:class:`~babylon.models.enums.CommunityType` values, e.g. ``"settler"``) on
the other — exactly the two node classes
:mod:`babylon.projection.community` already reads, never a graph node itself
(Constitution II.7; MEMORY hex/community Lawverian disposition).

**Interim provider, by design:** this module does not import
:mod:`babylon.projection.community` — that module's ``_memberships_of``
helper is a private implementation detail of WO-24's single-community
dossier (:func:`~babylon.projection.community.project_community`), not a
declared shared seam, and re-deriving the same small, honest read here (the
storage structure IS the bipartite graph; S9 says walk it, not a cache of
it) keeps this WO collision-free with a already-landed sibling WO's file.
Both modules independently mirror the same source-of-truth read: every
active entity's ``community_memberships`` list (Feature 022,
``models/entities/social_class.py``).

**Amendment D (read-only):** this module only reads and orders bipartite
membership; it defines no mutation affordance, matching every other Lane T
provider (PAOH, incidence/adjacency, map-room choropleth).

**No producer exists today (documented, not a bug):** as
:mod:`babylon.projection.community` documents, no scenario in this codebase
populates ``SocialClass.community_memberships`` — ``CommunitySystem.step``
is a structural no-op. :func:`levi_ego_tree` therefore honestly returns
``None`` for every real member/community id today (an attributed root with
zero edges), never a fabricated single-node tree; the code is the real,
correct read of the declared field, ready the moment a producer lands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.entities.community import CommunityMembership
from babylon.models.enums import CommunityType

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState

__all__ = ["LeviSide", "LeviNode", "LeviEgoTree", "levi_ego_tree"]

LeviSide = Literal["member", "community"]
"""Which of the Levi graph's two node classes an ego-tree's root sits on."""


class LeviNode(BaseModel):
    """One bipartite neighbor at ego-tree depth 1, with its own depth-2 fan-out.

    :param node_id: The neighbor's id — a
        :class:`~babylon.models.enums.CommunityType` value when
        :attr:`LeviEgoTree.root_side` is ``"member"``, or a member agent id
        when :attr:`LeviEgoTree.root_side` is ``"community"``.
    :param neighbors: This neighbor's own opposite-side neighbors — i.e.
        back on the root's own side — sorted, excluding the ego-tree's root
        itself (a bipartite graph has no edges within one side, and the root
        is not counted among its own depth-2 fan-out). May be empty: an
        attributed neighbor sharing zero further edges with anything else is
        a computed fact, not an absence (mirrors
        :attr:`~babylon.projection.view_models.CommunityView.overlaps`'
        empty-tuple-vs-``None`` discipline).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1)
    neighbors: tuple[str, ...] = ()


class LeviEgoTree(BaseModel):
    """A depth-2 bipartite ego-tree rooted at one member or community node.

    Depth is fixed at 2 (root -> children -> grandchildren) by construction,
    not merely by convention: the Levi graph has exactly two node classes, so
    a third hop from the grandchildren would only revisit the child class
    already enumerated at depth 1 — the bipartite structure itself statically
    bounds the walk (Power-of-10 rule 2: no loop here can iterate more than
    twice, by the shape of the data, not by a counter that could be raised).

    :param kind: The discriminator string, always ``"levi_ego_tree"`` — this
        record is not (yet) part of :data:`~babylon.projection.view_models.ProjectionRecord`
        (Lane T topology surfaces are read-only orderings feeding a directive,
        not a Lane P dossier page kind), but carries a stable literal anyway
        for forward compatibility with any future registry widening.
    :param root_id: The id the tree is rooted at, as given by the caller.
    :param root_side: Which Levi node class :attr:`root_id` belongs to.
    :param children: The root's immediate bipartite neighbors (opposite side
        from :attr:`root_side`), sorted by :attr:`LeviNode.node_id`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["levi_ego_tree"] = "levi_ego_tree"
    root_id: str = Field(min_length=1)
    root_side: LeviSide
    children: tuple[LeviNode, ...] = ()


def _active_memberships_by_agent(world: WorldState) -> dict[str, tuple[CommunityType, ...]]:
    """Walk every ACTIVE entity's ``community_memberships`` into a sorted map.

    Inactive entities are excluded (mirrors
    ``CommunitySystem._collect_memberships``'s own
    ``if not node.attributes.get("active", True): continue`` filter, and
    :func:`~babylon.projection.community.project_community`'s identical
    choice) — an inactive entity contributes no bipartite edges, though it
    may still exist as a known id (see :func:`levi_ego_tree`'s member-side
    absence-vs-error distinction).

    :param world: The committed world state (entity collection) to walk.
    :returns: A map from every active entity's id to its sorted
        :class:`~babylon.models.enums.CommunityType` memberships (empty
        tuple if the entity has none) — never omits an active entity, even
        one contributing zero edges, so callers can distinguish "known,
        zero edges" from "not a known entity at all."
    """
    result: dict[str, tuple[CommunityType, ...]] = {}
    for entity in world.entities.values():
        if not getattr(entity, "active", True):
            continue
        raw = getattr(entity, "community_memberships", None) or ()
        types: set[CommunityType] = set()
        for item in raw:
            if isinstance(item, CommunityMembership):
                types.add(item.community_type)
            else:
                types.add(CommunityMembership(**item).community_type)
        result[entity.id] = tuple(sorted(types))
    return result


def levi_ego_tree(root_id: str, *, world: WorldState) -> LeviEgoTree | None:
    """Project a depth-2 bipartite ego-tree rooted at ``root_id``.

    Precedence when ``root_id`` could conceivably be read either way: a
    :class:`~babylon.models.enums.CommunityType` value is checked first. In
    practice this never collides with a real member id — member ids follow
    the ``C[0-9]{3,}`` shape (mirrors
    :attr:`~babylon.projection.view_models.SocialClassView.class_id`'s own
    pattern) and the 14 ``CommunityType`` values are lowercase words — but the
    precedence is fixed and documented rather than left to accident.

    :param root_id: Either a member agent id or a
        :class:`~babylon.models.enums.CommunityType` value.
    :param world: The committed world state (entity collection) to walk.
    :raises ValueError: if ``root_id`` is neither a recognized
        ``CommunityType`` value nor a known entity id in ``world.entities``
        — an unrecognized *identity* is a caller error (mirrors
        ``project_community``'s own ``TestLoudFailure`` discipline), never
        absence.
    :returns: The ego-tree, or ``None`` if ``root_id`` is a recognized
        identity that currently has zero bipartite edges — an inactive
        entity, an entity with no ``community_memberships``, or a
        ``CommunityType`` with an empty roster (honest absence, III.11 —
        never a fabricated single-node tree). Community rosters and member
        membership sets are always non-empty when returned (an empty
        collection would itself have produced ``None`` instead), so
        :attr:`LeviEgoTree.children` is never empty on a non-``None`` return.
    """
    by_agent = _active_memberships_by_agent(world)

    if root_id in set(CommunityType):
        target = CommunityType(root_id)
        members = sorted(agent for agent, types in by_agent.items() if target in types)
        if not members:
            return None
        children = tuple(
            LeviNode(
                node_id=member,
                neighbors=tuple(t.value for t in by_agent[member] if t != target),
            )
            for member in members
        )
        return LeviEgoTree(root_id=root_id, root_side="community", children=children)

    if root_id not in world.entities:
        raise ValueError(f"{root_id!r} is neither a CommunityType value nor a known entity id")

    my_types = by_agent.get(root_id, ())
    if not my_types:
        return None
    children = tuple(
        LeviNode(
            node_id=community_type.value,
            neighbors=tuple(
                sorted(
                    agent
                    for agent, types in by_agent.items()
                    if community_type in types and agent != root_id
                )
            ),
        )
        for community_type in my_types
    )
    return LeviEgoTree(root_id=root_id, root_side="member", children=children)
