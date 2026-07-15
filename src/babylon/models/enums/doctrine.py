"""Doctrine Tree tag and trunk enums (Epoch 3, Wave 6 foundation).

Data source: ``ai/epochs/epoch3/doctrine-tree-mvp.yaml`` (SPEC_COMPLETE
3-trunk / 3-tag / 11-node MVP). This module defines the closed vocabularies
only; the tree structure itself lives in
``babylon.models.entities.doctrine`` and the data file
``babylon/data/game/doctrine_tree_mvp.json``.
"""

from __future__ import annotations

from enum import StrEnum


class DoctrineTag(StrEnum):
    """Doctrine tag tracked by the MVP Doctrine Tree (3 tags only).

    Each tag ranges over ``[0, 10]`` and is recomputed from the sum of
    ``tag_deltas`` across all acquired :class:`~babylon.models.entities.doctrine.DoctrineNode`
    instances, clamped to the range (see
    :func:`babylon.domain.doctrine.tags.compute_tags`).

    Values:
        CLASS_ANALYSIS: Clarity of materialist class analysis. High =
            correct prioritization, theory bonus. Low = confused
            strategy, opens traps.
        MASS_LINK: Connection to the broad masses. High = faster
            sympathizer generation, legitimacy. Low = isolated, actions
            seen as terrorism.
        MILITANCY: Capacity for militant action. High = can execute
            kinetic actions, deterrence. Low = cannot use force, purely
            defensive.
    """

    CLASS_ANALYSIS = "class_analysis"
    MASS_LINK = "mass_link"
    MILITANCY = "militancy"


class DoctrineTrunk(StrEnum):
    """The three strategic trunks of the MVP Doctrine Tree.

    Values:
        REFORMIST: Electoral/coalition path; the "too legal" trap
            (terminates at ``liquidationism``).
        SCIENTIFIC: Democratic-centralist/mass-line path; the balanced,
            correct line (terminates at the ``united_front`` goal).
        INSURRECTIONIST: Armed-vanguard/urban-guerrilla path; the "too
            militant" trap (terminates at ``adventurism``).
    """

    REFORMIST = "reformist"
    SCIENTIFIC = "scientific"
    INSURRECTIONIST = "insurrectionist"


__all__ = [
    "DoctrineTag",
    "DoctrineTrunk",
]
