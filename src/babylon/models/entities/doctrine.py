"""Doctrine Tree entity models (Epoch 3, Wave 6 foundation — Phase 0).

Defines the frozen data shape of the MVP Doctrine Tree: 3 trunks (reformist,
scientific, insurrectionist), 3 tags (CLASS_ANALYSIS, MASS_LINK, MILITANCY),
11 nodes. Source of truth for the content itself is
``ai/epochs/epoch3/doctrine-tree-mvp.yaml``, transcribed into
``babylon/data/game/doctrine_tree_mvp.json`` and loaded via
:func:`babylon.domain.doctrine.loader.load_doctrine_tree`.

This module is data-only (Phase 0): no engine wiring, no trap-condition
evaluator, no tick integration. ``trap_condition`` is stored verbatim as the
raw expression string from the corpus (e.g. ``"CLASS_ANALYSIS <= 0 AND
MILITANCY <= 0"``); parsing/evaluating it is explicitly out of scope and
depends on owner rulings for the gated engine system.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums.doctrine import DoctrineTag, DoctrineTrunk


class DoctrineNode(BaseModel):
    """A single node in the Doctrine Tree (one row of the MVP corpus).

    Frozen and immutable. Faithful transcription target for each YAML node
    entry under ``mvp_doctrine_tree.nodes`` in
    ``ai/epochs/epoch3/doctrine-tree-mvp.yaml``.

    Attributes:
        id: Unique node identifier (matches the YAML key, e.g.
            ``"class_consciousness"``).
        name: Human-readable display name.
        tier: Depth in the tree, 0 for the root. Strictly increases along
            every parent-to-child edge.
        parents: Parent node ids. Empty only for the root node.
        description: One-line flavor/mechanical description.
        tag_deltas: Signed per-tag contribution applied when this node is
            acquired. This MERGES the YAML's ``provides_tags`` (positive)
            and ``provides_tags_negative`` (negative) maps into one signed
            dict, since no MVP node has overlapping keys between the two.
        cost_tl: Theoretical Labor cost to acquire this node. ``0`` for the
            root (free starting node) and for trap nodes (fallen into, not
            purchased).
        trunk: Which of the 3 strategic trunks this node belongs to.
            ``None`` for the root and the shared tier-1 node
            (``trade_unionism``), which precede the branch split.
        unlocks: Node ids this node makes available once acquired. Empty
            for leaf nodes (traps and the goal).
        warning: Optional player-facing warning about where a path leads.
        is_trap: Whether this is a terminal trap ending.
        trap_condition: Raw trap-trigger expression string, verbatim from
            the corpus (e.g. ``"MASS_LINK <= 0"``). Not parsed or
            evaluated at this layer — Phase 0 stores it only.
        narrative: Flavor prose shown on reaching this node: the corpus's
            ``trap_narrative`` for trap nodes, or ``victory_bonus`` for the
            goal node. ``None`` for ordinary intermediate nodes.
        is_goal: Whether this is the victory-condition leaf
            (``united_front`` in the MVP).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        min_length=1,
        description="Unique node identifier",
    )
    name: str = Field(
        min_length=1,
        description="Human-readable display name",
    )
    tier: int = Field(
        ge=0,
        description="Depth in the tree, 0 for the root",
    )
    parents: tuple[str, ...] = Field(
        default=(),
        description="Parent node ids; empty only for the root",
    )
    description: str = Field(
        min_length=1,
        description="One-line flavor/mechanical description",
    )
    tag_deltas: Mapping[DoctrineTag, int] = Field(
        default_factory=dict,
        description=(
            "Signed per-tag contribution when acquired "
            "(merged provides_tags + provides_tags_negative)"
        ),
    )
    cost_tl: int = Field(
        ge=0,
        description="Theoretical Labor cost to acquire this node",
    )
    trunk: DoctrineTrunk | None = Field(
        default=None,
        description="Strategic trunk this node belongs to, if any",
    )
    unlocks: tuple[str, ...] = Field(
        default=(),
        description="Node ids this node makes available once acquired",
    )
    warning: str | None = Field(
        default=None,
        description="Optional player-facing warning about where a path leads",
    )
    is_trap: bool = Field(
        default=False,
        description="Whether this is a terminal trap ending",
    )
    trap_condition: str | None = Field(
        default=None,
        description="Raw trap-trigger expression string, verbatim from the corpus",
    )
    narrative: str | None = Field(
        default=None,
        description="Trap_narrative or victory_bonus flavor prose, if any",
    )
    is_goal: bool = Field(
        default=False,
        description="Whether this is the victory-condition leaf",
    )


class DoctrineTree(BaseModel):
    """The full Doctrine Tree: a DAG of :class:`DoctrineNode` instances.

    Frozen and immutable. Structural validity (single root, no cycles,
    monotonic tiers, referential integrity, trap/goal invariants) is NOT
    self-enforced here — see
    :func:`babylon.domain.doctrine.validation.validate_doctrine_tree`, which
    operates on an already-constructed tree so validation stays out of the
    ``models`` layer per the repository's layering rule (``models`` may not
    import ``domain``).

    Attributes:
        nodes: All nodes in the tree, keyed by ``id``.
        root_id: The id of the root node (empty ``parents``, ``cost_tl``
            ``0``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: Mapping[str, DoctrineNode] = Field(
        description="All nodes in the tree, keyed by id",
    )
    root_id: str = Field(
        min_length=1,
        description="The id of the root node",
    )

    def node(self, node_id: str) -> DoctrineNode:
        """Look up a node by id.

        Args:
            node_id: The node id to look up.

        Returns:
            The matching :class:`DoctrineNode`.

        Raises:
            KeyError: If ``node_id`` is not present in :attr:`nodes`.
        """
        return self.nodes[node_id]

    def children_of(self, node_id: str) -> tuple[str, ...]:
        """Return the ids of nodes whose ``parents`` include ``node_id``.

        Computed from each node's declared ``parents`` (the canonical
        backward edge), not from the denormalized ``unlocks`` field.

        Args:
            node_id: The parent node id.

        Returns:
            A sorted tuple of child node ids (empty for leaves).
        """
        return tuple(sorted(child.id for child in self.nodes.values() if node_id in child.parents))


__all__ = [
    "DoctrineNode",
    "DoctrineTree",
]
