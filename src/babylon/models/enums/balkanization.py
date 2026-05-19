"""Spec-070 Balkanization enums (political topology + faction influence).

This module introduces the categorical types load-bearing for the
political-topology overlay (Constitution I.20): the ColonialStance axis,
the derived ExtractionPolicy, plus enums for sovereign classification,
fiscal and legal status on CLAIMS edges, support type on INFLUENCES
edges, and player interaction mode.

Cross-references:

- Constitution I.1 (Settler-Colonial Frame), I.20 (Spatial Substrate /
  Political Claims as Overlay).
- spec-070 data-model.md §1.1-1.7.

All values use lowercase snake_case for JSON serialization
compatibility, consistent with other ``babylon.models.enums.*`` modules.

Naming disambiguation (FR-045):

- ``ClaimLegalStatus`` is the spec-070 CLAIMS-edge legal nature enum
  (de_jure / de_facto / disputed / occupied / ceded). Distinct from
  :class:`babylon.models.enums.legal.LegalStatus`, which is the
  spec-022 community-repression escalation enum (legal / surveilled /
  designated_extremist / etc.). Both coexist; importers reference each
  via its module-qualified path.
"""

from __future__ import annotations

from enum import StrEnum


class ColonialStance(StrEnum):
    """The fundamental political axis (spec-070 FR-002).

    The principal contradiction in MLM-TW analysis (Constitution I.1):
    settler colonialism vs anti-settler liberation. Every
    :class:`~babylon.models.entities.balkanization_faction.BalkanizationFaction`
    has exactly one ``colonial_stance``, which deterministically derives the
    Sovereign's :class:`ExtractionPolicy` when that faction rules.

    Values:
        UPHOLD: Defend settler sovereignty; intensify extraction.
        IGNORE: Focus on class struggle while ignoring land
            (the RED_OGV trap per spec-070 FR-032).
        ABOLISH: Dismantle the settler relationship; cease extraction.
    """

    UPHOLD = "uphold"
    IGNORE = "ignore"
    ABOLISH = "abolish"


class ExtractionPolicy(StrEnum):
    """Sovereign's per-tick relationship to extractive production
    (spec-070 FR-003).

    Derived deterministically from ``ruling_faction.colonial_stance`` via
    :func:`~babylon.formulas.balkanization.derive_extraction_policy_from_stance`.
    Drives Territory habitability through ``metabolic_impact`` per FR-004.

    Values:
        INTENSIFY: From UPHOLD; ``metabolic_impact = -0.02`` per tick.
        CONTINUE: From IGNORE; ``metabolic_impact = -0.005`` per tick.
        CEASE: From ABOLISH; ``metabolic_impact = +0.01`` per tick.
    """

    INTENSIFY = "intensify"
    CONTINUE = "continue"
    CEASE = "cease"


class SovereigntyType(StrEnum):
    """Classification of a sovereign claim (spec-070 FR-002).

    Used by FR-032a's ``FRAGMENTED_COLLAPSE`` predicate, which requires
    at least one sovereign of type ``INSURGENT``, ``OCCUPATION``, or
    ``EMERGENCY``.

    Values:
        RECOGNIZED_STATE: Internationally recognized sovereign authority.
        PROVISIONAL: Transitional / revolutionary government.
        INSURGENT: Armed revolutionary movement.
        OCCUPATION: Military occupation authority.
        SECESSIONIST: Breakaway state seeking recognition.
        EMERGENCY: Emergency / martial-law authority.
    """

    RECOGNIZED_STATE = "recognized_state"
    PROVISIONAL = "provisional"
    INSURGENT = "insurgent"
    OCCUPATION = "occupation"
    SECESSIONIST = "secessionist"
    EMERGENCY = "emergency"


class FiscalStatus(StrEnum):
    """Revenue relationship on a CLAIMS edge (spec-070 FR-010).

    Values:
        TAXED: Normal revenue extraction from the territory.
        REVOLT: Tax resistance reduces revenue.
        BLOCKADE: External forces prevent revenue collection.
        LIBERATED: No taxation (revolutionary zone).
        OCCUPIED: Extraction by military force.
    """

    TAXED = "taxed"
    REVOLT = "revolt"
    BLOCKADE = "blockade"
    LIBERATED = "liberated"
    OCCUPIED = "occupied"


class ClaimLegalStatus(StrEnum):
    """Legal nature of a CLAIMS edge (spec-070 FR-011).

    Distinct from :class:`babylon.models.enums.legal.LegalStatus`, which
    is the spec-022 community-repression escalation enum (LEGAL /
    SURVEILLED / DESIGNATED_EXTREMIST / DESIGNATED_TERRORIST /
    CRIMINALIZED). The spec-070 enum lives under a different name to
    avoid the public-import-surface collision.

    Values:
        DE_JURE: Internationally recognized claim.
        DE_FACTO: Actual control without recognition.
        DISPUTED: Multiple claimants; no clear winner.
        OCCUPIED: Military occupation; original sovereignty suspended.
        CEDED: Formerly held; formally transferred.
    """

    DE_JURE = "de_jure"
    DE_FACTO = "de_facto"
    DISPUTED = "disputed"
    OCCUPIED = "occupied"
    CEDED = "ceded"


class SupportType(StrEnum):
    """Primary form of support carried by an INFLUENCES edge
    (spec-070 FR-015).

    Used by the seed pipeline in
    :mod:`babylon.data.game.balkanization.compute_seed_influences` to
    annotate the proxy-data origin of each seeded influence edge.

    Values:
        MATERIAL: Money, weapons, supplies.
        IDEOLOGICAL: Propaganda, education, media.
        MILITARY: Armed cadre, militias.
        ELECTORAL: Voter base, candidates.
        LABOR: Union presence, strike capability.
    """

    MATERIAL = "material"
    IDEOLOGICAL = "ideological"
    MILITARY = "military"
    ELECTORAL = "electoral"
    LABOR = "labor"


class PlayerMode(StrEnum):
    """Player interaction mode for a run (spec-070 FR-047).

    Values:
        CAMPAIGN: Player picks one faction; verbs route through the
            spec-072 economy.
        OBSERVER: God-mode; direct INFLUENCES / CLAIMS manipulation
            via the GraphProtocol with each mutation flagged in the
            audit log (FR-049).
    """

    CAMPAIGN = "campaign"
    OBSERVER = "observer"


__all__ = [
    "ClaimLegalStatus",
    "ColonialStance",
    "ExtractionPolicy",
    "FiscalStatus",
    "PlayerMode",
    "SovereigntyType",
    "SupportType",
]
