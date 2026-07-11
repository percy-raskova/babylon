"""Class and role enums (MLM-TW class positions, organizational types).

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class SocialRole(StrEnum):
    """Class position in the world system.

    Based on Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory,
    classes are defined by their relationship to production AND their
    position in the imperial hierarchy.

    Values:
        CORE_BOURGEOISIE: Owns means of production in imperial core
        PERIPHERY_PROLETARIAT: Sells labor in exploited periphery
        LABOR_ARISTOCRACY: Core workers benefiting from imperial rent
        PETTY_BOURGEOISIE: Small owners, professionals, shopkeepers
        LUMPENPROLETARIAT: Outside formal economy, precarious existence
        COMPRADOR_BOURGEOISIE: Intermediary class in periphery, collaborates with imperial core
        INTERNAL_PROLETARIAT: Core workers outside LA (precariat, unemployed, incarcerated)
        CARCERAL_ENFORCER: Guards, cops, prison staff (repressive apparatus)

    Terminal Crisis Dynamics (ai/terminal-crisis-dynamics.md):
        When peripheral extraction fails and super-wages deplete, the Labor
        Aristocracy decomposes into CARCERAL_ENFORCER (30%) and INTERNAL_PROLETARIAT
        (70%). This models the carceral turn from productive to coercive labor.
    """

    CORE_BOURGEOISIE = "core_bourgeoisie"
    PERIPHERY_PROLETARIAT = "periphery_proletariat"
    LABOR_ARISTOCRACY = "labor_aristocracy"
    PETTY_BOURGEOISIE = "petty_bourgeoisie"
    LUMPENPROLETARIAT = "lumpenproletariat"
    COMPRADOR_BOURGEOISIE = "comprador_bourgeoisie"
    # Terminal Crisis Dynamics - Carceral Turn
    INTERNAL_PROLETARIAT = "internal_proletariat"
    CARCERAL_ENFORCER = "carceral_enforcer"


class MembershipRole(StrEnum):
    """Agent integration level within a community.

    Hypergraph Community Layer (Feature 022): Determines membership
    strength weight and visibility profile for threat score computation.

    Values:
        CORE_ORGANIZER: Infrastructure maintainers, visible leaders (weight 1.0)
        ACTIVE: Regular participants, known within community (weight 0.7)
        PARTICIPANT: Occasional engagement (weight 0.4)
        PERIPHERAL: Marginal connection (weight 0.2)
        SYMPATHIZER: External ally, not legible as member (weight 0.1)
    """

    CORE_ORGANIZER = "core_organizer"
    ACTIVE = "active"
    PARTICIPANT = "participant"
    PERIPHERAL = "peripheral"
    SYMPATHIZER = "sympathizer"


class OrgType(StrEnum):
    """Organization category discriminator (Feature 031).

    Used as the Pydantic discriminated union discriminator field to dispatch
    to the correct Organization subtype.

    Values:
        STATE_APPARATUS: Wields state violence/surveillance
        BUSINESS: Accumulates capital, employs labor
        POLITICAL_FACTION: Contests political power
        CIVIL_SOCIETY: Non-state, non-business collective
    """

    STATE_APPARATUS = "state_apparatus"
    BUSINESS = "business"
    POLITICAL_FACTION = "political_faction"
    CIVIL_SOCIETY = "civil_society"


class ClassCharacter(StrEnum):
    """Which class an organization objectively serves (Feature 031).

    May differ from the organization's stated mission or membership
    composition. Determined by material analysis of the organization's
    structural role in class reproduction.

    Values:
        BOURGEOIS: Serves bourgeois class interests
        PETTY_BOURGEOIS: Serves petty bourgeois class interests
        LABOR_ARISTOCRATIC: Serves labor aristocracy interests
        PROLETARIAN: Serves proletarian class interests
        LUMPEN: Serves lumpenproletariat interests
        CONTESTED: Class character actively contested
    """

    BOURGEOIS = "bourgeois"
    PETTY_BOURGEOIS = "petty_bourgeois"
    LABOR_ARISTOCRATIC = "labor_aristocratic"
    PROLETARIAN = "proletarian"
    LUMPEN = "lumpen"
    CONTESTED = "contested"


class SocialFunction(StrEnum):
    """Population need served by an institution (Feature 040).

    Each institution carries a social function representing a material
    need of the population. Institutions persist as long as their social
    function is needed and unmet by alternatives.

    Values:
        EMPLOYMENT: Job provision
        EDUCATION: Knowledge transmission
        WORSHIP: Meaning-making, spiritual community
        POLICING: Public safety (however distorted)
        HEALTHCARE: Medical care provision
        CARE: Dependent care (childcare, eldercare)
        ADJUDICATION: Dispute resolution, justice
        COMMUNICATION: Information dissemination
        LEGISLATION: Law-making
        INCARCERATION: Detention and punishment
        MILITARY_DEFENSE: National defense
        FINANCIAL_INTERMEDIATION: Banking, credit, investment
    """

    EMPLOYMENT = "employment"
    EDUCATION = "education"
    WORSHIP = "worship"
    POLICING = "policing"
    HEALTHCARE = "healthcare"
    CARE = "care"
    ADJUDICATION = "adjudication"
    COMMUNICATION = "communication"
    LEGISLATION = "legislation"
    INCARCERATION = "incarceration"
    MILITARY_DEFENSE = "military_defense"
    FINANCIAL_INTERMEDIATION = "financial_intermediation"


class ClassInscription(StrEnum):
    """Class inscription of an institution (Feature 040).

    More resistant to change than Organization.class_character. Changes
    only through sustained class struggle on coefficient timescale
    (alpha-smoothed).

    Values:
        BOURGEOIS: Serves ruling class interests
        PROLETARIAN: Serves working class interests
        CONTESTED: Actively contested terrain
    """

    BOURGEOIS = "bourgeois"
    PROLETARIAN = "proletarian"
    CONTESTED = "contested"


class RulingClassFraction(StrEnum):
    """Ruling-class faction within institutional balance of forces (Feature 040).

    Three-value classification of competing strategies for maintaining
    class rule. The hegemonic fraction (highest weight) modulates
    housed Organization OODA orientation.

    Values:
        LIBERAL_TECHNOCRATIC: Consent-based rule, slow escalation
        REVANCHIST_FASCIST: Naked repression, fast escalation
        INSTITUTIONALIST_BONAPARTIST: Self-preservation, institutional independence
    """

    LIBERAL_TECHNOCRATIC = "liberal_technocratic"
    REVANCHIST_FASCIST = "revanchist_fascist"
    INSTITUTIONALIST_BONAPARTIST = "institutionalist_bonapartist"


__all__ = [
    "ClassCharacter",
    "ClassInscription",
    "MembershipRole",
    "OrgType",
    "RulingClassFraction",
    "SocialFunction",
    "SocialRole",
]
