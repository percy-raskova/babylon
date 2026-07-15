"""Pure tag computation for the Doctrine Tree (Phase 0 foundation).

Implements the MVP tag-calculation formula from
``ai/epochs/epoch3/doctrine-tree-mvp.yaml`` (``mvp_mechanics.tag_calculation``):
for each tag, sum ``tag_deltas`` across all acquired nodes and clamp to
``[0, 10]``. Pure functions only — no engine state, no trap-condition
evaluation (that remains a raw string on
:class:`~babylon.models.entities.doctrine.DoctrineNode`, gated engine work).
"""

from __future__ import annotations

from collections.abc import Iterable

from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.enums.doctrine import DoctrineTag

_TAG_MIN = 0
_TAG_MAX = 10

# Corpus reference: ai/epochs/epoch3/doctrine-tree-mvp.yaml, mvp_tags section
# (lines ~59-85), each tag's `starting_value`. This is standalone reference
# data describing the tag state before any doctrine is acquired -- it is
# NOT added on top of compute_tags' sum-over-acquired-nodes formula (the
# yaml's own worked example sums provides_tags across acquired nodes only,
# with no separate starting-value term; see test_doctrine_tags.py).
_STARTING_TAG_VALUES: dict[DoctrineTag, int] = {
    DoctrineTag.CLASS_ANALYSIS: 1,
    DoctrineTag.MASS_LINK: 1,
    DoctrineTag.MILITANCY: 0,
}


def compute_tags(tree: DoctrineTree, acquired_ids: Iterable[str]) -> dict[DoctrineTag, int]:
    """Compute all 3 doctrine tag values from a set of acquired nodes.

    For each tag, sums ``tag_deltas`` across every acquired node, then
    clamps the total to ``[0, 10]``. Pure and order-independent (matches
    the corpus formula, which sums positive and negative contributions
    before a single final clamp — not a running per-acquisition clamp).

    Args:
        tree: The Doctrine Tree the acquired ids belong to.
        acquired_ids: Ids of nodes the player has acquired.

    Returns:
        A dict with all 3 :class:`DoctrineTag` members as keys, each
        clamped to ``[0, 10]``.

    Raises:
        KeyError: If any id in ``acquired_ids`` is not a node in ``tree``.
    """
    totals: dict[DoctrineTag, int] = dict.fromkeys(DoctrineTag, 0)
    for node_id in acquired_ids:
        node = tree.nodes[node_id]
        for tag, delta in node.tag_deltas.items():
            totals[tag] += delta
    return {tag: max(_TAG_MIN, min(_TAG_MAX, value)) for tag, value in totals.items()}


def starting_tags() -> dict[DoctrineTag, int]:
    """Return the MVP tags' starting values, verbatim from the corpus.

    Returns:
        A dict with all 3 :class:`DoctrineTag` members as keys:
        ``CLASS_ANALYSIS=1``, ``MASS_LINK=1``, ``MILITANCY=0``.
    """
    return dict(_STARTING_TAG_VALUES)


__all__ = [
    "compute_tags",
    "starting_tags",
]
