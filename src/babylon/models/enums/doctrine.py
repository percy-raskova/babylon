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
        REFORMIST: The Electoral Question — since P25 U11 (ADR137) a fork of
            five stances under ``trade_unionism`` (Principled Abstention/Boycott,
            Class-Struggle Elections, Entryism, Independent Ballot Line, the
            Governance Road); ``liquidationism`` is its "too legal" fate, no
            longer a purchasable terminal but a MEASURED absorbing state.
        SCIENTIFIC: Democratic-centralist/mass-line path; the balanced,
            correct line (terminates at the ``united_front`` goal).
        INSURRECTIONIST: Armed-vanguard/urban-guerrilla path; the "too
            militant" trap (terminates at ``adventurism``).
    """

    REFORMIST = "reformist"
    SCIENTIFIC = "scientific"
    INSURRECTIONIST = "insurrectionist"


class PracticeVariable(StrEnum):
    """Measured-practice quantities the ``trap_condition`` DSL resolves alongside
    :class:`DoctrineTag` (P25 U11, ADR137, the-electoral-question.md §3.1).

    A namespace DISTINCT from ``DoctrineTag`` — the charter's "do NOT fake
    pseudo-tags" rule. These are I-FRESH quantities read from an org's material
    position each tick, NEVER accumulated into the ``doctrine_tags`` field. The
    re-founded reformist trunk's traps (liquidationism as an absorbing state)
    are gated on measured practice, not punitive static ``tag_deltas``.

    Values:
        SOLIDARITY_MASS: Weighted SOLIDARITY out-edge density of the org — its
            autonomous mass base (the P(S|R) numerator's raw material).
        CO_OPTIVE_SHARE: CO_OPTIVE in-edge weight as a share of total incident
            tie weight — dependence on concessions-for-quiescence.
        OFFICE_TENURE: Accumulated tenure-ticks in office, normalized — the
            officeholder-capture (``institutional_pull``) driver.
        DELIVERY_DEPENDENCE: The governing org's delivery gap (promised minus
            delivered), from the one-tick-stale ``policy_delivery`` register.
        PETTY_BOURGEOIS_DRIFT: The petty-bourgeois share of the org's
            MEMBERSHIP-weighted class base — a CONTINUOUS material proxy, never
            the discrete ``class_character`` label (Aleksandrov Test).
    """

    SOLIDARITY_MASS = "solidarity_mass"
    CO_OPTIVE_SHARE = "co_optive_share"
    OFFICE_TENURE = "office_tenure"
    DELIVERY_DEPENDENCE = "delivery_dependence"
    PETTY_BOURGEOIS_DRIFT = "petty_bourgeois_drift"


__all__ = [
    "DoctrineTag",
    "DoctrineTrunk",
    "PracticeVariable",
]
