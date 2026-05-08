"""Legal status, legitimation, and dispossession enums.

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class LegitimationClassification(StrEnum):
    """Crisis classification for the legitimation index (Feature 030).

    Classifies the legitimation index into three regimes based on
    material conditions underwriting the D' promise.

    Values:
        CRISIS: Index < 0.3 — D' promise not credible, agitation routes to bifurcation.
        UNSTABLE: Index < 0.5 — D' promise weakening, risk accumulating.
        STABLE: Index >= 0.5 — D' promise credible, acquiescence maintained.
    """

    CRISIS = "crisis"
    UNSTABLE = "unstable"
    STABLE = "stable"


class DispossessionType(StrEnum):
    """Categories of ongoing primitive accumulation.

    Eight types of extra-economic wealth seizure that transfer value from
    working-class households to capital. These represent Marx's "primitive
    accumulation" as an ongoing process, not a historical phase.

    Feature 021: Capital Volume I Production Dynamics (FR-004).
    """

    FORECLOSURE = "foreclosure"
    EVICTION = "eviction"
    TAX_SALE = "tax_sale"
    EMINENT_DOMAIN = "eminent_domain"
    WAGE_THEFT = "wage_theft"
    INCARCERATION_SEIZURE = "incarceration_seizure"
    PENSION_DEFAULT = "pension_default"
    GENTRIFICATION_DISPLACEMENT = "gentrification_displacement"


class ExploitationMode(StrEnum):
    """Dominant mode of surplus value extraction for a territory-sector.

    Classifies how surplus value is extracted: by lengthening the working
    day (absolute), by increasing productivity during a fixed day (relative),
    or a blend of both.

    Feature 021: Capital Volume I Production Dynamics (FR-007).
    """

    ABSOLUTE_DOMINANT = "absolute_dominant"
    RELATIVE_DOMINANT = "relative_dominant"
    MIXED = "mixed"


class LegalStatus(StrEnum):
    """Legal designation status for community-level state repression.

    Hypergraph Community Layer (Feature 022): Escalation is strictly
    one-way for state action. De-escalation requires political struggle
    (player action). Each level increases the threat multiplier applied
    to community members.

    Values:
        LEGAL: Normal status, minimal state attention (multiplier 0.1)
        SURVEILLED: Active monitoring (multiplier 0.5)
        DESIGNATED_EXTREMIST: Formal extremist designation (multiplier 1.0)
        DESIGNATED_TERRORIST: Formal terrorist designation (multiplier 2.0)
        CRIMINALIZED: Membership itself criminalized (multiplier 3.0)
    """

    LEGAL = "legal"
    SURVEILLED = "surveilled"
    DESIGNATED_EXTREMIST = "designated_extremist"
    DESIGNATED_TERRORIST = "designated_terrorist"
    CRIMINALIZED = "criminalized"


class LegalStanding(StrEnum):
    """Legal status of an organization (Feature 031).

    Determines the organization's relationship to the state legal apparatus
    and affects credibility derivation for consciousness effect calculations.

    Values:
        SOVEREIGN: State itself (government agencies)
        CHARTERED: State-authorized entity (corporations, licensed orgs)
        REGISTERED: Officially registered (nonprofits, registered parties)
        INFORMAL: No legal registration (neighborhood groups, informal networks)
        UNDERGROUND: Explicitly illegal (banned organizations, clandestine cells)
    """

    SOVEREIGN = "sovereign"
    CHARTERED = "chartered"
    REGISTERED = "registered"
    INFORMAL = "informal"
    UNDERGROUND = "underground"


class JurisdictionLevel(StrEnum):
    """Scope of state apparatus authority (Feature 031).

    Used exclusively by StateApparatus subtypes to define the geographical
    and legal scope of their jurisdiction.

    Values:
        NATIONAL: Federal jurisdiction
        STATE: State-level jurisdiction
        COUNTY: County-level jurisdiction
        MUNICIPAL: City/municipal jurisdiction
    """

    NATIONAL = "national"
    STATE = "state"
    COUNTY = "county"
    MUNICIPAL = "municipal"


__all__ = [
    "DispossessionType",
    "ExploitationMode",
    "JurisdictionLevel",
    "LegalStanding",
    "LegalStatus",
    "LegitimationClassification",
]
