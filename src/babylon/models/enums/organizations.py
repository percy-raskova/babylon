"""Organization, state apparatus, and surveillance enums.

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class ServiceType(StrEnum):
    """Civil society service domain (Feature 031).

    Categorizes the primary service provided by a CivilSocietyOrg.
    Affects legitimacy derivation and community trust.

    Values:
        RELIGIOUS: Churches, mosques, temples
        EDUCATIONAL: Schools, universities, training programs
        HEALTHCARE: Hospitals, clinics, health collectives
        LEGAL_AID: Legal defense, bail funds
        MUTUAL_AID: Direct material support networks
        CULTURAL: Arts, cultural preservation organizations
        MEDIA: News, broadcasting, publishing
        LABOR: Unions, worker centers, cooperatives
    """

    RELIGIOUS = "religious"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    LEGAL_AID = "legal_aid"
    MUTUAL_AID = "mutual_aid"
    CULTURAL = "cultural"
    MEDIA = "media"
    LABOR = "labor"


class StateFaction(StrEnum):
    """Ruling-class factions within the state coalition (Feature 039).

    Each faction has a distinct material base and strategic verb preferences.
    The factional balance at any moment determines the state's objective
    function and verb selection.

    Values:
        FINANCE_CAPITAL: Material base in extraction efficiency and profit rate.
            Prefers CO_OPT, DEVELOP. Tolerates organizing unless it threatens
            accumulation.
        SECURITY_STATE: Material base in repressive apparatus. Prefers REPRESS,
            ADMINISTER. Institutional incentive to maintain threat perception.
        SETTLER_POPULIST: Material base in imperial rent distribution to settler
            nation. Provides mass base for fascism when imperial rent contracts.

    Reference: FR-C01, Constitution I.4 (George Jackson Bifurcation).
    """

    FINANCE_CAPITAL = "finance_capital"
    SECURITY_STATE = "security_state"
    SETTLER_POPULIST = "settler_populist"


class StateActionType(StrEnum):
    """State verb taxonomy for apparatus AI decision-making (Feature 039).

    Six top-level verbs with ~24 sub-verbs. These are SEPARATE from
    the player ActionType enum (Feature 032). The type system enforces
    asymmetry: the state cannot EDUCATE or STRIKE; the player cannot
    LEGISLATE or DISPLACE.

    Reference: FR-B01 through FR-B11, Constitution V (Action Vocabulary).

    Values:
        ADMINISTER: Internal capacity management.
        DEVELOP: Reshape the material base.
        RESEARCH: Expand capability space.
        CO_OPT: Absorb, neutralize, divide.
        REPRESS: Direct state violence.
        WITHDRAW: Concede, reposition, destroy.
    """

    # Top-level verbs
    ADMINISTER = "administer"
    DEVELOP = "develop"
    RESEARCH = "research"
    CO_OPT = "co_opt"
    REPRESS = "repress"
    WITHDRAW = "withdraw"

    # ADMINISTER sub-verbs
    FUND = "fund"
    STAFF = "staff"
    LEGISLATE = "legislate"
    AUDIT = "audit"
    REVOKE = "revoke"

    # DEVELOP sub-verbs
    INVEST = "invest"
    REZONE = "rezone"
    DISPLACE = "displace"
    NEGLECT = "neglect"

    # RESEARCH sub-verbs
    PURSUE_TECH = "pursue_tech"
    DEPLOY_TECH = "deploy_tech"

    # CO_OPT sub-verbs
    BRIBE = "bribe"
    PROPAGANDIZE = "propagandize"
    INCORPORATE = "incorporate"
    DIVIDE = "divide"

    # REPRESS sub-verbs
    SURVEIL = "surveil_state"
    INFILTRATE = "infiltrate_state"
    RAID = "raid"
    PROSECUTE = "prosecute"
    LIQUIDATE = "liquidate"

    # WITHDRAW sub-verbs
    STRATEGIC_WITHDRAWAL = "strategic_withdrawal"
    TACTICAL_RETREAT = "tactical_retreat"
    SCORCHED_EARTH = "scorched_earth"


class ThreadPhase(StrEnum):
    """Attention thread intelligence phase (Feature 039).

    Threads progress through discrete phases as intel_completeness
    grows. Phase transitions are quantitative-to-qualitative changes
    (Constitution I.7) driven by intel_completeness thresholds
    configured in StateApparatusAIDefines.

    Values:
        DORMANT: Thread exists but not actively resourced.
        MONITORING: Passive intelligence gathering. Low resource cost.
        ACTIVE_INVESTIGATION: Dedicated analysis. Sparrow analysis available.
        DISRUPTION: Active operations against target. Highest resource cost.

    Reference: FR-A08, R-002.
    """

    DORMANT = "dormant"
    MONITORING = "monitoring"
    ACTIVE_INVESTIGATION = "active_investigation"
    DISRUPTION = "disruption"


class SurveillanceMethod(StrEnum):
    """Intelligence collection methods for attention threads (Feature 039).

    Each method reveals specific graph structures while missing others.
    No single method reveals the full picture (Sparrow's intelligence
    mosaic). Players can exploit method-specific blind spots (e.g.,
    cash economy defeats FINANCIAL surveillance, face-to-face meetings
    defeat SIGNALS).

    Reference: FR-A06, R-007.

    Values:
        SIGNALS: Communication metadata (phone, email, encrypted messaging).
        FINANCIAL: Bank records, transaction monitoring, asset tracing.
        SOCIAL_MEDIA: Public-facing digital footprint analysis.
        INFORMANT: Human intelligence via recruited insiders.
        PHYSICAL: Direct observation, tailing, stakeouts.
    """

    SIGNALS = "signals"
    FINANCIAL = "financial"
    SOCIAL_MEDIA = "social_media"
    INFORMANT = "informant"
    PHYSICAL = "physical"


class InternetResponseMode(StrEnum):
    """State apparatus internet control modes (Feature 036).

    Determines how the state apparatus modulates internet consciousness
    diffusion at a given hex. PERMIT is default. THROTTLE is covert.
    SEVER is overt and triggers consciousness backfire.

    Values:
        PERMIT: Full throughput, full surveillance
        THROTTLE: Reduced throughput, maintained surveillance, covert
        SEVER: Zero throughput, zero surveillance, overt with backfire
    """

    PERMIT = "permit"
    THROTTLE = "throttle"
    SEVER = "sever"


class ApparatusType(StrEnum):
    """Althusserian apparatus type classification (Feature 040).

    Institutions are classified by their structural role in the reproduction
    of class relations. RSA types operate through repression, ISA types
    through ideology, and Economic types through surplus extraction.

    Values:
        RSA_EXECUTIVE: Government, administration
        RSA_MILITARY: Armed forces
        RSA_POLICE: Police departments
        RSA_JUDICIAL: Courts
        RSA_CARCERAL: Prisons
        ISA_EDUCATIONAL: Schools, universities
        ISA_RELIGIOUS: Churches, religious orders
        ISA_FAMILY: The family as institution
        ISA_LEGAL: Legal system as ideology
        ISA_POLITICAL: Electoral system, party system
        ISA_COMMUNICATIONS: Media
        ISA_CULTURAL: Arts, sports, cultural bodies
        ECONOMIC_PRODUCTIVE: Firms, factories
        ECONOMIC_FINANCIAL: Banks, exchanges
        ECONOMIC_EXTRACTIVE: Mining, resource firms
    """

    RSA_EXECUTIVE = "rsa_executive"
    RSA_MILITARY = "rsa_military"
    RSA_POLICE = "rsa_police"
    RSA_JUDICIAL = "rsa_judicial"
    RSA_CARCERAL = "rsa_carceral"
    ISA_EDUCATIONAL = "isa_educational"
    ISA_RELIGIOUS = "isa_religious"
    ISA_FAMILY = "isa_family"
    ISA_LEGAL = "isa_legal"
    ISA_POLITICAL = "isa_political"
    ISA_COMMUNICATIONS = "isa_communications"
    ISA_CULTURAL = "isa_cultural"
    ECONOMIC_PRODUCTIVE = "economic_productive"
    ECONOMIC_FINANCIAL = "economic_financial"
    ECONOMIC_EXTRACTIVE = "economic_extractive"


class LifecyclePhase(StrEnum):
    """D-P-D' lifecycle phase assignment for institutions (Feature 040).

    Optional phase assignment determining which stage of the lifecycle
    circuit an institution primarily mediates.

    Values:
        D_DEPENDENT: Youth/dependent -- controls ideological transmission
        P_PRODUCTIVE: Adult/productive -- where surplus extraction occurs
        D_PRIME_DEPENDENT: Elder/dependent -- the legitimation bargain
    """

    D_DEPENDENT = "d_dependent"
    P_PRODUCTIVE = "p_productive"
    D_PRIME_DEPENDENT = "d_prime_dependent"


__all__ = [
    "ApparatusType",
    "InternetResponseMode",
    "LifecyclePhase",
    "ServiceType",
    "StateActionType",
    "StateFaction",
    "SurveillanceMethod",
    "ThreadPhase",
]
