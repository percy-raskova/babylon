"""Ideology, intensity, and contradiction enums.

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class ContradictionType(StrEnum):
    """Main axes of structural contradiction (Constitutional Framework).

    Moving away from hardcoded models towards a dynamic Maoist contradiction
    framework. Defines the principal and secondary axes at a given scale.
    """

    NATIONAL = "national"
    CLASS = "class"
    GENDER = "gender"
    IMPERIAL = "imperial"
    ECOLOGICAL = "ecological"


class IntensityLevel(StrEnum):
    """Intensity scale for contradictions and tensions.

    Contradictions exist on a spectrum from dormant (latent potential)
    to critical (imminent rupture). This enum provides discrete levels
    for game mechanics while the underlying simulation may use
    continuous float values.

    Values:
        DORMANT: Contradiction exists but not yet manifest
        LOW: Minor tensions, easily managed
        MEDIUM: Noticeable conflict, requires attention
        HIGH: Serious crisis, intervention needed
        CRITICAL: Rupture imminent, phase transition likely
    """

    DORMANT = "dormant"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionCharacter(StrEnum):
    """Character flag for contradictions on edges.

    Dialectical Field Topology (Feature 002), FR-018: Every edge carrying
    an edge_mode also carries a contradiction_character flag indicating
    whether the contradiction is antagonistic (irreconcilable within the
    current mode of production) or non-antagonistic.

    Reference: Constitution I.14 (antagonistic vs non-antagonistic contradictions)

    Values:
        ANTAGONISTIC: Irreconcilable within current mode of production
        NON_ANTAGONISTIC: Resolvable without systemic transformation
    """

    ANTAGONISTIC = "antagonistic"
    NON_ANTAGONISTIC = "non_antagonistic"


class ConsciousnessTendency(StrEnum):
    """Dominant ideological tendency within a community (Feature 029).

    Represents the prevailing direction of collective consciousness — the
    default drift without active organizing.

    Values:
        LIBERAL: Seeks inclusion in existing institutions without transforming
            them. Organizational vehicle: liberal CSOs, Democratic Party.
        FASCIST: Collaboration with hegemonic order for individual escape.
            Strategy: shrink the marginalized definition, exclude the most marginal.
        REVOLUTIONARY: Oppositional collective identity, independent power.
            The contradiction is material, not a misunderstanding.
    """

    LIBERAL = "liberal"
    FASCIST = "fascist"
    REVOLUTIONARY = "revolutionary"


__all__ = [
    "ConsciousnessTendency",
    "ContradictionCharacter",
    "ContradictionType",
    "IntensityLevel",
]
